# Guía de validación: Reservas v0

Se comprueba usando la aplicación, sin leer código (principio IV).

## Preparación

1. Instalar dependencias: `pip install -r requirements.txt`.
2. Definir variables de entorno: clave de sesión y datos del servicio de correo (para pruebas basta un buzón de prueba).
3. Arrancar: `flask --app app run` (local) o el comando del `Procfile` (producción).
4. Abrir la dirección en el ordenador **y** en el móvil.
5. Pruebas automáticas: `pytest`.

## Recorrido (en orden)

| # | Hacer | Debe verse | Historia / criterio |
|---|-------|-----------|---------------------|
| 1 | Abrir la app recién instalada | "Reservas aún no disponibles"; sin registro | US1-3 |
| 2 | Entrar con `admin` / `admin` | obliga a elegir contraseña nueva; `admin` no se acepta como nueva | US1-1, FR-031 |
| 3 | Volver a entrar con `admin` / `admin` | se rechaza | US1-2 |
| 4 | Completar el asistente (nombre, logo, días, 10:00–20:00, 2 h, plazos, 1 planta, 2 espacios) | logo arriba a la izquierda; calendario con franjas 10, 12, 14, 16, 18 h | US1-4, SC-003 |
| 5 | Registrar un usuario nuevo | queda dentro; llega email de resumen | US2-1 |
| 6 | Registrar el mismo email | "Ya existe una cuenta con ese email" | US2-2 |
| 7 | Cerrar sesión → "¿Olvidó su contraseña?" → usar el enlace → entrar | cambia la contraseña; el enlace usado o con más de 1 h caduca | US2-3/5 |
| 8 | Reservar: calendario → día → franja y espacio → confirmar (≤ 4 pasos, < 1 min) | número tipo `15-10-2026-0001` y email | US3-3, SC-001 |
| 9 | Con otro usuario, mirar ese día | el espacio sale en rojo | US3-4 |
| 10 | Dos personas confirman a la vez el mismo hueco | solo una lo consigue; la otra ve "Este espacio acaba de ser reservado, elija otro" | US3-5, SC-004 |
| 11 | Modificar y luego cancelar una reserva fuera del plazo mínimo | emails; sigue en la lista como "Cancelada"; el espacio queda libre | US4-1/2 |
| 12 | Intentar cancelar una reserva dentro del plazo mínimo | no se permite y se indica el plazo | US4-3 |
| 13 | Como admin: crear usuario de consulta; cambiar un rol; quitarse el único rol de admin | se crea; se aplica; no se permite | US5 |
| 14 | Como admin: crear/modificar/eliminar reserva de un usuario | el usuario la ve y recibe email | US6 |
| 15 | Como admin: cambiar la duración con reservas futuras | avisa de cuántas se cancelarán; al confirmar, emails de cancelación | FR-033 |
| 16 | Entrar como consulta: filtrar por día, mes, usuario; buscar un número válido e inexistente | resultados correctos; "No existe ninguna reserva con ese número"; sin botones de editar | US7, SC-006 |
| 17 | 5 contraseñas erróneas seguidas | "Demasiados intentos, vuelva a probar en 15 minutos" | FR-032 |
| 18 | Revisar todas las pantallas en el móvil | sin desplazamiento horizontal; fechas `dd/mm/aaaa`, 24 h | SC-007, FR-028 |
| 19 | Reiniciar la aplicación | usuarios, reservas y configuración siguen ahí | FR-030 |

Detalles de pantallas en [contracts/pantallas.md](contracts/pantallas.md) y de datos en [data-model.md](data-model.md).
