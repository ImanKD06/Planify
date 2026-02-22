from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Cambiar en producción


# ---------------- CONEXIÓN BD ----------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- CREAR ADMIN INICIAL ----------------

def crear_admin_inicial():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE rol = ?", ("admin",))
    admin = cursor.fetchone()

    if not admin:
        password_temporal = "Admin123!"
        password_hash = generate_password_hash(password_temporal)

        cursor.execute("""
            INSERT INTO usuarios (nombre, email, password, rol, primer_login)
            VALUES (?, ?, ?, ?, ?)
        """, ("Admin", "admin@empresa.com", password_hash, "admin", 1))

        conn.commit()

        print(" Admin inicial creado")
        print(" Email: admin@empresa.com")
        print(" Contraseña temporal:", password_temporal)

    conn.close()


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return login()
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario and check_password_hash(usuario["password"], password):

        session["usuario_id"] = usuario["id"]
        session["rol"] = usuario["rol"]
        session["nombre"] = usuario["nombre"]

        if usuario["primer_login"] == 1:
            return redirect(url_for("cambiar_password"))

        if usuario["rol"] == "admin":
            return redirect(url_for("listar_empleados"))
        else:
            return redirect(url_for("empleado_dashboard"))

    return "Email o contraseña incorrectos"


# ---------------- CAMBIAR PASSWORD ----------------

@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():

    if "usuario_id" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        nueva_password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE usuarios 
            SET password=?, primer_login=0 
            WHERE id=?
        """, (nueva_password, session["usuario_id"]))

        conn.commit()
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


@app.route("/admin/empleados/crear", methods=["GET", "POST"])
def crear_empleado():

    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        puesto = request.form["puesto"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO usuarios (nombre, email, password, rol, primer_login)
            VALUES (?, ?, ?, ?, 0)
        """, (nombre, email, password, "empleado"))

        usuario_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO empleados (usuario_id, puesto)
            VALUES (?, ?)
        """, (usuario_id, puesto))

        conn.commit()
        conn.close()

        return redirect(url_for("listar_empleados"))

    return render_template("admin/crear_empleado.html")

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
            WHERE id = (
                SELECT usuario_id FROM empleados WHERE id=?
            )
        """, (nombre, email, id))

        cursor.execute("""
            UPDATE empleados
            SET puesto=?
            WHERE id=?
        """, (puesto, id))

        conn.commit()
        conn.close()

        return redirect(url_for("listar_empleados"))

    # GET
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

    conn.close()

    return render_template("admin/turnos.html", turnos=turnos)


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

    # Empleados
    cursor.execute("""
        SELECT e.id, u.nombre
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
    """)
    empleados = cursor.fetchall()

    # Turnos
    cursor.execute("SELECT * FROM turnos")
    turnos = cursor.fetchall()

    # Semana actual
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

    return render_template(
        "admin/asignaciones.html",
        empleados=empleados,
        turnos=turnos,
        asignaciones=asignaciones
    )


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

    if session.get("rol") != "empleado":
        return redirect(url_for("home"))

    return render_template("empleado_dashboard.html", nombre=session["nombre"])


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    crear_admin_inicial()
    app.run(debug=True)
