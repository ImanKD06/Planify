import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # ---------------- TABLA USUARIOS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        primer_login INTEGER DEFAULT 1,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        rol TEXT NOT NULL CHECK (rol IN ('admin', 'empleado'))
    )
    """)

    # ---------------- TABLA EMPLEADOS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL UNIQUE,
        puesto TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    )
    """)

    # ---------------- TABLA TURNOS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fin TEXT NOT NULL
    )
    """)

    # ---------------- TABLA ASIGNACIONES ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asignaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER NOT NULL,
        turno_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
        FOREIGN KEY (turno_id) REFERENCES turnos(id) ON DELETE CASCADE
    )
    """)

    # ---------------- TABLA SOLICITUDES ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solicitudes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        comentario TEXT,
        estado TEXT DEFAULT 'pendiente'
            CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
        FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    print(" Base de datos SQLite creada correctamente.")

if __name__ == "__main__":

    init_db()