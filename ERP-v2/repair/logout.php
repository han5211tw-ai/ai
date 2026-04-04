<?php
require_once __DIR__ . '/lib.php';
$db = load_db();
if (is_logged_in()) { log_action($db, 'logout', '登出系統'); save_db($db); }
logout_user();
header('Location: login.php');
exit;
?>