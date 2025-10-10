"""
scenarios/approve_only.py — 审批中专项（仅审批阶段断言）
适用：
  - 复核历史待办、不创建新单
  - Excel：场景类型=approveOnly，或“阶段”只写“审批”
"""

from .base import ScenarioBase


class ApproveOnlyScenario(ScenarioBase):
    name = "approveOnly"

    def run(self, context, grouped_data, group_keys):
        all_assertions, failed_group_keys, generated_approvals = [], [], []

        for group_key in group_keys:
            group = grouped_data[group_key]
            expected_count = int(float(group["form_data"].get("risk_check_count", 0) or 0))
            approval_number = group["form_data"].get("approval_number")  # 可改为你的定位方式

            if not approval_number:
                # 也可在这里实现一个查找：context.flow.find_latest_approval_by_filters(...)
                print(f"⚠️ 组 {group_key} 缺少审批号，跳过")
                continue

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
            all_assertions.extend(risk_engine.assertion_results)
            generated_approvals.append(approval_number)

            if any(r["status"] == "❌ 失败" and r["group_key"] == group_key for r in risk_engine.assertion_results):
                failed_group_keys.append(group_key)

        return {
            "assertion_results": all_assertions,
            "failed_groups": failed_group_keys,
            "generated_approvals": generated_approvals,
        }
"""
scenarios/approve_only.py — 审批中专项（仅审批阶段断言）
适用：
  - 复核历史待办、不创建新单
  - Excel：场景类型=approveOnly，或“阶段”只写“审批”
"""

from .base import ScenarioBase


class ApproveOnlyScenario(ScenarioBase):
    name = "approveOnly"

    def run(self, context, grouped_data, group_keys):
        all_assertions, failed_group_keys, generated_approvals = [], [], []

        for group_key in group_keys:
            group = grouped_data[group_key]
            expected_count = int(float(group["form_data"].get("risk_check_count", 0) or 0))
            approval_number = group["form_data"].get("approval_number")  # 可改为你的定位方式

            if not approval_number:
                # 也可在这里实现一个查找：context.flow.find_latest_approval_by_filters(...)
                print(f"⚠️ 组 {group_key} 缺少审批号，跳过")
                continue

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
            all_assertions.extend(risk_engine.assertion_results)
            generated_approvals.append(approval_number)

            if any(r["status"] == "❌ 失败" and r["group_key"] == group_key for r in risk_engine.assertion_results):
                failed_group_keys.append(group_key)

        return {
            "assertion_results": all_assertions,
            "failed_groups": failed_group_keys,
            "generated_approvals": generated_approvals,
        }
