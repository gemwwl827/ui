import dmPython  # ✅ 引入达梦数据库驱动（用于连接 DM 数据库）

# ✅ 获取数据库连接（达梦 DB）
def get_dm_conn():
    return dmPython.connect(
        user='pms_prodnew',
        password='Hydb001*',
        server='10.60.1.49',
        port=5236,
        schema='PMS_PROD'
    )

# ✅ 删除指定申请单编号对应的所有关联数据（包括子表、流程、主表）
def delete_approval_ignite_data(request_no: str):
    """
    删除一笔申请单 request_no 对应的所有业务与流程数据：
    包括资产/资金流水、成交单、风控检查、业务指令及流程实例记录。
    """
    conn = get_dm_conn()
    cursor = conn.cursor()

    try:
        print(f"\n🧹 开始删除申请单: {request_no}")

        # === 🔍 查询关键标识字段，用于后续删除关联表 ===

        # ✅ 查询成交单编号 EXEC_ID（来自表：CORE_ASSET_RECORD）
        cursor.execute("SELECT EXEC_ID FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ? AND EXEC_ID IS NOT NULL", (request_no,))
        exec_id_rows = cursor.fetchall()
        exec_ids = [row[0] for row in exec_id_rows]  # 提取所有 EXEC_ID（可能有多个）
        print(f"🔎 EXEC_ID 列表: {exec_ids}")

        # ✅ 查询流程实例号 WF_INST_NO（来自表：REQUEST_BASE_INDEX）
        cursor.execute("SELECT WF_INST_NO FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", (request_no,))
        result = cursor.fetchone()
        process_id = result[0] if result else None
        print(f"🔎 流程实例号: {process_id}")

        # ✅ 查询业务指令编号 BIZ_INST_NO（来自表：BIZ_INST_USUAL_INDEX）
        cursor.execute("SELECT BIZ_INST_NO FROM BIZ_INST_USUAL_INDEX WHERE REQUEST_NO = ?", (request_no,))
        result = cursor.fetchone()
        biz_inst_no = result[0] if result else None
        print(f"🔎 业务指令编号: {biz_inst_no}")

        # === 🗑 删除各业务相关子表 ===

        # ✅ 删除成交单主表（TRADE_BASE_INDEX），通过 EXEC_ID 删除
        print("🗑 删除成交单 TRADE_BASE_INDEX")
        cursor.execute("""
            DELETE FROM TRADE_BASE_INDEX
            WHERE EXEC_ID IN (
                SELECT EXEC_ID FROM CORE_ASSET_RECORD
                WHERE REQUEST_NO = ? AND EXEC_ID IS NOT NULL
            )
        """, (request_no,))

        # ✅ 删除资产流水表 CORE_ASSET_RECORD
        print("🗑 删除资产流水 CORE_ASSET_RECORD")
        cursor.execute("DELETE FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ?", (request_no,))

        # ✅ 删除资金流水表 CORE_CASH_RECORD
        print("🗑 删除资金流水 CORE_CASH_RECORD")
        cursor.execute("DELETE FROM CORE_CASH_RECORD WHERE REQUEST_NO = ?", (request_no,))

        # ✅ 删除风控检查结果表 RISK_CHECK_RESULTS
        print("🗑 删除风控检查 RISK_CHECK_RESULTS")
        cursor.execute("DELETE FROM RISK_CHECK_RESULTS WHERE REQUEST_NO = ?", (request_no,))

        # ✅ 删除业务指令明细相关（前提是查到了 biz_inst_no）
        if biz_inst_no:
            print(f"🗑 删除业务指令及明细，编号: {biz_inst_no}")

            # ✅ 删除指令和成交单匹配关系表 BIZ_INST_TRADE_CHECK_RECORD
            cursor.execute("DELETE FROM BIZ_INST_TRADE_CHECK_RECORD WHERE BIZ_INST_NO = ?", (biz_inst_no,))

            # ✅ 删除成交资产明细表 BIZ_TRADE_ASSET_DETAIL（通过 biz_inst_no + exec_id）
            cursor.execute("DELETE FROM BIZ_TRADE_ASSET_DETAIL WHERE UNIQUE_NO IN (?, ?)", (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 删除费用明细表 BIZ_INST_FEE_DETAIL
            cursor.execute("DELETE FROM BIZ_INST_FEE_DETAIL WHERE UNIQUE_NO IN (?, ?)", (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 删除资产分配账户明细表 BIZ_ASSET_ASSIGN_DETAIL
            cursor.execute("DELETE FROM BIZ_ASSET_ASSIGN_DETAIL WHERE UNIQUE_NO IN (?, ?)", (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 删除资金分配账号明细表 BIZ_CASH_ASSIGN_DETAIL
            cursor.execute("DELETE FROM BIZ_CASH_ASSIGN_DETAIL WHERE BIZ_INST_NO = ?", (biz_inst_no,))

            # ✅ 删除业务指令主表 BIZ_INST_USUAL_INDEX
            cursor.execute("DELETE FROM BIZ_INST_USUAL_INDEX WHERE BIZ_INST_NO = ?", (biz_inst_no,))

        # === 🗑 删除流程相关 WF_* 表 ===
        if process_id:
            print(f"🗑 删除流程 WF_* 表，流程号: {process_id}")
            # ✅ 工作流活动记录 WF_ACTIVITIES
            cursor.execute("DELETE FROM WF_ACTIVITIES WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 工作流活动用户 WF_ACTIVITYUSERS
            cursor.execute("DELETE FROM WF_ACTIVITYUSERS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 工作流扩展信息 WF_EXTENSION
            cursor.execute("DELETE FROM WF_EXTENSION WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 待办用户表 WF_LATESTTODOACTIVITYUSER（注意字段名不同）
            cursor.execute("DELETE FROM WF_LATESTTODOACTIVITYUSER WHERE PROCESS_INSTANCE_ID = ?", (process_id,))
            # ✅ 工作流追踪 WF_TRACKINGS
            cursor.execute("DELETE FROM WF_TRACKINGS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 工作流用户表 WF_USERS
            cursor.execute("DELETE FROM WF_USERS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 工作流变体 WF_VARIANTS
            cursor.execute("DELETE FROM WF_VARIANTS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 工作流主表 WF_PROCESSINSTANCE
            cursor.execute("DELETE FROM WF_PROCESSINSTANCE WHERE PROCESSINSTANCEID = ?", (process_id,))

        # ✅ 删除申请单主表 REQUEST_BASE_INDEX
        print("🗑 删除申请单主表 REQUEST_BASE_INDEX")
        cursor.execute("DELETE FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", (request_no,))

        # === ✅ 全部删除成功，提交事务 ===
        conn.commit()
        print(f"✅ 成功删除申请单 {request_no} 的所有相关数据")

    except Exception as e:
        # ❌ 异常处理：回滚事务
        print(f"❌ 删除失败：{e}")
        conn.rollback()
    finally:
        # ✅ 关闭资源
        cursor.close()
        conn.close()
        print("🔚 数据库连接已关闭")