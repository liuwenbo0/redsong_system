/**
 * making_agent.js
 * 负责 "问·古今" (making.html) 的 Agent 交互逻辑
 * 包括：对话流管理、意图识别响应、多模态卡片渲染、历史记录面板控制
 */

document.addEventListener('DOMContentLoaded', function() {
    // --- DOM 元素 ---
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const historyToggleBtn = document.getElementById('history-toggle');
    const mainGrid = document.querySelector('.main-grid');
    const quickPrompts = document.getElementById('quick-prompts');
    
    // --- 状态管理 ---
    let conversationHistory = []; // [{role: 'user', content: '...'}, {role: 'ai', content: '...'}]
    let isWaitingResponse = false;

    // --- 初始化 ---
    init();

    function init() {
        bindEvents();
        // 加载右侧历史记录面板
        loadHistoryPanel();
    }

    function bindEvents() {
        // 发送消息
        sendButton.addEventListener('click', handleSendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        // 历史记录开关 (移动端/折叠)
        historyToggleBtn.addEventListener('click', () => {
            mainGrid.classList.toggle('history-open');
        });

        // 快捷提示
        quickPrompts.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const text = e.target.dataset.question || e.target.textContent;
                chatInput.value = text;
                handleSendMessage();
            }
        });
        
        // 输入框监听 (控制发送按钮状态)
        chatInput.addEventListener('input', () => {
            if (chatInput.value.trim().length > 0) {
                sendButton.classList.add('is-active');
                sendButton.disabled = false;
            } else {
                sendButton.classList.remove('is-active');
                sendButton.disabled = true;
            }
        });

        // --- 历史记录面板事件 ---
        const clearHistoryButton = document.getElementById('clear-history-button');
        const modal = document.getElementById('delete-confirmation-modal');
        const confirmDeleteButton = document.getElementById('confirm-delete-button');
        const cancelDeleteButton = document.getElementById('cancel-delete-button');

        if (clearHistoryButton) {
            clearHistoryButton.addEventListener('click', () => modal.classList.remove('hidden'));
        }
        if (cancelDeleteButton) {
            cancelDeleteButton.addEventListener('click', () => modal.classList.add('hidden'));
        }
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.add('hidden');
            });
        }
        if (confirmDeleteButton) {
            confirmDeleteButton.addEventListener('click', handleClearHistory);
        }
    }

    // --- 历史记录面板逻辑 ---
    function loadHistoryPanel() {
        const historyList = document.getElementById('history-list');
        if (!historyList) return;

        const isVisitor = sessionStorage.getItem('visitorModeActive') === 'true';

        if (isVisitor) {
            let history = [];
            try {
                history = JSON.parse(localStorage.getItem('visitorChatHistory') || '[]');
            } catch (e) {
                localStorage.removeItem('visitorChatHistory');
            }
            renderHistoryList(history);
        } else {
            // 添加时间戳防止缓存
            fetch(`/api/chat/history?t=${new Date().getTime()}`)
            .then(response => {
                if (response.status === 401) {
                    historyList.innerHTML = '<p class="history-empty-placeholder">登录后可查看云端历史记录。</p>';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data && data.history) renderHistoryList(data.history);
            })
            .catch(error => {
                console.error("加载历史失败", error);
                historyList.innerHTML = '<p class="history-empty-placeholder">加载历史记录失败。</p>';
            });
        }
    }

    function renderHistoryList(historyItems) {
        const historyList = document.getElementById('history-list');
        historyList.innerHTML = ''; 
        
        if (historyItems && historyItems.length > 0) {
            [...historyItems].reverse().forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <p class="history-item-question">${item.question || ''}</p>
                    <p class="history-item-answer">${item.answer || ''}</p>
                    <p class="history-item-timestamp">${item.timestamp || ''}</p>
                `;
                historyList.appendChild(div);
            });
        } else {
            historyList.innerHTML = '<p class="history-empty-placeholder">暂无历史记录。</p>';
        }
    }

    async function handleClearHistory() {
        const modal = document.getElementById('delete-confirmation-modal');
        const isVisitor = sessionStorage.getItem('visitorModeActive') === 'true';
        
        if (isVisitor) {
            localStorage.removeItem('visitorChatHistory');
            loadHistoryPanel();
            modal.classList.add('hidden');
        } else {
            try {
                const resp = await fetch('/api/chat/history', { method: 'DELETE' });
                const data = await resp.json();
                if (data.success) {
                    loadHistoryPanel();
                } else {
                    alert('清除历史记录失败。');
                }
            } catch (e) {
                alert('清除失败，网络错误。');
            } finally {
                modal.classList.add('hidden');
            }
        }
    }

    // --- 核心逻辑: 发送消息 ---
    async function handleSendMessage() {
        const text = chatInput.value.trim();
        if (!text || isWaitingResponse) return;

        // 1. UI: 显示用户消息
        addMessage('user', text);
        chatInput.value = '';
        sendButton.classList.remove('is-active');
        sendButton.disabled = true;

        // 2. 状态: 记录历史
        addToHistory('user', text);

        // 3. UI: 显示思考中
        const typingId = showTypingIndicator();
        isWaitingResponse = true;

        try {
            // 4. API 请求
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_input: text,
                    conversation_history: conversationHistory
                })
            });

            const data = await response.json();
            removeTypingIndicator(typingId);

            if (!response.ok) {
                const errorMsg = data.error || data.message || '未知错误';
                throw new Error(errorMsg);
            }

            // 5. 处理响应
            handleAgentResponse(data);
            
            // 6. 刷新侧边栏历史记录
            setTimeout(loadHistoryPanel, 200);

        } catch (error) {
            console.error('Agent Error:', error);
            removeTypingIndicator(typingId);
            addMessage('ai', `抱歉，操作失败：${error.message || '请稍后再试'}`);
        } finally {
            isWaitingResponse = false;
            chatInput.focus();
        }
    }

    // --- 响应分发 ---
    function handleAgentResponse(data) {
        // 记录 AI 回复
        if (data.text_response) {
            addToHistory('assistant', data.text_response);
        }

        // 根据 response_type 渲染
        switch (data.response_type) {
            case 'text':
                addMessage('ai', data.text_response);
                break;
            
            case 'navigate':
                if (data.text_response) addMessage('ai', data.text_response);
                setTimeout(() => {
                    window.location.href = data.path;
                }, 1500); 
                break;

            case 'confirmation_required':
                if (data.text_response) addMessage('ai', data.text_response);
                renderConfirmationCard(data.data);
                break;
                
            case 'content_card':
                if (data.text_response) addMessage('ai', data.text_response);
                renderContentCard(data.card_type, data.data);
                break;
                
            default:
                addMessage('ai', data.text_response || '收到。');
        }
    }

    // --- 执行确认动作 ---
    async function executeConfirmedAction(intent, params) {
        const typingId = showTypingIndicator();
        
        try {
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    confirmed_action: { intent, params },
                    conversation_history: conversationHistory
                })
            });
            
            const data = await response.json();
            removeTypingIndicator(typingId);

            if (!response.ok) {
                throw new Error(data.error || '执行动作失败');
            }

            handleAgentResponse(data);
            setTimeout(loadHistoryPanel, 200);
            
        } catch (e) {
            removeTypingIndicator(typingId);
            addMessage('ai', `执行动作失败：${e.message || '请重试'}`);
        }
    }

    // --- UI 渲染函数 ---

    function addMessage(sender, text) {
        const row = document.createElement('div');
        row.className = `chat-row ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        const imgPath = sender === 'ai' ? '/static/images/HongXiaoYunFig.png' : 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix'; 
        avatar.innerHTML = `<img src="${imgPath}" alt="${sender}">`;
        
        const content = document.createElement('div');
        content.className = 'chat-bubble-content';
        
        if (typeof marked !== 'undefined') {
            content.innerHTML = marked.parse(text);
        } else {
            content.textContent = text;
        }

        row.appendChild(avatar);
        row.appendChild(content);
        
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = 'typing-' + Date.now();
        const row = document.createElement('div');
        row.id = id;
        row.className = 'chat-row ai';
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = `<img src="/static/images/HongXiaoYunFig.png" alt="ai">`;
        
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        
        row.appendChild(avatar);
        row.appendChild(indicator);
        chatMessages.appendChild(row);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function renderConfirmationCard(data) {
        const { intent, params } = data;
        const card = document.createElement('div');
        card.className = 'chat-row ai';
        const cardContent = document.createElement('div');
        cardContent.className = 'chat-bubble-content';
        cardContent.style.backgroundColor = '#fff';
        cardContent.style.border = '1px solid #e5e7eb';
        cardContent.style.width = '100%';
        cardContent.style.maxWidth = '300px';

        let title = '操作确认';
        let desc = '您确定要执行此操作吗？';
        
        if (intent === 'search_songs_by_keyword') {
            title = '🔍 搜索确认';
            desc = `即将为您搜索关于 **${params.keyword}** 的红歌。`;
        } else if (intent === 'create_song_lyrics') {
            title = '✍️ 创作确认';
            desc = `即将以 **${params.theme}** 为主题为您创作歌词。`;
        }

        cardContent.innerHTML = `
            <h3 style="font-weight:bold; margin-bottom:0.5rem; color:#1f2937;">${title}</h3>
            <div style="font-size:0.875rem; color:#4b5563; margin-bottom:1rem;">
                ${typeof marked !== 'undefined' ? marked.parse(desc) : desc}
            </div>
            <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
                <button class="cancel-btn" style="padding:4px 12px; border:1px solid #d1d5db; border-radius:4px; background:#fff; cursor:pointer;">取消</button>
                <button class="confirm-btn" style="padding:4px 12px; border:none; border-radius:4px; background:var(--theme-red); color:#fff; cursor:pointer;">确认执行</button>
            </div>
        `;
        
        const confirmBtn = cardContent.querySelector('.confirm-btn');
        const cancelBtn = cardContent.querySelector('.cancel-btn');
        
        confirmBtn.addEventListener('click', () => {
            cardContent.innerHTML = `<p style="color:#666; font-style:italic;">已确认执行。</p>`;
            executeConfirmedAction(intent, params);
        });
        
        cancelBtn.addEventListener('click', () => {
            cardContent.innerHTML = `<p style="color:#666; font-style:italic;">已取消操作。</p>`;
            addToHistory('user', '[用户取消了操作]');
        });

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = `<img src="/static/images/HongXiaoYunFig.png" alt="ai">`;
        
        card.appendChild(avatar);
        card.appendChild(cardContent);
        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function renderContentCard(cardType, data) {
        if (cardType === 'song_list') {
            // 后端返回的 data 直接就是歌曲数组，不需要 .songs
            renderSongListCard(data); 
        } else if (cardType === 'video_list') {
            renderVideoListCard(data);
        } else if (cardType === 'lyrics_card') {
            renderLyricsCard(data);
        } else {
            console.warn('Unknown card type:', cardType);
        }
    }

    function renderSongListCard(songs) {
        if (!songs || songs.length === 0) {
            addMessage('ai', '抱歉，没有找到相关歌曲。');
            return;
        }

        const card = document.createElement('div');
        card.className = 'chat-row ai';
        const content = document.createElement('div');
        content.className = 'chat-bubble-content';
        content.style.width = '100%';
        content.style.maxWidth = '400px'; 
        content.style.background = '#fff';

        let listHtml = `<div style="display:flex; flex-direction:column; gap:0.5rem;">`;
        songs.slice(0, 5).forEach(song => {
            listHtml += `
                <div style="display:flex; align-items:center; padding:0.5rem; background:#f9fafb; border-radius:0.375rem; border:1px solid #f3f4f6;">
                    <div style="flex-grow:1;">
                        <div style="font-weight:600; font-size:0.9rem;">${song.title}</div>
                        <div style="font-size:0.75rem; color:#6b7280;">${song.artist || '未知艺术家'}</div>
                    </div>
                    <a href="/circle?song_id=${song.id}" style="font-size:0.75rem; color:var(--theme-red); text-decoration:none; padding:2px 8px; border:1px solid var(--theme-red); border-radius:99px;">
                        去试听
                    </a>
                </div>
            `;
        });
        listHtml += `</div>`;

        content.innerHTML = `
            <h3 style="font-weight:bold; margin-bottom:0.5rem; border-bottom:1px solid #eee; padding-bottom:0.5rem;">为您找到 ${songs.length} 首歌曲</h3>
            ${listHtml}
        `;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = `<img src="/static/images/HongXiaoYunFig.png" alt="ai">`;
        
        card.appendChild(avatar);
        card.appendChild(content);
        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function renderVideoListCard(videos) {
        if (!videos || videos.length === 0) {
            addMessage('ai', '抱歉，没有找到相关视频。');
            return;
        }

        const card = document.createElement('div');
        card.className = 'chat-row ai';
        const content = document.createElement('div');
        content.className = 'chat-bubble-content';
        content.style.width = '100%';
        content.style.maxWidth = '400px'; 
        content.style.background = '#fff';

        let listHtml = `<div style="display:flex; flex-direction:column; gap:0.5rem;">`;
        videos.slice(0, 3).forEach(v => {
            listHtml += `
                <div style="display:flex; align-items:center; padding:0.5rem; background:#f9fafb; border-radius:0.375rem; border:1px solid #f3f4f6;">
                    <div style="flex-grow:1;">
                        <div style="font-weight:600; font-size:0.9rem;">${v.title}</div>
                        <div style="font-size:0.75rem; color:#6b7280;">${v.summary ? v.summary.substring(0, 20) + '...' : '暂无简介'}</div>
                    </div>
                    <a href="/plaza?article_id=${v.id}" style="font-size:0.75rem; color:var(--theme-red); text-decoration:none; padding:2px 8px; border:1px solid var(--theme-red); border-radius:99px;">
                        去观看
                    </a>
                </div>
            `;
        });
        listHtml += `</div>`;

        content.innerHTML = `
            <h3 style="font-weight:bold; margin-bottom:0.5rem; border-bottom:1px solid #eee; padding-bottom:0.5rem;">为您找到 ${videos.length} 个视频</h3>
            ${listHtml}
        `;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = `<img src="/static/images/HongXiaoYunFig.png" alt="ai">`;
        
        card.appendChild(avatar);
        card.appendChild(content);
        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function renderLyricsCard(data) {
        const { lyrics, theme, navigate_instruction } = data;
        
        const card = document.createElement('div');
        card.className = 'chat-row ai';
        const content = document.createElement('div');
        content.className = 'chat-bubble-content';
        content.style.background = '#fffefc'; // 纸张色
        content.style.border = '1px solid #e7e5e4';

        let jumpButtonHtml = '';
        if (navigate_instruction && navigate_instruction.path) {
            const btnId = 'lyrics-btn-' + Date.now();
            jumpButtonHtml = `
                <div style="margin-top:1rem; text-align:right;">
                    <button id="${btnId}" style="background:none; border:none; color:var(--theme-red); text-decoration:underline; cursor:pointer; font-size:0.8rem;">
                        前往「谱·华章」制作成曲 >
                    </button>
                </div>
            `;
            setTimeout(() => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', () => {
                        if (navigate_instruction.params && navigate_instruction.params.auto_fill_lyrics) {
                            localStorage.setItem('auto_fill_lyrics', navigate_instruction.params.auto_fill_lyrics);
                        }
                        window.location.href = navigate_instruction.path;
                    });
                }
            }, 0);
        }

        content.innerHTML = `
            <div style="text-align:center; margin-bottom:1rem;">
                <h3 style="font-weight:bold; font-size:1.1rem; color:#881337;">🎶 AI 原创红歌</h3>
                <p style="font-size:0.8rem; color:#78716c;">主题：${theme}</p>
            </div>
            <div style="white-space: pre-wrap; font-family: 'KaiTi', serif; line-height:1.8; color:#444; max-height:200px; overflow-y:auto;">${lyrics}</div>
            ${jumpButtonHtml}
        `;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.innerHTML = `<img src="/static/images/HongXiaoYunFig.png" alt="ai">`;
        
        card.appendChild(avatar);
        card.appendChild(content);
        chatMessages.appendChild(card);
        scrollToBottom();
    }

    // --- 辅助函数 ---
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addToHistory(role, content) {
        conversationHistory.push({ role, content });
        if (conversationHistory.length > 20) {
            conversationHistory = conversationHistory.slice(-20);
        }
    }
});