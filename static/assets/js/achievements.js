// ==================== 成就徽章页面逻辑 ====================

document.addEventListener('DOMContentLoaded', function() {
    // DOM 元素
    const totalScoreEl = document.getElementById('total-score');
    const unlockedCountEl = document.getElementById('unlocked-count');
    const progressPercentEl = document.getElementById('progress-percent');
    const unlockedBadge = document.getElementById('unlocked-badge');
    const lockedBadge = document.getElementById('locked-badge');
    const unlockedGrid = document.getElementById('unlocked-grid');
    const lockedGrid = document.getElementById('locked-grid');
    const leaderboardList = document.getElementById('leaderboard-list');
    const userPointsEl = document.getElementById('user-points');
    
    const categoryTabs = document.querySelectorAll('.category-tab');
    
    const detailOverlay = document.getElementById('achievement-detail-overlay');
    const detailIcon = document.getElementById('detail-icon');
    const detailName = document.getElementById('detail-name');
    const detailCategory = document.getElementById('detail-category');
    const detailDescription = document.getElementById('detail-description');
    const detailCondition = document.getElementById('detail-condition');
    const detailPoints = document.getElementById('detail-points');
    const closeDetailBtn = document.getElementById('close-detail-btn');
    
    let currentCategory = 'all';
    let allAchievements = [];
    let unlockedAchievements = [];
    
    // 初始化
    function init() {
        loadAchievements();
        loadLeaderboard();
        bindEvents();
    }
    
    // 绑定事件
    function bindEvents() {
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                categoryTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentCategory = tab.dataset.category;
                filterAchievements();
            });
        });
        
        closeDetailBtn.addEventListener('click', closeDetailModal);
        detailOverlay.addEventListener('click', (e) => {
            if (e.target === detailOverlay) {
                closeDetailModal();
            }
        });
        
        // 回到顶部按钮功能
        const backToTopBtn = document.getElementById('back-to-top-btn');
        if (backToTopBtn) {
            backToTopBtn.addEventListener('click', () => {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
        
        // 监听滚动事件，控制回到顶部按钮显示
        window.addEventListener('scroll', handleScroll);
    }
    
    // 处理滚动事件
    function handleScroll() {
        const backToTopBtn = document.getElementById('back-to-top-btn');
        if (backToTopBtn) {
            if (window.scrollY > 300) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        }
    }
    
    // 加载成就数据
    function loadAchievements() {
        fetch('/api/auth/status')
            .then(r => r.json())
            .then(authData => {
                if (authData.logged_in) {
                    userPointsEl.textContent = authData.user_id ? getTotalScore() : 0;
                    
                    fetch('/api/achievements')
                        .then(r => r.json())
                        .then(data => {
                            unlockedAchievements = data.unlocked;
                            const locked = data.locked;
                            
                            // 合并所有成就
                            allAchievements = [...unlockedAchievements, ...locked];
                            
                            // 更新概览
                            updateOverview(data);
                            
                            // 渲染成就
                            renderAchievements(unlockedAchievements, locked);
                        })
                        .catch(error => {
                            console.error('加载成就失败:', error);
                            unlockedGrid.innerHTML = '<p class="info-text">加载失败，请刷新页面</p>';
                        });
                }
            });
    }
    
    // 更新概览数据
    function updateOverview(data) {
        totalScoreEl.textContent = getTotalScore();
        updateCategoryCounts();
    }
    
    // 更新当前分类下的成就数量
    function updateCategoryCounts() {
        const unlocked = allAchievements.filter(a => isUnlocked(a));
        const locked = allAchievements.filter(a => !isUnlocked(a));
        
        const filteredUnlocked = filterByCategory(unlocked);
        const filteredLocked = filterByCategory(locked);
        
        unlockedCountEl.textContent = filteredUnlocked.length;
        
        // 计算当前分类下的总成就数
        const totalInCategory = filterByCategory(allAchievements).length;
        if (totalInCategory > 0) {
            progressPercentEl.textContent = Math.round((filteredUnlocked.length / totalInCategory) * 100);
        } else {
            progressPercentEl.textContent = 0;
        }
        
        unlockedBadge.textContent = filteredUnlocked.length;
        lockedBadge.textContent = filteredLocked.length;
    }
    
    // 获取总积分
    function getTotalScore() {
        fetch('/api/quiz/stats')
            .then(r => r.json())
            .then(stats => {
                const quizScore = stats.total_score_from_quiz || 0;
                const achievementPoints = unlockedAchievements.reduce((sum, a) => sum + a.points, 0);
                totalScoreEl.textContent = quizScore + achievementPoints;
            })
            .catch(error => console.error('加载积分失败:', error));
        return userPointsEl.textContent || 0;
    }
    
    // 渲染成就
    function renderAchievements(unlocked, locked) {
        renderUnlockedAchievements(unlocked);
        renderLockedAchievements(locked);
    }
    
    // 渲染已解锁成就
    function renderUnlockedAchievements(achievements) {
        unlockedGrid.innerHTML = '';
        
        if (achievements.length === 0) {
            unlockedGrid.innerHTML = '<p class="info-text">还没有解锁成就，快去答题吧！</p>';
            return;
        }
        
        const filtered = filterByCategory(achievements);
        
        filtered.forEach(achievement => {
            const card = createAchievementCard(achievement, true);
            unlockedGrid.appendChild(card);
        });
    }
    
    // 渲染未解锁成就
    function renderLockedAchievements(achievements) {
        lockedGrid.innerHTML = '';
        
        const filtered = filterByCategory(achievements);
        
        filtered.forEach(achievement => {
            const card = createAchievementCard(achievement, false);
            lockedGrid.appendChild(card);
        });
    }
    
    // 按类别筛选
    function filterByCategory(achievements) {
        if (currentCategory === 'all') {
            return achievements;
        }
        return achievements.filter(a => a.category === currentCategory);
    }
    
    // 筛选成就
    function filterAchievements() {
        const unlocked = allAchievements.filter(isUnlocked);
        const locked = allAchievements.filter(a => !isUnlocked(a));
        
        renderUnlockedAchievements(unlocked);
        renderLockedAchievements(locked);
        
        // 更新分类数量显示
        updateCategoryCounts();
    }
    
    // 判断是否已解锁
    function isUnlocked(achievement) {
        return unlockedAchievements.some(u => u.id === achievement.id);
    }
    
    // 创建成就卡片
    function createAchievementCard(achievement, isUnlocked) {
        const card = document.createElement('div');
        card.className = `achievement-card ${isUnlocked ? 'unlocked' : 'locked'}`;
        card.dataset.id = achievement.id;
        
        const categoryText = getCategoryText(achievement.category);
        
        card.innerHTML = `
            <div class="achievement-icon-wrapper">
                <span class="achievement-icon">${achievement.icon}</span>
            </div>
            <h3 class="achievement-name">${achievement.name}</h3>
            <p class="achievement-description">${achievement.description}</p>
            <span class="achievement-category">${categoryText}</span>
        `;
        
        card.addEventListener('click', () => showAchievementDetail(achievement));
        
        return card;
    }
    
    // 显示成就详情
    function showAchievementDetail(achievement) {
        detailIcon.textContent = achievement.icon;
        detailName.textContent = achievement.name;
        detailCategory.textContent = getCategoryText(achievement.category);
        detailDescription.textContent = achievement.description;
        detailCondition.textContent = getConditionText(achievement);
        detailPoints.textContent = achievement.points;
        
        detailOverlay.classList.remove('hidden');
    }
    
    // 关闭详情弹窗
    function closeDetailModal() {
        detailOverlay.classList.add('hidden');
    }
    
    // 获取类别文本
    function getCategoryText(category) {
        const categoryMap = {
            'quiz': '🎯 答题',
            'song': '🎵 收藏',
            'learn': '📖 浏览',
            'create': '✨ 创作',
            'chat': '📚 对话',
            'forum': '💬 论坛',
            'total': '🌟 综合'
        };
        return categoryMap[category] || category;
    }
    
    // 获取条件文本
    function getConditionText(achievement) {
        const conditionMap = {
            'quiz_correct': `答对 ${achievement.condition_value} 道题目`,
            'quiz_streak': `连续答对 ${achievement.condition_value} 道题目`,
            'learn_articles': `浏览 ${achievement.condition_value} 篇AI红歌微课文章`,
            'create_songs': `创作 ${achievement.condition_value} 首红歌`,
            'chat_messages': `与红歌专家对话 ${achievement.condition_value} 次`,
            'total_score': `累计获得 ${achievement.condition_value} 积分`,
            'favorite_songs': `收藏 ${achievement.condition_value} 首红歌`,
            'forum_posts': `发表 ${achievement.condition_value} 条论坛留言`,
            'achievement_count': `解锁 ${achievement.condition_value} 个成就`
        };
        return conditionMap[achievement.condition_type] || '满足特定条件';
    }
    
    // 加载排行榜（总积分排行榜）
    function loadLeaderboard() {
        fetch('/api/leaderboard?limit=10')
            .then(r => r.json())
            .then(data => {
                leaderboardList.innerHTML = '';
                data.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'leaderboard-item';
                    
                    // 排名
                    const rankSpan = document.createElement('span');
                    rankSpan.className = 'leaderboard-rank';
                    rankSpan.textContent = item.rank;
                    div.appendChild(rankSpan);
                    
                    // 用户名（支持展开/收起）
                    const usernameSpan = document.createElement('span');
                    usernameSpan.className = 'leaderboard-username';
                    usernameSpan.textContent = item.username;
                    usernameSpan.title = item.username;
                    
                    // 点击展开/收起功能
                    usernameSpan.addEventListener('click', function(e) {
                        e.stopPropagation();
                        this.classList.toggle('expanded');
                    });
                    
                    div.appendChild(usernameSpan);
                    
                    // 总积分
                    const pointsSpan = document.createElement('span');
                    pointsSpan.className = 'leaderboard-points';
                    pointsSpan.textContent = item.total_score + ' 分';
                    div.appendChild(pointsSpan);
                    
                    // 成就数
                    const achievementsSpan = document.createElement('span');
                    achievementsSpan.className = 'leaderboard-achievements';
                    achievementsSpan.textContent = '🏅 ' + (item.achievement_count || 0);
                    div.appendChild(achievementsSpan);
                    
                    leaderboardList.appendChild(div);
                });
            })
            .catch(error => console.error('加载排行榜失败:', error));
    }
    
    // AI Guide 逻辑
    const guideMascot = document.getElementById('ai-guide-mascot');
    const guideModal = document.getElementById('ai-guide-modal');
    const guideClose = document.getElementById('guide-close');
    const guideMessages = document.getElementById('guide-messages');
    const guideInput = document.getElementById('guide-input');
    const guideSend = document.getElementById('guide-send');
    
    // 添加CSS
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = `
        .spinner-small { 
            width: 1rem; height: 1rem; 
            border: 2px solid currentColor; 
            border-top-color: transparent; 
            border-radius: 50%; 
            animation: spin 1s linear infinite; 
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .info-text { 
            text-align: center; 
            color: #999; 
            padding: 2rem; 
            font-size: 1rem; 
        }
    `;
    document.head.appendChild(styleSheet);
    
    function addGuideMessage(text, isUser = false, isMarkdown = false) {
        const msg = document.createElement('div');
        msg.className = 'guide-message';
        
        if (isUser) {
            msg.innerHTML = `<p style="text-align: right; font-style: italic; color: #666;">我：${text}</p>`;
        } else {
            msg.className += ' guide-response';
            const contentDiv = document.createElement('div');
            if (isMarkdown && typeof marked !== 'undefined') {
                contentDiv.innerHTML = marked.parse(text);
            } else {
                contentDiv.innerHTML = `<p>${text}</p>`;
            }
            msg.appendChild(contentDiv);
        }
        
        guideMessages.appendChild(msg);
        guideMessages.scrollTop = guideMessages.scrollHeight;
        return msg;
    }
    
    function handleGuideCommand(query) {
        if (!query) return;
        guideInput.value = '';
        guideSend.disabled = true;
        
        addGuideMessage(query, true);
        
        const thinkingMsg = addGuideMessage("红小韵正在分析...", false);
        thinkingMsg.innerHTML = `<p><div class="spinner-small" style="width:1rem; height:1rem; border-color:#fee2e2; border-top-color:var(--theme-red); margin: 0 0.5rem; display: inline-block;"></div> 红小韵正在分析...</p>`;
        
        fetch('/api/guide/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            thinkingMsg.remove();
            
            // 自定义响应
            if (query.includes('快速解锁') || query.includes('怎么')) {
                addGuideMessage('💡 解锁成就的最佳方式：\n\n1. **多答题**：答对每题都能获得10-30积分\n2. **勤收藏**：收藏红歌也是加分项\n3. **论坛互动**：发表有意义的讨论\n4. **连续答题**：一次性答对更多题目效率更高\n\n加油！相信自己一定可以解锁全部成就！', false, true);
            } else if (query.includes('进度') || query.includes('多少分')) {
                const unlocked = unlockedAchievements.length;
                const total = allAchievements.length;
                const percent = Math.round((unlocked / total) * 100);
                const nextAchievement = findNextAchievement();
                let message = `📊 **您的成就进度**：\n\n已解锁：${unlocked}/${total} (${percent}%)\n\n`;
                if (nextAchievement) {
                    message += `🎯 下一个成就：**${nextAchievement.name}**\n${nextAchievement.description}\n`;
                    message += `还需要：${getNextSteps(nextAchievement)}\n`;
                } else {
                    message += `🎉 恭喜您已经解锁所有成就！`;
                }
                addGuideMessage(message, false, true);
            } else if (data.action === 'navigate') {
                const introText = data.intro_message || `好的，为您跳转到：**${data.label}**`;
                addGuideMessage(introText, false, true);
                const actionLink = document.createElement('a');
                actionLink.className = 'guide-action-link';
                actionLink.href = data.path;
                actionLink.textContent = `👉 点击前往 ${data.label.replace('前往', '').replace('开始', '').replace('进入', '').replace('查看', '')}`;
                
                const linkMsg = document.createElement('div');
                linkMsg.className = 'guide-message';
                linkMsg.appendChild(actionLink);
                guideMessages.appendChild(linkMsg);
            } else if (data.action === 'text_response') {
                addGuideMessage(data.message, false, true);
            } else {
                addGuideMessage("抱歉，我没听懂您的指令。", false);
            }
        })
        .catch(error => {
            console.error("AI Guide Error:", error);
            thinkingMsg.remove();
            addGuideMessage("红小韵好像断线了，请稍后再试。", false);
        })
        .finally(() => {
            guideSend.disabled = false;
            guideMessages.scrollTop = guideMessages.scrollHeight;
        });
    }
    
    // 找到下一个可解锁的成就
    function findNextAchievement() {
        for (const achievement of allAchievements) {
            if (!isUnlocked(achievement)) {
                return achievement;
            }
        }
        return null;
    }
    
    // 获取解锁下一个成就需要的步骤
    function getNextSteps(achievement) {
        const conditionMap = {
            'quiz_correct': `${achievement.condition_value} 道正确答题`,
            'learn_articles': `${achievement.condition_value} 篇微课文章浏览`,
            'create_songs': `${achievement.condition_value} 首歌曲创作`,
            'total_score': `${achievement.condition_value} 积分`,
            'favorite_songs': `${achievement.condition_value} 首收藏`,
            'forum_posts': `${achievement.condition_value} 条留言`,
            'achievement_count': `${achievement.condition_value} 个成就`
        };
        return conditionMap[achievement.condition_type] || '更多努力';
    }
    
    guideMascot.addEventListener('click', () => { 
        guideModal.classList.toggle('hidden'); 
        if (!guideModal.classList.contains('hidden')) { 
            guideMessages.scrollTop = guideMessages.scrollHeight; 
            guideInput.focus(); 
        } 
    });
    
    guideClose.addEventListener('click', () => guideModal.classList.add('hidden'));
    
    document.querySelectorAll('.guide-question-button').forEach(button => { 
        button.addEventListener('click', (e) => handleGuideCommand(e.target.dataset.command)); 
    });
    
    guideSend.addEventListener('click', () => handleGuideCommand(guideInput.value.trim()));
    
    guideInput.addEventListener('keypress', (e) => { 
        if (e.key === 'Enter') handleGuideCommand(guideInput.value.trim()); 
    });
    
    // 启动
    init();
});