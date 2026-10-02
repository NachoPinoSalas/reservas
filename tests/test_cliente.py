from datetime import timedelta

from app.cliente import aplicar_horario, reservas_que_no_encajan, validar_configuracion
from app.fechas import ahora
from app.reservas import crear_reserva
from tests.conftest import configurar_cliente, crear_espacio, crear_usuario, entrar

VALIDA = {"nombre": "Pádel Centro", "dias": "0,1,2,3,4", "apertura": "10:00", "cierre": "20:00",
          "duracion_min": 120, "antelacion_max_dias": 30, "cancelacion_min_horas": 24}


def test_configuracion_valida():
    assert validar_configuracion(VALIDA) == []


def test_duracion_multiplo_de_15():
    assert any("múltiplo de 15" in e for e in validar_configuracion({**VALIDA, "duracion_min": 50}))


def test_duracion_que_no_cabe_en_el_horario():
    errores = validar_configuracion({**VALIDA, "apertura": "10:00", "cierre": "11:00", "duracion_min": 120})
    assert any("no cabe" in e for e in errores)


def test_cierre_posterior_a_apertura_y_al_menos_un_dia():
    errores = validar_configuracion({**VALIDA, "apertura": "20:00", "cierre": "10:00", "dias": ""})
    assert "La hora de cierre debe ser posterior a la de apertura." in errores
    assert "Elija al menos un día de reserva." in errores


def _como_admin(cliente_http, bd):
    crear_usuario(bd, "jefa@ejemplo.es", rol="administrador")
    entrar(cliente_http, "jefa@ejemplo.es", "clave1234")


def test_asistente_completo(cliente_http, bd):
    _como_admin(cliente_http, bd)
    datos = {**VALIDA, "dias": ["0", "1", "2", "3", "4", "5", "6"]}
    assert cliente_http.post("/admin/cliente", data=datos).headers["Location"].endswith("/admin/espacios")
    cliente_http.post("/admin/plantas", data={"nombre": "Planta 1"})
    assert "Ya existe una planta" in cliente_http.post(
        "/admin/plantas", data={"nombre": "planta 1"}, follow_redirects=True).get_data(as_text=True)
    cliente_http.post("/admin/espacios/nuevo", data={"nombre": "Pista 1", "planta_id": "1"})
    cliente_http.post("/admin/espacios/nuevo", data={"nombre": "Pista 2", "planta_id": ""})
    cliente_http.post("/admin/terminar")
    assert bd.execute("SELECT configurado FROM cliente").fetchone()[0] == 1
    pagina = cliente_http.get(f"/calendario?dia={(ahora().date() + timedelta(days=1)).isoformat()}")
    texto = pagina.get_data(as_text=True)
    assert "Pista 1" in texto and "Planta 1" in texto and "18:00 – 20:00" in texto


def test_logo_se_guarda_y_se_ve(cliente_http, bd):
    _como_admin(cliente_http, bd)
    from io import BytesIO
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    cliente_http.post("/admin/cliente", data={**VALIDA, "dias": ["0"], "logo": (BytesIO(png), "logo.png")},
                      content_type="multipart/form-data")
    assert cliente_http.get("/logo").data == png
    assert 'class="logo"' in cliente_http.get("/admin/cliente").get_data(as_text=True)


def test_logo_que_no_es_imagen_se_rechaza(cliente_http, bd):
    _como_admin(cliente_http, bd)
    from io import BytesIO
    respuesta = cliente_http.post(
        "/admin/cliente", data={**VALIDA, "dias": ["0"], "logo": (BytesIO(b"hola"), "logo.png")},
        content_type="multipart/form-data")
    assert "El logo debe ser una imagen PNG o JPG." in respuesta.get_data(as_text=True)


def test_cambio_de_configuracion_cancela_solo_las_que_no_encajan(app, bd):
    configurar_cliente(bd)  # 10:00–20:00 en franjas de 2 h, todos los días
    pista = crear_espacio(bd, "Pista 1")
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    dia = (ahora().date() + timedelta(days=3)).isoformat()
    encaja, _ = crear_reserva(bd, usuario, pista, dia, "10:00")
    no_encaja, _ = crear_reserva(bd, usuario, pista, dia, "12:00")
    nuevo = {**dict(bd.execute("SELECT * FROM cliente").fetchone()), "duracion_min": 180}  # 10, 13, 16
    assert [r["id"] for r in reservas_que_no_encajan(bd, nuevo)] == [no_encaja]
    canceladas = aplicar_horario(bd, nuevo)
    assert [r["id"] for r in canceladas] == [no_encaja]
    estados = dict(bd.execute("SELECT id, estado FROM reserva").fetchall())
    assert estados == {encaja: "vigente", no_encaja: "cancelada"}
    # El espacio que ocupaba queda libre.
    assert crear_reserva(bd, usuario, pista, dia, "12:00")[1] is None


def test_cambio_de_configuracion_pide_confirmar_y_avisa(cliente_http, bd, correos):
    configurar_cliente(bd)
    pista = crear_espacio(bd, "Pista 1")
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    dia = (ahora().date() + timedelta(days=3)).isoformat()
    crear_reserva(bd, usuario, pista, dia, "12:00")
    _como_admin(cliente_http, bd)
    datos = {**VALIDA, "dias": ["0", "1", "2", "3", "4", "5", "6"], "duracion_min": 180}
    pagina = cliente_http.post("/admin/cliente", data=datos).get_data(as_text=True)
    assert "1 reservas futuras" in pagina
    assert bd.execute("SELECT duracion_min FROM cliente").fetchone()[0] == 120  # aún sin cambiar
    cliente_http.post("/admin/cliente/confirmar-horario", data=datos)
    assert bd.execute("SELECT duracion_min FROM cliente").fetchone()[0] == 180
    assert bd.execute("SELECT estado FROM reserva").fetchone()[0] == "cancelada"
    assert correos[-1]["para"] == "ana@ejemplo.es" and "Motivo" in correos[-1]["cuerpo"]


def test_no_se_borra_espacio_ni_planta_con_reservas_futuras(cliente_http, bd):
    configurar_cliente(bd)
    planta = bd.execute("INSERT INTO planta (nombre) VALUES ('Terraza')").lastrowid
    bd.commit()
    pista = crear_espacio(bd, "Mesa 4", planta)
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    dia = (ahora().date() + timedelta(days=3)).isoformat()
    crear_reserva(bd, usuario, pista, dia, "10:00")
    crear_reserva(bd, usuario, pista, dia, "12:00")
    _como_admin(cliente_http, bd)
    texto = cliente_http.post(f"/admin/espacios/{pista}/eliminar", follow_redirects=True).get_data(as_text=True)
    assert "tiene 2 reservas futuras" in texto
    texto = cliente_http.post(f"/admin/plantas/{planta}/eliminar", follow_redirects=True).get_data(as_text=True)
    assert "tienen 2 reservas futuras" in texto
    assert bd.execute("SELECT eliminado FROM espacio").fetchone()[0] == 0
    assert bd.execute("SELECT COUNT(*) FROM planta").fetchone()[0] == 1


def test_ultimo_administrador_no_pierde_el_rol(cliente_http, bd):
    configurar_cliente(bd)
    bd.execute("UPDATE usuario SET debe_cambiar_clave = 0, identificador = 'jefa@ejemplo.es'")
    bd.commit()
    from werkzeug.security import generate_password_hash
    bd.execute("UPDATE usuario SET clave_cifrada = ?", (generate_password_hash("clave1234"),))
    bd.commit()
    entrar(cliente_http, "jefa@ejemplo.es", "clave1234")
    datos = {"nombre": "Jefa", "apellidos": "Pérez", "email": "jefa@ejemplo.es", "telefono": "600",
             "rol": "usuario"}
    texto = cliente_http.post("/admin/usuarios/1", data=datos).get_data(as_text=True)
    assert "último administrador" in texto
    assert bd.execute("SELECT rol FROM usuario WHERE id = 1").fetchone()[0] == "administrador"


def test_admin_crea_usuario_de_consulta_y_solo_consulta(cliente_http, bd):
    configurar_cliente(bd)
    _como_admin(cliente_http, bd)
    datos = {"nombre": "Pepe", "apellidos": "Ruiz", "email": "pepe@ejemplo.es", "telefono": "600",
             "rol": "consulta", "clave": "clave1234"}
    cliente_http.post("/admin/usuarios/nuevo", data=datos)
    cliente_http.post("/salir")
    entrar(cliente_http, "pepe@ejemplo.es", "clave1234")
    assert cliente_http.get("/").headers["Location"].endswith("/consulta")
    assert cliente_http.get("/admin/usuarios").status_code == 403
    assert cliente_http.get("/admin/cliente").status_code == 403
