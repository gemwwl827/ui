# ✅ 引入达梦数据库官方驱动
import dmPython

# ✅ 获取数据库连接（针对 10.60.1.36 服务器）
def get_dm_conn():
    return dmPython.connect(
        user='pms_prodnew',
        password='Hydb001*',
        server='10.60.1.49',
        port=5236,
        schema='PMS_PROD'
    )


# ✅ 更新指定申请单号的 RECORD_TYPE 为任意目标值（默认设为 1）
def patch_core_asset_record_type(request_no: str, target_type: int = 0):
    """
    将 CORE_ASSET_RECORD 表中指定 RequestNo 的所有记录的 RECORD_TYPE 设置为目标状态（默认设为 1）
    :param request_no: 申请单编号，如 'REQ-20240530-00028'
    :param target_type: 更新目标值（默认 1，表示草稿状态）
    """
    conn = get_dm_conn()
    cursor = conn.cursor()

    sql = """
    UPDATE CORE_ASSET_RECORD
    SET RECORD_TYPE = ?
    WHERE REQUEST_NO = ? AND RECORD_TYPE <> ?
    """

    cursor.execute(sql, (target_type, request_no, target_type))
    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ 数据库更新成功：表 CORE_ASSET_RECORD 中 RequestNo = '{request_no}' 的 RECORD_TYPE 已设为 {target_type}")


# ✅ 查询指定申请单号下的所有 RECORD_TYPE（用于断言验证）
def query_record_type(request_no: str):
    """
    查询指定 RequestNo 的所有记录的 RECORD_TYPE 值
    :param request_no: 申请单编号
    :return: List[int]，所有匹配记录的 RECORD_TYPE 值
    """
    conn = get_dm_conn()
    cursor = conn.cursor()

    sql = """
    SELECT RECORD_TYPE FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ?
    """

    cursor.execute(sql, (request_no,))
    results = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return results

