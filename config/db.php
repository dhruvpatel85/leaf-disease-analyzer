<?php
// Start session FIRST before anything else
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Database Configuration
$host     = "localhost";
$username = "root";
$password = "";          // Default XAMPP/MAMP password is empty
$database = "leaf_analyzer";

$conn = new mysqli($host, $username, $password, $database);

if ($conn->connect_error) {
    // In JSON context (analyze.php), output JSON error; otherwise plain text
    $is_ajax = isset($_SERVER['HTTP_X_REQUESTED_WITH']) ||
               (isset($_SERVER['HTTP_ACCEPT']) && strpos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false);
    if ($is_ajax) {
        header('Content-Type: application/json');
        echo json_encode(["success" => false, "message" => "Database connection failed: " . $conn->connect_error]);
    } else {
        die("<h3 style='color:red;font-family:sans-serif;padding:20px;'>
            ❌ Database connection failed.<br><br>
            <strong>Error:</strong> " . htmlspecialchars($conn->connect_error) . "<br><br>
            <strong>Fix:</strong> Make sure XAMPP/MAMP is running and the database <code>leaf_analyzer</code> exists.<br>
            Import <code>leaf_analyzer.sql</code> in phpMyAdmin.
        </h3>");
    }
    exit;
}

// Set charset to UTF-8
$conn->set_charset("utf8mb4");
?>
