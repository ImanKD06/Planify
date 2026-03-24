1-. Función de los lenguajes de marcas en mi proyecto

1. Uso de lenguajes de marcas (HTML)
- Sirven para estructurar y organizar la información que se muestra en la aplicación web.
- Permiten separar la lógica del backend (Python + Flask) de la presentación visual.
- HTML construye formularios de login, tablas de empleados, listados de turnos y calendarios.

2. Comunicación entre cliente y servidor
- Flask genera plantillas HTML dinámicas (Jinja2) con datos obtenidos de la base de datos.
- El contenido no es estático: cambia según la información del sistema.
- HTML actúa como puente entre backend → datos → interfaz del usuario.

3. Interfaz clara y ordenada
- Los elementos estructurados en HTML facilitan la interacción del usuario.
- La página queda organizada en secciones comprensibles (formularios, tablas, bloques, etc.).

4. Función global de los lenguajes de marcas en el proyecto
- Estructuran la presentación del contenido.
- Permiten mostrar datos dinámicos procedentes del servidor.
- Aportan orden, claridad y separación de responsabilidades.


2.-Utiliza lenguajes de marcas para la transmisión y presentación de información a través de la web analizando la estructura de los documentos e identificando sus elementos. 
- Explica el uso de HTML y CSS que hace tu proyecto

1.-Uso de HTML en el proyecto
- Define la estructura de todas las páginas: login, panel de administrador y panel de empleado.
- Utilizo formularios (<form>) para recoger datos como email y contraseña.
- Uso inputs para datos del usuario y tablas para mostrar empleados y turnos.
- Empleo etiquetas semánticas y contenedores (<div>) para organizar la información en bloques (tarjetas, menús, listas).

2. Organización del contenido
- HTML permite dividir la página en secciones claras y entendibles.
- Facilita la lectura visual y la navegación del usuario.
- Cada bloque está diseñado para mejorar la usabilidad (formularios, tablas, paneles).

3. Uso de CSS en el proyecto
- CSS aplica estilos visuales: colores, márgenes, tipografías y distribución de elementos.
- Mejora la apariencia general y hace la aplicación más profesional e intuitiva.
- Se utiliza para adaptar la interfaz a diferentes tamaños y mejorar la experiencia del usuario.

4. Feedback y mensajes del sistema
- CSS muestra mensajes de error o éxito (flash de Flask) sin cambiar de página.
- Evita pantallas vacías y da retroalimentación visual dentro del mismo login.
- Aumenta claridad, accesibilidad y la interacción con el usuario.

5. Función conjunta de HTML + CSS
- HTML estructura la información.
- CSS aporta diseño, estilo y usabilidad.
- Ambos permiten una interfaz ordenada, clara, visual y fácil de usar.

3-Uso de JavaScript en el cliente

1. Función principal de JavaScript
- Aporta interactividad a la aplicación web desde el navegador.
- Permite ejecutar acciones sin recargar la página completa.
- Hace la experiencia más fluida y dinámica.

2. Uso en el calendario de turnos
- Scripts cargan los eventos del calendario de forma dinámica.
- Solicita datos al backend y los muestra sin refrescar la página.
- Mejora la rapidez y la usabilidad del calendario.

3. Gestión de eventos del usuario
- JavaScript detecta clics, cambios y envíos de formularios.
- Permite reacciones inmediatas dentro de la misma página.
- Facilita validaciones o acciones rápidas antes de enviar datos.

4. Manipulación del DOM
- JavaScript actualiza elementos visuales en tiempo real.
- Puede añadir, modificar o eliminar contenido según la acción del usuario.
- Mantiene la interfaz sincronizada con los datos del servidor.

5. Uso de JSON con Flask
- Recibe datos en formato JSON desde rutas del backend.
- Convierte la información JSON en elementos visibles (como turnos del calendario).
- Facilita la comunicación entre frontend y backend.

6. Contribución general a la aplicación
- Aumenta la interactividad y mejora la experiencia del usuario.
- Hace que la aplicación se comporte como una app moderna.
- Garantiza una navegación más rápida y sin interrupciones.

6. Consultas SQL y representación de datos
1. Uso de SQL en el proyecto
- Utilizo SQLite para guardar y gestionar la información del sistema.
- Las consultas SQL permiten obtener usuarios, empleados, turnos y asignaciones.
- El backend (Flask) ejecuta estas consultas para recuperar los datos necesarios.

2. Consulta de login
- SELECT * FROM usuarios WHERE email=?
- Comprueba si el usuario existe y valida las credenciales.
- Devuelve la información necesaria para iniciar sesión.

3. Listado de empleados
- Consulta con JOIN entre empleados y usuarios.
  SELECT e.id, u.nombre, u.email, e.puesto
  FROM empleados e
  JOIN usuarios u ON e.usuario_id = u.id
- Permite obtener datos completos del empleado (nombre, email, puesto).
- Se usa para mostrar la tabla de empleados en el panel del administrador.

4. Asignaciones de turnos
- Consulta con varios JOIN entre asignaciones, empleados, usuarios y turnos.
  SELECT a.id, u.nombre, t.nombre, a.fecha
  FROM asignaciones a
  JOIN empleados e ON a.empleado_id = e.id
  JOIN usuarios u ON e.usuario_id = u.id
  JOIN turnos t ON a.turno_id = t.id
- Devuelve los turnos asignados a cada empleado con su fecha y tipo de turno.
- Estos datos alimentan el calendario y los listados de turnos.

5. Envío de datos a las plantillas HTML
- Flask usa render_template para pasar los resultados de SQL a las vistas.
- Se integran datos dinámicos procedentes de la base de datos.

6. Representación de datos en las vistas
- Utilizo bucles de Jinja2 ({% for %}) para recorrer los resultados.
- Los datos se muestran en tablas HTML (empleados) o en calendarios/listados (turnos).
- Permite visualizar la información de forma clara, organizada e interactiva.

7. Función general de SQL en el proyecto
- Recuperar datos actualizados de la base de datos.
- Conectar la información del sistema con la interfaz del usuario.
- Permitir una representación visual dinámica en tableros, listas y calendarios.

7-Enfoque empreserial
1. Enfoque empresarial del sistema
- La aplicación está diseñada para gestionar empleados, turnos, asignaciones y solicitudes.
- Digitaliza procesos internos de una empresa y evita tareas manuales.

2. Funciones para administradores
- Organizan horarios y asignan turnos a los empleados.
- Gestionan solicitudes de vacaciones, permisos y cambios de turno.
- Centralizan toda la información en un panel de administración.

2. Tablas, columnas y estructura de la base de datos

BASE DE DATOS
6-Modelo entiadad-relación
Relaciones:
Un usuario → puede ser un empleado
Un empleado → puede tener muchas asignaciones
Un turno → puede estar en muchas asignaciones
Un empleado → puede tener muchas solicitudes
Un empleado → puede tener muchas vacaciones
Relación principal:
USUARIOS (1) —— (1) EMPLEADOS
EMPLEADOS (1) —— (N) ASIGNACIONES —— (N) TURNOS
EMPLEADOS (1) —— (N) SOLICITUDES
EMPLEADOS (1) —— (N) VACACIONES

7-Bases de datos NO relacionales
2. Posible uso de bases de datos NoSQL
- Algunas partes del sistema podrían usar NoSQL para almacenar información no estructurada o semiestructurada.
- Esto incluye logs de actividad, eventos del sistema o datos temporales en JSON.
