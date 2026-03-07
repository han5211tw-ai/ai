/**
 * App Shell Integration
 * 整合現有頁面到新的 App Shell 架構
 * @version 1.0.0
 */

class AppShellIntegration {
    constructor() {
        this.currentUser = null;
        this.sidebarNav = null;
        this.splitView = null;
        this.modalSystem = null;
        
        this.init();
    }
    
    /**
     * 初始化整合
     */
    async init() {
        // 等待 DOM 載入
        if (document.readyState === 'loading') {
            await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve));
        }
        
        // 檢查認證
        await this.checkAuth();
        
        // 初始化各組件
        this.initSidebarNav();
        this.initModalSystem();
        
        // 載入初始頁面
        this.loadInitialPage();
        
        console.log('✅ App Shell Integration initialized');
    }
    
    /**
     * 檢查認證
     */
    async checkAuth() {
        if (window.checkAuth) {
            const result = await window.checkAuth({ minRole: 'staff' });
            if (!result.success) {
                window.location.href = 'index.html';
                return;
            }
            this.currentUser = result;
        }
    }
    
    /**
     * 初始化側邊欄導航
     */
    initSidebarNav() {
        if (!window.SidebarNavigation) {
            console.error('SidebarNavigation not loaded');
            return;
        }
        
        this.sidebarNav = new SidebarNavigation({
            container: document.querySelector('.sidebar-nav'),
            currentUser: this.currentUser,
            activeRoute: 'dashboard',
            onRouteChange: (routeInfo) => {
                this.handleRouteChange(routeInfo);
            }
        });
    }
    
    /**
     * 初始化 Modal 系統
     */
    initModalSystem() {
        if (!window.ModalSystem) {
            console.error('ModalSystem not loaded');
            return;
        }
        
        this.modalSystem = ModalSystem.getInstance({
            preserveFormState: true
        });
        this.modalSystem.setCurrentUser(this.currentUser);
    }
    
    /**
     * 處理路由變更
     */
    handleRouteChange(routeInfo) {
        const workspace = document.getElementById('contentWorkspace');
        if (!workspace) return;
        
        // 根據路由載入不同內容
        switch(routeInfo.route) {
            case 'documents':
                this.loadDocumentModule(workspace);
                break;
            case 'quote':
                this.loadPageInIframe(workspace, 'quote_input.html');
                break;
            case 'sales':
                this.loadPageInIframe(workspace, 'sales_input.html');
                break;
            case 'needs':
                this.loadPageInIframe(workspace, 'needs_input.html');
                break;
            case 'schedule':
                this.loadPageInIframe(workspace, 'schedule.html');
                break;
            case 'inventory':
                this.loadPageInIframe(workspace, 'inventory_query.html');
                break;
            case 'customer-search':
                this.loadPageInIframe(workspace, 'customer_search.html');
                break;
            case 'products':
                this.loadPageInIframe(workspace, 'product_create.html');
                break;
            case 'customers':
                this.loadPageInIframe(workspace, 'customer_create.html');
                break;
            case 'suppliers':
                this.loadPageInIframe(workspace, 'supplier_create.html');
                break;
            case 'purchase':
                this.loadPageInIframe(workspace, 'purchase_input.html');
                break;
            case 'pending-needs':
                this.loadPageInIframe(workspace, 'boss.html');
                break;
            case 'pending-transfer':
                this.loadPageInIframe(workspace, 'Accountants.html');
                break;
            case 'report-dept':
            case 'report-sales':
            case 'report-store':
            case 'report-personal':
            case 'report-service':
                this.loadPageInIframe(workspace, 'Store_Manager.html');
                break;
            case 'admin':
                this.loadPageInIframe(workspace, 'admin.html');
                break;
            default:
                this.loadDashboard(workspace);
        }
    }
    
    /**
     * 載入單據作業模組（Split View）
     */
    loadDocumentModule(container) {
        if (!window.SplitViewModule) {
            console.error('SplitViewModule not loaded');
            return;
        }
        
        // 建立 Split View
        this.splitView = new SplitViewModule({
            container: container,
            leftWidth: '30%',
            onItemSelect: ({ item }) => {
                // 載入項目到右側工作區
                if (item.action === 'create') {
                    this.showCreateOptions();
                } else {
                    this.loadDocumentDetail(item);
                }
            },
            onItemClick: ({ item, action }) => {
                // 開啟 Modal 檢視
                this.openDocumentModal(item);
            },
            onSearch: ({ keyword, page }) => {
                this.searchDocuments(keyword, page);
            },
            onPageChange: ({ page }) => {
                this.loadDocumentList(page);
            }
        });
        
        // 載入初始列表
        this.loadDocumentList(1);
    }
    
    /**
     * 載入文件列表
     */
    async loadDocumentList(page = 1) {
        this.splitView.showLoading();
        
        try {
            // TODO: 替換為實際 API
            // const response = await fetch(`/api/sales-doc/list?page=${page}&limit=50`);
            // const data = await response.json();
            
            // 模擬資料
            const mockData = {
                documents: [
                    { id: '1', doc_no: 'QU-FY-20260307-001', target_name: '大樹不動產', total_amount: 25000, status: 'DRAFT', created_at: '2026-03-07 10:30', doc_type: 'QUOTE', salesperson_id: 'FY-001' },
                    { id: '2', doc_no: 'OD-FY-20260307-002', target_name: '李秉茗', total_amount: 15000, status: 'CONFIRMED', created_at: '2026-03-07 11:15', doc_type: 'ORDER', salesperson_id: 'FY-002' },
                    { id: '3', doc_no: 'SO-FY-20260307-003', target_name: '黃靖惟', total_amount: 32000, status: 'CLOSED', created_at: '2026-03-07 09:45', doc_type: 'SALES', salesperson_id: 'FY-001' }
                ],
                total: 3,
                page: 1,
                total_pages: 1
            };
            
            this.splitView.renderList(mockData.documents, {
                total: mockData.total,
                page: mockData.page,
                totalPages: mockData.total_pages
            });
        } catch (error) {
            console.error('載入文件列表失敗:', error);
            this.splitView.showError('載入失敗，請稍後再試');
        }
    }
    
    /**
     * 搜尋文件
     */
    async searchDocuments(keyword, page) {
        console.log('搜尋:', keyword, '頁面:', page);
        // TODO: 實作搜尋 API
        this.loadDocumentList(page);
    }
    
    /**
     * 載入文件詳情到工作區
     */
    loadDocumentDetail(item) {
        const canEdit = this.canEditDocument(item.doc_type, item.salesperson_id);
        
        const content = `
            <div class="form-section">
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">單號</label>
                        <input type="text" class="form-input" value="${item.doc_no}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">客戶</label>
                        <input type="text" class="form-input" value="${item.target_name}" ${canEdit ? '' : 'readonly'}>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">金額</label>
                        <input type="text" class="form-input" value="$${item.total_amount.toLocaleString()}" ${canEdit ? '' : 'readonly'}>
                    </div>
                    <div class="form-group">
                        <label class="form-label">狀態</label>
                        <input type="text" class="form-input" value="${item.status}" readonly>
                    </div>
                </div>
            </div>
        `;
        
        this.splitView.setWorkspaceContent({
            title: `${item.doc_no} - ${item.target_name}`,
            content: content,
            actions: canEdit ? [
                { label: '儲存變更', class: 'btn-primary', onClick: 'AppShell.saveDocument()' },
                { label: '轉訂單', class: 'btn-secondary', onClick: 'AppShell.convertDocument()' }
            ] : [
                { label: '列印', class: 'btn-secondary', onClick: 'window.print()' }
            ]
        });
    }
    
    /**
     * 開啟文件 Modal
     */
    openDocumentModal(item) {
        const canEdit = this.canEditDocument(item.doc_type, item.salesperson_id);
        
        this.modalSystem.open({
            title: `單據詳情 - ${item.doc_no}`,
            content: this.generateModalContent(item, canEdit),
            docType: item.doc_type,
            docOwnerId: item.salesperson_id,
            size: 'large',
            onSave: canEdit ? 'AppShell.saveFromModal()' : null,
            customActions: [
                { label: '列印', class: 'btn-secondary', icon: '🖨️', onClick: 'window.print()' }
            ]
        });
    }
    
    /**
     * 生成 Modal 內容
     */
    generateModalContent(item, canEdit) {
        return `
            <div class="form-section">
                <h3 class="form-section-title">📋 基本資訊</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">單號</label>
                        <input type="text" class="form-input" value="${item.doc_no}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">類型</label>
                        <input type="text" class="form-input" value="${item.doc_type}" readonly>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">客戶名稱</label>
                        <input type="text" class="form-input" value="${item.target_name}" ${canEdit ? '' : 'readonly'}>
                    </div>
                    <div class="form-group">
                        <label class="form-label">總金額</label>
                        <input type="text" class="form-input" value="$${item.total_amount.toLocaleString()}" ${canEdit ? '' : 'readonly'}>
                    </div>
                </div>
            </div>
            <div class="form-section">
                <h3 class="form-section-title">📦 產品明細</h3>
                <p style="color: var(--text-muted);">產品明細列表...</p>
            </div>
        `;
    }
    
    /**
     * 檢查是否可以編輯文件
     */
    canEditDocument(docType, ownerId) {
        if (!this.currentUser) return false;
        
        const userTitle = this.currentUser.title || '';
        const userId = this.currentUser.staff_code || this.currentUser.id;
        
        // 老闆和會計擁有所有權限
        if (userTitle === '老闆' || userTitle.includes('會計')) {
            return true;
        }
        
        // 銷貨單不可編輯
        if (docType === 'SALES') {
            return false;
        }
        
        // 報價單和訂單：建立者可編輯
        if (docType === 'QUOTE' || docType === 'ORDER') {
            return ownerId === userId;
        }
        
        return false;
    }
    
    /**
     * 顯示建立選項
     */
    showCreateOptions() {
        this.splitView.setWorkspaceContent({
            title: '建立新單據',
            content: `
                <div class="empty-state">
                    <h3>選擇單據類型</h3>
                    <div style="display: flex; gap: 16px; margin-top: 24px;">
                        <button class="btn btn-primary" onclick="window.location.href='quote_input.html'" style="padding: 24px 48px;">
                            <div style="font-size: 32px; margin-bottom: 8px;">📝</div>
                            <div>報價單</div>
                        </button>
                        <button class="btn btn-primary" onclick="window.location.href='sales_input.html'" style="padding: 24px 48px;">
                            <div style="font-size: 32px; margin-bottom: 8px;">💰</div>
                            <div>銷貨單</div>
                        </button>
                    </div>
                </div>
            `,
            actions: []
        });
    }
    
    /**
     * 在 iframe 中載入頁面
     */
    loadPageInIframe(container, src) {
        container.innerHTML = `
            <iframe src="${src}" 
                    style="width: 100%; height: 100%; border: none;" 
                    sandbox="allow-same-origin allow-scripts allow-forms">
            </iframe>
        `;
    }
    
    /**
     * 載入儀表板
     */
    loadDashboard(container) {
        container.innerHTML = `
            <div style="padding: 24px;">
                <h2 style="margin-bottom: 24px;">🏠 首頁</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px;">
                    <div class="card" style="padding: 24px;">
                        <h3>📊 今日業績</h3>
                        <p style="font-size: 32px; color: var(--accent-primary); margin-top: 16px;">$125,000</p>
                    </div>
                    <div class="card" style="padding: 24px;">
                        <h3>📝 待處理單據</h3>
                        <p style="font-size: 32px; color: var(--warning); margin-top: 16px;">12</p>
                    </div>
                    <div class="card" style="padding: 24px;">
                        <h3>👥 活耀客戶</h3>
                        <p style="font-size: 32px; color: var(--success); margin-top: 16px;">86</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 載入初始頁面
     */
    loadInitialPage() {
        const hash = window.location.hash.slice(1);
        const route = hash || 'dashboard';
        
        if (this.sidebarNav) {
            this.sidebarNav.setActiveRoute(route);
        }
        
        this.handleRouteChange({ route, label: '首頁' });
    }
    
    /**
     * 儲存文件（從工作區）
     */
    saveDocument() {
        alert('儲存功能開發中');
    }
    
    /**
     * 轉換文件
     */
    convertDocument() {
        alert('轉換功能開發中');
    }
    
    /**
     * 從 Modal 儲存
     */
    saveFromModal() {
        alert('從 Modal 儲存開發中');
        this.modalSystem.closeTopModal();
    }
}

// 全域實例
window.AppShell = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.AppShell = new AppShellIntegration();
});

// 匯出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AppShellIntegration };
}