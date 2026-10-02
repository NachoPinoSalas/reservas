import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import conectar


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "clave-de-pruebas",
        "RESERVAS_DB": str(tmp_path / "pruebas.db"),
        "CORREO_MODO": "memoria",
        "CSRF_ACTIVO": False,
        "SESSION_COOKIE_SECURE": False,
    })
    yield app


@pytest.fixture
def cliente_http(app):
    return app.test_client()


@pytest.fixture
def bd(app):
    conexion = conectar(app.config["RESERVAS_DB"])
    yield conexion
    conexion.close()


@pytest.fixture
def correos(app):
    return app.extensions.setdefault("correos", [])


def configurar_cliente(conexion, **cambios):
    """Cliente configurado: L–D, 10:00–20:00, 2 h, 30 días de antelación, 24 h para cancelar."""
    datos = {"nombre": "Pádel Centro", "dias": "0,1,2,3,4,5,6", "apertura": "10:00", "cierre": "20:00",
             "duracion_min": 120, "antelacion_max_dias": 30, "cancelacion_min_horas": 24, **cambios}
    conexion.execute(
        "UPDATE cliente SET nombre = :nombre, dias = :dias, apertura = :apertura, cierre = :cierre, "
        "duracion_min = :duracion_min, antelacion_max_dias = :antelacion_max_dias, "
        "cancelacion_min_horas = :cancelacion_min_horas, configurado = 1 WHERE id = 1",
        datos,
    )
    conexion.commit()


def crear_espacio(conexion, nombre, planta_id=None):
    cursor = conexion.execute("INSERT INTO espacio (nombre, planta_id) VALUES (?, ?)", (nombre, planta_id))
    conexion.commit()
    return cursor.lastrowid


def crear_usuario(conexion, email, clave="clave1234", rol="usuario"):
    cursor = conexion.execute(
        "INSERT INTO usuario (identificador, nombre, apellidos, telefono, clave_cifrada, rol) "
        "VALUES (?, 'Ana', 'López', '600000000', ?, ?)",
        (email, generate_password_hash(clave), rol),
    )
    conexion.commit()
    return cursor.lastrowid


def entrar(cliente_http, identificador, clave):
    return cliente_http.post("/entrar", data={"identificador": identificador, "clave": clave})
