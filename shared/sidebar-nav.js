/**
 * Sidebar Navigation Component
 * 全域側邊欄導航組件 - 支援路由切換與權限控制
 * @version 1.0.0
 */

class SidebarNavigation {
    constructor(options = {}) {
        this.container = options.container || document.querySelector('.sidebar-nav');
        this.currentUser = options.currentUser || null;
        this.activeRoute = options.activeRoute || 'dashboard';
        this.onRouteChange = options.onRouteChange || (() => {});
        
        this.navItems = [
            {
                section: '主要功能',
                items: [
                    { id: 'dashboard', icon: '🏠', label: '首頁', route: '/dashboard', minRole: 'staff' },
                    { id: 'documents', icon: '📝', label: '單據作業', route: '/documents', minRole: 'staff' },
                    { id: 'schedule', icon: '📅', label: '排班管理', route: '/schedule', minRole: 'staff' }
                ]
            },
            {
                section: '資料管理',
                items: [
                    { id: 'products', icon: '📦', label: '產品建檔', route: '/products', minRole: 'staff' },
                    { id: 'customers', icon: '👤', label: '客戶建檔', route: '/customers', minRole: 'staff' },
                    { id: 'suppliers', icon: '🏭', label: '廠商建檔', route: '/suppliers', minRole: 'staff' },
                    { id: 'purchase', icon: '📥', label: '進貨輸入', route: '/purchase', minRole: 'staff' }
                ]
            },
            {
                section: '系統管理',
                items: [
                    { id: 'admin', icon: '⚙️', label: '系統設定', route: '/admin', minRole: 'boss' },
                    { id: 'reports', icon: '📊', label: '報表中心', route: '/reports', minRole: 'accountant' }
                ],
                requireAdmin: true
            }
        ];
        
        this.init();
    }
    
    /**
     * 初始化導航組件
     */
    init() {
        if (!this.container) {
            console.error('SidebarNavigation: Container not found');
            return;
        }
        
        this.render();
        this.attachEvents();
        this.highlightActiveRoute();
    }
    
    /**
     * 檢查使用者權限
     */
    hasPermission(item) {
        if (!this.currentUser) return false;
        
        const userTitle = this.currentUser.title || '';
        const minRole = item.minRole || 'staff';
        
        // 老闆和會計擁有所有權限
        if (userTitle === '老闆' || userTitle.includes('會計')) {
            return true;
        }
        
        // 一般員工只能看到 staff 級別的項目
        if (minRole === 'staff') {
            return true;
        }
        
        return false;
    }
    
    /**
     * 渲染導航結構
     */
    render() {
        const html = this.navItems
            .filter(section => !section.requireAdmin || this.isAdmin())
            .map(section => {
                const visibleItems = section.items.filter(item => this.hasPermission(item));
                
                if (visibleItems.length === 0) return '';
                
                return `
                    <div class="nav-section" data-section="${section.section}">
                        <div class="nav-section-title">${section.section}</div>
                        ${visibleItems.map(item => `
                            <a href="#" 
                               class="nav-item ${item.id === this.activeRoute ? 'active' : ''}" 
                               data-route="${item.id}"
                               data-path="${item.route}"
                               title="${item.label}">
                                <span class="nav-item-icon">${item.icon}</span>
                                <span class="nav-item-text">${item.label}</span>
                                ${item.badge ? `<span class="nav-item-badge">${item.badge}</span>` : ''}
                            </a>
                        `).join('')}
                    </div>
                `;
            }).join('');
        
        this.container.innerHTML = html;
    }
    
    /**
     * 檢查是否為管理員
     */
    isAdmin() {
        if (!this.currentUser) return false;
        const title = this.currentUser.title || '';
        return title === '老闆' || title.includes('會計');
    }
    
    /**
     * 綁定事件
     */
    attachEvents() {
        this.container.addEventListener('click', (e) => {
            const navItem = e.target.closest('.nav-item');
            if (!navItem) return;
            
            e.preventDefault();
            
            const route = navItem.dataset.route;
            const path = navItem.dataset.path;
            
            // 檢查表單是否有未儲存資料
            if (window.AppState && window.AppState.formDirty) {
                if (!confirm('您有未儲存的資料，確定要離開嗎？')) {
                    return;
                }
            }
            
            // 更新活動狀態
            this.setActiveRoute(route);
            
            // 觸發路由變更回調
            this.onRouteChange({
                route: route,
                path: path,
                label: navItem.querySelector('.nav-item-text').textContent
            });
        });
        
        // 鍵盤導航支援
        this.container.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                const navItem = document.activeElement.closest('.nav-item');
                if (navItem) {
                    e.preventDefault();
                    navItem.click();
                }
            }
        });
    }
    
    /**
     * 設定活動路由
     */
    setActiveRoute(route) {
        this.activeRoute = route;
        
        // 移除所有活動狀態
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // 設定新的活動狀態
        const activeItem = this.container.querySelector(`[data-route="${route}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
        
        // 更新頁面標題
        this.updatePageTitle(route);
    }
    
    /**
     * 更新頁面標題
     */
    updatePageTitle(route) {
        const titles = {
            'dashboard': '首頁',
            'documents': '單據作業',
            'schedule': '排班管理',
            'products': '產品建檔',
            'customers': '客戶建檔',
            'suppliers': '廠商建檔',
            'purchase': '進貨輸入',
            'admin': '系統設定',
            'reports': '報表中心'
        };
        
        const title = titles[route] || route;
        const pageTitleEl = document.getElementById('pageTitle');
        if (pageTitleEl) {
            pageTitleEl.textContent = title;
        }
        
        // 更新文件標題
        document.title = `${title} - 電腦舖營運系統`;
    }
    
    /**
     * 高亮當前路由
     */
    highlightActiveRoute() {
        this.setActiveRoute(this.activeRoute);
    }
    
    /**
     * 更新徽章數字
     */
    updateBadge(routeId, count) {
        const navItem = this.container.querySelector(`[data-route="${routeId}"]`);
        if (!navItem) return;
        
        let badge = navItem.querySelector('.nav-item-badge');
        
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'nav-item-badge';
                navItem.appendChild(badge);
            }
            badge.textContent = count > 99 ? '99+' : count;
        } else if (badge) {
            badge.remove();
        }
    }
    
    /**
     * 折疊/展開側邊欄
     */
    toggle() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('collapsed');
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
// 全域導航管理器 (Global Navigation Manager)
// ============================================

const NavigationManager = {
    sidebar: null,
    history: [],
    currentIndex: -1,
    
    /**
     * 初始化導航系統
     */
    init(options = {}) {
        this.sidebar = new SidebarNavigation({
            container: document.querySelector('.sidebar-nav'),
            currentUser: options.currentUser,
            activeRoute: options.activeRoute || 'dashboard',
            onRouteChange: (routeInfo) => {
                this.handleRouteChange(routeInfo);
                if (options.onRouteChange) {
                    options.onRouteChange(routeInfo);
                }
            }
        });
        
        // 監聽瀏覽器返回/前進按鈕
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.route) {
                this.navigate(e.state.route, false);
            }
        });
        
        return this;
    },
    
    /**
     * 處理路由變更
     */
    handleRouteChange(routeInfo) {
        // 添加到歷史記錄
        this.history.push(routeInfo);
        this.currentIndex++;
        
        // 更新瀏覽器 URL（不重新整理）
        history.pushState({ route: routeInfo.route }, '', routeInfo.path);
        
        // 載入對應頁面內容
        this.loadPageContent(routeInfo.route);
    },
    
    /**
     * 導航到指定路由
     */
    navigate(route, addToHistory = true) {
        if (this.sidebar) {
            this.sidebar.setActiveRoute(route);
        }
        
        if (addToHistory) {
            const path = this.getPathByRoute(route);
            history.pushState({ route }, '', path);
        }
        
        this.loadPageContent(route);
    },
    
    /**
     * 根據路由取得路徑
     */
    getPathByRoute(route) {
        const paths = {
            'dashboard': '/dashboard',
            'documents': '/documents',
            'schedule': '/schedule',
            'products': '/products',
            'customers': '/customers',
            'suppliers': '/suppliers',
            'purchase': '/purchase',
            'admin': '/admin',
            'reports': '/reports'
        };
        return paths[route] || '/';
    },
    
    /**
     * 載入頁面內容
     */
    loadPageContent(route) {
        const workspace = document.getElementById('contentWorkspace');
        if (!workspace) return;
        
        // 觸發頁面載入事件
        const event = new CustomEvent('page:load', { 
            detail: { route } 
        });
        document.dispatchEvent(event);
        
        // 根據路由載入不同內容
        switch(route) {
            case 'documents':
                this.loadDocumentModule(workspace);
                break;
            case 'products':
                this.loadIframe(workspace, 'product_create.html');
                break;
            case 'customers':
                this.loadIframe(workspace, 'customer_create.html');
                break;
            case 'suppliers':
                this.loadIframe(workspace, 'supplier_create.html');
                break;
            case 'purchase':
                this.loadIframe(workspace, 'purchase_input.html');
                break;
            default:
                this.loadPlaceholder(workspace, route);
        }
    },
    
    /**
     * 載入單據作業模組
     */
    loadDocumentModule(container) {
        container.innerHTML = `
            <div class="split-view">
                <div class="split-left">
                    <div class="history-header">
                        <div class="search-box">
                            <input type="text" id="historySearch" placeholder="🔍 搜尋單號、客戶...">
                        </div>
                    </div>
                    <div class="history-list" id="historyList">
                        <div class="loading-state">載入中...</div>
                    </div>
                    <div class="history-pagination">
                        <button class="btn btn-secondary" onclick="NavigationManager.prevPage()">←</button>
                        <span id="pageInfo">第 1 頁</span>
                        <button class="btn btn-secondary" onclick="NavigationManager.nextPage()">→</button>
                    </div>
                </div>
                <div class="split-right" id="activeWorkspace">
                    <div class="empty-state">
                        <h2>📝 單據作業</h2>
                        <p>請從左側選擇單據查看詳情，或建立新單據</p>
                        <div class="action-buttons">
                            <button class="btn btn-primary" onclick="window.location.href='quote_input.html'">+ 新增報價單</button>
                            <button class="btn btn-primary" onclick="window.location.href='sales_input.html'">+ 新增銷貨單</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 載入歷史列表
        this.loadHistoryList();
    },
    
    /**
     * 載入 iframe
     */
    loadIframe(container, src) {
        container.innerHTML = `<iframe src="${src}" class="page-iframe"></iframe>`;
    },
    
    /**
     * 載入佔位符
     */
    loadPlaceholder(container, route) {
        container.innerHTML = `
            <div class="empty-state">
                <h2>🚧 開發中</h2>
                <p>「${route}」功能正在開發中，請稍後再試</p>
            </div>
        `;
    },
    
    /**
     * 載入歷史列表
     */
    async loadHistoryList(page = 1) {
        const listEl = document.getElementById('historyList');
        if (!listEl) return;
        
        try {
            // TODO: 替換為實際 API 呼叫
            // const response = await fetch(`/api/sales-doc/list?page=${page}&limit=50`);
            // const data = await response.json();
            
            // 模擬資料
            const mockData = [
                { doc_no: 'QU-FY-20260307-001', target_name: '大樹不動產', total_amount: 25000, status: 'DRAFT', created_at: '2026-03-07 10:30', doc_type: 'QUOTE' },
                { doc_no: 'OD-FY-20260307-002', target_name: '李秉茗', total_amount: 15000, status: 'CONFIRMED', created_at: '2026-03-07 11:15', doc_type: 'ORDER' },
                { doc_no: 'SO-FY-20260307-003', target_name: '黃靖惟', total_amount: 32000, status: 'CLOSED', created_at: '2026-03-07 09:45', doc_type: 'SALES' }
            ];
            
            this.renderHistoryList(mockData);
        } catch (error) {
            console.error('載入歷史列表失敗:', error);
            listEl.innerHTML = '<div class="error-state">載入失敗</div>';
        }
    },
    
    /**
     * 渲染歷史列表
     */
    renderHistoryList(data) {
        const listEl = document.getElementById('historyList');
        if (!listEl) return;
        
        const statusMap = {
            'DRAFT': ['草稿', 'badge-draft'],
            'CONFIRMED': ['已確認', 'badge-confirmed'],
            'CLOSED': ['已結案', 'badge-closed']
        };
        
        listEl.innerHTML = data.map(item => {
            const [statusText, statusClass] = statusMap[item.status] || ['未知', ''];
            return `
                <div class="history-item" onclick="NavigationManager.openModal('${item.doc_no}', '${item.doc_type}')">
                    <div class="history-item-header">
                        <span class="history-item-no">${item.doc_no}</span>
                        <span class="history-item-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="history-item-customer">${item.target_name}</div>
                    <div class="history-item-footer">
                        <span class="history-item-amount">$${item.total_amount.toLocaleString()}</span>
                        <span class="history-item-date">${item.created_at}</span>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    /**
     * 開啟 Modal
     */
    openModal(docNo, docType) {
        const event = new CustomEvent('modal:open', {
            detail: { docNo, docType }
        });
        document.dispatchEvent(event);
    },
    
    /**
     * 上一頁
     */
    prevPage() {
        // TODO: 實作分頁邏輯
        console.log('Previous page');
    },
    
    /**
     * 下一頁
     */
    nextPage() {
        // TODO: 實作分頁邏輯
        console.log('Next page');
    }
};

// 匯出供全域使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SidebarNavigation, NavigationManager };
} else {
    window.SidebarNavigation = SidebarNavigation;
    window.NavigationManager = NavigationManager;
}