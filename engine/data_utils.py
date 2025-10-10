def split_multi_row(row: dict, multi_keys: list) -> list:
    """
    拆分含有多个组合/金额等字段的一条 row 为多条 row
    :param row: 原始行（一个 dict）
    :param multi_keys: 需要拆分的字段名列表（如 ['组合', '交易面额(万元)']）
    :return: 拆分后的多条子 row（list of dict）
    """
    split_values = {key: str(row.get(key, '')).split(',') for key in multi_keys}
    max_len = max(len(v) for v in split_values.values())

    result = []
    for i in range(max_len):
        new_row = row.copy()
        for key in multi_keys:
            values = split_values.get(key, [])
            new_row[key] = values[i].strip() if i < len(values) else values[-1].strip()
        result.append(new_row)
    return result
