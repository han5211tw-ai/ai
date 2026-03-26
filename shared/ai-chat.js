/**
 * ERP AI 聊天機器人 - 浮動視窗組件
 * 支援 SSE 串流、多輪對話、ReadableStream 偵測
 */

(function() {
    'use strict';

    // 防止重複初始化
    if (window.ERPAIChat) return;

    const AI_CHAT_CONFIG = {
        apiEndpoint: '/api/chat',
        storageKey: 'erp_ai_session_id',
        maxHistory: 50
    };

    class ERPChatBot {
        constructor() {
            this.sessionId = this._getSessionId();
            this.messages = [];
            this.isOpen = false;
            this.isStreaming = false;
            this.container = null;
            this._init();
        }

        _getSessionId() {
            let sid = sessionStorage.getItem(AI_CHAT_CONFIG.storageKey);
            if (!sid) {
                sid = 'erp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem(AI_CHAT_CONFIG.storageKey, sid);
            }
            return sid;
        }

        _init() {
            this._createStyles();
            this._createDOM();
            this._bindEvents();
        }

        _createStyles() {
            if (document.getElementById('erp-ai-chat-styles')) return;

            const styles = document.createElement('style');
            styles.id = 'erp-ai-chat-styles';
            styles.textContent = `
                /* 浮動按鈕 */
                .erp-ai-chat-float-btn {
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #FABF13 0%, #F59E0B 100%);
                    border: none;
                    box-shadow: 0 4px 12px rgba(250, 191, 19, 0.4);
                    cursor: pointer;
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.3s ease;
                }
                .erp-ai-chat-float-btn:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 20px rgba(250, 191, 19, 0.5);
                }
                .erp-ai-chat-float-btn svg {
                    width: 28px;
                    height: 28px;
                    fill: #1a1a2e;
                }
                .erp-ai-chat-float-btn.hidden {
                    opacity: 0;
                    pointer-events: none;
                }

                /* 聊天視窗 */
                .erp-ai-chat-window {
                    position: fixed;
                    bottom: 90px;
                    right: 24px;
                    width: 380px;
                    height: 520px;
                    background: #1a1a2e;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                    display: flex;
                    flex-direction: column;
                    z-index: 9998;
                    overflow: hidden;
                    border: 1px solid rgba(250, 191, 19, 0.2);
                    transition: all 0.3s ease;
                    opacity: 0;
                    transform: translateY(20px) scale(0.95);
                    pointer-events: none;
                }
                .erp-ai-chat-window.open {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                    pointer-events: auto;
                }

                /* 視窗頭部 */
                .erp-ai-chat-header {
                    background: linear-gradient(135deg, #FABF13 0%, #F59E0B 100%);
                    padding: 16px 20px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                .erp-ai-chat-header-title {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    color: #1a1a2e;
                    font-weight: 600;
                    font-size: 15px;
                }
                .erp-ai-chat-header-title svg {
                    width: 20px;
                    height: 20px;
                    fill: #1a1a2e;
                }
                .erp-ai-chat-close {
                    background: none;
                    border: none;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                .erp-ai-chat-close:hover {
                    background: rgba(26, 26, 46, 0.1);
                }
                .erp-ai-chat-close svg {
                    width: 20px;
                    height: 20px;
                    fill: #1a1a2e;
                }

                /* 訊息區域 */
                .erp-ai-chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                .erp-ai-chat-messages::-webkit-scrollbar {
                    width: 6px;
                }
                .erp-ai-chat-messages::-webkit-scrollbar-track {
                    background: transparent;
                }
                .erp-ai-chat-messages::-webkit-scrollbar-thumb {
                    background: rgba(250, 191, 19, 0.3);
                    border-radius: 3px;
                }

                /* 訊息氣泡 */
                .erp-ai-chat-message {
                    max-width: 85%;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 14px;
                    line-height: 1.6;
                    word-wrap: break-word;
                    animation: messageFadeIn 0.3s ease;
                }
                @keyframes messageFadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .erp-ai-chat-message.user {
                    align-self: flex-end;
                    background: linear-gradient(135deg, #FABF13 0%, #F59E0B 100%);
                    color: #1a1a2e;
                    border-bottom-right-radius: 4px;
                }
                .erp-ai-chat-message.bot {
                    align-self: flex-start;
                    background: #2d2d44;
                    color: #e0e0e0;
                    border-bottom-left-radius: 4px;
                }
                .erp-ai-chat-message.bot.streaming::after {
                    content: '▌';
                    animation: cursorBlink 1s infinite;
                    color: #FABF13;
                }
                @keyframes cursorBlink {
                    0%, 50% { opacity: 1; }
                    51%, 100% { opacity: 0; }
                }
                .erp-ai-chat-message.error {
                    background: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.3);
                }

                /* 輸入區域 */
                .erp-ai-chat-input-area {
                    padding: 12px 16px 16px;
                    border-top: 1px solid rgba(250, 191, 19, 0.1);
                    display: flex;
                    gap: 10px;
                    align-items: flex-end;
                }
                .erp-ai-chat-input {
                    flex: 1;
                    background: #2d2d44;
                    border: 1px solid rgba(250, 191, 19, 0.2);
                    border-radius: 10px;
                    padding: 10px 14px;
                    color: #e0e0e0;
                    font-size: 14px;
                    resize: none;
                    min-height: 20px;
                    max-height: 120px;
                    font-family: inherit;
                    line-height: 1.5;
                }
                .erp-ai-chat-input:focus {
                    outline: none;
                    border-color: #FABF13;
                }
                .erp-ai-chat-input::placeholder {
                    color: #6b7280;
                }
                .erp-ai-chat-send {
                    width: 40px;
                    height: 40px;
                    border-radius: 10px;
                    background: linear-gradient(135deg, #FABF13 0%, #F59E0B 100%);
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s;
                    flex-shrink: 0;
                }
                .erp-ai-chat-send:hover:not(:disabled) {
                    transform: scale(1.05);
                }
                .erp-ai-chat-send:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .erp-ai-chat-send svg {
                    width: 18px;
                    height: 18px;
                    fill: #1a1a2e;
                }

                /* 歡迎訊息 */
                .erp-ai-chat-welcome {
                    text-align: center;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 13px;
                }
                .erp-ai-chat-welcome-icon {
                    width: 48px;
                    height: 48px;
                    margin: 0 auto 12px;
                    background: rgba(250, 191, 19, 0.1);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .erp-ai-chat-welcome-icon svg {
                    width: 24px;
                    height: 24px;
                    fill: #FABF13;
                }

                /* 響應式 */
                @media (max-width: 480px) {
                    .erp-ai-chat-window {
                        width: calc(100vw - 32px);
                        height: 60vh;
                        right: 16px;
                        bottom: 80px;
                    }
                    .erp-ai-chat-float-btn {
                        right: 16px;
                        bottom: 16px;
                    }
                }
            `;
            document.head.appendChild(styles);
        }

        _createDOM() {
            // 浮動按鈕
            this.floatBtn = document.createElement('button');
            this.floatBtn.className = 'erp-ai-chat-float-btn';
            this.floatBtn.innerHTML = `
                <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.82.38 3.55 1.07 5.11L2 22l4.89-1.07A9.96 9.96 0 0 0 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-1 14.5c-2.49 0-4.5-2.01-4.5-4.5S8.51 7.5 11 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm5.5-7h-1v-1h1v1zm0-2h-1v-1h1v1z"/></svg>
            `;

            // 聊天視窗
            this.chatWindow = document.createElement('div');
            this.chatWindow.className = 'erp-ai-chat-window';
            this.chatWindow.innerHTML = `
                <div class="erp-ai-chat-header">
                    <div class="erp-ai-chat-header-title">
                        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.82.38 3.55 1.07 5.11L2 22l4.89-1.07A9.96 9.96 0 0 0 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-1 14.5c-2.49 0-4.5-2.01-4.5-4.5S8.51 7.5 11 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm5.5-7h-1v-1h1v1zm0-2h-1v-1h1v1z"/></svg>
                        <span>AI 助理</span>
                    </div>
                    <button class="erp-ai-chat-close">
                        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                </div>
                <div class="erp-ai-chat-messages">
                    <div class="erp-ai-chat-welcome">
                        <div class="erp-ai-chat-welcome-icon">
                            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.82.38 3.55 1.07 5.11L2 22l4.89-1.07A9.96 9.96 0 0 0 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-1 14.5c-2.49 0-4.5-2.01-4.5-4.5S8.51 7.5 11 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm5.5-7h-1v-1h1v1zm0-2h-1v-1h1v1z"/></svg>
                        </div>
                        <div>我是公司內部 AI 助理</div>
                        <div style="margin-top:4px;font-size:12px;">可以回答 ERP 操作、業務流程、一般知識等問題</div>
                    </div>
                </div>
                <div class="erp-ai-chat-input-area">
                    <textarea class="erp-ai-chat-input" placeholder="輸入訊息..." rows="1"></textarea>
                    <button class="erp-ai-chat-send">
                        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                    </button>
                </div>
            `;

            document.body.appendChild(this.floatBtn);
            document.body.appendChild(this.chatWindow);

            this.messagesContainer = this.chatWindow.querySelector('.erp-ai-chat-messages');
            this.input = this.chatWindow.querySelector('.erp-ai-chat-input');
            this.sendBtn = this.chatWindow.querySelector('.erp-ai-chat-send');
            this.closeBtn = this.chatWindow.querySelector('.erp-ai-chat-close');
        }

        _bindEvents() {
            // 開關視窗
            this.floatBtn.addEventListener('click', () => this.toggle());
            this.closeBtn.addEventListener('click', () => this.close());

            // 輸入框自動調整高度
            this.input.addEventListener('input', () => {
                this.input.style.height = 'auto';
                this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
            });

            // Enter 換行，按鈕送出（Shift+Enter 也是換行）
            this.input.addEventListener('keydown', (e) => {
                // 不做任何攔截，讓 Enter 預設行為（換行）
                // 只有按送出按鈕才會送出
            });

            // 送出按鈕
            this.sendBtn.addEventListener('click', () => this._sendMessage());

            // 點擊外部關閉
            document.addEventListener('click', (e) => {
                if (this.isOpen && !this.chatWindow.contains(e.target) && !this.floatBtn.contains(e.target)) {
                    this.close();
                }
            });
        }

        toggle() {
            this.isOpen ? this.close() : this.open();
        }

        open() {
            this.isOpen = true;
            this.chatWindow.classList.add('open');
            this.floatBtn.classList.add('hidden');
            this.input.focus();
        }

        close() {
            this.isOpen = false;
            this.chatWindow.classList.remove('open');
            this.floatBtn.classList.remove('hidden');
        }

        _addMessage(content, role) {
            const msg = document.createElement('div');
            msg.className = `erp-ai-chat-message ${role}`;
            msg.textContent = content;
            this.messagesContainer.appendChild(msg);
            this._scrollToBottom();
            return msg;
        }

        _scrollToBottom() {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }

        // 過濾思考區塊和 SQL 查詢，只保留最終答案
        _filterThinkBlocks(text) {
            // 移除 <think>...</think> 思考區塊
            let filtered = text.replace(/<think>[\s\S]*?<\/think>/g, '');
            // 移除 ```sql ... ``` SQL 區塊
            filtered = filtered.replace(/```sql[\s\S]*?```/g, '');
            // 移除 "為了...我需要查詢..." 等思考過程句子
            filtered = filtered.replace(/為了[\s\S]*?我需要[\s\S]*?。/g, '');
            filtered = filtered.replace(/讓我[\s\S]*?查詢[\s\S]*?。/g, '');
            // 清理多餘空白行
            filtered = filtered.replace(/\n{3,}/g, '\n\n');
            return filtered.trim();
        }

        async _sendMessage() {
            const content = this.input.value.trim();
            if (!content || this.isStreaming) return;

            // 顯示使用者訊息
            this._addMessage(content, 'user');
            this.messages.push({ role: 'user', content });

            // 清空輸入框並重置高度
            this.input.value = '';
            this.input.style.height = 'auto';
            this.input.rows = 1;

            // 顯示機器人訊息（串流中）
            const botMsg = this._addMessage('', 'bot');
            botMsg.classList.add('streaming');

            this.isStreaming = true;
            this.sendBtn.disabled = true;

            try {
                const response = await fetch(AI_CHAT_CONFIG.apiEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: this.messages,
                        session_id: this.sessionId
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                let fullReply = '';

                // 偵測 ReadableStream 支援
                if (window.ReadableStream && response.body) {
                    // 使用串流
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value, { stream: true });
                        const lines = chunk.split('\n');

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const dataStr = line.slice(6);
                                if (dataStr === '[DONE]') continue;
                                try {
                                    const data = JSON.parse(dataStr);
                                    if (data.content) {
                                        fullReply += data.content;
                                        // 過濾思考區塊後顯示
                                        botMsg.textContent = this._filterThinkBlocks(fullReply);
                                        this._scrollToBottom();
                                    }
                                    if (data.error) {
                                        throw new Error(data.error);
                                    }
                                } catch (e) {
                                    // 忽略 JSON 解析錯誤
                                }
                            }
                        }
                    }
                } else {
                    // Fallback: 一次解析
                    const text = await response.text();
                    const lines = text.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.slice(6);
                            if (dataStr === '[DONE]') continue;
                            try {
                                const data = JSON.parse(dataStr);
                                if (data.content) {
                                    fullReply += data.content;
                                }
                            } catch (e) {}
                        }
                    }
                    botMsg.textContent = this._filterThinkBlocks(fullReply);
                }

                // 儲存機器人回覆
                const filteredReply = this._filterThinkBlocks(fullReply);
                this.messages.push({ role: 'assistant', content: filteredReply });

                // 限制歷史記錄長度
                if (this.messages.length > AI_CHAT_CONFIG.maxHistory) {
                    this.messages = this.messages.slice(-AI_CHAT_CONFIG.maxHistory);
                }

            } catch (error) {
                console.error('[AI Chat] Error:', error);
                botMsg.classList.remove('streaming');
                botMsg.classList.add('error');
                botMsg.textContent = '抱歉，發生錯誤，請稍後再試。';
            } finally {
                botMsg.classList.remove('streaming');
                this.isStreaming = false;
                this.sendBtn.disabled = false;
            }
        }
    }

    // 初始化
    window.ERPAIChat = new ERPChatBot();
})();
