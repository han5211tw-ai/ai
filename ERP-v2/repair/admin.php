<?php
require_once __DIR__ . '/lib.php';
$db = load_db();
require_login();
$user = current_user($db);
if (!$user || !has_permission('access_admin', $db, $user)) {
    http_response_code(403);
    echo '<!DOCTYPE html><meta charset="utf-8"><title>權限不足</title><div style="font-family:sans-serif;padding:24px"><h2>權限不足</h2><p>你目前沒有存取後台的權限。</p><p><a href="index.php">回前台</a></p></div>';
    exit;
}
$perms = current_permissions($db, $user);
$msg = $_GET['msg'] ?? '';
$type = $_GET['type'] ?? 'ok';
$tab = $_GET['tab'] ?? 'dashboard';
$tabPermMap = [
    'dashboard' => 'access_admin',
    'groups' => 'manage_groups',
    'scenarios' => 'manage_scenarios',
    'users' => 'manage_users',
    'layout' => 'manage_layout',
    'permissions' => 'manage_permissions',
    'account' => 'access_admin',
    'logs' => 'view_logs',
];
if (!isset($tabPermMap[$tab]) || !($perms[$tabPermMap[$tab]] ?? false)) {
    foreach ($tabPermMap as $candidate => $permName) {
        if ($perms[$permName] ?? false) { $tab = $candidate; break; }
    }
}


$aiLogoPath = (string)($db['settings']['ai_logo_path'] ?? 'assets/ai-logo.png');
$aiLogoFabScale = (string)($db['settings']['ai_logo_fab_scale'] ?? $db['settings']['ai_logo_scale'] ?? '1.18');
$aiLogoBadgeScale = (string)($db['settings']['ai_logo_badge_scale'] ?? '1.12');
$aiLogoFabOffsetX = (string)($db['settings']['ai_logo_fab_offset_x'] ?? $db['settings']['ai_logo_offset_x'] ?? '0');
$aiLogoFabOffsetY = (string)($db['settings']['ai_logo_fab_offset_y'] ?? $db['settings']['ai_logo_offset_y'] ?? '0');
$aiLogoBadgeOffsetX = (string)($db['settings']['ai_logo_badge_offset_x'] ?? $db['settings']['ai_logo_offset_x'] ?? '0');
$aiLogoBadgeOffsetY = (string)($db['settings']['ai_logo_badge_offset_y'] ?? $db['settings']['ai_logo_offset_y'] ?? '0');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    if ($action === 'save_layout') {
        require_admin_permission('manage_layout', $db);
        $db['settings']['site_name'] = trim((string)($_POST['site_name'] ?? '電腦舖門市系統'));
        $db['settings']['subtitle'] = trim((string)($_POST['subtitle'] ?? ''));
        $db['settings']['brand_notice'] = trim((string)($_POST['brand_notice'] ?? ''));
        $db['settings']['sidebar_notice_title'] = trim((string)($_POST['sidebar_notice_title'] ?? '強化重點'));
        $db['settings']['sidebar_notice_text'] = trim((string)($_POST['sidebar_notice_text'] ?? ''));
        $db['settings']['sidebar_usage_text'] = trim((string)($_POST['sidebar_usage_text'] ?? ''));
        $db['settings']['ai_logo_fab_scale'] = (string)max(0.6, min(2.4, (float)($_POST['ai_logo_fab_scale'] ?? $_POST['ai_logo_scale'] ?? '1.18')));
        $db['settings']['ai_logo_badge_scale'] = (string)max(0.6, min(2.4, (float)($_POST['ai_logo_badge_scale'] ?? '1.12')));
        $db['settings']['ai_logo_fab_offset_x'] = (string)max(-80, min(80, (float)($_POST['ai_logo_fab_offset_x'] ?? $_POST['ai_logo_offset_x'] ?? '0')));
        $db['settings']['ai_logo_fab_offset_y'] = (string)max(-80, min(80, (float)($_POST['ai_logo_fab_offset_y'] ?? $_POST['ai_logo_offset_y'] ?? '0')));
        $db['settings']['ai_logo_badge_offset_x'] = (string)max(-80, min(80, (float)($_POST['ai_logo_badge_offset_x'] ?? $_POST['ai_logo_offset_x'] ?? '0')));
        $db['settings']['ai_logo_badge_offset_y'] = (string)max(-80, min(80, (float)($_POST['ai_logo_badge_offset_y'] ?? $_POST['ai_logo_offset_y'] ?? '0')));
        $db['settings']['ai_logo_scale'] = $db['settings']['ai_logo_fab_scale'];
        $db['settings']['ai_logo_offset_x'] = $db['settings']['ai_logo_fab_offset_x'];
        $db['settings']['ai_logo_offset_y'] = $db['settings']['ai_logo_fab_offset_y'];
        if (!empty($_POST['reset_ai_logo'])) {
            $db['settings']['ai_logo_path'] = 'assets/ai-logo.png';
        }
        if (!empty($_FILES['ai_logo_upload']['tmp_name']) && is_uploaded_file($_FILES['ai_logo_upload']['tmp_name'])) {
            $ext = strtolower((string)pathinfo((string)$_FILES['ai_logo_upload']['name'], PATHINFO_EXTENSION));
            if (!in_array($ext, ['png','jpg','jpeg','webp','gif'], true)) {
                redirect_with_message('admin.php?tab=layout', 'AI LOGO 只支援 png / jpg / jpeg / webp / gif', 'err');
            }
            $targetDir = __DIR__ . '/assets';
            if (!is_dir($targetDir) || !is_writable($targetDir)) {
                redirect_with_message('admin.php?tab=layout', 'assets 資料夾不可寫入，無法更新 AI LOGO', 'err');
            }
            $targetName = 'ai-logo-custom.' . $ext;
            $targetPath = $targetDir . '/' . $targetName;
            if (!move_uploaded_file($_FILES['ai_logo_upload']['tmp_name'], $targetPath)) {
                redirect_with_message('admin.php?tab=layout', 'AI LOGO 上傳失敗', 'err');
            }
            $db['settings']['ai_logo_path'] = 'assets/' . $targetName . '?v=' . time();
        }
        log_action($db, 'save_layout', '更新版面管理設定（含 AI 助理 LOGO）');
        if (save_db($db)) redirect_with_message('admin.php?tab=layout', '版面管理已更新');
        redirect_with_message('admin.php?tab=layout', '版面管理更新失敗，請確認 data/db.json 可寫入', 'err');
    }
    if ($action === 'save_permissions') {
        require_admin_permission('manage_permissions', $db);
        $default = default_permissions();
        foreach ($default as $role => $items) {
            foreach ($items as $key => $v) {
                $db['role_permissions'][$role][$key] = isset($_POST['perm'][$role][$key]);
            }
        }
        log_action($db, 'save_permissions', '更新角色權限矩陣');
        if (save_db($db)) redirect_with_message('admin.php?tab=permissions', '權限管理已更新');
        redirect_with_message('admin.php?tab=permissions', '權限管理更新失敗', 'err');
    }
    if ($action === 'add_group') {
        require_admin_permission('manage_groups', $db);
        $key = slugify((string)($_POST['group_key'] ?? $_POST['group_label'] ?? ''));
        if (isset($db['custom_groups'][$key])) redirect_with_message('admin.php?tab=groups', '群組代碼已存在', 'err');
        $db['custom_groups'][$key] = ['label' => trim((string)($_POST['group_label'] ?? $key)), 'icon' => trim((string)($_POST['group_icon'] ?? 'generic')), 'items' => []];
        log_action($db, 'add_group', $key);
        if (save_db($db)) redirect_with_message('admin.php?tab=groups', '已新增類別 / 群組');
        redirect_with_message('admin.php?tab=groups', '新增群組失敗，請確認寫入權限', 'err');
    }
    if ($action === 'delete_group') {
        require_admin_permission('manage_groups', $db);
        $key = (string)($_POST['group_key'] ?? '');
        if (!isset($db['custom_groups'][$key])) redirect_with_message('admin.php?tab=groups', '找不到群組', 'err');
        if (!empty($db['custom_groups'][$key]['locked'])) redirect_with_message('admin.php?tab=groups', '系統內建故障類別不可刪除', 'err');
        unset($db['custom_groups'][$key]);
        log_action($db, 'delete_group', $key);
        if (save_db($db)) redirect_with_message('admin.php?tab=groups', '已刪除類別 / 群組');
        redirect_with_message('admin.php?tab=groups', '刪除群組失敗', 'err');
    }
    if ($action === 'add_scenario') {
        require_admin_permission('manage_scenarios', $db);
        $groupKey = (string)($_POST['scenario_group'] ?? '');
        if (!isset($db['custom_groups'][$groupKey])) redirect_with_message('admin.php?tab=scenarios', '請先建立故障類別 / 群組', 'err');
        $db['custom_groups'][$groupKey]['items'][] = [
            'title' => trim((string)($_POST['scenario_title'] ?? '')),
            'severity' => trim((string)($_POST['scenario_severity'] ?? '中')),
            'steps' => parse_lines((string)($_POST['scenario_steps'] ?? '')),
            'causes' => parse_lines((string)($_POST['scenario_causes'] ?? '')),
            'tests' => parse_lines((string)($_POST['scenario_tests'] ?? '')),
            'fix' => parse_lines((string)($_POST['scenario_fix'] ?? '')),
        ];
        log_action($db, 'add_scenario', $groupKey . ' / ' . ((string)($_POST['scenario_title'] ?? '')));
        if (save_db($db)) redirect_with_message('admin.php?tab=scenarios', '已新增故障情境');
        redirect_with_message('admin.php?tab=scenarios', '新增故障情境失敗', 'err');
    }
    if ($action === 'update_scenario') {
        require_admin_permission('manage_scenarios', $db);
        $originalGroup = (string)($_POST['original_group'] ?? '');
        $originalIndex = (int)($_POST['original_index'] ?? -1);
        $newGroup = (string)($_POST['scenario_group'] ?? '');
        if (!isset($db['custom_groups'][$newGroup])) redirect_with_message('admin.php?tab=scenarios', '請先建立故障類別 / 群組', 'err');
        if (!isset($db['custom_groups'][$originalGroup]['items'][$originalIndex])) redirect_with_message('admin.php?tab=scenarios', '找不到要編輯的故障情境', 'err');
        $updatedScenario = [
            'title' => trim((string)($_POST['scenario_title'] ?? '')),
            'severity' => trim((string)($_POST['scenario_severity'] ?? '中')),
            'steps' => parse_lines((string)($_POST['scenario_steps'] ?? '')),
            'causes' => parse_lines((string)($_POST['scenario_causes'] ?? '')),
            'tests' => parse_lines((string)($_POST['scenario_tests'] ?? '')),
            'fix' => parse_lines((string)($_POST['scenario_fix'] ?? '')),
        ];
        $originalTitle = (string)($db['custom_groups'][$originalGroup]['items'][$originalIndex]['title'] ?? '');
        if ($newGroup === $originalGroup) {
            $db['custom_groups'][$originalGroup]['items'][$originalIndex] = $updatedScenario;
        } else {
            array_splice($db['custom_groups'][$originalGroup]['items'], $originalIndex, 1);
            $db['custom_groups'][$newGroup]['items'][] = $updatedScenario;
        }
        log_action($db, 'update_scenario', $originalGroup . ' / ' . $originalTitle . ' → ' . $newGroup . ' / ' . ($updatedScenario['title'] ?? ''));
        if (save_db($db)) redirect_with_message('admin.php?tab=scenarios', '已更新故障情境');
        redirect_with_message('admin.php?tab=scenarios', '更新故障情境失敗', 'err');
    }
    if ($action === 'delete_scenario') {
        require_admin_permission('manage_scenarios', $db);
        $groupKey = (string)($_POST['group_key'] ?? '');
        $idx = (int)($_POST['scenario_index'] ?? -1);
        if (isset($db['custom_groups'][$groupKey]['items'][$idx])) {
            $title = $db['custom_groups'][$groupKey]['items'][$idx]['title'] ?? '';
            array_splice($db['custom_groups'][$groupKey]['items'], $idx, 1);
            log_action($db, 'delete_scenario', $groupKey . ' / ' . $title);
            if (save_db($db)) redirect_with_message('admin.php?tab=scenarios', '已刪除故障情境');
        }
        redirect_with_message('admin.php?tab=scenarios', '刪除故障情境失敗', 'err');
    }
    if ($action === 'add_user') {
        require_admin_permission('manage_users', $db);
        $username = slugify((string)($_POST['username'] ?? ''));
        foreach ($db['users'] as $u) if (($u['username'] ?? '') === $username) redirect_with_message('admin.php?tab=users', '帳號已存在', 'err');
        $role = trim((string)($_POST['role'] ?? 'staff'));
        if (!in_array($role, ['staff','manager','admin'], true)) $role = 'staff';
        $db['users'][] = ['username'=>$username,'display_name'=>trim((string)($_POST['display_name'] ?? $username)),'role'=>$role,'password_hash'=>hash_password((string)($_POST['password'] ?? '123456')),'last_login'=>''];
        log_action($db, 'add_user', $username);
        if (save_db($db)) redirect_with_message('admin.php?tab=users', '已新增使用者');
        redirect_with_message('admin.php?tab=users', '新增使用者失敗', 'err');
    }
    if ($action === 'delete_user') {
        require_admin_permission('manage_users', $db);
        $username = (string)($_POST['username'] ?? '');
        if ($username === ($user['username'] ?? '')) redirect_with_message('admin.php?tab=users', '不能刪除目前登入的帳號', 'err');
        $db['users'] = array_values(array_filter($db['users'], fn($u) => ($u['username'] ?? '') !== $username));
        log_action($db, 'delete_user', $username);
        if (save_db($db)) redirect_with_message('admin.php?tab=users', '已刪除使用者');
        redirect_with_message('admin.php?tab=users', '刪除使用者失敗', 'err');
    }
    if ($action === 'change_my_password') {
        $new = trim((string)($_POST['new_password'] ?? ''));
        if ($new === '') redirect_with_message('admin.php?tab=account', '新密碼不可空白', 'err');
        foreach ($db['users'] as &$u) if (($u['username'] ?? '') === ($user['username'] ?? '')) { $u['password_hash'] = hash_password($new); break; }
        unset($u);
        log_action($db, 'change_my_password', '修改自己的密碼');
        if (save_db($db)) redirect_with_message('admin.php?tab=account', '密碼已更新');
        redirect_with_message('admin.php?tab=account', '密碼更新失敗', 'err');
    }
}
$customCount = 0;
foreach (($db['custom_groups'] ?? []) as $g) $customCount += count($g['items'] ?? []);
$mode = is_db_writable() ? 'NAS 同步中' : 'NAS 唯讀';
$modeColor = is_db_writable() ? '#22c55e' : '#ef4444';
$roleLabels = ['admin'=>'系統管理員','manager'=>'門市主管','staff'=>'門市人員'];
$systemVersion = (string)($db['version'] ?? 'v2.4.4');
$totalScenarioCount = 0; foreach (($db['custom_groups'] ?? []) as $g) { $totalScenarioCount += count($g['items'] ?? []); }
$permLabels = [
    'access_frontend'=>'可進前台','access_admin'=>'可進後台','manage_groups'=>'可管理故障類別/群組','manage_scenarios'=>'可管理故障情境',
    'manage_users'=>'可管理使用者','manage_layout'=>'可管理版面','manage_permissions'=>'可管理權限','view_logs'=>'可看操作紀錄','change_settings'=>'保留系統設定權限'
];
$editingScenario = null;
$editingGroupKey = '';
$editingIndex = -1;
if (($perms['manage_scenarios'] ?? false) && isset($_GET['edit_group'], $_GET['edit_idx'])) {
    $candidateGroup = (string)($_GET['edit_group'] ?? '');
    $candidateIndex = (int)($_GET['edit_idx'] ?? -1);
    if (isset($db['custom_groups'][$candidateGroup]['items'][$candidateIndex])) {
        $editingGroupKey = $candidateGroup;
        $editingIndex = $candidateIndex;
        $editingScenario = $db['custom_groups'][$candidateGroup]['items'][$candidateIndex];
        $tab = 'scenarios';
    }
}
?><!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title><?php echo h($db['settings']['site_name'] ?? '電腦舖門市系統'); ?>｜後台管理</title>
<style>
:root{--bg:#0b0f14;--line:rgba(255,255,255,.1);--ink:#e5e7eb;--muted:#9ca3af;--pri:#fbbf24;--pri2:#f59e0b}
*{box-sizing:border-box}html,body{margin:0;height:100%}body{font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI","Noto Sans TC",sans-serif;background:radial-gradient(1100px 700px at 12% 0%, rgba(251,191,36,.10), transparent 55%),radial-gradient(900px 650px at 92% 18%, rgba(59,130,246,.09), transparent 50%), var(--bg);color:var(--ink)}
.app{display:grid;grid-template-columns:290px 1fr;min-height:100vh}aside{background:linear-gradient(180deg, rgba(17,24,39,.95), rgba(11,15,20,.97));border-right:1px solid var(--line);padding:16px 14px;position:sticky;top:0;height:100vh;overflow:auto}main{padding:18px 18px 40px}
.brand{padding:14px;border:1px solid var(--line);border-radius:18px;background:rgba(0,0,0,.22);margin-bottom:12px}.brand h1{margin:0;font-size:20px}.sub{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.6}
.sidebox{margin-top:12px;padding:12px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.03)}.lamp{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:12px;background:rgba(255,255,255,.03);border:1px solid var(--line);margin-top:10px}
.menu{display:flex;flex-direction:column;gap:8px;margin-top:14px}.menu a{display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:14px;border:1px solid var(--line);background:rgba(255,255,255,.02);color:inherit;text-decoration:none}.menu a.active,.menu a:hover{border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.10)}
.topbar{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:14px;border:1px solid var(--line);border-radius:18px;background:rgba(0,0,0,.24)}.topbar h2{margin:0;font-size:20px}.muted{color:var(--muted);font-size:13px}
.notice{margin-top:12px;padding:12px 13px;border-radius:14px;border:1px solid var(--line)}.notice.ok{background:rgba(34,197,94,.10);border-color:rgba(34,197,94,.28);color:#bbf7d0}.notice.err{background:rgba(239,68,68,.10);border-color:rgba(239,68,68,.28);color:#fecaca}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}.box,.card{border:1px solid var(--line);border-radius:18px;padding:14px;background:linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02))}.box .num{font-size:28px;font-weight:900}.box .lab{font-size:12px;color:var(--muted)}
.section{display:none;margin-top:14px}.section.active{display:block}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
input,select,textarea{width:100%;padding:10px 11px;border-radius:14px;border:1px solid var(--line);background:rgba(0,0,0,.35);color:var(--ink);outline:none}textarea{min-height:110px;resize:vertical}
label{display:block;font-size:13px;color:#fff;margin:10px 0 6px}button{border:none;border-radius:14px;padding:10px 12px;background:var(--pri);color:#1f2937;font-weight:800;cursor:pointer}button:hover{background:var(--pri2)}button.bad{background:rgba(239,68,68,.18);color:#fecaca;border:1px solid rgba(239,68,68,.35)}
table{width:100%;border-collapse:separate;border-spacing:0;border:1px solid var(--line);border-radius:16px;overflow:hidden}th,td{padding:10px;font-size:13px;border-bottom:1px solid var(--line);vertical-align:top}th{text-align:left;color:var(--muted);background:rgba(255,255,255,.03)}tr:last-child td{border-bottom:none}small{color:var(--muted)}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}code{background:rgba(255,255,255,.05);padding:2px 6px;border-radius:8px}.permTable th,.permTable td{text-align:center}.permTable th:first-child,.permTable td:first-child{text-align:left}

.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.previewWrap{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;align-items:start;margin:12px 0 8px}
.previewStage{position:relative;min-height:360px;border:1px solid var(--line);border-radius:18px;padding:16px;background:
linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)),
radial-gradient(600px 280px at 82% 10%, rgba(251,191,36,.08), transparent 55%),
#0d1117;overflow:hidden}
.previewStage h4{margin:0 0 8px;font-size:14px}
.previewHint{font-size:12px;color:var(--muted);line-height:1.6}
.previewDock{position:absolute;right:18px;bottom:18px;display:grid;gap:16px;justify-items:end}
.previewFab{width:84px;height:84px;border-radius:999px;background:#05070b;border:1px solid rgba(255,255,255,.18);display:grid;place-items:center;overflow:hidden;box-shadow:0 0 0 1px rgba(251,191,36,.16),0 14px 35px rgba(0,0,0,.32)}
.previewFab img,.previewBadge img{width:100%;height:100%;object-fit:contain;display:block}
.previewChat{width:min(100%,340px);border:1px solid rgba(255,255,255,.12);border-radius:22px;background:linear-gradient(180deg, rgba(15,23,42,.97), rgba(2,6,23,.97));box-shadow:0 14px 40px rgba(0,0,0,.35);overflow:hidden}
.previewChatHead{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,.08)}
.previewBadge{width:44px;height:44px;border-radius:999px;overflow:hidden;background:#05070b;border:1px solid rgba(255,255,255,.14);display:grid;place-items:center;flex:none}
.previewChatTitle{font-weight:800;color:#fff}
.previewChatSub{font-size:12px;color:#cbd5e1}
.previewChatBody{padding:14px 16px}
.previewBubble{border-radius:16px;padding:12px 13px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);font-size:13px;line-height:1.7;color:#f8fafc}
.controlCard{border:1px solid var(--line);border-radius:16px;padding:14px;background:rgba(255,255,255,.03)}
.rangeRow{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:10px;align-items:center}
.rangeRow input[type=range]{accent-color:#fbbf24;padding:0}
.rangeSet{display:grid;gap:12px;margin-top:8px}
@media (max-width:1100px){.previewWrap{grid-template-columns:1fr}.grid2{grid-template-columns:1fr 1fr}}
@media (max-width:760px){.grid2{grid-template-columns:1fr}.previewStage{min-height:320px}}

@media (max-width:1100px){.app{grid-template-columns:1fr}aside{position:relative;height:auto}.grid,.row{grid-template-columns:1fr 1fr}}@media (max-width:760px){.grid,.row{grid-template-columns:1fr}main{padding:14px}}
</style></head><body>
<div class="app"><aside>
<div class="brand"><h1><?php echo h($db['settings']['site_name'] ?? '電腦舖門市系統'); ?></h1><div class="sub"><?php echo h($db['settings']['subtitle'] ?? '後台管理中心'); ?></div></div>
<div class="sidebox"><div><b><?php echo h($user['display_name'] ?? $user['username'] ?? ''); ?></b></div><div class="muted">帳號：<?php echo h($user['username'] ?? ''); ?> ｜ 角色：<?php echo h($roleLabels[$user['role'] ?? 'staff'] ?? ($user['role'] ?? '')); ?></div><div class="lamp"><span style="width:10px;height:10px;border-radius:999px;background:<?php echo $modeColor; ?>;display:inline-block"></span><span><?php echo h($mode); ?></span></div><div class="actions"><a href="index.php"><button type="button">回前台</button></a><a href="logout.php"><button type="button">登出</button></a></div></div>
<nav class="menu">
<a href="#dashboard" data-tab="dashboard" class="<?php echo $tab==='dashboard' ? 'active':''; ?>">📊 儀表板</a>
<?php if ($perms['manage_groups']): ?><a href="#groups" data-tab="groups" class="<?php echo $tab==='groups' ? 'active':''; ?>">📁 故障類別/群組</a><?php endif; ?>
<?php if ($perms['manage_scenarios']): ?><a href="#scenarios" data-tab="scenarios" class="<?php echo $tab==='scenarios' ? 'active':''; ?>">🛠 故障情境</a><?php endif; ?>
<?php if ($perms['manage_users']): ?><a href="#users" data-tab="users" class="<?php echo $tab==='users' ? 'active':''; ?>">👤 使用者</a><?php endif; ?>
<?php if ($perms['manage_layout']): ?><a href="#layout" data-tab="layout" class="<?php echo $tab==='layout' ? 'active':''; ?>">🎨 版面管理</a><?php endif; ?>
<?php if ($perms['manage_permissions']): ?><a href="#permissions" data-tab="permissions" class="<?php echo $tab==='permissions' ? 'active':''; ?>">🛡 權限管理</a><?php endif; ?>
<a href="#account" data-tab="account" class="<?php echo $tab==='account' ? 'active':''; ?>">🔐 我的密碼</a>
<?php if ($perms['view_logs']): ?><a href="#logs" data-tab="logs" class="<?php echo $tab==='logs' ? 'active':''; ?>">📜 操作紀錄</a><?php endif; ?>
</nav></aside>
<main>
<div class="topbar"><div><h2>後台管理中心</h2><div class="muted">v2.5.5：版面管理新增 AI 助理雙預覽、即時調整與開啟後徽章獨立設定。</div></div><div class="muted">資料模式：<?php echo h($mode); ?></div></div>
<?php if ($msg): ?><div class="notice <?php echo h($type); ?>"><?php echo h($msg); ?></div><?php endif; ?>

<section id="dashboard" class="section active"><div class="grid"><div class="box"><div class="num">218</div><div class="lab">內建情境數</div></div><div class="box"><div class="num"><?php echo count($db['custom_groups'] ?? []); ?></div><div class="lab">故障類別數</div></div><div class="box"><div class="num"><?php echo $customCount; ?></div><div class="lab">新增情境數</div></div><div class="box"><div class="num"><?php echo count($db['users'] ?? []); ?></div><div class="lab">系統帳號數</div></div></div>
<div class="row"><div class="card"><h3>目前權限摘要</h3><ul>
<?php foreach ($permLabels as $key => $label): ?><?php if ($perms[$key] ?? false): ?><li><?php echo h($label); ?></li><?php endif; ?><?php endforeach; ?>
</ul></div><div class="card"><h3>部署提醒</h3><ul><li>請確認 <code>data/db.json</code> 可寫入</li><li>前台入口：<code>index.php</code></li><li>後台入口：<code>admin.php</code></li><li>登入入口：<code>login.php</code></li></ul></div></div></section>

<?php if ($perms['manage_groups']): ?><section id="groups" class="section"><div class="row"><div class="card"><h3>新增故障類別 / 群組</h3><form method="post"><input type="hidden" name="action" value="add_group"><label>群組代碼（可留空，自動產生）</label><input name="group_key" placeholder="例如: store_pos_custom"><label>群組名稱</label><input name="group_label" required placeholder="例如：門市情境｜自訂區"><label>Icon</label><select name="group_icon"><option value="generic">generic</option><option value="storage">storage</option><option value="power">power</option><option value="battery">battery</option><option value="display">display</option><option value="camera">camera</option><option value="apps">apps</option></select><div class="actions"><button type="submit">新增群組</button></div></form></div>
<div class="card"><h3>現有故障類別（含內建）</h3><table><tr><th>代碼</th><th>名稱</th><th>情境數</th><th>類型</th><th>操作</th></tr><?php foreach (($db['custom_groups'] ?? []) as $key => $group): ?><tr><td><code><?php echo h((string)$key); ?></code></td><td><?php echo h((string)($group['label'] ?? '')); ?></td><td><?php echo count($group['items'] ?? []); ?></td><td><?php echo !empty($group['locked']) ? '內建類別' : '自訂類別'; ?></td><td><?php if (!empty($group['locked'])): ?><small>內建不可刪除</small><?php else: ?><form method="post" onsubmit="return confirm('確定刪除此群組？群組內情境也會一起刪除。');"><input type="hidden" name="action" value="delete_group"><input type="hidden" name="group_key" value="<?php echo h((string)$key); ?>"><button class="bad" type="submit">刪除</button></form><?php endif; ?></td></tr><?php endforeach; ?><?php if (empty($db['custom_groups'])): ?><tr><td colspan="5"><small>目前尚無故障類別。</small></td></tr><?php endif; ?></table></div></div></section><?php endif; ?>

<?php if ($perms['manage_scenarios']): ?><section id="scenarios" class="section"><div class="row"><div class="card"><h3><?php echo $editingScenario ? '編輯故障情境' : '新增故障情境'; ?></h3><form method="post"><input type="hidden" name="action" value="<?php echo $editingScenario ? 'update_scenario' : 'add_scenario'; ?>"><?php if ($editingScenario): ?><input type="hidden" name="original_group" value="<?php echo h($editingGroupKey); ?>"><input type="hidden" name="original_index" value="<?php echo (int)$editingIndex; ?>"><?php endif; ?><label>放入哪個群組</label><select name="scenario_group" required><option value="">請選擇故障類別</option><?php foreach (($db['custom_groups'] ?? []) as $key => $group): ?><option value="<?php echo h((string)$key); ?>" <?php echo (($editingGroupKey !== '' ? $editingGroupKey : '') === (string)$key) ? 'selected' : ''; ?>><?php echo h((string)($group['label'] ?? $key)); ?><?php echo !empty($group['locked']) ? '（預設）' : ''; ?></option><?php endforeach; ?></select><small>下拉選單已與前台故障類別同步；若需額外分類，可先到「故障類別 / 群組管理」新增。</small><label>情境標題</label><input name="scenario_title" required placeholder="例如：POS 小白單無法列印" value="<?php echo h((string)($editingScenario['title'] ?? '')); ?>"><label>風險等級</label><select name="scenario_severity"><?php $scenarioSeverity = (string)($editingScenario['severity'] ?? '中'); foreach (['低','中','高','Critical'] as $level): ?><option value="<?php echo h($level); ?>" <?php echo $scenarioSeverity === $level ? 'selected' : ''; ?>><?php echo h($level); ?></option><?php endforeach; ?></select><label>排查步驟（每行一項）</label><textarea name="scenario_steps"><?php echo h(implode("
", $editingScenario['steps'] ?? [])); ?></textarea><label>可能原因（每行一項）</label><textarea name="scenario_causes"><?php echo h(implode("
", $editingScenario['causes'] ?? [])); ?></textarea><label>建議測試（每行一項）</label><textarea name="scenario_tests"><?php echo h(implode("
", $editingScenario['tests'] ?? [])); ?></textarea><label>建議處置（每行一項）</label><textarea name="scenario_fix"><?php echo h(implode("
", $editingScenario['fix'] ?? [])); ?></textarea><div class="actions"><button type="submit"><?php echo $editingScenario ? '儲存修改' : '新增情境'; ?></button><?php if ($editingScenario): ?><a href="admin.php?tab=scenarios"><button type="button">取消編輯</button></a><?php endif; ?></div></form></div>
<div class="card"><h3>現有故障情境</h3><table><tr><th>故障類別</th><th>標題</th><th>風險</th><th>操作</th></tr><?php foreach (($db['custom_groups'] ?? []) as $key => $group): ?><?php foreach (($group['items'] ?? []) as $idx => $item): ?><tr><td><?php echo h((string)($group['label'] ?? $key)); ?></td><td><?php echo h((string)($item['title'] ?? '')); ?></td><td><?php echo h((string)($item['severity'] ?? '')); ?></td><td><div class="actions"><a href="admin.php?tab=scenarios&edit_group=<?php echo urlencode((string)$key); ?>&edit_idx=<?php echo (int)$idx; ?>"><button type="button" style="background:#facc15;color:#111827;font-weight:800;border:0">✏ 編輯</button></a><form method="post" onsubmit="return confirm('確定刪除此情境？');"><input type="hidden" name="action" value="delete_scenario"><input type="hidden" name="group_key" value="<?php echo h((string)$key); ?>"><input type="hidden" name="scenario_index" value="<?php echo (int)$idx; ?>"><button class="bad" type="submit">刪除</button></form></div></td></tr><?php endforeach; ?><?php endforeach; ?><?php if ($customCount === 0): ?><tr><td colspan="4"><small>這裡會列出全部故障情境，包含系統預設情境與你後台新增的情境。</small></td></tr><?php endif; ?></table></div></div></section><?php endif; ?>

<?php if ($perms['manage_users']): ?><section id="users" class="section"><div class="row"><div class="card"><h3>新增使用者</h3><form method="post"><input type="hidden" name="action" value="add_user"><label>帳號</label><input name="username" required placeholder="例如：amy"><label>顯示名稱</label><input name="display_name" required placeholder="例如：Amy 店長"><label>角色</label><select name="role"><option value="staff">staff</option><option value="manager">manager</option><option value="admin">admin</option></select><label>初始密碼</label><input name="password" required value="123456"><div class="actions"><button type="submit">新增使用者</button></div></form></div>
<div class="card"><h3>使用者清單</h3><table><tr><th>帳號</th><th>名稱</th><th>角色</th><th>細節權限</th><th>最後登入</th><th>操作</th></tr><?php foreach (($db['users'] ?? []) as $u): $up=current_permissions($db,$u); ?><tr><td><code><?php echo h((string)($u['username'] ?? '')); ?></code></td><td><?php echo h((string)($u['display_name'] ?? '')); ?></td><td><?php echo h((string)($u['role'] ?? '')); ?></td><td><small><?php $enabled=[]; foreach($permLabels as $k=>$lbl){ if($up[$k] ?? false) $enabled[]=$lbl; } echo h(implode('、',$enabled)); ?></small></td><td><?php echo h((string)($u['last_login'] ?? '')); ?></td><td><?php if (($u['username'] ?? '') !== ($user['username'] ?? '')): ?><form method="post" onsubmit="return confirm('確定刪除此使用者？');"><input type="hidden" name="action" value="delete_user"><input type="hidden" name="username" value="<?php echo h((string)($u['username'] ?? '')); ?>"><button class="bad" type="submit">刪除</button></form><?php else: ?><small>目前登入者</small><?php endif; ?></td></tr><?php endforeach; ?></table></div></div></section><?php endif; ?>

<?php if ($perms['manage_layout']): ?><section id="layout" class="section"><div class="row"><div class="card"><h3>版面管理</h3><form method="post" enctype="multipart/form-data"><input type="hidden" name="action" value="save_layout"><label>系統名稱</label><input name="site_name" value="<?php echo h((string)($db['settings']['site_name'] ?? '')); ?>"><label>副標題</label><input name="subtitle" value="<?php echo h((string)($db['settings']['subtitle'] ?? '')); ?>"><label>登入頁提示文字</label><textarea name="brand_notice"><?php echo h((string)($db['settings']['brand_notice'] ?? '')); ?></textarea><label>前台左側說明標題</label><input name="sidebar_notice_title" value="<?php echo h((string)($db['settings']['sidebar_notice_title'] ?? '')); ?>"><label>前台左側說明內容</label><textarea name="sidebar_notice_text"><?php echo h((string)($db['settings']['sidebar_notice_text'] ?? '')); ?></textarea><label>前台使用方式文字</label><textarea name="sidebar_usage_text"><?php echo h((string)($db['settings']['sidebar_usage_text'] ?? '')); ?></textarea>

<div style="margin-top:18px;padding:14px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.03)">
  <h4 style="margin:0 0 12px">AI 助理 LOGO 設定</h4>
  <div class="previewWrap">
    <div class="previewStage">
      <h4>即時預覽</h4>
      <div class="previewHint">左邊調整後會即時反映在下方預覽。上方是右下角浮動按鈕，下方是「點進 AI 助理後」的對話視窗徽章。</div>
      <div class="previewDock">
        <div class="previewChat">
          <div class="previewChatHead">
            <div class="previewBadge"><img id="previewBadgeImg" src="<?php echo h($aiLogoPath); ?>" alt="AI LOGO"></div>
            <div>
              <div class="previewChatTitle">電腦舖 AI 助理</div>
              <div class="previewChatSub">開啟後視窗徽章預覽</div>
            </div>
          </div>
          <div class="previewChatBody">
            <div class="previewBubble">你好，我可以協助你快速找到故障情境。這裡會即時預覽你目前設定的 AI LOGO 大小與置中位置。</div>
          </div>
        </div>
        <div class="previewFab"><img id="previewFabImg" src="<?php echo h($aiLogoPath); ?>" alt="AI LOGO"></div>
      </div>
    </div>
    <div class="controlCard">
      <label>更換 AI 助理 LOGO</label>
      <input id="ai_logo_upload" type="file" name="ai_logo_upload" accept=".png,.jpg,.jpeg,.webp,.gif,image/png,image/jpeg,image/webp,image/gif">
      <div class="muted" style="font-size:13px;margin-top:8px">可分別設定右下角浮動按鈕，以及點進 AI 助理後左上角徽章的大小與位置。</div>

      <div class="rangeSet">
        <div>
          <label>浮動按鈕 LOGO 大小倍率</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_fab_scale_range" min="0.6" max="2.4" step="0.01" value="<?php echo h($aiLogoFabScale); ?>">
            <input type="number" name="ai_logo_fab_scale" id="ai_logo_fab_scale" step="0.01" min="0.6" max="2.4" value="<?php echo h($aiLogoFabScale); ?>">
          </div>
        </div>
        <div>
          <label>浮動按鈕 LOGO 水平位移（px）</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_fab_offset_x_range" min="-80" max="80" step="1" value="<?php echo h($aiLogoFabOffsetX); ?>">
            <input type="number" name="ai_logo_fab_offset_x" id="ai_logo_fab_offset_x" step="1" min="-80" max="80" value="<?php echo h($aiLogoFabOffsetX); ?>">
          </div>
        </div>
        <div>
          <label>浮動按鈕 LOGO 垂直位移（px）</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_fab_offset_y_range" min="-80" max="80" step="1" value="<?php echo h($aiLogoFabOffsetY); ?>">
            <input type="number" name="ai_logo_fab_offset_y" id="ai_logo_fab_offset_y" step="1" min="-80" max="80" value="<?php echo h($aiLogoFabOffsetY); ?>">
          </div>
        </div>

        <div>
          <label>對話徽章 LOGO 大小倍率</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_badge_scale_range" min="0.6" max="2.4" step="0.01" value="<?php echo h($aiLogoBadgeScale); ?>">
            <input type="number" name="ai_logo_badge_scale" id="ai_logo_badge_scale" step="0.01" min="0.6" max="2.4" value="<?php echo h($aiLogoBadgeScale); ?>">
          </div>
        </div>
        <div>
          <label>對話徽章 LOGO 水平位移（px）</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_badge_offset_x_range" min="-80" max="80" step="1" value="<?php echo h($aiLogoBadgeOffsetX); ?>">
            <input type="number" name="ai_logo_badge_offset_x" id="ai_logo_badge_offset_x" step="1" min="-80" max="80" value="<?php echo h($aiLogoBadgeOffsetX); ?>">
          </div>
        </div>
        <div>
          <label>對話徽章 LOGO 垂直位移（px）</label>
          <div class="rangeRow">
            <input type="range" id="ai_logo_badge_offset_y_range" min="-80" max="80" step="1" value="<?php echo h($aiLogoBadgeOffsetY); ?>">
            <input type="number" name="ai_logo_badge_offset_y" id="ai_logo_badge_offset_y" step="1" min="-80" max="80" value="<?php echo h($aiLogoBadgeOffsetY); ?>">
          </div>
        </div>
      </div>

      <label style="display:flex;align-items:center;gap:8px;margin-top:12px"><input type="checkbox" name="reset_ai_logo" value="1" style="width:auto">還原成系統預設 AI LOGO</label>
    </div>
  </div>
</div>

<div class="actions"><button type="submit">儲存版面設定</button></div></form></div>
<div class="card"><h3>版面管理說明</h3><ul><li>登入頁預設帳號顯示已移除。</li><li>前台與後台標題會套用系統名稱與副標題。</li><li>左側欄說明文字可在這裡直接修改。</li><li>AI 助理 LOGO 可自由更換，並可分別調整浮動按鈕與開啟後徽章，且支援即時預覽。</li></ul></div></div></section><?php endif; ?>

<?php if ($perms['manage_permissions']): ?><section id="permissions" class="section"><div class="card"><h3>權限管理</h3><form method="post"><input type="hidden" name="action" value="save_permissions"><table class="permTable"><tr><th>權限項目</th><th>admin</th><th>manager</th><th>staff</th></tr><?php foreach ($permLabels as $key => $label): ?><tr><td><?php echo h($label); ?><br><small><code><?php echo h($key); ?></code></small></td><?php foreach (['admin','manager','staff'] as $role): ?><td><input type="checkbox" name="perm[<?php echo h($role); ?>][<?php echo h($key); ?>]" <?php echo !empty($db['role_permissions'][$role][$key]) ? 'checked' : ''; ?>></td><?php endforeach; ?></tr><?php endforeach; ?></table><div class="actions"><button type="submit">儲存權限矩陣</button></div></form></div></section><?php endif; ?>

<section id="account" class="section"><div class="card"><h3>修改我的密碼</h3><form method="post"><input type="hidden" name="action" value="change_my_password"><label>新密碼</label><input name="new_password" type="password" required><div class="actions"><button type="submit">更新密碼</button></div></form></div></section>
<?php if ($perms['view_logs']): ?><section id="logs" class="section"><div class="card"><h3>最近操作紀錄</h3><table><tr><th>時間</th><th>使用者</th><th>動作</th><th>內容</th><th>IP</th></tr><?php foreach (array_reverse(array_slice($db['logs'] ?? [], -80)) as $log): ?><tr><td><?php echo h((string)($log['time'] ?? '')); ?></td><td><?php echo h((string)($log['user'] ?? '')); ?></td><td><?php echo h((string)($log['action'] ?? '')); ?></td><td><?php echo h((string)($log['detail'] ?? '')); ?></td><td><?php echo h((string)($log['ip'] ?? '')); ?></td></tr><?php endforeach; ?><?php if (empty($db['logs'])): ?><tr><td colspan="5"><small>目前尚無紀錄。</small></td></tr><?php endif; ?></table></div></section><?php endif; ?>
</main></div>
<script>
const initialTab = <?php echo json_encode($tab, JSON_UNESCAPED_UNICODE); ?>;
function openTab(name){ document.querySelectorAll('.section').forEach(s => s.classList.toggle('active', s.id === name)); document.querySelectorAll('.menu a[data-tab]').forEach(a => a.classList.toggle('active', a.dataset.tab === name)); const u=new URL(window.location.href); u.searchParams.set('tab', name); history.replaceState(null,'',u); }
document.querySelectorAll('.menu a[data-tab]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); openTab(a.dataset.tab); }));
openTab(initialTab || 'dashboard');

const liveMap = [
  ['ai_logo_fab_scale','ai_logo_fab_scale_range'],
  ['ai_logo_fab_offset_x','ai_logo_fab_offset_x_range'],
  ['ai_logo_fab_offset_y','ai_logo_fab_offset_y_range'],
  ['ai_logo_badge_scale','ai_logo_badge_scale_range'],
  ['ai_logo_badge_offset_x','ai_logo_badge_offset_x_range'],
  ['ai_logo_badge_offset_y','ai_logo_badge_offset_y_range'],
];
function syncPair(textId, rangeId){
  const text=document.getElementById(textId);
  const range=document.getElementById(rangeId);
  if(!text || !range) return;
  const push=(val, fromRange=false)=>{ 
    const v=String(val);
    text.value=v;
    range.value=v;
    applyAiLogoPreview();
  };
  text.addEventListener('input', ()=>push(text.value));
  range.addEventListener('input', ()=>push(range.value, true));
}
function applyAiLogoPreview(){
  const fabImg=document.getElementById('previewFabImg');
  const badgeImg=document.getElementById('previewBadgeImg');
  if(!fabImg || !badgeImg) return;
  const fabScale=parseFloat(document.getElementById('ai_logo_fab_scale')?.value || '1.18');
  const fabX=parseFloat(document.getElementById('ai_logo_fab_offset_x')?.value || '0');
  const fabY=parseFloat(document.getElementById('ai_logo_fab_offset_y')?.value || '0');
  const badgeScale=parseFloat(document.getElementById('ai_logo_badge_scale')?.value || '1.12');
  const badgeX=parseFloat(document.getElementById('ai_logo_badge_offset_x')?.value || '0');
  const badgeY=parseFloat(document.getElementById('ai_logo_badge_offset_y')?.value || '0');
  fabImg.style.transform=`translate(${fabX}px, ${fabY}px) scale(${fabScale})`;
  badgeImg.style.transform=`translate(${badgeX}px, ${badgeY}px) scale(${badgeScale})`;
  fabImg.style.transformOrigin='center center';
  badgeImg.style.transformOrigin='center center';
}
liveMap.forEach(pair => syncPair(pair[0], pair[1]));
document.getElementById('ai_logo_upload')?.addEventListener('change', (e) => {
  const file = e.target.files && e.target.files[0];
  if(!file) return;
  const url = URL.createObjectURL(file);
  const fabImg=document.getElementById('previewFabImg');
  const badgeImg=document.getElementById('previewBadgeImg');
  if(fabImg) fabImg.src=url;
  if(badgeImg) badgeImg.src=url;
  applyAiLogoPreview();
});
applyAiLogoPreview();

</script></body></html>
<div style="position:fixed;right:12px;bottom:10px;background:#111827;color:#facc15;padding:6px 10px;border-radius:999px;font:12px sans-serif;z-index:9999;border:1px solid #374151">版本 v2.6.2</div>
