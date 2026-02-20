from config import Config
from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config.from_object(Config)

# Conexión a MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=app.config["DB_HOST"],
        user=app.config["DB_USER"],
        password=app.config["DB_PASSWORD"],
        database=app.config["DB_NAME"]
    )

# ---------------- LOGIN ----------------

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()

    cursor.close()
    conn.close()

    if usuario and check_password_hash(usuario["password"], password):
        session["usuario_id"] = usuario["id"]
        session["rol"] = usuario["rol"]
        session["nombre"] = usuario["nombre"]

        if usuario["rol"] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("empleado_dashboard"))
    else:
        return "Email o contraseña incorrectos"

# ---------------- DASHBOARD ADMIN ----------------
from datetime import date, timedelta

# ---------------- ASIGNACIONES ----------------

@app.route("/admin/asignaciones", methods=["GET", "POST"])
def gestionar_asignaciones():
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ---------------- CREAR ASIGNACIÓN ----------------
    if request.method == "POST":
        empleado_id = request.form["empleado_id"]
        turno_id = request.form["turno_id"]
        fecha = request.form["fecha"]

        # Evitar duplicar turno mismo día
        cursor.execute("""
            SELECT * FROM asignaciones
            WHERE empleado_id=%s AND fecha=%s
        """, (empleado_id, fecha))

        existe = cursor.fetchone()

        if not existe:
            cursor.execute("""
                INSERT INTO asignaciones (empleado_id, turno_id, fecha)
                VALUES (%s, %s, %s)
            """, (empleado_id, turno_id, fecha))
            conn.commit()

    # ---------------- OBTENER EMPLEADOS ----------------
    cursor.execute("""
        SELECT e.id, u.nombre
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
    """)
    empleados = cursor.fetchall()

    # ---------------- OBTENER TURNOS ----------------
    cursor.execute("SELECT * FROM turnos")
    turnos = cursor.fetchall()

    # ---------------- FILTRO POR EMPLEADO ----------------
    empleado_filtro = request.args.get("empleado_id")

    # ---------------- VISTA SEMANA ACTUAL ----------------
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)

    query = """
        SELECT a.id, u.nombre, t.nombre AS turno, t.hora_inicio, t.hora_fin, a.fecha
        FROM asignaciones a
        JOIN empleados e ON a.empleado_id = e.id
        JOIN usuarios u ON e.usuario_id = u.id
        JOIN turnos t ON a.turno_id = t.id
        WHERE a.fecha BETWEEN %s AND %s
    """

    params = [inicio_semana, fin_semana]

    if empleado_filtro:
        query += " AND e.id=%s"
        params.append(empleado_filtro)

    query += " ORDER BY a.fecha ASC"

    cursor.execute(query, params)
    asignaciones = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/asignaciones.html",
        empleados=empleados,
        turnos=turnos,
        asignaciones=asignaciones,
        empleado_filtro=empleado_filtro
    )


# ---------------- ELIMINAR ASIGNACIÓN ----------------

@app.route("/admin/asignaciones/eliminar/<int:id>")
def eliminar_asignacion(id):
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM asignaciones WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("gestionar_asignaciones"))



@app.route("/admin/empleados")
def listar_empleados():
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT u.id, u.nombre, u.email, e.puesto FROM usuarios u "
                   "JOIN empleados e ON u.id = e.usuario_id WHERE u.rol='empleado'")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("admin/empleados.html", empleados=empleados)

from werkzeug.security import generate_password_hash

@app.route("/admin/empleados/crear", methods=["GET", "POST"])
def crear_empleado():
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        puesto = request.form["puesto"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nombre, email, password, rol) VALUES (%s, %s, %s, 'empleado')",
                       (nombre, email, password))
        usuario_id = cursor.lastrowid
        cursor.execute("INSERT INTO empleados (usuario_id, puesto) VALUES (%s, %s)",
                       (usuario_id, puesto))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("listar_empleados"))

    return render_template("admin/crear_empleado.html")

@app.route("/admin/empleados/editar/<int:id>", methods=["GET", "POST"])
def editar_empleado(id):
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        puesto = request.form["puesto"]

        cursor.execute("UPDATE usuarios SET nombre=%s, email=%s WHERE id=%s",
                       (nombre, email, id))
        cursor.execute("UPDATE empleados SET puesto=%s WHERE usuario_id=%s",
                       (puesto, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("listar_empleados"))

    cursor.execute("SELECT u.id, u.nombre, u.email, e.puesto FROM usuarios u "
                   "JOIN empleados e ON u.id = e.usuario_id WHERE u.id=%s", (id,))
    empleado = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("admin/crear_empleado.html", empleado=empleado)

@app.route("/admin/empleados/eliminar/<int:id>")
def eliminar_empleado(id):
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Solo eliminamos el usuario
    # El empleado se elimina automáticamente por ON DELETE CASCADE
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (id,))
    
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("listar_empleados"))

# ---------------- DASHBOARD EMPLEADO ----------------

@app.route("/empleado")
def empleado_dashboard():
    if "rol" not in session or session["rol"] != "empleado":
        return redirect(url_for("home"))

    return render_template("empleado_dashboard.html", nombre=session["nombre"])

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
