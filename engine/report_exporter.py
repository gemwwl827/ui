# engine/report_exporter.py
from __future__ import annotations
import pandas as pd
import allure

def _status_cn(v: str) -> str:
    v = str(v or "")
    if "失败" in v:
        return "❌ 失败"
    if "成功" in v:
        return "✅ 成功"
    if "不适用" in v or "跳过" in v:
        return "🚫 不适用"
    return v or ""

def attach_assert_table_flat(rows: list[dict], name: str = "📋 风控断言详情表格（失败高亮）") -> None:
    """
    扁平表：一条记录=一个阶段（提交/审批）的一次断言
    期望用于排查时看明细。
    需要字段：
      - group_key, check_point_name, 阶段, status, actual_result, expected_value, actual_value, 备注
    """
    if not rows:
        return
    df = pd.DataFrame(rows)
    if df.empty:
        return

    # 列映射 & 顺序
    col_map = {
        "group_key": "用例编号",
        "check_point_name": "检查点",
        "阶段": "阶段",
        "status": "断言状态",
        "actual_result": "检查状态",
        "expected_value": "预期值",
        "actual_value": "实际值",
        "备注": "备注说明",
    }
    use_cols = [c for c in col_map if c in df.columns]
    df = df[use_cols].rename(columns=col_map)

    # 失败高亮
    def _hl(row):
        return ['background-color:#ffe6e6' if '失败' in str(row.get('断言状态','')) else '' for _ in row]
    df["断言状态"] = df["断言状态"].map(_status_cn)
    styled = df.style.apply(_hl, axis=1)
    html = styled.hide_index().to_html()
    allure.attach(html, name=name, attachment_type=allure.attachment_type.HTML)


def attach_assert_table_merged(rows: list[dict], name: str = "📋 风控断言汇总（提交/审批合并一行，失败高亮）") -> None:
    """
    合并表：一条记录=一个 (用例编号, 检查点)，行内包含“提交_* / 审批_*”两组字段。
    需要字段：
      - group_key, check_point_name
      - 阶段: "提交"/"审批"
      - status(断言状态), actual_result(检查状态), expected_value, actual_value, 备注(可选)
    """
    if not rows:
        return
    df = pd.DataFrame(rows)
    if df.empty:
        return

    # 只保留我们关心的列
    need = ["group_key", "check_point_name", "阶段",
            "status", "actual_result", "expected_value", "actual_value", "备注"]
    for c in need:
        if c not in df.columns:
            df[c] = ""

    merged: dict[tuple[str,str], dict] = {}
    for _, r in df.iterrows():
        key = (str(r["group_key"]), str(r["check_point_name"]))
        row = merged.setdefault(key, {
            "用例编号": str(r["group_key"]),
            "检查点": str(r["check_point_name"]),
            # 预留列
            "提交_断言状态": "", "提交_检查状态": "", "提交_预期值": "", "提交_实际值": "",
            "审批_断言状态": "", "审批_检查状态": "", "审批_预期值": "", "审批_实际值": "",
            "备注说明": "",
        })
        phase = "提交" if str(r["阶段"]) == "提交" else ("审批" if str(r["阶段"]) == "审批" else None)
        if phase:
            row[f"{phase}_断言状态"] = _status_cn(r["status"])
            row[f"{phase}_检查状态"] = r["actual_result"] or ""
            row[f"{phase}_预期值"] = "" if pd.isna(r["expected_value"]) else str(r["expected_value"])
            row[f"{phase}_实际值"] = "" if pd.isna(r["actual_value"]) else str(r["actual_value"])
        # 合并备注
        remark = str(r.get("备注") or "").strip()
        if remark:
            row["备注说明"] = (row["备注说明"] + " | " + remark).strip(" |")

    out = pd.DataFrame(merged.values())

    # 行级失败高亮：任一阶段断言失败即高亮
    def _hl(row):
        fail = any("失败" in str(row[c]) for c in ["提交_断言状态","审批_断言状态"])
        return ['background-color:#ffe6e6' if fail else '' for _ in row]

    styled = out.style.apply(_hl, axis=1)
    html = styled.hide_index().to_html()
    allure.attach(html, name=name, attachment_type=allure.attachment_type.HTML)
