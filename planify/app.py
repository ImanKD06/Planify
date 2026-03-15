from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3, os, logging, traceback
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta
from time import time

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(funcName)s - %(message)s",
    handlers=[logging.StreamHandler()]  # StreamHandler → stdout → Render logs
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "super_secret_key"

DB_PATH = "database.db"


# ---------------- CONEXIÓN BD ----------------
def get_db_connection():
    logger.debug("Abriendo conexión a la base de datos: %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- CREAR TABLAS ----------------
def crear_tablas():
    if not os.path.exists(DB_PATH):
        logger.info("Base de datos no encontrada. Creando tablas...")
        try:
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
            logger.info("Tablas creadas correctamente.")
        except Exception as e:
            logger.error("ERROR al crear tablas: %s", e)
            logger.debug(traceback.format_exc())
    else:
        logger.info("Base de datos existente encontrada: %s", DB_PATH)


# ---------------- CREAR ADMIN INICIAL ----------------
def crear_admin_inicial():
    logger.info("Verificando si existe admin inicial...")
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
            logger.info("Admin inicial creado → email: admin@empresa.com | password: %s", password_temporal)
        else:
            logger.info("Admin ya existe, no se crea uno nuevo.")
        conn.close()
    except Exception as e:
        logger.error("ERROR en crear_admin_inicial: %s", e)
        logger.debug(traceback.format_exc())


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return login()
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    logger.info("Intento de login desde IP: %s", request.remote_addr)
    try:
        email = request.form.get("email")
        password = request.form.get("password")

        logger.debug("Email recibido: %s", email)

        if not email or not password:
            logger.warning("Login fallido: campos vacíos.")
            flash("Todos los campos son obligatorios", "error")
            return redirect(url_for("home"))

        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email=?",
            (email,)
        ).fetchone()
        conn.close()

        if usuario is None:
            logger.warning("Login fallido: email no encontrado → %s", email)
            flash("Email o contraseña incorrectos", "error")
            return redirect(url_for("home"))

        if check_password_hash(usuario["password"], password):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["rol"] = usuario["rol"]
            session["nombre"] = usuario["nombre"]
            logger.info("Login exitoso → usuario_id=%s rol=%s nombre=%s", usuario["id"], usuario["rol"], usuario["nombre"])

            if usuario["primer_login"] == 1:
                logger.info("Primer login detectado, redirigiendo a cambiar_password.")
                return redirect(url_for("cambiar_password"))

            if usuario["rol"] == "admin":
                return redirect(url_for("listar_empleados"))

            return redirect(url_for("empleado_dashboard"))

        logger.warning("Login fallido: contraseña incorrecta para email → %s", email)
        flash("Email o contraseña incorrectos", "error")
        return redirect(url_for("home"))

    except Exception as e:
        logger.error("ERROR en login: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error interno al iniciar sesión: {e}", "error")
        return redirect(url_for("home"))


# ---------------- CAMBIAR PASSWORD ----------------
@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():
    logger.debug("Acceso a cambiar_password | método: %s", request.method)
    try:
        if "usuario_id" not in session:
            logger.warning("Acceso no autorizado a cambiar_password (sin sesión).")
            return redirect(url_for("home"))

        if request.method == "POST":
            nueva_password = request.form.get("password")
            if not nueva_password:
                logger.warning("cambiar_password: campo password vacío.")
                flash("La contraseña no puede estar vacía", "error")
                return redirect(url_for("cambiar_password"))

            nueva = generate_password_hash(nueva_password)
            conn = get_db_connection()
            conn.execute("UPDATE usuarios SET password=?, primer_login=0 WHERE id=?",
                         (nueva, session["usuario_id"]))
            conn.commit()
            conn.close()
            logger.info("Contraseña actualizada para usuario_id=%s", session["usuario_id"])
            flash("Contraseña actualizada correctamente", "success")
            return redirect(url_for("home"))

        return render_template("cambiar_password.html")

    except Exception as e:
        logger.error("ERROR en cambiar_password: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error al cambiar contraseña: {e}", "error")
        return redirect(url_for("home"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    usuario_id = session.get("usuario_id", "desconocido")
    session.clear()
    logger.info("Logout → usuario_id=%s", usuario_id)
    return redirect(url_for("home"))


# ---------------- DASHBOARD EMPLEADO ----------------
@app.route("/empleado")
def empleado_dashboard():
    logger.debug("Acceso a empleado_dashboard | usuario_id=%s", session.get("usuario_id"))
    try:
        if session.get("rol") != "empleado":
            logger.warning("Acceso denegado a empleado_dashboard | rol=%s", session.get("rol"))
            return redirect(url_for("home"))

        return render_template(
            "empleado/dashboard.html",
            nombre=session["nombre"],
            time=int(time())
        )
    except Exception as e:
        logger.error("ERROR en empleado_dashboard: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error al cargar dashboard: {e}", "error")
        return redirect(url_for("home"))


# ---------------- MANEJADOR DE ERRORES GLOBAL ----------------
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error("Excepción no controlada: %s", e)
    logger.debug(traceback.format_exc())
    flash(f"Error inesperado: {e}", "error")
    return redirect(url_for("home"))

@app.errorhandler(404)
def not_found(e):
    logger.warning("404 - Ruta no encontrada: %s", request.url)
    return render_template("login.html"), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error("500 - Error interno del servidor: %s", e)
    logger.debug(traceback.format_exc())
    return render_template("login.html"), 500


# ---------------- INICIAR APP ----------------
if __name__ == "__main__":
    logger.info("Iniciando aplicación Flask...")
    crear_tablas()
    crear_admin_inicial()
    app.run(debug=True)
