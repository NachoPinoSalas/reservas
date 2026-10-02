"""Fechas y horas en hora de Madrid, con formato español (FR-028)."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("Europe/Madrid")
DIAS_LETRA = ["L", "M", "X", "J", "V", "S", "D"]
DIAS_NOMBRE = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def ahora():
    return datetime.now(ZONA)


def a_minutos(hora):
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def de_minutos(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def es_hora(texto):
    try:
        time.fromisoformat(texto)
    except (TypeError, ValueError):
        return False
    return len(texto) == 5


def leer_dia(texto):
    """'aaaa-mm-dd' → date, o None si no es una fecha válida."""
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


def inicio_reserva(dia, hora):
    """Momento (con zona horaria) en que empieza una franja."""
    if isinstance(dia, str):
        dia = date.fromisoformat(dia)
    return datetime.combine(dia, time.fromisoformat(hora), tzinfo=ZONA)


def fecha_es(valor):
    """date o 'aaaa-mm-dd' → 'dd/mm/aaaa'."""
    if not valor:
        return ""
    if isinstance(valor, str):
        valor = date.fromisoformat(valor[:10])
    return valor.strftime("%d/%m/%Y")


def dia_semana(valor):
    if isinstance(valor, str):
        valor = date.fromisoformat(valor[:10])
    return DIAS_NOMBRE[valor.weekday()]


def mes_es(texto):
    """'aaaa-mm' → 'octubre de 2026'."""
    anio, mes = texto.split("-")
    return f"{MESES[int(mes) - 1]} de {anio}"
