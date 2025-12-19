import json
import logging
from database import Article
from services.llm_service import call_openrouter_api

logger = logging.getLogger(__name__)

SENSITIVE_WORDS = ["暴力", "色情", "赌博", "反动", "脏话", "违规"]

AGENT_SYSTEM_PROMPT = """你是一个名为'红小韵'的AI陪伴助手，专注于红歌文化与中国革命史。
你的任务是分析用户输入，并返回一个 JSON 对象。格式: {"intent": "...", "params": {...}, "reply_text": "..."}

Intent 判别规则:
1. 'navigate': 用户想去某个页面. params: {target: "..."}.
   **可用路径(target):**
   - '/circle' (听·山河/听歌/搜歌页面)
   - '/making' (问·古今/对话/故事页面)
   - '/plaza' (阅·峥嵘/视频/微课/史实页面)
   - '/creation' (谱·华章/创作/写歌页面)
   - '/favorites' (我的收藏)
   - '/' (主页)
   如果用户未指定具体页面，根据上下文判断最合适的页面。

2. 'create_song_lyrics': 用户想写歌/创作 (params: {theme: string})
3. 'search_video': 用户想看视频/学历史 (params: {keyword: string})
4. 'search_songs': 用户想听歌/找歌 (params: {keyword: string})
5. 'chat': 其他闲聊

注意：reply_text 必须填写，且不能为空。"""


def process_agent_request(
    user_input, history, confirmed_action, api_key, data_service, user
):
    """
    处理 Agent 请求的核心业务逻辑
    :param user_input: 用户输入的文本
    :param history: 对话历史 (frontend_history)
    :param confirmed_action: 前端传回的确认动作
    :param api_key: LLM API Key
    :param data_service: 数据服务实例
    :param user: 当前用户对象 (current_user)
    :return: 响应字典 (可直接 JSONify) 或 tuple (dict, status_code)
    """
    if not api_key:
        return {"error": "API Key 未配置"}, 500

    if not user_input and not confirmed_action:
        return {"error": "输入不能为空"}, 400

    # 1. 执行已确认动作
    if confirmed_action:
        return _handle_confirmed_action(confirmed_action, api_key, data_service, user)

    # 2. 敏感词过滤
    for word in SENSITIVE_WORDS:
        if word in user_input:
            return {"response_type": "text", "text_response": "请文明用语"}

    # 3. 构建上下文
    messages = []
    if user.is_authenticated:
        # 从数据库获取最近历史
        db_history = data_service.get_chat_history(user.id)[-6:]
        for h in db_history:
            messages.extend(
                [
                    {"role": "user", "content": h["question"]},
                    {"role": "assistant", "content": h["answer"]},
                ]
            )
    else:
        # 使用前端传来的历史
        messages = history[-6:]

    messages.append({"role": "user", "content": user_input})

    # 4. 调用 LLM 进行意图识别
    llm_res = call_openrouter_api(
        api_key,
        messages,
        response_format={"type": "json_object"},
        system_instruction=AGENT_SYSTEM_PROMPT,
    )

    try:
        # 解析 LLM 响应
        content = llm_res["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        intent = parsed.get("intent", "chat")
        params = parsed.get("params", {})
        reply = parsed.get("reply_text", "收到")

        if not reply:
            reply = "好的"

        # 5. 根据意图分发
        if intent == "chat":
            if user.is_authenticated:
                data_service.add_chat_history(user.id, user_input, reply)
            return {"response_type": "text", "text_response": reply}

        elif intent in ["search_songs", "search_songs_by_keyword"]:
            kw = params.get("keyword", "").strip()
            songs = data_service.search_songs(
                kw, user if user.is_authenticated else None
            )
            return {
                "response_type": "content_card",
                "card_type": "song_list",
                "data": songs,
                "text_response": reply,
            }

        elif intent == "search_video":
            kw = params.get("keyword", "").strip()
            vids = [
                a.to_dict()
                for a in Article.query.filter(Article.title.contains(kw)).all()
                if a.video_url
            ]
            if not vids:
                return {
                    "response_type": "text",
                    "text_response": f"未找到关于{kw}的视频。",
                }
            return {
                "response_type": "content_card",
                "card_type": "video_list",
                "data": vids,
                "text_response": reply,
            }

        elif intent == "navigate":
            return {
                "response_type": "navigate",
                "path": params.get("target", "/"),
                "text_response": reply,
            }

        elif intent == "create_song_lyrics":
            # 只有歌词创作需要二次确认
            return {
                "response_type": "confirmation_required",
                "data": {"intent": intent, "params": params},
                "text_response": reply,
            }

        return {"response_type": "text", "text_response": reply}

    except Exception as e:
        logger.error(f"Agent Logic Error: {e}")
        return {"response_type": "text", "text_response": "红小韵走神了，请再说一遍。"}


def _handle_confirmed_action(confirmed_action, api_key, data_service, user):
    """处理前端确认后的动作"""
    intent = confirmed_action.get("intent")
    params = confirmed_action.get("params", {})

    if intent == "create_song_lyrics":
        theme = params.get("theme", "祖国")
        res = call_openrouter_api(
            api_key,
            [{"role": "user", "content": f"创作主题：{theme}"}],
            system_instruction="你是一位才华横溢的红歌作词家。请创作一首正能量、朗朗上口的歌词。",
        )

        lyrics = "创作失败"
        if "choices" in res and len(res["choices"]) > 0:
            lyrics = res["choices"][0]["message"]["content"]

        return {
            "response_type": "content_card",
            "card_type": "lyrics_card",
            "data": {
                "lyrics": lyrics,
                "theme": theme,
                "navigate_instruction": {
                    "path": "/creation",
                    "params": {"auto_fill_lyrics": lyrics},
                },
            },
            "text_response": "歌词创作完成！",
        }

    return {"response_type": "text", "text_response": "暂不支持该操作"}
