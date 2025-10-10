"""
executors/single_executor.py — 单指令执行器
流程（提交阶段）：
  1) navigator.navigate_to_business(page, business_type)
  2) 点击【新建】（容错）
  3) dispatcher.dispatch(page, group)           # 一次性填单
  4) flow.submit_and_open_risk()
  5) flow.handle_risk_dialogs_and_submit()
  6) RiskAssertionEngine(...).print_and_assert_risk_details_multi(..., phase="提交")
  7) flow.extract_approval_number()             # 返回审批号

流程（审批阶段）：
  1) flow.goto_pending_approval()
  2) flow.approve_request(approval_number, risk_engine, expected_checks, group_key, expected_count, phase="审批")

备注：
  - 仅处理“单指令”用例；多指令请使用 MultiExecutor
  - 入仓由 Scenario 决定是否调用（不是执行器职责）
"""

from .base import ExecutorBase
from utils.case_data_utils import extract_business_type


class SingleExecutor(ExecutorBase):
    def run_submit(self, context, group_key, group, expected_count):
        business_type = extract_business_type(group)

        # 导航 + 新建
        context.navigator.navigate_to_business(context.page, business_type)
        try:
            context.page.get_by_role("button", name="新建").click()
        except Exception:
            pass

        # ✅ 关键：给调度器一个包含 business_type 的 payload
        dispatch_payload = {
            "business_type": business_type,
            "form_data": group.get("form_data", {})
        }
        context.dispatcher.dispatch(context.page, dispatch_payload)

        # 触发风控 + 提交
        # context.flow.submit_and_open_risk()
        # context.flow.handle_risk_dialogs_and_submit()
        # ✅ 触发风控并提交（统一入口：主提交 + 弹窗处理）
        context.flow.submit_with_risk_popup()

        # 提交阶段断言
        engine = context.engine_cls(group, context.page, context.test_data_file)
        engine.print_and_assert_risk_details_multi(
            expected_checks=group["checks"],
            current_group_key=group_key,
            expected_count=expected_count,
            phase="提交",
        )
        approval_number = context.flow.extract_approval_number()
        return engine, approval_number


    def run_approve(self, context, group_key, group, expected_count, approval_number):
        """审批阶段：进入待办→审批→断言"""
        context.flow.goto_pending_approval()

        risk_engine = context.engine_cls(group, context.page, context.test_data_file)
        context.flow.approve_request(
            approval_number=approval_number,
            risk_engine=risk_engine,
            expected_checks=group["checks"],
            group_key=group_key,
            expected_count=expected_count,
            phase="审批",
        )
        return risk_engine
