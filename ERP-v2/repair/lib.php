<?php
declare(strict_types=1);
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.use_strict_mode', '1');
    ini_set('session.cookie_httponly', '1');
    session_name('store_system_session');
    session_start();
}
const DB_FILE = __DIR__ . '/data/db.json';


function builtin_fault_groups(): array {
    $indexFile = __DIR__ . '/index.php';
    if (!file_exists($indexFile)) return [];
    $content = (string)file_get_contents($indexFile);
    preg_match_all('/"([a-zA-Z0-9_]+)"\s*:\s*\{\s*"label"\s*:\s*"([^"]+)"/u', $content, $matches, PREG_SET_ORDER);
    $groups = [];
    foreach ($matches as $m) {
        $key = (string)($m[1] ?? '');
        $label = trim((string)($m[2] ?? ''));
        if ($key === '' || $label === '') continue;
        if (isset($groups[$key])) continue;
        $groups[$key] = ['label' => $label, 'icon' => 'generic', 'items' => [], 'locked' => true];
    }
    return $groups;
}

function default_scenario_groups(): array {
    $groups = builtin_fault_groups();
    if (!empty($groups)) return $groups;
    return [
        'power_desktop' => ['label' => '桌機｜電源/無法開機', 'icon' => 'power', 'items' => [], 'locked' => true],
        'power_laptop' => ['label' => '筆電｜電源/充電/電池', 'icon' => 'battery', 'items' => [], 'locked' => true],
        'display' => ['label' => '顯示｜黑畫面/破圖/外接', 'icon' => 'display', 'items' => [], 'locked' => true],
        'boot_system' => ['label' => '系統｜無法進入/修復/更新', 'icon' => 'storage', 'items' => [], 'locked' => true],
        'network_wifi' => ['label' => '網路｜Wi-Fi/有線/共享', 'icon' => 'network', 'items' => [], 'locked' => true],
        'other' => ['label' => '其他', 'icon' => 'generic', 'items' => [], 'locked' => true],
    ];
}

function default_permissions(): array {
    return [
        'admin' => [
            'access_frontend'=>true,'access_admin'=>true,'manage_groups'=>true,'manage_scenarios'=>true,
            'manage_users'=>true,'manage_layout'=>true,'manage_permissions'=>true,'view_logs'=>true,
            'change_settings'=>true,
        ],
        'manager' => [
            'access_frontend'=>true,'access_admin'=>true,'manage_groups'=>true,'manage_scenarios'=>true,
            'manage_users'=>false,'manage_layout'=>true,'manage_permissions'=>false,'view_logs'=>true,
            'change_settings'=>false,
        ],
        'staff' => [
            'access_frontend'=>true,'access_admin'=>false,'manage_groups'=>false,'manage_scenarios'=>false,
            'manage_users'=>false,'manage_layout'=>false,'manage_permissions'=>false,'view_logs'=>false,
            'change_settings'=>false,
        ],
    ];
}

function default_db(): array {
    return [
        'version' => 'v2.6.1',
        'settings' => [
            'site_name' => '電腦舖門市系統',
            'subtitle' => '門市實戰細節優化版｜NAS 多人共用｜前台 AI 助理 v2.6.1',
            'brand_notice' => '所有人員需先登入才能進入前台或後台，AI 助理已升級為門市實戰導引模式。',
            'sidebar_notice_title' => '強化重點',
            'sidebar_notice_text' => '移除維修單、客戶資料庫、匯入匯出模組，全部資源集中在故障排查。',
            'sidebar_usage_text' => "可用方式：\n1. 直接選類別與情境\n2. 搜尋錯誤碼或症狀\n3. 勾選現象，讓系統列出最可能原因",
            'ai_logo_path' => 'assets/ai-logo.png',
            'ai_logo_scale' => '1.18',
            'ai_logo_badge_scale' => '1.12',
            'ai_logo_offset_x' => '0',
            'ai_logo_offset_y' => '0',
        ],
        'role_permissions' => default_permissions(),
        'users' => [], 'custom_groups' => default_scenario_groups(), 'logs' => [],
    ];
}
function load_db(): array {
    if (!file_exists(DB_FILE)) return default_db();
    $data = json_decode((string)file_get_contents(DB_FILE), true);
    $db = is_array($data) ? array_replace_recursive(default_db(), $data) : default_db();
    foreach (default_permissions() as $role => $perms) {
        $db['role_permissions'][$role] = array_replace($perms, $db['role_permissions'][$role] ?? []);
    }
    $mergedGroups = default_scenario_groups();
    foreach (($db['custom_groups'] ?? []) as $key => $group) {
        $base = $mergedGroups[$key] ?? ['label' => (string)$key, 'icon' => 'generic', 'items' => [], 'locked' => false];
        $mergedGroups[$key] = array_replace($base, is_array($group) ? $group : []);
        if (!array_key_exists('locked', $mergedGroups[$key])) $mergedGroups[$key]['locked'] = isset(default_scenario_groups()[$key]);
        if (!isset($mergedGroups[$key]['items']) || !is_array($mergedGroups[$key]['items'])) $mergedGroups[$key]['items'] = [];
    }
    $db['custom_groups'] = $mergedGroups;
    return $db;
}
function save_db(array $db): bool {
    $dir = dirname(DB_FILE);
    if (!is_dir($dir) || !is_writable($dir)) return false;
    $tmp = DB_FILE . '.tmp';
    $json = json_encode($db, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    if (file_put_contents($tmp, $json, LOCK_EX) === false) return false;
    return rename($tmp, DB_FILE);
}
function h(string $s): string { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
function current_username(): ?string { return $_SESSION['user'] ?? null; }
function current_user(?array $db = null): ?array {
    $db = $db ?? load_db();
    $u = current_username(); if (!$u) return null;
    foreach ($db['users'] as $user) if (($user['username'] ?? '') === $u) return $user;
    return null;
}
function is_logged_in(): bool { return current_username() !== null; }
function require_login(): void {
    if (is_logged_in()) return;
    $next = basename($_SERVER['PHP_SELF'] ?? 'index.php');
    header('Location: login.php?next=' . urlencode($next)); exit;
}
function user_has_role(array $user, array $roles): bool { return in_array($user['role'] ?? '', $roles, true); }
function current_permissions(?array $db = null, ?array $user = null): array {
    $db = $db ?? load_db();
    $user = $user ?? current_user($db);
    $role = $user['role'] ?? 'staff';
    return array_replace(default_permissions()['staff'], $db['role_permissions'][$role] ?? []);
}
function has_permission(string $permission, ?array $db = null, ?array $user = null): bool {
    $perms = current_permissions($db, $user);
    return (bool)($perms[$permission] ?? false);
}
function require_admin_permission(string $permission, ?array $db = null): void {
    require_login();
    $db = $db ?? load_db();
    $user = current_user($db);
    if (!$user || !has_permission('access_admin', $db, $user) || !has_permission($permission, $db, $user)) {
        http_response_code(403);
        echo '<!DOCTYPE html><meta charset="utf-8"><title>權限不足</title><div style="font-family:sans-serif;padding:24px"><h2>權限不足</h2><p>你目前沒有存取此功能的權限。</p><p><a href="index.php">回前台</a></p></div>';
        exit;
    }
}
function hash_password(string $password): string { return hash('sha256', $password); }
function verify_password(string $password, string $hash): bool { return hash_equals($hash, hash_password($password)); }
function set_login(array $user): void { session_regenerate_id(true); $_SESSION['user'] = $user['username']; }
function logout_user(): void {
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $p = session_get_cookie_params();
        setcookie(session_name(), '', time()-42000, $p['path'] ?? '/', $p['domain'] ?? '', (bool)($p['secure'] ?? false), (bool)($p['httponly'] ?? true));
    }
    session_destroy();
}
function get_client_ip(): string { return $_SERVER['REMOTE_ADDR'] ?? 'unknown'; }
function log_action(array &$db, string $action, string $detail=''): void {
    $db['logs'][] = ['time'=>date('Y-m-d H:i:s'),'user'=>current_username() ?? 'guest','action'=>$action,'detail'=>$detail,'ip'=>get_client_ip()];
    if (count($db['logs']) > 500) $db['logs'] = array_slice($db['logs'], -500);
}
function is_db_writable(): bool { return file_exists(DB_FILE) ? is_writable(DB_FILE) : is_writable(dirname(DB_FILE)); }
function parse_lines(string $text): array {
    $parts = preg_split('/\r\n|\r|\n/', trim($text)) ?: [];
    $parts = array_map('trim', $parts);
    return array_values(array_filter($parts, fn($x) => $x !== ''));
}
function slugify(string $text): string {
    $text = trim($text);
    $text = preg_replace('/[^\p{L}\p{N}_-]+/u', '_', $text);
    $text = trim((string)$text, '_');
    return $text !== '' ? strtolower($text) : 'group_' . substr(md5((string)microtime(true)), 0, 6);
}
function redirect_with_message(string $url, string $msg, string $type='ok'): void {
    header('Location: ' . $url . (str_contains($url, '?') ? '&' : '?') . 'msg=' . urlencode($msg) . '&type=' . urlencode($type));
    exit;
}
?>