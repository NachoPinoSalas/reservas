# Implementation Plan: Reservas v0

**Branch**: `001-reservas-v0` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-reservas-v0/spec.md`

## Summary

Una única aplicación web, pequeña y sencilla, que sirve páginas completas desde el servidor (sin
aplicación de navegador aparte), con una base de datos de un solo fichero y envío de emails por un
servicio de correo ya existente. Una instalación = un cliente. Se publica como un único servicio
online con un disco persistente. Todo se diseña para que se vea bien en el móvil desde el principio.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Flask (web), Gunicorn (servidor de producción), tzdata (hora de Madrid). Nada más: contraseñas con las utilidades de Werkzeug (ya incluidas en Flask), emails con la librería estándar de Python.

**Storage**: SQLite (un solo fichero en el disco persistente). El logo del cliente se guarda dentro de la misma base de datos para que haya un único sitio que copiar.

**Testing**: pytest (lógica de franjas, número de reserva, doble reserva simultánea, bloqueo de acceso, cambios de configuración) + la guía manual de [quickstart.md](quickstart.md).

**Target Platform**: Servicio web Linux en un alojamiento con disco persistente; navegadores de móvil, tableta y ordenador.

**Project Type**: Aplicación web única (un solo proyecto, sin separar "frontend" y "backend").

**Performance Goals**: Un cliente pequeño (decenas de espacios, cientos de usuarios). Pantallas que cargan en menos de 2 s en móvil con 4G.

**Constraints**: Español de España, `dd/mm/aaaa`, 24 h, hora de Madrid; sin desplazamiento horizontal en móvil (SC-007); secretos solo en variables de entorno.

**Scale/Scope**: 1 cliente, ~10–50 espacios, hasta unos cientos de usuarios; ~15 pantallas.

## Constitution Check

*GATE: pasa antes de Phase 0 y se vuelve a comprobar tras el diseño.*

Se aplica la constitución de Reservas v2.1.0.

| Principio | Estado | Cómo se cumple |
|-----------|--------|----------------|
| I. Simplicidad ante todo | ✅ | Un proyecto, una base de datos de fichero, sin API separada, sin cola de tareas, sin caché, sin JavaScript pesado. Ver "Decisiones" en [research.md](research.md). |
| II. Español de España | ✅ | Todos los textos en español; fechas `dd/mm/aaaa`; hora de Madrid. El euro no interviene (no hay pagos). |
| III. Cero alcance fantasma | ✅ | Solo se construye lo de la spec. El RF6 del borrador ("apificar") se decide como **no construir** en v1 (research.md, D-02). |
| IV. Verificable sin código | ✅ | [quickstart.md](quickstart.md) recorre cada historia como lo haría una persona con la app. |
| V. Datos con respeto | ✅ | Solo los datos de la spec; contraseñas guardadas cifradas (nunca en claro); `admin/admin` permitido como única excepción del principio V (primer uso con cambio obligatorio, FR-002); claves de email y de sesión en variables de entorno. |

**Resultado**: sin violaciones; no se necesita tabla de complejidad. Se vuelve a comprobar tras el diseño: sigue sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/001-reservas-v0/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pantallas.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── __init__.py          # crea la aplicación, protege rutas por rol
├── db.py                # conexión SQLite y creación inicial de tablas
├── schema.sql           # tablas (ver data-model.md)
├── auth.py              # registro, acceso, bloqueo, recuperación de contraseña
├── cliente.py           # configuración del cliente, plantas, espacios, asistente
├── reservas.py          # franjas, calendario, crear/modificar/cancelar, número
├── usuarios.py          # perfil, gestión de usuarios y roles (admin)
├── consulta.py          # filtros y búsqueda por número (rol consulta)
├── correo.py            # envío de emails (SMTP) y textos de los emails
├── templates/           # páginas HTML en español
└── static/              # un único CSS adaptable a móvil

tests/
├── test_franjas.py
├── test_reservas.py     # incluye doble reserva simultánea
├── test_auth.py         # incluye bloqueo y contraseñas
└── test_cliente.py      # incluye cambios que cancelan reservas

requirements.txt
Procfile                 # comando de arranque en producción
```

**Structure Decision**: un solo proyecto con un módulo por área de la spec. Sin capas de
repositorios/servicios: cada módulo habla directamente con la base de datos.

## Complexity Tracking

Sin violaciones que justificar.
