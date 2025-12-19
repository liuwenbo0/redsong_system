# coding=utf-8
import os
import time
import logging
from flask import Flask, jsonify, render_template, request,  send_from_directory
from flask_cors import CORS
# 导入登录管理
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from google import genai
import json # 引入json库
import logging
import requests
# 从 database.py 导入 db 对象、所有模型和注册命令的函数
from database import db, Song, Article, HistoricalEvent, ChatHistory, register_commands,DataService, User
import re # (新增) 导入正则表达式
from dotenv import load_dotenv

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# --- 加载环境变量 ---
load_dotenv()  # 从 .env 文件加载环境变量

# --- 获取项目根目录 ---
basedir = os.path.abspath(os.path.dirname(__file__))
SENSITIVE_WORDS = ["暴力", "色情", "赌博", "反动", "脏话", "违规"]
CACHE_DIR = os.path.join(basedir, 'temp_tasks')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ==============================================================================
# 1. 应用配置 (Configuration)
# ==============================================================================
class Config:
    # 基础配置
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'jf83h_sdf98f3h2983hf9834hf9834h')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "project.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API 密钥配置
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    KIE_API_KEY = os.getenv('KIE_API_KEY', '')
    
    # 生产环境配置
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

# ==============================================================================
# 2. 数据服务层 (Data Service)
# ==============================================================================
data_service = DataService()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login 用于从 session 中加载用户的回调"""
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """当 @login_required 失败时返回的 JSON 错误"""
    return jsonify({"error": "需要登录才能执行此操作。"}), 401

# ==============================================================================
# 3. 应用工厂函数 (Application Factory)
# ==============================================================================
def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
    CORS(app, supports_credentials=True) # supports_credentials=True 对 session 至关重要
    db.init_app(app)
    login_manager.init_app(app) # 初始化登录管理器
    register_routes(app)
    register_commands(app) # 注册来自 database.py 的命令行
    
    # 自动创建数据库表（在应用上下文中）
    with app.app_context():
        db.create_all()
        logger.info("数据库表已自动创建/检查")
    
    return app

# ==============================================================================
# 3. 核心工具函数 (OpenRouter API) - [新增与润色部分]
# ==============================================================================

def _call_openrouter_api(api_key, messages, response_format=None, system_instruction=None):
    """
    OpenRouter API 统一调用入口 (核心函数)。
    负责处理 HTTP 请求、API Key 校验、错误捕获和 JSON 模式。
    
    :param api_key: OpenRouter API Key
    :param messages: 消息列表 [{"role": "user", "content": "..."}]
    :param response_format: (可选) 强制返回格式，如 {"type": "json_object"}
    :param system_instruction: (可选) 系统提示词，会自动插入到消息列表头部
    """
    if not api_key or "YOUR_" in api_key:
        return {"error": "API Key 未配置或无效。"}

    # 构造请求 Payload
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "max_tokens": 4096
    }
    
    # 处理系统提示词
    if system_instruction:
        payload["messages"].append({"role": "system", "content": system_instruction})
    
    # 追加用户消息
    payload["messages"].extend(messages)

    # 处理响应格式 (强制 JSON)
    if response_format:
        payload["response_format"] = response_format

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8", 
                "HTTP-Referer": "https://redsong.bond", 
            },
            data=json.dumps(payload),
            timeout=30 # 设置超时，防止后端卡死
        )
        
        if response.status_code != 200:
            logger.error(f"OpenRouter Error {response.status_code}: {response.text}")
            if response.status_code == 401: return {"error": "API鉴权失败"}
            if response.status_code == 402: return {"error": "账户余额不足"}
            return {"error": f"API调用失败 ({response.status_code})"}
            
        return response.json()

    except Exception as e:
        logger.error(f"OpenRouter Exception: {e}")
        return {"error": f"请求异常: {str(e)}"}

def generate_openrouter_content(messages, api_key, system_instruction):
    """
    便捷包装函数：用于只需返回纯文本内容的场景 (如聊天、简单作词)。
    复用 _call_openrouter_api。
    """
    # 直接调用核心函数
    result = _call_openrouter_api(api_key, messages, system_instruction)
    
    if "error" in result:
        return f"API错误: {result['error']}"
    
    try:
        # 提取内容
        if result.get('choices') and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        return "API 返回了空内容。"
    except (KeyError, IndexError, TypeError):
        return "API 返回格式异常，无法解析。"



# ==============================================================================
# 4. 注册路由
# ==============================================================================
def register_routes(app):
    # --- 页面路由 ---
    @app.route('/')
    def index(): return render_template('index.html')
    @app.route('/circle')
    def circle_page(): return render_template('circle.html')
    @app.route('/favorites')
    @login_required # 收藏夹页面现在需要登录
    def favorites_page(): return render_template('favorites.html')
    @app.route('/making')
    # @login_required # 游客模式
    def making_page(): return render_template('making.html')
    @app.route('/plaza')
    def plaza_page(): return render_template('plaza.html')
    @app.route('/creation')
    # @login_required # 游客模式
    def creation_page(): return render_template('creation.html')
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory('static/images', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


    # --- (新增) 用户认证 API ---
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        confirm_password = data.get('confirm_password') # (新增) 获取确认密码

        # --- (新增) 详细的后端验证 ---
        if not username or not password or not confirm_password:
            return jsonify({"error": "所有字段都不能为空。"}), 400
        
        if len(username) > 15:
            return jsonify({"error": "用户名不能超过15个字符。"}), 400
            
        if password != confirm_password:
            return jsonify({"error": "两次输入的密码不一致。"}), 400

        # 密码：检查中文或非法字符
        if not re.match(r"^[a-zA-Z0-9!@#$%^&*()_+-=,./?;:'\"\[\]{}|<>~`]+$", password):
            return jsonify({"error": "密码不能包含中文或非法字符。"}), 400

        # 密码：必须有字母
        if not re.search(r"[a-zA-Z]", password):
            return jsonify({"error": "密码必须包含至少一个字母。"}), 400
            
        # 密码：必须有数字
        if not re.search(r"[0-9]", password):
            return jsonify({"error": "密码必须包含至少一个数字。"}), 400
        # --- 验证结束 ---
        
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "用户名已存在。"}), 400

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user) # 注册后自动登录
        return jsonify({"success": True, "username": new_user.username})

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True) # 登录用户，remember=True 保持会话
            return jsonify({"success": True, "username": user.username})
        
        return jsonify({"error": "用户名或密码无效。"}), 401

    @app.route('/api/auth/logout')
    @login_required
    def logout():
        logout_user() # 清除用户 session
        return jsonify({"success": True})

    @app.route('/api/auth/status')
    def auth_status():
        if current_user.is_authenticated:
            return jsonify({
                "logged_in": True, 
                "username": current_user.username,
                "user_id": current_user.id
            })
        else:
            return jsonify({"logged_in": False})
    # --- API 路由 ---
    @app.route('/api/song/chat', methods=['POST'])
    # @login_required # 保护
    def api_song_chat():
        question = request.json.get('question', '')
        api_key = app.config.get("OPENROUTER_API_KEY")

        if not question:
            return jsonify({"answer": "请输入您的问题。"}), 400
        
        # 检查 OpenRouter API Key 是否已配置
        if not api_key or api_key == "YOUR_OPENROUTER_API_KEY":
             return jsonify({"answer": "后端尚未配置有效的 OpenRouter API Key。"}), 500

        answer = generate_openrouter_content(
            [{"role": "user", "content": question}], 
            api_key,"你是一个红歌文化专家。请用中文、简洁并友好地回答以下问题。"
        )

        if answer.startswith("API 调用失败") or answer.startswith("API 调用发生异常"):
                raise Exception(answer)
        
        if current_user.is_authenticated:
            data_service.add_chat_history(current_user.id, question, answer)
            
        return jsonify({"answer": answer})

    # --- 新增：获取聊天记录的API ---
    @app.route('/api/chat/history', methods=['GET'])
    # @login_required 
    def api_get_chat_history():
        # 更新：使用 current_user.id
        if current_user.is_authenticated: # <-- 登录用户返回历史
            return jsonify({"history": data_service.get_chat_history(current_user.id)})
        else:
            return jsonify({"history": []}) # <-- 游客返回空列表

    @app.route('/api/chat/history', methods=['DELETE'])
    # @login_required 
    def api_clear_chat_history():
        if current_user.is_authenticated: # <-- 只在登录时清除
            data_service.clear_chat_history(current_user.id)
        return jsonify({"success": True})
    
    # --- 搜索红歌的api ---
    @app.route('/api/songs/search', methods=['GET'])
    def api_search_songs():
        # 更新：传入 current_user 以检查收藏状态
        return jsonify({"songs": data_service.search_songs(request.args.get('q', ''), current_user)})
    
    @app.route('/api/songs/by_region/<region_name>', methods=['GET'])
    def api_get_songs_by_region(region_name):
        # 更新：传入 current_user
        return jsonify({"songs": data_service.get_songs_by_region(region_name, current_user)})
    
    # --- 收藏红歌的API ---
    @app.route('/api/songs/favorites', methods=['GET'])
    @login_required # 保护
    def api_get_favorite_songs():
        # 更新：从 current_user 获取收藏
        return jsonify({"songs": data_service.get_favorite_songs(current_user)})
    
    @app.route('/api/song/toggle_favorite/<int:song_id>', methods=['POST'])
    @login_required # 保护
    def api_toggle_favorite(song_id):
        song = Song.query.get(song_id)
        if not song:
            return jsonify({"success": False, "message": "歌曲未找到"}), 404
        # 更新：传入 current_user 和 song 对象
        updated_song_dict = data_service.toggle_favorite_status(current_user, song)
        return jsonify({"success": True, "song": updated_song_dict})
    
    @app.route('/api/articles', methods=['GET'])
    def api_get_articles(): return jsonify({"articles": data_service.get_articles()})
    
    @app.route('/api/historical_events', methods=['GET'])
    def api_get_historical_events(): return jsonify({"events": data_service.get_historical_events()})
    
    @app.route('/api/create/lyrics', methods=['POST'])
    def api_create_lyrics():
        prompt = request.json.get('prompt', '我的家乡')
        sys_msg = "你是一位才华横溢的词曲作者。请围绕主题创作一首红歌歌词，包含主歌和副歌，正能量、朗朗上口。"
        
        # 直接调用核心函数，传入 system_instruction
        result = _call_openrouter_api(
            app.config["OPENROUTER_API_KEY"],
            [{"role": "user", "content": f"创作主题：{prompt}"}],
            system_instruction=sys_msg
        )
        
        if "error" in result: return jsonify({"lyrics": f"生成失败: {result['error']}"}), 500
        
        try:
            lyrics = result['choices'][0]['message']['content']
            return jsonify({"lyrics": lyrics})
        except:
            return jsonify({"lyrics": "生成内容解析失败"}), 500
        
    # 2. 开始AI作曲任务 (保持不变)
    @app.route('/api/create/song/start', methods=['POST'])
    def api_create_song_start():
        """
        仅调用 Kie.ai 进行音乐生成。
        步骤:
        1. 接收前端的歌词(prompt)和风格(style)。
        2. 发送 POST 请求给 Kie.ai，带上 callBackUrl (防止报错)。
        3. 提取返回的 taskId 并发送给前端。
        """
        data = request.json
        lyrics = data.get('lyrics')
        style = data.get('style', 'Classical')
        title = data.get('title', 'AI Red Song')

        if not lyrics: return jsonify({"error": "歌词不能为空"}), 400

        kie_key = app.config.get("KIE_API_KEY")
        if not kie_key or "YOUR_" in kie_key:
             return jsonify({"error": "Kie.ai API Key 未配置。"}), 500
        
        try:
            # 💥 修复：添加 callBackUrl 以满足 Kie.ai 要求
            kie_payload = {
                "prompt": lyrics,
                "style": style,
                "title": title,
                "customMode": True,
                "instrumental": False,
                "model": "V3_5",
                "callBackUrl": "https://redsong.bond/api/kie/callback" # 即使不处理，也必须传一个URL
            }
            
            headers = {
                "Authorization": f"Bearer {kie_key}",
                "Content-Type": "application/json"
            }
            
            resp = requests.post("https://api.kie.ai/api/v1/generate", headers=headers, json=kie_payload, timeout=20)
            
            if resp.status_code == 200:
                resp_data = resp.json()
                # 提取 taskId
                if resp_data.get("code") == 200 and resp_data.get("data"):
                    task_id = resp_data["data"].get("taskId")
                    # 返回给前端，前端会用这个 ID 来轮询 status 接口
                    return jsonify({"task_id": task_id, "provider": "kie"})
                else:
                    return jsonify({"error": f"Kie.ai 错误: {resp_data.get('msg')}"}), 500
            else:
                logger.error(f"Kie.ai HTTP Error: {resp.text}")
                return jsonify({"error": f"服务异常: {resp.status_code}"}), 503

        except Exception as e:
            logger.error(f"Kie.ai Connect Error: {e}")
            return jsonify({"error": f"连接失败: {str(e)}"}), 500
    # --- Kie.ai 回调接口 ---
    @app.route('/api/kie/callback', methods=['POST'])
    def api_kie_callback():
        try:
            req_data = request.get_json()
            logger.info(f"收到 Kie.ai 回调: {json.dumps(req_data, ensure_ascii=False)}")
            
            # 1. 解析数据
            inner_data = req_data.get("data", {})
            if not inner_data: return jsonify({"code": 200}), 200

            task_id = inner_data.get("task_id")
            songs_list = inner_data.get("data", [])
            
            # 2. 提取 URL
            audio_url = None
            if isinstance(songs_list, list) and len(songs_list) > 0:
                # 优先找 source_stream_audio_url (CDN直链)
                # 其次找 stream_audio_url
                song = songs_list[0]
                audio_url = (
                    song.get("source_stream_audio_url") or 
                    song.get("stream_audio_url") or 
                    song.get("audio_url")
                )

            # 3. 【关键修改】将结果写入共享文件，而不是内存变量
            if task_id and audio_url:
                file_path = os.path.join(CACHE_DIR, f"{task_id}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({"status": "SUCCESS", "audio_url": audio_url}, f)
                
                logger.info(f"✅ 任务文件已写入: {file_path}")
            
            return jsonify({"code": 200, "msg": "received"}), 200
                
        except Exception as e:
            logger.error(f"处理 Kie 回调失败: {e}")
            return jsonify({"code": 500, "msg": "Server Error"}), 500

    @app.route('/api/create/song/status/<task_id>', methods=['GET'])
    def api_create_song_status(task_id):
        # 1. 构建文件路径
        file_path = os.path.join(CACHE_DIR, f"{task_id}.json")
        
        # 2. 检查文件是否存在
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # --- (新增) 智能过滤逻辑 ---
                    # 获取当前的 audio_url
                    audio_url = data.get("audio_url", "")
                    
                    # 判断逻辑：如果 URL 存在，但既没有 .mp3 后缀，也不包含 cdn 关键字
                    # 我们认为这是一个"过程文件"（不可下载），因此返回 PROCESSING 让前端继续等
                    if audio_url and ".mp3" not in audio_url and "cdn" not in audio_url:
                        # 打印日志方便调试
                        logger.info(f"Task {task_id}: 命中缓存但链接非MP3 (URL: {audio_url[:30]}...)，等待覆盖...")
                        return jsonify({"status": "PROCESSING"})
                    
                    # 如果是通过校验的（是 MP3），直接返回成功
                    return jsonify(data) 
                    
            except Exception as e:
                logger.error(f"读取缓存文件失败: {e}")
                # 读取出错也返回处理中，防止前端报错停止
                return jsonify({"status": "PROCESSING"})

        # 3. 文件不存在，说明还在生成中
        return jsonify({"status": "PROCESSING"})


    

    @app.route('/api/guide/command', methods=['POST'])
    def api_guide_command():
        user_query = request.json.get('query', '')
        api_key = app.config.get("OPENROUTER_API_KEY")

        if not user_query:
            return jsonify({"action": "text_response", "message": "请输入您的问题。"}), 400
        
        if not api_key or api_key == "YOUR_OPENROUTER_API_KEY":
             return jsonify({"action": "text_response", "message": "AI Guide服务未配置API Key。"}), 500

        # 定义网站的预设可操作指令及其意图
        tool_map = {
            "search_songs": {"path": "/circle", "label": "前往听·山河"},
            "learn_stories": {"path": "/making", "label": "开始问·古今"},
            "study_history": {"path": "/plaza", "label": "进入阅·峥嵘"},
            "create_song": {"path": "/creation", "label": "开始谱·华章"},
            "view_favorites": {"path": "/favorites", "label": "查看我的收藏 (需登录)"},
            "site_info": {"path": "/", "label": "网站功能介绍"},
            "unrecognized": {"path": None, "label": "无法识别指令"}
        }
        
        # ... (硬编码的快捷回复逻辑保持不变) ...
        # 针对特定指令提供固定文本回复
        if "功能" in user_query and "网站" in user_query:
            info_message = (
                "本网站是**数智红韵网**，致力于传承红色文化：<br/>"
                "1. **听·山河**: 地图探索和歌曲检索。<br/>"
                "2. **问·古今**: 与AI专家对话，了解歌曲背后的故事。<br/>"
                "3. **阅·峥嵘**: 学习微课和史实时间轴。<br/>"
                "4. **谱·华章**: 利用AI生成歌词和旋律。"
            )
            return jsonify({
                "action": "text_response",
                "message": info_message,
                "label": "好的，这是网站功能介绍。"
            })
        
        if "主页" in user_query or "数智红韵" in user_query:
             return jsonify({
                "action": "navigate",
                "path": "/",
                "label": "主页"
            })
        
        identity_keywords = ["你是谁", "你是什么", "介绍一下你自己", "红小韵", "名字","你是"]
        if any(k in user_query for k in identity_keywords):
             return jsonify({
                "action": "text_response", 
                "message": "我是**红小韵**，数智红韵网的专属AI助手。<br/>我可以带您欣赏祖国各地的红歌，为您讲述红歌背后的历史故事，甚至辅佐您创作属于自己的红歌作品！",
                "label": "自我介绍"
            })

        action_id_list = list(tool_map.keys())
        
        # 修改 Prompt：明确要求 JSON 格式，因为我们不能依赖 response_schema 参数了
        system_prompt = (
            "你是一个网站导航AI助手。你的任务是根据用户提出的问题，从提供的预设指令中选出最符合用户意图的一个 action_id。\n"
            "请务必只返回一个标准的 JSON 对象，格式为: {\"action_id\": \"...\", \"intro_message\": \"...\"}。\n"
            "其中 'intro_message' 是你在执行跳转前对用户说的一句简短的话（支持Markdown），例如：'没问题，这就带您去了解这首红歌的故事！'\n"
            "如果用户的问题与任何预设指令都不匹配，action_id 请填 'unrecognized'。\n"
            "可选的 action_id 包括: "
            f"{', '.join(action_id_list)}"
        )
        # 调用核心函数，强制 JSON 格式
        data = _call_openrouter_api(
            api_key,
            [{"role": "user", "content": user_query}],
            response_format={"type": "json_object"}, 
            system_instruction=system_prompt)
        
        # 3. 解析返回的 JSON 内容
        if not data.get('choices'):
                raise Exception("API返回内容为空")

        action_json_str = data['choices'][0]['message']['content']
        
        # 清理可能存在的 markdown 标记 (虽然 prompt 禁止了，但为了稳健性)
        action_json_str = action_json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            action_data = json.loads(action_json_str)
        except json.JSONDecodeError:
            print(f"JSON解析失败，原始内容: {action_json_str}")
            action_data = {"action_id": "unrecognized"}

        action_id = action_data.get('action_id', 'unrecognized')
        action_info = tool_map.get(action_id, tool_map['unrecognized'])
        intro_message = action_data.get('intro_message', '') # 获取 LLM 生成的回复

        if action_id == 'unrecognized' or action_id == 'site_info':
            return jsonify({
                "action": "text_response",
                "message": "抱歉，我不太理解您的意图，您可以尝试点击预设按钮，或直接访问相应页面。"
            })
        elif action_info.get("path"):
            return jsonify({
                "action": "navigate",
                "path": action_info["path"],
                "label": action_info["label"],
                "intro_message": intro_message  # 将 LLM 的回复传给前端
            })
        else:
                return jsonify({
                "action": "text_response",
                "message": "抱歉，无法执行该指令。"
            })

    # --- 地域红歌深度分析 API ---
    @app.route('/api/region/analyze', methods=['POST'])
    def api_analyze_region():
        region_name = request.json.get('region', '')
        api_key = app.config.get("OPENROUTER_API_KEY")

        if not region_name:
            return jsonify({"analysis": "请选择一个地区进行分析。"}), 400

        # 为了给AI提供依据，我们需要查出该地区的红歌数量和几首代表作
        if region_name == "全国":
             songs = Song.query.all()
        else:
            # 模糊匹配，处理“陕西省” vs “陕西”
            clean_region = region_name.replace('省', '').replace('市', '').replace('自治区', '')
            songs = Song.query.filter(Song.region.ilike(f"%{clean_region}%")).all()
        
        
        count = len(songs)
        if count == 0:
            return jsonify({"analysis": f"暂未收录 {region_name} 地区的红歌数据，因此无法进行风格分析。欢迎补充！"})

        
        # 取出前5首代表作作为上下文
        sample_titles = [s.title for s in songs[:5]]
        sample_str = "、".join(sample_titles)

        # 构造 AI Prompt
        sys_msg = (
            "你是一位著名的红歌文化与中国革命史专家。请根据用户提供的地区、红歌数量和代表作，"
            "分析该地区红歌的**历史成因**（如：是否为革命根据地、发生了什么重大事件）和**艺术风格**（如：结合了当地什么民歌特色）。"
            "回答要简练深刻，具有文化底蕴，字数控制在150字以内。"
        )

        user_query = (
            f"分析对象：{region_name}\n"
            f"收录红歌数量：{count}首\n"
            f"部分代表作：{sample_str}\n\n"
            "请分析为什么该地区会诞生这些红歌？其风格有何独特性？"
        )

        
        # 调用核心函数，传入 system_instruction
        result = _call_openrouter_api(
            api_key,
            [{"role": "user", "content": user_query}],
            system_instruction=sys_msg
        )
        
        if "error" in result: return jsonify({"analysis": "分析服务暂时不可用。"}), 503
        
        try:
            analysis = result['choices'][0]['message']['content']
            return jsonify({"region": region_name, "count": count, "analysis": analysis})
        except:
            return jsonify({"analysis": "分析生成失败。"}), 500
    @app.route('/api/forum/posts', methods=['GET'])
    def api_get_forum_posts():
        return jsonify({"posts": data_service.get_forum_posts(current_user)})

    @app.route('/api/forum/posts', methods=['POST'])
    @login_required 
    def api_add_forum_post():
        content = request.json.get('content', '').strip()
        if not content: return jsonify({"error": "内容不能为空"}), 400
        if len(content) > 200: return jsonify({"error": "内容不能超过200字"}), 400
        
        SENSITIVE_WORDS = ["暴力", "色情", "赌博", "反动", "脏话", "违规"]
        for word in SENSITIVE_WORDS:
            if word in content:
                return jsonify({"error": f"内容包含敏感词汇“{word}”，发布失败。"}), 400

        new_post = data_service.add_forum_post(current_user.id, content)
        return jsonify({"success": True, "post": new_post})

    @app.route('/api/forum/posts/<int:post_id>', methods=['DELETE'])
    @login_required
    def api_delete_forum_post(post_id):
        if data_service.delete_forum_post(post_id, current_user.id):
            return jsonify({"success": True})
        return jsonify({"error": "删除失败"}), 403

    @app.route('/api/forum/posts/like/<int:post_id>', methods=['POST'])
    @login_required
    def api_toggle_post_like(post_id):
        result = data_service.toggle_post_like(post_id, current_user)
        if result: return jsonify({"success": True, "liked": result['liked'], "count": result['count']})
        return jsonify({"error": "帖子不存在"}), 404



# ==============================================================================
# 5. 应用启动
# ==============================================================================
app = create_app()

if __name__ == '__main__':
    print("服务器已启动，请在浏览器中打开 http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000)

