# scenarios/a_b_approve_a.py — 214 特殊编排（A → B → 回批 A）
# 使用方式：
#   - 在 Excel “风控点”中，为需要成对执行的两组设置相同的“配对ID”，并把“场景类型”设置为：A-B-approveA
# 编排顺序：
#   1) 组 A：提交（断言“提交”），不审批
#   2) 组 B：提交（断言“提交”） + 审批（断言“审批”）
#   3) 回头审批 组 A（断言“审批”）

from .base import ScenarioBase
from engine.executors.single_executor import SingleExecutor  # 单指令执行器
from engine.executors.multi_executor import MultiExecutor    # 多指令执行器


def choose_executor_by_group(group: dict):
    # ✅ 根据当前分组（group）的结构判断使用哪种执行器（单指令 or 多指令）

    declared_mode = (group.get("checks", [{}])[0].get("指令模式") or "").strip().lower()
    # 方式一：显式配置“指令模式”为 multi / single

    if declared_mode == "multi":
        return MultiExecutor()
    if declared_mode == "single":
        return SingleExecutor()

    # 方式二：通过 form_data_list 的长度判断是否多指令
    is_multi = len(group.get("form_data_list", [])) > 1
    return MultiExecutor() if is_multi else SingleExecutor()


class ABApproveAScenario(ScenarioBase):
    name = "A-B-approveA"  # ✅ 场景名，用于注册调度

    def run(self, context, grouped_data, group_keys):
        # ✅ 场景主入口：按顺序执行提交 A → 提交 B → 审批 B → 审批 A

        if len(group_keys) < 2:
            # 若分组数不足两个，直接返回空结果（场景不成立）
            return {"assertion_results": [], "failed_groups": ["<need>=2"], "generated_approvals": []}

        group_key_a, group_key_b = group_keys[0], group_keys[1]  # ✅ 提取两个分组的 key
        all_assertions, failed_group_keys, generated_approvals = [], [], []  # 初始化结果收集器

        group_a = grouped_data[group_key_a]
        group_b = grouped_data[group_key_b]

        # ✅ 获取预期风控数量（用于断言对比）
        expected_count_a = int(float(group_a["form_data"].get("risk_check_count", 0) or 0))
        expected_count_b = int(float(group_b["form_data"].get("risk_check_count", 0) or 0))

        # ✅ 为 A/B 两组分别选择合适的执行器
        executor_a = choose_executor_by_group(group_a)
        executor_b = choose_executor_by_group(group_b)

        # ✅ 阶段一：提交 A（不审批）
        submit_engine_a, approval_number_a = executor_a.run_submit(
            context, group_key_a, group_a, expected_count_a
        )
        generated_approvals.append(approval_number_a)                      # 保存 A 的审批编号
        all_assertions.extend(submit_engine_a.assertion_results)           # 收集断言结果

        # ✅ 阶段二：提交 B + 审批 B
        submit_engine_b, approval_number_b = executor_b.run_submit(
            context, group_key_b, group_b, expected_count_b
        )
        all_assertions.extend(submit_engine_b.assertion_results)
        generated_approvals.append(approval_number_b)

        approve_engine_b = executor_b.run_approve(
            context, group_key_b, group_b, expected_count_b, approval_number_b
        )
        all_assertions.extend(approve_engine_b.assertion_results)

        # ✅ 阶段三：回头审批 A
        approve_engine_a = executor_a.run_approve(
            context, group_key_a, group_a, expected_count_a, approval_number_a
        )
        all_assertions.extend(approve_engine_a.assertion_results)

        # ✅ 聚合失败组：如果任意执行环节失败，则标记该组为失败组
        for gk, engines in [
            (group_key_a, [submit_engine_a, approve_engine_a]),
            (group_key_b, [submit_engine_b, approve_engine_b]),
        ]:
            any_failed = any(
                record["status"] == "❌ 失败" and record["group_key"] == gk
                for engine in engines
                for record in engine.assertion_results
            )
            if any_failed:
                failed_group_keys.append(gk)

        # ✅ 返回场景执行结果（断言结果、失败组、审批编号）
        return {
            "assertion_results": all_assertions,
            "failed_groups": list(set(failed_group_keys)),
            "generated_approvals": generated_approvals,
        }
