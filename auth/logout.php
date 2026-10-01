<?php
// Start session and destroy it
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
session_unset();
session_destroy();

// Redirect to login (same folder: auth/)
header("Location: login.php");
exit;
?>