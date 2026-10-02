-- Tablas de Reservas v0 (ver specs/001-reservas-v0/data-model.md).
-- Fechas como 'aaaa-mm-dd' y horas como 'hh:mm', siempre en hora de Madrid.

-- Una sola fila por instalación (FR-003). Días: 0 = lunes ... 6 = domingo.
CREATE TABLE IF NOT EXISTS cliente (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nombre TEXT NOT NULL DEFAULT '',
    logo BLOB,
    logo_tipo TEXT,
    dias TEXT NOT NULL DEFAULT '0,1,2,3,4',
    apertura TEXT NOT NULL DEFAULT '10:00',
    cierre TEXT NOT NULL DEFAULT '20:00',
    duracion_min INTEGER NOT NULL DEFAULT 60,
    antelacion_max_dias INTEGER NOT NULL DEFAULT 30,
    cancelacion_min_horas INTEGER NOT NULL DEFAULT 24,
    configurado INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS planta (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
);

-- Un espacio borrado se marca como eliminado para no perder el historial de sus reservas.
CREATE TABLE IF NOT EXISTS espacio (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    planta_id INTEGER REFERENCES planta (id) ON DELETE SET NULL,
    eliminado INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY,
    identificador TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre TEXT NOT NULL DEFAULT '',
    apellidos TEXT NOT NULL DEFAULT '',
    nif TEXT NOT NULL DEFAULT '',
    telefono TEXT NOT NULL DEFAULT '',
    clave_cifrada TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('administrador', 'usuario', 'consulta')),
    debe_cambiar_clave INTEGER NOT NULL DEFAULT 0,
    fallos_acceso INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT
);

-- Solo se guarda la huella del enlace, nunca el enlace (FR-011).
CREATE TABLE IF NOT EXISTS enlace_recuperacion (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario (id),
    huella TEXT NOT NULL UNIQUE,
    caduca_en TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reserva (
    id INTEGER PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    usuario_id INTEGER NOT NULL REFERENCES usuario (id),
    espacio_id INTEGER NOT NULL REFERENCES espacio (id),
    dia TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'vigente' CHECK (estado IN ('vigente', 'cancelada')),
    creada_en TEXT NOT NULL
);

-- Garantía de no duplicados (FR-019): un espacio, un día y una hora solo admiten una reserva vigente.
CREATE UNIQUE INDEX IF NOT EXISTS reserva_unica_vigente
    ON reserva (espacio_id, dia, hora_inicio) WHERE estado = 'vigente';

CREATE INDEX IF NOT EXISTS reserva_por_usuario ON reserva (usuario_id);
CREATE INDEX IF NOT EXISTS reserva_por_dia ON reserva (dia);

-- Contador anual del número de reserva (FR-021).
CREATE TABLE IF NOT EXISTS contador_reservas (
    anio INTEGER PRIMARY KEY,
    ultimo INTEGER NOT NULL
);
