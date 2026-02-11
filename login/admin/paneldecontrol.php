<?php
session_start();
if (!isset($_SESSION['rol']) || $_SESSION['rol'] != 'admin') {
    header("Location: ../login.html");
    exit;
}

echo "Bienvenido administrador, " . $_SESSION['nombre'];
?>
