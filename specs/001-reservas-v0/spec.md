# Feature Specification: Reservas v0

**Feature Branch**: `001-reservas-v0`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Reservas v0: página web para que usuarios españoles reserven espacios
(pista de pádel, cabina de rayos UVA, consulta médica, mesa de restaurante, puesto de oficina,
curso de surf) de un cliente concreto, con roles de administrador, usuario y consulta."

## Clarifications

### Session 2026-10-02

- Q: ¿El contador NNNN del número de reserva se reinicia cada día o sigue durante todo el año? → A: Sigue todo el año; se reinicia solo el 1 de enero del año de la fecha de reserva (ej. `15-10-2026-0001`, `16-10-2026-0002`).
- Q: ¿Qué reglas mínimas debe cumplir una contraseña? → A: Mínimo 8 caracteres, con al menos una letra y un número.
- Q: ¿Qué pasa tras varios fallos de contraseña seguidos? → A: Tras 5 fallos seguidos se bloquea el acceso a esa cuenta 15 minutos.
- Q: ¿Qué se hace con las reservas futuras que dejan de encajar tras cambiar horario, días o duración? → A: Se cancelan automáticamente y se avisa por email a cada usuario afectado.
- Q: ¿Qué ve el usuario en su lista de reservas? → A: Todo su historial, pasado y futuro, vigente y cancelado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Primer uso: el administrador pone en marcha la aplicación (Priority: P1)

Tras instalar la aplicación para un cliente, el administrador entra con la cuenta inicial
(usuario `admin`, contraseña `admin`). Antes de nada debe cambiar la contraseña. Después completa
sus datos (nombre, apellidos, NIF, email y teléfono) y un asistente le guía para configurar el
cliente: nombre, logo, días y horario de reserva, duración de cada reserva, plazos, plantas y
espacios. Hasta que el cliente no esté configurado, los visitantes ven el mensaje
"Reservas aún no disponibles".

**Why this priority**: sin un cliente configurado no hay nada que reservar.

**Independent Test**: en una instalación nueva, entrar como `admin`, cambiar la contraseña,
completar el asistente y comprobar que el calendario muestra los espacios y horarios configurados.

**Acceptance Scenarios**:

1. **Given** una instalación nueva, **When** el administrador entra con `admin` / `admin`,
   **Then** la aplicación le obliga a elegir una contraseña nueva antes de mostrar nada más.
2. **Given** que ya ha cambiado la contraseña, **When** intenta entrar de nuevo con `admin` / `admin`,
   **Then** el acceso se rechaza.
3. **Given** que el cliente no está configurado, **When** un visitante abre la aplicación,
   **Then** ve el mensaje "Reservas aún no disponibles" y no puede registrarse ni reservar.
4. **Given** que el administrador completa el asistente, **When** guarda la configuración,
   **Then** el logo del cliente aparece arriba a la izquierda y el calendario queda disponible.
5. **Given** un cliente configurado, **When** el administrador cambia cualquier dato del cliente
   (horario, días, espacios, plantas, plazos, logo), **Then** el cambio se ve al momento en el calendario.

---

### User Story 2 - Registro, acceso y recuperación de contraseña (Priority: P1)

Un visitante puede registrarse o entrar. Al registrarse recibe un email con el resumen de su
registro y su cuenta tiene el rol "usuario". Si olvida la contraseña, indica su email y recibe un
enlace para cambiarla. Una vez dentro, puede ver y editar su perfil.

**Why this priority**: hace falta tener cuenta para reservar.

**Independent Test**: registrarse con un email nuevo, comprobar que llega el email de resumen,
cerrar sesión, usar "¿Olvidó su contraseña?", cambiarla desde el enlace y entrar con la nueva.

**Acceptance Scenarios**:

1. **Given** un visitante, **When** se registra con nombre, apellidos, email, teléfono y contraseña,
   **Then** queda dentro con rol "usuario" y recibe un email con el resumen del registro.
2. **Given** un email ya registrado, **When** alguien intenta registrarse con él,
   **Then** se muestra el mensaje "Ya existe una cuenta con ese email".
3. **Given** un usuario registrado, **When** pulsa "¿Olvidó su contraseña?" e indica su email,
   **Then** ve el mensaje "Se ha enviado un email a <email informado>, compruebe su bandeja de entrada"
   y recibe un email con un enlace para cambiar la contraseña.
4. **Given** un email que no pertenece a ninguna cuenta, **When** se usa en "¿Olvidó su contraseña?",
   **Then** se muestra "No existe ninguna cuenta con ese email" y no se envía nada.
5. **Given** un enlace de cambio de contraseña ya usado o con más de 1 hora, **When** se abre,
   **Then** se indica que el enlace ha caducado y se ofrece pedir otro.
6. **Given** un usuario dentro de la aplicación, **When** edita su nombre, apellidos, NIF, email
   o teléfono y guarda, **Then** los cambios se ven al volver a abrir su perfil.

---

### User Story 3 - Reservar un espacio desde el calendario (Priority: P1)

El usuario elige un día en el calendario y ve, para cada franja horaria, qué espacios están libres
y cuáles ocupados (en rojo). Elige una franja y un espacio libre, confirma, y recibe un número de
reserva y un email con el resumen.

**Why this priority**: es el objetivo de negocio: reservar en pocos pasos.

**Independent Test**: con un cliente configurado y un usuario registrado, hacer una reserva y
comprobar que aparece el número, que llega el email y que ese espacio sale en rojo para otro usuario.

**Acceptance Scenarios**:

1. **Given** un usuario dentro de la aplicación, **When** abre el calendario,
   **Then** solo puede elegir días permitidos por el cliente y dentro del plazo máximo de antelación.
2. **Given** un día elegido, **When** se muestran las franjas, **Then** los espacios ocupados salen
   en rojo y no se pueden elegir, y los libres se distinguen claramente.
3. **Given** una franja y un espacio libres, **When** el usuario confirma la reserva,
   **Then** ve un mensaje de confirmación con el número de reserva (por ejemplo `15-10-2026-0001`)
   y recibe un email con el resumen: número, cliente, espacio, planta, día y hora.
4. **Given** una reserva confirmada, **When** otro usuario mira ese día,
   **Then** ese espacio aparece en rojo en esa franja.
5. **Given** dos usuarios que intentan reservar el mismo espacio y franja casi a la vez,
   **When** ambos confirman, **Then** solo uno lo consigue y el otro ve "Este espacio acaba de
   ser reservado, elija otro".

---

### User Story 4 - Gestionar mis reservas (Priority: P2)

El usuario ve la lista de todas sus reservas (pasadas y futuras, vigentes y canceladas; las canceladas
se marcan como "Cancelada"). Puede modificar las futuras vigentes (día, hora o espacio) o
cancelarlas, siempre que falte más tiempo que el plazo mínimo de cancelación del cliente.
Recibe un email cada vez que modifica o cancela.

**Why this priority**: es habitual cambiar de planes, pero se puede reservar sin ello.

**Independent Test**: hacer una reserva, modificarla, comprobar el email, cancelarla, comprobar
el email y que el espacio vuelve a estar libre.

**Acceptance Scenarios**:

1. **Given** una reserva futura fuera del plazo mínimo de cancelación, **When** el usuario la
   modifica a otro día, hora o espacio libre, **Then** el cambio queda guardado y recibe un email
   con el resumen actualizado.
2. **Given** una reserva futura fuera del plazo mínimo de cancelación, **When** el usuario la
   cancela, **Then** sigue en su lista marcada como "Cancelada", el espacio queda libre y recibe un email de cancelación.
3. **Given** una reserva dentro del plazo mínimo de cancelación (por ejemplo, faltan 2 horas y el
   plazo es 24 horas), **When** el usuario intenta modificarla o cancelarla, **Then** no se le
   permite y se le indica el plazo.

---

### User Story 5 - El administrador gestiona usuarios y roles (Priority: P2)

El administrador da de alta y edita usuarios a mano. Es el único que puede cambiar roles
(administrador, usuario, consulta) y el único que puede crear usuarios con rol consulta.

**Why this priority**: necesario para crear personal de consulta y atender casos especiales.

**Independent Test**: como administrador, crear un usuario con rol consulta, entrar con él y
comprobar que solo puede consultar.

**Acceptance Scenarios**:

1. **Given** el administrador, **When** crea un usuario con cualquier rol y sus datos,
   **Then** el usuario puede entrar con esos datos.
2. **Given** el administrador, **When** cambia el rol de un usuario, **Then** el usuario ve las
   opciones de su nuevo rol la próxima vez que entra.
3. **Given** un usuario sin rol de administrador, **When** busca cómo cambiar roles o crear
   usuarios, **Then** no tiene esas opciones.
4. **Given** que solo queda un administrador, **When** intenta quitarse su propio rol,
   **Then** no se le permite.

---

### User Story 6 - El administrador gestiona las reservas de cualquier usuario (Priority: P2)

El administrador puede crear reservas a nombre de cualquier usuario, modificarlas y eliminarlas.

**Why this priority**: cubre reservas por teléfono o en persona, y correcciones.

**Independent Test**: como administrador, crear una reserva para un usuario, comprobar que el
usuario la ve y recibe el email; después eliminarla y comprobar que el espacio queda libre.

**Acceptance Scenarios**:

1. **Given** el administrador, **When** crea una reserva para un usuario en un espacio libre,
   **Then** la reserva aparece en la lista del usuario y este recibe el email de resumen.
2. **Given** una reserva dentro del plazo mínimo de cancelación, **When** el administrador la
   modifica o elimina, **Then** se le permite, y el usuario recibe el email correspondiente.

---

### User Story 7 - El personal de consulta verifica reservas (Priority: P3)

Un usuario con rol consulta ve todas las reservas del cliente y filtra por día, por mes y por
usuario. También puede buscar una reserva por su número para comprobar que es válida.
No puede crear, modificar ni eliminar nada.

**Why this priority**: útil en el punto de acceso, pero la aplicación ya aporta valor sin ello.

**Independent Test**: con varias reservas creadas, entrar con un usuario de consulta, filtrar por
día, mes y usuario, y buscar una reserva por número.

**Acceptance Scenarios**:

1. **Given** un usuario de consulta, **When** filtra por un día, un mes o un usuario,
   **Then** ve solo las reservas que cumplen el filtro.
2. **Given** un número de reserva existente, **When** lo busca, **Then** ve el usuario, espacio,
   día, hora y si la reserva está vigente o cancelada.
3. **Given** un número de reserva inexistente, **When** lo busca,
   **Then** ve "No existe ninguna reserva con ese número".
4. **Given** un usuario de consulta, **When** mira una reserva, **Then** no tiene opciones para
   crear, modificar ni eliminar.

---

### Edge Cases

- **Franjas pasadas**: no se pueden reservar franjas de hoy cuya hora de inicio ya ha pasado.
- **Última franja del día**: una franja solo existe si termina antes del cierre. Por ejemplo, con
  horario 10:00–20:00 y duración 2 h, la última franja empieza a las 18:00.
- **Fuera de plazo**: no se puede elegir un día más allá del plazo máximo de antelación.
- **Días no permitidos**: los días que el cliente no abre no se pueden elegir.
- **Cambios de configuración con reservas existentes**: si el administrador cambia horario, días o
  duración, antes de guardar se le indica cuántas reservas futuras dejarían de encajar y debe
  confirmar. Al confirmar, esas reservas se cancelan automáticamente (sus espacios quedan libres) y
  cada usuario afectado recibe un email de cancelación que explica el motivo. Las reservas que siguen
  encajando no se tocan.
- **Eliminar un espacio o planta con reservas futuras**: no se permite; se indica cuántas reservas
  futuras tiene.
- **Fallo al enviar un email**: la reserva o el registro se guardan igualmente y se informa al
  usuario de que el email no se pudo enviar.
- **Cambio de año**: el contador es único para todas las reservas cuya fecha de reserva cae en el mismo
  año; la primera reserva con fecha de 2027 lleva `0001`, aunque se haga en 2026.
- **Números cancelados**: el número de una reserva cancelada no se reutiliza.
- **Contraseña incorrecta**: se muestra "Email o contraseña incorrectos", sin indicar cuál de los
  dos falla. A los 5 fallos seguidos se aplica el bloqueo de 15 minutos (FR-032).

## Requirements *(mandatory)*

### Functional Requirements

**Instalación y cliente**

- **FR-001**: La aplicación MUST incluir de serie una cuenta de administrador con usuario `admin`
  y contraseña `admin`.
- **FR-002**: La aplicación MUST obligar a cambiar la contraseña `admin` en el primer acceso, antes
  de permitir ninguna otra acción.
- **FR-003**: Cada instalación MUST atender a un único cliente con sus propios datos; un cliente
  distinto requiere otra instalación, con su propia dirección web.
- **FR-004**: El administrador MUST poder crear y editar el cliente con: nombre, logo (opcional),
  días de reserva (L/M/X/J/V/S/D), horario (hora de apertura y de cierre), duración de cada
  reserva (múltiplo de 15 minutos, por ejemplo 15 min, 1 h o 2 h), plazo máximo de antelación
  (en días) y plazo mínimo de cancelación (en horas).
- **FR-005**: El administrador MUST poder crear, renombrar y eliminar plantas (opcionales) y
  espacios con nombre (por ejemplo "Pista 1", "Mesa 4"), cada uno opcionalmente en una planta.
- **FR-006**: Mientras el cliente no esté configurado, la aplicación MUST mostrar a los visitantes
  "Reservas aún no disponibles" y no permitir registrarse ni reservar.
- **FR-007**: Si el cliente tiene logo, MUST verse en la esquina superior izquierda de todas las pantallas.

**Cuentas y perfil**

- **FR-008**: Los visitantes MUST poder registrarse indicando nombre, apellidos, email, teléfono y
  contraseña; el NIF es opcional. Toda cuenta registrada así tiene rol "usuario".
- **FR-009**: Tras el registro, el sistema MUST enviar un email con el resumen de los datos registrados
  (sin la contraseña).
- **FR-010**: Cada email MUST pertenecer a una sola cuenta.
- **FR-011**: El sistema MUST ofrecer "¿Olvidó su contraseña?": si el email existe, envía un enlace
  para cambiarla, válido una sola vez durante 1 hora, y muestra "Se ha enviado un email a <email>,
  compruebe su bandeja de entrada"; si no existe, muestra "No existe ninguna cuenta con ese email".
- **FR-012**: Cada usuario MUST poder ver y editar su perfil: nombre, apellidos, NIF, email y teléfono.
- **FR-031**: Toda contraseña nueva (registro, cambio, recuperación, primer acceso del administrador
  y alta manual) MUST tener al menos 8 caracteres, con al menos una letra y un número; si no, se
  muestra "La contraseña debe tener al menos 8 caracteres, una letra y un número". Como `admin` no
  cumple la regla, no puede elegirse como contraseña nueva.
- **FR-013**: Se accede con email y contraseña. La cuenta inicial usa el identificador `admin`
  hasta que el administrador guarda su email en el perfil; desde entonces entra con su email.
- **FR-032**: Tras 5 intentos fallidos seguidos de acceso a una cuenta, el sistema MUST bloquear el
  acceso a esa cuenta durante 15 minutos y mostrar "Demasiados intentos, vuelva a probar en 15
  minutos". Un acceso correcto reinicia la cuenta de fallos.

**Roles**

- **FR-014**: Existen tres roles: administrador, usuario y consulta.
- **FR-015**: Solo un administrador MUST poder crear usuarios a mano, editar sus datos, cambiar
  roles y crear usuarios de consulta.
- **FR-016**: El sistema MUST impedir quitar el rol de administrador al último administrador.

**Reservas**

- **FR-017**: El usuario MUST poder elegir en un calendario un día permitido y dentro del plazo
  máximo de antelación, ver sus franjas y elegir un espacio libre en una franja.
- **FR-018**: Los espacios ocupados MUST verse en rojo y no poder elegirse.
- **FR-019**: Cada espacio MUST admitir como máximo una reserva por franja, incluso si dos usuarios
  confirman a la vez.
- **FR-020**: Cada reserva MUST ocupar exactamente una franja.
- **FR-021**: Cada reserva MUST recibir un número con formato `dd-mm-aaaa-NNNN`, donde la fecha es
  el día de la reserva y `NNNN` es un contador común a todas las reservas de ese año (según la fecha
  de reserva) que empieza en `0001` con la primera reserva del año, aumenta de uno en uno y no se
  reutiliza.
- **FR-022**: El usuario MUST poder modificar (día, hora o espacio) y cancelar sus reservas futuras
  mientras falte más que el plazo mínimo de cancelación. Al modificarla conserva su número.
- **FR-023**: El sistema MUST enviar un email al usuario al crear, modificar y cancelar una reserva,
  con número, cliente, espacio, planta, día y hora.
- **FR-024**: El administrador MUST poder crear reservas para cualquier usuario y modificarlas o
  eliminarlas en cualquier momento, sin el límite del plazo mínimo de cancelación.
- **FR-033**: Si el administrador cambia días, horario o duración del cliente, el sistema MUST avisar
  de cuántas reservas futuras dejarían de encajar y pedir confirmación; al confirmar MUST cancelarlas
  y enviar un email de cancelación a cada usuario afectado.
- **FR-034**: El usuario MUST poder ver en su lista todas sus reservas, pasadas y futuras, vigentes y
  canceladas, con el estado de cada una; solo puede modificar o cancelar las futuras vigentes.
- **FR-025**: No hay límite de reservas por usuario.

**Consulta**

- **FR-026**: Los usuarios de consulta MUST poder ver todas las reservas del cliente, filtrar por día,
  por mes y por usuario, y buscar por número de reserva.
- **FR-027**: Los usuarios de consulta MUST NOT poder crear, modificar ni eliminar nada.

**General**

- **FR-028**: Toda la aplicación MUST estar en español de España, con fechas `dd/mm/aaaa` y horas
  de 24 h, en hora peninsular española.
- **FR-029**: Todas las pantallas MUST poder usarse en un móvil, una tableta o un ordenador.
- **FR-030**: Toda la información (cliente, usuarios, reservas) MUST conservarse aunque la
  aplicación se reinicie.

### Key Entities

- **Cliente**: el negocio que ofrece los espacios. Nombre, logo, días y horario de reserva,
  duración de la reserva, plazo máximo de antelación y plazo mínimo de cancelación. Uno por instalación.
- **Planta**: agrupación opcional de espacios (por ejemplo "Planta 1", "Terraza").
- **Espacio**: lo que se reserva (pista, cabina, mesa, puesto...). Nombre y planta opcional.
- **Franja**: intervalo de un día en que se puede reservar un espacio; sale del horario y la duración del cliente.
- **Usuario**: persona con cuenta. Nombre, apellidos, NIF (opcional), email, teléfono, contraseña y rol.
- **Reserva**: un usuario, un espacio, un día y una franja. Tiene número, estado (vigente o cancelada)
  y fecha de creación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario ya registrado completa una reserva en 4 pasos o menos (abrir calendario,
  elegir día, elegir franja y espacio, confirmar) y en menos de 1 minuto.
- **SC-002**: Un visitante nuevo se registra y hace su primera reserva en menos de 3 minutos.
- **SC-003**: Partiendo de una instalación nueva, un administrador deja el cliente configurado y
  listo para reservar en menos de 15 minutos.
- **SC-004**: En una prueba en la que dos personas confirman a la vez el mismo espacio y franja,
  solo una reserva queda guardada, en 10 de 10 intentos.
- **SC-005**: Los emails de registro, reserva, modificación, cancelación y cambio de contraseña
  llegan en menos de 2 minutos.
- **SC-006**: Una persona de consulta comprueba si un número de reserva es válido en menos de 30 segundos.
- **SC-007**: Todas las pantallas se pueden usar en un móvil sin desplazarse en horizontal.
- **SC-008**: Al menos 9 de cada 10 usuarios de prueba completan su primera reserva sin ayuda.

## Assumptions

- **Constitución**: se aplica la constitución de Reservas (v2.1.0).
- **Cuenta inicial**: `admin` / `admin` es solo el acceso de primer uso y se cambia obligatoriamente
  (principio V de la constitución).
- **Web adaptable**: la v0 es una página web que funciona en el móvil; no hay app nativa.
- **Modelo de espacios**: un espacio = una reserva por franja. Los cursos con varias plazas se
  modelan como varios espacios.
- **Plazos**: hay dos plazos distintos por cliente: máximo de antelación para reservar y mínimo
  para modificar o cancelar.
- **Número al modificar**: una reserva modificada conserva su número original, aunque cambie de día.
- **Usuarios**: no se pueden eliminar cuentas en la v0 (solo crear y editar).
- **Email**: la instalación dispone de un servicio de envío de email.
- **Requisito RF6 del borrador** ("apificar todos los recursos"): es una decisión técnica y se
  trata en el plan, no en esta spec.
- **Fuera de alcance (v0)**: pagos; plano de los espacios (anotado como idea futura); app nativa
  para iOS o Android; varios clientes en una misma instalación; reservar varias franjas seguidas;
  aforo de varias personas por espacio; límite de reservas por usuario; eliminar cuentas de usuario.
