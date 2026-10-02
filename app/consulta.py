"""Consulta de reservas: filtros por día, mes y usuario, y búsqueda por número (FR-026, FR-027)."""
import re

from flask import Blueprint, g, render_template, request

from app import es_admin, rol_requerido
from app.db import get_db
from app.fechas import ahora, leer_dia
from app.reservas import SQL_RESERVA, hora_fin, puede_cambiar

bp = Blueprint("consulta", __name__)

MENSAJE_NO_EXISTE = "No existe ninguna reserva con ese número"


@bp.route("/consulta")
@rol_requerido("consulta", "administrador")
def lista():
    """Solo lectura para el rol consulta; el administrador ve además crear, modificar y eliminar."""
    conexion, momento = get_db(), ahora()

    numero = (request.args.get("numero") or "").strip()
    encontrada = None
    if numero:
        encontrada = conexion.execute(SQL_RESERVA + " WHERE r.numero = ?", (numero,)).fetchone()

    filtros = {
        "dia": request.args.get("dia") or "",
        "mes": request.args.get("mes") or "",
        "usuario": request.args.get("usuario", type=int),
    }
    condiciones, parametros = [], []
    if leer_dia(filtros["dia"]):
        condiciones.append("r.dia = ?")
        parametros.append(filtros["dia"])
    if re.fullmatch(r"\d{4}-\d{2}", filtros["mes"]):
        condiciones.append("substr(r.dia, 1, 7) = ?")
        parametros.append(filtros["mes"])
    if filtros["usuario"]:
        condiciones.append("r.usuario_id = ?")
        parametros.append(filtros["usuario"])
    donde = " WHERE " + " AND ".join(condiciones) if condiciones else ""
    filas = conexion.execute(SQL_RESERVA + donde + " ORDER BY r.dia, r.hora_inicio, e.nombre", parametros).fetchall()

    def detalle(fila):
        return {
            "r": fila,
            "fin": hora_fin(g.cliente, fila["hora_inicio"]),
            "gestionable": es_admin() and puede_cambiar(fila, g.cliente, g.usuario, momento) is None,
        }

    usuarios = conexion.execute(
        "SELECT id, nombre, apellidos, identificador FROM usuario "
        "WHERE id IN (SELECT DISTINCT usuario_id FROM reserva) ORDER BY apellidos, nombre, identificador"
    ).fetchall()
    return render_template(
        "consulta.html",
        reservas=[detalle(f) for f in filas],
        filtros=filtros,
        usuarios=usuarios,
        numero=numero,
        encontrada=detalle(encontrada) if encontrada else None,
        no_existe=bool(numero) and encontrada is None,
        mensaje_no_existe=MENSAJE_NO_EXISTE,
    )
