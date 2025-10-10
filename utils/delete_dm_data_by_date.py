import dmPython

# ✅ 获取数据库连接（达梦 DB）
def get_dm_conn():
    return dmPython.connect(
        user='pms_prodnew',
        password='Hydb001*',
        server='10.60.1.49',
        port=5236,
        schema='PMS_PROD'
    )

# ✅ 按日期批量删除所有申请单相关数据
def delete_dm_data_by_date(start_date: str, created_user_id: str = 'zhuyang'):
    """
    删除 CREATED_DATE >= 指定日期 且 CREATED_USER_ID=指定用户 的全链路申请单数据
    :param start_date: 起始日期字符串，如 '2025-06-01'
    :param created_user_id: 创建用户 ID，默认 'zhuyang'
    """
    conn = get_dm_conn()
    cursor = conn.cursor()

    try:
        print(f"\n🧹 开始批量删除 CREATED_DATE >= {start_date} 且 CREATED_USER_ID = {created_user_id} 的所有数据")

        # === 删除主表与子表 ===
        tables_and_conditions = [
            ("REQUEST_BASE_INDEX", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("TRADE_BASE_INDEX", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("CORE_ASSET_RECORD", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("CORE_CASH_RECORD", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_INST_USUAL_INDEX", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_INST_TRADE_CHECK_RECORD", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_API_CONTACT_DETAIL", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_TRADE_ASSET_DETAIL", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_INST_FEE_DETAIL", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_ASSET_ASSIGN_DETAIL", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("BIZ_CASH_ASSIGN_DETAIL", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_ACTIVITIES", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_ACTIVITYUSERS", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_EXTENSION", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_LATESTTODOACTIVITYUSER", "CREATED_DATE >= ? AND USER_NAME = ?"),  # ⚠️ 字段不同
            ("WF_TRACKINGS", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_USERS", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_VARIANTS", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
            ("WF_PROCESSINSTANCE", "CREATED_DATE >= ? AND CREATED_USER_ID = ?"),
        ]

        for table, condition in tables_and_conditions:
            print(f"🗑 正在删除表 {table} 中的相关数据...")
            cursor.execute(f"DELETE FROM {table} WHERE {condition}", (start_date, created_user_id))

        conn.commit()
        print(f"✅ 删除完成：已清除用户 {created_user_id} 在 {start_date} 之后创建的所有记录")

    except Exception as e:
        print(f"❌ 删除失败：{e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        print("🔚 数据库连接已关闭")
