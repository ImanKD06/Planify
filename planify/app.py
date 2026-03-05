from flask import Flask, render_template, request, redirect, session, url_for, flash
import logging
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from time import time

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------------- CONEXIÓN Y BASE DE DATOS ----------------
DB_PATH = os.path.join("/opt/render/data", "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ---------------- CREAR TABLAS ----------------
def init_db():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primer_login INTEGER DEFAULT 1,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('admin','empleado'))
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            puesto TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL
        )
        """)

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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            comentario TEXT,
            estado TEXT DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente','aprobada','rechazada')),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
    finally:
        conn.close()

# ---------------- CREAR ADMIN INICIAL ----------------
def crear_admin_inicial():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE rol = 'admin'")
        if not cursor.fetchone():
            password_hash = generate_password_hash("Admin123!")
            cursor.execute("""
                INSERT INTO usuarios (nombre, email, password, rol, primer_login)
                VALUES (?, ?, ?, ?, 1)
            """, ("Admin", "admin@empresa.com", password_hash, "admin"))
            conn.commit()
            print("Admin inicial creado correctamente")
    finally:
        conn.close()

# 🔥 IMPORTANTE: ESTO SE EJECUTA SIEMPRE (también en Render con gunicorn)
os.makedirs("/opt/render/data", exist_ok=True)
init_db()
crear_admin_inicial()

# ---------------- MANEJO DE ERRORES ----------------
@app.errorhandler(500)
def internal_error(error):
    return f"Error interno del servidor: {error}", 500

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return login()
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Todos los campos son obligatorios")
        return redirect(url_for("home"))

    conn = get_db_connection()
    try:
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    if usuario and check_password_hash(usuario["password"], password):
        session.clear()
        session["usuario_id"] = usuario["id"]
        session["rol"] = usuario["rol"]
        session["nombre"] = usuario["nombre"]

        if usuario["primer_login"] == 1:
            return redirect(url_for("cambiar_password"))

        if usuario["rol"] == "admin":
            return redirect(url_for("listar_empleados"))

        return redirect(url_for("empleado_dashboard"))

    flash("Email o contraseña incorrectos", "error")
    return redirect(url_for("home"))


# ---------------- CAMBIAR CONTRASEÑA ----------------
@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():
    if "usuario_id" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        nueva_password = generate_password_hash(request.form["password"])
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios 
                SET password=?, primer_login=0 
                WHERE id=?
            """, (nueva_password, session["usuario_id"]))
            conn.commit()
        finally:
            conn.close()
        return redirect(url_for("home"))

    return render_template("cambiar_password.html")

# ---------------- EMPLEADOS (ADMIN) ----------------
@app.route("/admin/empleados")
def listar_empleados():
    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, u.nombre, u.email, e.puesto 
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
    """)
    empleados = cursor.fetchall()
    conn.close()
    return render_template("admin/empleados.html", empleados=empleados)

@app.route('/admin/empleados/crear', methods=['GET', 'POST'])
def crear_empleado():
    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        puesto = request.form['puesto']
        rol = "empleado"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        if cursor.fetchone():
            flash("Ese correo ya está registrado", "error")
            conn.close()
            return redirect(url_for('crear_empleado'))

        cursor.execute("""
            INSERT INTO usuarios (nombre, email, password, rol, primer_login)
            VALUES (?, ?, ?, ?, 1)
        """, (nombre, email, password, rol))
        usuario_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO empleados (usuario_id, puesto)
            VALUES (?, ?)
        """, (usuario_id, puesto))
        conn.commit()
        conn.close()
        flash("Empleado creado correctamente", "success")
        return redirect(url_for('listar_empleados'))

    return render_template('admin/crear_empleado.html')

@app.route("/admin/empleados/editar/<int:id>", methods=["GET", "POST"])
def editar_empleado(id):
    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        puesto = request.form["puesto"]

        cursor.execute("""
            UPDATE usuarios
            SET nombre=?, email=?
            WHERE id = (SELECT usuario_id FROM empleados WHERE id=?)
        """, (nombre, email, id))

        cursor.execute("""
            UPDATE empleados
            SET puesto=?
            WHERE id=?
        """, (puesto, id))

        conn.commit()
        conn.close()
        return redirect(url_for("listar_empleados"))

    cursor.execute("""
        SELECT e.id, u.nombre, u.email, e.puesto
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.id=?
    """, (id,))
    empleado = cursor.fetchone()
    conn.close()
    return render_template("admin/editar_empleado.html", empleado=empleado)

@app.route("/admin/empleados/eliminar/<int:id>")
def eliminar_empleado(id):
    if session.get("rol") != "admin":
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM empleados WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_empleados"))

# ---------------- TURNOS ----------------
@app.route("/admin/turnos", methods=["GET", "POST"])
def gestionar_turnos():
    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        nombre = request.form["nombre"]
        hora_inicio = request.form["hora_inicio"]
        hora_fin = request.form["hora_fin"]
        cursor.execute("""
            INSERT INTO turnos (nombre, hora_inicio, hora_fin)
            VALUES (?, ?, ?)
        """, (nombre, hora_inicio, hora_fin))
        conn.commit()

    cursor.execute("SELECT * FROM turnos")
    turnos = cursor.fetchall()
    turnos_con_empleados = []
    for t in turnos:
        cursor.execute("""
            SELECT COUNT(a.id) AS total_empleados
            FROM asignaciones a
            JOIN empleados e ON a.empleado_id = e.id
            WHERE a.turno_id = ?
        """, (t["id"],))
        count = cursor.fetchone()["total_empleados"]
        turnos_con_empleados.append({
            "id": t["id"],
            "nombre": t["nombre"],
            "hora_inicio": t["hora_inicio"],
            "hora_fin": t["hora_fin"],
            "total_empleados": count
        })
    conn.close()
    return render_template("admin/turnos.html", turnos=turnos_con_empleados)

@app.route("/admin/turnos/eliminar/<int:id>")
def eliminar_turno(id):
    if session.get("rol") != "admin":
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM turnos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("gestionar_turnos"))

# ---------------- ASIGNACIONES ----------------
@app.route("/admin/asignaciones", methods=["GET", "POST"])
def gestionar_asignaciones():
    if session.get("rol") != "admin":
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        empleado_id = request.form["empleado_id"]
        turno_id = request.form["turno_id"]
        fecha = request.form["fecha"]
        cursor.execute("""
            SELECT * FROM asignaciones
            WHERE empleado_id=? AND fecha=?
        """, (empleado_id, fecha))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO asignaciones (empleado_id, turno_id, fecha)
                VALUES (?, ?, ?)
            """, (empleado_id, turno_id, fecha))
            conn.commit()

    cursor.execute("""
        SELECT e.id, u.nombre
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
    """)
    empleados = cursor.fetchall()
    cursor.execute("SELECT * FROM turnos")
    turnos = cursor.fetchall()
    hoy = date.today()
    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)
    cursor.execute("""
        SELECT a.id, u.nombre, t.nombre AS turno, t.hora_inicio, t.hora_fin, a.fecha
        FROM asignaciones a
        JOIN empleados e ON a.empleado_id = e.id
        JOIN usuarios u ON e.usuario_id = u.id
        JOIN turnos t ON a.turno_id = t.id
        WHERE a.fecha BETWEEN ? AND ?
        ORDER BY a.fecha ASC
    """, (inicio.isoformat(), fin.isoformat()))
    asignaciones = cursor.fetchall()
    conn.close()
    return render_template("admin/asignaciones.html",
                           empleados=empleados,
                           turnos=turnos,
                           asignaciones=asignaciones)

@app.route("/admin/asignaciones/eliminar/<int:id>")
def eliminar_asignacion(id):
    if session.get("rol") != "admin":
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM asignaciones WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("gestionar_asignaciones"))

# ---------------- DASHBOARD EMPLEADO ----------------
@app.route("/empleado")
def empleado_dashboard():
    if "usuario_id" not in session or session.get("rol") != "empleado":
        return redirect(url_for("home"))
    return render_template("empleado/dashboard.html", nombre=session["nombre"])

# ---------------- TURNOS EMPLEADO ----------------
@app.route("/empleado/turnos")
def empleado_turnos():
    if "usuario_id" not in session or session.get("rol") != "empleado":
        return redirect(url_for("home"))

    hoy = date.today()
    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    if desde:
        inicio = date.fromisoformat(desde)
    if hasta:
        fin = date.fromisoformat(hasta)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM empleados WHERE usuario_id = ?", (session["usuario_id"],))
    emp = cursor.fetchone()
    if emp is None:
        asignaciones = []
    else:
        empleado_id = emp["id"]
        cursor.execute("""
            SELECT t.nombre AS turno, t.hora_inicio, t.hora_fin, a.fecha
            FROM asignaciones a
            JOIN turnos t ON a.turno_id = t.id
            WHERE a.empleado_id = ? AND a.fecha BETWEEN ? AND ?
            ORDER BY a.fecha ASC
        """, (empleado_id, inicio.isoformat(), fin.isoformat()))
        asignaciones = cursor.fetchall()
    conn.close()
    return render_template('empleado/turnos.html', nombre=session['nombre'],
                           inicio=inicio, fin=fin, asignaciones=asignaciones, time=int(time()))

# ---------------- SOLICITUDES EMPLEADO ----------------
@app.route("/empleado/solicitudes", methods=["GET", "POST"])
def empleado_solicitudes():
    if "usuario_id" not in session or session.get("rol") != "empleado":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM empleados WHERE usuario_id = ?", (session["usuario_id"],))
    emp = cursor.fetchone()
    if emp is None:
        conn.close()
        return redirect(url_for("logout"))
    empleado_id = emp["id"]

    if request.method == "POST":
        tipo = request.form.get("tipo")
        comentario = request.form.get("comentario")
        cursor.execute("""
            INSERT INTO solicitudes (empleado_id, tipo, comentario)
            VALUES (?, ?, ?)
        """, (empleado_id, tipo, comentario))
        conn.commit()
        flash("Solicitud enviada", "success")

    cursor.execute("""
        SELECT tipo, comentario, estado 
        FROM solicitudes 
        WHERE empleado_id = ? ORDER BY id DESC
    """, (empleado_id,))
    solicitudes = cursor.fetchall()
    conn.close()
    return render_template("empleado/solicitudes.html", solicitudes=solicitudes)

# ---------------- PERFIL EMPLEADO ----------------
@app.route("/empleado/perfil", methods=["GET", "POST"])
def empleado_perfil():
    if "usuario_id" not in session or session.get("rol") != "empleado":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, email FROM usuarios WHERE id = ?", (session["usuario_id"],))
    usuario = cursor.fetchone()
    cursor.execute("SELECT puesto FROM empleados WHERE usuario_id = ?", (session["usuario_id"],))
    empleado = cursor.fetchone()
    if usuario is None:
        conn.close()
        return redirect(url_for("logout"))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        cursor.execute("UPDATE usuarios SET nombre=? WHERE id=?", (nombre, session["usuario_id"]))
        conn.commit()
        session["nombre"] = nombre
        flash("Perfil actualizado", "success")

    conn.close()
    return render_template("empleado/perfil.html", usuario=usuario, empleado=empleado)

# ---------------- CAMBIAR CONTRASEÑA EMPLEADO ----------------
@app.route("/empleado/cambiar-password", methods=["GET", "POST"])
def empleado_cambiar_password():
    if "usuario_id" not in session or session.get("rol") != "empleado":
        return redirect(url_for("home"))

    if request.method == "POST":
        p1 = request.form.get("password")
        p2 = request.form.get("confirm")
        if p1 != p2:
            flash("Las contraseñas no coinciden", "error")
            return redirect(url_for("empleado_cambiar_password"))
        nueva = generate_password_hash(p1)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET password=?, primer_login=0 WHERE id=?", (nueva, session["usuario_id"]))
        conn.commit()
        conn.close()
        flash("Contraseña actualizada", "success")
        return redirect(url_for("empleado_dashboard"))

    return render_template("empleado/cambiar_password.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


