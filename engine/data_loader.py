# engine/data_loader.py
import re
import pandas as pd
from typing import List
from engine.risk_field_extractor import (
    CHECKPOINT_FIELD_MAP, FORM_FIELD_TO_EXCEL_COLUMN, normalize_text
)
from engine.data_utils import split_multi_row


# ---------- 小工具 ----------
# def _safe_get(row, col, default: str = ""):
#     """安全取值：空/NaN/异常 → default（不做任何归一化转换）"""
#     try:
#         val = row.get(col, default)
#         return default if (val is None or (isinstance(val, float) and pd.isna(val))) else str(val).strip()
#     except Exception:
#         return default
def _safe_get(row, col, default: str = ""):
    """
    安全取值：空 / NaN / None / '无' / 'NAN' / 'nan' / 'W' → default
    """
    try:
        val = row.get(col, default)
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default

        s = str(val).strip()

        # ✅ 全面屏蔽无效值
        if s in ("", "无", "空", "不适用"):
            return default
        if s.upper() in ("NONE", "NULL", "NAN", "NA", "W"):
            return default

        return s
    except Exception:
        return default


def _to_int_or_none(v: str):
    """把 '0'/'0.0'/''/None 转成 int 或 None；仅用于“指令序号”"""
    s = (v or "").strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def _norm_exec_str(v: str) -> str:
    """
    🔸仅用于创建“别名 key”的轻量归一化：
      - '3.0' -> '3'
      - '3.5' 保持 '3.5'
      - 空/非数 保持原样
    ⚠ 不改变原始数据，仅在 dict 的 key 上提供一个可用别名。
    """
    s = (v or "").strip()
    if s == "":
        return ""
    try:
        f = float(s); i = int(f)
        return str(i) if abs(f - i) < 1e-9 else s
    except Exception:
        return s

def _pick_sheets(xls: pd.ExcelFile, want: str, prefix: str) -> List[str]:
    """
    want == "auto": 所有以 prefix 开头的 sheet
    want 是具体名 : 只读它
    want 是正则   : 用正则匹配
    """
    if want == "auto":
        return [n for n in xls.sheet_names if n.startswith(prefix)]
    if want in xls.sheet_names:
        return [want]
    try:
        pat = re.compile(want)
        return [n for n in xls.sheet_names if pat.match(n)]
    except Exception:
        return [want]  # 兜底尝试


# ---------- 主函数 ----------
def load_grouped_test_data(test_data_file: str,
                           form_sheet: str = "用例库",
                           check_sheet: str = "风控点") -> dict:
    """
    最小改动版（不做全局归一化）：
    - ✅ group_key 按 Excel 原样（exec_order 原样，如 '3.0'）
    - ✅ 但额外给 '3-xxx' 建一个“别名 key”，兼容下游用 '3' 的地方
    - ✅ 多指令：form_data 用 list；仅有 1 条时“压扁”为 dict（兼容旧代码）
    - ✅ instruction_index：组内 0/1/2…（与风控点『指令序号』对齐）
    - ✅ 兼容列名：操作模式(多个指令) / 操作模式；并同时写入 operation_mode/submit_modes/multi_mode
    - ✅ 顶层 business_type：便于调度器/导航器直接读取
    """
    xls = pd.ExcelFile(test_data_file, engine="openpyxl")

    # === 1) 表单：用例库* ===
    form_sheet_names = _pick_sheets(xls, form_sheet, "用例库")
    form_df_list = [pd.read_excel(xls, sheet_name=s) for s in form_sheet_names]
    form_df = pd.concat(form_df_list, ignore_index=True)
    form_df.ffill(inplace=True)

    # ✅ 清洗配对ID（防止大小写、空格、None 导致匹配失败）
    if "配对ID" in form_df.columns:
        form_df["配对ID"] = form_df["配对ID"].astype(str).str.strip().str.upper()
    if "场景类型" in form_df.columns:
        form_df["场景类型"] = form_df["场景类型"].astype(str).str.strip()

    print(f"[DEBUG] 用例库配对ID采样: {form_df['配对ID'].dropna().unique()[:10]}", flush=True)

    grouped: dict = {}
    multi_fields = ['组合', '交易面额(万元)']  # 保持你原有的多值展开策略

    for _, row in form_df.iterrows():
        # 如提示 Series，可以 row.to_dict() 再传；实际 Series 也可用 .get()
        split_rows = split_multi_row(row, multi_fields)

        for sub_row in split_rows:
            case_id    = _safe_get(sub_row, '用例编号')
            exec_order = _safe_get(sub_row, '执行编号')   # ❗保持原样（可能是 '3.0'）
            if not case_id:
                continue

            # 原样 key（主 key）
            raw_key  = f"{exec_order}-{case_id}" if exec_order else case_id
            # 别名 key（只在 '3.0' 这类场景时出现）
            eo_norm  = _norm_exec_str(exec_order)
            norm_key = f"{eo_norm}-{case_id}" if eo_norm else raw_key

            biz_type = _safe_get(sub_row, '业务类型')

            # 用 raw_key 创建/取组对象
            if raw_key not in grouped:
                grouped[raw_key] = {
                    'business_type': biz_type,
                    'form_data': [],
                    'checks': []
                }
            else:
                grouped[raw_key].setdefault('business_type', biz_type)

            # ➕ 建立“别名 key”指向同一个对象（避免下游用 '3' 找不到）
            if norm_key != raw_key and norm_key not in grouped:
                grouped[norm_key] = grouped[raw_key]

            # ✅ 统一兜底：兼容多种列名
            operation_mode = (
                    _safe_get(sub_row, '操作模式(多个指令)')
                    or _safe_get(sub_row, '操作模式')
                    or _safe_get(sub_row, '指令模式')
            )

            instruction_index = len(grouped[raw_key]['form_data'])  # 组内 0/1/2…

            form_data_dict = {
                'counterparty': _safe_get(sub_row, '交易对手方'),
                'full_name': _safe_get(sub_row, '交易对手方全称'),
                'bond_code': _safe_get(sub_row, '债券代码'),
                'bond_full_name': _safe_get(sub_row, '债券全称'),
                'price': _safe_get(sub_row, '净价(元)'),
                'first_net_price': _safe_get(sub_row, '首次净价(元)'),
                'settlement_speed': _safe_get(sub_row, '清算速度'),
                'combination': _safe_get(sub_row, '组合'),
                'actual_counterparty': _safe_get(sub_row, '实际对手方'),
                'transaction_direction': _safe_get(sub_row, '交易方向'),
                'sub_case_no': case_id,
                'sub_no': case_id,

                # 兼容老代码读取 submit_modes / multi_mode
                'operation_mode': operation_mode,
                'submit_modes': operation_mode,
                'multi_mode': operation_mode,

                'risk_type': _safe_get(sub_row, '风控类型'),
                "expected_value": _safe_get(sub_row, "预期值"),
                'request_no': _safe_get(sub_row, '申请单编号'),
                'sub_request_no': _safe_get(sub_row, '子申请单号'),
                'patch_flag': _safe_get(sub_row, '是否Patch'),
                'face_value': _safe_get(sub_row, '交易面额(万元)'),
                'trade_date': _safe_get(sub_row, '交易日期'),

                #（可选）表单里也带上 business_type
                'business_type': biz_type,

                'repo_days': _safe_get(sub_row, '回购期限(天)'),
                'repo_rate': _safe_get(sub_row, '回购利率(%)'),
                'repo_amount': _safe_get(sub_row, '回购金额(元)'),
                'pledge_bond_code': _safe_get(sub_row, '质押债券代码'),
                'pledge_bond_name': _safe_get(sub_row, '质押债券全称'),
                'max_amount': _safe_get(sub_row, '上限金额(万元)'),
                'fund_code': _safe_get(sub_row, '基金代码'),
                'fund_full_name': _safe_get(sub_row, '基金全称'),
                'redemption_time': _safe_get(sub_row, '计划赎回时间'),
                'fund_price': _safe_get(sub_row, '交易价格(元)'),
                'fund_volume': _safe_get(sub_row, '份额'),
                'fund_amount': _safe_get(sub_row, '交易金额(元)'),
                'custody_account': _safe_get(sub_row, '托管账户信息'),
                'risk_check_count': _safe_get(sub_row, '风控数量'),
                'bond_position': _safe_get(sub_row, '债券持仓量(万)'),
                'bond_liquidity': _safe_get(sub_row, '流通量(万)'),
                'bond_concentration': _safe_get(sub_row, '集中度(%)'),
                'bond_total_investment': _safe_get(sub_row, '债券投资总规模(万)'),
                'bid_yield': _safe_get(sub_row, '中标利率(%)'),
                'full_price': _safe_get(sub_row, '全价(元)'),
                # —— 新增：债券借贷专属字段 ——
                'lending_rate': _safe_get(sub_row, col='借贷费率(%)'),
                'lending_days': _safe_get(sub_row, col='借贷期限(天)'),
                # —— 新增：信用拆借字段 ——
                'loan_days': _safe_get(sub_row, col='拆借期限(天)'),
                'loan_rate': _safe_get(sub_row, col='拆借利率(%)'),
                'loan_amount_wan': _safe_get(sub_row, col='拆借金额(万元)'),
                'instruction_index': instruction_index,
                'scene_type': _safe_get(sub_row, '场景类型'),
                'pair_id': _safe_get(sub_row, '配对ID'),

            }
            grouped[raw_key]['form_data'].append(form_data_dict)
            # ✅ 调试输出：确认场景是否提取成功
            # scene_type_val = form_data_dict.get("scene_type")
            # if not scene_type_val:
            #     print(
            #         f"⚠️ form_data 行 scene_type 缺失 → case_id={case_id}, exec_order={exec_order}, row={sub_row.to_dict()}")
            # else:
            #     print(f"✅ form_data 行读取 scene_type='{scene_type_val}' ← case_id={case_id}, exec_order={exec_order}")

    # === 1.5) 单指令“压扁”为 dict（向后兼容关键点） ===
    # 注意：存在“别名 key”会有两个键指向同一对象，这里做两次也无害（幂等）。
    for g in grouped.values():
        fd = g.get('form_data')
        if isinstance(fd, list) and len(fd) == 1:
            g['form_data'] = fd[0]

    # === 2) 风控点：风控点* ===
    check_sheet_names = _pick_sheets(xls, check_sheet, "风控点")
    check_df_list = [pd.read_excel(xls, sheet_name=s) for s in check_sheet_names]
    check_df = pd.concat(check_df_list, ignore_index=True)
    check_df.ffill(inplace=True)

    # ✅ 清洗配对ID与场景类型，保持与表单一致
    if "配对ID" in check_df.columns:
        check_df["配对ID"] = check_df["配对ID"].astype(str).str.strip().str.upper()
    if "场景类型" in check_df.columns:
        check_df["场景类型"] = check_df["场景类型"].astype(str).str.strip()

    # 🧩 调试：查看配对ID列的真实值
    print(f"[DEBUG] 配对ID采样: {check_df['配对ID'].dropna().unique()[:10]}")
    print("✅ [DEBUG] 即将加载风控点 sheet", flush=True)
    print(f"[DEBUG] check_sheet_names = {_pick_sheets(xls, check_sheet, '风控点')}", flush=True)

    # === 🧠 不再使用继承：直接按风控点字段读取 ===
    for _, row in check_df.iterrows():
        case_id = _safe_get(row, '用例编号')
        exec_order = _safe_get(row, '执行编号')
        if not case_id:
            continue

        raw_key = f"{exec_order}-{case_id}" if exec_order else case_id
        eo_norm = _norm_exec_str(exec_order)
        norm_key = f"{eo_norm}-{case_id}" if eo_norm else raw_key

        # ✅ 改进：只按用例编号匹配，不再强依赖执行编号
        entry_key = None
        if case_id in grouped:
            entry_key = case_id
        else:
            for k in grouped.keys():
                if k.endswith(f"-{case_id}"):
                    entry_key = k
                    break
        if not entry_key:
            print(f"[WARN] 未找到匹配组: case_id={case_id}, exec_order={exec_order}")
            continue

        check_name = _safe_get(row, '检查点名称')
        field_key = CHECKPOINT_FIELD_MAP.get(normalize_text(check_name), "")
        excel_column = FORM_FIELD_TO_EXCEL_COLUMN.get(field_key, "")
        expected_value_fallback = _safe_get(row, excel_column) if excel_column else ""

        instruction_mode = _safe_get(row, '指令模式') or _safe_get(row, '操作模式(多个指令)')
        scene_type = _safe_get(row, '场景类型').strip()
        pair_id = _safe_get(row, '配对ID').strip()

        # ✅ 打印调试确认
        print(f"[DEBUG] 加入check: case={case_id}, scene_type={scene_type}, pair_id={pair_id}")

        grouped[entry_key]['checks'].append({
            'check_point_name': check_name,
            'check_result': _safe_get(row, '检查结果'),
            'check_description': _safe_get(row, '结果描述'),
            'sub_case_no': case_id,
            "expected_value": _safe_get(row, "预期值") or expected_value_fallback,
            'instruction_index': _to_int_or_none(_safe_get(row, '指令序号')),
            'instruction_mode': instruction_mode,
            'scene_type': scene_type,
            'pair_id': pair_id
        })
    return grouped
