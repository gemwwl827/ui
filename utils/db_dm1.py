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

def get_request_no_by_approval(approval_no: str) -> str:
    """
    根据审批单编号（approval_no）反查申请单编号（request_no）
    ✅ 注意：在你的系统中，申请单编号和审批单编号是同一值（如 REQ-2025...）
    """
    conn = get_dm_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT REQUEST_NO FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", (approval_no,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()
        conn.close()


# ✅ PATCH：将指定子申请单号（业务指令编号）对应记录设为目标状态（默认草稿 = 1），并返回旧值
def patch_core_asset_record_type(sub_request_no: str, target_type: int = 1) -> int:
    """
    根据子申请单编号（BIZ_INST_NO）修改 CORE_ASSET_RECORD 表中某条记录的 RECORD_TYPE
    ✅ 仅修改指定子单，不影响同一个父申请单下其他子单
    ✅ 返回原始 RECORD_TYPE 值用于后续还原

    :param sub_request_no: 子申请单编号，如 'RCBT-20240530-00017'（对应 BIZ_INST_NO 字段）
    :param target_type: 要设置的 RECORD_TYPE 值（默认 1 = 草稿）
    :return: int，记录修改前的 RECORD_TYPE 原始值
    """
    conn = get_dm_conn()  # ✅ 建立数据库连接
    cursor = conn.cursor()  # ✅ 创建游标

    try:
        print(f"🚀 开始 PATCH 操作：子申请单号 = {sub_request_no}，目标 RECORD_TYPE = {target_type}")  # ✅ 打印传入信息

        # ✅ 查询该子申请单当前的 RECORD_TYPE 值
        cursor.execute("SELECT RECORD_TYPE FROM CORE_ASSET_RECORD WHERE BIZ_INST_NO = ?", (sub_request_no,))
        result = cursor.fetchone()  # ✅ 获取查询结果
        original_type = result[0] if result else None  # ✅ 若查询不到返回 None

        if original_type is None:
            print(f"⚠️ 未找到 BIZ_INST_NO = {sub_request_no} 的记录，PATCH 中止")
            return None  # ✅ 如果找不到记录，直接返回 None

        if original_type == target_type:
            print(f"ℹ️ 子申请单 {sub_request_no} 的 RECORD_TYPE 已是目标值 {target_type}，无需修改")
            return original_type  # ✅ 如果原始值已是目标状态，则跳过更新

        # ✅ 执行 PATCH 更新操作，仅当当前值不等于目标值
        cursor.execute("""
            UPDATE CORE_ASSET_RECORD
            SET RECORD_TYPE = ?
            WHERE BIZ_INST_NO = ? AND RECORD_TYPE <> ?
        """, (target_type, sub_request_no, target_type))  # ✅ 更新子单的 RECORD_TYPE

        conn.commit()  # ✅ 提交事务

        print(f"✅ PATCH 成功：子申请单 {sub_request_no} 的 RECORD_TYPE 从 {original_type} 更新为 {target_type}")
        return original_type  # ✅ 返回更新前的原始值

    except Exception as e:
        print(f"❌ PATCH 过程中发生异常：{e}")  # ✅ 异常处理
        return None

    finally:
        cursor.close()  # ✅ 关闭游标
        conn.close()   # ✅ 关闭连接



# ✅ RESTORE：将指定子申请单号对应记录的 RECORD_TYPE 恢复为原始值（加强版）
def restore_core_asset_record_type(sub_request_no: str, original_type: int):
    """
    将指定子申请单（BIZ_INST_NO）对应记录的 RECORD_TYPE 恢复为 patch 前的原始值
    ✅ 加强日志、异常处理、执行前验证

    :param sub_request_no: 子申请单编号，如 'RCBT-20240530-00017'
    :param original_type: PATCH 前的 RECORD_TYPE 值（用于恢复）
    """
    conn = get_dm_conn()  # ✅ 建立数据库连接
    cursor = conn.cursor()

    try:
        print(f"🔁 准备恢复 RECORD_TYPE：子申请单号 = {sub_request_no}，目标恢复值 = {original_type}")

        # ✅ 查询当前值
        cursor.execute("SELECT RECORD_TYPE FROM CORE_ASSET_RECORD WHERE BIZ_INST_NO = ?", (sub_request_no,))
        row = cursor.fetchone()

        if not row:
            print(f"⚠️ 未找到 BIZ_INST_NO = {sub_request_no} 的记录，跳过恢复操作")
            return

        current_type = row[0]
        if current_type == original_type:
            print(f"ℹ️ 当前 RECORD_TYPE 已为 {original_type}，无需恢复")
            return

        # ✅ 执行更新
        cursor.execute("""
            UPDATE CORE_ASSET_RECORD
            SET RECORD_TYPE = ?
            WHERE BIZ_INST_NO = ?
        """, (original_type, sub_request_no))

        conn.commit()  # ✅ 提交事务
        print(f"✅ 恢复完成：子申请单 {sub_request_no} 的 RECORD_TYPE 已从 {current_type} 恢复为 {original_type}")

    except Exception as e:
        print(f"❌ 恢复失败：子申请单 {sub_request_no} 出现异常：{e}")
        conn.rollback()  # ✅ 异常时回滚事务

    finally:
        cursor.close()  # ✅ 关闭游标
        conn.close()    # ✅ 关闭连接



#  删除指定申请单编号对应的所有关联数据（包括子表、流程、主表）
def delete_approval_dm_data(request_no: str):
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
        cursor.execute("SELECT EXEC_ID FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ? AND EXEC_ID IS NOT NULL",
                       (request_no,))
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

            # ✅ 1.删除指令和成交单匹配关系表 BIZ_INST_TRADE_CHECK_RECORD
            cursor.execute("DELETE FROM BIZ_INST_TRADE_CHECK_RECORD WHERE BIZ_INST_NO = ?", (biz_inst_no,))

            # ✅ 2.删除接口映射表：BIZ_API_CONTACT_DETAIL（使用 UNIQUE_NO）
            cursor.execute("DELETE FROM BIZ_API_CONTACT_DETAIL WHERE UNIQUE_NO IN (?, ?)",
                           (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 3.删除成交资产明细表 BIZ_TRADE_ASSET_DETAIL（通过 biz_inst_no + exec_id）
            cursor.execute("DELETE FROM BIZ_TRADE_ASSET_DETAIL WHERE UNIQUE_NO IN (?, ?)",
                           (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 4.删除费用明细表 BIZ_INST_FEE_DETAIL
            cursor.execute("DELETE FROM BIZ_INST_FEE_DETAIL WHERE UNIQUE_NO IN (?, ?)",
                           (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 5.删除资产分配账户明细表 BIZ_ASSET_ASSIGN_DETAIL
            cursor.execute("DELETE FROM BIZ_ASSET_ASSIGN_DETAIL WHERE UNIQUE_NO IN (?, ?)",
                           (biz_inst_no, exec_ids[0] if exec_ids else None))

            # ✅ 6.删除资金分配账号明细表 BIZ_CASH_ASSIGN_DETAIL
            cursor.execute("DELETE FROM BIZ_CASH_ASSIGN_DETAIL WHERE BIZ_INST_NO = ?", (biz_inst_no,))

            # ✅ 7.删除业务指令主表 BIZ_INST_USUAL_INDEX
            cursor.execute("DELETE FROM BIZ_INST_USUAL_INDEX WHERE BIZ_INST_NO = ?", (biz_inst_no,))

        # === 🗑 删除流程相关 WF_* 表 ===
        if process_id:
            print(f"🗑 删除流程 WF_* 表，流程号: {process_id}")
            # ✅ 1.工作流活动记录 WF_ACTIVITIES
            cursor.execute("DELETE FROM WF_ACTIVITIES WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 2.工作流活动用户 WF_ACTIVITYUSERS
            cursor.execute("DELETE FROM WF_ACTIVITYUSERS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 3.工作流扩展信息 WF_EXTENSION
            cursor.execute("DELETE FROM WF_EXTENSION WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 4.待办用户表 WF_LATESTTODOACTIVITYUSER（注意字段名不同）
            cursor.execute("DELETE FROM WF_LATESTTODOACTIVITYUSER WHERE PROCESS_INSTANCE_ID = ?", (process_id,))
            # ✅ 5.工作流追踪 WF_TRACKINGS
            cursor.execute("DELETE FROM WF_TRACKINGS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 6.工作流用户表 WF_USERS
            cursor.execute("DELETE FROM WF_USERS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 7.工作流变体 WF_VARIANTS
            cursor.execute("DELETE FROM WF_VARIANTS WHERE PROCESSINSTANCEID = ?", (process_id,))
            # ✅ 8.工作流主表 WF_PROCESSINSTANCE
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
