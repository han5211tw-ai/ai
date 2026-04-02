-- 績效考核系統資料表建立腳本
-- 執行時間: 2026-03-31

-- 1. 季度淨利與獎金池（老闆輸入）
CREATE TABLE IF NOT EXISTS quarterly_profit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter IN (1,2,3,4)),
    net_profit INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed')),
    created_by TEXT,
    created_at DATETIME DEFAULT (datetime('now','localtime')),
    updated_at DATETIME DEFAULT (datetime('now','localtime')),
    UNIQUE(year, quarter)
);

-- 2. 關鍵貢獻舉證表（員工填寫、主管審核）
CREATE TABLE IF NOT EXISTS kpi_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    item_number INTEGER NOT NULL CHECK (item_number IN (1,2,3)),
    description TEXT,
    category TEXT CHECK (category IN ('teamwork', 'individual')),
    evidence_type TEXT,
    evidence_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    reviewed_at DATETIME,
    score REAL DEFAULT 0 CHECK (score IN (0, 5)),
    created_at DATETIME DEFAULT (datetime('now','localtime')),
    UNIQUE(year, quarter, staff_name, item_number)
);

-- 3. KPI 得分總表（系統計算 + 人工輸入）
CREATE TABLE IF NOT EXISTS kpi_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    staff_role TEXT NOT NULL CHECK (staff_role IN ('store', 'engineer', 'manager', 'accounting')),
    
    -- 門市/工程同仁 KPI
    kpi1_achievement REAL DEFAULT 0,
    kpi2_margin REAL DEFAULT 0,
    kpi3_company_achievement REAL DEFAULT 0,
    kpi4_reviews REAL DEFAULT 0,
    kpi5_contribution REAL DEFAULT 0,
    
    -- 主管 KPI
    m_kpi1_dept_margin REAL DEFAULT 0,
    m_kpi2_staff_avg REAL DEFAULT 0,
    m_kpi3_company_margin REAL DEFAULT 0,
    m_kpi4_turnover REAL DEFAULT 0,
    m_kpi5_complaint REAL DEFAULT 0,
    m_kpi6_cross_dept REAL DEFAULT 0,
    
    -- 會計 KPI
    a_kpi1_accuracy REAL DEFAULT 0,
    a_kpi2_on_time REAL DEFAULT 0,
    a_kpi3_ar_control REAL DEFAULT 0,
    a_kpi4_support REAL DEFAULT 0,
    a_kpi5_cost_opt REAL DEFAULT 0,
    
    total_score REAL DEFAULT 0,
    rank INTEGER DEFAULT 0,
    multiplier REAL DEFAULT 1.0,
    bonus_amount INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT (datetime('now','localtime')),
    updated_at DATETIME DEFAULT (datetime('now','localtime')),
    UNIQUE(year, quarter, staff_name)
);
