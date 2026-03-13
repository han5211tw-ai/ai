CREATE TABLE finance_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL CHECK(record_type IN ('AR', 'AP')),
    target_id TEXT NOT NULL,
    target_name TEXT,
    reference_doc TEXT,
    total_amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'UNPAID' CHECK(status IN ('UNPAID', 'PAID')),
    payment_method TEXT CHECK(payment_method IN ('現金', '匯款', '刷卡', '支票')),
    due_date DATE,
    cleared_at DATETIME,
    created_at DATETIME DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_finance_ledger_type ON finance_ledger(record_type);
CREATE INDEX idx_finance_ledger_target ON finance_ledger(target_id);
CREATE INDEX idx_finance_ledger_status ON finance_ledger(status);
CREATE INDEX idx_finance_ledger_payment ON finance_ledger(payment_method);
CREATE INDEX idx_finance_ledger_due_date ON finance_ledger(due_date);
CREATE INDEX idx_finance_ledger_reference ON finance_ledger(reference_doc);
CREATE INDEX idx_finance_ledger_cleared ON finance_ledger(cleared_at);
