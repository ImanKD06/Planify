from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3, os
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta
from time import time

app = Flask(__name__)
app.secret_key = "super_secret_key"

DB_PATH = "database.db"


# ---------------- CONEXIÓN BD ----------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- CREAR TABLAS ----------------
def crear_tablas():
    if not os.path.exists(DB_PATH):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            primer_login INTEGER DEFAULT 1
        )
        """)
        cursor.execute("""
        CREATE TABLE empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            puesto TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            color TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE asignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            turno_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
            FOREIGN KEY(turno_id) REFERENCES turnos(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            comentario TEXT,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        conn.close()


# ---------------- CREAR ADMIN INICIAL ----------------
def crear_admin_inicial():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE rol='admin'")
        admin = cursor.fetchone()
        if not admin:
            password_temporal = "Admin123!"
            password_hash = generate_password_hash(password_temporal)
            cursor.execute("""
                INSERT INTO usuarios (nombre, email, password, rol, primer_login)
                VALUES (?, ?, ?, ?, 1)
            """, ("Admin", "admin@empresa.com", password_hash, "admin"))
            conn.commit()
            print("Admin inicial creado")
            print("Email: admin@empresa.com")
            print("Password:", password_temporal)
        conn.close()
    except Exception as e:
        print("ERROR crear_admin_inicial:", e)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return login()
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    try:
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash("Todos los campos son obligatorios", "error")
            return redirect(url_for("home"))
        conn = get_db_connection()
        usuario = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
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
    except Exception as e:
        print("ERROR LOGIN:", e)
        flash(f"Ocurrió un error al iniciar sesión: {e}", "error")
        return redirect(url_for("home"))


# ---------------- CAMBIAR PASSWORD ----------------
@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():
    try:
        if "usuario_id" not in session:
            return redirect(url_for("home"))
        if request.method == "POST":
            nueva = generate_password_hash(request.form["password"])
            conn = get_db_connection()
            conn.execute("UPDATE usuarios SET password=?, primer_login=0 WHERE id=?",
                         (nueva, session["usuario_id"]))
            conn.commit()
            conn.close()
            flash("Contraseña actualizada correctamente", "success")
            return redirect(url_for("home"))
        return render_template("cambiar_password.html")
    except Exception as e:
        print("ERROR cambiar_password:", e)
        flash(f"Error al cambiar contraseña: {e}", "error")
        return redirect(url_for("home"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- EJEMPLO DE DASHBOARD EMPLEADO ----------------
@app.route("/empleado")
def empleado_dashboard():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        return render_template(
            "empleado/dashboard.html",
            nombre=session["nombre"],
            time=int(time())
        )
    except Exception as e:
        print("ERROR empleado_dashboard:", e)
        flash(f"Error al cargar dashboard: {e}", "error")
        return redirect(url_for("home"))


# ---------------- INICIAR APP ----------------
if __name__ == "__main__":
    crear_tablas()
    crear_admin_inicial()
    app.run(debug=True)
