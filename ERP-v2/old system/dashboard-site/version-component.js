/**
 * 版本號與更新日誌組件
 * 使用方法：
 * 1. 引入此 JS 檔案
 * 2. 在頁面中加入 <div id="versionBadge"></div>
 * 3. 定義 window.PAGE_VERSION 和 window.PAGE_CHANGELOG
 */

(function() {
    'use strict';
    
    // 等待 DOM 載入完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVersionComponent);
    } else {
        initVersionComponent();
    }
    
    function initVersionComponent() {
        // 檢查是否已定義版本資訊
        if (typeof window.PAGE_VERSION === 'undefined') {
            console.warn('[VersionComponent] 請定義 window.PAGE_VERSION');
            return;
        }
        
        const version = window.PAGE_VERSION;
        const changelog = window.PAGE_CHANGELOG || [];
        
        // 創建版本號按鈕
        const badge = document.createElement('div');
        badge.className = 'version-badge';
        badge.innerHTML = `v${version}`;
        badge.setAttribute('title', '點擊查看更新日誌');
        badge.onclick = function() {
            openChangelogModal(changelog, version);
        };
        
        document.body.appendChild(badge);
    }
    
    function openChangelogModal(changelog, currentVersion) {
        // 檢查是否已存在彈窗
        let existingModal = document.getElementById('changelogModal');
        if (existingModal) {
            existingModal.classList.add('active');
            return;
        }
        
        // 創建彈窗
        const modal = document.createElement('div');
        modal.id = 'changelogModal';
        modal.className = 'changelog-modal';
        
        // 組合日誌內容
        let changelogHTML = '';
        if (changelog.length === 0) {
            changelogHTML = '<li class="changelog-item"><span class="changelog-text">暫無更新記錄</span></li>';
        } else {
            changelogHTML = changelog.map(item => `
                <li class="changelog-item">
                    <span class="changelog-version">v${item.version}</span>
                    <div>
                        <div class="changelog-text">${item.text}</div>
                        ${item.date ? `<div class="changelog-date">${item.date}</div>` : ''}
                    </div>
                </li>
            `).join('');
        }
        
        modal.innerHTML = `
            <div class="changelog-content">
                <div class="changelog-header">
                    <h3 class="changelog-title">💡 系統更新日誌</h3>
                    <button class="changelog-close" onclick="closeChangelogModal()">&times;</button>
                </div>
                <ul class="changelog-list">
                    ${changelogHTML}
                </ul>
                <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: #8892b0; font-size: 0.85em;">當前版本：v${currentVersion}</span>
                </div>
            </div>
        `;
        
        // 點擊背景關閉
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeChangelogModal();
            }
        });
        
        // ESC 鍵關閉
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeChangelogModal();
            }
        });
        
        document.body.appendChild(modal);
        
        // 顯示彈窗
        setTimeout(function() {
            modal.classList.add('active');
        }, 10);
    }
    
    // 全域函式供外部呼叫
    window.closeChangelogModal = function() {
        const modal = document.getElementById('changelogModal');
        if (modal) {
            modal.classList.remove('active');
            setTimeout(function() {
                modal.remove();
            }, 300);
        }
    };
    
})();