# engine/scenario_router.py
# -*- coding: utf-8 -*-
"""
scenario_router.py — 场景路由与分组
职责：
  - pick_scenario_name：优先 ENV[SCENARIO] → Excel[场景类型] → 默认 'normal'
  - group_by_pair_id：将同一“配对ID”的组聚合为一个执行单元；未填配对的各自单独执行
  - run_scenario：根据场景名调用具体 Scenario.run()
"""

import os
from typing import Dict, List
from .scenarios.base import ScenarioContext
from .scenarios.normal import NormalScenario
from .scenarios.a_b_approve_a import ABApproveAScenario
from .scenarios.approve_only import ApproveOnlyScenario

SCENARIOS = {
    "normal": NormalScenario(),
    "A-B-approveA": ABApproveAScenario(),
    "approveOnly": ApproveOnlyScenario(),
    "214": ABApproveAScenario(),  # 别名
}


# =====================================================
# ✅ 1) 选择场景类型：ENV > Excel > 默认 normal
# =====================================================
def pick_scenario_name(grouped_data: Dict, group_keys: List[str]) -> str:
    """
    决定当前执行使用哪个场景类（如 normal / A-B-approveA）
    优先级：ENV > Excel 中任一组有合法场景类型 > 兜底 normal
    """
    # ✅ ENV 优先
    env_scene = (os.getenv("SCENARIO") or "").strip()
    if env_scene:
        if env_scene in SCENARIOS:
            print(f"🔧 SCENARIO 来自 ENV: {env_scene}")
            return env_scene
        else:
            raise ValueError(f"❌ 无效 SCENARIO='{env_scene}'，应为：{list(SCENARIOS.keys())}")

    # ✅ Excel 场景类型（遍历所有 checks）
    for group_key in group_keys:
        checks = grouped_data.get(group_key, {}).get("checks", [])
        print(f"🔍 检查组 {group_key} 的 checks 列表: "
              f"{[c.get('scene_type') or c.get('场景类型') for c in checks]}")
        for item in checks:
            # ✅ 兼容两种字段名
            scene_value = (item.get("scene_type") or item.get("场景类型") or "").strip()
            if not scene_value:
                continue
            if scene_value in SCENARIOS:
                print(f"📄 SCENARIO 来自 Excel: {scene_value}（组: {group_key}）")
                return scene_value
            else:
                raise ValueError(f"❌ Excel 中无效场景类型：'{scene_value}'，应为：{list(SCENARIOS.keys())}")

    # ✅ 默认
    print("🟡 SCENARIO 默认使用：normal")
    return "normal"


# =====================================================
# ✅ 2) 分组逻辑：按配对ID聚合
# =====================================================
def group_by_pair_id(grouped_data: Dict, group_keys: List[str]) -> List[List[str]]:
    """
    ✅ 改进版：按“配对ID”聚合执行单元
    - 自动把 Excel 里的数值型/空值配对ID 转成字符串
    - 兼容 pair_id / 配对ID 字段
    - 打印每个分组的配对信息
    """
    buckets_by_pair_id, singles = {}, []

    for group_key in group_keys:
        checks = grouped_data[group_key].get("checks", [])

        # ✅ 确保每条 check 都含“场景类型”
        for item in checks:
            if "场景类型" not in item:
                item["场景类型"] = ""

        # ✅ 改进：兼容英文/中文字段名
        raw_pair = ""
        if checks:
            first = checks[0]
            raw_pair = first.get("pair_id") or first.get("配对ID") or ""
        pair_id = str(raw_pair).strip() if raw_pair else ""

        # 🧩 打印调试信息
        print(f"🔗 group_key={group_key} → 配对ID='{pair_id or '无'}'")

        # ✅ 聚合逻辑：有配对ID归入 bucket，否则放入 singles
        if pair_id:
            buckets_by_pair_id.setdefault(pair_id, []).append(group_key)
        else:
            singles.append(group_key)

    # ✅ 打印最终分组结构
    print("🧩 分组结果：")
    print(f"  普通单组(single)：{singles}")
    print(f"  配对组(bucket)：{buckets_by_pair_id}")

    return list(buckets_by_pair_id.values()) + [[k] for k in singles]




# =====================================================
# ✅ 3) 运行对应场景
# =====================================================
def run_scenario(scenario_name: str, context: ScenarioContext, grouped_data: Dict, unit_group_keys: List[str]) -> Dict:
    print(f"🚀 运行场景：{scenario_name} | 单元组: {unit_group_keys}")
    if scenario_name not in SCENARIOS:
        raise ValueError(f"❌ 未注册场景类型: {scenario_name}")
    return SCENARIOS[scenario_name].run(context, grouped_data, unit_group_keys)
