# Tasks: Reservas v0

**Input**: `/specs/001-reservas-v0/` (plan.md, spec.md, research.md, data-model.md, contracts/pantallas.md, quickstart.md)

**Tests**: la spec no pide TDD. Solo se incluyen pruebas automáticas para la lógica delicada que el plan lista en `tests/` (franjas, número, doble reserva, bloqueo, cambios de configuración); el resto se valida con [quickstart.md](quickstart.md).

**Organización**: por historia de usuario, en orden de prioridad. Rutas relativas a la raíz del repositorio (proyecto único de Flask, ver plan.md).

## Formato: `[ID] [P?] [Historia] Descripción con ruta`

- **[P]**: se puede hacer en paralelo (ficheros distintos, sin dependencias pendientes)
- Todos los textos visibles en español de España; fechas `dd/mm/aaaa`, 24 h, hora de Madrid (FR-028)

---

## Phase 1: Setup

- [X] T001 Crear la estructura `app/`, `app/templates/`, `app/static/`, `tests/` según plan.md
- [X] T002 Crear `requirements.txt` con solo: Flask, gunicorn, tzdata, pytest
- [X] T003 [P] Crear `Procfile` con el arranque en producción (`gunicorn "app:create_app()"`) y un `.gitignore` (base de datos `*.db`, `__pycache__`, `.env`)

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T004 Crear `app/schema.sql` con las tablas de data-model.md: `cliente` (una sola fila), `planta`, `espacio`, `usuario` (rol ∈ `administrador`/`usuario`/`consulta`; identificador único), `enlace_recuperacion`, `reserva` (estado ∈ `vigente`/`cancelada`; **índice único sobre (`espacio_id`,`dia`,`hora_inicio`) solo donde estado = 'vigente'**) y `contador_reservas`
- [X] T005 Crear `app/db.py`: conexión SQLite (ruta por variable de entorno `RESERVAS_DB`), creación de tablas si no existen y alta de la cuenta inicial `admin`/`admin` con `debe_cambiar_clave` = verdadero y rol administrador (FR-001); contraseña guardada cifrada con Werkzeug
- [X] T006 Crear `app/__init__.py` con `create_app()`: clave de sesión desde variable de entorno `SECRET_KEY` (nunca en código), cookie de sesión segura, protección CSRF ligera en todos los formularios, página de error 404/500 en español
- [X] T007 [P] Añadir en `app/__init__.py` los decoradores de acceso por rol (`login_required`, `rol_requerido(...)`) que comprueban en el servidor; si el usuario tiene `debe_cambiar_clave`, redirigir a la pantalla de cambio obligatorio (FR-002); si el cliente no está configurado, mostrar "Reservas aún no disponibles" a visitantes (FR-006)
- [X] T008 [P] Crear `app/templates/base.html` y `app/static/style.css`: plantilla común adaptable a móvil (columna única, botones grandes, sin scroll horizontal), logo del cliente arriba a la izquierda si existe (FR-007), menú según el rol
- [X] T009 [P] Crear `app/correo.py`: envío por SMTP estándar con datos en variables de entorno; si falla, devuelve un error recuperable (nunca rompe la acción, ver spec "Fallo al enviar un email"); textos de los emails en español
- [X] T010 [P] Crear utilidades de fecha/hora en `app/reservas.py` (o `app/fechas.py` si se prefiere): zona `Europe/Madrid`, formato `dd/mm/aaaa` y `hh:mm`, función `calcular_franjas(cliente, dia)` (apertura → cierre en pasos de `duracion_min`, solo si la franja termina a o antes del cierre, solo días abiertos, dentro de `antelacion_max_dias`, descartando franjas de hoy ya empezadas)
- [X] T011 [P] Crear `tests/test_franjas.py`: horario 10:00–20:00 con 2 h da 10, 12, 14, 16, 18; día no permitido; más allá del plazo máximo; franja de hoy ya pasada

**Checkpoint**: la app arranca, existe `admin` y las pantallas heredan la plantilla.

---

## Phase 3: US1 – El administrador pone en marcha la aplicación (P1) 🎯 MVP

**Objetivo**: entrar con `admin`/`admin`, cambiar contraseña, completar el cliente.

**Prueba independiente**: instalación nueva → entrar como `admin` → contraseña nueva → asistente → el calendario (aunque vacío de reservas) muestra espacios y horarios; el logo aparece arriba a la izquierda.

- [X] T012 [US1] Crear `app/auth.py` con acceso por identificador (email o `admin`) y contraseña, cierre de sesión, y mensaje genérico "Email o contraseña incorrectos"; plantilla `app/templates/entrar.html`
- [X] T013 [US1] En `app/auth.py` añadir la validación de contraseña nueva (FR-031: "al menos 8 caracteres, con al menos una letra y un número"; mensaje exacto "La contraseña debe tener al menos 8 caracteres, una letra y un número") y la pantalla de cambio obligatorio de contraseña (`app/templates/cambiar_clave_obligatoria.html`) que limpia `debe_cambiar_clave`; `admin` no pasa la regla, por lo que no puede reutilizarse (US1-1, US1-2)
- [X] T014 [P] [US1] Crear `app/cliente.py` con la configuración del cliente: nombre (obligatorio), logo opcional (PNG/JPG, tamaño limitado, guardado en la base de datos), días L–D, apertura < cierre, duración múltiplo de 15 min y que quepa al menos una vez, plazo máximo de antelación (días), plazo mínimo de cancelación (horas); marca `configurado` al guardar (FR-004)
- [X] T015 [US1] En `app/cliente.py` añadir CRUD de plantas (opcionales, nombre único) y espacios (nombre, planta opcional) (FR-005); borrar planta/espacio con reservas futuras vigentes se rechaza indicando cuántas tienen
- [X] T016 [US1] Crear `app/templates/asistente.html` (y plantillas de plantas/espacios): asistente de configuración paso a paso solo para administrador, usable en móvil (depende de T014, T015)
- [X] T017 [US1] En `app/__init__.py` servir el logo del cliente (ruta de imagen desde la base de datos) y mostrarlo en `base.html`
- [X] T018 [P] [US1] Crear `tests/test_cliente.py` (primera parte): validación de duración/horario; plantas y espacios

**Checkpoint**: pasos 1–4 del quickstart.

---

## Phase 4: US2 – Registro, acceso y recuperación de contraseña (P1)

**Objetivo**: autoservicio de cuentas.

**Prueba independiente**: registrarse → llega email → cerrar sesión → recuperar contraseña con enlace → entrar.

- [X] T019 [US2] En `app/auth.py` añadir registro: nombre, apellidos, email, teléfono, contraseña obligatorios, NIF opcional; rol `usuario`; email único ("Ya existe una cuenta con ese email"); solo si el cliente está configurado; plantilla `app/templates/registro.html` (FR-008, FR-010)
- [X] T020 [US2] En `app/correo.py` añadir el email de resumen de registro (sin contraseña) y llamarlo desde el registro; si falla, avisar al usuario sin deshacer el registro (FR-009)
- [X] T021 [US2] En `app/auth.py` añadir bloqueo: contar fallos seguidos en `usuario.fallos_acceso`; a los 5 guardar `bloqueado_hasta` = ahora + 15 min y mostrar "Demasiados intentos, vuelva a probar en 15 minutos"; un acceso correcto reinicia el contador (FR-032)
- [X] T022 [US2] En `app/auth.py` añadir "¿Olvidó su contraseña?": si el email existe, guardar solo la huella del enlace (un solo uso, caduca a 1 h) y enviar el email; mostrar "Se ha enviado un email a <email>, compruebe su bandeja de entrada"; si no existe, "No existe ninguna cuenta con ese email" y no enviar nada; pantalla de nueva contraseña con la regla de FR-031; enlace usado o caducado → aviso de caducidad y opción de pedir otro (FR-011); si falla el envío, mostrar "No se ha podido enviar el email, inténtelo de nuevo más tarde" y anular el enlace; plantillas `olvido.html` y `nueva_clave.html`
- [X] T023 [P] [US2] Crear `app/usuarios.py` con "Mi perfil": ver/editar nombre, apellidos, NIF, email (único) y teléfono (FR-012); plantilla `app/templates/perfil.html`. El administrador inicial completa aquí sus datos; al guardar su email, el identificador pasa a ser ese email (FR-013)
- [X] T024 [P] [US2] Crear `tests/test_auth.py`: reglas de contraseña, bloqueo a los 5 fallos y reinicio al acertar, enlace de recuperación de un solo uso y caducidad de 1 h

**Checkpoint**: pasos 5–7 y 17 del quickstart.

---

## Phase 5: US3 – Reservar desde el calendario (P1)

**Objetivo**: reservar en ≤ 4 pasos con número y email.

**Prueba independiente**: con cliente configurado y usuario registrado, reservar, ver número y email, y ver el espacio en rojo para otro usuario.

- [X] T025 [US3] En `app/reservas.py` crear la creación de reserva en una sola transacción: calcular el número `dd-mm-aaaa-NNNN` incrementando `contador_reservas` del año de la fecha de reserva (empieza en `0001`, nunca se reutiliza, común a todo el año) e insertar la reserva `vigente`; si la restricción única falla, devolver "Este espacio acaba de ser reservado, elija otro" (FR-019, FR-021)
- [X] T026 [US3] En `app/reservas.py` crear el calendario: solo días permitidos y dentro del plazo; para el día elegido, franjas (T010) con espacios libres y ocupados (ocupados en rojo y no elegibles); confirmar muestra el número; plantillas `calendario.html` y `confirmacion.html` (FR-017, FR-018, FR-020)
- [X] T027 [US3] En `app/correo.py` añadir el email de reserva (número, cliente, espacio, planta, día y hora) y enviarlo al confirmar; si falla, la reserva se guarda y se avisa (FR-023)
- [X] T028 [P] [US3] Crear `tests/test_reservas.py`: número correcto y contador por año (la primera reserva de 2027 hecha en 2026 lleva `0001`), número no reutilizado tras cancelar, y **dos confirmaciones simultáneas del mismo espacio/franja guardan solo una** (SC-004)

**Checkpoint**: pasos 8–10 del quickstart. **MVP desplegable**: US1 + US2 + US3.

---

## Phase 6: US4 – Gestionar mis reservas (P2)

**Prueba independiente**: reservar, modificar, cancelar; comprobar emails y que el espacio vuelve a estar libre.

- [X] T029 [US4] En `app/reservas.py` crear "Mis reservas": todo el historial (pasado y futuro, vigente y cancelada, con estado); plantilla `mis_reservas.html` (FR-034)
- [X] T030 [US4] En `app/reservas.py` crear modificar (día, hora o espacio libre; conserva el número) y cancelar (pasa a `cancelada`, el hueco queda libre) solo para reservas futuras vigentes y si falta más que `cancelacion_min_horas`; si no, indicar el plazo (FR-022). El nuevo día y franja se validan con `calcular_franjas` (días permitidos, plazo máximo, franja no pasada); si otro usuario ocupa el hueco a la vez, mostrar "Este espacio acaba de ser reservado, elija otro" y la reserva original no cambia
- [X] T031 [US4] En `app/correo.py` añadir los emails de modificación y cancelación y enviarlos desde T030 (FR-023)

**Checkpoint**: pasos 11–12.

---

## Phase 7: US5 – El administrador gestiona usuarios y roles (P2)

**Prueba independiente**: crear un usuario de consulta, entrar con él y comprobar que solo consulta.

- [X] T032 [US5] En `app/usuarios.py` crear (solo administrador) listado, alta manual (con contraseña según FR-031), edición de datos y cambio de rol; plantillas `usuarios.html` y `usuario_form.html` (FR-015)
- [X] T033 [US5] En `app/usuarios.py` impedir quitar el rol al último administrador (FR-016); un usuario sin rol de administrador no ve ni puede usar estas rutas (comprobación en servidor); no hay borrado de usuarios

**Checkpoint**: paso 13.

---

## Phase 8: US6 – El administrador gestiona reservas de cualquier usuario (P2)

**Prueba independiente**: crear una reserva para un usuario, comprobar su email y su lista; eliminarla y ver el espacio libre.

- [X] T034 [US6] En `app/reservas.py` crear (solo administrador) crear/modificar/eliminar reservas de cualquier usuario sin límite de plazo mínimo; respeta días, horario y franjas no pasadas, pero puede ir más allá del plazo máximo de antelación; "eliminar" = marcar `cancelada` para no perder números; plantillas `admin_reservas.html` y `admin_reserva_form.html` (FR-024)
- [X] T035 [US6] Enviar al usuario el email correspondiente en cada acción de T034 (reutilizando `app/correo.py`)
- [X] T036 [US6] En `app/cliente.py` implementar FR-033: al cambiar días, horario o duración, calcular cuántas reservas futuras vigentes dejarían de encajar, mostrar el aviso con la cifra, pedir confirmación y, al confirmar, cancelarlas y enviar a cada usuario afectado un email de cancelación que explique el motivo; las que siguen encajando no se tocan
- [X] T037 [P] [US6] Completar `tests/test_cliente.py`: el cambio de configuración cancela solo las reservas que dejan de encajar y deja libres sus espacios; y no se puede borrar una planta o espacio con reservas futuras vigentes (indica cuántas)

**Checkpoint**: pasos 14–15.

---

## Phase 9: US7 – El personal de consulta verifica reservas (P3)

**Prueba independiente**: con reservas creadas, entrar como consulta, filtrar y buscar por número.

- [X] T038 [US7] Crear `app/consulta.py` (roles consulta y administrador, solo lectura): lista de todas las reservas con filtros por día, mes y usuario (FR-026); plantilla `consulta.html`
- [X] T039 [US7] En `app/consulta.py` añadir búsqueda por número: muestra usuario, espacio, día, hora y estado (vigente/cancelada); si no existe, "No existe ninguna reserva con ese número"; sin ninguna acción de crear/modificar/eliminar (FR-027)

**Checkpoint**: paso 16.

---

## Phase 10: Polish y publicación

- [X] T040 Revisar que todos los textos, errores y emails estén en español de España y que las fechas sean `dd/mm/aaaa` y 24 h (FR-028)
- [ ] T041 Revisar en un móvil todas las pantallas: sin desplazamiento horizontal, botones usables (SC-007, FR-029)
- [X] T042 [P] Escribir `README.md` corto: variables de entorno (`SECRET_KEY`, `RESERVAS_DB`, datos SMTP), arranque local y en producción, y copia de seguridad (copiar el fichero de base de datos)
- [X] T043 Comprobar que no hay claves ni contraseñas en el código (excepto la contraseña inicial `admin`, permitida por el principio V) (constitución, principio V)
- [X] T044 Recorrer completo [quickstart.md](quickstart.md) (los 19 pasos) y ejecutar `pytest`
- [ ] T045 Publicar como un único servicio web con disco persistente y variables de entorno; comprobar el paso 19 (reinicio sin perder datos) en la dirección real

---

## Dependencias y orden

- Setup → Foundational → historias. Foundational bloquea todo.
- **US1** primero (sin cliente configurado no hay nada que reservar). **US2** puede ir en paralelo con US1 salvo el registro, que necesita el cliente configurado.
- **US3** necesita US1 (cliente, espacios) y US2 (cuentas).
- **US4** necesita US3. **US6** necesita US3 y US1 (T036 amplía `cliente.py`). **US5** y **US7** son independientes de US3–US4 (US7 necesita reservas para tener algo que mostrar).
- Mismo fichero = no en paralelo: `auth.py` (T012, T013, T019, T021, T022), `cliente.py` (T014, T015, T036), `reservas.py` (T010, T025, T026, T029, T030, T034), `correo.py` (T009, T020, T027, T031, T035).

## Paralelo

- Foundational: T007, T008, T009, T010, T011 a la vez tras T006.
- US1: T018 en paralelo con T016–T017. US2: T023 y T024 a la vez con el resto del registro.
- Tras US3: US4, US5 y US7 pueden avanzar a la vez.

## Estrategia

1. **MVP**: Setup + Foundational + US1 + US2 + US3 → validar pasos 1–10 del quickstart → **publicar** (la reserva ya funciona de extremo a extremo).
2. Añadir US4 → US6 → US5 → US7, validando cada una, y volver a publicar.
3. Polish y publicación final (T040–T045).
