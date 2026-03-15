from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3, os, logging, traceback
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta
from time import time

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(funcName)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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
# ⚠️ ESTO FALTABA — sin esto Render falla en el primer request

def crear_tablas():
    logger.info("Verificando/creando tablas...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            primer_login INTEGER DEFAULT 1
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            puesto TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            color TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS asignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            turno_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
            FOREIGN KEY(turno_id) REFERENCES turnos(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            comentario TEXT,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        # ⚠️ TABLA QUE FALTABA — usada en admin_vacaciones y calendario_eventos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY(empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        conn.close()
        logger.info("Tablas listas.")
    except Exception as e:
        logger.error("ERROR al crear tablas: %s", e)
        logger.debug(traceback.format_exc())


# ---------------- CREAR ADMIN INICIAL ----------------

def crear_admin_inicial():
    logger.info("Verificando admin inicial...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE rol='admin'")
        admin = cursor.fetchone()
        if not admin:
            password_temporal = "Admin123!"
            password_hash = generate_password_hash(password_temporal)
            cursor.execute("""
                INSERT INTO usuarios (nombre,email,password,rol,primer_login)
                VALUES (?,?,?,?,1)
            """, ("Admin", "admin@empresa.com", password_hash, "admin"))
            conn.commit()
            logger.info("Admin creado → admin@empresa.com / %s", password_temporal)
        else:
            logger.info("Admin ya existe.")
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

        if not email or not password:
            flash("Todos los campos son obligatorios", "error")
            return redirect(url_for("home"))

        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["password"], password):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["rol"] = usuario["rol"]
            session["nombre"] = usuario["nombre"]
            logger.info("Login OK → id=%s rol=%s", usuario["id"], usuario["rol"])

            if usuario["primer_login"] == 1:
                return redirect(url_for("cambiar_password"))
            if usuario["rol"] == "admin":
                return redirect(url_for("listar_empleados"))
            return redirect(url_for("empleado_dashboard"))

        logger.warning("Login fallido para email: %s", email)
        flash("Email o contraseña incorrectos", "error")
        return redirect(url_for("home"))

    except Exception as e:
        logger.error("ERROR en login: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error interno: {e}", "error")
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
            logger.info("Password cambiado para usuario_id=%s", session["usuario_id"])
            return redirect(url_for("home"))
        return render_template("cambiar_password.html")
    except Exception as e:
        logger.error("ERROR en cambiar_password: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


# ---------------- EMPLEADOS ----------------

@app.route("/admin/empleados")
def listar_empleados():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        empleados = conn.execute("""
            SELECT e.id, u.nombre, u.email, e.puesto
            FROM empleados e
            JOIN usuarios u ON e.usuario_id=u.id
        """).fetchall()
        conn.close()
        return render_template("admin/empleados.html", empleados=empleados)
    except Exception as e:
        logger.error("ERROR en listar_empleados: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


@app.route("/admin/empleados/crear", methods=["GET", "POST"])
def crear_empleado():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        if request.method == "POST":
            nombre = request.form["nombre"]
            email = request.form["email"]
            puesto = request.form["puesto"]
            password = generate_password_hash(request.form["password"])
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE email=?", (email,))
            if cursor.fetchone():
                flash("Ese correo ya existe", "error")
                return redirect(url_for("crear_empleado"))
            cursor.execute("""
                INSERT INTO usuarios (nombre,email,password,rol,primer_login)
                VALUES (?,?,?,?,1)
            """, (nombre, email, password, "empleado"))
            usuario_id = cursor.lastrowid
            cursor.execute("INSERT INTO empleados (usuario_id,puesto) VALUES (?,?)",
                           (usuario_id, puesto))
            conn.commit()
            conn.close()
            flash("Empleado creado", "success")
            return redirect(url_for("listar_empleados"))
        return render_template("admin/crear_empleado.html")
    except Exception as e:
        logger.error("ERROR en crear_empleado: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("listar_empleados"))


@app.route("/admin/empleados/editar/<int:id>", methods=["GET", "POST"])
def editar_empleado(id):
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == "POST":
            nombre = request.form["nombre"]
            email = request.form["email"]
            puesto = request.form["puesto"]
            cursor.execute("""
                UPDATE usuarios SET nombre=?, email=?
                WHERE id = (SELECT usuario_id FROM empleados WHERE id=?)
            """, (nombre, email, id))
            cursor.execute("UPDATE empleados SET puesto=? WHERE id=?", (puesto, id))
            conn.commit()
            conn.close()
            return redirect(url_for("listar_empleados"))
        cursor.execute("""
            SELECT e.id, u.nombre, u.email, e.puesto
            FROM empleados e JOIN usuarios u ON e.usuario_id=u.id
            WHERE e.id=?
        """, (id,))
        empleado = cursor.fetchone()
        conn.close()
        return render_template("admin/editar_empleado.html", empleado=empleado)
    except Exception as e:
        logger.error("ERROR en editar_empleado: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("listar_empleados"))


@app.route("/admin/empleados/eliminar/<int:id>")
def eliminar_empleado(id):
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        conn.execute("DELETE FROM empleados WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_empleados"))
    except Exception as e:
        logger.error("ERROR en eliminar_empleado: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("listar_empleados"))


# ---------------- TURNOS ----------------

@app.route("/admin/turnos", methods=["GET", "POST"])
def gestionar_turnos():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == "POST":
            nombre = request.form["nombre"]
            hora_inicio = request.form["hora_inicio"]
            hora_fin = request.form["hora_fin"]
            color = request.form.get("color", "#3788d8")
            tipo = request.form["tipo"]
            cursor.execute("""
                INSERT INTO turnos (nombre,hora_inicio,hora_fin,color)
                VALUES (?,?,?,?)
            """, (nombre + " (" + tipo + ")", hora_inicio, hora_fin, color))
            conn.commit()
        turnos = cursor.execute("SELECT * FROM turnos").fetchall()
        conn.close()
        return render_template("admin/turnos.html", turnos=turnos)
    except Exception as e:
        logger.error("ERROR en gestionar_turnos: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


@app.route("/admin/turnos/eliminar/<int:id>", methods=["POST"])
def eliminar_turno(id):
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        conn.execute("DELETE FROM turnos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return redirect(url_for("gestionar_turnos"))
    except Exception as e:
        logger.error("ERROR en eliminar_turno: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("gestionar_turnos"))


# ---------------- ASIGNACIONES ----------------

@app.route("/admin/asignaciones", methods=["GET", "POST"])
def gestionar_asignaciones():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == "POST":
            empleado_id = request.form["empleado_id"]
            turno_id = request.form["turno_id"]
            inicio = date.fromisoformat(request.form["fecha_inicio"])
            fin = date.fromisoformat(request.form["fecha_fin"])
            while inicio <= fin:
                cursor.execute("""
                    SELECT * FROM asignaciones WHERE empleado_id=? AND fecha=?
                """, (empleado_id, inicio.isoformat()))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO asignaciones (empleado_id,turno_id,fecha)
                        VALUES (?,?,?)
                    """, (empleado_id, turno_id, inicio.isoformat()))
                inicio += timedelta(days=1)
            conn.commit()
        cursor.execute("""
            SELECT e.id, u.nombre FROM empleados e
            JOIN usuarios u ON e.usuario_id=u.id
        """)
        empleados = cursor.fetchall()
        cursor.execute("SELECT * FROM turnos")
        turnos = cursor.fetchall()
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        cursor.execute("""
            SELECT a.id, u.nombre, t.nombre AS turno, t.hora_inicio, t.hora_fin, a.fecha
            FROM asignaciones a
            JOIN empleados e ON a.empleado_id=e.id
            JOIN usuarios u ON e.usuario_id=u.id
            JOIN turnos t ON a.turno_id=t.id
            WHERE a.fecha BETWEEN ? AND ?
            ORDER BY a.fecha ASC
        """, (inicio_semana.isoformat(), fin_semana.isoformat()))
        asignaciones = cursor.fetchall()
        conn.close()
        return render_template("admin/asignaciones.html",
                               empleados=empleados, turnos=turnos, asignaciones=asignaciones)
    except Exception as e:
        logger.error("ERROR en gestionar_asignaciones: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


@app.route("/admin/asignaciones/eliminar/<int:id>")
def eliminar_asignacion(id):
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        conn.execute("DELETE FROM asignaciones WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return redirect(url_for("gestionar_asignaciones"))
    except Exception as e:
        logger.error("ERROR en eliminar_asignacion: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("gestionar_asignaciones"))


# ---------------- SOLICITUDES ADMIN ----------------

@app.route("/admin/solicitudes")
def admin_solicitudes():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        solicitudes = conn.execute("""
            SELECT s.id, u.nombre, s.tipo, s.comentario, s.estado
            FROM solicitudes s
            JOIN empleados e ON s.empleado_id=e.id
            JOIN usuarios u ON e.usuario_id=u.id
        """).fetchall()
        conn.close()
        return render_template("admin/solicitudes.html", solicitudes=solicitudes)
    except Exception as e:
        logger.error("ERROR en admin_solicitudes: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


@app.route("/admin/solicitud/<int:id>/<accion>")
def gestionar_solicitud(id, accion):
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        estado = "aprobada" if accion == "aprobar" else "rechazada"
        conn = get_db_connection()
        conn.execute("UPDATE solicitudes SET estado=? WHERE id=?", (estado, id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_solicitudes"))
    except Exception as e:
        logger.error("ERROR en gestionar_solicitud: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("admin_solicitudes"))


# ---------------- VACACIONES ADMIN ----------------

@app.route("/admin/vacaciones", methods=["GET", "POST"])
def admin_vacaciones():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == "POST":
            empleado_id = request.form["empleado_id"]
            fecha_inicio = request.form["fecha_inicio"]
            fecha_fin = request.form["fecha_fin"]
            tipo = request.form["tipo"]
            cursor.execute("""
                INSERT INTO vacaciones (empleado_id,fecha_inicio,fecha_fin,tipo,estado)
                VALUES (?,?,?,?,'aprobada')
            """, (empleado_id, fecha_inicio, fecha_fin, tipo))
            conn.commit()
        cursor.execute("""
            SELECT e.id, u.nombre FROM empleados e
            JOIN usuarios u ON e.usuario_id=u.id
        """)
        empleados = cursor.fetchall()
        cursor.execute("""
            SELECT v.id, u.nombre, v.fecha_inicio, v.fecha_fin, v.tipo
            FROM vacaciones v
            JOIN empleados e ON v.empleado_id=e.id
            JOIN usuarios u ON e.usuario_id=u.id
            ORDER BY v.fecha_inicio DESC
        """)
        vacaciones = cursor.fetchall()
        conn.close()
        return render_template("admin/vacaciones.html",
                               empleados=empleados, vacaciones=vacaciones)
    except Exception as e:
        logger.error("ERROR en admin_vacaciones: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("home"))


# ---------------- CALENDARIO ADMIN ----------------

@app.route("/admin/calendario")
def admin_calendario():
    try:
        if session.get("rol") != "admin":
            return redirect(url_for("home"))
        return render_template("admin/calendario.html")
    except Exception as e:
        logger.error("ERROR en admin_calendario: %s", e)
        logger.debug(traceback.format_exc())
        return redirect(url_for("home"))


@app.route("/admin/calendario/eventos")
def calendario_eventos():
    try:
        conn = get_db_connection()
        datos = conn.execute("""
            SELECT a.fecha, u.nombre, t.nombre AS turno, t.color
            FROM asignaciones a
            JOIN empleados e ON a.empleado_id=e.id
            JOIN usuarios u ON e.usuario_id=u.id
            JOIN turnos t ON a.turno_id=t.id
        """).fetchall()
        conn.close()
        eventos = [{"title": f"{r['nombre']} - {r['turno']}",
                    "start": r["fecha"], "color": r["color"]} for r in datos]
        return jsonify(eventos)
    except Exception as e:
        logger.error("ERROR en calendario_eventos: %s", e)
        logger.debug(traceback.format_exc())
        return jsonify([])


# ---------------- EMPLEADO DASHBOARD ----------------

@app.route("/empleado")
def empleado_dashboard():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        return render_template("empleado/dashboard.html",
                               nombre=session["nombre"], time=int(time()))
    except Exception as e:
        logger.error("ERROR en empleado_dashboard: %s", e)
        logger.debug(traceback.format_exc())
        return redirect(url_for("home"))


@app.route("/empleado/perfil", methods=["GET", "POST"])
def empleado_perfil():
    try:
        if "usuario_id" not in session or session.get("rol") != "empleado":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, email FROM usuarios WHERE id=?", (session["usuario_id"],))
        usuario = cursor.fetchone()
        cursor.execute("SELECT puesto FROM empleados WHERE usuario_id=?", (session["usuario_id"],))
        empleado = cursor.fetchone()
        if usuario is None:
            conn.close()
            return redirect(url_for("logout"))
        if request.method == "POST":
            nombre = request.form.get("nombre")
            cursor.execute("UPDATE usuarios SET nombre=? WHERE id=?",
                           (nombre, session["usuario_id"]))
            conn.commit()
            session["nombre"] = nombre
            flash("Perfil actualizado", "success")
        conn.close()
        return render_template("empleado/perfil.html", usuario=usuario, empleado=empleado)
    except Exception as e:
        logger.error("ERROR en empleado_perfil: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/turnos")
def empleado_turnos():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        hoy = date.today()
        inicio = hoy - timedelta(days=hoy.weekday())
        fin = inicio + timedelta(days=6)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM empleados WHERE usuario_id=?", (session["usuario_id"],))
        emp = cursor.fetchone()
        turnos = []
        if emp:
            turnos = cursor.execute("""
                SELECT t.nombre, t.hora_inicio, t.hora_fin, a.fecha, t.color
                FROM asignaciones a JOIN turnos t ON a.turno_id=t.id
                WHERE a.empleado_id=? AND a.fecha BETWEEN ? AND ?
                ORDER BY a.fecha
            """, (emp["id"], inicio.isoformat(), fin.isoformat())).fetchall()
        conn.close()
        return render_template("empleado/turnos.html", turnos=turnos,
                               inicio=inicio, fin=fin, time=int(time()))
    except Exception as e:
        logger.error("ERROR en empleado_turnos: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/solicitudes", methods=["GET", "POST"])
def empleado_solicitudes():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM empleados WHERE usuario_id=?", (session["usuario_id"],))
        emp = cursor.fetchone()
        if request.method == "POST":
            tipo = request.form["tipo"]
            comentario = request.form["comentario"]
            cursor.execute("""
                INSERT INTO solicitudes (empleado_id,tipo,comentario) VALUES (?,?,?)
            """, (emp["id"], tipo, comentario))
            conn.commit()
        solicitudes = cursor.execute("""
            SELECT * FROM solicitudes WHERE empleado_id=? ORDER BY id DESC
        """, (emp["id"],)).fetchall()
        conn.close()
        return render_template("empleado/solicitudes.html",
                               solicitudes=solicitudes, time=int(time()))
    except Exception as e:
        logger.error("ERROR en empleado_solicitudes: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/solicitar", methods=["GET", "POST"])
def solicitar_permiso():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        if request.method == "POST":
            tipo = request.form["tipo"]
            comentario = request.form["comentario"]
            conn = get_db_connection()
            empleado = conn.execute(
                "SELECT id FROM empleados WHERE usuario_id=?", (session["usuario_id"],)
            ).fetchone()
            conn.execute("""
                INSERT INTO solicitudes (empleado_id,tipo,comentario) VALUES (?,?,?)
            """, (empleado["id"], tipo, comentario))
            conn.commit()
            conn.close()
            return redirect(url_for("empleado_turnos"))
        return render_template("empleado/solicitar.html")
    except Exception as e:
        logger.error("ERROR en solicitar_permiso: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/cambiar-password", methods=["GET", "POST"])
def empleado_cambiar_password():
    try:
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
            conn.execute("UPDATE usuarios SET password=?, primer_login=0 WHERE id=?",
                         (nueva, session["usuario_id"]))
            conn.commit()
            conn.close()
            flash("Contraseña actualizada", "success")
            return redirect(url_for("empleado_dashboard"))
        return render_template("empleado/cambiar_password.html")
    except Exception as e:
        logger.error("ERROR en empleado_cambiar_password: %s", e)
        logger.debug(traceback.format_exc())
        flash(f"Error: {e}", "error")
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/calendario")
def empleado_calendario():
    try:
        if session.get("rol") != "empleado":
            return redirect(url_for("home"))
        return render_template("empleado/calendario.html")
    except Exception as e:
        logger.error("ERROR en empleado_calendario: %s", e)
        logger.debug(traceback.format_exc())
        return redirect(url_for("empleado_dashboard"))


@app.route("/empleado/calendario/eventos")
def empleado_calendario_eventos():
    try:
        if session.get("rol") != "empleado":
            return jsonify([])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM empleados WHERE usuario_id=?", (session["usuario_id"],))
        empleado = cursor.fetchone()
        eventos = []
        if empleado:
            for t in cursor.execute("""
                SELECT a.fecha, t.nombre, t.hora_inicio, t.hora_fin, t.color
                FROM asignaciones a JOIN turnos t ON a.turno_id=t.id
                WHERE a.empleado_id=?
            """, (empleado["id"],)).fetchall():
                eventos.append({"title": f"{t['nombre']} {t['hora_inicio']}-{t['hora_fin']}",
                                 "start": t["fecha"], "color": t["color"]})
            for v in cursor.execute("""
                SELECT fecha_inicio, fecha_fin, tipo FROM vacaciones
                WHERE empleado_id=? AND estado='aprobada'
            """, (empleado["id"],)).fetchall():
                eventos.append({"title": v["tipo"], "start": v["fecha_inicio"],
                                 "end": v["fecha_fin"], "color": "#2ecc71"})
        conn.close()
        return jsonify(eventos)
    except Exception as e:
        logger.error("ERROR en empleado_calendario_eventos: %s", e)
        logger.debug(traceback.format_exc())
        return jsonify([])


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    usuario_id = session.get("usuario_id", "?")
    session.clear()
    logger.info("Logout → usuario_id=%s", usuario_id)
    return redirect(url_for("home"))


# ---------------- MANEJADORES DE ERROR ----------------

@app.errorhandler(500)
def internal_error(e):
    logger.error("500: %s", e)
    logger.debug(traceback.format_exc())
    flash("Error interno del servidor", "error")
    return redirect(url_for("home"))

@app.errorhandler(404)
def not_found(e):
    logger.warning("404 - Ruta no encontrada: %s", request.url)
    return redirect(url_for("home"))


# ---------------- RUN APP ----------------

with app.app_context():
    crear_tablas()
    crear_admin_inicial()

if __name__ == '__main__':
    app.run(debug=True)
