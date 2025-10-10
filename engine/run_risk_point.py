"""
run_risk_point.py — 统一 Runner（单入口驱动）
职责：
  1) 读取 Excel → 按【风控类型 + 执行序号】过滤要执行的用例组（group_key=执行编号-用例编号 或 用例编号）
  2) 构造 ScenarioContext（注入 Page、Navigator、Dispatcher、ApprovalFlow、RiskEngine）
  3) 调用场景路由：选择场景 + 切分执行单元
  4) 执行场景、汇总断言、导出 Allure 报告
"""

import os
import traceback  # ⬅️ 新增：为了打印完整堆栈
from engine.data_loader import load_grouped_test_data
from engine.form_navigator import TradeFormNavigator
from engine.form_dispatcher import FormDispatcher
from engine.approval_flow import ApprovalFlow
from engine.risk_assertion_engine import RiskAssertionEngine
from engine.scenario_router import ScenarioContext, pick_scenario_name, group_by_pair_id, run_scenario
from engine.risk_field_extractor import normalize_text

try:
    from engine.use_case_selector import get_case_ids_by_exec_order
except Exception:
    def get_case_ids_by_exec_order(test_data_file, exec_order):
        return []


# =========================
# ✅ 新增1：把 “用例编号列表” 解析为真实存在的 group_key（支持 3 ↔ 3.0）
# =========================
def _norm_exec_str(v: str) -> str:
    """
    轻量归一化执行序号字符串：
      - '3.0' -> '3'
      - '3'   -> '3'
      - '3.5' -> '3.5'（保留小数）
      - 其他/空 保持原样
    仅用于“匹配/查找”，不会改变任何原始数据。
    """
    s = (str(v) or "").strip()
    if s == "":
        return ""
    try:
        f = float(s); i = int(f)
        return str(i) if abs(f - i) < 1e-9 else s
    except Exception:
        return s


def _build_case_index(grouped: dict):
    """
    构建索引：用例编号 -> [(exec_order原样, group_key), ...]
    例如：
      {'3-323_024': {...}, '3.0-323_024': {...}, '223_024': {...}}
    会生成：
      by_case['323_024'] = [('3', '3-323_024'), ('3.0', '3.0-323_024')]
      by_case['223_024'] = [('', '223_024')]
    """
    by_case = {}
    for gk in grouped.keys():
        if "-" in gk:
            eo, cid = gk.split("-", 1)
            eo = (eo or "").strip()
        else:
            eo, cid = "", gk
        cid = (cid or "").strip()
        by_case.setdefault(cid, []).append((eo, gk))
    return by_case


def _resolve_case_ids_to_group_keys(grouped: dict, exec_case_ids: list, exec_order: str):
    """
    把“用例编号数组”解析为“真实存在的 group_key 数组”：
      - 优先选与 exec_order（归一后）等价的那条（'3' == '3.0'）
      - 若找不到等价项，则退而求其次：取该用例编号的第一条候选
      - 如果该用例编号压根不在 grouped 里，则跳过
    """
    by_case = _build_case_index(grouped)
    want_eo = _norm_exec_str(exec_order)
    resolved = []
    for cid in exec_case_ids:
        cid = (str(cid) or "").strip()
        cand = by_case.get(cid, [])
        if not cand:
            continue  # 这个用例编号不在 grouped 里
        picked = None
        for eo_raw, gk in cand:
            if _norm_exec_str(eo_raw) == want_eo:
                picked = gk
                break
        if not picked:
            picked = cand[0][1]  # 降级用第一条
        resolved.append(picked)
    return resolved


# =========================
# ✅ 新增2：业务类型自检 + 路由校验（并自动回填顶层 business_type）
# =========================
def _ensure_business_type(grouped: dict, group_keys: list):
    """
    若顶层 business_type 为空，则尝试从 form_data 回填：
      - form_data 是 dict：直接读 entry['business_type']
      - form_data 是 list：找第一条非空 entry['business_type']
    """
    patched = []
    for gk in group_keys:
        bundle = grouped.get(gk) or {}
        bt_top = (bundle.get("business_type") or "").strip()
        if bt_top:
            continue
        fd = bundle.get("form_data")
        cand = ""
        if isinstance(fd, dict):
            cand = (fd.get("business_type") or "").strip()
        elif isinstance(fd, list):
            for entry in fd:
                cand = (entry.get("business_type") or "").strip()
                if cand:
                    break
        if cand:
            bundle["business_type"] = cand
            patched.append((gk, cand))
        else:
            print(f"[BT-EMPTY] 组 {gk} 顶层与 form_data 中均未找到 business_type")
    if patched:
        print(f"[BT-PATCH] 顶层 business_type 回填成功：{patched}")


def _validate_routes(grouped: dict, group_keys: list, navigator) -> bool:
    """
    校验 business_type 是否命中导航路由；打印详细问题清单。
    返回 True 表示全部可用；False 表示有问题。
    """
    misses = []
    for gk in group_keys:
        bt = (grouped.get(gk, {}).get("business_type") or "").strip()
        if not bt or bt not in getattr(navigator, "ROUTES", {}):
            misses.append((gk, bt))
    if misses:
        print("❌ 以下组的 business_type 未命中导航路由：")
        for gk, bt in misses:
            print(f"   - group_key={gk!r}, business_type={bt!r}")
        print("🧭 可用业务类型键：", list(getattr(navigator, "ROUTES", {}).keys()))
        return False
    # 额外打印下每组确认
    for gk in group_keys:
        bt = grouped[gk]["business_type"]
        print(f"[BT-OK] {gk} → {bt} → path={navigator.ROUTES.get(bt)}")
    return True


# === 关键：容错取字段（列名可能带空格或命名变体） ===
def _first_field(d: dict, keys: list, fuzzy_keys: list = None):
    # 先尝试精确匹配（去除左右空白）
    for k in list(d.keys()):
        key_norm = str(k).strip()
        if key_norm in keys:
            return d.get(k)
    # 再尝试模糊匹配（key 同时包含所有片段）
    if fuzzy_keys:
        for k in list(d.keys()):
            key_norm = str(k).strip()
            if all(part in key_norm for part in fuzzy_keys):
                return d.get(k)
    return None


def _has_risk_type(bundle: dict, expected_type: str) -> bool:
    """鲁棒匹配：优先读‘风控类型’，读不到则回退到‘检查点名称’包含关键字。"""
    if not expected_type:
        return True
    target = normalize_text(expected_type)

    checks = bundle.get("checks", []) or []
    # 1) 先按“风控类型”列名变体找
    values = []
    for c in checks:
        v = _first_field(
            c,
            keys=["风控类型", "风控点类型", "风险类型"],
            fuzzy_keys=["风", "控", "类"]
        )
        if v:
            values.append(normalize_text(str(v)))
    if values:
        if any(v == target for v in values):
            return True

    # 2) 回退到“检查点名称”模糊包含（比如：单券集中度检查）
    names = []
    for c in checks:
        n = _first_field(
            c,
            keys=["检查点名称", "检查点", "检查项目"],
            fuzzy_keys=["检", "查", "名"]
        )
        if n:
            names.append(normalize_text(str(n)))
    if names:
        return any(target in n for n in names)

    return False


def _debug_dump_columns(grouped_data: dict, sample: int = 2):
    # 打印两组的 checks 的 key 列表，帮助确认列名
    print("🔎 调试：随机抽查 checks 的可用列名：")
    i = 0
    for gk, b in grouped_data.items():
        if i >= sample:
            break
        ck = b.get("checks", []) or []
        if not ck:
            print(f"  - 组 {gk}: checks 为空")
            i += 1
            continue
        cols = set()
        for row in ck:
            cols.update([str(k).strip() for k in row.keys()])
        print(f"  - 组 {gk}: {sorted(cols)}")
        i += 1


def run_risk_point(
    page,
    test_data_file: str,
    risk_type: str,
    exec_order: str = "",
    export_mode: str = "both",   # 🆕 'detail' | 'merged' | 'both' | 'none'
):
    """
    :param export_mode: 导出到 Allure 的模式
                        - 'detail'  仅导出逐行明细（提交/审批各一行）
                        - 'merged'  仅导出合并视图（提交/审批合并为一行）
                        - 'both'    两种都导出（默认）
                        - 'none'    不导出（CI 调试用）
    """
    grouped_data = load_grouped_test_data(test_data_file, "用例库", "风控点")

    # 可选：打印列名调试
    _debug_dump_columns(grouped_data, sample=2)

    match_mode = (os.getenv("RISK_MATCH_MODE") or "lenient").strip().lower()
    print(f"🧩 匹配模式：{match_mode}（strict=先按风控类型过滤；lenient=ExecOrder 优先且风控类型仅告警）")

    # —— ExecOrder 的用例列表（如设置）
    exec_keys = []
    if exec_order:
        exec_keys = [str(x).strip() for x in get_case_ids_by_exec_order(test_data_file, exec_order)]
        print(f"🧮 EXEC_ORDER={exec_order} → 对应用例编号: {exec_keys}")

    # A) 严格模式：先按风控类型过滤（复刻旧逻辑）
    if match_mode == "strict":
        risk_matched = [k for k, b in grouped_data.items() if _has_risk_type(b, risk_type)]
        if not risk_matched:
            print(f"⚠️ 未匹配到风控类型='{risk_type}' 的任何组；请检查列名或值。")
            return [], {}

        if exec_keys:
            # ✅ 关键修复：用例编号 → 真实 group_key（优先匹配 exec_order）
            resolved = _resolve_case_ids_to_group_keys(grouped_data, exec_keys, exec_order)
            if not resolved:
                print(f"⚠️ EXEC_ORDER={exec_order} 未解析到任何可用组；原始用例编号={exec_keys}")
                return [], {}
            # 与风控类型命中集合做交集（并保持选择器顺序）
            group_keys = [k for k in resolved if k in risk_matched]
            if not group_keys:
                print(f"⚠️ 解析到了组但与风控类型不相交。exec={exec_order} → {resolved}；risk匹配={len(risk_matched)}组")
                return [], {}
            # 调试：看看映射
            print(f"[DEBUG] 解析 exec={exec_order} 用例→组: {dict(zip(exec_keys, group_keys))}")
        else:
            group_keys = risk_matched

    # B) 宽松模式：ExecOrder 优先；风控类型仅做校验与告警（保证能跑起来）
    else:
        if exec_keys:
            # ✅ 关键修复：用例编号 → 真实 group_key（优先匹配 exec_order）
            group_keys = _resolve_case_ids_to_group_keys(grouped_data, exec_keys, exec_order)
            if not group_keys:
                print(f"⚠️ EXEC_ORDER={exec_order} 未解析到任何可用组；原始用例编号={exec_keys}")
                return [], {}
            # 风控类型不一致仅告警
            mismatched = [k for k in group_keys if not _has_risk_type(grouped_data[k], risk_type)]
            if mismatched:
                print(f"⚠️ 以下用例与当前风控类型 '{risk_type}' 不一致（仍将执行）：{mismatched}")
            print(f"[DEBUG] 解析 exec={exec_order} 用例→组: {dict(zip(exec_keys, group_keys))}")
        else:
            # 未指定 EXEC_ORDER → 按风控类型过滤
            group_keys = [k for k, b in grouped_data.items() if _has_risk_type(b, risk_type)]
            if not group_keys:
                print(f"⚠️ 未匹配到风控类型='{risk_type}' 的任何组；请检查列名或值。")
                return [], {}

    if not group_keys:
        print(f"⚠️ 无匹配用例: risk_type='{risk_type}', exec_order='{exec_order}'")
        return [], {}

    # ==== ✅ 新增：一次性自检（并回填）====
    # 1) 若顶层 business_type 为空 → 从 form_data 回填
    _ensure_business_type(grouped_data, group_keys)
    # 2) 校验业务类型是否命中导航路由；如有问题直接 Fail（避免“静默不导航”）
    _nav = TradeFormNavigator()
    if not _validate_routes(grouped_data, group_keys, _nav):
        raise RuntimeError("业务类型未命中路由（详见上方 ❌ 列表以及🧭可用键）")

    # 组装上下文 → 场景选择/分组 → 执行
    context = ScenarioContext(
        page=page,
        test_data_file=test_data_file,
        navigator=_nav,                     # ✅ 复用上面的 navigator（已校验过 ROUTES）
        flow=ApprovalFlow(page),
        dispatcher=FormDispatcher(),
        engine_cls=RiskAssertionEngine
    )
    scenario_name = pick_scenario_name(grouped_data, group_keys)
    unit_groups = group_by_pair_id(grouped_data, group_keys)
    print(f"🧭 场景: {scenario_name} | 风控: {risk_type} | 执行单元: {unit_groups}")

    # 汇总所有执行单元的断言与数量统计
    all_assertions = []
    group_failed_map = {}
    all_quantity_summary = []     # 🆕 收集数量对比中间数据

    for unit in unit_groups:
        # run_scenario 期望返回结构：
        #   - assertion_results: List[dict]
        #   - quantity_comparison_summary: List[dict]（若场景里记录了的话）
        # result = run_scenario(scenario_name, context, grouped_data, unit)
        try:
            result = run_scenario(scenario_name, context, grouped_data, unit)
        except Exception as e:
            # 🔎 关键：打印充足的上下文 + 完整堆栈，随后把异常抛回给上层（pytest 才会把这个序号标记为 hard_failed）
            print("💥 run_scenario 执行异常：")
            print(f"  场景={scenario_name} | 风控={risk_type} | 执行序号={exec_order} | 单元(unit)={unit}")
            # 尝试把该执行单元里每个 group 的业务类型与导航路由也打出来，方便定位是否路由/页面不匹配
            try:
                bt_info = []
                for k in unit:
                    bt = (grouped_data.get(k, {}) or {}).get("business_type", "")
                    path = context.navigator.ROUTES.get(bt, "")
                    bt_info.append((k, bt, path))
                print("  业务/路由明细：", bt_info)
            except Exception:
                pass
            traceback.print_exc()
            raise  # ⚠️ 必须重新抛出，让外层用例把该执行序号记为 hard_failed

        # ---------- ⭐ 给每条记录打上当前“执行序号/风控类型”标签 ----------
        _asserts = result.get("assertion_results", []) or []
        for r in _asserts:
            r.setdefault("exec_order", str(exec_order))     # 执行序号
            r.setdefault("risk_type", str(risk_type))       # 风控类型
        all_assertions.extend(_asserts)
        print(f"🧾 收集断言 {len(_asserts)} 条（已标记 执行序号={exec_order}）")

        # ---------- ⭐ 数量对比中间数据也带上“执行序号” ----------
        _qty = result.get("quantity_comparison_summary", []) or []
        for row in _qty:
            row.setdefault("exec_order", str(exec_order))
            row.setdefault("执行序号", str(exec_order))      # 中文键名，方便中文表头
        all_quantity_summary.extend(_qty)
        # -----------------------------------------------------------------

        # 标记该用例组是否有断言失败
        for k in unit:
            group_failed_map[k] = any(
                r.get("status") == "❌ 失败" and r.get("group_key") == k
                for r in all_assertions
            )

    # === 统一导出到 Allure（在末尾、return 之前）===
    try:
        tmp = RiskAssertionEngine(None, None, None)
        tmp.assertion_results = all_assertions

        if all_quantity_summary:
            tmp.quantity_comparison_summary = all_quantity_summary

        # if export_mode in ("detail", "both") and hasattr(tmp, "export_all_assertions_to_allure"):
        #     tmp.export_all_assertions_to_allure()            # 逐行明细

        if export_mode in ("merged", "both") and hasattr(tmp, "export_all_assertions_to_allure_merged"):
            tmp.export_all_assertions_to_allure_merged()     # 合并视图

        if hasattr(tmp, "export_quantity_comparison_summary"):
            tmp.export_quantity_comparison_summary()         # 风控点数量对比
    except Exception as e:
        print(f"⚠️ Allure 导出失败: {e}")
    # ============================================================

    return all_assertions, group_failed_map
