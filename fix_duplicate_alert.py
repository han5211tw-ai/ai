#!/usr/bin/env python3
# 修復重複告警問題 - 直接插入新代碼

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到第 712 行：# 資料庫連線失敗也發送告警
# 在第 712-728 行之間插入新的邏輯
new_lines = [
    '        # 資料庫連線失敗也發送告警，但要避免重複通知\n',
    '        try:\n',
    "            # 檢查是否在 30 分鐘內已發送過「系統嚴重告警」\n",
    "            conn = get_db_connection()\n",
    '            cursor = conn.cursor()\n',
    '            cursor.execute("""\n',
    "                SELECT COUNT(*) as alert_count\n",
    "                FROM notification_logs\n",
    "                WHERE notification_type = '系統嚴重告警'\n",
    "                AND status != 'failed'\n",
    "                AND created_at >= datetime('now', '-30 minutes')\n",
    '            """)\n',
    '            alert_count = cursor.fetchone()["alert_count"]\n',
    '            conn.close()\n',
    '            \n',
    '            # 只在首次發現問題時發送，避免重複\n',
    '            if alert_count == 0:\n',
    '                alert_msg = f"""🚨 <b>系統嚴重告警</b>\n',
    '\n',
    '資料庫連線異常！\n',
    '錯誤：{str(e)[:100]}\n',
    '\n',
    '時間：{datetime.now().strftime(\'%Y-%m-%d %H:%M:%S\')}"""\n',
    "                send_telegram_notification(alert_msg, TELEGRAM_CHAT_ID, notification_type='系統嚴重告警')\n",
    '                print("[HEALTH MONITOR] 已發送系統嚴重告警（避免重複)")\n',
    '            else:\n',
    '                print(f"[HEALTH MONITOR] 檢測到資料庫連線異常，但 30 分鐘內已發送告警（避免重複)")\n',
    '        except:\n',
    '            print("[HEALTH MONITOR] 發送告警時也失敗了")\n',
]

# 從第 712 行刪除到 728 行（包含）
# 插入新代碼
start_index = 711  # 0-based: 第 712 行
end_index = 728    # 0-based: 第 729 行

# 刪除舊代碼
del lines[start_index:end_index+1]

# 插入新代碼
for i, line in enumerate(new_lines):
    lines.insert(start_index + i, line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ 修復完成！")
