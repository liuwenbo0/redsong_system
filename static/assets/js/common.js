/**
 * 全站通用脚本 (common.js)
 * 负责处理页面间的平滑过渡效果。
 */

function checkAuthStatus() {
    // 更新：使用绝对路径
    fetch('/api/auth/status')
        .then(response => {
            if (!response.ok) { return { logged_in: false }; }
            return response.json();
        })
        .then(data => {
            const authContainer = document.getElementById('auth-container');
            if (!authContainer) return;

            if (data.logged_in) {
                // 如果已登录，显示欢迎信息和登出按钮
                authContainer.innerHTML = `
                    <span class="nav-user-info">欢迎, ${data.username}</span>
                    <a href="#" id="logout-button" class="nav-logout-button">登出</a>
                `;
                
                const logoutButton = document.getElementById('logout-button');
                if (logoutButton) {
                    logoutButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        // 更新：使用绝对路径
                        fetch(window.location.origin + '/api/auth/logout')
                            .then(() => {
                                window.location.href = '/'; 
                            });
                    });
                }
            } else {
                // 游客模式下的用户名
                if (sessionStorage.getItem('visitorModeActive') === 'true') {
                    const visitorName = sessionStorage.getItem('visitorName') || '游客_0000';
                    
                    authContainer.innerHTML = `
                        <span class="nav-user-info">欢迎, ${visitorName}</span>
                        <a href="#" id="auth-modal-open" class="nav-login-link">登录</a>
                    `;
                } else {
                    // 如果未登录，且不是游客模式，才显示登录图标
                    authContainer.innerHTML = `
                        <button id="auth-modal-open" class="nav-login-button" title="登录/注册">
                            <svg class="nav-login-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                        </button>
                    `;
                }
                // 如果未登录，显示登录/注册按钮
                
            }
        })
        .catch(err => {
            console.error("无法获取认证状态:", err);
            const authContainer = document.getElementById('auth-container');
            if (authContainer) {
                authContainer.innerHTML = `<span class="nav-user-info" style="color:red;">状态加载失败</span>`;
            }
        });
}

window.addEventListener('DOMContentLoaded', () => {
    
    const pageContent = document.getElementById('page-content');
    const pageLoader = document.getElementById('page-loader');
    
    checkAuthStatus();
    // --- 页面淡入逻辑 ---
    // 确保内容元素存在
    if (pageContent) {
        // 使用 requestAnimationFrame 确保在下一帧应用 'is-loaded' 类，从而触发CSS过渡
        requestAnimationFrame(() => {
            pageContent.classList.add('is-loaded');
        });
    }

    // --- 页面淡出逻辑 ---
    // 选取所有内部链接 (以'/'开头，但不包含'#'开头的锚点链接)
    const internalLinks = document.querySelectorAll('a[href^="/"]:not([href*="#"])');

    internalLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            // // (新增) 确保收藏夹链接在未登录时不触发淡出（因为它会被JS拦截）
            // if (this.getAttribute('href') === '/favorites' && !document.getElementById('logout-button')) {
            //     // 触发登录弹窗
            //     document.getElementById('auth-modal-open')?.click();
            //     event.preventDefault();
            //     return;
            // }
            // 阻止默认的立即跳转行为
            console.log("事件绑定成功：点击到了 link 元素");
            event.preventDefault();
            
            const destinationUrl = this.href;
            // const destinationPath = this.getAttribute('href');
            const destinationPath = new URL(this.href).pathname;
            console.error("目的页面是：", destinationPath);
            // (更新) 确保登出按钮不会触发页面淡出
            if(this.id === 'logout-button') {
                return;
            }

            // (新增) 检查是否是受保护的链接，并且用户未登录
            const protectedLinks = ['/favorites', '/making', '/creation'];
            // 通过检查是否存在 'logout-button' 来判断是否登录
            const isLoggedIn = !!document.getElementById('logout-button'); 
            const isVisitor = sessionStorage.getItem('visitorModeActive') === 'true';

            if (protectedLinks.includes(destinationPath) && !isLoggedIn) {
                // 在弹出弹窗前，用 sessionStorage 记住用户想去的页面
                // 规则：如果是游客，且要去的是 making 或 creation，则允许通过
                const isAllowedVisitorPage = (destinationPath === '/making' || destinationPath === '/creation');
                
                if (isVisitor && isAllowedVisitorPage) {
                    // -> 游客访问允许的页面：放行，不执行下面的拦截代码，直接向下执行淡出跳转
                    console.log("游客身份，允许访问:", destinationPath);
                } else {
                    sessionStorage.setItem('pendingDestination', destinationPath);
                    // --- 触发登录弹窗 ---
                    const authModal = document.getElementById('auth-modal-overlay');
                    const loginForm = document.getElementById('login-form');
                    const registerForm = document.getElementById('register-form');
                    const loginError = document.getElementById('login-error');

                    if (authModal) {
                        authModal.classList.remove('hidden');
                        if (loginForm) loginForm.classList.remove('hidden');
                        if (registerForm) registerForm.classList.add('hidden');
                        
                        // 重置表单并显示提示
                        if (loginError) {
                            // 针对游客访问收藏夹给出一个更准确的提示，或者保持通用提示
                            if (isVisitor && destinationPath === '/favorites') {
                                loginError.textContent = "收藏夹功能需要正式登录账号。";
                            } else {
                                loginError.textContent = "请先登录才能访问此页面。";
                            }
                            loginError.classList.remove('hidden');
                        }
                        if (document.getElementById('login-username')) document.getElementById('login-username').value = '';
                        if (document.getElementById('login-password')) document.getElementById('login-password').value = '';
                    }
                    // event.preventDefault();
                    return; // 停止执行，不进行页面跳转
                }
            }

            // 确保加载器和内容元素都存在
            if (pageLoader && pageContent) {
                // 1. 显示加载器
                pageLoader.classList.add('is-visible');
                
                // 2. 淡出当前页面内容
                pageContent.classList.add('page-fade-out');
                
                // 3. 在淡出动画结束后 (约300毫秒) 再进行页面跳转
                setTimeout(() => {
                    window.location.href = destinationUrl;
                }, 300);
            } else {
                // 如果关键元素不存在，则直接跳转
                window.location.href = destinationUrl;
            }
        });
    });

});
