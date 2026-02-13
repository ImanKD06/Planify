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
    cursor.execute("DELETE FROM empleados WHERE usuario_id=%s", (id,))
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("listar_empleados"))

# ---------------- DASHBOARD EMPLEADO ----------------

@app.route("/empleado")
def empleado_dashboard():
    if "rol" not in session or session[" rol"] != "empleado":
        return redirect(url_for("home"))

    return render_template("empleado_dashboard.html", nombre=session["nombre"])

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
