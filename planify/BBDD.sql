-- Tabla usuarios
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    rol TEXT NOT NULL,
    primer_login INTEGER DEFAULT 1
);

-- Tabla empleados
CREATE TABLE empleados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    puesto TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla turnos
CREATE TABLE turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT NOT NULL,
    color TEXT
);

-- Tabla asignaciones
CREATE TABLE asignaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL,
    turno_id INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
    FOREIGN KEY(turno_id) REFERENCES turnos(id) ON DELETE CASCADE
);

-- Tabla solicitudes
CREATE TABLE solicitudes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    comentario TEXT,
    estado TEXT DEFAULT 'pendiente',
    FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
);
