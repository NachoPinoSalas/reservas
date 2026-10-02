"""Envío de emails por SMTP estándar y textos de los emails (en español).

Si un envío falla, la función devuelve False y la acción que lo pidió sigue adelante
(spec, caso límite "Fallo al enviar un email").
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

from app.fechas import a_minutos, de_minutos, fecha_es

FIRMA = "\n\nEste es un mensaje automático; no responda a este email."


def enviar(destino, asunto, cuerpo):
    """Envía un email. Devuelve True si se ha enviado y False si no."""
    if not destino or "@" not in destino:
        return False
    modo = current_app.config["CORREO_MODO"]
    if modo == "memoria":  # pruebas automáticas
        if current_app.config.get("CORREO_FALLA"):
            return False
        current_app.extensions.setdefault("correos", []).append(
            {"para": destino, "asunto": asunto, "cuerpo": cuerpo}
        )
        return True
    if modo == "consola":  # pruebas locales sin servicio de correo
        current_app.logger.warning("EMAIL para %s | %s\n%s", destino, asunto, cuerpo)
        return True

    servidor = os.environ.get("SMTP_SERVIDOR")
    if not servidor:
        current_app.logger.error("No se ha configurado SMTP_SERVIDOR: no se envía el email.")
        return False
    puerto = int(os.environ.get("SMTP_PUERTO", "587"))
    usuario = os.environ.get("SMTP_USUARIO")
    clave = os.environ.get("SMTP_CLAVE")

    mensaje = EmailMessage()
    mensaje["From"] = os.environ.get("SMTP_REMITENTE") or usuario
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo + FIRMA)
    try:
        contexto = ssl.create_default_context()
        if puerto == 465:
            conexion = smtplib.SMTP_SSL(servidor, puerto, context=contexto, timeout=15)
        else:
            conexion = smtplib.SMTP(servidor, puerto, timeout=15)
            if os.environ.get("SMTP_TLS", "1") != "0":
                conexion.starttls(context=contexto)
        with conexion:
            if usuario:
                conexion.login(usuario, clave or "")
            conexion.send_message(mensaje)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("No se ha podido enviar el email a %s", destino)
        return False


def enviar_registro(usuario, nombre_cliente):
    """Resumen de los datos registrados, sin la contraseña (FR-009)."""
    cuerpo = (
        f"Hola, {usuario['nombre']}:\n\n"
        f"Se ha creado su cuenta en las reservas de {nombre_cliente}. Estos son sus datos:\n\n"
        f"Nombre: {usuario['nombre']}\n"
        f"Apellidos: {usuario['apellidos']}\n"
        f"NIF: {usuario['nif'] or '(no indicado)'}\n"
        f"Email: {usuario['identificador']}\n"
        f"Teléfono: {usuario['telefono']}\n\n"
        "Para entrar, use su email y la contraseña que eligió."
    )
    return enviar(usuario["identificador"], f"Registro en {nombre_cliente}", cuerpo)


def enviar_recuperacion(email, enlace, nombre_cliente):
    """Enlace de un solo uso, válido 1 hora (FR-011)."""
    cuerpo = (
        "Hola:\n\n"
        f"Hemos recibido una petición para cambiar la contraseña de su cuenta en {nombre_cliente}.\n"
        "Abra este enlace para elegir una contraseña nueva (sirve una sola vez y caduca en 1 hora):\n\n"
        f"{enlace}\n\n"
        "Si no lo ha pedido usted, ignore este email: su contraseña no cambia."
    )
    return enviar(email, "Cambio de contraseña", cuerpo)


ASUNTOS_RESERVA = {
    "creada": "Reserva confirmada",
    "modificada": "Reserva modificada",
    "cancelada": "Reserva cancelada",
}


def enviar_reserva(tipo, reserva, cliente, motivo=None):
    """Email de reserva creada, modificada o cancelada (FR-023, FR-033).

    `reserva` debe traer: numero, dia, hora_inicio, espacio, planta, nombre y email del usuario.
    """
    fin = de_minutos(a_minutos(reserva["hora_inicio"]) + cliente["duracion_min"])
    textos = {
        "creada": "Su reserva está confirmada.",
        "modificada": "Su reserva se ha modificado. Estos son los datos actualizados.",
        "cancelada": "Su reserva se ha cancelado.",
    }
    cuerpo = f"Hola, {reserva['u_nombre'] or reserva['u_email']}:\n\n{textos[tipo]}\n"
    if motivo:
        cuerpo += f"\nMotivo: {motivo}\n"
    cuerpo += (
        f"\nNúmero de reserva: {reserva['numero']}\n"
        f"Cliente: {cliente['nombre']}\n"
        f"Espacio: {reserva['espacio']}\n"
        f"Planta: {reserva['planta'] or '(sin planta)'}\n"
        f"Día: {fecha_es(reserva['dia'])}\n"
        f"Hora: de {reserva['hora_inicio']} a {fin}\n"
    )
    asunto = f"{ASUNTOS_RESERVA[tipo]} {reserva['numero']} – {cliente['nombre']}"
    return enviar(reserva["u_email"], asunto, cuerpo)
