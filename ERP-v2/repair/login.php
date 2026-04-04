<?php
require_once __DIR__ . '/lib.php';
$db = load_db();
if (is_logged_in()) { header('Location: index.php'); exit; }
$error = '';
$next = basename($_GET['next'] ?? $_POST['next'] ?? 'index.php');
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim((string)($_POST['username'] ?? ''));
    $password = (string)($_POST['password'] ?? '');
    $found = null;
    foreach ($db['users'] as &$u) {
        if (($u['username'] ?? '') === $username && verify_password($password, (string)($u['password_hash'] ?? ''))) {
            $u['last_login'] = date('Y-m-d H:i:s'); $found = $u; break;
        }
    } unset($u);
    if ($found) {
        set_login($found);
        log_action($db, 'login', '登入成功');
        save_db($db);
        header('Location: ' . ($next ?: 'index.php'));
        exit;
    }
    log_action($db, 'login_failed', '帳號或密碼錯誤：' . $username);
    save_db($db);
    $error = '帳號或密碼錯誤';
}
?><!DOCTYPE html><html lang="zh-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title><?php echo h($db['settings']['site_name'] ?? '系統登入'); ?>｜登入</title>
<style>
:root{--bg:#0b0f14;--line:rgba(255,255,255,.09);--ink:#e5e7eb;--muted:#9ca3af;--pri:#fbbf24;--pri2:#f59e0b}
*{box-sizing:border-box}html,body{height:100%;margin:0}body{font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI","Noto Sans TC",sans-serif;background:radial-gradient(900px 500px at 15% 0%, rgba(251,191,36,.11), transparent 45%),radial-gradient(700px 500px at 85% 15%, rgba(59,130,246,.09), transparent 40%), var(--bg);color:var(--ink);display:grid;place-items:center;padding:20px}
.wrap{width:min(460px,100%);background:rgba(18,25,38,.96);border:1px solid var(--line);border-radius:24px;padding:26px;box-shadow:0 18px 48px rgba(0,0,0,.35)}
h1{margin:0 0 6px 0;font-size:28px}.sub{color:var(--muted);line-height:1.6;font-size:14px;margin-bottom:18px}label{display:block;margin:12px 0 6px;color:#fff;font-size:14px}
input{width:100%;padding:12px 13px;border-radius:14px;border:1px solid var(--line);background:rgba(0,0,0,.3);color:var(--ink);outline:none}
button{margin-top:16px;width:100%;padding:12px 14px;border:none;border-radius:14px;background:var(--pri);color:#1f2937;font-weight:800;cursor:pointer}button:hover{background:var(--pri2)}
.err{margin-top:14px;padding:12px 13px;border-radius:14px;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.28);color:#fecaca}.demo{margin-top:18px;padding:12px 13px;border-radius:14px;background:rgba(255,255,255,.04);border:1px solid var(--line);font-size:13px;color:var(--muted);line-height:1.7}code{background:rgba(255,255,255,.05);padding:2px 6px;border-radius:8px}
</style></head><body>
<form class="wrap" method="post" autocomplete="off">
<h1><?php echo h($db['settings']['site_name'] ?? '電腦舖門市系統'); ?></h1>
<div class="sub"><?php echo h($db['settings']['brand_notice'] ?? '請先登入後再使用系統。'); ?></div>
<input type="hidden" name="next" value="<?php echo h($next); ?>">
<label for="username">帳號</label><input id="username" name="username" required>
<label for="password">密碼</label><input id="password" name="password" type="password" required>
<button type="submit">登入系統</button>
<?php if ($error): ?><div class="err"><?php echo h($error); ?></div><?php endif; ?>

</form><div style="position:fixed;right:12px;bottom:10px;background:#111827;color:#facc15;padding:6px 10px;border-radius:999px;font:12px sans-serif;z-index:9999;border:1px solid #374151">版本 v2.6.2</div></body></html>