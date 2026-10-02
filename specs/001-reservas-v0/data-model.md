# Modelo de datos: Reservas v0

Fechas guardadas como `aaaa-mm-dd` y horas como `hh:mm`, siempre en hora de Madrid; se muestran como `dd/mm/aaaa` (FR-028).

## cliente (una sola fila por instalación)

| Campo | Notas |
|-------|-------|
| nombre | obligatorio |
| logo, logo_tipo | opcional (PNG/JPG, tamaño limitado) |
| dias | lista de días abiertos (L–D) |
| apertura, cierre | `hh:mm`; cierre posterior a apertura |
| duracion_min | múltiplo de 15 y que quepa al menos una vez en el horario |
| antelacion_max_dias | plazo máximo para reservar |
| cancelacion_min_horas | plazo mínimo para modificar/cancelar |
| configurado | falso hasta completar el asistente (FR-006) |

## planta

`id`, `nombre` (único). Opcional: puede no haber plantas.

## espacio

`id`, `nombre`, `planta_id` (opcional). No se puede borrar un espacio/planta con reservas futuras vigentes (spec).

## usuario

| Campo | Notas |
|-------|-------|
| id | |
| identificador | email; en la cuenta inicial vale `admin` (FR-013). Único (FR-010) |
| nombre, apellidos, telefono | obligatorios para usuarios registrados; el admin inicial los completa tras el primer acceso |
| nif | opcional |
| clave_cifrada | nunca en claro |
| rol | `administrador`, `usuario` o `consulta` (FR-014) |
| debe_cambiar_clave | verdadero en `admin` inicial |
| fallos_acceso, bloqueado_hasta | bloqueo de 15 min a los 5 fallos (FR-032) |

Regla: siempre debe quedar al menos un administrador (FR-016). No hay borrado de usuarios (spec).

## enlace_recuperacion

`usuario_id`, `huella` (del enlace, no el enlace), `caduca_en` (1 h), `usado`. Un solo uso (FR-011).

## reserva

| Campo | Notas |
|-------|-------|
| id | |
| numero | `dd-mm-aaaa-NNNN`; único; se conserva al modificar (FR-022) |
| usuario_id, espacio_id | |
| dia, hora_inicio | la franja; la hora de fin se calcula con la duración |
| estado | `vigente` o `cancelada` |
| creada_en | |

**Garantía de no duplicados (FR-019)**: índice único sobre (`espacio_id`, `dia`, `hora_inicio`) **solo para reservas vigentes**; al cancelar, el hueco queda libre pero el número no se reutiliza.

**Transiciones**: `vigente` → `cancelada` (por el usuario, el administrador, o automáticamente por un cambio de configuración, FR-033). No se vuelve atrás. El administrador puede "eliminar" (FR-024), que se guarda como cancelada para no perder números.

## contador_reservas

`anio` (año de la fecha de reserva), `ultimo`. Se incrementa en la misma operación que crea la reserva (FR-021).

## Franja (no se guarda)

Se calcula: desde `apertura`, de `duracion_min` en `duracion_min`, mientras termine antes o a `cierre`; solo en `dias` abiertos; dentro de `antelacion_max_dias`; descartando las de hoy que ya empezaron (casos límite de la spec).
