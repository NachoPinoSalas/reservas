"""Aplicación Reservas: creación, seguridad común y acceso por rol."""
import os
import secrets
from functools import wraps

from flask import Flask, Response, abort, g, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from app import db, fechas

# Pantallas que se pueden usar aunque el cliente aún no esté configurado (FR-006).
LIBRES_SIN_CONFIGURAR = {
    "index", "logo", "static", "auth.entrar", "auth.salir", "auth.cambiar_clave_obligatoria",
    "auth.olvido", "auth.nueva_clave",
}
MENSAJES_ERROR = {
    400: "La petición no es válida. Vuelva a la página anterior e inténtelo de nuevo.",
    403: "No tiene permiso para ver esta página.",
    404: "No se ha encontrado la página.",
    405: "Esta acción no está permitida.",
    413: "El fichero es demasiado grande.",
    500: "Ha ocurrido un error inesperado. Inténtelo de nuevo más tarde.",
}


def es_admin(usuario=None):
    usuario = usuario if usuario is not None else g.get("usuario")
    return usuario is not None and usuario["rol"] == "administrador"


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("auth.entrar"))
        return vista(*args, **kwargs)
    return envoltura


def rol_requerido(*roles):
    """Comprueba el rol en el servidor, no solo ocultando opciones del menú (FR-015, FR-027)."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("auth.entrar"))
            if g.usuario["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        RESERVAS_DB=os.environ.get("RESERVAS_DB") or os.path.join(app.instance_path, "reservas.db"),
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURA", "1") != "0",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        CORREO_MODO=os.environ.get("CORREO_MODO", "smtp"),
        CSRF_ACTIVO=True,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Falta la variable de entorno SECRET_KEY (clave de sesión).")

    # El alojamiento da HTTPS delante de la aplicación: así los enlaces de los emails salen con https.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    carpeta_bd = os.path.dirname(os.path.abspath(app.config["RESERVAS_DB"]))
    os.makedirs(carpeta_bd, exist_ok=True)
    db.inicializar(app.config["RESERVAS_DB"])
    app.teardown_appcontext(db.cerrar_db)

    app.jinja_env.filters["fecha"] = fechas.fecha_es
    app.jinja_env.filters["dia_semana"] = fechas.dia_semana
    app.jinja_env.filters["mes"] = fechas.mes_es

    @app.context_processor
    def contexto():
        return {
            "cliente": g.get("cliente"),
            "usuario_actual": g.get("usuario"),
            "es_admin": es_admin(),
            "csrf_token": csrf_token,
            "DIAS_LETRA": fechas.DIAS_LETRA,
        }

    @app.before_request
    def antes_de_cada_peticion():
        conexion = db.get_db()
        g.cliente = conexion.execute("SELECT * FROM cliente WHERE id = 1").fetchone()
        g.usuario = None
        if "usuario_id" in session:
            g.usuario = conexion.execute(
                "SELECT * FROM usuario WHERE id = ?", (session["usuario_id"],)
            ).fetchone()
            if g.usuario is None:
                session.clear()

        if request.method == "POST" and app.config["CSRF_ACTIVO"]:
            enviado = request.form.get("_csrf", "")
            guardado = session.get("_csrf", "")
            if not guardado or not secrets.compare_digest(guardado, enviado):
                abort(400)

        endpoint = request.endpoint or ""
        if endpoint in ("static", "logo"):
            return None
        # Primer acceso de admin: ninguna otra pantalla responde hasta cambiar la contraseña (FR-002).
        if g.usuario is not None and g.usuario["debe_cambiar_clave"] and endpoint not in (
            "auth.cambiar_clave_obligatoria", "auth.salir"
        ):
            return redirect(url_for("auth.cambiar_clave_obligatoria"))
        if not g.cliente["configurado"] and not es_admin() and endpoint not in LIBRES_SIN_CONFIGURAR:
            return render_template("no_disponible.html")
        return None

    @app.route("/")
    def index():
        if not g.cliente["configurado"]:
            if es_admin():
                return redirect(url_for("cliente.datos"))
            return render_template("no_disponible.html")
        if g.usuario is None:
            return redirect(url_for("auth.entrar"))
        if g.usuario["rol"] == "consulta":
            return redirect(url_for("consulta.lista"))
        return redirect(url_for("reservas.calendario"))

    @app.route("/logo")
    def logo():
        """Logo del cliente guardado en la base de datos (FR-007)."""
        if not g.cliente["logo"]:
            abort(404)
        return Response(
            g.cliente["logo"], mimetype=g.cliente["logo_tipo"], headers={"Cache-Control": "no-cache"}
        )

    def pagina_error(error):
        codigo = getattr(error, "code", 500) or 500
        mensaje = MENSAJES_ERROR.get(codigo, MENSAJES_ERROR[500])
        return render_template("error.html", mensaje=mensaje), codigo

    for codigo in MENSAJES_ERROR:
        app.register_error_handler(codigo, pagina_error)

    from app import auth, cliente, consulta, reservas, usuarios

    app.register_blueprint(auth.bp)
    app.register_blueprint(cliente.bp)
    app.register_blueprint(reservas.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(consulta.bp)
    return app
