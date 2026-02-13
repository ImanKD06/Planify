-- Crear base de datos
CREATE DATABASE planify;
USE planify;

-- Tabla usuarios
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'empleado') NOT NULL
);

-- Tabla empleados
CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    puesto VARCHAR(100),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- Tabla turnos
CREATE TABLE turnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL
);

-- Tabla asignaciones
CREATE TABLE asignaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    turno_id INT NOT NULL,
    fecha DATE NOT NULL,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        ON DELETE CASCADE,
    FOREIGN KEY (turno_id) REFERENCES turnos(id)
        ON DELETE CASCADE
);

-- Tabla solicitudes
CREATE TABLE solicitudes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    comentario TEXT,
    estado ENUM('pendiente', 'aprobada', 'rechazada') DEFAULT 'pendiente',
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        ON DELETE CASCADE
);
