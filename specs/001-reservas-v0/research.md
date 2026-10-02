# Research y decisiones: Reservas v0

No quedaban "NEEDS CLARIFICATION" en el contexto técnico. Estas son las decisiones importantes,
explicadas en lenguaje de negocio. Criterio general: lo más simple que cumpla la spec (constitución, principio I).

## D-01 · Una sola aplicación web que muestra páginas completas

- **Decisión**: Python + Flask; las páginas se generan en el servidor y se adaptan al tamaño de pantalla con un único CSS.
- **Qué significa para el negocio**: se construye y se publica una sola cosa, no dos (una "web" y un "motor" por detrás). Menos piezas = menos fallos y salida más rápida. Funciona en móvil, tableta y ordenador sin app que instalar (FR-029).
- **Alternativas descartadas**: una web interactiva moderna con servidor aparte (el doble de trabajo y de cosas que mantener, sin que la spec lo pida); app nativa (fuera de alcance).

## D-02 · No se construye una API pública en la v1 (RF6 del borrador)

- **Decisión**: no se ofrece ninguna "puerta de datos" para otros programas. Las direcciones de la web se organizan por recurso (espacios, reservas, usuarios), así que añadirla más adelante es fácil.
- **Qué significa para el negocio**: se ahorra una parte importante del trabajo y de la seguridad a revisar. Nada de la spec la necesita hoy (la spec dice que se decide en el plan). Si más adelante se quiere integrar con otro sistema, se añade a la spec primero (principio III).
- **Alternativa descartada**: API completa desde el inicio "por si acaso" (viola el principio I).

## D-03 · Base de datos de un solo fichero (SQLite)

- **Decisión**: SQLite en un disco persistente del servicio.
- **Qué significa para el negocio**: no hay que contratar ni administrar un servidor de base de datos aparte; copiar el negocio entero = copiar un fichero (FR-030: los datos sobreviven a reinicios). Es más que suficiente para un cliente con decenas de espacios.
- **Alternativa descartada**: PostgreSQL (coste y mantenimiento extra sin necesidad con 1 cliente por instalación, FR-003). Si algún día hiciera falta, es un cambio acotado.

## D-04 · Imposible reservar dos veces lo mismo, garantizado por la propia base de datos

- **Decisión**: una regla en la base de datos impide que existan dos reservas vigentes del mismo espacio, día y hora. Si dos personas confirman a la vez, la base de datos deja pasar a una y rechaza a la otra, que ve "Este espacio acaba de ser reservado, elija otro" (FR-019, SC-004).
- **Qué significa para el negocio**: la garantía no depende de que el código "se acuerde" de comprobarlo; no hay forma de saltársela.

## D-05 · Las franjas no se guardan, se calculan

- **Decisión**: las franjas salen siempre de apertura, cierre y duración del cliente; solo se guarda la reserva (día + hora de inicio).
- **Qué significa para el negocio**: cambiar el horario se refleja al momento (US1-5) y no hay franjas "viejas" que limpiar. Al guardar un cambio que descuadra reservas futuras, se cuentan, se pide confirmación y se cancelan con email (FR-033).

## D-06 · Número de reserva con contador anual dentro de la misma operación

- **Decisión**: una pequeña tabla guarda el último número de cada año; se incrementa en la misma operación que crea la reserva, de forma que nunca se repite ni se salta por error (FR-021). Las canceladas conservan su número.
- **Alternativa descartada**: calcularlo contando reservas existentes (podría repetir números si se borra algo o hay concurrencia).

## D-07 · Contraseñas, bloqueo y recuperación

- **Decisión**: las contraseñas se guardan cifradas (no reversibles); los fallos de acceso y el bloqueo de 15 min se guardan en la propia cuenta (FR-032); el enlace de recuperación es de un solo uso, caduca a 1 hora y solo se guarda su huella (FR-011).
- **Qué significa para el negocio**: ni el equipo técnico puede ver una contraseña; un enlace robado de un email antiguo no sirve.
- **Primer acceso**: la cuenta `admin` nace con una marca "debe cambiar contraseña"; mientras la tenga, ninguna otra pantalla responde (FR-001/002). Como `admin` no cumple las reglas de contraseña (FR-031), no puede volver a elegirse.

## D-08 · Emails por SMTP estándar, sin servicio especial

- **Decisión**: se envían con el correo estándar de Python hacia el servicio de email que ya tiene la instalación (supuesto de la spec). Usuario y clave del correo van en variables de entorno, no en el código (principio V). El envío se hace al momento de la acción; si falla, la reserva/registro se guarda igual y se avisa (spec, casos límite).
- **Alternativa descartada**: cola de envíos en segundo plano (más piezas; con el volumen previsto, SC-005 de 2 minutos se cumple de sobra).

## D-09 · Idioma y hora

- **Decisión**: textos en español de España escritos directamente en las páginas (sin sistema de traducciones, solo hay un idioma); fechas `dd/mm/aaaa`, 24 h; todo en hora de Madrid, que incluye el cambio de hora de verano.
- **Alternativa descartada**: sistema multi-idioma (la spec solo pide español).

## D-10 · Logo

- **Decisión**: el logo se guarda en la base de datos (tamaño limitado, formatos PNG/JPG).
- **Qué significa para el negocio**: una sola cosa que copiar y restaurar; no hay carpeta de ficheros aparte que se pueda perder.

## D-11 · Publicación

- **Decisión**: un único servicio web con un disco persistente y variables de entorno (clave de sesión, datos del correo), arrancado con Gunicorn. Dirección web propia por cliente (FR-003), con HTTPS que da el propio alojamiento.
- **Qué significa para el negocio**: se puede publicar el mismo día en cualquier alojamiento sencillo que ofrezca disco persistente. No se fija proveedor aquí; es una decisión de coste a tomar con el cliente.
- **Copias de seguridad**: copia periódica del fichero de base de datos (la hace el proveedor o una copia manual); no se construye nada propio.

## D-12 · Seguridad mínima imprescindible (no es alcance extra)

- Formularios con protección contra envíos falsos (token CSRF de Flask, con una función ligera) y sesión en cookie firmada y solo por HTTPS.
- Cada pantalla comprueba el rol (administrador / usuario / consulta) en el servidor, no solo ocultando botones (FR-015, FR-027).
- Mensaje de acceso incorrecto genérico (spec).
