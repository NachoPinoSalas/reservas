# Contrato de pantallas: Reservas v0

La aplicación no ofrece API para otros programas (research.md, D-02). Su "interfaz" son estas
pantallas. Todas usables en móvil (columna única, botones grandes, sin scroll horizontal).

| Pantalla | Quién | Qué hace | Spec |
|----------|-------|----------|------|
| Aviso "Reservas aún no disponibles" | visitante | se muestra mientras el cliente no esté configurado | FR-006 |
| Entrar | visitante | email + contraseña; enlace a registro y a "¿Olvidó su contraseña?" | FR-013, FR-032 |
| Registrarse | visitante | nombre, apellidos, email, teléfono, contraseña (NIF opcional) | FR-008 |
| ¿Olvidó su contraseña? / Nueva contraseña | visitante | pide email; el enlace del email abre la pantalla de cambio | FR-011 |
| Cambiar contraseña obligatoria | admin (primer acceso) | bloquea el resto de pantallas hasta cambiarla | FR-002 |
| Mi perfil | usuario, admin | ver/editar nombre, apellidos, NIF, email, teléfono | FR-012 |
| Calendario | usuario, admin | elegir día permitido → ver franjas y espacios (ocupados en rojo) → confirmar | FR-017/018 |
| Mis reservas | usuario | todo el historial, con estado; modificar/cancelar las futuras vigentes | FR-022, FR-034 |
| Asistente del cliente | admin | nombre, logo, días, horario, duración, plazos, plantas y espacios; aviso con nº de reservas afectadas antes de guardar | FR-004/005/033 |
| Usuarios | admin | alta manual, edición, cambio de rol | FR-015/016 |
| Reservas (gestión) | admin | crear/modificar/eliminar reservas de cualquier usuario | FR-024 |
| Consulta | consulta, admin | lista de todas las reservas con filtros día/mes/usuario y búsqueda por número; solo lectura | FR-026/027 |

Elementos comunes: logo del cliente arriba a la izquierda (FR-007); menú que muestra solo lo permitido por el rol (y el servidor lo comprueba además); mensajes exactos de la spec.

## Emails (contrato)

| Cuándo | Contenido | Spec |
|--------|-----------|------|
| Registro | resumen de datos (sin contraseña) | FR-009 |
| Recuperar contraseña | enlace de un solo uso, 1 h | FR-011 |
| Reserva creada / modificada / cancelada | número, cliente, espacio, planta, día y hora (y motivo si la cancela un cambio de configuración) | FR-023, FR-033 |
