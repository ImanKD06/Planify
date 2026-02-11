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

@app.route("/admin")
def admin_dashboard():
    if "rol" not in session or session["rol"] != "admin":
        return redirect(url_for("home"))

    return render_template("admin_dashboard.html", nombre=session["nombre"])

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
