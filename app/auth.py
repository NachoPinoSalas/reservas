"""Acceso, cambio obligatorio de contraseña, registro, bloqueo y recuperación de contraseña."""
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import login_required
from app.correo import enviar_recuperacion, enviar_registro
from app.db import get_db
from app.fechas import ahora

bp = Blueprint("auth", __name__)

MENSAJE_CLAVE = "La contraseña debe tener al menos 8 caracteres, una letra y un número"
MENSAJE_ACCESO = "Email o contraseña incorrectos"
MENSAJE_BLOQUEO = "Demasiados intentos, vuelva a probar en 15 minutos"
MENSAJE_EMAIL_REPETIDO = "Ya existe una cuenta con ese email"
MAX_FALLOS = 5
MINUTOS_BLOQUEO = 15
HORAS_ENLACE = 1


def validar_clave(clave):
    """Regla de FR-031. Devuelve el mensaje de error o None."""
    if len(clave) < 8 or not any(c.isalpha() for c in clave) or not any(c.isdigit() for c in clave):
        return MENSAJE_CLAVE
    return None


def normalizar_email(texto):
    return (texto or "").strip().lower()


def es_email(texto):
    usuario, arroba, dominio = texto.partition("@")
    return bool(usuario) and arroba == "@" and "." in dominio and " " not in texto


def huella(token):
    return hashlib.sha256(token.encode()).hexdigest()


def iniciar_sesion(usuario):
    session.clear()
    session["usuario_id"] = usuario["id"]


def comprobar_acceso(conexion, identificador, clave, momento=None):
    """Comprueba la contraseña aplicando el bloqueo de FR-032.

    Devuelve (usuario, None) si es correcta, o (None, mensaje) si no.
    """
    momento = momento or ahora()
    usuario = conexion.execute(
        "SELECT * FROM usuario WHERE identificador = ?", (normalizar_email(identificador),)
    ).fetchone()
    if usuario is None:
        return None, MENSAJE_ACCESO
    if usuario["bloqueado_hasta"] and datetime.fromisoformat(usuario["bloqueado_hasta"]) > momento:
        return None, MENSAJE_BLOQUEO
    if check_password_hash(usuario["clave_cifrada"], clave):
        conexion.execute(
            "UPDATE usuario SET fallos_acceso = 0, bloqueado_hasta = NULL WHERE id = ?", (usuario["id"],)
        )
        conexion.commit()
        return usuario, None
    fallos = usuario["fallos_acceso"] + 1
    if fallos >= MAX_FALLOS:
        hasta = (momento + timedelta(minutes=MINUTOS_BLOQUEO)).isoformat(timespec="seconds")
        conexion.execute(
            "UPDATE usuario SET fallos_acceso = 0, bloqueado_hasta = ? WHERE id = ?", (hasta, usuario["id"])
        )
        conexion.commit()
        return None, MENSAJE_BLOQUEO
    conexion.execute("UPDATE usuario SET fallos_acceso = ? WHERE id = ?", (fallos, usuario["id"]))
    conexion.commit()
    return None, MENSAJE_ACCESO


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if g.usuario is not None:
        return redirect(url_for("index"))
    error = None
    identificador = ""
    if request.method == "POST":
        identificador = request.form.get("identificador", "")
        usuario, error = comprobar_acceso(get_db(), identificador, request.form.get("clave", ""))
        if usuario is not None:
            iniciar_sesion(usuario)
            if usuario["debe_cambiar_clave"]:
                return redirect(url_for("auth.cambiar_clave_obligatoria"))
            return redirect(url_for("index"))
    return render_template("entrar.html", error=error, identificador=identificador)


@bp.route("/salir", methods=["POST"])
def salir():
    session.clear()
    return redirect(url_for("index"))


@bp.route("/cambiar-clave", methods=["GET", "POST"])
@login_required
def cambiar_clave_obligatoria():
    """Primer acceso con admin/admin: hay que elegir contraseña antes de nada (FR-002)."""
    if not g.usuario["debe_cambiar_clave"]:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        clave = request.form.get("clave", "")
        error = validar_clave(clave)
        if error is None and clave != request.form.get("repetir", ""):
            error = "Las dos contraseñas no coinciden."
        if error is None:
            conexion = get_db()
            conexion.execute(
                "UPDATE usuario SET clave_cifrada = ?, debe_cambiar_clave = 0 WHERE id = ?",
                (generate_password_hash(clave), g.usuario["id"]),
            )
            conexion.commit()
            flash("Contraseña cambiada. Complete ahora sus datos.", "ok")
            return redirect(url_for("usuarios.perfil"))
    return render_template("cambiar_clave_obligatoria.html", error=error)


CAMPOS_REGISTRO = ("nombre", "apellidos", "nif", "email", "telefono")


def leer_datos_personales(form):
    """Lee y valida nombre, apellidos, NIF (opcional), email y teléfono. Devuelve (datos, errores)."""
    datos = {campo: (form.get(campo) or "").strip() for campo in CAMPOS_REGISTRO}
    datos["email"] = normalizar_email(datos["email"])
    errores = []
    for campo, texto in (("nombre", "el nombre"), ("apellidos", "los apellidos"), ("telefono", "el teléfono")):
        if not datos[campo]:
            errores.append(f"Indique {texto}.")
    if not es_email(datos["email"]):
        errores.append("Indique un email válido.")
    return datos, errores


def email_en_uso(conexion, email, excepto_id=None):
    return conexion.execute(
        "SELECT 1 FROM usuario WHERE identificador = ? AND id IS NOT ?", (email, excepto_id)
    ).fetchone() is not None


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Registro de visitantes con rol usuario (FR-008, FR-009, FR-010)."""
    if g.usuario is not None:
        return redirect(url_for("index"))
    datos, errores = {}, []
    if request.method == "POST":
        conexion = get_db()
        datos, errores = leer_datos_personales(request.form)
        clave = request.form.get("clave", "")
        error_clave = validar_clave(clave)
        if error_clave:
            errores.append(error_clave)
        if not errores and email_en_uso(conexion, datos["email"]):
            errores.append(MENSAJE_EMAIL_REPETIDO)
        if not errores:
            cursor = conexion.execute(
                "INSERT INTO usuario (identificador, nombre, apellidos, nif, telefono, clave_cifrada, rol) "
                "VALUES (?, ?, ?, ?, ?, ?, 'usuario')",
                (datos["email"], datos["nombre"], datos["apellidos"], datos["nif"], datos["telefono"],
                 generate_password_hash(clave)),
            )
            conexion.commit()
            usuario = conexion.execute("SELECT * FROM usuario WHERE id = ?", (cursor.lastrowid,)).fetchone()
            iniciar_sesion(usuario)
            flash("Su cuenta está creada. Ya puede reservar.", "ok")
            if not enviar_registro(usuario, g.cliente["nombre"]):
                flash("No se ha podido enviar el email con el resumen del registro, pero su cuenta está creada.", "info")
            return redirect(url_for("reservas.calendario"))
    return render_template("registro.html", datos=datos, errores=errores)


@bp.route("/olvido", methods=["GET", "POST"])
def olvido():
    """«¿Olvidó su contraseña?»: enlace de un solo uso válido 1 hora (FR-011)."""
    error = enviado = None
    email = ""
    if request.method == "POST":
        conexion = get_db()
        email = normalizar_email(request.form.get("email"))
        usuario = conexion.execute("SELECT * FROM usuario WHERE identificador = ?", (email,)).fetchone()
        if usuario is None or not es_email(email):
            error = "No existe ninguna cuenta con ese email"
        else:
            token = secrets.token_urlsafe(32)
            caduca = (ahora() + timedelta(hours=HORAS_ENLACE)).isoformat(timespec="seconds")
            cursor = conexion.execute(
                "INSERT INTO enlace_recuperacion (usuario_id, huella, caduca_en) VALUES (?, ?, ?)",
                (usuario["id"], huella(token), caduca),
            )
            conexion.commit()
            enlace = url_for("auth.nueva_clave", token=token, _external=True)
            if enviar_recuperacion(email, enlace, g.cliente["nombre"] or "Reservas"):
                enviado = email
            else:
                conexion.execute("UPDATE enlace_recuperacion SET usado = 1 WHERE id = ?", (cursor.lastrowid,))
                conexion.commit()
                error = "No se ha podido enviar el email, inténtelo de nuevo más tarde"
    return render_template("olvido.html", error=error, enviado=enviado, email=email)


def enlace_valido(conexion, token, momento=None):
    momento = momento or ahora()
    enlace = conexion.execute(
        "SELECT * FROM enlace_recuperacion WHERE huella = ?", (huella(token),)
    ).fetchone()
    if enlace is None or enlace["usado"] or datetime.fromisoformat(enlace["caduca_en"]) <= momento:
        return None
    return enlace


@bp.route("/nueva-clave/<token>", methods=["GET", "POST"])
def nueva_clave(token):
    conexion = get_db()
    enlace = enlace_valido(conexion, token)
    if enlace is None:
        return render_template("nueva_clave.html", caducado=True)
    error = None
    if request.method == "POST":
        clave = request.form.get("clave", "")
        error = validar_clave(clave)
        if error is None and clave != request.form.get("repetir", ""):
            error = "Las dos contraseñas no coinciden."
        if error is None:
            conexion.execute(
                "UPDATE usuario SET clave_cifrada = ?, debe_cambiar_clave = 0 WHERE id = ?",
                (generate_password_hash(clave), enlace["usuario_id"]),
            )
            conexion.execute("UPDATE enlace_recuperacion SET usado = 1 WHERE id = ?", (enlace["id"],))
            conexion.commit()
            session.clear()
            flash("Contraseña cambiada. Ya puede entrar con la nueva.", "ok")
            return redirect(url_for("auth.entrar"))
    return render_template("nueva_clave.html", caducado=False, error=error)
