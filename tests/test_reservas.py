import threading
from datetime import timedelta

from app.db import conectar
from app.fechas import ahora
from app.reservas import MENSAJE_OCUPADO, cancelar_reserva, crear_reserva
from tests.conftest import configurar_cliente, crear_espacio, crear_usuario, entrar


def test_numero_de_reserva_y_contador_anual(bd):
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    pista1, pista2 = crear_espacio(bd, "Pista 1"), crear_espacio(bd, "Pista 2")
    primera, _ = crear_reserva(bd, usuario, pista1, "2026-10-15", "10:00")
    segunda, _ = crear_reserva(bd, usuario, pista2, "2026-10-16", "10:00")
    # La primera reserva con fecha de 2027 empieza en 0001, aunque se haga en 2026.
    de_2027, _ = crear_reserva(bd, usuario, pista1, "2027-01-04", "12:00")
    numeros = [bd.execute("SELECT numero FROM reserva WHERE id = ?", (i,)).fetchone()[0]
               for i in (primera, segunda, de_2027)]
    assert numeros == ["15-10-2026-0001", "16-10-2026-0002", "04-01-2027-0001"]


def test_numero_no_se_reutiliza_tras_cancelar(bd):
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    pista = crear_espacio(bd, "Pista 1")
    primera, _ = crear_reserva(bd, usuario, pista, "2026-10-15", "10:00")
    assert cancelar_reserva(bd, primera)
    # El hueco queda libre, pero el número nuevo es otro.
    nueva, error = crear_reserva(bd, usuario, pista, "2026-10-15", "10:00")
    assert error is None
    assert bd.execute("SELECT numero FROM reserva WHERE id = ?", (nueva,)).fetchone()[0] == "15-10-2026-0002"


def test_mismo_hueco_ocupado_no_gasta_numero(bd):
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    pista = crear_espacio(bd, "Pista 1")
    crear_reserva(bd, usuario, pista, "2026-10-15", "10:00")
    assert crear_reserva(bd, usuario, pista, "2026-10-15", "10:00") == (None, MENSAJE_OCUPADO)
    nueva, _ = crear_reserva(bd, usuario, pista, "2026-10-15", "12:00")
    assert bd.execute("SELECT numero FROM reserva WHERE id = ?", (nueva,)).fetchone()[0] == "15-10-2026-0002"


def test_dos_confirmaciones_simultaneas_guardan_solo_una(app, bd):
    """SC-004: 10 de 10 intentos con dos personas confirmando a la vez."""
    ana, luis = crear_usuario(bd, "ana@ejemplo.es"), crear_usuario(bd, "luis@ejemplo.es")
    pista = crear_espacio(bd, "Pista 1")
    ruta = app.config["RESERVAS_DB"]
    for intento in range(10):
        hora = f"{8 + intento:02d}:00"
        salida = threading.Barrier(2)
        resultados = []

        def confirmar(usuario):
            conexion = conectar(ruta)
            try:
                salida.wait()
                resultados.append(crear_reserva(conexion, usuario, pista, "2026-11-02", hora))
            finally:
                conexion.close()

        hilos = [threading.Thread(target=confirmar, args=(u,)) for u in (ana, luis)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        assert sorted(error or "" for _, error in resultados) == ["", MENSAJE_OCUPADO]
        guardadas = bd.execute(
            "SELECT COUNT(*) FROM reserva WHERE dia = '2026-11-02' AND hora_inicio = ?", (hora,)
        ).fetchone()[0]
        assert guardadas == 1


def _dia_futuro(dias=3):
    return (ahora().date() + timedelta(days=dias)).isoformat()


def test_reservar_desde_el_calendario(cliente_http, bd, correos):
    configurar_cliente(bd)
    pista = crear_espacio(bd, "Pista 1")
    crear_usuario(bd, "ana@ejemplo.es")
    entrar(cliente_http, "ana@ejemplo.es", "clave1234")
    dia = _dia_futuro()
    pagina = cliente_http.get(f"/calendario?dia={dia}").get_data(as_text=True)
    assert "18:00 – 20:00" in pagina
    respuesta = cliente_http.post("/reservar", data={"dia": dia, "hora": "10:00", "espacio": pista})
    pagina = cliente_http.get(respuesta.headers["Location"]).get_data(as_text=True)
    numero = bd.execute("SELECT numero FROM reserva").fetchone()[0]
    assert numero in pagina and "Reserva confirmada" in pagina
    assert numero in correos[-1]["asunto"] and "Pista 1" in correos[-1]["cuerpo"]

    # Otro usuario ve ese espacio ocupado y no puede reservarlo.
    cliente_http.post("/salir")
    crear_usuario(bd, "luis@ejemplo.es")
    entrar(cliente_http, "luis@ejemplo.es", "clave1234")
    pagina = cliente_http.get(f"/calendario?dia={dia}").get_data(as_text=True)
    assert 'class="espacio ocupado"' in pagina
    respuesta = cliente_http.post("/reservar", data={"dia": dia, "hora": "10:00", "espacio": pista},
                                  follow_redirects=True)
    assert MENSAJE_OCUPADO in respuesta.get_data(as_text=True)


def test_no_se_puede_reservar_fuera_de_plazo(cliente_http, bd):
    configurar_cliente(bd, antelacion_max_dias=5)
    pista = crear_espacio(bd, "Pista 1")
    crear_usuario(bd, "ana@ejemplo.es")
    entrar(cliente_http, "ana@ejemplo.es", "clave1234")
    cliente_http.post("/reservar", data={"dia": _dia_futuro(10), "hora": "10:00", "espacio": pista})
    assert bd.execute("SELECT COUNT(*) FROM reserva").fetchone()[0] == 0


def test_modificar_conserva_numero_y_cancelar_libera(cliente_http, bd, correos):
    configurar_cliente(bd)
    pista1, pista2 = crear_espacio(bd, "Pista 1"), crear_espacio(bd, "Pista 2")
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    reserva, _ = crear_reserva(bd, usuario, pista1, _dia_futuro(), "10:00")
    numero = bd.execute("SELECT numero FROM reserva").fetchone()[0]
    entrar(cliente_http, "ana@ejemplo.es", "clave1234")
    cliente_http.post(f"/reservas/{reserva}/modificar/confirmar",
                      data={"dia": _dia_futuro(4), "hora": "12:00", "espacio": pista2})
    fila = bd.execute("SELECT * FROM reserva").fetchone()
    assert (fila["numero"], fila["dia"], fila["hora_inicio"], fila["espacio_id"]) == (
        numero, _dia_futuro(4), "12:00", pista2)
    assert correos[-1]["asunto"].startswith("Reserva modificada")
    cliente_http.post(f"/reservas/{reserva}/cancelar")
    assert bd.execute("SELECT estado FROM reserva").fetchone()[0] == "cancelada"
    assert correos[-1]["asunto"].startswith("Reserva cancelada")
    assert "Cancelada" in cliente_http.get("/mis-reservas").get_data(as_text=True)


def test_no_se_cancela_dentro_del_plazo_minimo(cliente_http, bd):
    configurar_cliente(bd, cancelacion_min_horas=24 * 30)
    pista = crear_espacio(bd, "Pista 1")
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    reserva, _ = crear_reserva(bd, usuario, pista, _dia_futuro(), "10:00")
    entrar(cliente_http, "ana@ejemplo.es", "clave1234")
    respuesta = cliente_http.post(f"/reservas/{reserva}/cancelar", follow_redirects=True)
    assert "720 horas de antelación" in respuesta.get_data(as_text=True)
    assert bd.execute("SELECT estado FROM reserva").fetchone()[0] == "vigente"


def test_el_administrador_reserva_y_elimina_para_un_usuario(cliente_http, bd, correos):
    configurar_cliente(bd, cancelacion_min_horas=24 * 30, antelacion_max_dias=2)
    pista = crear_espacio(bd, "Pista 1")
    usuario = crear_usuario(bd, "ana@ejemplo.es")
    crear_usuario(bd, "jefa@ejemplo.es", rol="administrador")
    entrar(cliente_http, "jefa@ejemplo.es", "clave1234")
    # Más allá del plazo máximo de antelación (FR-024).
    cliente_http.post(f"/admin/reservas/nueva/{usuario}/confirmar",
                      data={"dia": _dia_futuro(20), "hora": "14:00", "espacio": pista})
    fila = bd.execute("SELECT * FROM reserva").fetchone()
    assert fila["usuario_id"] == usuario and correos[-1]["para"] == "ana@ejemplo.es"
    # Sin plazo mínimo de cancelación para el administrador.
    cliente_http.post(f"/reservas/{fila['id']}/cancelar")
    assert bd.execute("SELECT estado FROM reserva").fetchone()[0] == "cancelada"
    assert correos[-1]["asunto"].startswith("Reserva cancelada")


def test_otro_usuario_no_ve_reservas_ajenas(cliente_http, bd):
    configurar_cliente(bd)
    pista = crear_espacio(bd, "Pista 1")
    ana = crear_usuario(bd, "ana@ejemplo.es")
    crear_usuario(bd, "luis@ejemplo.es")
    reserva, _ = crear_reserva(bd, ana, pista, _dia_futuro(), "10:00")
    entrar(cliente_http, "luis@ejemplo.es", "clave1234")
    assert cliente_http.get(f"/reservas/{reserva}").status_code == 404
    assert cliente_http.post(f"/reservas/{reserva}/cancelar").status_code == 404


def test_consulta_filtra_busca_y_no_modifica(cliente_http, bd):
    configurar_cliente(bd)
    pista = crear_espacio(bd, "Pista 1")
    ana = crear_usuario(bd, "ana@ejemplo.es")
    crear_reserva(bd, ana, pista, "2026-10-16", "10:00")
    crear_reserva(bd, ana, pista, "2026-11-20", "10:00")
    reserva, _ = crear_reserva(bd, ana, pista, _dia_futuro(), "12:00")
    crear_usuario(bd, "portero@ejemplo.es", rol="consulta")
    entrar(cliente_http, "portero@ejemplo.es", "clave1234")
    pagina = cliente_http.get("/consulta?mes=2026-11").get_data(as_text=True)
    assert "20-11-2026-0002" in pagina and "16-10-2026-0001" not in pagina
    pagina = cliente_http.get("/consulta?dia=2026-10-16").get_data(as_text=True)
    assert "16-10-2026-0001" in pagina and "20-11-2026-0002" not in pagina
    pagina = cliente_http.get("/consulta?numero=16-10-2026-0001").get_data(as_text=True)
    assert "Vigente" in pagina and "ana@ejemplo.es" in pagina
    pagina = cliente_http.get("/consulta?numero=01-01-2026-9999").get_data(as_text=True)
    assert "No existe ninguna reserva con ese número" in pagina
    assert "Modificar" not in pagina and "Eliminar" not in pagina
    assert cliente_http.post(f"/reservas/{reserva}/cancelar").status_code == 403
    assert cliente_http.get("/calendario").status_code == 403
