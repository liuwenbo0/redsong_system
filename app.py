# coding=utf-8
import os
import time
import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

# 导入登录管理
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import json  # 引入json库
import logging
import requests

# 从 database.py 导入 db 对象、所有模型和注册命令的函数
from database import (
    db,
    Song,
    Article,
    HistoricalEvent,
    ChatHistory,
    register_commands,
    DataService,
    User,
    init_db,
)
import re  # (新增) 导入正则表达式
from dotenv import load_dotenv

# --- 引入新拆分的服务 ---
from services.llm_service import call_openrouter_api, generate_openrouter_content
from services.agent_service import process_agent_request

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# --- 加载环境变量 ---
load_dotenv()  # 从 .env 文件加载环境变量

# --- 获取项目根目录 ---
basedir = os.path.abspath(os.path.dirname(__file__))
SENSITIVE_WORDS = ["暴力", "色情", "赌博", "反动", "脏话", "违规"]
CACHE_DIR = os.path.join(basedir, "temp_tasks")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


# ==============================================================================
# 1. 应用配置 (Configuration)
# ==============================================================================
class Config:
    # 基础配置
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "jf83h_sdf98f3h2983hf9834hf9834h")

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'project.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API 密钥配置
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    KIE_API_KEY = os.getenv("KIE_API_KEY", "")
    
    # 回调URL配置 (用于接收Kie API生成的歌曲回调)
    # 生产环境使用生产地址，本地开发可以使用ngrok等工具创建公网访问地址
    CALLBACK_URL = os.getenv(
        "CALLBACK_URL", "https://redsong.bond/api/kie/callback"
    )

    # 生产环境配置
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))


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
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    CORS(
        app, supports_credentials=True
    )  # supports_credentials=True 对 session 至关重要
    db.init_app(app)
    login_manager.init_app(app)  # 初始化登录管理器
    register_routes(app)
    register_commands(app)  # 注册来自 database.py 的命令行

    # 自动创建数据库表（在应用上下文中）
    with app.app_context():
        db.create_all()
        init_db()
        logger.info("数据库表已自动创建/检查")

    return app


# ==============================================================================
# 4. 注册路由
# ==============================================================================
def register_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/circle")
    def circle_page():
        return render_template("circle.html")

    @app.route("/favorites")
    @login_required
    def favorites_page():
        return render_template("favorites.html")

    @app.route("/making")
    def making_page():
        return render_template("making.html")

    @app.route("/plaza")
    def plaza_page():
        return render_template("plaza.html")

    @app.route("/creation")
    def creation_page():
        return render_template("creation.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            "static/images", "favicon.ico", mimetype="image/vnd.microsoft.icon"
        )

    # --- 用户认证 API ---
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json()
        username, password, confirm = (
            data.get("username"),
            data.get("password"),
            data.get("confirm_password"),
        )
        if not username or not password or not confirm:
            return jsonify({"error": "字段不能为空"}), 400
        if len(username) > 15:
            return jsonify({"error": "用户名太长"}), 400
        if password != confirm:
            return jsonify({"error": "密码不一致"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "用户名已存在"}), 400
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return jsonify({"success": True, "username": new_user.username})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data.get("username")).first()
        if user and user.check_password(data.get("password")):
            login_user(user, remember=True)
            return jsonify({"success": True, "username": user.username})
        return jsonify({"error": "用户名或密码无效"}), 401

    @app.route("/api/auth/logout")
    @login_required
    def logout():
        logout_user()
        return jsonify({"success": True})

    @app.route("/api/auth/status")
    def auth_status():
        if current_user.is_authenticated:
            return jsonify(
                {
                    "logged_in": True,
                    "username": current_user.username,
                    "user_id": current_user.id,
                }
            )
        return jsonify({"logged_in": False})

    # --- 统一 Agent 核心路由 ---
    @app.route("/api/agent/chat", methods=["POST"])
    def api_agent_chat():
        """
        Agent 对话接口：
        1. 接收用户输入或确认动作
        2. 调用 Agent Service 处理业务逻辑
        3. 返回 JSON 响应
        """
        data = request.json
        result_dict_or_tuple = process_agent_request(
            user_input=data.get("user_input", "").strip(),
            history=data.get("conversation_history", []),
            confirmed_action=data.get("confirmed_action"),
            api_key=app.config.get("OPENROUTER_API_KEY"),
            data_service=data_service,
            user=current_user,
        )

        if isinstance(result_dict_or_tuple, tuple):
            return jsonify(result_dict_or_tuple[0]), result_dict_or_tuple[1]
        return jsonify(result_dict_or_tuple)

    # --- 其他 API ---
    @app.route("/api/chat/history", methods=["GET"])
    def api_get_chat_history():
        if current_user.is_authenticated:
            return jsonify({"history": data_service.get_chat_history(current_user.id)})
        return jsonify({"history": []})

    @app.route("/api/chat/history", methods=["DELETE"])
    def api_clear_chat_history():
        if current_user.is_authenticated:
            data_service.clear_chat_history(current_user.id)
        return jsonify({"success": True})

    @app.route("/api/songs/search", methods=["GET"])
    def api_search_songs():
        return jsonify(
            {
                "songs": data_service.search_songs(
                    request.args.get("q", ""), current_user
                )
            }
        )

    @app.route("/api/songs/by_region/<region_name>", methods=["GET"])
    def api_get_songs_by_region(region_name):
        return jsonify(
            {"songs": data_service.get_songs_by_region(region_name, current_user)}
        )

    @app.route("/api/songs/favorites", methods=["GET"])
    @login_required
    def api_get_favorite_songs():
        return jsonify({"songs": data_service.get_favorite_songs(current_user)})

    @app.route("/api/song/toggle_favorite/<int:song_id>", methods=["POST"])
    @login_required
    def api_toggle_favorite(song_id):
        song = Song.query.get(song_id)
        if not song:
            return jsonify({"success": False}), 404
        return jsonify(
            {
                "success": True,
                "song": data_service.toggle_favorite_status(current_user, song),
            }
        )

    @app.route("/api/articles", methods=["GET"])
    def api_get_articles():
        return jsonify({"articles": data_service.get_articles()})

    @app.route("/api/historical_events", methods=["GET"])
    def api_get_historical_events():
        return jsonify({"events": data_service.get_historical_events()})

    @app.route("/api/create/lyrics", methods=["POST"])
    def api_create_lyrics():
        p = request.json.get("prompt", "家乡")
        res = call_openrouter_api(
            app.config["OPENROUTER_API_KEY"],
            [{"role": "user", "content": f"主题：{p}"}],
            system_instruction="你是一位红歌作词家。",
        )
        if "error" in res:
            return jsonify({"lyrics": "生成失败"}), 500
        return jsonify({"lyrics": res["choices"][0]["message"]["content"]})

    @app.route("/api/create/song/start", methods=["POST"])
    def api_create_song_start():
        d = request.json
        kie_key = app.config.get("KIE_API_KEY")
        if not kie_key:
            logger.warning(
                "Kie API Key is missing. Please configure KIE_API_KEY in .env."
            )
            return jsonify(
                {"error": "Kie API Key未配置，请联系管理员或检查.env文件"}
            ), 500
        try:
            p = {
                "prompt": d.get("lyrics"),
                "style": d.get("style", "Classical"),
                "title": d.get("title", "AI Red Song"),
                "customMode": True,
                "instrumental": False,
                "model": "V3_5",
                "callBackUrl": app.config.get("CALLBACK_URL"),
            }

            api_host = os.getenv("KIE_API_HOST", "https://api.kie.ai")
            api_url = f"{api_host.rstrip('/')}/api/v1/generate"
            is_relay = "api.kie.ai" not in api_host

            try:
                r = requests.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {kie_key}",
                        "Content-Type": "application/json",
                    },
                    json=p,
                    timeout=20,
                )
            except requests.exceptions.ConnectionError:
                err_msg = f"连接失败: 无法访问{'中转服务器' if is_relay else 'Kie接口'}({api_host})，请检查网络或中转服务是否开启。"
                logger.error(err_msg)
                return jsonify({"error": err_msg}), 502
            except requests.exceptions.Timeout:
                err_msg = "请求超时: 服务器响应过慢，请稍后再试。"
                logger.error(err_msg)
                return jsonify({"error": err_msg}), 504

            if r.status_code == 200:
                rj = r.json()
                code = rj.get("code")
                if code == 200:
                    return jsonify(
                        {"task_id": rj["data"].get("taskId"), "provider": "kie"}
                    )

                msg = rj.get("msg", "")
                logger.error(f"Kie API Logic Error: {rj}")

                # Check for IP whitelist error
                if code == 401 or "whitelist" in msg.lower():
                    try:
                        my_ip = requests.get("https://api.ipify.org", timeout=2).text
                    except:
                        my_ip = "无法自动获取"

                    target = "中转服务器IP" if is_relay else "本地IP"
                    err_msg = f"API权限错误: {target}不在白名单。当前检测到IP: {my_ip}。请在Kie后台添加{'中转机IP' if is_relay else ''}。"
                    logger.error(err_msg)
                    return jsonify({"error": err_msg}), 500

                return jsonify({"error": f"Kie服务错误: {msg}"}), 500

            # 处理中转服务器可能返回的 502/503/504
            if r.status_code in [502, 503, 504] and is_relay:
                err_msg = f"中转服务异常({r.status_code}): 请检查服务器 {api_host} 的 Nginx 配置是否正确。"
                logger.error(err_msg)
                return jsonify({"error": err_msg}), r.status_code

            logger.error(f"Kie API HTTP Error: {r.status_code} - {r.text}")
            return jsonify({"error": f"外部服务HTTP错误: {r.status_code}"}), 500
        except Exception as e:
            logger.exception("Unexpected error in api_create_song_start")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/kie/callback", methods=["POST"])
    def api_kie_callback():
        try:
            d = request.get_json().get("data", {})
            tid, slist = d.get("task_id"), d.get("data", [])
            if tid and slist:
                url = (
                    slist[0].get("source_stream_audio_url")
                    or slist[0].get("stream_audio_url")
                    or slist[0].get("audio_url")
                )
                if url:
                    with open(os.path.join(CACHE_DIR, f"{tid}.json"), "w") as f:
                        json.dump({"status": "SUCCESS", "audio_url": url}, f)
            return jsonify({"code": 200}), 200
        except:
            return jsonify({"code": 500}), 500

    @app.route("/api/create/song/status/<task_id>", methods=["GET"])
    def api_create_song_status(task_id):
        path = os.path.join(CACHE_DIR, f"{task_id}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                d = json.load(f)
                if ".mp3" in d.get("audio_url", "") or "cdn" in d.get("audio_url", ""):
                    return jsonify(d)
        return jsonify({"status": "PROCESSING"})

    @app.route("/api/guide/command", methods=["POST"])
    def api_guide_command():
        q = request.json.get("query", "")
        api_key = app.config.get("OPENROUTER_API_KEY")
        if not q or not api_key:
            return jsonify({"action": "text_response", "message": "请输入问题"}), 400
        tool_map = {
            "search_songs": {"path": "/circle", "label": "听·山河"},
            "learn_stories": {"path": "/making", "label": "问·古今"},
            "study_history": {"path": "/plaza", "label": "阅·峥嵘"},
            "create_song": {"path": "/creation", "label": "谱·华章"},
            "view_favorites": {"path": "/favorites", "label": "我的收藏"},
            "site_info": {"path": "/", "label": "功能介绍"},
        }
        prompt = (
            """你是一个导航AI。根据用户问题返回 JSON: {"action_id": "...", "intro_message": "..."}。可选 action_id: """
            + ", ".join(tool_map.keys())
        )
        res = call_openrouter_api(
            api_key,
            [{"role": "user", "content": q}],
            response_format={"type": "json_object"},
            system_instruction=prompt,
        )
        try:
            aj = json.loads(res["choices"][0]["message"]["content"])
            aid = aj.get("action_id", "unrecognized")
            if aid in tool_map:
                return jsonify(
                    {
                        "action": "navigate",
                        "path": tool_map[aid]["path"],
                        "label": tool_map[aid]["label"],
                        "intro_message": aj.get("intro_message", ""),
                    }
                )
            return jsonify({"action": "text_response", "message": "抱歉，没听懂"})
        except:
            return jsonify({"action": "text_response", "message": "服务异常"}), 500

    @app.route("/api/region/analyze", methods=["POST"])
    def api_analyze_region():
        rname = request.json.get("region", "")
        api_key = app.config.get("OPENROUTER_API_KEY")
        if not rname or not api_key:
            return jsonify({"analysis": "参数错误"}), 400
        songs = (
            Song.query.all()
            if rname == "全国"
            else Song.query.filter(
                Song.region.ilike(f"%{rname.replace('省', '').replace('市', '')}%")
            ).all()
        )
        if not songs:
            return jsonify({"analysis": "暂无数据"})
        prompt = "你是一位红歌文化专家。分析该地区红歌的历史成因和艺术风格，150字以内。"
        q = f"地区：{rname}，数量：{len(songs)}，代表作：{'、'.join([s.title for s in songs[:5]])}"
        res = call_openrouter_api(
            api_key, [{"role": "user", "content": q}], system_instruction=prompt
        )
        try:
            return jsonify(
                {
                    "region": rname,
                    "count": len(songs),
                    "analysis": res["choices"][0]["message"]["content"],
                }
            )
        except:
            return jsonify({"analysis": "生成失败"}), 500

    @app.route("/api/forum/posts", methods=["GET"])
    def api_get_forum_posts():
        return jsonify({"posts": data_service.get_forum_posts(current_user)})

    @app.route("/api/forum/posts", methods=["POST"])
    @login_required
    def api_add_forum_post():
        c = request.json.get("content", "").strip()
        if not c or len(c) > 200:
            return jsonify({"error": "内容不合法"}), 400
        for w in SENSITIVE_WORDS:
            if w in c:
                return jsonify({"error": f"含敏感词{w}"}), 400
        return jsonify(
            {"success": True, "post": data_service.add_forum_post(current_user.id, c)}
        )

    @app.route("/api/forum/posts/<int:post_id>", methods=["DELETE"])
    @login_required
    def api_delete_forum_post(post_id):
        if data_service.delete_forum_post(post_id, current_user.id):
            return jsonify({"success": True})
        return jsonify({"error": "失败"}), 403

    @app.route("/api/forum/posts/like/<int:post_id>", methods=["POST"])
    @login_required
    def api_toggle_post_like(post_id):
        res = data_service.toggle_post_like(post_id, current_user)
        if res:
            return jsonify(
                {"success": True, "liked": res["liked"], "count": res["count"]}
            )
        return jsonify({"error": "不存在"}), 404


# ==============================================================================
# 5. 应用启动
# ==============================================================================
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config.get("PORT", 5000))
