/**
 * 全站认证弹窗脚本 (common_auth.js)
 * 负责处理登录/注册弹窗的所有交互。
 * (版本: 已修复重复监听器 + 改用 sessionStorage 实现不保留游客状态)
 */
document.addEventListener('DOMContentLoaded', () => {
    // 弹窗元素
    const authModalOverlay = document.getElementById('auth-modal-overlay');
    const authModalClose = document.getElementById('auth-modal-close');
    
    // 表单切换链接
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    
    // 表单
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    // 登录元素
    const loginError = document.getElementById('login-error');
    const loginUsername = document.getElementById('login-username');
    const loginPassword = document.getElementById('login-password');
    const loginSubmit = document.getElementById('login-submit');
    
    // 注册元素
    const registerError = document.getElementById('register-error');
    const registerUsername = document.getElementById('register-username');
    const registerPassword = document.getElementById('register-password');
    const registerConfirmPassword = document.getElementById('register-confirm-password'); 
    const registerSubmit = document.getElementById('register-submit');

    // 游客模式按钮
    const visitorModeButton = document.getElementById('visitor-mode-button');

    // 1. 打开弹窗
    document.body.addEventListener('click', (e) => {
        const openButton = e.target.closest('#auth-modal-open');
        if (openButton) {
            if (authModalOverlay) {
                authModalOverlay.classList.remove('hidden');
                loginForm.classList.remove('hidden');
                registerForm.classList.add('hidden');
                resetForms();
            }
        }
    });

    // 2. 关闭弹窗
    if (authModalClose) {
        authModalClose.addEventListener('click', () => {
            authModalOverlay.classList.add('hidden');
            resetForms();
            sessionStorage.removeItem('pendingDestination'); 
        });
    }
    if (authModalOverlay) {
        authModalOverlay.addEventListener('click', (e) => {
            if (e.target === authModalOverlay) {
                authModalOverlay.classList.add('hidden');
                resetForms();
                sessionStorage.removeItem('pendingDestination'); 
            }
        });
    }

    // 3. 切换到注册表单
    if (showRegisterLink) {
        showRegisterLink.addEventListener('click', (e) => {
            e.preventDefault();
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
            resetForms();
        });
    }

    // 4. 切换到登录表单
    if (showLoginLink) {
        showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            registerForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
            resetForms();
        });
    }
    
    // 5. 处理登录逻辑
    if (loginSubmit) {
        loginSubmit.addEventListener('click', (e) => {
            e.preventDefault(); 
            const username = loginUsername.value;
            const password = loginPassword.value;
            
            fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // (修改) 登录成功，清除 sessionStorage 中的游客状态
                    sessionStorage.removeItem('visitorModeActive');
                    sessionStorage.removeItem('visitorName');
                    sessionStorage.removeItem('pendingDestination');
                    
                    const destination = sessionStorage.getItem('pendingDestination'); // 其实上一行已经删了，这里应该取不到，逻辑上也没问题，因为登录成功通常刷新即可
                    // 如果你希望保留登录后跳转功能，上面的 removeItem('pendingDestination') 应该移到 if 块里
                    
                    window.location.reload();
                } else {
                    showError(loginError, data.error || '登录失败');
                }
            })
            .catch(() => showError(loginError, '网络错误，请稍后再试。'));
        });
    }
    
    // 6. 处理注册逻辑
    if (registerSubmit) {
        registerSubmit.addEventListener('click', (e) => {
            e.preventDefault(); 
            const username = registerUsername.value;
            const password = registerPassword.value;
            const confirmPassword = registerConfirmPassword.value; // (新增)

            // --- (新增) 前端验证 ---
            if (!username || !password || !confirmPassword) {
                showError(registerError, "所有字段都不能为空。");
                return;
            }
            
            if (username.length > 15) {
                showError(registerError, "用户名不能超过15个字符。");
                return;
            }

            if (password !== confirmPassword) {
                showError(registerError, "两次输入的密码不一致。");
                return;
            }

            // 密码：检查中文
            const hasChinese = /[\u4e00-\u9fa5]/.test(password);
            if (hasChinese) {
                showError(registerError, "密码不能包含中文字符。");
                return;
            }
            
            // 密码：必须有字母
            const hasLetter = /[a-zA-Z]/.test(password);
            if (!hasLetter) {
                showError(registerError, "密码必须包含至少一个字母。");
                return;
            }
            
            // 密码：必须有数字
            const hasNumber = /[0-9]/.test(password);
            if (!hasNumber) {
                showError(registerError, "密码必须包含至少一个数字。");
                return;
            }
            fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    username, 
                    password, 
                    confirm_password: confirmPassword // (更新) 发送确认密码
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // (修改) 注册成功，清除 sessionStorage 中的游客状态
                    sessionStorage.removeItem('visitorModeActive');
                    sessionStorage.removeItem('visitorName');
                    sessionStorage.removeItem('pendingDestination');
                    
                    window.location.reload();
                } else {
                    showError(registerError, data.error || '注册失败');
                }
            })
            .catch(() => showError(registerError, '网络错误，请稍后再试。'));
        });
    }
    
    // 7. 处理游客模式
    if (visitorModeButton) {
        visitorModeButton.addEventListener('click', (e) => {
            e.preventDefault(); 

            const destination = sessionStorage.getItem('pendingDestination');
            sessionStorage.removeItem('pendingDestination');

            if (destination === '/favorites') {
                alert('游客模式无法访问收藏夹，即将返回主页。');
                window.location.href = '/'; 

            } else if (destination === '/making' || destination === '/creation') {
                
                // (修改) 使用 sessionStorage 保存游客状态
                const visitorName = '游客_' + (Math.floor(Math.random() * 9000) + 1000);
                sessionStorage.setItem('visitorModeActive', 'true');
                sessionStorage.setItem('visitorName', visitorName);
                
                window.location.href = destination;

            } else {
                // (修改) 使用 sessionStorage 保存游客状态
                const visitorName = '游客_' + (Math.floor(Math.random() * 9000) + 1000);
                sessionStorage.setItem('visitorModeActive', 'true');
                sessionStorage.setItem('visitorName', visitorName);
                
                if (authModalOverlay) {
                    authModalOverlay.classList.add('hidden');
                    resetForms();
                    
                    if (typeof checkAuthStatus === 'function') {
                        checkAuthStatus();
                    }
                }
            }
        });
    }

    // --- 辅助函数 ---
    function showError(errorElement, message) {
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('hidden');
        }
    }
    
    function resetForms() {
        if (loginError) loginError.classList.add('hidden');
        if (registerError) registerError.classList.add('hidden');
        if (loginUsername) loginUsername.value = '';
        if (loginPassword) loginPassword.value = '';
        if (registerUsername) registerUsername.value = '';
        if (registerPassword) registerPassword.value = '';
        if (registerConfirmPassword) registerConfirmPassword.value = ''; 
    }
});