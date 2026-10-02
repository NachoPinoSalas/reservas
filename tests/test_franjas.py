from datetime import date, datetime

from app.fechas import ZONA
from app.reservas import calcular_franjas, dias_reservables, encaja

CLIENTE = {"dias": "0,1,2,3,4", "apertura": "10:00", "cierre": "20:00", "duracion_min": 120,
           "antelacion_max_dias": 7}
# Jueves 15/10/2026 a las 09:00, hora de Madrid.
MOMENTO = datetime(2026, 10, 15, 9, 0, tzinfo=ZONA)


def test_horario_de_10_a_20_con_2_horas():
    assert calcular_franjas(CLIENTE, date(2026, 10, 16), MOMENTO) == ["10:00", "12:00", "14:00", "16:00", "18:00"]


def test_ultima_franja_debe_terminar_antes_del_cierre():
    cliente = {**CLIENTE, "cierre": "19:00"}
    assert calcular_franjas(cliente, date(2026, 10, 16), MOMENTO) == ["10:00", "12:00", "14:00", "16:00"]


def test_duracion_de_15_minutos():
    cliente = {**CLIENTE, "apertura": "10:00", "cierre": "11:00", "duracion_min": 15}
    assert calcular_franjas(cliente, date(2026, 10, 16), MOMENTO) == ["10:00", "10:15", "10:30", "10:45"]


def test_dia_no_permitido():
    assert calcular_franjas(CLIENTE, date(2026, 10, 17), MOMENTO) == []  # sábado


def test_mas_alla_del_plazo_maximo():
    assert calcular_franjas(CLIENTE, date(2026, 10, 22), MOMENTO)  # justo 7 días
    assert calcular_franjas(CLIENTE, date(2026, 10, 23), MOMENTO) == []


def test_el_administrador_puede_pasar_del_plazo_maximo():
    assert calcular_franjas(CLIENTE, date(2026, 12, 1), MOMENTO, sin_limite_antelacion=True)


def test_dia_pasado():
    assert calcular_franjas(CLIENTE, date(2026, 10, 14), MOMENTO, sin_limite_antelacion=True) == []


def test_franjas_de_hoy_ya_empezadas_no_se_ofrecen():
    momento = datetime(2026, 10, 15, 12, 0, tzinfo=ZONA)
    assert calcular_franjas(CLIENTE, date(2026, 10, 15), momento) == ["14:00", "16:00", "18:00"]


def test_dias_reservables_solo_abiertos_y_en_plazo():
    dias = dias_reservables(CLIENTE, MOMENTO)
    assert dias[0] == date(2026, 10, 15)
    assert date(2026, 10, 17) not in dias and date(2026, 10, 18) not in dias
    assert dias[-1] == date(2026, 10, 22)


def test_encaja():
    assert encaja(CLIENTE, "2026-10-16", "12:00")
    assert not encaja(CLIENTE, "2026-10-16", "11:00")
    assert not encaja(CLIENTE, "2026-10-17", "12:00")
