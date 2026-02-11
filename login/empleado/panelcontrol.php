<?php
session_start();
if (!isset($_SESSION['rol']) || $_SESSION['rol'] != 'empleado') {
    header("Location: ../login.html");
    exit;
}

echo "Bienvenido empleado, " . $_SESSION['nombre'];
?>
