# cases/test_risk.py
import os
from pathlib import Path
import pytest, allure
from playwright.sync_api import Page

# ✅ 仍然用你现有的能力：解析风控类型 & 执行序号计划
from engine.run_risk_point import run_risk_point
from engine.use_case_selector import plan_exec_orders, parse_risk_types

# 测试数据文件
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "test_data_01.xlsx"


# =========================
# NEW 1/3: 生成参数对 (risk_type, exec_order)
# =========================
def _risk_exec_pairs():
    """
    根据环境变量拼出所有要跑的 (risk_type, exec_order) 组合：
      - RISK_TYPES: None/'all'/'A,B,C'  -> 通过 parse_risk_types 解析成列表
      - EXEC_PLAN : None/'all'/'1,2'    -> 对每个 risk_type 调用 plan_exec_orders 得到序号列表
    """
    # risk_plan = os.getenv("RISK_TYPES")  # None / "all" / "单券集中度, 债券可用检查"
    # exec_plan = os.getenv("EXEC_PLAN") or os.getenv("EXEC_ORDER", "1")

    # risk_plan = os.getenv("RISK_TYPES", "all")
    # exec_plan = os.getenv("EXEC_PLAN") or os.getenv("EXEC_ORDER") or "all"  # 执行序号默认 all
    #调试
    risk_plan = "单券集中度"  # ✅ 写死风控类型
    exec_plan = "3"  # ✅ 写死执行序号

    risk_types = parse_risk_types(str(DATA_FILE), risk_plan)
    print(f"[DEBUG] RISK_TYPES plan={risk_plan!r} -> {risk_types}")
    print(f"[DEBUG] EXEC plan={exec_plan!r}")

    pairs = []
    for rt in risk_types:
        orders = plan_exec_orders(str(DATA_FILE), rt, exec_plan)  # ['1'] / ['1','2'] / ...
        if not orders:
            print(f"[WARN] 风控类型 {rt} 未解析到任何执行序号，已跳过")
            continue
        for od in orders:
            pairs.append((rt, od))  # 一个用例就是一对 (风控类型, 执行序号)

    # 打印一下最终的参数矩阵，便于确认并行粒度
    print(f"[DEBUG] Param matrix -> {pairs}")
    return pairs


# =========================
# CHANGED 2/3: 两个参数一起参数化（并行单位 = 一条 pair）
# =========================
@pytest.mark.parametrize(
    "risk_type, exec_order",
    _risk_exec_pairs(),
    ids=lambda p: f"{p[0]}|序号{p[1]}" if isinstance(p, (list, tuple)) else str(p)
)
def test_risk_by_type(login_save_auth, page: Page, risk_type: str, exec_order: str):
    """
    每条测试 == 一个 风控类型 × 执行序号
    配合 pytest-xdist：`pytest -n auto` 即可并行把这些“条目”分发到多个 worker。
    """
    # ===== SELF-CHECK: 确认当前会话已登录 =====
    page.goto("/", wait_until="networkidle")  # 有 base_url，"/" 就会去 10.60.1.49:8091/
    allure.attach(page.url, name="URL-after-state", attachment_type=allure.attachment_type.TEXT)
    if "/login" in page.url:
        pytest.fail(f"仍在登录页：{page.url}（storage_state 未生效或登录失败）")



    # Allure 元信息
    # allure.dynamic.feature("产品风控自动化")
    allure.dynamic.story(risk_type)
    allure.dynamic.title(f"{risk_type}｜执行序号 {exec_order}")

    failed_groups = {}       # {group_key: True} —— 断言失败的“用例组”
    hard_failed_orders = []  # 直接异常的执行序号（页面或流程出错）

    # =========================
    # CHANGED 3/3: 不再 for 循环 orders；每条用例只跑“当前 exec_order”
    # =========================
    with allure.step(f"执行序号组 {exec_order}"):
        try:
            _, gf = run_risk_point(page, str(DATA_FILE), risk_type, exec_order)
            # 收集断言失败的组（不中断本条用例的其它步骤）
            for k, v in (gf or {}).items():
                if v:
                    failed_groups[k] = True
        except Exception as e:
            hard_failed_orders.append(str(exec_order))
            allure.attach(str(e), name=f"ORDER-{exec_order}-异常", attachment_type=allure.attachment_type.TEXT)
            # 尽量留现场，避免并行时文件名冲突：带上风控+序号
            try:
                page.screenshot(path=f"test-results/{risk_type}-{exec_order}-error.png", full_page=True)
            except Exception:
                pass

    # 只就本条参数（该风控类型 × 该执行序号）给出结果
    if failed_groups or hard_failed_orders:
        pytest.fail(f"{risk_type} 失败：执行序号={hard_failed_orders}; 编号组={list(failed_groups)}")
