# 監控系統整併重構計劃

## 重構前狀態
- health_check.py（舊版監控邏輯）
- observability.py（新版 v2.0 監控）
- UI 存在重複監控區塊

## 重構目標
建立 Single Source of Truth：所有健康檢查統一由 observability.py 提供

## 執行步驟

### 1. API 整併
- 保留：/api/v1/admin/observability/health
- 移除：health_check.py 的舊路由
- 統一所有前端呼叫到這支 API

### 2. UI 整併
- 上方卡片移除「DB Monitor」格
- 下方保留資料庫監控詳細資訊
- 統一資料來源

### 3. observability.py 成為唯一來源
- 整合 system/database/import/freshness/api/run 狀態
- 統一計算 overall_status

### 4. 錯誤隔離
- 所有 fetch 使用 try/catch
- 子區塊錯誤不影響其他模組

## 預計修改檔案
- dashboard-site/observability.py（擴充功能）
- dashboard-site/app.py（移除舊路由）
- dashboard-site/admin/health.html（整併 UI）
