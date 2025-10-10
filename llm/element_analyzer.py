# llm/element_analyzer.py
# 字段结构智能识别器：从 HTML DOM 中提取交互字段（输入框、下拉、日期、弹窗等）

import pathlib
import os
from llm.llm_client import call_model  # 调用统一模型接口（支持 Ollama / GPT4o）
from dotenv import load_dotenv  # 加载 .env 中的 API Key

# ✅ 加载环境变量（支持读取 OPENAI_API_KEY）
load_dotenv()


def analyze_dom_structure(dom_text: str, source: str = "ollama", api_key: str = None, model: str = None) -> str:
    """
    调用大模型分析 HTML，提取结构化字段信息。

    :param dom_text: 页面 HTML 内容
    :param source: 模型来源（ollama 或 gpt4）
    :param api_key: GPT 模型密钥（可选，默认读取 .env）
    :param model: 模型名称（例如 "gpt-4"、"gpt-3.5-turbo"、"qwen:7b"）
    :return: 模型返回的结构化字段 JSON 字符串
    """
    # 构造提示词
    prompt = f"""你是一名资深自动化测试工程师，擅长解析页面 DOM 结构。

请从以下 HTML 页面中提取所有“可交互字段”（如输入框、日期选择、下拉、弹窗等），输出结构化 JSON 数组。

要求如下：
- 每个字段一个对象
- 字段包含字段名、字段类型、是否必填、示例值（字符串或数组）

示例输出：
[
  {{
    "字段名": "债券代码",
    "字段类型": "输入框",
    "是否必填": "是",
    "示例值": "000123"
  }}
]

以下是 HTML 页面内容：
{dom_text}
"""

    # ✅ 调用模型（统一封装接口）
    return call_model(prompt, source=source, api_key=api_key, model=model)


# ✅ 可单独运行本模块进行测试
if __name__ == "__main__":
    html_path = pathlib.Path("data/example_form.html")  # 指定示例 HTML 路径

    if not html_path.exists():
        print(f"❌ 文件不存在: {html_path}")
    else:
        html_content = html_path.read_text(encoding="utf-8")

        # 使用 GPT-4o 模型（默认从环境变量读取 API Key）
        result = analyze_dom_structure(html_content, source="gpt4", model="gpt-4o")

        print("\n📦 模型输出结果：\n")
        print(result)
