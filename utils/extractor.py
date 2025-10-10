# 工具函数：标准化文本，统一空格、大小写等，便于断言匹配
import re

def extract_all_numbers(text: str) -> list:
    """
    从文本中提取所有浮点数（忽略单位、标点等）
    :param text: 结果描述，如 "托管量为0.00万元，流通量为100000.00万元，集中度为0.01%"
    :return: 数值列表，如 [0.0, 100000.0, 0.01]
    """
    cleaned_text = text.replace(",", "")
    # matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)", cleaned_text)
    matches = re.findall(r"(-?\d+(?:\.\d+)?)", cleaned_text)
    return [float(m) for m in matches]

# ✅ 检查点名称映射到主数值索引位置（0 表示取第一个数值）
CHECKPOINT_VALUE_INDEX = {
    "债券投资规模检查": 0,
    "债券可用检查": 0,
    "基金可用检查": 0,
    "单券集中度": 2,
    "流通量检查": 1,
    "单基金持仓规模检查": 0,
    "组合基金持仓规模检查": 0,
    "对手方黑白名单检查": 0,
    "投资总规模检查": 0
}

def extract_number(text: str, check_point_name: str) -> float:
    """
    按照检查点名称，从文本中提取主数值用于断言比对
    :param text: 结果描述，如 "托管量为0.00万元，流通量为100000.00万元，集中度为0.01%"
    :param check_point_name: 风控检查点，如 "单券集中度检查"
    :return: 提取的主数值（float），如 0.01
    """
    numbers = extract_all_numbers(text)
    idx = CHECKPOINT_VALUE_INDEX.get(check_point_name.strip(), 0)
    return numbers[idx] if len(numbers) > idx else None
    print(
        f"📌 [提取日志] 检查点={check_point_name} | 提取全部数值={numbers} | 使用索引={idx} | 结果={numbers[idx] if len(numbers) > idx else 'None'}")

def normalize_text(text: str) -> str:
    """
    规范化文本：转小写、去空格、替换中文括号
    """

    if not isinstance(text, str):
        text = str(text)
    # 替换中文括号为英文括号
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r'\s+', '', text).strip().lower()