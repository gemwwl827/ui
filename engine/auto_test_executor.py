# engine/auto_test_executor.py
# -*- coding: utf-8 -*-
# ✅ 用例统一执行器（模块化版）
# - 不再引用巨无霸页面类
# - 组合式：Navigator(导航) + Dispatcher(填表) + ApprovalFlow(提交/审批)
# - 保留你原有：数据补丁、风险断言、Allure 导出等

import os  # 标准库（有些环境会用到，保留）

from playwright.sync_api import Page  # Playwright Page 类型提示

# ==== 数据补丁相关（照旧保留） ====
from utils.db_dm1 import (                              # 核心资产库打补丁/恢复
    patch_core_asset_record_type,
    restore_core_asset_record_type,
)
from utils.db_ignite_dele1 import (                     # ignite 侧打补丁/恢复
    patch_ignite_record_type_by_sub_request,
    restore_ignite_record_type_by_sub_request,
)

# ==== 业务/执行器依赖 ====
from utils.data_utils import normalize_entry            # 业务名标准化
from engine.form_dispatcher import FormDispatcher       # 选择页面类并调用 fill_form
from engine.risk_assertion_engine import RiskAssertionEngine  # 风控断言引擎
from engine.entry_dispatcher import confirm_entry       # 审批完成后的“入库/确认”动作
from engine.data_loader import load_grouped_test_data   # 读取分组后的测试数据
from engine.approval_flow import ApprovalFlow           # 提交/审批模块（新）
from engine.form_navigator import TradeFormNavigator    # 导航/新建模块（新）

# ❌ 不再需要巨无霸：
# from pages.ficc_ui_case_09_page_bond_risk import InterbankBondTradingPage


class AutoTestExecutor:
    def __init__(self, page: Page, test_data_file: str, exec_order: str = "1"):
        self.page = page                                       # Playwright Page
        self.test_data_file = test_data_file                   # 测试数据 Excel 路径
        self.exec_order = exec_order                           # 执行序号（便于筛选用例）
        self.generated_approval_numbers = []                   # 汇总所有申请单号
        self.all_assertion_results = []                        # 累计所有断言结果
        self.group_number_results = {}                         # 记录每个 group 的通过/失败

        # ✅ 模块化组件（取代巨无霸）
        self.navigator = TradeFormNavigator()                  # 导航 & 新建
        self.approval = ApprovalFlow(page)                     # 提交/审批

        # ❌ 旧：实例化巨无霸并导航
        # self.add_project = InterbankBondTradingPage(page, test_data_file)
        # self.add_project.navigate()

    def run(self):
        # ✅ Step 1: 读取目标用例编号（按执行序号筛选）
        from engine.use_case_selector import get_case_ids_by_exec_order  # 延迟导入，避免循环依赖
        target_group_keys = get_case_ids_by_exec_order(                  # 取符合本次执行序号的用例编号
            test_data_file=self.test_data_file,
            exec_order=self.exec_order
        )
        target_group_keys = [str(x).strip() for x in target_group_keys]  # 统一转字符串并去空格
        print(f"\n🎯 执行序号 = {self.exec_order}，匹配到用例编号: {target_group_keys}")

        # ✅ Step 2: 加载测试数据（包含 form_data + checks）
        grouped_data = load_grouped_test_data(                           # 从 Excel 读取分组数据
            test_data_file=self.test_data_file,
            form_sheet="用例库",                                          # 表单数据所在 sheet
            check_sheet="风控点"                                         # 风控断言所在 sheet
        )

        valid_group_keys = list(grouped_data.keys())                     # 实际存在的组
        group_keys_to_run = [k for k in target_group_keys if k in valid_group_keys]  # 取交集
        print(f"✅ 实际执行 group_keys: {group_keys_to_run}")

        if not group_keys_to_run:                                        # 没有可执行用例则退出
            print("⚠️ 没有匹配到任何 group_key，提前退出")
            return

        # ✅ Step 3: 逐组执行
        dispatcher = FormDispatcher()                                    # 调度器（全流程复用一个即可）
        for group_key in group_keys_to_run:                              # 遍历每个分组
            print(f"🧭 当前 group_key: {group_key}")
            group = grouped_data[group_key]                              # 本组数据（含 form_data / checks）
            form_data = group["form_data"]                               # 取出表单数据（可能是 dict 或 list）

            # ---- 兼容单指令/多指令两种结构，提取补丁字段 ----
            if isinstance(form_data, list):                              # 多指令：取第 1 条的公共字段
                sub_case_no = form_data[0].get("sub_case_no", "")
                request_no = form_data[0].get("request_no", "")
                sub_request_no = form_data[0].get("sub_request_no", "")
                patch_flag = (form_data[0].get("patch_flag") or "").strip().upper()
            else:                                                        # 单指令：直接从 dict 取值
                sub_case_no = form_data.get("sub_case_no", "")
                request_no = form_data.get("request_no", "")
                sub_request_no = form_data.get("sub_request_no", "")
                patch_flag = (form_data.get("patch_flag") or "").strip().upper()

            need_patch = patch_flag == "Y"                               # 是否需要打补丁
            original_type = original_type_ignite = None                  # 记录原值，便于 finally 恢复

            try:
                # ✅ Step 3.1: （可选）打补丁
                if need_patch and sub_request_no:                        # 仅当需要补丁且有子单号
                    original_type = patch_core_asset_record_type(sub_request_no, 0)              # 核心资产
                    original_type_ignite = patch_ignite_record_type_by_sub_request(sub_request_no, 0)  # ignite

                # ✅ Step 3.2: 业务名标准化（便于映射）
                entry = normalize_entry(form_data)                       # 归一化 business_type 等

                # ✅ Step 3.3: 导航到业务页 + 如需点击“新建”
                biz = entry["business_type"]                             # 当前业务类型（如“银行间债券借贷”）
                self.navigator.navigate_to_business(self.page, biz)      # 跳业务 URL，并等待页面就绪
                self.navigator.try_create_new_request(self.page, biz)    # 部分业务需要点“新建”
                group.setdefault("business_type", biz)                   # 确保 group 中带上业务名

                # ✅ Step 3.4: 填表（调度器 → 页面类.fill_form）
                dispatcher.dispatch(self.page, group)                    # 直接把 Page + group 交给调度器

                # ✅ Step 3.5: 点击“提交”打开风控弹窗（不立即确认）
                self.approval.submit_with_risk_popup(wait_ms=800)          # 轻等 0.8s 后点提交，弹出风控

                # ✅ Step 3.6: 风控断言（在风控弹窗里读取并断言）
                risk_engine = RiskAssertionEngine(                       # 实例化断言引擎
                    test_data=group,
                    page_obj=self.page,
                    test_data_file=self.test_data_file
                )
                expected_count = int(float(entry.get("risk_check_count") or 0))  # 期望风控条数
                risk_engine.print_and_assert_risk_details_multi(         # 执行多条断言
                    expected_checks=group["checks"],
                    current_group_key=group_key,
                    expected_count=expected_count
                )
                self.all_assertion_results.extend(risk_engine.assertion_results)  # 汇总断言结果

                # 🆕 检测“禁止” → 跳过 Step 3.7~3.10（提交/审批/入库），继续下一组
                from engine.risk_field_extractor import normalize_text   # 🆕 局部引入，避免顶部污染
                has_forbidden = any(                                     # 🆕
                    (r.get("group_key") == group_key) and
                    (normalize_text(r.get("actual_result")) == "禁止") and
                    (r.get("阶段") in (None, "", "提交"))
                    for r in risk_engine.assertion_results
                )
                if has_forbidden:                                        # 🆕
                    print(f"⛔ 检测到 {group_key} 存在【禁止】 → 已断言记录，跳过提交/审批")
                    # 🆕 确保该组在统计里有记录（失败与否仍以断言结果为准）
                    self.group_number_results[group_key] = {
                        "failed": any(
                            (r.get("group_key") == group_key) and (r.get("status") == "❌ 失败")
                            for r in risk_engine.assertion_results
                        )
                    }
                    # 🆕 尝试关闭风控弹窗，避免遮挡后续
                    try:
                        if hasattr(self.approval, "close_risk_dialog"):
                            self.approval.close_risk_dialog()
                    except Exception as _e:
                        print(f"⚠️ 关闭风控弹窗失败（可忽略）：{_e}")
                    continue  # 🆕 直接进入下一组

                # ✅ Step 3.7: 提交风控弹窗（忽略警告/风控信息提交/兜底提交）
                self.approval.handle_risk_dialogs_and_submit()           # 真正提交至流程

                # ✅ Step 3.8: 读取申请单号
                approval_number = self.approval.extract_approval_number()  # 提取“申请单编号”
                self.generated_approval_numbers.append(approval_number)    # 保存编号

                # ✅ Step 3.9: 进入审批列表 → 完成审批（含审批阶段风控断言）
                self.approval.goto_pending_approval()                    # 打开“审批列表-待办审批”
                self.approval.approve_request(                           # 在列表里按编号审批
                    approval_number=approval_number,
                    risk_engine=risk_engine,
                    expected_checks=group.get('checks'),
                    group_key=group_key,
                    expected_count=expected_count,
                    phase="审批",
                )

                # ✅ Step 3.10: 审批完成后的入库/确认（沿用你现有函数）
                #    这里需要一个拥有 .page 属性的对象；ApprovalFlow 本身就有，所以直接传它
                confirm_entry(self.approval, approval_number, biz)

                # ✅ 统计本组是否有断言失败
                self.group_number_results[group_key] = {
                    "failed": any(
                        r["status"] == "❌ 失败" and r.get("group_key") == group_key
                        for r in risk_engine.assertion_results
                    )
                }

                print(f"✅ 全流程通过: {group_key}-{sub_case_no}")        # 成功打点

            except Exception as e:
                print(f"❌ 流程失败: {group_key}-{sub_case_no}，错误信息: {e}")  # 失败打点
                self.group_number_results[group_key] = {"failed": True}   # 🆕 确保失败组有标记

            finally:
                # ✅ Step 3.F: 恢复补丁（不影响后续用例）
                if need_patch and sub_request_no and original_type is not None:
                    restore_core_asset_record_type(sub_request_no, original_type)
                if need_patch and sub_request_no and original_type_ignite is not None:
                    restore_ignite_record_type_by_sub_request(sub_request_no, original_type_ignite)

                # ✅ Step 3.F2: 回到“新建”入口（为下一笔做准备）
                try:
                    self.approval.reset_to_new_request_page()            # 默认跳回银行间现券新建入口
                except Exception as e:
                    print(f"⚠️ 新建页重置失败（可忽略，后续导航会覆盖）：{e}")
                # 🆕 每个 group 执行完后，立即导出一次 Allure 报告，避免报错导致断言丢失
                try:
                    temp_engine = RiskAssertionEngine(None, None, None)
                    temp_engine.assertion_results = self.all_assertion_results
                    temp_engine.export_all_assertions_to_allure_merged()
                    print(f"📦 已导出 Allure 报告（group={group_key} 累计结果）")
                except Exception as e:
                    print(f"⚠️ Allure 导出失败（group={group_key}）：{e}")
                # if group_key not in self.group_number_results:           # 🆕 兜底：确保有记录
                #     self.group_number_results[group_key] = {"failed": False}

        # ✅ Step 4: 导出断言结果到 Allure（维持你原有写法）
        try:
            temp_engine = RiskAssertionEngine(None, None, None)          # 临时引擎，用于导出
            temp_engine.assertion_results = self.all_assertion_results   # 注入累计结果
            #temp_engine.export_all_assertions_to_allure()                # 生成 Allure 附件/报告(旧的导出)
            # ✅ 改成调用合并版
            temp_engine.export_all_assertions_to_allure_merged()
            print("📦 Allure 报告已导出")
        except Exception as e:
            print(f"⚠️ 报告导出失败: {e}")

        # ✅ Step 5: 统一失败判断（组维度）
        failed_groups = [k for k, v in self.group_number_results.items() if v["failed"]]  # 取失败组
        if failed_groups:
            raise AssertionError(f"❌ 以下用例组存在断言失败: {failed_groups}")          # 组维度失败

        # ✅ Step 6: 统一失败判断（断言条目维度）
        if any(r["status"] == "❌ 失败" for r in self.all_assertion_results):             # 若有任一失败条目
            raise AssertionError("⚠️ 检测到风控断言失败，详见控制台及报告")                 # 抛出失败

        print("✅ 所有断言通过")                                                          # 结束语

    def run_by_exec_order(self, exec_order: str):
        """✅ 统一入口，供 runner.py 调用指定执行序号"""
        self.exec_order = exec_order                                 # 覆盖执行序号
        self.run()                                                   # 复用 run
        self.failed_groups = [k for k, v in self.group_number_results.items() if v["failed"]]  # 留存失败组
