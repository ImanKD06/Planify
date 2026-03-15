from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta
from time import time

app = Flask(__name__)
app.secret_key = "super_secret_key"


# ---------------- CONEXIÓN BD ----------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- CREAR TABLAS ----------------

def crear_tablas():
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


# ---------------- CREAR ADMIN INICIAL ----------------

def crear_admin_inicial():
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

        print("Admin inicial creado")
        print("Email: admin@empresa.com")
        print("Password:", password_temporal)

    conn.close()


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
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE email=?",
        (email,)
    ).fetchone()

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


# ---------------- CAMBIAR PASSWORD ----------------

@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():

    if "usuario_id" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        nueva = generate_password_hash(request.form["password"])

        conn = get_db_connection()

        conn.execute("""
            UPDATE usuarios
            SET password=?, primer_login=0
            WHERE id=?
        """, (nueva, session["usuario_id"]))

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("cambiar_password.html")


# ---------------- EMPLEADOS ----------------

@app.route("/admin/empleados")
def listar_empleados():

    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    empleados = conn.execute("""
        SELECT e.id,u.nombre,u.email,e.puesto
        FROM empleados e
        JOIN usuarios u ON e.usuario_id=u.id
    """).fetchall()

    conn.close()

    return render_template("admin/empleados.html", empleados=empleados)


# ---------------- CREAR EMPLEADO ----------------

@app.route("/admin/empleados/crear", methods=["GET", "POST"])
def crear_empleado():

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

        cursor.execute("""
            INSERT INTO empleados (usuario_id,puesto)
            VALUES (?,?)
        """, (usuario_id, puesto))

        conn.commit()
        conn.close()

        flash("Empleado creado", "success")
        return redirect(url_for("listar_empleados"))

    return render_template("admin/crear_empleado.html")

# ---------------- EDITAR EMPLEADO ----------------

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


# ---------------- ELIMINAR EMPLEADO ----------------

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

@app.route("/admin/turnos/eliminar/<int:id>", methods=["POST"])
def eliminar_turno(id):
    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM turnos WHERE id = ?", (id,))
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

        fecha_inicio = request.form["fecha_inicio"]
        fecha_fin = request.form["fecha_fin"]

        inicio = date.fromisoformat(fecha_inicio)
        fin = date.fromisoformat(fecha_fin)

        while inicio <= fin:

            cursor.execute("""
                SELECT * FROM asignaciones
                WHERE empleado_id=? AND fecha=?
            """, (empleado_id, inicio.isoformat()))

            if not cursor.fetchone():

                cursor.execute("""
                    INSERT INTO asignaciones (empleado_id, turno_id, fecha)
                    VALUES (?, ?, ?)
                """, (empleado_id, turno_id, inicio.isoformat()))

            inicio += timedelta(days=1)

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


@app.route("/admin/solicitudes")
def admin_solicitudes():

    if session.get("rol") != "admin":
        return redirect("/")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    solicitudes = conn.execute("""
        SELECT s.id, u.nombre, s.tipo, s.comentario, s.estado
        FROM solicitudes s
        JOIN empleados e ON s.empleado_id = e.id
        JOIN usuarios u ON e.usuario_id = u.id
    """).fetchall()

    conn.close()

    return render_template("admin/solicitudes.html", solicitudes=solicitudes)

@app.route("/admin/solicitud/<int:id>/<accion>")
def gestionar_solicitud(id, accion):

    if session.get("rol") != "admin":
        return redirect("/")

    conn = sqlite3.connect("database.db")

    if accion == "aprobar":
        estado = "aprobada"
    else:
        estado = "rechazada"

    conn.execute(
        "UPDATE solicitudes SET estado = ? WHERE id = ?",
        (estado, id)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/solicitudes")


@app.route("/admin/vacaciones", methods=["GET", "POST"])
def admin_vacaciones():

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
            VALUES (?,?,?,?, 'aprobada')
        """, (empleado_id, fecha_inicio, fecha_fin, tipo))

        conn.commit()

    # lista empleados
    cursor.execute("""
        SELECT e.id, u.nombre
        FROM empleados e
        JOIN usuarios u ON e.usuario_id = u.id
    """)

    empleados = cursor.fetchall()

    # lista vacaciones
    cursor.execute("""
        SELECT v.id, u.nombre, v.fecha_inicio, v.fecha_fin, v.tipo
        FROM vacaciones v
        JOIN empleados e ON v.empleado_id = e.id
        JOIN usuarios u ON e.usuario_id = u.id
        ORDER BY v.fecha_inicio DESC
    """)

    vacaciones = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/vacaciones.html",
        empleados=empleados,
        vacaciones=vacaciones
    )


@app.route("/admin/calendario")
def admin_calendario():

    if session.get("rol") != "admin":
        return redirect(url_for("home"))

    return render_template("admin/calendario.html")

@app.route("/admin/calendario/eventos")
def calendario_eventos():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.fecha, u.nombre, t.nombre AS turno, t.color
        FROM asignaciones a
        JOIN empleados e ON a.empleado_id = e.id
        JOIN usuarios u ON e.usuario_id = u.id
        JOIN turnos t ON a.turno_id = t.id
    """)

    datos = cursor.fetchall()
    conn.close()

    eventos = []

    for fila in datos:
        eventos.append({
            "title": f"{fila['nombre']} - {fila['turno']}",
            "start": fila["fecha"],
            "color": fila["color"]
        })

    return eventos



# ---------------- EMPLEADO DASHBOARD ----------------

@app.route("/empleado")
def empleado_dashboard():

    if session.get("rol") != "empleado":
        return redirect(url_for("home"))

    return render_template(
        "empleado/dashboard.html",
        nombre=session["nombre"],
        time=int(time())
    )

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

        cursor.execute(
            "UPDATE usuarios SET nombre=? WHERE id=?",
            (nombre, session["usuario_id"])
        )
        conn.commit()

        session["nombre"] = nombre
        flash("Perfil actualizado", "success")

    conn.close()

    return render_template("empleado/perfil.html", usuario=usuario, empleado=empleado)



# ---------------- TURNOS EMPLEADO ----------------

@app.route("/empleado/turnos")
def empleado_turnos():

    if session.get("rol") != "empleado":
        return redirect(url_for("home"))

    hoy = date.today()

    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM empleados WHERE usuario_id=?",
        (session["usuario_id"],)
    )

    emp = cursor.fetchone()

    if emp:

        turnos = cursor.execute("""
            SELECT t.nombre,t.hora_inicio,t.hora_fin,a.fecha,t.color
            FROM asignaciones a
            JOIN turnos t ON a.turno_id=t.id
            WHERE a.empleado_id=? AND a.fecha BETWEEN ? AND ?
            ORDER BY a.fecha
        """, (emp["id"], inicio.isoformat(), fin.isoformat())).fetchall()

    else:
        turnos = []

    conn.close()

    return render_template(
        "empleado/turnos.html",
        turnos=turnos,
        inicio=inicio,
        fin=fin,
        time=int(time())
    )


# ---------------- SOLICITUDES EMPLEADO ----------------

@app.route("/empleado/solicitudes", methods=["GET", "POST"])
def empleado_solicitudes():

    if session.get("rol") != "empleado":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM empleados WHERE usuario_id=?",
        (session["usuario_id"],)
    )

    emp = cursor.fetchone()

    if request.method == "POST":

        tipo = request.form["tipo"]
        comentario = request.form["comentario"]

        cursor.execute("""
            INSERT INTO solicitudes (empleado_id,tipo,comentario)
            VALUES (?,?,?)
        """, (emp["id"], tipo, comentario))

        conn.commit()

    solicitudes = cursor.execute("""
        SELECT * FROM solicitudes
        WHERE empleado_id=?
        ORDER BY id DESC
    """, (emp["id"],)).fetchall()

    conn.close()

    return render_template(
        "empleado/solicitudes.html",
        solicitudes=solicitudes,
        time=int(time())
    )

@app.route("/empleado/solicitar", methods=["GET","POST"])
def solicitar_permiso():

    if session.get("rol") != "empleado":
        return redirect("/")

    if request.method == "POST":

        tipo = request.form["tipo"]
        comentario = request.form["comentario"]

        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row

        empleado = conn.execute("""
        SELECT id FROM empleados
        WHERE usuario_id = ?
        """,(session["usuario_id"],)).fetchone()

        conn.execute("""
        INSERT INTO solicitudes (empleado_id,tipo,comentario)
        VALUES (?,?,?)
        """,(empleado["id"],tipo,comentario))

        conn.commit()
        conn.close()

        return redirect("/empleado/turnos")

    return render_template("empleado/solicitar.html")



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

        cursor.execute("""
            UPDATE usuarios 
            SET password=?, primer_login=0 
            WHERE id=?
        """, (nueva, session["usuario_id"]))

        conn.commit()
        conn.close()

        flash("Contraseña actualizada", "success")
        return redirect(url_for("empleado_dashboard"))

    return render_template("empleado/cambiar_password.html")

@app.route("/empleado/calendario")
def empleado_calendario():

    if session.get("rol") != "empleado":
        return redirect(url_for("home"))

    return render_template("empleado/calendario.html")

@app.route("/empleado/calendario/eventos")
def empleado_calendario_eventos():

    if session.get("rol") != "empleado":
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM empleados WHERE usuario_id=?",
        (session["usuario_id"],)
    )

    empleado = cursor.fetchone()

    eventos = []

    if empleado:

        # TURNOS
        cursor.execute("""
            SELECT a.fecha, t.nombre, t.hora_inicio, t.hora_fin, t.color
            FROM asignaciones a
            JOIN turnos t ON a.turno_id = t.id
            WHERE a.empleado_id=?
        """, (empleado["id"],))

        for t in cursor.fetchall():

            eventos.append({
                "title": f"{t['nombre']} {t['hora_inicio']}-{t['hora_fin']}",
                "start": t["fecha"],
                "color": t["color"]
            })

        # VACACIONES
        cursor.execute("""
            SELECT fecha_inicio, fecha_fin, tipo
            FROM vacaciones
            WHERE empleado_id=? AND estado='aprobada'
        """, (empleado["id"],))

        for v in cursor.fetchall():

            eventos.append({
                "title": v["tipo"],
                "start": v["fecha_inicio"],
                "end": v["fecha_fin"],
                "color": "#2ecc71"
            })

        # SOLICITUDES (ASUNTOS PROPIOS)
        cursor.execute("""
            SELECT tipo
            FROM solicitudes
            WHERE empleado_id=? AND estado='aprobada'
        """, (empleado["id"],))

        for s in cursor.fetchall():

            eventos.append({
                "title": s["tipo"],
                "color": "#f39c12"
            })

    conn.close()

    return eventos


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- RUN APP ----------------

# Esto se ejecuta tanto con "python app.py" como con Gunicorn en Render
crear_tablas()
crear_admin_inicial()

if __name__ == "__main__":
    app.run(debug=True)
