# llm/llm_client.py
# 支持多模型调用：本地 Ollama (qwen:7b)，云端 GPT-4o，并从 .env 文件读取密钥

import requests  # 用于发送 HTTP 请求
import os        # 用于读取环境变量
from dotenv import load_dotenv  # 自动加载 .env 文件

# ✅ 加载环境变量（自动读取 .env 中的 OPENAI_API_KEY）
load_dotenv()

# ✅ 本地 Ollama 模型调用地址（你部署在服务器的 qwen:7b 模型）
OLLAMA_API_URL = "http://150.158.137.35:11434/api/generate"

# ✅ OpenAI Chat 模型调用地址（GPT-4o / GPT-4 / GPT-3.5）
OPENAI_CHAT_API_URL = "https://api.openai.com/v1/chat/completions"


def call_ollama(prompt: str, model: str = "qwen:7b", timeout: int = 120) -> str:
    """
    调用本地 Ollama 模型，默认使用 qwen:7b。
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        res = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
        return res.json().get("response", "").strip()
    except Exception as e:
        return f"❌ Ollama 模型调用失败: {e}"


def call_gpt4(prompt: str, api_key: str, model: str = "gpt-4o", timeout: int = 120) -> str:
    """
    调用 OpenAI GPT-4o 或 GPT-4 模型（需传入 API 密钥）
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        res = requests.post(OPENAI_CHAT_API_URL, headers=headers, json=payload, timeout=timeout)
        data = res.json()
        print("📥 原始响应 JSON：", data)
        return data.get("choices", [{}])[0].get("message", {}).get("content", "❌ 未获取到有效响应")

    except Exception as e:
        return f"❌ GPT 模型调用失败: {e}"


def call_model(prompt: str, source: str = "ollama", api_key: str = None, model: str = None) -> str:
    """
    通用模型调用入口，支持 source = "ollama" 或 "gpt4"。

    :param prompt: 提示词内容
    :param source: 模型来源（ollama 或 gpt4）
    :param api_key: GPT 模型用的 OpenAI API Key（可省略，默认读取环境变量）
    :param model: 可选，指定具体模型，如 "gpt-4" / "gpt-3.5-turbo" / "qwen:7b"
    """
    if source == "gpt4":
        # ✅ 优先使用传入的 key，否则读取环境变量
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "❌ GPT API key 未传入，且未在环境变量中设置 OPENAI_API_KEY"
        return call_gpt4(prompt, api_key, model=model or "gpt-4o")

    elif source == "deepseek":
        # ✅ 调用本地部署的 DeepSeek 模型（通过 Ollama）
        return call_ollama(prompt, model=model or "deepseek-coder:instruct")

    else:
        # 默认走 Ollama qwen:7b
        return call_ollama(prompt, model=model or "qwen:7b")


# ✅ 测试入口（直接运行本文件进行快速验证）
if __name__ == "__main__":
    prompt = "请列出5种常见的自动化测试工具，并简要说明用途"

    print("\n--- ✅ 本地 Ollama ---")
    print(call_model(prompt, source="ollama"))

    print("\n--- 🤖 GPT-4o (环境变量 API Key) ---")
    print(call_model(prompt, source="gpt4"))
