/**
 * Split View Module
 * 左右分欄佈局組件 - 歷史列表 + 主工作區
 * @version 1.0.0
 */

class SplitViewModule {
    constructor(options = {}) {
        this.container = options.container || document.getElementById('contentWorkspace');
        this.leftWidth = options.leftWidth || '30%';
        this.rightWidth = options.rightWidth || '70%';
        this.minLeftWidth = options.minLeftWidth || 300;
        this.maxLeftWidth = options.maxLeftWidth || 400;
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.searchKeyword = '';
        this.selectedItem = null;
        
        this.onItemSelect = options.onItemSelect || (() => {});
        this.onItemClick = options.onItemClick || (() => {});
        this.onSearch = options.onSearch || (() => {});
        this.onPageChange = options.onPageChange || (() => {});
        
        this.init();
    }
    
    /**
     * 初始化 Split View
     */
    init() {
        if (!this.container) {
            console.error('SplitViewModule: Container not found');
            return;
        }
        
        this.render();
        this.attachEvents();
        this.initResizable();
    }
    
    /**
     * 渲染佈局結構
     */
    render() {
        this.container.innerHTML = `
            <div class="split-view" id="splitView">
                <!-- Left Panel: History List -->
                <div class="split-left" id="splitLeft" style="width: ${this.leftWidth}">
                    <div class="split-panel-header">
                        <div class="search-box">
                            <input type="text" 
                                   id="historySearch" 
                                   class="search-input"
                                   placeholder="🔍 搜尋單號、客戶..."
                                   autocomplete="off">
                            <button class="search-clear" id="searchClear" style="display: none;">✕</button>
                        </div>
                    </div>
                    <div class="split-panel-toolbar">
                        <span class="toolbar-info" id="listInfo">共 0 筆</span>
                        <div class="toolbar-actions">
                            <button class="btn-icon" id="refreshBtn" title="重新整理">🔄</button>
                            <button class="btn-icon" id="filterBtn" title="篩選">🔽</button>
                        </div>
                    </div>
                    <div class="history-list" id="historyList">
                        <div class="loading-state">
                            <div class="spinner"></div>
                            <p>載入中...</p>
                        </div>
                    </div>
                    <div class="split-panel-footer">
                        <button class="btn btn-secondary btn-sm" id="prevPageBtn" disabled>←</button>
                        <span class="pagination-info" id="pageInfo">第 1 頁 / 共 1 頁</span>
                        <button class="btn btn-secondary btn-sm" id="nextPageBtn" disabled>→</button>
                    </div>
                    <!-- Resizer Handle -->
                    <div class="resizer" id="resizer"></div>
                </div>
                
                <!-- Right Panel: Active Workspace -->
                <div class="split-right" id="splitRight">
                    <div class="workspace-header">
                        <h2 class="workspace-title" id="workspaceTitle">歡迎使用</h2>
                        <div class="workspace-actions" id="workspaceActions">
                            <button class="btn btn-primary" id="createNewBtn">+ 新增</button>
                        </div>
                    </div>
                    <div class="workspace-content" id="workspaceContent">
                        <div class="empty-state">
                            <div class="empty-icon">📋</div>
                            <h3>請選擇左側單據</h3>
                            <p>點擊左側列表中的單據查看詳情，或點擊「新增」建立新單據</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.cacheElements();
    }
    
    /**
     * 快取 DOM 元素參考
     */
    cacheElements() {
        this.elements = {
            splitView: document.getElementById('splitView'),
            splitLeft: document.getElementById('splitLeft'),
            splitRight: document.getElementById('splitRight'),
            resizer: document.getElementById('resizer'),
            searchInput: document.getElementById('historySearch'),
            searchClear: document.getElementById('searchClear'),
            historyList: document.getElementById('historyList'),
            listInfo: document.getElementById('listInfo'),
            pageInfo: document.getElementById('pageInfo'),
            prevPageBtn: document.getElementById('prevPageBtn'),
            nextPageBtn: document.getElementById('nextPageBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            filterBtn: document.getElementById('filterBtn'),
            workspaceTitle: document.getElementById('workspaceTitle'),
            workspaceActions: document.getElementById('workspaceActions'),
            workspaceContent: document.getElementById('workspaceContent'),
            createNewBtn: document.getElementById('createNewBtn')
        };
    }
    
    /**
     * 綁定事件
     */
    attachEvents() {
        // 搜尋功能
        this.elements.searchInput.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });
        
        this.elements.searchClear.addEventListener('click', () => {
            this.elements.searchInput.value = '';
            this.handleSearch('');
            this.elements.searchInput.focus();
        });
        
        // 分頁控制
        this.elements.prevPageBtn.addEventListener('click', () => {
            this.goToPage(this.currentPage - 1);
        });
        
        this.elements.nextPageBtn.addEventListener('click', () => {
            this.goToPage(this.currentPage + 1);
        });
        
        // 工具列按鈕
        this.elements.refreshBtn.addEventListener('click', () => {
            this.refreshList();
        });
        
        this.elements.filterBtn.addEventListener('click', () => {
            this.toggleFilter();
        });
        
        // 新增按鈕
        this.elements.createNewBtn.addEventListener('click', () => {
            this.onItemSelect({ action: 'create' });
        });
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + F 聚焦搜尋
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                this.elements.searchInput.focus();
            }
            
            // ESC 清除搜尋
            if (e.key === 'Escape' && this.elements.searchInput.value) {
                this.elements.searchInput.value = '';
                this.handleSearch('');
            }
        });
    }
    
    /**
     * 初始化可調整大小功能
     */
    initResizable() {
        const resizer = this.elements.resizer;
        const leftPanel = this.elements.splitLeft;
        const container = this.elements.splitView;
        
        let isResizing = false;
        let startX;
        let startWidth;
        
        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = leftPanel.offsetWidth;
            
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            resizer.classList.add('resizing');
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const diff = e.clientX - startX;
            let newWidth = startWidth + diff;
            
            // 限制最小和最大寬度
            newWidth = Math.max(this.minLeftWidth, Math.min(this.maxLeftWidth, newWidth));
            
            leftPanel.style.width = `${newWidth}px`;
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                resizer.classList.remove('resizing');
                
                // 儲存用戶偏好
                this.saveUserPreference('splitLeftWidth', leftPanel.style.width);
            }
        });
    }
    
    /**
     * 處理搜尋
     */
    handleSearch(keyword) {
        this.searchKeyword = keyword.trim();
        
        // 顯示/隱藏清除按鈕
        this.elements.searchClear.style.display = this.searchKeyword ? 'block' : 'none';
        
        // 重置到第一頁
        this.currentPage = 1;
        
        // 觸發搜尋回調
        this.onSearch({
            keyword: this.searchKeyword,
            page: this.currentPage
        });
    }
    
    /**
     * 跳轉到指定頁面
     */
    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        
        this.currentPage = page;
        this.onPageChange({ page });
        this.updatePagination();
    }
    
    /**
     * 更新分頁控制
     */
    updatePagination() {
        this.elements.pageInfo.textContent = `第 ${this.currentPage} 頁 / 共 ${this.totalPages} 頁`;
        this.elements.prevPageBtn.disabled = this.currentPage <= 1;
        this.elements.nextPageBtn.disabled = this.currentPage >= this.totalPages;
    }
    
    /**
     * 渲染歷史列表
     */
    renderList(data, options = {}) {
        const { total = 0, page = 1, totalPages = 1 } = options;
        
        this.totalPages = totalPages;
        this.currentPage = page;
        
        // 更新列表資訊
        this.elements.listInfo.textContent = `共 ${total.toLocaleString()} 筆`;
        this.updatePagination();
        
        // 渲染列表項目
        if (data.length === 0) {
            this.elements.historyList.innerHTML = `
                <div class="empty-state small">
                    <p>暫無資料</p>
                </div>
            `;
            return;
        }
        
        this.elements.historyList.innerHTML = data.map((item, index) => {
            const isSelected = this.selectedItem && this.selectedItem.id === item.id;
            return this.renderListItem(item, isSelected, index);
        }).join('');
        
        // 綁定項目點擊事件
        this.elements.historyList.querySelectorAll('.history-item').forEach((el, index) => {
            el.addEventListener('click', () => {
                this.selectItem(data[index]);
            });
            
            // 雙擊開啟 Modal
            el.addEventListener('dblclick', () => {
                this.onItemClick({ item: data[index], action: 'view' });
            });
        });
    }
    
    /**
     * 渲染單個列表項目
     */
    renderListItem(item, isSelected, index) {
        const statusConfig = this.getStatusConfig(item.status);
        
        return `
            <div class="history-item ${isSelected ? 'active' : ''}" 
                 data-id="${item.id}" 
                 tabindex="0"
                 role="button"
                 aria-selected="${isSelected}">
                <div class="history-item-header">
                    <span class="history-item-no">${item.doc_no}</span>
                    <span class="history-item-status ${statusConfig.class}">${statusConfig.label}</span>
                </div>
                <div class="history-item-body">
                    <div class="history-item-customer">
                        <span class="customer-icon">👤</span>
                        ${item.target_name}
                    </div>
                    ${item.description ? `<div class="history-item-desc">${item.description}</div>` : ''}
                </div>
                <div class="history-item-footer">
                    <span class="history-item-amount">$${item.total_amount.toLocaleString()}</span>
                    <span class="history-item-date">${this.formatDate(item.created_at)}</span>
                </div>
            </div>
        `;
    }
    
    /**
     * 取得狀態配置
     */
    getStatusConfig(status) {
        const configs = {
            'DRAFT': { label: '草稿', class: 'badge-draft' },
            'CONFIRMED': { label: '已確認', class: 'badge-confirmed' },
            'CLOSED': { label: '已結案', class: 'badge-closed' },
            'PENDING': { label: '待處理', class: 'badge-pending' },
            'CANCELLED': { label: '已取消', class: 'badge-cancelled' }
        };
        return configs[status] || { label: status, class: '' };
    }
    
    /**
     * 選擇項目
     */
    selectItem(item) {
        // 移除之前的選中狀態
        this.elements.historyList.querySelectorAll('.history-item').forEach(el => {
            el.classList.remove('active');
            el.setAttribute('aria-selected', 'false');
        });
        
        // 設定新的選中狀態
        const selectedEl = this.elements.historyList.querySelector(`[data-id="${item.id}"]`);
        if (selectedEl) {
            selectedEl.classList.add('active');
            selectedEl.setAttribute('aria-selected', 'true');
        }
        
        this.selectedItem = item;
        this.onItemSelect({ item });
    }
    
    /**
     * 設定工作區內容
     */
    setWorkspaceContent(options) {
        const { title, content, actions = [] } = options;
        
        this.elements.workspaceTitle.textContent = title || '工作區';
        
        // 設定操作按鈕
        if (actions.length > 0) {
            this.elements.workspaceActions.innerHTML = actions.map(action => `
                <button class="btn ${action.class || 'btn-secondary'}" 
                        onclick="${action.onClick}"
                        ${action.disabled ? 'disabled' : ''}>
                    ${action.icon ? `<span>${action.icon}</span>` : ''}
                    ${action.label}
                </button>
            `).join('');
        }
        
        // 設定內容
        if (typeof content === 'string') {
            this.elements.workspaceContent.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            this.elements.workspaceContent.innerHTML = '';
            this.elements.workspaceContent.appendChild(content);
        }
    }
    
    /**
     * 顯示載入狀態
     */
    showLoading() {
        this.elements.historyList.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>載入中...</p>
            </div>
        `;
    }
    
    /**
     * 顯示錯誤狀態
     */
    showError(message) {
        this.elements.historyList.innerHTML = `
            <div class="error-state">
                <p>❌ ${message}</p>
                <button class="btn btn-secondary" onclick="location.reload()">重新整理</button>
            </div>
        `;
    }
    
    /**
     * 重新整理列表
     */
    refreshList() {
        this.showLoading();
        this.onSearch({
            keyword: this.searchKeyword,
            page: this.currentPage,
            refresh: true
        });
    }
    
    /**
     * 切換篩選
     */
    toggleFilter() {
        // TODO: 實作篩選彈窗
        console.log('Toggle filter');
    }
    
    /**
     * 格式化日期
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-TW', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * 儲存用戶偏好設定
     */
    saveUserPreference(key, value) {
        try {
            const prefs = JSON.parse(localStorage.getItem('splitViewPrefs') || '{}');
            prefs[key] = value;
            localStorage.setItem('splitViewPrefs', JSON.stringify(prefs));
        } catch (e) {
            console.warn('Failed to save preference:', e);
        }
    }
    
    /**
     * 讀取用戶偏好設定
     */
    loadUserPreference(key, defaultValue = null) {
        try {
            const prefs = JSON.parse(localStorage.getItem('splitViewPrefs') || '{}');
            return prefs[key] || defaultValue;
        } catch (e) {
            return defaultValue;
        }
    }
    
    /**
     * 銷毀組件
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// ============================================
// CSS Styles for Split View
// ============================================

const splitViewStyles = `
    /* Split View Container */
    .split-view {
        display: flex;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
    
    /* Left Panel */
    .split-left {
        display: flex;
        flex-direction: column;
        background: var(--color-bg-elevated);
        border-right: 1px solid var(--color-border-default);
        position: relative;
        min-width: 250px;
        max-width: 500px;
    }
    
    /* Resizer Handle */
    .resizer {
        position: absolute;
        right: -4px;
        top: 0;
        bottom: 0;
        width: 8px;
        cursor: col-resize;
        z-index: 10;
        transition: background 0.2s;
    }
    
    .resizer:hover,
    .resizer.resizing {
        background: var(--color-accent-cyan);
    }
    
    /* Panel Header */
    .split-panel-header {
        padding: 16px;
        border-bottom: 1px solid var(--color-border-default);
    }
    
    .search-box {
        position: relative;
    }
    
    .search-input {
        width: 100%;
        padding: 10px 36px 10px 12px;
        background: var(--color-bg-primary);
        border: 1px solid var(--color-border-default);
        border-radius: 8px;
        color: var(--color-text-primary);
        font-size: 14px;
        transition: all 0.2s;
    }
    
    .search-input:focus {
        outline: none;
        border-color: var(--color-accent-cyan);
        box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
    }
    
    .search-clear {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--color-bg-hover);
        border: none;
        color: var(--color-text-secondary);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
    }
    
    /* Toolbar */
    .split-panel-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        border-bottom: 1px solid var(--color-border-default);
    }
    
    .toolbar-info {
        font-size: 12px;
        color: var(--color-text-muted);
    }
    
    .toolbar-actions {
        display: flex;
        gap: 4px;
    }
    
    /* History List */
    .history-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px;
    }
    
    .history-item {
        padding: 16px;
        margin-bottom: 8px;
        background: var(--color-bg-primary);
        border: 1px solid var(--color-border-default);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.15s;
        outline: none;
    }
    
    .history-item:hover {
        background: var(--color-bg-hover);
        border-color: var(--color-border-accent);
        transform: translateX(4px);
    }
    
    .history-item.active {
        background: var(--color-bg-active);
        border-color: var(--color-accent-cyan);
        box-shadow: 0 0 0 1px var(--color-accent-cyan);
    }
    
    .history-item:focus {
        box-shadow: 0 0 0 2px var(--color-accent-cyan);
    }
    
    .history-item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .history-item-no {
        font-weight: 600;
        color: var(--color-accent-cyan);
        font-size: 13px;
    }
    
    .history-item-status {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
    }
    
    .history-item-body {
        margin-bottom: 8px;
    }
    
    .history-item-customer {
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--color-text-secondary);
        font-size: 14px;
        margin-bottom: 4px;
    }
    
    .customer-icon {
        opacity: 0.5;
    }
    
    .history-item-desc {
        font-size: 12px;
        color: var(--color-text-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .history-item-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .history-item-amount {
        font-weight: 600;
        color: var(--color-text-primary);
    }
    
    .history-item-date {
        font-size: 12px;
        color: var(--color-text-muted);
    }
    
    /* Panel Footer */
    .split-panel-footer {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-top: 1px solid var(--color-border-default);
    }
    
    .pagination-info {
        font-size: 13px;
        color: var(--color-text-secondary);
        min-width: 120px;
        text-align: center;
    }
    
    /* Right Panel */
    .split-right {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .workspace-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        border-bottom: 1px solid var(--color-border-default);
    }
    
    .workspace-title {
        font-size: 20px;
        font-weight: 600;
        color: var(--color-text-primary);
    }
    
    .workspace-actions {
        display: flex;
        gap: 8px;
    }
    
    .workspace-content {
        flex: 1;
        overflow: auto;
        padding: 24px;
    }
    
    /* Empty State */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-align: center;
        color: var(--color-text-secondary);
    }
    
    .empty-state .empty-icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
    }
    
    .empty-state h3 {
        font-size: 20px;
        margin-bottom: 8px;
        color: var(--color-text-primary);
    }
    
    .empty-state p {
        max-width: 400px;
        margin-bottom: 24px;
    }
    
    .empty-state.small {
        padding: 40px 20px;
    }
    
    .empty-state.small .empty-icon {
        font-size: 32px;
    }
    
    /* Loading & Error States */
    .loading-state,
    .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        text-align: center;
    }
    
    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid var(--color-border-default);
        border-top-color: var(--color-accent-cyan);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 16px;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .split-view {
            flex-direction: column;
        }
        
        .split-left {
            width: 100% !important;
            max-width: none;
            height: 40%;
            border-right: none;
            border-bottom: 1px solid var(--color-border-default);
        }
        
        .split-right {
            height: 60%;
        }
        
        .resizer {
            display: none;
        }
    }
`;

// 自動注入樣式
(function injectStyles() {
    if (document.getElementById('split-view-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'split-view-styles';
    styleEl.textContent = splitViewStyles;
    document.head.appendChild(styleEl);
})();

// 匯出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SplitViewModule };
} else {
    window.SplitViewModule = SplitViewModule;
}