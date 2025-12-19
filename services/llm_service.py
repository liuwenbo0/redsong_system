import json
import logging
import requests
import re

logger = logging.getLogger(__name__)

def call_openrouter_api(api_key, messages, response_format=None, system_instruction=None):
    """
    OpenRouter API Unified Call Entry Point.
    Handles HTTP requests, API Key validation, error catching, and JSON mode.
    """
    if not api_key or "YOUR_" in api_key:
        return {"error": "API Key not configured or invalid."}

    # Construct Request Payload
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "max_tokens": 4096
    }
    
    # Handle system instruction
    if system_instruction:
        # Insert at the beginning of the messages list
        final_messages = [{"role": "system", "content": system_instruction}] + messages
        payload["messages"] = final_messages
    else:
        payload["messages"] = messages 

    # Handle response format
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
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"OpenRouter Error {response.status_code}: {response.text}")
            if response.status_code == 401:
                return {"error": "API Authentication Failed"}
            if response.status_code == 402:
                return {"error": "Insufficient Balance"}
            return {"error": f"API Call Failed ({response.status_code})"}
        
        result = response.json()

        # --- Enhancement: JSON Extraction ---
        if response_format and response_format.get("type") == "json_object":
            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    # Try to find JSON content within markdown code blocks or text
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        result['choices'][0]['message']['content'] = match.group(0)
            
        return result

    except Exception as e:
        logger.error(f"OpenRouter Exception: {e}")
        return {"error": f"Request Exception: {str(e)}"}

def generate_openrouter_content(messages, api_key, system_instruction):
    """Convenience wrapper function for simple text generation."""
    result = call_openrouter_api(api_key, messages, None, system_instruction)
    if "error" in result:
        return f"API Error: {result['error']}"
    try:
        if result.get("choices") and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return "API returned empty content."
    except Exception:
        return "API returned abnormal format."