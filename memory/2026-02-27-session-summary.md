# 2026-02-27 工作總結

## 一、銷貨資料匯入系統（重大修復）

### 問題與解決
1. **資料重複問題**
   - 建立 unique constraint：`date + salesperson + customer_name + product_code + product_name + quantity + amount`
   - 新增檔案記錄機制防止 Parser 重複執行

2. **退貨處理**
   - 修正 Parser 負數記錄處理：`lstrip('-').isdigit()`
   - 林榮祺 2/3 退貨 $91,890 正確計入

3. **每日增量模式**
   - 完成 2/26 資料匯入（33 筆）
   - 總計 8,151 筆銷貨資料

## 二、需求表網站

### 完成項目
- staff_passwords 資料表建立
- 10 位員工密碼匯入
- 主管單位修正（莊圍迪→豐原門市，萬書佑→業務部）
- 欄位高度統一（44px）
- 首頁按鈕開新分頁（target="_blank"）
- needs 資料表清空等待重建

## 三、看板網站備份機制

### Git + OneDrive 雙重備份
```bash
# Git 本地倉庫
Location: /Users/aiserver/.openclaw/workspace/dashboard-site/.git/
Initial commit: 16 files, 8,474 lines

# 每日 04:00 自動備份（auto_backup.sh）
- company_HHMM.db（資料庫）
- parser_scripts_HHMM.tar.gz（Parser）
- dashboard_site_HHMM.tar.gz（看板網站）
```

## 四、關鍵經驗

1. **Unique Constraint 設計**：必須包含能區分不同記錄的所有欄位
2. **負數處理**：使用 `lstrip('-')` 而非 `isdigit()`
3. **雙重防護**：流程防護 + 資料防護
4. **Git 版本控制**：本地追蹤 + 雲端備份

---
_總結時間：2026-02-27 凌晨_
