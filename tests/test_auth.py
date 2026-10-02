import re
from datetime import timedelta

import pytest

from app.auth import MENSAJE_ACCESO, MENSAJE_BLOQUEO, MENSAJE_CLAVE, comprobar_acceso, validar_clave
from app.fechas import ahora
from tests.conftest import configurar_cliente, crear_usuario, entrar


@pytest.mark.parametrize("clave", ["corta1", "solo-letras", "12345678", "admin"])
def test_contrasenas_que_no_cumplen(clave):
    assert validar_clave(clave) == MENSAJE_CLAVE


def test_contrasena_valida():
    assert validar_clave("reservas2026") is None


def test_primer_acceso_obliga_a_cambiar_y_admin_ya_no_sirve(cliente_http):
    respuesta = entrar(cliente_http, "admin", "admin")
    assert respuesta.headers["Location"].endswith("/cambiar-clave")
    # Ninguna otra pantalla responde hasta cambiarla (FR-002).
    assert cliente_http.get("/admin/cliente").headers["Location"].endswith("/cambiar-clave")
    respuesta = cliente_http.post("/cambiar-clave", data={"clave": "admin", "repetir": "admin"})
    assert MENSAJE_CLAVE in respuesta.get_data(as_text=True)
    cliente_http.post("/cambiar-clave", data={"clave": "nueva1234", "repetir": "nueva1234"})
    cliente_http.post("/salir")
    respuesta = entrar(cliente_http, "admin", "admin")
    assert MENSAJE_ACCESO in respuesta.get_data(as_text=True)
    assert entrar(cliente_http, "admin", "nueva1234").status_code == 302


def test_bloqueo_a_los_5_fallos_y_reinicio_al_acertar(app, bd):
    crear_usuario(bd, "ana@ejemplo.es", "clave1234")
    momento = ahora()
    with app.app_context():
        for _ in range(4):
            assert comprobar_acceso(bd, "ana@ejemplo.es", "mala", momento)[1] == MENSAJE_ACCESO
        # Un acierto reinicia la cuenta de fallos.
        assert comprobar_acceso(bd, "ana@ejemplo.es", "clave1234", momento)[0] is not None
        for _ in range(4):
            assert comprobar_acceso(bd, "ana@ejemplo.es", "mala", momento)[1] == MENSAJE_ACCESO
        assert comprobar_acceso(bd, "ana@ejemplo.es", "mala", momento)[1] == MENSAJE_BLOQUEO
        # Bloqueada aunque la contraseña sea correcta...
        assert comprobar_acceso(bd, "ana@ejemplo.es", "clave1234", momento)[1] == MENSAJE_BLOQUEO
        # ...hasta que pasan 15 minutos.
        despues = momento + timedelta(minutes=15, seconds=1)
        assert comprobar_acceso(bd, "ana@ejemplo.es", "clave1234", despues)[0] is not None


def test_mensaje_de_bloqueo_en_pantalla(cliente_http, bd):
    configurar_cliente(bd)
    crear_usuario(bd, "ana@ejemplo.es")
    for _ in range(4):
        entrar(cliente_http, "ana@ejemplo.es", "mala")
    respuesta = entrar(cliente_http, "ana@ejemplo.es", "mala")
    assert MENSAJE_BLOQUEO in respuesta.get_data(as_text=True)


def _pedir_enlace(cliente_http, correos, email):
    respuesta = cliente_http.post("/olvido", data={"email": email})
    assert f"Se ha enviado un email a {email}, compruebe su bandeja de entrada" in respuesta.get_data(as_text=True)
    return re.search(r"/nueva-clave/\S+", correos[-1]["cuerpo"]).group(0)


def test_enlace_de_recuperacion_de_un_solo_uso(cliente_http, bd, correos):
    configurar_cliente(bd)
    crear_usuario(bd, "ana@ejemplo.es")
    enlace = _pedir_enlace(cliente_http, correos, "ana@ejemplo.es")
    respuesta = cliente_http.post(enlace, data={"clave": "otra12345", "repetir": "otra12345"})
    assert respuesta.headers["Location"].endswith("/entrar")
    assert entrar(cliente_http, "ana@ejemplo.es", "otra12345").status_code == 302
    cliente_http.post("/salir")
    assert "ha caducado" in cliente_http.get(enlace).get_data(as_text=True)


def test_enlace_de_recuperacion_caduca_a_la_hora(cliente_http, bd, correos):
    configurar_cliente(bd)
    crear_usuario(bd, "ana@ejemplo.es")
    enlace = _pedir_enlace(cliente_http, correos, "ana@ejemplo.es")
    hace_un_rato = (ahora() - timedelta(seconds=1)).isoformat(timespec="seconds")
    bd.execute("UPDATE enlace_recuperacion SET caduca_en = ?", (hace_un_rato,))
    bd.commit()
    assert "ha caducado" in cliente_http.get(enlace).get_data(as_text=True)


def test_olvido_con_email_inexistente(cliente_http, bd, correos):
    configurar_cliente(bd)
    respuesta = cliente_http.post("/olvido", data={"email": "nadie@ejemplo.es"})
    assert "No existe ninguna cuenta con ese email" in respuesta.get_data(as_text=True)
    assert correos == []


def test_si_falla_el_email_de_recuperacion_el_enlace_se_anula(app, cliente_http, bd):
    configurar_cliente(bd)
    crear_usuario(bd, "ana@ejemplo.es")
    app.config["CORREO_FALLA"] = True
    respuesta = cliente_http.post("/olvido", data={"email": "ana@ejemplo.es"})
    assert "No se ha podido enviar el email, inténtelo de nuevo más tarde" in respuesta.get_data(as_text=True)
    assert bd.execute("SELECT usado FROM enlace_recuperacion").fetchone()[0] == 1


def test_registro_y_email_repetido(cliente_http, bd, correos):
    configurar_cliente(bd)
    datos = {"nombre": "Ana", "apellidos": "López", "email": "Ana@Ejemplo.es", "telefono": "600000000",
             "clave": "clave1234"}
    respuesta = cliente_http.post("/registro", data=datos)
    assert respuesta.headers["Location"].endswith("/calendario")
    assert correos[-1]["para"] == "ana@ejemplo.es"
    assert "clave1234" not in correos[-1]["cuerpo"]
    cliente_http.post("/salir")
    respuesta = cliente_http.post("/registro", data=datos)
    assert "Ya existe una cuenta con ese email" in respuesta.get_data(as_text=True)


def test_sin_configurar_no_se_puede_registrar(cliente_http):
    assert "Reservas aún no disponibles" in cliente_http.get("/registro").get_data(as_text=True)
    assert "Reservas aún no disponibles" in cliente_http.get("/").get_data(as_text=True)


def test_formulario_sin_token_csrf_se_rechaza(app, cliente_http):
    app.config["CSRF_ACTIVO"] = True
    assert cliente_http.post("/entrar", data={"identificador": "admin", "clave": "admin"}).status_code == 400
