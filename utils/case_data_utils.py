# ✅ 文件: utils/case_data_utils.py
# 说明：
# - 兼容 dict / list 两种 form_data 结构（单指令 & 多指令）
# - 提供从 group / form_data 中提取公共元字段的工具
# - 提供给调度器的标准化 payload 构造

from typing import Any, Dict, List, Union

FormData = Union[Dict[str, Any], List[Dict[str, Any]]]

def extract_meta(form_data: FormData, key: str, default: Any = "") -> Any:
    """
    兼容读取：
    - form_data 为 dict：直接 .get
    - form_data 为 list[dict]：优先第一个元素的 key；若为空则向后寻找第一个非空
    """
    if isinstance(form_data, dict):
        return form_data.get(key, default) or default

    if isinstance(form_data, list) and form_data:
        first = form_data[0]
        if isinstance(first, dict) and first.get(key) not in ("", None):
            return first.get(key)
        for item in form_data:
            if isinstance(item, dict) and item.get(key) not in ("", None):
                return item.get(key)
    return default


def extract_business_type(group: Dict[str, Any], default: str = "") -> str:
    """
    从 group（load_grouped_test_data 返回的分组对象）里解析业务类型：
      1) group['form_data'] 为 dict：form_data['business_type']
      2) group['form_data'] 为 list：优先第一个元素 -> 其他元素 -> group['business_type']
    """
    fd = group.get("form_data")

    if isinstance(fd, dict):
        return fd.get("business_type", "") or group.get("business_type", default) or default

    if isinstance(fd, list) and fd:
        # 先看第一个
        bt = fd[0].get("business_type") if isinstance(fd[0], dict) else None
        if bt:
            return bt
        # 再向后找
        bt = extract_meta(fd, "business_type", "")
        if bt:
            return bt

    return group.get("business_type", default) or default


def build_dispatch_payload(group: Dict[str, Any]) -> Dict[str, Any]:
    """
    构造传给 FormDispatcher 的标准 payload：
    {
        "business_type": <str>,
        "form_data": <dict 或 list[dict]>
    }
    """
    return {
        "business_type": extract_business_type(group),
        "form_data": group.get("form_data"),
    }
