from pyignite import Client

def delete_ignite_data_by_date(start_date: str, created_user_id: str = 'zhuyang'):
    """
    根据创建日期 >= start_date 和用户ID 删除所有相关数据（批量删除）
    :param start_date: 日期字符串，如 '2025-06-01'
    :param created_user_id: 创建用户ID，默认 'zhuyang'
    """
    client = Client()
    client.connect('10.60.1.49', 10800)

    try:
        print(f"\n🧹 开始批量删除 CREATED_DATE >= {start_date} 且 CREATED_USER_ID = {created_user_id} 的数据")

        # 主表
        client.sql("DELETE FROM REQUEST_BASE_INDEX WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM TRADE_BASE_INDEX WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM CORE_ASSET_RECORD WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM CORE_CASH_RECORD WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])

        # 业务指令明细表
        client.sql("DELETE FROM BIZ_INST_USUAL_INDEX WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_INST_TRADE_CHECK_RECORD WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_API_CONTACT_DETAIL WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_TRADE_ASSET_DETAIL WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_INST_FEE_DETAIL WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_ASSET_ASSIGN_DETAIL WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM BIZ_CASH_ASSIGN_DETAIL WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])

        # 流程相关表（注意 WF_LATESTTODOACTIVITYUSER 是 USER_NAME 字段）
        client.sql("DELETE FROM WF_ACTIVITIES WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_ACTIVITYUSERS WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_EXTENSION WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_LATESTTODOACTIVITYUSER WHERE CREATED_DATE >= ? AND USER_NAME = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_TRACKINGS WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_USERS WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_VARIANTS WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])
        client.sql("DELETE FROM WF_PROCESSINSTANCE WHERE CREATED_DATE >= ? AND CREATED_USER_ID = ?", query_args=[start_date, created_user_id])

        print(f"✅ 删除成功：已清除 {created_user_id} 用户在 {start_date} 之后创建的所有数据")
    except Exception as e:
        print(f"❌ 删除失败：{e}")
    finally:
        client.close()
        print("🔚 Ignite 连接已关闭")
