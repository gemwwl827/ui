# ai_element_filler.py
# 智能充值表单元素：根据 label 名称调用大模型，输出元素类型、是否必填、示例值

from llm.llm_client import call_model


def generate_fields_by_labels(label_list: list[str]) -> list[dict]:
    """
    根据 label 列表调用大模型，输出结构化元素配置
    输出格式：[{label, 类型, 是否必填, 示例值}, ...]
    """
    prompt = """请将以下字段识别其类型（输入框/下拉框/弹窗），是否必填，提供一个示例值，并输出 JSON 数组：
{}
    """.format('\n'.join(f"- {label}" for label in label_list))

    result = call_model(prompt)

    try:
        parsed = eval(result) if isinstance(result, str) else result
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception as e:
        print("解析失败", e)
        return []


if __name__ == "__main__":
    labels = ["债券代码", "发行机构", "债券类型", "交易价格"]
    data = generate_fields_by_labels(labels)
    for item in data:
        print(item)
