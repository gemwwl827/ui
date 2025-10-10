"""
executors/multi_executor.py — 多指令执行器
适用：
  - 同一 group_key 下存在多条 form_data（或 Excel 指令模式=multi）

流程（提交阶段）：
  1) 导航→新建
  2) 遍历 group['form_data_list']，按“指令序号”排序
     - 每条指令 dispatch 后，根据“操作模式(多个指令)”点击：
       · '加入并继续' → 继续填下一条
       · '加入列表'   → 加入列表后再继续
  3) flow.submit_and_open_risk() → flow.handle_risk_dialogs_and_submit()
  4) 断言（phase="提交"）→ 取审批号

流程（审批阶段）：
  - 与 SingleExecutor 一致：goto_pending_approval() → approve_request(..., phase="审批")

数据要求：
  - form_data_list: List[dict] 且包含：
      · '指令序号'：0..n-1（连续）
      · '操作模式(多个指令)'：'加入并继续' / '加入列表'
"""

from .base import ExecutorBase
from utils.case_data_utils import extract_business_type


class MultiExecutor(ExecutorBase):
    def run_submit(self, context, group_key, group, expected_count):
        business_type = extract_business_type(group)

        # 导航 → 新建
        context.navigator.navigate_to_business(context.page, business_type)
        try:
            context.page.get_by_role("button", name="新建").click()
        except Exception:
            pass

        # 多指令：按指令序号逐条添加
        form_data_list = group.get("form_data_list", [])
        form_data_list = sorted(form_data_list, key=lambda row: int(row.get("指令序号", 0)))

        for instruction in form_data_list:
            payload = {"form_data": instruction, "business_type": business_type}
            context.dispatcher.dispatch(context.page, payload)

            operation_mode = (instruction.get("操作模式(多个指令)") or "加入并继续").strip()
            try:
                if "继续" in operation_mode:
                    context.page.get_by_role("button", name="加入并继续").click()
                else:
                    context.page.get_by_role("button", name="加入列表").click()
            except Exception:
                # 按钮标识不同或已自动加入时，可容错
                pass

        # # 触发风控并提交
        # context.flow.submit_and_open_risk()
        # context.flow.handle_risk_dialogs_and_submit()
        # ✅ 触发风控并提交（统一入口：主提交 + 弹窗处理）
        context.flow.submit_with_risk_popup()
        # 提交阶段断言
        risk_engine = context.engine_cls(group, context.page, context.test_data_file)
        risk_engine.print_and_assert_risk_details_multi(
            expected_checks=group["checks"],
            current_group_key=group_key,
            expected_count=expected_count,
            phase="提交",
        )

        approval_number = context.flow.extract_approval_number()
        return risk_engine, approval_number

    def run_approve(self, context, group_key, group, expected_count, approval_number):
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
