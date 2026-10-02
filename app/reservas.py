"""Franjas, calendario y reservas: crear, modificar y cancelar."""
import sqlite3
from datetime import timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app import es_admin, rol_requerido
from app.correo import enviar_reserva
from app.db import get_db, transaccion
from app.fechas import a_minutos, ahora, de_minutos, inicio_reserva, leer_dia

bp = Blueprint("reservas", __name__)

MENSAJE_OCUPADO = "Este espacio acaba de ser reservado, elija otro"
MENSAJE_NO_DISPONIBLE = "Esa franja ya no está disponible, elija otra."
AVISO_EMAIL = "No se ha podido enviar el email con el resumen, pero la operación está guardada."

SQL_RESERVA = """
    SELECT r.*, e.nombre AS espacio, p.nombre AS planta,
           u.nombre AS u_nombre, u.apellidos AS u_apellidos, u.identificador AS u_email
    FROM reserva r
    JOIN espacio e ON e.id = r.espacio_id
    LEFT JOIN planta p ON p.id = e.planta_id
    JOIN usuario u ON u.id = r.usuario_id
"""


# --- Franjas: no se guardan, se calculan con la configuración del cliente (research D-05) ---

def dias_abiertos(cliente):
    return {int(d) for d in cliente["dias"].split(",") if d.strip()}


def horas_del_horario(cliente):
    """Horas de inicio de las franjas: de apertura a cierre, en pasos de la duración."""
    inicio, fin = a_minutos(cliente["apertura"]), a_minutos(cliente["cierre"])
    duracion = cliente["duracion_min"]
    horas = []
    while duracion > 0 and inicio + duracion <= fin:
        horas.append(de_minutos(inicio))
        inicio += duracion
    return horas


def calcular_franjas(cliente, dia, momento=None, sin_limite_antelacion=False):
    """Franjas reservables de un día: solo días abiertos, dentro del plazo y sin las ya empezadas."""
    momento = momento or ahora()
    hoy = momento.date()
    if dia < hoy or dia.weekday() not in dias_abiertos(cliente):
        return []
    if not sin_limite_antelacion and dia > hoy + timedelta(days=cliente["antelacion_max_dias"]):
        return []
    horas = horas_del_horario(cliente)
    if dia == hoy:
        actual = momento.strftime("%H:%M")
        horas = [hora for hora in horas if hora > actual]
    return horas


def dias_reservables(cliente, momento=None):
    momento = momento or ahora()
    hoy = momento.date()
    candidatos = (hoy + timedelta(days=n) for n in range(cliente["antelacion_max_dias"] + 1))
    return [dia for dia in candidatos if calcular_franjas(cliente, dia, momento)]


def encaja(cliente, dia, hora):
    """Una reserva encaja si su día está abierto y su hora es el inicio de una franja (FR-033)."""
    return leer_dia(dia).weekday() in dias_abiertos(cliente) and hora in horas_del_horario(cliente)


def hora_fin(cliente, hora):
    return de_minutos(a_minutos(hora) + cliente["duracion_min"])


# --- Datos ---

def obtener_reserva(conexion, reserva_id):
    return conexion.execute(SQL_RESERVA + " WHERE r.id = ?", (reserva_id,)).fetchone()


def reservas_futuras(conexion, momento, condicion="1 = 1", parametros=()):
    """Reservas vigentes que aún no han empezado."""
    hoy, hora = momento.date().isoformat(), momento.strftime("%H:%M")
    return conexion.execute(
        SQL_RESERVA + " WHERE r.estado = 'vigente' AND (r.dia > ? OR (r.dia = ? AND r.hora_inicio > ?))"
        f" AND {condicion} ORDER BY r.dia, r.hora_inicio",
        (hoy, hoy, hora, *parametros),
    ).fetchall()


def espacios_activos(conexion):
    return conexion.execute(
        "SELECT e.id, e.nombre, p.nombre AS planta FROM espacio e "
        "LEFT JOIN planta p ON p.id = e.planta_id WHERE e.eliminado = 0 ORDER BY p.nombre, e.nombre"
    ).fetchall()


def numero_reserva(dia, contador):
    anio, mes, dia_mes = dia.split("-")
    return f"{dia_mes}-{mes}-{anio}-{contador:04d}"


def crear_reserva(conexion, usuario_id, espacio_id, dia, hora):
    """Crea la reserva y su número en una sola operación (FR-019, FR-021).

    El contador es del año de la fecha de reserva y nunca se reutiliza. Si el hueco ya está
    ocupado, la base de datos lo rechaza y no se gasta número. Devuelve (id, error).
    """
    try:
        with transaccion(conexion):
            anio = int(dia[:4])
            conexion.execute(
                "INSERT INTO contador_reservas (anio, ultimo) VALUES (?, 1) "
                "ON CONFLICT (anio) DO UPDATE SET ultimo = ultimo + 1",
                (anio,),
            )
            contador = conexion.execute(
                "SELECT ultimo FROM contador_reservas WHERE anio = ?", (anio,)
            ).fetchone()[0]
            cursor = conexion.execute(
                "INSERT INTO reserva (numero, usuario_id, espacio_id, dia, hora_inicio, estado, creada_en) "
                "VALUES (?, ?, ?, ?, ?, 'vigente', ?)",
                (numero_reserva(dia, contador), usuario_id, espacio_id, dia, hora,
                 ahora().isoformat(timespec="seconds")),
            )
            return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        return None, MENSAJE_OCUPADO


def modificar_reserva(conexion, reserva_id, espacio_id, dia, hora):
    """Cambia día, hora o espacio conservando el número (FR-022). Devuelve el error o None."""
    try:
        with transaccion(conexion):
            conexion.execute(
                "UPDATE reserva SET espacio_id = ?, dia = ?, hora_inicio = ? WHERE id = ? AND estado = 'vigente'",
                (espacio_id, dia, hora, reserva_id),
            )
    except sqlite3.IntegrityError:
        return MENSAJE_OCUPADO
    return None


def cancelar_reserva(conexion, reserva_id):
    """Pasa la reserva a cancelada: el hueco queda libre y el número no se reutiliza."""
    with transaccion(conexion):
        cursor = conexion.execute(
            "UPDATE reserva SET estado = 'cancelada' WHERE id = ? AND estado = 'vigente'", (reserva_id,)
        )
    return cursor.rowcount == 1


def puede_cambiar(reserva, cliente, usuario, momento=None):
    """None si la reserva se puede modificar o cancelar; si no, el motivo para mostrarlo."""
    momento = momento or ahora()
    if reserva["estado"] != "vigente":
        return "La reserva está cancelada."
    inicio = inicio_reserva(reserva["dia"], reserva["hora_inicio"])
    if inicio <= momento:
        return "Solo se pueden cambiar reservas futuras."
    if es_admin(usuario):  # el administrador no tiene plazo mínimo (FR-024)
        return None
    horas = cliente["cancelacion_min_horas"]
    if inicio - momento <= timedelta(hours=horas):
        return f"Solo se puede modificar o cancelar una reserva con más de {horas} horas de antelación."
    return None


# --- Pantallas ---

def quien(nombre, apellidos, email):
    nombre_completo = f"{nombre} {apellidos}".strip()
    return f"{nombre_completo} ({email})" if nombre_completo else email


def _reserva_accesible(reserva_id):
    reserva = obtener_reserva(get_db(), reserva_id)
    if reserva is None or (not es_admin() and reserva["usuario_id"] != g.usuario["id"]):
        abort(404)
    return reserva


def _para_quien(reserva):
    if reserva["usuario_id"] == g.usuario["id"]:
        return None
    return quien(reserva["u_nombre"], reserva["u_apellidos"], reserva["u_email"])


def _url_vuelta(reserva):
    if reserva["usuario_id"] == g.usuario["id"]:
        return url_for("reservas.mis_reservas")
    return url_for("consulta.lista")


def _pantalla_calendario(titulo, url_dia, url_elegir, reserva=None, para_usuario=None):
    """Calendario: días permitidos → franjas con espacios libres y ocupados (FR-017, FR-018)."""
    conexion, cliente, momento = get_db(), g.cliente, ahora()
    dias = dias_reservables(cliente, momento)
    texto_dia = request.args.get("dia") or (reserva["dia"] if reserva else None)
    dia = leer_dia(texto_dia) if texto_dia else (dias[0] if dias else None)
    franjas = []
    if dia is not None:
        horas = calcular_franjas(cliente, dia, momento, sin_limite_antelacion=es_admin())
        dia_iso = dia.isoformat()
        ocupados = {
            (fila["espacio_id"], fila["hora_inicio"])
            for fila in conexion.execute(
                "SELECT espacio_id, hora_inicio FROM reserva WHERE dia = ? AND estado = 'vigente'", (dia_iso,)
            )
        }
        espacios = espacios_activos(conexion)
        for hora in horas:
            celdas = []
            for espacio in espacios:
                actual = (reserva is not None and reserva["espacio_id"] == espacio["id"]
                          and reserva["dia"] == dia_iso and reserva["hora_inicio"] == hora)
                celdas.append({
                    "espacio": espacio,
                    "actual": actual,
                    "ocupado": (espacio["id"], hora) in ocupados and not actual,
                    "url": url_elegir(espacio["id"], dia_iso, hora),
                })
            franjas.append({"hora": hora, "fin": hora_fin(cliente, hora), "celdas": celdas})
    return render_template(
        "calendario.html", titulo=titulo, dias=dias, dia=dia, franjas=franjas, url_dia=url_dia,
        reserva=reserva, para_usuario=para_usuario,
    )


def _leer_eleccion(valores):
    """Valida el día, la franja y el espacio elegidos. Devuelve la elección o None."""
    dia = leer_dia(valores.get("dia", ""))
    hora = valores.get("hora", "")
    espacio_id = valores.get("espacio", type=int)
    if dia is None or espacio_id is None:
        return None
    if hora not in calcular_franjas(g.cliente, dia, sin_limite_antelacion=es_admin()):
        return None
    espacio = get_db().execute(
        "SELECT e.id, e.nombre, p.nombre AS planta FROM espacio e LEFT JOIN planta p ON p.id = e.planta_id "
        "WHERE e.id = ? AND e.eliminado = 0",
        (espacio_id,),
    ).fetchone()
    if espacio is None:
        return None
    return {"dia": dia.isoformat(), "hora": hora, "fin": hora_fin(g.cliente, hora), "espacio": espacio}


def _ocupado(eleccion, excepto_id=None):
    return get_db().execute(
        "SELECT 1 FROM reserva WHERE espacio_id = ? AND dia = ? AND hora_inicio = ? "
        "AND estado = 'vigente' AND id IS NOT ?",
        (eleccion["espacio"]["id"], eleccion["dia"], eleccion["hora"], excepto_id),
    ).fetchone() is not None


def _reservar(destinatario, url_dia, url_accion):
    """Confirmar (GET) y guardar (POST) una reserva nueva para `destinatario`."""
    eleccion = _leer_eleccion(request.values)
    if eleccion is None:
        flash(MENSAJE_NO_DISPONIBLE, "error")
        return redirect(url_dia(request.values.get("dia")))
    if request.method == "GET":
        if _ocupado(eleccion):
            flash(MENSAJE_OCUPADO, "error")
            return redirect(url_dia(eleccion["dia"]))
        para_otro = None
        if destinatario["id"] != g.usuario["id"]:
            para_otro = quien(destinatario["nombre"], destinatario["apellidos"], destinatario["identificador"])
        return render_template(
            "confirmar.html", eleccion=eleccion, accion=url_accion, para_usuario=para_otro,
            boton="Confirmar reserva", url_volver=url_dia(eleccion["dia"]),
        )

    conexion = get_db()
    reserva_id, error = crear_reserva(
        conexion, destinatario["id"], eleccion["espacio"]["id"], eleccion["dia"], eleccion["hora"]
    )
    if error:
        flash(error, "error")
        return redirect(url_dia(eleccion["dia"]))
    if not enviar_reserva("creada", obtener_reserva(conexion, reserva_id), g.cliente):
        flash(AVISO_EMAIL, "info")
    return redirect(url_for("reservas.confirmada", reserva_id=reserva_id))


@bp.route("/calendario")
@rol_requerido("usuario", "administrador")
def calendario():
    return _pantalla_calendario(
        "Reservar",
        url_dia=lambda dia: url_for("reservas.calendario", dia=dia),
        url_elegir=lambda espacio, dia, hora: url_for("reservas.confirmar", espacio=espacio, dia=dia, hora=hora),
    )


@bp.route("/reservar", methods=["GET", "POST"])
@rol_requerido("usuario", "administrador")
def confirmar():
    return _reservar(
        g.usuario,
        url_dia=lambda dia: url_for("reservas.calendario", dia=dia),
        url_accion=url_for("reservas.confirmar"),
    )


@bp.route("/reservas/<int:reserva_id>")
@rol_requerido("usuario", "administrador")
def confirmada(reserva_id):
    reserva = _reserva_accesible(reserva_id)
    return render_template(
        "confirmacion.html", reserva=reserva, fin=hora_fin(g.cliente, reserva["hora_inicio"]),
        url_vuelta=_url_vuelta(reserva),
    )


@bp.route("/mis-reservas")
@rol_requerido("usuario", "administrador")
def mis_reservas():
    """Todo el historial del usuario, con estado (FR-034)."""
    momento = ahora()
    filas = get_db().execute(
        SQL_RESERVA + " WHERE r.usuario_id = ? ORDER BY r.dia DESC, r.hora_inicio DESC", (g.usuario["id"],)
    ).fetchall()
    reservas = [{
        "r": fila,
        "fin": hora_fin(g.cliente, fila["hora_inicio"]),
        "pasada": inicio_reserva(fila["dia"], fila["hora_inicio"]) <= momento,
        "motivo": puede_cambiar(fila, g.cliente, g.usuario, momento),
    } for fila in filas]
    return render_template("mis_reservas.html", reservas=reservas)


@bp.route("/reservas/<int:reserva_id>/modificar")
@rol_requerido("usuario", "administrador")
def modificar(reserva_id):
    reserva = _reserva_accesible(reserva_id)
    motivo = puede_cambiar(reserva, g.cliente, g.usuario)
    if motivo:
        flash(motivo, "error")
        return redirect(_url_vuelta(reserva))
    return _pantalla_calendario(
        f"Modificar la reserva {reserva['numero']}",
        url_dia=lambda dia: url_for("reservas.modificar", reserva_id=reserva_id, dia=dia),
        url_elegir=lambda espacio, dia, hora: url_for(
            "reservas.modificar_confirmar", reserva_id=reserva_id, espacio=espacio, dia=dia, hora=hora
        ),
        reserva=reserva, para_usuario=_para_quien(reserva),
    )


@bp.route("/reservas/<int:reserva_id>/modificar/confirmar", methods=["GET", "POST"])
@rol_requerido("usuario", "administrador")
def modificar_confirmar(reserva_id):
    reserva = _reserva_accesible(reserva_id)
    motivo = puede_cambiar(reserva, g.cliente, g.usuario)
    if motivo:
        flash(motivo, "error")
        return redirect(_url_vuelta(reserva))

    def url_dia(dia):
        return url_for("reservas.modificar", reserva_id=reserva_id, dia=dia)

    eleccion = _leer_eleccion(request.values)
    if eleccion is None:
        flash(MENSAJE_NO_DISPONIBLE, "error")
        return redirect(url_dia(request.values.get("dia")))
    if request.method == "GET":
        if _ocupado(eleccion, excepto_id=reserva_id):
            flash(MENSAJE_OCUPADO, "error")
            return redirect(url_dia(eleccion["dia"]))
        para_otro = _para_quien(reserva)
        return render_template(
            "confirmar.html", eleccion=eleccion, reserva=reserva, para_usuario=para_otro,
            fin_actual=hora_fin(g.cliente, reserva["hora_inicio"]),
            accion=url_for("reservas.modificar_confirmar", reserva_id=reserva_id),
            boton="Confirmar cambio", url_volver=url_dia(eleccion["dia"]),
        )

    conexion = get_db()
    error = modificar_reserva(
        conexion, reserva_id, eleccion["espacio"]["id"], eleccion["dia"], eleccion["hora"]
    )
    if error:
        flash(error, "error")
        return redirect(url_dia(eleccion["dia"]))
    flash(f"Reserva modificada. Conserva el número {reserva['numero']}.", "ok")
    if not enviar_reserva("modificada", obtener_reserva(conexion, reserva_id), g.cliente):
        flash(AVISO_EMAIL, "info")
    return redirect(_url_vuelta(reserva))


@bp.route("/reservas/<int:reserva_id>/cancelar", methods=["GET", "POST"])
@rol_requerido("usuario", "administrador")
def cancelar(reserva_id):
    """Cancelar (usuario) o eliminar (administrador, FR-024): la reserva queda como cancelada."""
    reserva = _reserva_accesible(reserva_id)
    motivo = puede_cambiar(reserva, g.cliente, g.usuario)
    if motivo:
        flash(motivo, "error")
        return redirect(_url_vuelta(reserva))
    if request.method == "GET":
        return render_template(
            "cancelar.html", reserva=reserva, fin=hora_fin(g.cliente, reserva["hora_inicio"]),
            url_vuelta=_url_vuelta(reserva), eliminar=reserva["usuario_id"] != g.usuario["id"],
        )
    conexion = get_db()
    if cancelar_reserva(conexion, reserva_id):
        flash(f"Reserva {reserva['numero']} cancelada. El espacio queda libre.", "ok")
        if not enviar_reserva("cancelada", obtener_reserva(conexion, reserva_id), g.cliente):
            flash(AVISO_EMAIL, "info")
    return redirect(_url_vuelta(reserva))


# --- El administrador reserva para cualquier usuario (FR-024) ---

def _usuario_para_reservar(usuario_id):
    usuario = get_db().execute(
        "SELECT * FROM usuario WHERE id = ? AND rol != 'consulta'", (usuario_id,)
    ).fetchone()
    if usuario is None:
        abort(404)
    return usuario


@bp.route("/admin/reservas/nueva")
@rol_requerido("administrador")
def admin_elegir_usuario():
    usuario_id = request.args.get("usuario", type=int)
    if usuario_id:
        return redirect(url_for("reservas.admin_calendario", usuario_id=usuario_id))
    usuarios = get_db().execute(
        "SELECT id, nombre, apellidos, identificador FROM usuario WHERE rol != 'consulta' "
        "ORDER BY apellidos, nombre, identificador"
    ).fetchall()
    return render_template("admin_reserva_form.html", usuarios=usuarios)


@bp.route("/admin/reservas/nueva/<int:usuario_id>")
@rol_requerido("administrador")
def admin_calendario(usuario_id):
    destinatario = _usuario_para_reservar(usuario_id)
    return _pantalla_calendario(
        "Nueva reserva para un usuario",
        url_dia=lambda dia: url_for("reservas.admin_calendario", usuario_id=usuario_id, dia=dia),
        url_elegir=lambda espacio, dia, hora: url_for(
            "reservas.admin_confirmar", usuario_id=usuario_id, espacio=espacio, dia=dia, hora=hora
        ),
        para_usuario=quien(destinatario["nombre"], destinatario["apellidos"], destinatario["identificador"]),
    )


@bp.route("/admin/reservas/nueva/<int:usuario_id>/confirmar", methods=["GET", "POST"])
@rol_requerido("administrador")
def admin_confirmar(usuario_id):
    destinatario = _usuario_para_reservar(usuario_id)
    return _reservar(
        destinatario,
        url_dia=lambda dia: url_for("reservas.admin_calendario", usuario_id=usuario_id, dia=dia),
        url_accion=url_for("reservas.admin_confirmar", usuario_id=usuario_id),
    )
