"""Mi perfil y gestión de usuarios y roles por el administrador."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app import login_required, rol_requerido
from app.auth import MENSAJE_EMAIL_REPETIDO, email_en_uso, leer_datos_personales, validar_clave
from app.db import get_db

bp = Blueprint("usuarios", __name__)

ROLES = {"administrador": "Administrador", "usuario": "Usuario", "consulta": "Consulta"}
MENSAJE_ULTIMO_ADMIN = "No se puede quitar el rol de administrador al último administrador."


def _datos_de(usuario):
    return {
        "nombre": usuario["nombre"], "apellidos": usuario["apellidos"], "nif": usuario["nif"],
        "email": usuario["identificador"] if usuario["identificador"] != "admin" else "",
        "telefono": usuario["telefono"], "rol": usuario["rol"],
    }


def _guardar_datos(conexion, usuario_id, datos):
    # El email es también el identificador de acceso (FR-013).
    conexion.execute(
        "UPDATE usuario SET identificador = ?, nombre = ?, apellidos = ?, nif = ?, telefono = ? WHERE id = ?",
        (datos["email"], datos["nombre"], datos["apellidos"], datos["nif"], datos["telefono"], usuario_id),
    )


def quedaria_sin_admin(conexion, usuario, rol_nuevo):
    """FR-016: siempre debe quedar al menos un administrador."""
    if usuario["rol"] != "administrador" or rol_nuevo == "administrador":
        return False
    admins = conexion.execute("SELECT COUNT(*) FROM usuario WHERE rol = 'administrador'").fetchone()[0]
    return admins <= 1


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    """Ver y editar nombre, apellidos, NIF, email y teléfono (FR-012)."""
    conexion = get_db()
    datos, errores = _datos_de(g.usuario), []
    if request.method == "POST":
        datos, errores = leer_datos_personales(request.form)
        if not errores and email_en_uso(conexion, datos["email"], excepto_id=g.usuario["id"]):
            errores.append(MENSAJE_EMAIL_REPETIDO)
        if not errores:
            _guardar_datos(conexion, g.usuario["id"], datos)
            conexion.commit()
            flash("Datos guardados.", "ok")
            if g.usuario["rol"] == "administrador" and not g.cliente["configurado"]:
                return redirect(url_for("cliente.datos"))
            return redirect(url_for("usuarios.perfil"))
    return render_template("perfil.html", datos=datos, errores=errores)


@bp.route("/admin/usuarios")
@rol_requerido("administrador")
def lista():
    usuarios = get_db().execute(
        "SELECT * FROM usuario ORDER BY apellidos, nombre, identificador"
    ).fetchall()
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES)


@bp.route("/admin/usuarios/nuevo", methods=["GET", "POST"])
@rol_requerido("administrador")
def nuevo():
    """Alta manual con cualquier rol (FR-015); la contraseña cumple FR-031."""
    datos, errores = {"rol": "usuario"}, []
    if request.method == "POST":
        conexion = get_db()
        datos, errores = leer_datos_personales(request.form)
        datos["rol"] = request.form.get("rol", "")
        if datos["rol"] not in ROLES:
            errores.append("Elija un rol.")
        clave = request.form.get("clave", "")
        error_clave = validar_clave(clave)
        if error_clave:
            errores.append(error_clave)
        if not errores and email_en_uso(conexion, datos["email"]):
            errores.append(MENSAJE_EMAIL_REPETIDO)
        if not errores:
            conexion.execute(
                "INSERT INTO usuario (identificador, nombre, apellidos, nif, telefono, clave_cifrada, rol) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datos["email"], datos["nombre"], datos["apellidos"], datos["nif"], datos["telefono"],
                 generate_password_hash(clave), datos["rol"]),
            )
            conexion.commit()
            flash(f"Usuario {datos['email']} creado con rol {ROLES[datos['rol']].lower()}.", "ok")
            return redirect(url_for("usuarios.lista"))
    return render_template("usuario_form.html", datos=datos, errores=errores, roles=ROLES, nuevo=True)


@bp.route("/admin/usuarios/<int:usuario_id>", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar(usuario_id):
    """Editar datos y cambiar el rol. No hay borrado de usuarios en la v0."""
    conexion = get_db()
    usuario = conexion.execute("SELECT * FROM usuario WHERE id = ?", (usuario_id,)).fetchone()
    if usuario is None:
        abort(404)
    datos, errores = _datos_de(usuario), []
    if request.method == "POST":
        datos, errores = leer_datos_personales(request.form)
        datos["rol"] = request.form.get("rol", "")
        if datos["rol"] not in ROLES:
            errores.append("Elija un rol.")
        elif quedaria_sin_admin(conexion, usuario, datos["rol"]):
            errores.append(MENSAJE_ULTIMO_ADMIN)
        if not errores and email_en_uso(conexion, datos["email"], excepto_id=usuario_id):
            errores.append(MENSAJE_EMAIL_REPETIDO)
        if not errores:
            _guardar_datos(conexion, usuario_id, datos)
            conexion.execute("UPDATE usuario SET rol = ? WHERE id = ?", (datos["rol"], usuario_id))
            conexion.commit()
            flash("Usuario guardado.", "ok")
            if usuario_id == g.usuario["id"] and datos["rol"] != "administrador":
                return redirect(url_for("index"))
            return redirect(url_for("usuarios.lista"))
    return render_template(
        "usuario_form.html", datos=datos, errores=errores, roles=ROLES, nuevo=False, usuario=usuario
    )
