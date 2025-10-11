# engine/risk_assertion_engine.py
# -*- coding: utf-8 -*-
import re
from tabulate import tabulate  # 表格格式化输出

# ✅ 引入字段提取工具类 + 标准化函数 + 映射表
from engine.risk_field_extractor import RiskDataExtractor, normalize_text, CHECKPOINT_FIELD_MAP
from utils.number_utils import extract_number_smart

# ======================== 跳过标记（Excel「检查结果」列） ========================
# 只要 Excel 「检查结果」是下列任意值，就不会做页面比对，但仍写入 Allure 表格：
SKIP_RESULT_MARKERS = {"不触发", "不检查", "跳过", "NA", "N/A", "N\\A", "--"}
# ===============================================================================


# ========================= 🆕 辅助：安全转 int =========================
def _to_int_or_none(v):
    try:
        if v is None or str(v).strip() == "":
            return None
        return int(float(str(v).strip()))
    except Exception:
        return None
# =====================================================================


class RiskAssertionEngine:
    """
    风控断言引擎：负责执行页面风控断言、风控点数量比对、结果导出等核心操作
    """

    def __init__(self, test_data, page_obj, test_data_file):
        """
        初始化 RiskAssertionEngine 实例
        """
        self.test_data = test_data
        self.page_obj = page_obj
        self.test_data_file = test_data_file
        self.assertion_results = []
        self.failed_asserts = []
        self.quantity_comparison_summary = []
        self.failed_cases_summary = []

    # def print_and_assert_risk_details_multi(
    #         self,
    #         expected_checks: list,
    #         current_group_key: str,
    #         expected_count: int,
    #         phase: str = "提交",  # ✅ 阶段参数，默认“提交”，审批阶段传 "审批"
    # ):
    #     """
    #     遍历页面所有风控检查项，与预期断言结果逐项对比
    #     """
    #     self.page_obj.wait_for_timeout(5000)
    #
    #     # ------------------------- 🆕 新增：结果型检查点名单（只对比检查结果，不做数值断言） -------------------------
    #     RESULT_ONLY_CHECKPOINTS = {
    #         "组合DV01检查",
    #         "债券投资范围检查",
    #         "永续债检查",
    #         "反向交易检查",
    #         "同向交易检查",
    #         "债券黑名单检查",
    #         "债券主承销商检查",
    #     }
    #
    #     # --------------------------------------------------------------------------------------------------
    #
    #     # ===================== 预处理：Excel 标记跳过的检查点 =====================
    #     skip_items, normal_items = [], []
    #     for item in expected_checks:
    #         expected_result_raw = normalize_text(item.get("check_result") or item.get("expected_result") or "")
    #         if expected_result_raw in SKIP_RESULT_MARKERS:
    #             skip_items.append(item)
    #         else:
    #             normal_items.append(item)
    #
    #     for item in skip_items:
    #         self.assertion_results.append({
    #             "group_key": current_group_key,
    #             "check_point_name": item.get("check_point_name", ""),
    #             "actual_result": "不检查",
    #             "actual_description": "Excel 标记为不触发/不检查/跳过，未执行页面比对。",
    #             "expected_value": "--",
    #             "actual_value": "--",
    #             "status": "⏭ 跳过",
    #             "阶段": phase,
    #         })
    #
    #     expected_checks = normal_items
    #     # ========================================================================
    #
    #     # ✅ 取到最新的弹窗（风控弹窗）
    #     overlays = self.page_obj.locator("div.el-overlay:visible")
    #     last_overlay = overlays.nth(overlays.count() - 1)
    #
    #     # ✅ 表头
    #     header_cells = last_overlay.locator("thead tr th")
    #     header_count = header_cells.count()
    #     header_texts = [header_cells.nth(j).inner_text().strip() for j in range(header_count)]
    #
    #     # ✅ 数据行
    #     rows = last_overlay.locator("table.el-table__body tbody tr")
    #     count = rows.count()
    #     print(f"📊 当前页面风控检查项数量：{count}")
    #
    #     for i in range(count):
    #         row = rows.nth(i)
    #         cells = row.locator("td")
    #         cell_texts = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
    #         print(f"🧩 第 {i + 1} 行实际列数: {cells.count()}，内容为: {cell_texts}")
    #
    #         headers = ["申请单编号", "检查结果", "检查点名称", "检查组合", "资产代码", "资产简称", "阈值", "计算值",
    #                    "结果描述"]
    #         print(f"\n🧾 第 {i + 1} 行检查项明细：")
    #         print(tabulate([cell_texts], headers=headers, tablefmt="grid"))
    #
    #         check_point_name = normalize_text(cell_texts[2])
    #         actual_result = normalize_text(cell_texts[1])  # ✅ 取检查结果列
    #         actual_description = cell_texts[8]
    #
    #         matched = False
    #         for expected in expected_checks:
    #             expected_name = normalize_text(expected["check_point_name"])
    #             if expected_name != check_point_name:
    #                 continue
    #
    #             expected_result = normalize_text(expected.get("check_result"))
    #
    #             try:
    #                 # ===== 1) 按阶段取预期值 =====
    #                 if phase == "提交":
    #                     expected_value_raw = str(
    #                         expected.get("提交阶段预期值") or expected.get("expected_value", "")).strip()
    #                 elif phase == "审批":
    #                     expected_value_raw = str(
    #                         expected.get("审批阶段预期值") or expected.get("expected_value", "")).strip()
    #                 else:
    #                     expected_value_raw = str(expected.get("expected_value", "")).strip()
    #
    #                 expected_value = extract_number_smart(expected_value_raw)
    #
    #                 # ------------------------- 🆕 新增：兜底逻辑（检查结果断言模式） -------------------------
    #                 if expected_value is None or check_point_name in RESULT_ONLY_CHECKPOINTS:
    #                     expected_text = normalize_text(expected.get("check_result", ""))
    #                     actual_text = normalize_text(actual_result)
    #                     print(f"🧮 文本断言模式：实际={actual_text}, 预期={expected_text}")
    #
    #                     assert actual_text == expected_text, f"❌ 文本不一致：预期={expected_text}, 实际={actual_text}"
    #
    #                     self.assertion_results.append({
    #                         "group_key": current_group_key,
    #                         "check_point_name": cell_texts[2],
    #                         "actual_result": actual_text,
    #                         "actual_description": actual_description,
    #                         "expected_value": expected_text,
    #                         "actual_value": actual_text,
    #                         "status": "✅ 成功",
    #                         "阶段": phase,
    #                     })
    #                     matched = True
    #                     break
    #                 # ---------------------------------------------------------------------
    #
    #                 # ===== 2) 默认逻辑：取【计算值】做数值断言 =====
    #                 if "计算值" in header_texts:
    #                     calc_index = header_texts.index("计算值")
    #                 else:
    #                     raise Exception("❌ 表格中未找到 '计算值' 列，请确认前端页面结构是否变更")
    #
    #                 actual_value_raw = cell_texts[calc_index].strip()
    #                 actual_value = extract_number_smart(actual_value_raw)
    #
    #                 # 兜底从描述提取
    #                 remark = ""
    #                 if actual_value is None:
    #                     fallback = extract_number_smart(actual_description)
    #                     if fallback is not None:
    #                         actual_value = fallback
    #                         remark = "实际值来自结果描述"
    #
    #                 # 状态一致性
    #                 assert actual_result == expected_result, f"❌ 状态不一致：预期={expected_result}, 实际={actual_result}"
    #
    #                 # 数值断言
    #                 assert expected_value is not None and actual_value is not None, (
    #                     f"❌ 无法提取数值进行断言：expected={expected_value}, actual={actual_value}"
    #                 )
    #
    #                 print(f"✅ 检查点 {cell_texts[2]} 数值断言通过")
    #                 self.assertion_results.append({
    #                     "group_key": current_group_key,
    #                     "check_point_name": cell_texts[2],
    #                     "actual_result": actual_result,
    #                     "actual_description": actual_description,
    #                     "expected_value": expected_value,
    #                     "actual_value": actual_value,
    #                     "status": "✅ 成功",
    #                     "阶段": phase,
    #                     "备注": remark,
    #                 })
    #
    #             except AssertionError as e:
    #                 print(str(e))
    #                 self.failed_asserts.append(str(e))
    #                 self.assertion_results.append({
    #                     "group_key": current_group_key,
    #                     "check_point_name": cell_texts[2],
    #                     "actual_result": actual_result,
    #                     "actual_description": actual_description,
    #                     "expected_value": expected_value_raw if expected_value is None else expected_value,
    #                     "actual_value": actual_result if expected_value is None else actual_value,
    #                     "status": "❌ 失败",
    #                     "阶段": phase,
    #                 })
    #             matched = True
    #             break
    #
    #         if not matched:
    #             msg = f"🚫 非本轮指令的检查点，已跳过断言：页面={check_point_name}（行号={i}）"
    #             print(msg)
    #             self.assertion_results.append({
    #                 "group_key": current_group_key,
    #                 "check_point_name": check_point_name,
    #                 "actual_result": actual_result,
    #                 "actual_description": actual_description,
    #                 "expected_value": "--",
    #                 "actual_value": cell_texts[7].strip(),
    #                 "status": "🚫 不适用",
    #                 "阶段": phase,
    #                 "备注": "白名单命中但指令序号不匹配",
    #             })
    #
    #     # ✅ 数量对比收集保持不变
    #     expected_point_names = self.process_expected_checkpoints(expected_checks, expected_count)
    #     actual_point_names = []
    #     for i in range(count):
    #         row = rows.nth(i)
    #         cells = row.locator("td")
    #         point_name = normalize_text(cells.nth(2).inner_text().strip())
    #         actual_point_names.append(point_name)
    #
    #     if not hasattr(self, "quantity_comparison_summary"):
    #         self.quantity_comparison_summary = []
    #
    #     self.quantity_comparison_summary.append({
    #         "用例编号": current_group_key,
    #         "类型": "预期",
    #         "数量": len(expected_point_names),
    #         "风控点": "、".join(expected_point_names),
    #     })
    #     self.quantity_comparison_summary.append({
    #         "用例编号": current_group_key,
    #         "类型": "实际",
    #         "数量": len(actual_point_names),
    #         "风控点": "、".join(actual_point_names),
    #     })

    def print_and_assert_risk_details_multi(
            self,
            expected_checks: list,
            current_group_key: str,
            expected_count: int,
            phase: str = "提交",  # ✅ 阶段参数，默认“提交”，审批阶段传 "审批"
    ):
        """
        遍历页面所有风控检查项，与预期断言结果逐项对比
        """
        self.page_obj.wait_for_timeout(5000)

        # ------------------------- 🆕 新增：风控点断言模式映射表（名称取检查点名称） -------------------------
        CHECKPOINT_ASSERTION_MODE = {
            # 数值型（取计算值列）
            "单券集中度检查": "numeric",
            "单券集中度检查_多指令": "numeric",
            "单券集中度检查_审批中": "numeric",
            "债券投资总规模检查": "numeric",

            "组合DV01检查": "numeric",
            "组合久期检查": "numeric",
            "组合债券浮盈检查": "numeric",
            "债券交易价格偏离检查": "numeric",

            # 描述型（取结果描述）
            "债券可用检查": "description",


            # 结果型（只看检查结果）
            "债券投资范围检查": "result",
            "永续债检查": "result",
            "反向交易检查": "result",
            "同向交易检查": "result",
            "债券黑名单检查": "result",
            "债券主承销商检查": "result",
        }
        # ---------------------------------------------------------------------------

        # ------------------------- 原逻辑保留 -------------------------
        RESULT_ONLY_CHECKPOINTS = {
            "组合DV01检查",
            "债券投资范围检查",
            "永续债检查",
            "反向交易检查",
            "同向交易检查",
            "债券黑名单检查",
            "债券主承销商检查",
        }

        skip_items, normal_items = [], []
        for item in expected_checks:
            expected_result_raw = normalize_text(item.get("check_result") or item.get("expected_result") or "")
            if expected_result_raw in SKIP_RESULT_MARKERS:
                skip_items.append(item)
            else:
                normal_items.append(item)

        for item in skip_items:
            self.assertion_results.append({
                "group_key": current_group_key,
                "check_point_name": item.get("check_point_name", ""),
                "actual_result": "不检查",
                "actual_description": "Excel 标记为不触发/不检查/跳过，未执行页面比对。",
                "expected_value": "--",
                "actual_value": "--",
                "status": "⏭ 跳过",
                "阶段": phase,
            })

        expected_checks = normal_items
        # ------------------------------------------------------------------

        overlays = self.page_obj.locator("div.el-overlay:visible")
        last_overlay = overlays.nth(overlays.count() - 1)
        header_cells = last_overlay.locator("thead tr th")
        header_count = header_cells.count()
        header_texts = [header_cells.nth(j).inner_text().strip() for j in range(header_count)]

        rows = last_overlay.locator("table.el-table__body tbody tr")
        count = rows.count()
        print(f"📊 当前页面风控检查项数量：{count}")

        for i in range(count):
            row = rows.nth(i)
            cells = row.locator("td")
            cell_texts = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
            print(f"🧩 第 {i + 1} 行实际列数: {cells.count()}，内容为: {cell_texts}")

            headers = ["申请单编号", "检查结果", "检查点名称", "检查组合", "资产代码", "资产简称", "阈值", "计算值",
                       "结果描述"]
            print(f"\n🧾 第 {i + 1} 行检查项明细：")
            print(tabulate([cell_texts], headers=headers, tablefmt="grid"))

            check_point_name = normalize_text(cell_texts[2])
            actual_result = normalize_text(cell_texts[1])
            actual_description = cell_texts[8]

            matched = False
            for expected in expected_checks:
                expected_name = normalize_text(expected["check_point_name"])
                if expected_name != check_point_name:
                    continue

                expected_result = normalize_text(expected.get("check_result"))

                try:
                    if phase == "提交":
                        expected_value_raw = str(
                            expected.get("提交阶段预期值") or expected.get("expected_value", "")).strip()
                    elif phase == "审批":
                        expected_value_raw = str(
                            expected.get("审批阶段预期值") or expected.get("expected_value", "")).strip()
                    else:
                        expected_value_raw = str(expected.get("expected_value", "")).strip()

                    expected_value = extract_number_smart(expected_value_raw)

                    # 🆕 根据风控点类型决定断言逻辑模式
                    mode = CHECKPOINT_ASSERTION_MODE.get(check_point_name, "numeric")
                    print(f"🧭 当前检查点断言模式: {mode}")  # ✅ 修改：输出当前模式

                    # ============================ 🧩 模式分支 ============================

                    if mode == "result":  # ✅ 修改：结果型，只比对检查结果
                        assert actual_result == expected_result, f"❌ 检查结果不一致：预期={expected_result}, 实际={actual_result}"
                        self.assertion_results.append({
                            "group_key": current_group_key,
                            "check_point_name": cell_texts[2],
                            "actual_result": actual_result,
                            "actual_description": actual_description,
                            "expected_value": expected_result,
                            "actual_value": actual_result,
                            "status": "✅ 成功",
                            "阶段": phase,
                        })

                    elif mode == "description":  # ✅ 修改：描述型，从描述中提取数值
                        actual_value = extract_number_smart(actual_description)
                        print(f"🧮 描述提取值：实际={actual_value}，预期={expected_value}")
                        assert expected_value is not None and actual_value is not None, (
                            f"❌ 无法提取数值进行断言：expected={expected_value}, actual={actual_value}"
                        )
                        tolerance = 1e-8
                        assert abs(actual_value - expected_value) < tolerance, (
                            f"❌ 描述数值不一致：预期={expected_value}, 实际={actual_value}"
                        )
                        self.assertion_results.append({
                            "group_key": current_group_key,
                            "check_point_name": cell_texts[2],
                            "actual_result": actual_result,
                            "actual_description": actual_description,
                            "expected_value": expected_value,
                            "actual_value": actual_value,
                            "status": "✅ 成功",
                            "阶段": phase,
                            "备注": "结果描述提取",
                        })

                    else:  # ✅ 修改：默认 numeric 模式（取计算值列）
                        if "计算值" in header_texts:
                            calc_index = header_texts.index("计算值")
                        else:
                            raise Exception("❌ 表格中未找到 '计算值' 列，请确认前端页面结构是否变更")

                        actual_value_raw = cell_texts[calc_index].strip()
                        actual_value = extract_number_smart(actual_value_raw)

                        if actual_value is None:
                            fallback = extract_number_smart(actual_description)
                            if fallback is not None:
                                actual_value = fallback

                        print(f"🧪 获取预期值 => 检查点={check_point_name}，最终值={expected_value}")
                        print(f"🧮 提取值：页面实际值 = {actual_value}，预期值 = {expected_value}")

                        assert actual_result == expected_result, f"❌ 状态不一致：预期={expected_result}, 实际={actual_result}"
                        assert expected_value is not None and actual_value is not None, (
                            f"❌ 无法提取数值进行断言：expected={expected_value}, actual={actual_value}"
                        )
                        tolerance = 1e-8
                        assert abs(actual_value - expected_value) < tolerance, (
                            f"❌ 数值不一致：预期={expected_value}, 实际={actual_value}"
                        )
                        # ✅ 修改：新增断言成功提示
                        print(f"✅ 检查点 {check_point_name} 全部通过")
                        self.assertion_results.append({
                            "group_key": current_group_key,
                            "check_point_name": cell_texts[2],
                            "actual_result": actual_result,
                            "actual_description": actual_description,
                            "expected_value": expected_value,
                            "actual_value": actual_value,
                            "status": "✅ 成功",
                            "阶段": phase,
                        })

                    # ============================ END ============================

                except AssertionError as e:
                    print(str(e))
                    self.failed_asserts.append(str(e))
                    self.assertion_results.append({
                        "group_key": current_group_key,
                        "check_point_name": cell_texts[2],
                        "actual_result": actual_result,
                        "actual_description": actual_description,
                        "expected_value": expected_value_raw if expected_value is None else expected_value,
                        "actual_value": actual_result if expected_value is None else actual_value,
                        "status": "❌ 失败",
                        "阶段": phase,
                    })
                matched = True
                break

            if not matched:
                msg = f"🚫 非本轮指令的检查点，已跳过断言：页面={check_point_name}（行号={i}）"
                print(msg)
                self.assertion_results.append({
                    "group_key": current_group_key,
                    "check_point_name": check_point_name,
                    "actual_result": actual_result,
                    "actual_description": actual_description,
                    "expected_value": "--",
                    "actual_value": cell_texts[7].strip(),
                    "status": "🚫 不适用",
                    "阶段": phase,
                    "备注": "白名单命中但指令序号不匹配",
                })

        # ✅ 数量比对逻辑保持不变
        expected_point_names = self.process_expected_checkpoints(expected_checks, expected_count)
        actual_point_names = []
        for i in range(count):
            row = rows.nth(i)
            cells = row.locator("td")
            point_name = normalize_text(cells.nth(2).inner_text().strip())
            actual_point_names.append(point_name)

        if not hasattr(self, "quantity_comparison_summary"):
            self.quantity_comparison_summary = []

        self.quantity_comparison_summary.append({
            "用例编号": current_group_key,
            "类型": "预期",
            "数量": len(expected_point_names),
            "风控点": "、".join(expected_point_names),
        })
        self.quantity_comparison_summary.append({
            "用例编号": current_group_key,
            "类型": "实际",
            "数量": len(actual_point_names),
            "风控点": "、".join(actual_point_names),
        })

    # 清洗和补足 Excel 中预期的风控点数量，保持与实际对齐
    def process_expected_checkpoints(self, expected_checks: list, expected_count: int):
        cleaned = []
        for check in expected_checks:
            name = normalize_text(check.get("check_point_name", ""))
            if not name:
                name = "❌ 缺失"
            cleaned.append(name)

        while len(cleaned) < expected_count:
            cleaned.append("❌ 缺失")
        if len(cleaned) > expected_count:
            cleaned = cleaned[:expected_count]
        return cleaned

    # 将数量对比结果以表格方式展示在 Allure 报告中（Markdown + HTML）
    def export_quantity_comparison_summary(self):
        """
        ✅ 导出风控数量对比（预期 vs 实际），以 HTML 表格展示至 Allure 报告
        """
        if not hasattr(self, "quantity_comparison_summary") or not self.quantity_comparison_summary:
            return

        import pandas as pd
        import allure

        # ⭐ 新增：把每个用例编号对应的执行序号记下来，便于放到最终表头
        exec_order_map = {}
        for row in self.quantity_comparison_summary:
            exec_order_map[row["用例编号"]] = str(row.get("执行序号") or row.get("exec_order") or "")

        # ✅ 整理每组用例的预期与实际风控点列表
        grouped = {}  # key: 用例编号 → { "预期": [...], "实际": [...] }
        for row in self.quantity_comparison_summary:
            key = row["用例编号"]
            if key not in grouped:
                grouped[key] = {"预期": [], "实际": []}

            if "风控点列表" in row:
                grouped[key][row["类型"]] = [p.strip() for p in row["风控点列表"] if p.strip()]
            else:
                grouped[key][row["类型"]] = [p.strip() for p in row["风控点"].split("、") if p.strip()]

        # ✅ 构建比对行（两行一组：预期、实际）
        aligned_rows = []
        for group_key, data in grouped.items():
            expected = data.get("预期", [])
            actual = data.get("实际", [])
            max_len = max(len(expected), len(actual))

            while len(expected) < max_len:
                expected.append("")
            while len(actual) < max_len:
                actual.append("")

            # ✅ 实际值按预期顺序重排
            actual_reordered = []
            actual_copy = actual.copy()
            for point in expected:
                if point in actual_copy:
                    actual_reordered.append(point)
                    actual_copy.remove(point)
                else:
                    actual_reordered.append("❌ 缺失")
            if actual_copy:
                actual_reordered.extend(actual_copy)

            # ✅ 构造字典行（风控点1，风控点2...）
            row_expected = {
                "执行序号": exec_order_map.get(group_key, ""),  # ⭐ 新增
                "用例编号": group_key,
                "类型": "预期",
                "风控点数量": len(expected),
            }
            row_actual = {
                "执行序号": exec_order_map.get(group_key, ""),  # ⭐ 新增
                "用例编号": group_key,
                "类型": "实际",
                "风控点数量": len(actual_reordered),
            }
            for i in range(max_len):
                row_expected[f"风控点{i + 1}"] = expected[i]
                row_actual[f"风控点{i + 1}"] = actual_reordered[i]

            aligned_rows.append(row_expected)
            aligned_rows.append(row_actual)

        # ✅ DataFrame 并替换 NaN → ""
        df = pd.DataFrame(aligned_rows).fillna("")

        # 🔧 调整列顺序（把“执行序号”放到最前）
        cols = list(df.columns)
        for first in ["执行序号", "用例编号", "类型"]:
            if first in cols:
                cols.remove(first)
                cols.insert(0, first)
        df = df[cols]

        # ✅ 转为 HTML 表格
        html_table = df.to_html(index=False, escape=False, justify="center", border=1)

        # ✅ 封装为带样式的 HTML 并附加至 Allure
        html_wrapper = f"""
        <html><head><meta charset='utf-8'><style>
        body {{ font-family: Arial, sans-serif; }}
        h2 {{ color: #2e6c80; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
        th, td {{ border: 1px solid #ccc; padding: 6px; text-align: center; }}
        th {{ background-color: #e8f4ff; }}
        td {{ white-space: pre-line; }}
        </style></head><body>
        <h2>📊 风控数量预期 vs 实际 对比表（顺序对齐）</h2>
        {html_table}
        </body></html>
        """
        allure.attach(html_wrapper, name="风控数量对比(表格)", attachment_type=allure.attachment_type.HTML)

    def export_all_assertions_to_allure(self):
        """
        ✅ 导出所有断言（成功 + 失败 + 跳过），以 HTML 表格形式展示：
        - 显示“执行序号”列（第一列）和横幅
        - 『跳过』将以 ⏭ 图标展示
        """
        import pandas as pd
        import allure

        df = pd.DataFrame(self.assertion_results)
        if df.empty:
            print("⚠️ 无断言记录，跳过导出")
            return

        # ⭐ 新增：横幅所需的执行序号集合
        unique_orders = []
        if "exec_order" in df.columns:
            unique_orders = sorted({str(x) for x in df["exec_order"].dropna().astype(str).tolist() if str(x).strip()})

        df["is_failed"] = df["status"].apply(lambda x: "失败" in str(x))

        # ✅ 中文列标题映射（⭐ 新增 exec_order）
        col_name_map = {
            "exec_order": "执行序号",   # ⭐ 新增
            "risk_type": "风控类型",    # ⭐ 可选：如果上游写入了 risk_type 也能显示
            "group_key": "用例编号",
            "check_point_name": "检查点",
            "status": "断言状态",
            "actual_result": "检查状态",
            "expected_value": "预期值",
            "actual_value": "实际值",
            "备注": "备注说明"
        }

        # ✅ 展示顺序（⭐ 把执行序号放第一列；风险类型放第二列，按需可删）
        headers = [
            "exec_order",     # ⭐ 新增
            "risk_type",      # ⭐ 可选（没有这个字段也不会报错）
            "group_key",
            "check_point_name",
            "status",
            "actual_result",
            "expected_value",
            "actual_value",
            "备注"
        ]

        # 🔧 只保留实际存在的列，避免 KeyError
        headers = [h for h in headers if h in col_name_map and h in df.columns or h in ("exec_order", "risk_type")]
        header_html = "".join(f"<th>{col_name_map.get(col, col)}</th>" for col in headers)

        # ⭐ 横幅（执行序号）
        order_banner = ""
        if unique_orders:
            order_banner = f"<div class='order-banner'>执行序号：{', '.join(unique_orders)}</div>"

        html_rows = ""
        for _, row in df.iterrows():
            row_class = "failed-row" if row["is_failed"] else ""
            row_html = ""
            for col in headers:
                value = row.get(col, "")
                # pandas NA 处理
                try:
                    import pandas as _pd  # 避免局部未引
                    if _pd.isna(value):
                        value = ""
                except Exception:
                    pass

                if col == "status":
                    # ✅ 支持『跳过』态
                    s = str(value)
                    if "失败" in s:
                        value = "❌ 失败"
                    elif "跳过" in s:
                        value = "⏭ 跳过"
                    else:
                        value = "✅ 成功"
                elif col in ["expected_value", "actual_value"]:
                    if value in [None, "nan", "NaN"]:
                        value = "--"
                    else:
                        value = str(value).strip()
                row_html += f"<td>{value}</td>"
            html_rows += f"<tr class='{row_class}'>{row_html}</tr>"

        html_table = f"""
        <html><head><meta charset='utf-8'><style>
        body {{
            font-family: Arial, sans-serif;
        }}
        h2 {{
            color: #333;
        }}
        .order-banner {{              /* ⭐ 新增：执行序号横幅样式 */
            margin: 8px 0 12px 0;
            padding: 8px 12px;
            display: inline-block;
            background: #eef7ff;
            border: 1px solid #cfe6ff;
            border-radius: 6px;
            font-weight: 600;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 6px;
            text-align: center;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .failed-row {{
            background-color: #f8d7da;
        }}
        </style></head><body>
        <h2>📋 风控断言详情表格（含图标与中文状态，失败高亮）</h2>
        {order_banner}   <!-- ⭐ 新增：执行序号横幅 -->
        <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{html_rows}</tbody>
        </table>
        </body></html>
        """

        allure.attach(html_table, name="📋 风控断言详情表格（失败高亮）", attachment_type=allure.attachment_type.HTML)
        print("📤 已将风控断言表附加到 Allure 报告")

    def record_failed_case_summary(self, sub_case: str, request_no: str, biz_no: str, checkpoint: str, expected: float,
                                   actual: float, result_desc: str):
        self.failed_cases_summary.append({
            "sub_case": sub_case,
            "request_no": request_no,
            "biz_no": biz_no,
            "checkpoint": checkpoint,
            "expected": expected,
            "actual": actual,
            "result_desc": result_desc
        })

    # === 🆕 新增：提交/审批 合并视图导出到 Allure（每个用例编号+检查点 只占一行） ===
    def export_all_assertions_to_allure_merged(self):
        import pandas as pd
        import allure

        data = self.assertion_results or []
        if not data:
            print("⚠️ 无断言记录（merged），跳过导出")
            return

        def _norm_phase(x: str) -> str:
            x = str(x or "").strip()
            if x in ("审批", "提交"):
                return x
            return "提交"

        def _iconize_assert(status: str) -> str:
            s = str(status)
            if "失败" in s:
                return "❌ 失败"
            if "跳过" in s:
                return "⏭ 跳过"
            return "✅ 成功"

        # ⭐ 收集执行序号集合，用于横幅
        orders_set = set()

        # 聚合：key=(exec_order, group_key, check_point_name)
        merged: dict[tuple, dict] = {}
        for r in data:
            exec_order = str(r.get("exec_order", "")).strip()
            orders_set.add(exec_order)
            key = (exec_order,
                   str(r.get("group_key", "")).strip(),
                   str(r.get("check_point_name", "")).strip())
            phase = _norm_phase(r.get("阶段"))

            if key not in merged:
                merged[key] = {
                    "执行序号": exec_order,        # ⭐ 新增
                    "用例编号": key[1],
                    "检查点": key[2],
                    # 提交阶段
                    "提交检查状态": "",
                    "提交断言": "",
                    "提交预期值": "",
                    "提交实际值": "",
                    # 审批阶段
                    "审批检查状态": "",
                    "审批断言": "",
                    "审批预期值": "",
                    "审批实际值": "",
                }

            if phase == "提交":
                merged[key]["提交检查状态"] = str(r.get("actual_result", "") or "").strip()
                merged[key]["提交断言"] = _iconize_assert(r.get("status", ""))
                merged[key]["提交预期值"] = "" if r.get("expected_value") in (None, "nan", "NaN") else str(r.get("expected_value"))
                merged[key]["提交实际值"] = "" if r.get("actual_value")   in (None, "nan", "NaN") else str(r.get("actual_value"))
            else:  # 审批
                merged[key]["审批检查状态"] = str(r.get("actual_result", "") or "").strip()
                merged[key]["审批断言"] = _iconize_assert(r.get("status", ""))
                merged[key]["审批预期值"] = "" if r.get("expected_value") in (None, "nan", "NaN") else str(r.get("expected_value"))
                merged[key]["审批实际值"] = "" if r.get("actual_value")   in (None, "nan", "NaN") else str(r.get("actual_value"))

        # 生成 DataFrame
        df = pd.DataFrame(merged.values())

        # 合并断言状态：任一阶段失败 → 标红
        def _merged_fail(row) -> bool:
            return ("失败" in row.get("提交断言", "")) or ("失败" in row.get("审批断言", ""))

        df["_is_failed"] = df.apply(_merged_fail, axis=1)

        # 展示列顺序（“执行序号”置顶）
        headers = [
            "执行序号", "用例编号", "检查点",
            "提交检查状态", "提交断言", "提交预期值", "提交实际值",
            "审批检查状态", "审批断言", "审批预期值", "审批实际值",
        ]

        # 生成 HTML 表格
        def _th(c): return f"<th>{c}</th>"
        header_html = "".join(_th(h) for h in headers)

        # ⭐ 横幅（执行序号）
        orders_list = sorted([o for o in orders_set if o])
        order_banner = ""
        if orders_list:
            order_banner = f"<div class='order-banner'>执行序号：{', '.join(orders_list)}</div>"

        html_rows = ""
        for _, row in df.iterrows():
            row_class = "failed-row" if row["_is_failed"] else ""
            tds = []
            for col in headers:
                val = row.get(col, "")
                try:
                    import pandas as _pd
                    if _pd.isna(val):
                        val = ""
                except Exception:
                    pass
                tds.append(f"<td>{val}</td>")
            html_rows += f"<tr class='{row_class}'>{''.join(tds)}</tr>"

        html = f"""
        <html><head><meta charset="utf-8"><style>
        body {{ font-family: Arial, sans-serif; }}
        .order-banner {{
            margin: 8px 0 12px 0;
            padding: 8px 12px;
            display: inline-block;
            background: #eef7ff;
            border: 1px solid #cfe6ff;
            border-radius: 6px;
            font-weight: 600;
        }}
        table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
        th, td {{ border: 1px solid #ccc; padding: 6px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .failed-row {{ background-color: #f8d7da; }}
        </style></head><body>
        <h2>📋 风控断言（提交/审批 合并视图）</h2>
        {order_banner}   <!-- ⭐ 新增横幅 -->
        <table>
          <thead><tr>{header_html}</tr></thead>
          <tbody>{html_rows}</tbody>
        </table>
        </body></html>
        """

        allure.attach(html, name="📋 风控断言（合并视图）", attachment_type=allure.attachment_type.HTML)
        print("📤 已将【合并视图】附加到 Allure 报告")
