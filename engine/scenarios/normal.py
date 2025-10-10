# engine/scenarios/normal.py
"""
Normal 场景（默认编排）
编排：
  对每个 group_key 执行：提交(断言) → 审批(断言) → 入仓(可选)

说明：
  - 自动选择 Single/Multi 执行器：
      · 优先读 checks[0]['指令模式']（'single' / 'multi'）
      · 若为空则根据 form_data_list 条数判断（>1 视为 multi）
"""

from .base import ScenarioBase
from engine.executors.single_executor import SingleExecutor
from engine.executors.multi_executor import MultiExecutor
from engine.entry_dispatcher import confirm_entry
from utils.case_data_utils import extract_business_type


def choose_executor_by_group(group: dict):
    """
    根据元数据选择单/多指令执行器。
    优先读取 checks[0]['指令模式']；
    若未声明，则以 form_data_list 的条数作为回退判断。
    """
    declared_mode = (group.get("checks", [{}])[0].get("指令模式") or "").strip().lower()
    if declared_mode == "multi":
        return MultiExecutor()
    if declared_mode == "single":
        return SingleExecutor()
    # 回退：看 form_data_list 的条数
    is_multi = len(group.get("form_data_list", [])) > 1
    return MultiExecutor() if is_multi else SingleExecutor()


# === utils: 兼容单/多指令，稳健取得“预期风控点数量” =========================
def _expected_check_count(group: dict) -> int:
    """
    取预期风控点数量，兼容以下来源（按优先级）：
      1) form_data 为 dict → 读 form_data['risk_check_count']
      2) form_data 为 list → 读第一条里带有 risk_check_count 的值
      3) 组上直挂的 'risk_check_count'
      4) 兜底：用 checks 的条数
    """
    raw = None
    fd = group.get("form_data")

    if isinstance(fd, dict):
        raw = fd.get("risk_check_count")
    elif isinstance(fd, list):
        for e in fd:
            if isinstance(e, dict) and e.get("risk_check_count") not in (None, "", "nan", "NaN"):
                raw = e.get("risk_check_count")
                break

    if raw in (None, "", "nan", "NaN"):
        raw = group.get("risk_check_count")

    if raw in (None, "", "nan", "NaN"):
        raw = len(group.get("checks", []) or [])

    try:
        return int(float(raw))
    except Exception:
        # 最后再兜底一次，保证返回 int
        return int(len(group.get("checks", []) or []))


class NormalScenario(ScenarioBase):
    name = "normal"

    def run(self, context, grouped_data, group_keys):
        all_assertions, failed_group_keys, generated_approvals = [], [], []

        for group_key in group_keys:
            group = grouped_data[group_key]

            # ★ 修复：expected_count 对多指令(list) 兼容，不再对 list 调用 .get()
            expected_count = _expected_check_count(group)

            # 选择执行器
            executor = choose_executor_by_group(group)

            # === DEBUG: 打印执行器选择依据 + form_data 形态 + 预期数量 =========
            declared_mode_dbg = (group.get("checks", [{}])[0].get("指令模式") or "").strip().lower()
            fdl_dbg = group.get("form_data_list", []) or []
            fd_dbg = group.get("form_data")
            if isinstance(fd_dbg, list):
                fd_shape = f"list[{len(fd_dbg)}]"
            elif isinstance(fd_dbg, dict):
                fd_shape = "dict"
            else:
                fd_shape = type(fd_dbg).__name__

            print(
                "[EXECUTOR] 组={gk} | 申明指令模式={declared} | form_data_list条数={fdl} | "
                "form_data形态={shape} | 选择={executor} | 预期风控点数={exp}".format(
                    gk=group_key,
                    declared=declared_mode_dbg or "-",
                    fdl=len(fdl_dbg),
                    shape=fd_shape,
                    executor=type(executor).__name__,
                    exp=expected_count,
                )
            )
            # ===================================================================

            # 提交阶段
            submit_engine, approval_number = executor.run_submit(context, group_key, group, expected_count)
            generated_approvals.append(approval_number)
            all_assertions.extend(submit_engine.assertion_results)

            # 审批阶段
            approve_engine = executor.run_approve(context, group_key, group, expected_count, approval_number)
            all_assertions.extend(approve_engine.assertion_results)

            # 入仓（可选）
            try:
                business_type = extract_business_type(group)
                confirm_entry(context.page, approval_number, business_type)
            except Exception as error:
                print(f"⚠️ 入仓失败或未实现，忽略：{error}")

            # 失败聚合（该组任一检查点失败则记为失败）
            has_failed = any(
                record.get("status") == "❌ 失败" and record.get("group_key") == group_key
                for record in (submit_engine.assertion_results + approve_engine.assertion_results)
            )
            if has_failed:
                failed_group_keys.append(group_key)

        return {
            "assertion_results": all_assertions,
            "failed_groups": failed_group_keys,
            "generated_approvals": generated_approvals,
        }
