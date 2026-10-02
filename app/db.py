"""Conexión a la base de datos SQLite y creación inicial de las tablas."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

ESQUEMA = Path(__file__).with_name("schema.sql")


def conectar(ruta):
    conexion = sqlite3.connect(ruta, timeout=15)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def get_db():
    if "db" not in g:
        g.db = conectar(current_app.config["RESERVAS_DB"])
    return g.db


def cerrar_db(_error=None):
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


@contextmanager
def transaccion(conexion):
    """Operación atómica que bloquea la escritura desde el principio (evita carreras)."""
    if conexion.in_transaction:
        conexion.commit()
    conexion.execute("BEGIN IMMEDIATE")
    try:
        yield conexion
    except BaseException:
        conexion.rollback()
        raise
    conexion.commit()


def inicializar(ruta):
    """Crea las tablas si no existen, la fila del cliente y la cuenta inicial admin/admin (FR-001)."""
    conexion = conectar(ruta)
    try:
        conexion.execute("PRAGMA journal_mode = WAL")
        conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
        conexion.execute("INSERT OR IGNORE INTO cliente (id) VALUES (1)")
        # Contraseña de primer uso permitida por la constitución (principio V); se cambia obligatoriamente (FR-002).
        conexion.execute(
            "INSERT OR IGNORE INTO usuario (identificador, clave_cifrada, rol, debe_cambiar_clave) "
            "SELECT 'admin', ?, 'administrador', 1 WHERE NOT EXISTS (SELECT 1 FROM usuario)",
            (generate_password_hash("admin"),),
        )
        conexion.commit()
    finally:
        conexion.close()
