<?php
session_start();
include "conexion.php";

// Recoger datos del formulario
$email = $_POST['email'];
$password = $_POST['password'];

// Preparar consulta
$sql = "SELECT * FROM usuarios WHERE email = ?";
$stmt = $conn->prepare($sql);
$stmt->execute([$email]);
$usuario = $stmt->fetch(PDO::FETCH_ASSOC);

// Verificar usuario y contraseña
if ($usuario && password_verify($password, $usuario['password'])) {

    // Guardar datos en sesión
    $_SESSION['usuario_id'] = $usuario['id'];
    $_SESSION['rol'] = $usuario['rol'];
    $_SESSION['nombre'] = $usuario['nombre'];

    // Redirigir según rol
    if ($usuario['rol'] == 'admin') {
        header("Location: admin/dashboard.php");
        exit;
    } else {
        header("Location: empleado/dashboard.php");
        exit;
    }

} else {
    echo "Email o contraseña incorrectos";
}
?>
