# 2026-02-27 - 外勤服務紀錄系統與客戶搜尋功能

## 一、外勤服務紀錄網站 (service_record.html)

### 功能架構
- **登入權限**：業務部三人（鄭宇晉/梁仁佑可編輯，萬書佑唯讀）
- **批次輸入**：五欄同時填寫，橫排欄位節省空間
- **時間限制**：送出後三天內可修改（以 updated_at 計算）
- **資料儲存**：串接後端 API，非 localStorage

### 欄位設計
| 欄位 | 說明 |
|------|------|
| 日期 | 預設今天，不可選未來 |
| 服務分類 | 7種：交機、施工、設備問題、網通設定、現場維修、門市支援、其它 |
| 門市選擇 | 選「門市支援」才顯示（豐原/潭子/大雅） |
| 客戶搜尋 | 反向搜尋（輸入姓名/手機→選擇→回填customer_id） |
| 客戶來源 | 業務聯絡、門市轉介 |
| 合約客戶 | 是/否 |
| 服務事宜 | 文字描述 |

### API 端點
- `GET /api/service-records` - 獲取列表
- `POST /api/service-records` - 批次新增
- `DELETE /api/service-records/<id>` - 刪除

## 二、客戶反向搜尋功能

### 實現方式
- **輸入**：客戶姓名或手機號碼
- **搜尋**：oninput + debounce 300ms
- **顯示**：下拉清單（姓名、電話、編號）
- **選擇**：自動回填 customer_id 到隱藏欄位
- **顯示**：已選客戶資訊 + 清除重選按鈕

### 後端 API
```
GET /api/customers/search?keyword=xxx
```
- 至少 2 個字元才查詢
- 純數字至少 3 碼
- 回傳最多 20 筆

## 三、客戶查詢看板規則修改

### 修改內容
```javascript
// 修改前
const query = document.getElementById('searchInput').value.trim();
if (!query) return;

// 修改後
const keyword = document.getElementById('searchInput').value.trim();
if (!keyword || keyword.length < 2) {
    alert('請至少輸入 2 個字');
    return;
}
```

### 觸發方式
- 按 Enter 或點擊「搜尋」按鈕
- 無 oninput 即時搜尋

## 四、關鍵技術點

1. **反向搜尋 UX**：讓員工不用記客戶編號，用人名即可
2. **隱藏欄位**：customer_id 存於 hidden input，避免手改
3. **條件顯示**：門市支援時動態顯示/隱藏相關欄位
4. **批次驗證**：多欄同時驗證，錯誤訊息分欄提示

---
_總結時間：2026-02-27_
