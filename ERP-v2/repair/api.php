<?php
require_once __DIR__ . '/lib.php';
$db = load_db();
header('Content-Type: application/json; charset=utf-8');
$action = $_GET['action'] ?? '';
if ($action === 'ping') {
    if (!is_logged_in()) { echo json_encode(['status'=>'guest','mode'=>'none'], JSON_UNESCAPED_UNICODE); exit; }
    echo json_encode(['status'=>'ok','mode'=>is_db_writable() ? 'nas' : 'readonly','user'=>current_username(),'time'=>date('c')], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit;
}
if ($action === 'me') { require_login(); echo json_encode(['status'=>'ok','user'=>current_user($db)], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit; }
if ($action === 'custom_groups') { require_login(); echo json_encode(['status'=>'ok','custom_groups'=>$db['custom_groups'] ?? []], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit; }
echo json_encode(['status'=>'error','message'=>'unknown action'], JSON_UNESCAPED_UNICODE);
?>