# pages/ficc_ai_element_page.py
# 新增页面类：自动解析页面字段结构并输出 JSON

from playwright.sync_api import Page
from llm.element_analyzer import analyze_dom_structure

class AiElementExtractorPage:
    def __init__(self, page: Page, model_source: str = "ollama", api_key: str = None):
        self.page = page
        self.model_source = model_source
        self.api_key = api_key

    def analyze_fields(self, save_to: str = None) -> str:
        """
        获取页面 HTML，调用大模型识别字段结构，并输出结构化 JSON。
        如果指定 save_to 路径，则保存结果到该文件。
        """
        print("📄 正在提取页面 HTML...")
        html_content = self.page.content()

        print("🤖 调用大模型进行字段识别...")
        result = analyze_dom_structure(html_content, source=self.model_source, api_key=self.api_key)

        print("✅ 字段结构识别完成：\n", result)

        if save_to:
            with open(save_to, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"📁 已保存到: {save_to}")

        return result
