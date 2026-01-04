// ==================== 答题页面逻辑 ====================

document.addEventListener('DOMContentLoaded', function() {
    // DOM 元素
    const startScreen = document.getElementById('start-screen');
    const questionScreen = document.getElementById('question-screen');
    const resultScreen = document.getElementById('result-screen');
    
    const startQuizBtn = document.getElementById('start-quiz-btn');
    const nextQuestionBtn = document.getElementById('next-question-btn');
    const restartQuizBtn = document.getElementById('restart-quiz-btn');
    const backHomeBtn = document.getElementById('back-home-btn');
    
    const questionNumber = document.getElementById('question-number');
    const questionDifficulty = document.getElementById('question-difficulty');
    const questionPoints = document.getElementById('question-points');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    
    const totalCorrectEl = document.getElementById('total-correct');
    const accuracyEl = document.getElementById('accuracy');
    const quizScoreEl = document.getElementById('quiz-score');
    const userPointsEl = document.getElementById('user-points');
    
    const resultIcon = document.getElementById('result-icon');
    const resultTitle = document.getElementById('result-title');
    const resultCorrect = document.getElementById('result-correct');
    const resultTotal = document.getElementById('result-total');
    const resultPoints = document.getElementById('result-points');
    
    const achievementModal = document.getElementById('achievement-modal-overlay');
    const achievementIcon = document.getElementById('achievement-icon');
    const achievementName = document.getElementById('achievement-name');
    const achievementDesc = document.getElementById('achievement-desc');
    const achievementPoints = document.getElementById('achievement-points');
    const achievementCloseBtn = document.getElementById('achievement-close-btn');
    
    const leaderboardList = document.getElementById('leaderboard-list');
    
    // 游戏状态
    let questions = [];
    let currentQuestionIndex = 0;
    let correctCount = 0;
    let totalScore = 0;
    let currentQuestionPoints = 0;
    
    // 初始化
    function init() {
        loadUserStats();
        loadLeaderboard();
        bindEvents();
    }
    
    // 绑定事件
    function bindEvents() {
        startQuizBtn.addEventListener('click', startQuiz);
        nextQuestionBtn.addEventListener('click', nextQuestion);
        restartQuizBtn.addEventListener('click', restartQuiz);
        backHomeBtn.addEventListener('click', () => window.location.href = '/');
        achievementCloseBtn.addEventListener('click', closeAchievementModal);
    }
    
    // 加载用户统计
    function loadUserStats() {
        fetch('/api/auth/status')
            .then(r => r.json())
            .then(data => {
                if (data.logged_in) {
                    fetch('/api/quiz/stats')
                        .then(r => r.json())
                        .then(stats => {
                            totalCorrectEl.textContent = stats.total_correct;
                            accuracyEl.textContent = stats.accuracy + '%';
                            quizScoreEl.textContent = stats.total_score_from_quiz;
                            userPointsEl.textContent = data.user_id ? getTotalScore(data.username) : 0;
                        });
                }
            })
            .catch(error => console.error('加载用户统计失败:', error));
    }
    
    // 开始答题
    function startQuiz() {
        fetch('/api/quiz/questions?count=5')
            .then(r => r.json())
            .then(data => {
                questions = data.questions;
                if (questions.length === 0) {
                    alert('暂无题目，请稍后再试');
                    return;
                }
                
                currentQuestionIndex = 0;
                correctCount = 0;
                totalScore = 0;
                
                showQuestion();
            })
            .catch(error => {
                console.error('加载题目失败:', error);
                alert('加载题目失败，请稍后再试');
            });
    }
    
    // 显示当前题目
    function showQuestion() {
        const question = questions[currentQuestionIndex];
        
        questionNumber.textContent = `${currentQuestionIndex + 1}/${questions.length}`;
        questionDifficulty.textContent = getDifficultyText(question.difficulty);
        questionDifficulty.dataset.difficulty = question.difficulty;
        questionPoints.textContent = `+${question.points}分`;
        questionText.textContent = question.question;
        
        // 生成选项
        optionsContainer.innerHTML = '';
        const options = [question.option_a, question.option_b, question.option_c, question.option_d];
        options.forEach((option, index) => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerHTML = `<span class="option-label">${['A', 'B', 'C', 'D'][index]}</span> ${option}`;
            btn.addEventListener('click', () => handleAnswer(index, btn));
            optionsContainer.appendChild(btn);
        });
        
        // 切换屏幕
        startScreen.classList.add('hidden');
        resultScreen.classList.add('hidden');
        questionScreen.classList.remove('hidden');
        nextQuestionBtn.classList.add('hidden');
    }
    
    // 处理答题
    function handleAnswer(selectedIndex, btn) {
        const question = questions[currentQuestionIndex];
        const correctIndex = ['A', 'B', 'C', 'D'][selectedIndex];
        
        // 禁用所有选项
        const allButtons = optionsContainer.querySelectorAll('.option-btn');
        allButtons.forEach(button => button.disabled = true);
        
        // 提交答案
        fetch('/api/quiz/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_id: question.id,
                answer: correctIndex
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // 显示正确/错误
                allButtons.forEach((button, index) => {
                    const thisAnswer = ['A', 'B', 'C', 'D'][index];
                    if (thisAnswer === data.correct_answer) {
                        button.classList.add('correct');
                    } else if (index === selectedIndex && !data.is_correct) {
                        button.classList.add('wrong');
                    }
                });
                
                // 更新分数并显示加分动画
                if (data.is_correct) {
                    correctCount++;
                    totalScore += data.score_earned;
                    showPointsAnimation(btn, data.score_earned);
                    updateQuizScore(data.score_earned);
                }
                
                // 检查并显示成就解锁通知
                if (data.newly_unlocked && data.newly_unlocked.length > 0) {
                    console.log('quiz页面解锁新成就:', data.newly_unlocked[0]);
                    loadUserStats(); // 更新积分显示
                    setTimeout(() => showAchievementNotification(data.newly_unlocked[0]), 500);
                }
                
                // 显示下一题按钮
                nextQuestionBtn.classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('提交答案失败:', error);
            btn.disabled = false;
        });
    }
    
    // 显示加分动画
    function showPointsAnimation(element, points) {
        const rect = element.getBoundingClientRect();
        const floatEl = document.createElement('div');
        floatEl.className = 'float-points';
        floatEl.textContent = `+${points}`;
        floatEl.style.cssText = `
            position: fixed;
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top}px;
            color: #ffd700;
            font-size: 2rem;
            font-weight: 700;
            pointer-events: none;
            z-index: 9999;
            animation: floatUp 1s ease-out forwards;
        `;
        document.body.appendChild(floatEl);
        
        // 动画结束后移除元素
        setTimeout(() => {
            floatEl.remove();
        }, 1000);
    }
    
    // 更新答题积分显示
    function updateQuizScore(pointsToAdd) {
        const currentScore = parseInt(quizScoreEl.textContent) || 0;
        const newScore = currentScore + pointsToAdd;
        
        // 数字滚动动画
        const duration = 500;
        const startTime = performance.now();
        const startValue = currentScore;
        
        function animateScore(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // ease-out
            
            const currentValue = Math.round(startValue + (newScore - startValue) * easeProgress);
            quizScoreEl.textContent = currentValue;
            
            if (progress < 1) {
                requestAnimationFrame(animateScore);
            }
        }
        
        requestAnimationFrame(animateScore);
    }
    
    // 下一题
    function nextQuestion() {
        currentQuestionIndex++;
        
        if (currentQuestionIndex >= questions.length) {
            showResults();
        } else {
            showQuestion();
        }
    }
    
    // 显示结果
    function showResults() {
        questionScreen.classList.add('hidden');
        resultScreen.classList.remove('hidden');
        
        resultCorrect.textContent = correctCount;
        resultTotal.textContent = questions.length;
        resultPoints.textContent = totalScore;
        
        // 根据成绩显示不同的图标和标题
        const accuracy = correctCount / questions.length;
        if (accuracy === 1) {
            resultIcon.textContent = '🏆';
            resultTitle.textContent = '完美表现！';
        } else if (accuracy >= 0.8) {
            resultIcon.textContent = '🎉';
            resultTitle.textContent = '太棒了！';
        } else if (accuracy >= 0.6) {
            resultIcon.textContent = '👍';
            resultTitle.textContent = '继续加油！';
        } else {
            resultIcon.textContent = '💪';
            resultTitle.textContent = '再接再厉！';
        }
        
        // 刷新统计
        loadUserStats();
    }
    
    // 重新开始
    function restartQuiz() {
        resultScreen.classList.add('hidden');
        startQuiz();
    }
    
    // 显示成就解锁通知（浮动通知）
    function showAchievementNotification(achievement) {
        console.log('显示成就通知:', achievement);
        
        // 检查是否已存在通知，避免重复
        const existingNotification = document.querySelector('.achievement-notification');
        if (existingNotification) {
            console.log('已存在成就通知，移除旧通知');
            existingNotification.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = 'achievement-notification';
        notification.style.zIndex = '99999';
        notification.innerHTML = `
            <div class="achievement-notification-content">
                <span class="achievement-notification-icon">${achievement.icon}</span>
                <div class="achievement-notification-text">
                    <span class="achievement-notification-title">成就解锁！</span>
                    <span class="achievement-notification-name">${achievement.name}</span>
                </div>
            </div>
        `;
        document.body.appendChild(notification);
        console.log('成就通知已添加到 DOM, 元素:', notification);
        console.log('通知位置:', notification.getBoundingClientRect());
        
        // 3秒后自动消失
        setTimeout(() => {
            notification.classList.add('achievement-notification-hide');
            setTimeout(() => {
                notification.remove();
                console.log('成就通知已从 DOM 中移除');
            }, 300);
        }, 3000);
    }
    
    // 检查新成就
    function checkNewAchievements() {
        fetch('/api/achievements/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(r => r.json())
        .then(data => {
            console.log('quiz页面成就检查响应:', data);
            if (data.success && data.newly_unlocked && data.newly_unlocked.length > 0) {
                console.log('quiz页面解锁新成就:', data.newly_unlocked[0]);
                // 更新积分显示
                loadUserStats();
                // 显示成就解锁通知（使用浮动通知）
                setTimeout(() => showAchievementNotification(data.newly_unlocked[0]), 500);
            } else {
                console.log('quiz页面没有新成就解锁');
            }
        })
        .catch(error => console.error('quiz页面检查成就失败:', error));
    }
    
    // 显示成就弹窗
    function showAchievementModal(achievement) {
        console.log('显示成就弹窗:', achievement); // 调试日志
        console.log('弹窗元素存在性:', {
            modal: !!achievementModal,
            icon: !!achievementIcon,
            name: !!achievementName,
            desc: !!achievementDesc,
            points: !!achievementPoints
        }); // 调试日志
        
        // 确认所有元素都存在
        if (!achievementModal || !achievementIcon || !achievementName || !achievementDesc || !achievementPoints) {
            console.error('成就弹窗元素未找到！');
            return;
        }
        
        achievementIcon.textContent = achievement.icon;
        achievementName.textContent = achievement.name;
        achievementDesc.textContent = achievement.description;
        achievementPoints.textContent = achievement.points;
        
        achievementModal.classList.remove('hidden');
        console.log('弹窗已显示'); // 调试日志
    }
    
    // 关闭成就弹窗
    function closeAchievementModal() {
        achievementModal.classList.add('hidden');
    }
    
    // 获取难度文本
    function getDifficultyText(difficulty) {
        const difficultyMap = {
            'easy': '简单',
            'medium': '中等',
            'hard': '困难'
        };
        return difficultyMap[difficulty] || difficulty;
    }
    
    // 加载排行榜（答题积分排行榜）
    function loadLeaderboard() {
        fetch('/api/quiz/leaderboard?limit=10')
            .then(r => r.json())
            .then(data => {
                leaderboardList.innerHTML = '';
                data.forEach(item => {
                    // 创建完整的排行榜样式
                    const div = document.createElement('div');
                    div.className = 'leaderboard-item';
                    
                    // 排名
                    const rankSpan = document.createElement('span');
                    rankSpan.className = 'leaderboard-rank';
                    rankSpan.textContent = item.rank;
                    div.appendChild(rankSpan);
                    
                    // 用户名
                    const usernameSpan = document.createElement('span');
                    usernameSpan.className = 'leaderboard-username';
                    usernameSpan.textContent = item.username;
                    usernameSpan.title = item.username; // 鼠标悬停显示完整名字
                    
                    // 点击展开/收起用户名
                    usernameSpan.addEventListener('click', function(e) {
                        e.stopPropagation(); // 阻止事件冒泡
                        this.classList.toggle('expanded');
                    });
                    
                    div.appendChild(usernameSpan);
                    
                    // 答题积分（显示答题积分而非总积分）
                    const pointsSpan = document.createElement('span');
                    pointsSpan.className = 'leaderboard-points';
                    pointsSpan.textContent = item.quiz_score + ' 分';
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
    
    // 增加CSS
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
        
        const thinkingMsg = addGuideMessage("红小韵正在回答...", false);
        thinkingMsg.innerHTML = `<p><div class="spinner-small" style="width:1rem; height:1rem; border-color:#fee2e2; border-top-color:var(--theme-red); margin: 0 0.5rem; display: inline-block;"></div> 红小韵正在回答...</p>`;
        
        fetch('/api/guide/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            thinkingMsg.remove();
            
            // 自定义响应
            if (query.includes('积分')) {
                addGuideMessage('💡 您可以通过以下方式获取积分：\n1. 答题：答对每道可获得10-30分\n2. 收藏红歌首次收藏获得30分\n3. 发表论坛留言首次获得40分\n4. 解锁成就：每解锁一个成就可获得额外积分！', false, true);
            } else if (query.includes('成就')) {
                addGuideMessage('🏅 目前有以下成就可以解锁：\n\n🎯 **答题类**：\n- 初学乍练（答对第1题）\n- 渐入佳境（答对10题）\n- 红歌专家（答对50题）\n\n🎵 **收藏类**：\n- 初露锋芒（收藏1首红歌）\n- 收藏家（收藏10首红歌）\n\n💬 **论坛类**：\n- 初声发问（发表第1条留言）\n- 社区活跃（发表5条留言）\n\n继续努力，解锁更多成就吧！', false, true);
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

// 辅助函数：获取总积分（需要从当前用户获取）
function getTotalScore(username) {
    // 实际应用中应该从用户数据获取
    // 这里返回一个占位值，实际会从 /api/quiz/stats 和成就获取
    return document.getElementById('quiz-score').textContent || 0;
}