"""
LLM 服务模块

提供与 OpenRouter API 交互的接口，使用 Google Gemini 模型进行：
- 意图识别
- 文本生成
- 歌词创作
"""

import json
import logging
import re

import requests

logger = logging.getLogger(__name__)


def call_openrouter_api(
    api_key, messages, response_format=None, system_instruction=None
):
    """
    OpenRouter API 统一调用入口

    该函数是与 OpenRouter API 交互的核心方法，负责：
    1. 验证 API Key
    2. 构建请求 payload
    3. 处理系统指令
    4. 处理响应格式（支持 JSON 模式）
    5. 错误处理和日志记录
    6. JSON 响应的增强提取（支持从 Markdown 代码块中提取）

    Args:
        api_key (str): OpenRouter API 密钥
        messages (list): 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
        response_format (dict, optional): 响应格式配置，例如 {"type": "json_object"}
        system_instruction (str, optional): 系统指令，用于设置 AI 的行为模式

    Returns:
        dict: API 响应字典，包含：
            - 成功时：OpenRouter API 的完整响应
            - 失败时：包含 "error" 键的错误信息字典

    Error Codes:
        401: API 认证失败
        402: API 余额不足
        其他: API 调用失败

    Examples:
        简单调用：
        >>> result = call_openrouter_api(
        ...     api_key="sk-...",
        ...     messages=[{"role": "user", "content": "你好"}]
        ... )

        JSON 模式调用：
        >>> result = call_openrouter_api(
        ...     api_key="sk-...",
        ...     messages=[{"role": "user", "content": "分析我的意图"}],
        ...     response_format={"type": "json_object"},
        ...     system_instruction="返回 JSON 格式的结果"
        ... )
    """
    # 验证 API Key
    if not api_key or "YOUR_" in api_key:
        return {"error": "API Key not configured or invalid."}

    # 构建请求 payload
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "max_tokens": 4096,
    }

    # 处理系统指令
    if system_instruction:
        # 将系统指令插入到消息列表的开头
        final_messages = [{"role": "system", "content": system_instruction}] + messages
        payload["messages"] = final_messages
    else:
        payload["messages"] = messages

    # 处理响应格式
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
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter Error {response.status_code}: {response.text}")
            if response.status_code == 401:
                return {"error": "API Authentication Failed"}
            if response.status_code == 402:
                return {"error": "Insufficient Balance"}
            return {"error": f"API Call Failed ({response.status_code})"}

        result = response.json()

        # JSON 模式增强：从 Markdown 代码块中提取 JSON
        if response_format and response_format.get("type") == "json_object":
            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    # 尝试从 Markdown 代码块或文本中查找 JSON 内容
                    match = re.search(r"\{.*\}", content, re.DOTALL)
                    if match:
                        result["choices"][0]["message"]["content"] = match.group(0)

        return result

    except Exception as e:
        logger.error(f"OpenRouter Exception: {e}")
        return {"error": f"Request Exception: {str(e)}"}
