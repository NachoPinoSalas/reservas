# Reservas

Página web para reservar los espacios de un cliente (pistas, cabinas, mesas, puestos…).
Una instalación = un cliente. Especificación en [specs/001-reservas-v0/](specs/001-reservas-v0/).

## Variables de entorno

| Variable | Obligatoria | Para qué |
|----------|-------------|----------|
| `SECRET_KEY` | sí | Clave de la sesión. Una cadena larga y aleatoria, distinta en cada instalación. |
| `RESERVAS_DB` | en producción | Ruta del fichero de base de datos en el disco persistente (por ejemplo `/datos/reservas.db`). Si no se indica: `instance/reservas.db`. |
| `SMTP_SERVIDOR`, `SMTP_PUERTO` | sí, para enviar emails | Servicio de correo. Puerto 587 (STARTTLS) por defecto; 465 usa SSL. |
| `SMTP_USUARIO`, `SMTP_CLAVE` | según el servicio | Credenciales del correo. |
| `SMTP_REMITENTE` | no | Dirección que aparece como remitente (por defecto, `SMTP_USUARIO`). |
| `SMTP_TLS` | no | `0` para un servidor de pruebas sin cifrado. |
| `CORREO_MODO` | no | `smtp` (por defecto) o `consola`, que escribe los emails en el registro en lugar de enviarlos (solo para pruebas locales). |
| `COOKIE_SEGURA` | no | `0` para probar por `http://` desde otro dispositivo de la red local. En producción, no definirla (la cookie solo viaja por HTTPS). |

Nunca se escriben claves en el código: todo va en estas variables.

## Arranque local

```sh
python -m venv .venv
.venv/Scripts/activate        # Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
export SECRET_KEY=algo-largo-y-aleatorio CORREO_MODO=consola   # en PowerShell: $env:SECRET_KEY="..."
flask --app app run
```

Abrir <http://localhost:5000>. Primer acceso: usuario `admin`, contraseña `admin`; la aplicación
obliga a cambiarla y después guía la configuración del cliente.

Pruebas automáticas: `pytest`. Recorrido manual completo: [quickstart.md](specs/001-reservas-v0/quickstart.md).

## Producción

Un único servicio web Linux con disco persistente, HTTPS del propio alojamiento y las variables de
entorno de arriba. El comando de arranque está en el `Procfile`:

```sh
gunicorn "app:create_app()"
```

(Gunicorn escucha en el puerto de la variable `PORT` si el alojamiento la define.)

## Copia de seguridad

Todo (cliente, logo, usuarios y reservas) está en el fichero de `RESERVAS_DB`. Para hacer una copia
basta con copiar ese fichero (mejor con la aplicación parada, o con `sqlite3 reservas.db ".backup copia.db"`).
Para restaurar, se pone la copia en su sitio y se reinicia la aplicación.
