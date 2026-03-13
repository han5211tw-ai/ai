/**
 * 共用登入元件 auth_ui.js v2.0
 * 統一所有頁面的登入介面與流程
 * Version: 20250304-0200
 * ChangeLog:
 *   - 20250304: 全新科技風格登入介面（玻璃擬態 + 霓虹光暈）
 *   - 20250304: 新增密碼顯示/隱藏切換功能
 *   - 20250304: 新增輸入框焦點動畫（鎖圖示變閃電）
 *   - 20250304: 新增底部狀態列顯示
 *   - 20250303: 新增自動過期機制（每天晚上9點自動登出）
 *   - 20250303: 新增 getTonight9PM() 和 isAuthExpired() 函數
 *   - 20250303: 修改 getAuthData() 自動檢查過期時間
 * 顏色定義在 auth_ui.css 中使用 CSS 變數
 */

(function() {
    'use strict';

    // 權限等級定義
    const ROLE_LEVELS = {
        'staff': 1,      // 一般員工
        'accountant': 2, // 會計/督導
        'boss': 3        // 老闆/管理員
    };

    // 頁面權限對應表
    const PAGE_PERMISSIONS = {
        'needs_input.html': 'staff',
        'needs_input_v2.html': 'staff',
        'service_record.html': 'staff',
        'roster_input.html': 'staff',
        'supervision_score.html': 'accountant',
        'admin.html': 'boss',
        'boss.html': 'boss'
    };

    // 建立登入 Modal HTML（只使用 CSS 類，不寫死顏色）
    function createLoginModal() {
        if (document.getElementById('auth-login-modal')) return;

        // 載入 CSS（如果還沒載入）
        if (!document.getElementById('auth-ui-css')) {
            const link = document.createElement('link');
            link.id = 'auth-ui-css';
            link.rel = 'stylesheet';
            link.href = 'shared/auth_ui.css';
            document.head.appendChild(link);
        }

        const modal = document.createElement('div');
        modal.id = 'auth-login-modal';
        modal.innerHTML = `
            <div id="auth-login-overlay">
                <div id="auth-login-box">
                    <!-- 頂部科技圖示 -->
                    <div id="auth-icon-container">
                        <div id="auth-icon-ring-outer"></div>
                        <div id="auth-icon-ring-inner"></div>
                        <div id="auth-icon-bg">
                            <svg id="auth-shield-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            </svg>
                        </div>
                    </div>
                    
                    <!-- 標題 -->
                    <h2 id="auth-login-title">系統登入</h2>
                    <p id="auth-login-subtitle">請輸入密碼驗證身份</p>
                    
                    <!-- 輸入框 -->
                    <div id="auth-input-wrapper">
                        <div id="auth-input-glow"></div>
                        <svg id="auth-lock-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                        <input type="password" id="auth-password-input" maxlength="4" placeholder="••••" onkeypress="if(event.key==='Enter') window.authSubmitLogin()">
                        <button type="button" id="auth-toggle-password" onclick="window.authTogglePassword()" aria-label="切換密碼顯示">
                            <svg id="auth-eye-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                            <svg id="auth-eye-off-icon" class="auth-hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                                <line x1="1" y1="1" x2="23" y2="23"></line>
                            </svg>
                        </button>
                    </div>
                    
                    <!-- 登入按鈕 -->
                    <button id="auth-login-btn" onclick="window.authSubmitLogin()">
                        <svg id="auth-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                            <polyline points="10 17 15 12 10 7"></polyline>
                            <line x1="15" y1="12" x2="3" y2="12"></line>
                        </svg>
                        <span id="auth-btn-text">登入</span>
                    </button>
                    
                    <!-- 錯誤訊息 -->
                    <div id="auth-login-error"></div>
                    <div id="auth-login-loading">驗證中...</div>
                    
                    <!-- 底部狀態列 -->
                    <div id="auth-status-bar">
                        <div id="auth-system-status">
                            <span id="auth-status-dot"></span>
                            <span>系統正常</span>
                        </div>
                        <a href="#" id="auth-override-link" onclick="event.preventDefault();">忘記密碼？</a>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // 顯示登入 Modal
    function showLoginModal(options) {
        createLoginModal();
        const modal = document.getElementById('auth-login-modal');
        const title = document.getElementById('auth-login-title');
        const subtitle = document.getElementById('auth-login-subtitle');
        const errorDiv = document.getElementById('auth-login-error');
        
        // 重置狀態
        errorDiv.textContent = '';
        document.getElementById('auth-password-input').value = '';
        
        // 設定標題
        if (options.title) {
            title.textContent = options.title;
        }
        if (options.subtitle) {
            subtitle.textContent = options.subtitle;
        }
        
        modal.style.display = 'block';
        
        // 自動聚焦
        setTimeout(() => {
            document.getElementById('auth-password-input').focus();
        }, 100);
        
        // 添加焦點事件監聽（鎖圖示變閃電）
        const passwordInput = document.getElementById('auth-password-input');
        const lockIcon = document.getElementById('auth-lock-icon');
        if (passwordInput && lockIcon) {
            passwordInput.addEventListener('focus', () => {
                lockIcon.classList.add('zap');
                lockIcon.innerHTML = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>';
            });
            passwordInput.addEventListener('blur', () => {
                lockIcon.classList.remove('zap');
                lockIcon.innerHTML = '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>';
            });
        }
    }

    // 隱藏登入 Modal
    function hideLoginModal() {
        const modal = document.getElementById('auth-login-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // 切換密碼顯示/隱藏
    window.authTogglePassword = function() {
        const input = document.getElementById('auth-password-input');
        const eyeIcon = document.getElementById('auth-eye-icon');
        const eyeOffIcon = document.getElementById('auth-eye-off-icon');
        
        if (input.type === 'password') {
            input.type = 'text';
            eyeIcon.classList.add('auth-hidden');
            eyeOffIcon.classList.remove('auth-hidden');
        } else {
            input.type = 'password';
            eyeIcon.classList.remove('auth-hidden');
            eyeOffIcon.classList.add('auth-hidden');
        }
    };

    // 顯示錯誤訊息
    function showLoginError(message) {
        const errorDiv = document.getElementById('auth-login-error');
        if (errorDiv) {
            errorDiv.textContent = message;
        }
    }

    // 顯示/隱藏 Loading
    function setLoading(show) {
        const loadingDiv = document.getElementById('auth-login-loading');
        const btn = document.getElementById('auth-login-btn');
        const btnIcon = document.getElementById('auth-btn-icon');
        const btnText = document.getElementById('auth-btn-text');
        
        if (loadingDiv) {
            loadingDiv.style.display = show ? 'block' : 'none';
        }
        if (btn) {
            btn.disabled = show;
        }
        if (btnIcon && btnText) {
            if (show) {
                // 載入狀態：旋轉圖示 + "驗證中..."
                btnIcon.innerHTML = '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="31.416" stroke-dashoffset="10"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/></circle>';
                btnIcon.classList.add('spin');
                btnText.textContent = '驗證中...';
            } else {
                // 正常狀態：登入圖示 + "登入"
                btnIcon.innerHTML = '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line>';
                btnIcon.classList.remove('spin');
                btnText.textContent = '登入';
            }
        }
    }

    // 呼叫驗證 API
    async function callVerifyAPI(password) {
        const response = await fetch('/api/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        return await response.json();
    }

    // 檢查權限
    function checkPermission(userRole, requiredMinRole) {
        const userLevel = ROLE_LEVELS[userRole] || 1;
        const requiredLevel = ROLE_LEVELS[requiredMinRole] || 1;
        return userLevel >= requiredLevel;
    }

    // 取得今天晚上9點的時間戳（自動過期時間）
    function getTonight9PM() {
        const now = new Date();
        const tonight9PM = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 21, 0, 0);
        // 如果現在已經過了晚上9點，則設定為明天晚上9點
        if (now > tonight9PM) {
            tonight9PM.setDate(tonight9PM.getDate() + 1);
        }
        return tonight9PM.getTime();
    }

    // 檢查是否已過期
    function isAuthExpired(expireTime) {
        if (!expireTime) return true;
        return Date.now() > expireTime;
    }

    // 儲存登入資訊（含過期時間）
    function saveAuthData(data) {
        const authData = {
            name: data.name,
            department: data.department,
            title: data.title,
            loginTime: new Date().toISOString(),
            expireTime: getTonight9PM() // 今天晚上9點自動過期
        };
        sessionStorage.setItem('currentUser', JSON.stringify(authData));
        localStorage.setItem('currentUser', JSON.stringify(authData));
    }

    // 獲取登入資訊（檢查是否過期）
    function getAuthData() {
        const sessionData = sessionStorage.getItem('currentUser');
        const localData = localStorage.getItem('currentUser');
        const dataStr = sessionData || localData;
        
        if (!dataStr) return null;
        
        try {
            const data = JSON.parse(dataStr);
            
            // 檢查是否過期
            if (isAuthExpired(data.expireTime)) {
                console.log('[AuthUI] 登入已過期（晚上9點自動登出）');
                clearAuthData();
                return null;
            }
            
            return data;
        } catch (e) {
            console.error('[AuthUI] 解析登入資料失敗:', e);
            clearAuthData();
            return null;
        }
    }

    // 清除登入資訊
    function clearAuthData() {
        sessionStorage.removeItem('currentUser');
        localStorage.removeItem('currentUser');
    }

    // 判斷使用者角色
    function getUserRole(title) {
        if (!title) return 'staff';
        const t = title.toLowerCase();
        if (t.includes('老闆') || t.includes('老闆') || t.includes('管理員') || t.includes('boss')) {
            return 'boss';
        }
        if (t.includes('會計') || t.includes('督導') || t.includes('accountant') || t.includes('主管')) {
            return 'accountant';
        }
        return 'staff';
    }

    // 主要登入函數
    window.authSubmitLogin = async function() {
        const passwordInput = document.getElementById('auth-password-input');
        const password = passwordInput.value.trim();
        
        // 驗證格式
        if (!password || password.length !== 4 || !/^\d{4}$/.test(password)) {
            showLoginError('請輸入4位數字密碼');
            return;
        }
        
        setLoading(true);
        showLoginError('');
        
        try {
            const result = await callVerifyAPI(password);
            
            if (result.success) {
                // 儲存登入資訊
                saveAuthData(result);
                
                // 隱藏登入框
                hideLoginModal();
                
                // 觸發回調
                if (window.authSuccessCallback) {
                    window.authSuccessCallback(result);
                }
            } else {
                showLoginError(result.message || '密碼錯誤');
            }
        } catch (e) {
            console.error('Login error:', e);
            showLoginError('登入失敗，請稍後再試');
        } finally {
            setLoading(false);
        }
    };

    // 公開 API：requireLogin
    window.requireLogin = function(options) {
        options = options || {};
        
        return new Promise((resolve, reject) => {
            // 檢查是否已登入
            const authData = getAuthData();
            
            if (authData) {
                // 已登入，檢查權限
                const userRole = getUserRole(authData.title);
                const requiredRole = options.minRole || 'staff';
                
                if (!checkPermission(userRole, requiredRole)) {
                    // 權限不足
                    alert('⚠️ 權限不足：您沒有權限訪問此頁面');
                    reject(new Error('Permission denied'));
                    return;
                }
                
                // 有權限，直接返回（標記為已登入狀態）
                authData._justLoggedIn = false;
                resolve(authData);
                return;
            }
            
            // 未登入，顯示登入框
            window.authSuccessCallback = function(data) {
                const userRole = getUserRole(data.title);
                const requiredRole = options.minRole || 'staff';
                
                if (!checkPermission(userRole, requiredRole)) {
                    alert('⚠️ 權限不足：您沒有權限訪問此頁面');
                    clearAuthData();
                    reject(new Error('Permission denied'));
                    return;
                }
                
                // 標記為剛登入
                data._justLoggedIn = true;
                resolve(data);
            };
            
            showLoginModal({
                title: options.title || '🔐 請輸入密碼',
                subtitle: options.subtitle || '身分證後四碼驗證'
            });
        });
    };

    // 公開 API：登出
    window.authLogout = function() {
        clearAuthData();
        location.reload();
    };

    // 公開 API：獲取當前使用者
    window.getCurrentUser = function() {
        return getAuthData();
    };

    // 公開 API：檢查是否已登入
    window.isLoggedIn = function() {
        return getAuthData() !== null;
    };

    // 公開 API：檢查登入狀態（回傳 Promise，相容 checkAuth 用法）
    window.checkAuth = async function(options) {
        options = options || {};
        try {
            const result = await requireLogin(options);
            return {
                success: true,
                name: result.name,
                user: result.name,
                department: result.department,
                title: result.title
            };
        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    };

    // 自動判斷當前頁面所需權限並執行登入
    window.autoRequireLogin = function() {
        const path = window.location.pathname;
        const filename = path.split('/').pop() || 'index.html';
        
        // 根據頁面檔名決定權限
        let minRole = 'staff';
        for (const [page, role] of Object.entries(PAGE_PERMISSIONS)) {
            if (filename.includes(page.replace('.html', ''))) {
                minRole = role;
                break;
            }
        }
        
        console.log('[AuthUI] Auto require login for:', filename, 'minRole:', minRole);
        
        return requireLogin({
            minRole: minRole,
            title: '🔐 請輸入密碼',
            subtitle: '身分證後四碼驗證'
        });
    };

    console.log('[AuthUI] Shared auth component loaded. Version: 20250303-1301 (staff permission fix)');
})();
