# engine/use_case_selector.py
# -*- coding: utf-8 -*-
"""
用途：
- 读取 Excel「风控点」sheet，按【风控类型】与【执行序号】筛选出要执行的用例编号。
- 支持“多风控类型计划”（RISK_TYPES）与“执行序号计划”（EXEC_PLAN / EXEC_ORDER）。
- 做了名称归一与别名映射，避免“债券可用 / 债券可用检查 / 单券集中度检查”等写法差异导致匹配失败。

对外主要函数：
- get_case_ids_by_exec_order(test_data_file, exec_order)
- list_exec_orders_for_risk_type(test_data_file, risk_type)
- list_all_risk_types(test_data_file)
- plan_exec_orders(test_data_file, risk_type, plan)
- parse_risk_types(test_data_file, plan)

依赖：
- pandas（读 Excel）
- openpyxl（pandas 的 Excel 引擎）
- engine.risk_field_extractor.normalize_text（做文本规整）
"""

from __future__ import annotations

import re
import pandas as pd
from engine.risk_field_extractor import normalize_text


# =============================================================================
# 基础工具：执行序号、列名选择、风控名规整/别名映射
# =============================================================================

def _norm_exec_token(v: object) -> str:
    """
    把执行序号统一成字符串形式（用于比较）：
    - 1 / "1" / 1.0 / "1.0" 统一成 "1"
    - 3.5 / "3.50" 统一成 "3.5"
    - NaN / 空 → 返回 ""
    """
    if pd.isna(v):
        return ""
    s = str(v).strip().replace("\u3000", " ")  # 全角空格 → 半角
    try:
        f = float(s)
        # 是整数就去掉小数部分，否则去掉末尾多余的 0
        return str(int(f)) if f.is_integer() else re.sub(r"\.?0+$", "", str(f))
    except Exception:
        # 非数字（比如 "A组"）原样返回
        return s


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    从 DataFrame 中选择一个符合期望的列名：
    - 先精确匹配（去空白）
    - 如果失败，再做一次“模糊匹配”：列名里包含“执行”且（包含“序”或“编号”）
    """
    cols = {c.strip(): c for c in df.columns}

    # 精确命中
    for key in candidates:
        if key in cols:
            return cols[key]

    # 模糊命中（用于“执行序号/执行编号”一类的多写法）
    for c in cols:
        c0 = c.strip()
        if "执行" in c0 and ("序" in c0 or "编号" in c0):
            return cols[c]
    return None


def _to_risk_label(s: str) -> str:
    """
    把“风控名称/检查点名称”规整成更简洁的展示标签：
    - 去掉全角空白
    - 去掉常见后缀：检查点/检查规则/风控检查/风控规则/检查/校验/规则/风控
    例：'单券集中度检查' → '单券集中度'
        '债券可用检查'   → '债券可用'
    """
    s = str(s or "").strip().replace("\u3000", " ")
    if not s:
        return ""
    for suf in ("检查点", "检查规则", "风控检查", "风控规则", "检查", "校验", "规则", "风控"):
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    return s.strip()


# 别名映射：把各种写法收敛到“标准名”（标准名也走 normalize_text 规整）
# 注意：字典的 key、value 都会走 normalize_text（小写/去空白/全角半角）后再比较
RISK_TYPE_ALIASES: dict[str, str] = {
    # 单券集中度

    "债券投资总规模检查": "债券投资总规模检查",
    "组合DV01检查": "组合DV01检查",
    "组合债券浮盈检查": "组合债券浮盈检查",
    "组合久期检查": "组合久期检查",
    "债券交易价格偏离检查": "债券交易价格偏离检查",
    "债券投资范围检查": "债券投资范围检查",
    "永续债检查": "永续债检查",
    "反向交易检查": "反向交易检查",
    "同向交易": "同向交易检查",
    "债券黑名单检查": "债券黑名单检查",
    "债券主承销商检查": "债券主承销商检查",


    # 债券可用检查

}


def _norm_risk_name(x: str) -> str:
    """
    风控名称归一：
    1) 先 normalize_text（去空白/大小写/全角等）
    2) 再做别名收敛（RISK_TYPE_ALIASES）
    """
    s = normalize_text(str(x or "").strip())
    # 先看是否配置了别名，命中则替换为“标准名”（别名也走 normalize_text）
    mapped = RISK_TYPE_ALIASES.get(s)
    return mapped if mapped else s


# =============================================================================
# 公开函数：按执行序号取用例、按风控类型列出执行序号、列出全部风控类型
# =============================================================================

def get_case_ids_by_exec_order(
    test_data_file: str,
    exec_order: str,
    check_sheet: str = "风控点",
) -> list[str]:
    """
    按【执行序号/执行编号】返回该组的用例编号列表（保持 Excel 出现顺序）
    - 兼容 1/1.0/“1.0”
    - 列名兼容：执行序号 / 执行编号
    """
    try:
        df = pd.read_excel(test_data_file, sheet_name=check_sheet, engine="openpyxl")
        df.columns = df.columns.str.strip()
        df.ffill(inplace=True)  # 合并单元格前向填充
    except Exception as e:
        print(f"❌ 无法读取风控点 sheet: {e}")
        return []

    order_col = _pick_col(df, ["执行序号", "执行编号"])
    case_col = _pick_col(df, ["用例编号"])
    if not order_col or not case_col:
        print("❌ 风控点 sheet 缺少列：执行序号/执行编号 或 用例编号")
        return []

    # 归一执行序号 + 用例编号
    df["_order_norm"] = df[order_col].map(_norm_exec_token)
    df["_case_id"] = df[case_col].astype(str).str.strip()

    token = _norm_exec_token(exec_order)
    matched = df[df["_order_norm"] == token]

    #不去重
    case_ids = matched["_case_id"].dropna().tolist()

    # ✅ 去重，避免同一用例编号因为多行断言被执行多次
    # case_ids = matched["_case_id"].dropna().unique().tolist()

    # 调试输出
    print("📋 执行序号列原始数据(含归一):")
    print(df[[order_col, "_order_norm", case_col]].head(30))
    print(f"✅ get_case_ids_by_exec_order({exec_order}) → {case_ids}")
    return case_ids


def list_all_risk_types(test_data_file: str, check_sheet: str = "风控点") -> list[str]:
    """
    从「风控点」sheet 自动枚举**全部风控类型**（去重、保序、别名归一）：
    - 优先读取“风控类型”列
    - 没有则退回读“检查点名称/check_point_name”，并做后缀清理 + 别名归一
    返回为**标准风控名**列表（已经过 _norm_risk_name）
    """
    try:
        df = pd.read_excel(test_data_file, sheet_name=check_sheet, engine="openpyxl")
        df.columns = df.columns.str.strip()
        df.ffill(inplace=True)
    except Exception as e:
        print(f"❌ 无法读取风控点 sheet: {e}")
        return []

    type_col = _pick_col(df, ["风控类型"])
    name_col = _pick_col(df, ["检查点名称", "check_point_name"])

    raw_list: list[str] = []
    if type_col:
        raw_list = df[type_col].astype(str).tolist()
    elif name_col:
        raw_list = df[name_col].astype(str).tolist()
    else:
        return []

    seen, out = set(), []
    for raw in raw_list:
        # 展示名规整（去“检查”等后缀），再做别名归一，最后 normalize_text 去重
        pretty = _to_risk_label(raw)
        canon = _norm_risk_name(pretty)
        key = normalize_text(canon)
        if canon and key not in seen:
            seen.add(key)
            out.append(canon)  # 返回标准名
    return out


def list_exec_orders_for_risk_type(
    test_data_file: str,
    risk_type: str,
    check_sheet: str = "风控点",
) -> list[str]:
    """
    列出指定【风控类型】在 Excel 中出现过的所有【执行序号】（去重、排序）：
    - 风控类型识别：优先“风控类型”列；没有则退回“检查点名称”的包含匹配
    - 执行序号按数值排序在前、非数值按出现顺序在后，最后去重
    """
    try:
        df = pd.read_excel(test_data_file, sheet_name=check_sheet, engine="openpyxl")
        df.columns = df.columns.str.strip()
        df.ffill(inplace=True)
    except Exception as e:
        print(f"❌ 无法读取风控点 sheet: {e}")
        return []

    order_col = _pick_col(df, ["执行序号", "执行编号"])
    if not order_col:
        return []

    type_col = _pick_col(df, ["风控类型"])
    name_col = _pick_col(df, ["检查点名称", "check_point_name"])

    target = _norm_risk_name(risk_type)  # 归一成标准风控名

    if type_col:
        # 直接与“风控类型”归一后做等值匹配
        df["_type_norm"] = df[type_col].astype(str).map(lambda x: _norm_risk_name(_to_risk_label(x)))
        df["_match"] = df["_type_norm"] == target
    else:
        if not name_col:
            return []
        # 没有“风控类型”列时，从“检查点名称”归一后做包含匹配
        df["_name_norm"] = df[name_col].astype(str).map(lambda x: _norm_risk_name(_to_risk_label(x)))
        df["_match"] = df["_name_norm"].map(lambda x: target in x)

    # 归一执行序号
    df["_order_norm"] = df[order_col].map(_norm_exec_token)
    orders = [o for o in df.loc[df["_match"], "_order_norm"].tolist() if o]

    # 数字优先排序；非数字保持出现顺序；去重
    numeric = [float(o) for o in orders if re.fullmatch(r"-?\d+(\.\d+)?", o)]
    numeric_sorted = sorted(numeric)
    numeric_fmt = [
        str(int(x)) if float(x).is_integer() else re.sub(r"\.?0+$", "", str(x))
        for x in numeric_sorted
    ]
    nonnum = [o for o in orders if not re.fullmatch(r"-?\d+(\.\d+)?", o)]

    seen, out = set(), []
    for x in numeric_fmt + nonnum:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# =============================================================================
# 计划解析：风控类型计划（RISK_TYPES）、执行序号计划（EXEC_PLAN/EXEC_ORDER）
# =============================================================================

def plan_exec_orders(test_data_file: str, risk_type: str, plan: str | None) -> list[str]:
    """
    解析【执行序号计划】：
      - None / ""  → 默认只跑 ["1"]
      - "all"      → 跑该风控类型下出现过的所有执行序号（list_exec_orders_for_risk_type）
      - "1,2,3"    → 按给定顺序依次跑（逗号/空白/竖线均可分隔）
    """
    if not plan:
        return ["1"]

    plan = plan.strip().lower()
    if plan == "all":
        orders = list_exec_orders_for_risk_type(test_data_file, risk_type)
        print(f"🗂️ ALL 执行序号: {orders}")
        return orders

    items = re.split(r"[,\s|]+", plan)  # 兼容 "1,2" / "1 2" / "1|2"
    return [x for x in (s.strip() for s in items) if x]


def parse_risk_types(test_data_file: str, plan: str | None, check_sheet: str = "风控点") -> list[str]:
    """
    解析【风控类型计划】：
      - None / ""  → 默认 ["单券集中度"]
      - "all"      → Excel 中出现过的所有风控类型（list_all_risk_types）
      - "A,B,C"    → 按给定顺序依次跑（逗号/空白/竖线均可分隔）
    返回：归一后的“标准风控名”列表（去重、保序）
    """
    if not plan:
        return ["单券集中度"]

    plan = plan.strip()
    if plan.lower() == "all":
        types = list_all_risk_types(test_data_file, check_sheet=check_sheet)
        print(f"🗂️ ALL 风控类型: {types}")
        return types

    items = re.split(r"[,\s|]+", plan)
    seen, out = set(), []
    for it in (i.strip() for i in items):
        if not it:
            continue
        # 先做展示名规整（去“检查”等后缀），再做别名归一，最后去重
        canon = _norm_risk_name(_to_risk_label(it))
        key = normalize_text(canon)
        if canon and key not in seen:
            seen.add(key)
            out.append(canon)

    print(f"🧭 解析风控类型: {out}")
    return out
