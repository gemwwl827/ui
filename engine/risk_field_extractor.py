import re

# ============================
# ✅ 风控断言字段提取工具模块
# ============================

# ✅ 通用工具：标准化文本（统一括号、去空格、转小写）
def normalize_text(text: str) -> str:
    """标准化文本：统一括号、去空格、转小写"""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r'\s+', '', text).strip().lower()


# ✅ 检查点名称 → 内部字段名映射（用于从 form_data 中取值）
CHECKPOINT_FIELD_MAP = {
    normalize_text("单券集中度检查"): "bond_concentration",
    normalize_text("流通量检查"): "bond_liquidity",
    normalize_text("债券持仓检查"): "bond_position",
    normalize_text("债券投资总规模检查"): "bond_total_investment",
    normalize_text("投资总规模检查"): "bond_total_investment",
    normalize_text("单券集中度检查1"): "bond_concentration",
    normalize_text("债券可用检查"): "bond_available",
    # 可根据需要继续扩展
}

# ✅ 字段名 → Excel 列标题映射（用于从 Excel 中提取值构造 form_data）
FORM_FIELD_TO_EXCEL_COLUMN = {
    "bond_concentration": "集中度(%)",
    "bond_total_investment": "债券投资总规模(万)",
    "bond_liquidity": "流通量(万)",
    "bond_position": "债券持仓量(万)",
    "bond_available":"债券持仓量(万)",
    # 可以根据你 Excel 表格的实际列名继续加
}


class RiskDataExtractor:

    @staticmethod
    def extract_all_numbers(text: str) -> list:
        """从字符串中提取所有浮点数"""
        cleaned_text = text.replace(",", "")
        matches = re.findall(r"(-?\d+(?:\.\d+)?)", cleaned_text)
        return [float(m) for m in matches]

    @staticmethod
    def get_value_from_form(form_data: dict, check_point_name: str) -> float:
        """
        ✅ 从结构化表单数据中提取预期值（如 form_data 中的 'bond_concentration'）
        :param form_data: 当前用例的表单结构数据
        :param check_point_name: 检查点名称
        :return: 提取到的浮点值或 None
        """
        key = normalize_text(check_point_name)
        field = CHECKPOINT_FIELD_MAP.get(key)

        if not field:
            print(f"⚠️ 无匹配字段：{check_point_name} (标准化: {key})")
            return None

        try:
            value = form_data.get(field)
            if isinstance(value, str):
                value = value.strip().replace("%", "").replace(",", "")
            if not value:
                return None
            return float(value)
        except Exception as e:
            print(f"❌ 字段值转换失败：字段={field}, 值={value}, 错误={e}")
            return None

    @staticmethod
    def get_expected_value_from_check(expected: dict, form_data: dict) -> float:
        """
        ✅ 提取预期值：直接从 expected['expected_value'] 中读取，不再回退 form_data 字段
        """
        check_point_name = normalize_text(expected.get("check_point_name", ""))
        print(f"🧩 当前检查点名称: {check_point_name}")

        expected_raw = expected.get("expected_value", "")
        print(f"🔍 从 Excel 风控点中读取的 expected_value = '{expected_raw}'")

        # ✅ 去除 %, 万, 逗号，统一为 float 可解析格式
        expected_raw = str(expected_raw).replace("%", "").replace("万", "").replace(",", "").strip()

        try:
            value = float(expected_raw) if expected_raw else None
            print(f"✅ 最终转换为 float 的值: {value}")
            return value
        except Exception as e:
            print(f"❌ 预期值转换失败：原始值={expected_raw}, 错误={e}")
            return None

    @staticmethod
    def extract_column_value_by_header(row, header_map, column_name: str) -> str:
        """
        ✅ 提取页面表格中指定列的值（通过列名动态获取索引）
        """
        try:
            col_index = header_map.get(column_name)
            if col_index is None:
                print(f"⚠️ 未找到列名：{column_name}")
                return ""
            cell = row.locator("td").nth(col_index)
            return cell.inner_text().strip()
        except Exception as e:
            print(f"❌ 提取列值失败: {column_name}, 错误: {e}")
            return ""

    @staticmethod
    def extract_number(text: str, check_point_name: str) -> float:
        """
        ✅ 核心方法：根据检查点名称，从描述中提取实际值（用于与预期值比较）
        :param text: 风控检查项描述（如“集中度为3.34%，未超过阈值”）
        :param check_point_name: 检查点名称（如“单券集中度检查”）
        :return: 提取的浮点数值（如 3.34）
        """
        numbers = RiskDataExtractor.extract_all_numbers(text)
        index_map = {
            normalize_text("债券投资规模检查"): 0,
            normalize_text("债券可用检查"): 0,
            normalize_text("基金可用检查"): 0,
            normalize_text("单券集中度检查"): 2,
            normalize_text("流通量检查"): 1,
            normalize_text("单基金持仓规模检查"): 0,
            normalize_text("组合基金持仓规模检查"): 0,
            normalize_text("对手方黑白名单检查"): 0,
            normalize_text("投资总规模检查"): 0,
        }

        idx = index_map.get(normalize_text(check_point_name), 0)
        return numbers[idx] if len(numbers) > idx else None
