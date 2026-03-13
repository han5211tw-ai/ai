/**
 * Modal System
 * 彈窗系統 - 支援權限控制與表單狀態保護
 * @version 1.0.0
 */

class ModalSystem {
    constructor(options = {}) {
        this.container = options.container || document.body;
        this.zIndex = options.zIndex || 5000;
        this.closeOnBackdrop = options.closeOnBackdrop !== false;
        this.closeOnEscape = options.closeOnEscape !== false;
        this.preserveFormState = options.preserveFormState !== false;
        
        this.currentUser = null;
        this.openModals = [];
        this.formBackup = null;
        
        this.init();
    }
    
    /**
     * 初始化 Modal 系統
     */
    init() {
        this.createModalContainer();
        this.attachGlobalEvents();
    }
    
    /**
     * 建立 Modal 容器
     */
    createModalContainer() {
        // 檢查是否已存在
        if (document.getElementById('modal-system-container')) {
            this.modalContainer = document.getElementById('modal-system-container');
            return;
        }
        
        this.modalContainer = document.createElement('div');
        this.modalContainer.id = 'modal-system-container';
        this.modalContainer.innerHTML = `
            <!-- Backdrop -->
            <div class="modal-backdrop" id="modalBackdrop" style="display: none;"></div>
            
            <!-- Modal Stack -->
            <div class="modal-stack" id="modalStack"></div>
        `;
        
        this.container.appendChild(this.modalContainer);
        
        // 快取元素
        this.backdrop = document.getElementById('modalBackdrop');
        this.stack = document.getElementById('modalStack');
    }
    
    /**
     * 綁定全域事件
     */
    attachGlobalEvents() {
        // ESC 關閉
        if (this.closeOnEscape) {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.openModals.length > 0) {
                    this.closeTopModal();
                }
            });
        }
        
        // Backdrop 點擊
        if (this.closeOnBackdrop) {
            this.backdrop.addEventListener('click', () => {
                this.closeTopModal();
            });
        }
        
        // 監聽表單變更
        if (this.preserveFormState) {
            this.observeFormChanges();
        }
    }
    
    /**
     * 監聽表單變更
     */
    observeFormChanges() {
        document.addEventListener('input', (e) => {
            if (e.target.closest('.workspace-content')) {
                window.AppState = window.AppState || {};
                window.AppState.formDirty = true;
            }
        });
    }
    
    /**
     * 設定當前使用者
     */
    setCurrentUser(user) {
        this.currentUser = user;
    }
    
    /**
     * 檢查編輯權限
     */
    canEdit(docType, docOwnerId) {
        if (!this.currentUser) return false;
        
        const userTitle = this.currentUser.title || '';
        const userId = this.currentUser.staff_code || this.currentUser.id;
        
        // 老闆和會計擁有所有權限
        if (userTitle === '老闆' || userTitle.includes('會計')) {
            return true;
        }
        
        // 銷貨單 (SALES) 不可編輯
        if (docType === 'SALES') {
            return false;
        }
        
        // 報價單 (QUOTE) 和 訂單 (ORDER)：同單位可編輯
        if (docType === 'QUOTE' || docType === 'ORDER') {
            // 檢查是否為建立者
            if (docOwnerId && docOwnerId === userId) {
                return true;
            }
            // TODO: 檢查是否為同單位
            return true;
        }
        
        return false;
    }
    
    /**
     * 開啟 Modal
     */
    open(options) {
        const {
            id = 'modal-' + Date.now(),
            title = '詳情',
            content,
            docType = 'QUOTE',
            docOwnerId = null,
            data = null,
            size = 'medium', // small, medium, large, full
            onSave = null,
            onClose = null,
            customActions = []
        } = options;
        
        // 檢查權限
        const canEdit = this.canEdit(docType, docOwnerId);
        
        // 備份表單狀態
        if (this.preserveFormState) {
            this.backupFormState();
        }
        
        // 建立 Modal 元素
        const modalEl = this.createModalElement({
            id,
            title,
            content,
            canEdit,
            docType,
            data,
            size,
            onSave,
            customActions
        });
        
        // 加入堆疊
        this.stack.appendChild(modalEl);
        this.openModals.push({
            id,
            element: modalEl,
            onClose,
            canEdit,
            data
        });
        
        // 顯示 Backdrop
        this.showBackdrop();
        
        // 動畫進入
        requestAnimationFrame(() => {
            modalEl.classList.add('active');
        });
        
        // 聚焦第一個輸入框
        if (canEdit) {
            const firstInput = modalEl.querySelector('input:not([readonly]), select:not([disabled]), textarea:not([readonly])');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
        
        // 觸發事件
        this.dispatchEvent('modal:open', { id, canEdit, docType });
        
        return id;
    }
    
    /**
     * 建立 Modal 元素
     */
    createModalElement(options) {
        const { id, title, content, canEdit, docType, data, size, onSave, customActions } = options;
        
        const modal = document.createElement('div');
        modal.id = id;
        modal.className = `modal-wrapper modal-${size}`;
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', `${id}-title`);
        
        // 尺寸對應的最大寬度
        const sizeMap = {
            'small': '400px',
            'medium': '600px',
            'large': '800px',
            'full': '95vw'
        };
        
        modal.style.cssText = `
            max-width: ${sizeMap[size] || sizeMap.medium};
        `;
        
        // 權限提示
        const permissionTip = canEdit 
            ? '<span class="permission-tip edit">✏️ 您可以編輯此單據</span>'
            : '<span class="permission-tip view">👁️ 您僅能檢視此單據</span>';
        
        // 操作按鈕
        const actions = this.buildActions({ canEdit, onSave, customActions, modalId: id });
        
        modal.innerHTML = `
            <div class="modal-content">
                <header class="modal-header">
                    <div class="modal-title-wrapper">
                        <h2 class="modal-title" id="${id}-title">${title}</h2>
                        ${permissionTip}
                    </div>
                    <button class="modal-close" onclick="ModalSystem.getInstance().close('${id}')" aria-label="關閉">
                        <span>✕</span>
                    </button>
                </header>
                <div class="modal-body" id="${id}-body">
                    ${typeof content === 'string' ? content : ''}
                </div>
                <footer class="modal-footer" id="${id}-footer">
                    ${actions}
                </footer>
            </div>
        `;
        
        // 如果是 HTMLElement，附加到 body
        if (content instanceof HTMLElement) {
            const bodyEl = modal.querySelector(`#${id}-body`);
            bodyEl.innerHTML = '';
            bodyEl.appendChild(content);
        }
        
        // 綁定表單事件
        this.attachFormEvents(modal, canEdit);
        
        return modal;
    }
    
    /**
     * 建立操作按鈕
     */
    buildActions({ canEdit, onSave, customActions, modalId }) {
        const buttons = [];
        
        // 自定義操作
        customActions.forEach(action => {
            buttons.push(`
                <button class="btn ${action.class || 'btn-secondary'}" 
                        onclick="${action.onClick}"
                        ${action.disabled ? 'disabled' : ''}>
                    ${action.icon || ''} ${action.label}
                </button>
            `);
        });
        
        // 關閉按鈕
        buttons.push(`
            <button class="btn btn-secondary" onclick="ModalSystem.getInstance().close('${modalId}')">
                關閉
            </button>
        `);
        
        // 儲存按（僅有編輯權限時顯示）
        if (canEdit && onSave) {
            buttons.push(`
                <button class="btn btn-primary" id="${modalId}-saveBtn" onclick="${onSave}">
                    💾 儲存
                </button>
            `);
        }
        
        return buttons.join('');
    }
    
    /**
     * 綁定表單事件
     */
    attachFormEvents(modal, canEdit) {
        const form = modal.querySelector('form');
        if (!form) return;
        
        // 如果無編輯權限，禁用所有輸入
        if (!canEdit) {
            form.querySelectorAll('input, select, textarea').forEach(input => {
                input.readOnly = true;
                input.disabled = true;
            });
            
            form.querySelectorAll('button:not(.modal-close)').forEach(btn => {
                btn.disabled = true;
            });
        }
        
        // 監聽表單變更
        form.addEventListener('input', () => {
            modal.dataset.dirty = 'true';
        });
    }
    
    /**
     * 關閉 Modal
     */
    close(id) {
        const modalIndex = this.openModals.findIndex(m => m.id === id);
        if (modalIndex === -1) return;
        
        const modal = this.openModals[modalIndex];
        
        // 檢查是否有未儲存的變更
        if (modal.element.dataset.dirty === 'true') {
            if (!confirm('您有未儲存的變更，確定要關閉嗎？')) {
                return;
            }
        }
        
        // 執行關閉回調
        if (modal.onClose) {
            modal.onClose(modal.data);
        }
        
        // 動畫離開
        modal.element.classList.remove('active');
        
        setTimeout(() => {
            modal.element.remove();
            this.openModals.splice(modalIndex, 1);
            
            // 隱藏 Backdrop（如果沒有其他 Modal）
            if (this.openModals.length === 0) {
                this.hideBackdrop();
                this.restoreFormState();
            }
        }, 300);
        
        // 觸發事件
        this.dispatchEvent('modal:close', { id });
    }
    
    /**
     * 關閉最頂層 Modal
     */
    closeTopModal() {
        if (this.openModals.length > 0) {
            const topModal = this.openModals[this.openModals.length - 1];
            this.close(topModal.id);
        }
    }
    
    /**
     * 關閉所有 Modal
     */
    closeAll() {
        [...this.openModals].forEach(modal => {
            this.close(modal.id);
        });
    }
    
    /**
     * 顯示 Backdrop
     */
    showBackdrop() {
        this.backdrop.style.display = 'block';
        requestAnimationFrame(() => {
            this.backdrop.classList.add('active');
        });
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * 隱藏 Backdrop
     */
    hideBackdrop() {
        this.backdrop.classList.remove('active');
        setTimeout(() => {
            this.backdrop.style.display = 'none';
        }, 300);
        document.body.style.overflow = '';
    }
    
    /**
     * 備份表單狀態
     */
    backupFormState() {
        const workspace = document.querySelector('.workspace-content');
        if (!workspace) return;
        
        const form = workspace.querySelector('form');
        if (form) {
            this.formBackup = new FormData(form);
        }
    }
    
    /**
     * 還原表單狀態
     */
    restoreFormState() {
        if (!this.formBackup) return;
        
        const workspace = document.querySelector('.workspace-content');
        if (!workspace) return;
        
        const form = workspace.querySelector('form');
        if (form) {
            for (let [key, value] of this.formBackup.entries()) {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = value;
                }
            }
        }
        
        this.formBackup = null;
    }
    
    /**
     * 更新 Modal 內容
     */
    updateContent(id, content) {
        const modal = this.openModals.find(m => m.id === id);
        if (!modal) return;
        
        const bodyEl = document.getElementById(`${id}-body`);
        if (bodyEl) {
            if (typeof content === 'string') {
                bodyEl.innerHTML = content;
            } else if (content instanceof HTMLElement) {
                bodyEl.innerHTML = '';
                bodyEl.appendChild(content);
            }
        }
    }
    
    /**
     * 更新 Modal 標題
     */
    updateTitle(id, title) {
        const titleEl = document.getElementById(`${id}-title`);
        if (titleEl) {
            titleEl.textContent = title;
        }
    }
    
    /**
     * 觸發自定義事件
     */
    dispatchEvent(eventName, detail) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
    
    /**
     * 銷毀 Modal 系統
     */
    destroy() {
        this.closeAll();
        if (this.modalContainer) {
            this.modalContainer.remove();
        }
    }
    
    // 單例模式
    static instance = null;
    static getInstance(options) {
        if (!ModalSystem.instance) {
            ModalSystem.instance = new ModalSystem(options);
        }
        return ModalSystem.instance;
    }
}

// ============================================
// CSS Styles for Modal System
// ============================================

const modalStyles = `
    /* Modal Container */
    #modal-system-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 5000;
    }
    
    /* Backdrop */
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(4px);
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: auto;
    }
    
    .modal-backdrop.active {
        opacity: 1;
    }
    
    /* Modal Stack */
    .modal-stack {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        padding: 20px;
    }
    
    /* Modal Wrapper */
    .modal-wrapper {
        position: relative;
        width: 100%;
        max-height: 90vh;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        opacity: 0;
        transform: scale(0.95) translateY(20px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        pointer-events: auto;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .modal-wrapper.active {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
    
    /* Modal Sizes */
    .modal-small { max-width: 400px; }
    .modal-medium { max-width: 600px; }
    .modal-large { max-width: 800px; }
    .modal-full { max-width: 95vw; max-height: 95vh; }
    
    /* Modal Content */
    .modal-content {
        display: flex;
        flex-direction: column;
        max-height: 90vh;
    }
    
    /* Modal Header */
    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 20px 24px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .modal-title-wrapper {
        flex: 1;
        min-width: 0;
    }
    
    .modal-title {
        font-size: 20px;
        font-weight: 600;
        color: #fff;
        margin: 0 0 8px 0;
    }
    
    .permission-tip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 4px;
    }
    
    .permission-tip.edit {
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
    }
    
    .permission-tip.view {
        background: rgba(136, 146, 176, 0.2);
        color: #8892b0;
    }
    
    .modal-close {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #8892b0;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        margin-left: 16px;
        flex-shrink: 0;
    }
    
    .modal-close:hover {
        background: #f44336;
        color: white;
        border-color: #f44336;
    }
    
    /* Modal Body */
    .modal-body {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
    }
    
    .modal-body:has(> .empty-state) {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Modal Footer */
    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        padding: 16px 24px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.2);
    }
    
    /* Form Styles in Modal */
    .modal-body .form-section {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .modal-body .form-section:last-child {
        margin-bottom: 0;
    }
    
    .modal-body .form-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 16px;
    }
    
    .modal-body .form-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .modal-body .form-label {
        font-size: 13px;
        color: #8892b0;
        font-weight: 500;
    }
    
    .modal-body .form-input {
        padding: 10px 14px;
        background: #0a0a0a;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        color: #fff;
        font-size: 14px;
        transition: all 0.2s;
    }
    
    .modal-body .form-input:focus {
        outline: none;
        border-color: #00d4ff;
        box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
    }
    
    .modal-body .form-input:read-only,
    .modal-body .form-input:disabled {
        background: rgba(255, 255, 255, 0.05);
        color: #64748b;
        cursor: not-allowed;
    }
    
    /* Responsive */
    @media (max-width: 640px) {
        .modal-stack {
            padding: 10px;
        }
        
        .modal-wrapper {
            max-width: 100% !important;
            max-height: 95vh;
        }
        
        .modal-header {
            padding: 16px 20px;
        }
        
        .modal-body {
            padding: 20px;
        }
        
        .modal-footer {
            padding: 12px 20px;
            flex-direction: column-reverse;
        }
        
        .modal-footer .btn {
            width: 100%;
        }
    }
    
    /* Animation Keyframes */
    @keyframes modalEnter {
        from {
            opacity: 0;
            transform: scale(0.95) translateY(20px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }
    
    @keyframes modalLeave {
        from {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
        to {
            opacity: 0;
            transform: scale(0.95) translateY(20px);
        }
    }
`;

// 自動注入樣式
(function injectModalStyles() {
    if (document.getElementById('modal-system-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'modal-system-styles';
    styleEl.textContent = modalStyles;
    document.head.appendChild(styleEl);
})();

// 匯出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ModalSystem };
} else {
    window.ModalSystem = ModalSystem;
}