# ✅ 文件: utils/data_utils.py

from typing import Union, List, Dict

def normalize_entry(form_data: Union[Dict, List[Dict]]) -> Dict:
    """
    通用数据处理：兼容单条 dict 和多条 list[dict] 的 form_data 数据结构。

    - 如果是 list，则取第一个 dict 返回
    - 如果是 dict，则直接返回
    - 否则抛出异常
    """
    if isinstance(form_data, list):
        if not form_data:
            raise ValueError("❌ form_data 是空列表")
        return form_data[0]
    elif isinstance(form_data, dict):
        return form_data
    else:
        raise TypeError(f"❌ 不支持的 form_data 类型: {type(form_data)}")
