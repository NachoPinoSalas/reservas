"""Configuración del cliente, plantas y espacios: asistente del administrador (FR-004, FR-005, FR-033)."""
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app import rol_requerido
from app.correo import enviar_reserva
from app.db import get_db, transaccion
from app.fechas import a_minutos, ahora, es_hora
from app.reservas import encaja, reservas_futuras

bp = Blueprint("cliente", __name__, url_prefix="/admin")

MAX_LOGO = 500 * 1024
MOTIVO_CAMBIO = (
    "El cliente ha cambiado sus días, su horario o la duración de las reservas, "
    "y su reserva ya no encaja en el nuevo calendario."
)


def _entero(texto):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return None


def leer_configuracion(form):
    """Lee los datos del cliente del formulario. Devuelve (datos, errores)."""
    dias = sorted({d for d in form.getlist("dias") if d in {"0", "1", "2", "3", "4", "5", "6"}})
    datos = {
        "nombre": (form.get("nombre") or "").strip(),
        "dias": ",".join(dias),
        "apertura": (form.get("apertura") or "").strip(),
        "cierre": (form.get("cierre") or "").strip(),
        "duracion_min": _entero(form.get("duracion_min")),
        "antelacion_max_dias": _entero(form.get("antelacion_max_dias")),
        "cancelacion_min_horas": _entero(form.get("cancelacion_min_horas")),
    }
    return datos, validar_configuracion(datos)


def validar_configuracion(datos):
    errores = []
    if not datos["nombre"]:
        errores.append("Indique el nombre del cliente.")
    if not datos["dias"]:
        errores.append("Elija al menos un día de reserva.")
    horario_valido = es_hora(datos["apertura"]) and es_hora(datos["cierre"])
    if not horario_valido:
        errores.append("Indique la hora de apertura y la de cierre (hh:mm).")
    elif a_minutos(datos["cierre"]) <= a_minutos(datos["apertura"]):
        errores.append("La hora de cierre debe ser posterior a la de apertura.")
        horario_valido = False
    duracion = datos["duracion_min"]
    if duracion is None or duracion <= 0 or duracion % 15:
        errores.append("La duración debe ser un múltiplo de 15 minutos (por ejemplo 15, 60 o 120).")
    elif horario_valido and a_minutos(datos["apertura"]) + duracion > a_minutos(datos["cierre"]):
        errores.append("La duración no cabe en el horario: debe caber al menos una reserva entre la apertura y el cierre.")
    if datos["antelacion_max_dias"] is None or datos["antelacion_max_dias"] < 0:
        errores.append("El plazo máximo de antelación debe ser un número de días (0 o más).")
    if datos["cancelacion_min_horas"] is None or datos["cancelacion_min_horas"] < 0:
        errores.append("El plazo mínimo de cancelación debe ser un número de horas (0 o más).")
    return errores


def leer_logo(fichero):
    """Logo opcional PNG o JPG de tamaño limitado. Devuelve (contenido, tipo, error)."""
    contenido = fichero.read()
    if len(contenido) > MAX_LOGO:
        return None, None, "El logo no puede ocupar más de 500 KB."
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return contenido, "image/png", None
    if contenido.startswith(b"\xff\xd8\xff"):
        return contenido, "image/jpeg", None
    return None, None, "El logo debe ser una imagen PNG o JPG."


def reservas_que_no_encajan(conexion, nuevo, momento=None):
    """Reservas futuras vigentes que dejarían de encajar con la nueva configuración (FR-033)."""
    momento = momento or ahora()
    return [r for r in reservas_futuras(conexion, momento) if not encaja(nuevo, r["dia"], r["hora_inicio"])]


def aplicar_horario(conexion, nuevo, momento=None):
    """Guarda días, horario y duración, y cancela las reservas que dejan de encajar. Las devuelve."""
    afectadas = reservas_que_no_encajan(conexion, nuevo, momento)
    with transaccion(conexion):
        conexion.execute(
            "UPDATE cliente SET dias = ?, apertura = ?, cierre = ?, duracion_min = ? WHERE id = 1",
            (nuevo["dias"], nuevo["apertura"], nuevo["cierre"], nuevo["duracion_min"]),
        )
        for reserva in afectadas:
            conexion.execute(
                "UPDATE reserva SET estado = 'cancelada' WHERE id = ? AND estado = 'vigente'", (reserva["id"],)
            )
    return afectadas


def contar_futuras(conexion, condicion, parametros):
    return len(reservas_futuras(conexion, ahora(), condicion, parametros))


@bp.route("/cliente", methods=["GET", "POST"])
@rol_requerido("administrador")
def datos():
    """Paso 1 del asistente: nombre, logo, días, horario, duración y plazos."""
    if request.method == "GET":
        return render_template("asistente.html", datos=dict(g.cliente), errores=[])

    conexion = get_db()
    datos, errores = leer_configuracion(request.form)
    logo = request.files.get("logo")
    contenido = tipo = None
    if logo and logo.filename:
        contenido, tipo, error = leer_logo(logo)
        if error:
            errores.append(error)
    if errores:
        return render_template("asistente.html", datos=datos, errores=errores), 400

    # Nombre, logo y plazos no descuadran reservas: se guardan siempre.
    conexion.execute(
        "UPDATE cliente SET nombre = ?, antelacion_max_dias = ?, cancelacion_min_horas = ? WHERE id = 1",
        (datos["nombre"], datos["antelacion_max_dias"], datos["cancelacion_min_horas"]),
    )
    if contenido:
        conexion.execute("UPDATE cliente SET logo = ?, logo_tipo = ? WHERE id = 1", (contenido, tipo))
    elif request.form.get("quitar_logo"):
        conexion.execute("UPDATE cliente SET logo = NULL, logo_tipo = NULL WHERE id = 1")
    conexion.commit()

    afectadas = reservas_que_no_encajan(conexion, datos)
    if afectadas:
        return render_template("cliente_confirmar_cambio.html", datos=datos, cuantas=len(afectadas))
    aplicar_horario(conexion, datos)
    flash("Configuración guardada.", "ok")
    if not g.cliente["configurado"]:
        return redirect(url_for("cliente.espacios"))
    return redirect(url_for("cliente.datos"))


@bp.route("/cliente/confirmar-horario", methods=["POST"])
@rol_requerido("administrador")
def confirmar_horario():
    """El administrador acepta cancelar las reservas que dejan de encajar (FR-033)."""
    conexion = get_db()
    datos, errores = leer_configuracion(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("cliente.datos"))
    cliente_anterior = g.cliente  # la duración antigua da la hora de fin correcta en el email
    canceladas = aplicar_horario(conexion, datos)
    fallidos = sum(not enviar_reserva("cancelada", r, cliente_anterior, MOTIVO_CAMBIO) for r in canceladas)
    flash(
        f"Configuración guardada. Se han cancelado {len(canceladas)} reservas y se ha avisado por email a sus usuarios.",
        "ok",
    )
    if fallidos:
        flash(f"No se ha podido enviar el email de cancelación a {fallidos} usuarios.", "info")
    return redirect(url_for("cliente.datos"))


@bp.route("/espacios")
@rol_requerido("administrador")
def espacios():
    """Paso 2 del asistente: plantas (opcionales) y espacios."""
    conexion = get_db()
    plantas = conexion.execute("SELECT * FROM planta ORDER BY nombre").fetchall()
    lista = conexion.execute(
        "SELECT e.*, p.nombre AS planta FROM espacio e LEFT JOIN planta p ON p.id = e.planta_id "
        "WHERE e.eliminado = 0 ORDER BY p.nombre, e.nombre"
    ).fetchall()
    return render_template("espacios.html", plantas=plantas, espacios=lista)


def _planta_elegida(conexion, texto):
    """'' → sin planta; si no, el id de una planta existente. Devuelve (planta_id, válido)."""
    if not texto:
        return None, True
    planta_id = _entero(texto)
    existe = planta_id is not None and conexion.execute(
        "SELECT 1 FROM planta WHERE id = ?", (planta_id,)
    ).fetchone()
    return planta_id, bool(existe)


@bp.route("/plantas", methods=["POST"])
@rol_requerido("administrador")
def crear_planta():
    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("Indique el nombre de la planta.", "error")
        return redirect(url_for("cliente.espacios"))
    conexion = get_db()
    try:
        conexion.execute("INSERT INTO planta (nombre) VALUES (?)", (nombre,))
        conexion.commit()
        flash(f"Planta «{nombre}» creada.", "ok")
    except sqlite3.IntegrityError:
        conexion.rollback()
        flash("Ya existe una planta con ese nombre.", "error")
    return redirect(url_for("cliente.espacios"))


@bp.route("/plantas/<int:planta_id>", methods=["POST"])
@rol_requerido("administrador")
def renombrar_planta(planta_id):
    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("Indique el nombre de la planta.", "error")
        return redirect(url_for("cliente.espacios"))
    conexion = get_db()
    try:
        conexion.execute("UPDATE planta SET nombre = ? WHERE id = ?", (nombre, planta_id))
        conexion.commit()
        flash("Planta guardada.", "ok")
    except sqlite3.IntegrityError:
        conexion.rollback()
        flash("Ya existe una planta con ese nombre.", "error")
    return redirect(url_for("cliente.espacios"))


@bp.route("/plantas/<int:planta_id>/eliminar", methods=["POST"])
@rol_requerido("administrador")
def eliminar_planta(planta_id):
    conexion = get_db()
    futuras = contar_futuras(conexion, "e.planta_id = ?", (planta_id,))
    if futuras:
        flash(f"No se puede eliminar la planta: sus espacios tienen {futuras} reservas futuras.", "error")
        return redirect(url_for("cliente.espacios"))
    # Sus espacios se quedan sin planta.
    conexion.execute("DELETE FROM planta WHERE id = ?", (planta_id,))
    conexion.commit()
    flash("Planta eliminada.", "ok")
    return redirect(url_for("cliente.espacios"))


@bp.route("/espacios/nuevo", methods=["POST"])
@rol_requerido("administrador")
def crear_espacio():
    conexion = get_db()
    nombre = (request.form.get("nombre") or "").strip()
    planta_id, planta_valida = _planta_elegida(conexion, request.form.get("planta_id"))
    if not nombre or not planta_valida:
        flash("Indique el nombre del espacio y, si quiere, una planta existente.", "error")
        return redirect(url_for("cliente.espacios"))
    conexion.execute("INSERT INTO espacio (nombre, planta_id) VALUES (?, ?)", (nombre, planta_id))
    conexion.commit()
    flash(f"Espacio «{nombre}» creado.", "ok")
    return redirect(url_for("cliente.espacios"))


@bp.route("/espacios/<int:espacio_id>", methods=["POST"])
@rol_requerido("administrador")
def editar_espacio(espacio_id):
    conexion = get_db()
    nombre = (request.form.get("nombre") or "").strip()
    planta_id, planta_valida = _planta_elegida(conexion, request.form.get("planta_id"))
    if not nombre or not planta_valida:
        flash("Indique el nombre del espacio y, si quiere, una planta existente.", "error")
        return redirect(url_for("cliente.espacios"))
    conexion.execute(
        "UPDATE espacio SET nombre = ?, planta_id = ? WHERE id = ? AND eliminado = 0",
        (nombre, planta_id, espacio_id),
    )
    conexion.commit()
    flash("Espacio guardado.", "ok")
    return redirect(url_for("cliente.espacios"))


@bp.route("/espacios/<int:espacio_id>/eliminar", methods=["POST"])
@rol_requerido("administrador")
def eliminar_espacio(espacio_id):
    conexion = get_db()
    futuras = contar_futuras(conexion, "r.espacio_id = ?", (espacio_id,))
    if futuras:
        flash(f"No se puede eliminar el espacio: tiene {futuras} reservas futuras.", "error")
        return redirect(url_for("cliente.espacios"))
    # Se marca como eliminado para conservar el historial de sus reservas.
    conexion.execute("UPDATE espacio SET eliminado = 1 WHERE id = ?", (espacio_id,))
    conexion.commit()
    flash("Espacio eliminado.", "ok")
    return redirect(url_for("cliente.espacios"))


@bp.route("/terminar", methods=["POST"])
@rol_requerido("administrador")
def terminar():
    conexion = get_db()
    if not conexion.execute("SELECT 1 FROM espacio WHERE eliminado = 0").fetchone():
        flash("Añada al menos un espacio antes de terminar.", "error")
        return redirect(url_for("cliente.espacios"))
    conexion.execute("UPDATE cliente SET configurado = 1 WHERE id = 1")
    conexion.commit()
    flash("Cliente configurado. Ya se puede reservar.", "ok")
    return redirect(url_for("reservas.calendario"))
