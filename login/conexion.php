<?php
$host = "localhost";
$db   = "planify";
$user = "root";  // tu usuario de MySQL
$pass = "";      // tu contraseña de MySQL

try {
    $conn = new PDO("mysql:host=$host;dbname=$db;charset=utf8", $user, $pass);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    echo "Error de conexión: " . $e->getMessage();
    exit;
}
?>
