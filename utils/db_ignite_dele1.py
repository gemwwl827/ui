from pyignite import Client

# ✅ 新增：根据审批单号查申请单号（在 Ignite 内存库中）
def get_request_no_by_approval(approval_no: str) -> str:
    """
    ✅ 新增：根据审批单编号（approval_no）反查申请单编号（request_no）
    当前审批单号和申请单号一致，如 REQ-20250605-00002，直接查 REQUEST_BASE_INDEX 表
    """
    client = Client()
    client.connect('10.60.1.49', 10800)  # ✅ 替换为你实际的 Ignite 地址

    try:
        result = client.sql("SELECT REQUEST_NO FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", query_args=[approval_no])
        for row in result:
            return row[0]
        return None
    except Exception as e:
        print(f"⚠️ 查询审批单号 {approval_no} 失败：{e}")
        return None
    finally:
        client.close()

# ✅ PATCH：根据子申请单号（BIZ_INST_NO）将 Ignite 中 RECORD_TYPE 设置为目标值（如 0），并返回原值
def patch_ignite_record_type_by_sub_request(sub_request_no: str, target_type: int = 1) -> int:
    """
    更新 Ignite 中 CORE_ASSET_RECORD 表中某条记录的 RECORD_TYPE 字段
    ✅ 精准控制：只修改指定子申请单号（BIZ_INST_NO）对应的一条记录
    ✅ 返回原始 RECORD_TYPE（用于后续还原）

    :param sub_request_no: 子申请单编号，如 'RCBT-20250605-00017'
    :param target_type: 要设定的目标状态（默认 1 = 草稿）
    :return: 原始 RECORD_TYPE 值（用于还原），未找到则返回 None
    """
    from pyignite import Client  # ✅ 引入 Ignite 客户端
    client = Client()
    client.connect('10.60.1.49', 10800)  # ✅ 连接 Ignite 节点

    try:
        print(f"🛠️ [Ignite] 开始 PATCH，子申请单号 = {sub_request_no}，目标值 = {target_type}")

        # ✅ 查询当前记录的 RECORD_TYPE（只取一条）
        query = "SELECT RECORD_TYPE FROM CORE_ASSET_RECORD WHERE BIZ_INST_NO = ?"
        result = client.sql(query, query_args=[sub_request_no])
        original_type = None
        for row in result:
            original_type = row[0]  # ✅ 提取第一条结果
            break

        if original_type is None:
            print(f"⚠️ [Ignite] 未找到子申请单号 {sub_request_no} 对应的记录")
            return None  # ❌ 未查询到该子单，返回 None

        if original_type == target_type:
            print(f"ℹ️ [Ignite] RECORD_TYPE 已为目标值 {target_type}，无需更新")
            return original_type  # ✅ 不需要更新，直接返回原值

        # ✅ 执行更新语句，仅当当前值不等于目标值时执行
        update_sql = """
            UPDATE CORE_ASSET_RECORD
            SET RECORD_TYPE = ?
            WHERE BIZ_INST_NO = ? AND RECORD_TYPE <> ?
        """
        client.sql(update_sql, query_args=[target_type, sub_request_no, target_type])
        print(f"✅ [Ignite] PATCH 成功：{sub_request_no} 的 RECORD_TYPE 从 {original_type} 改为 {target_type}")
        return original_type

    except Exception as e:
        print(f"❌ [Ignite] PATCH 异常：{e}")
        return None  # ✅ 出错时返回 None

    finally:
        client.close()  # ✅ 关闭 Ignite 连接，避免资源泄漏


# ✅ RESTORE：根据子申请单号（BIZ_INST_NO）将 Ignite 中 RECORD_TYPE 恢复为原始值（加强版）
def restore_ignite_record_type_by_sub_request(sub_request_no: str, original_type: int):
    """
    将 Ignite 中指定子申请单号对应记录的 RECORD_TYPE 恢复为原始值
    ✅ 增加当前值判断与不存在记录时的提示

    :param sub_request_no: 子申请单编号，如 'RCBT-20250605-00017'
    :param original_type: patch 前的 RECORD_TYPE 值
    """
    from pyignite import Client
    client = Client()
    client.connect('10.60.1.49', 10800)

    try:
        print(f"🔁 [Ignite] 开始恢复：子申请单号 = {sub_request_no}，目标恢复值 = {original_type}")

        # ✅ 先查询当前值
        query = "SELECT RECORD_TYPE FROM CORE_ASSET_RECORD WHERE BIZ_INST_NO = ?"
        result = client.sql(query, query_args=[sub_request_no])
        current_type = None
        for row in result:
            current_type = row[0]
            break

        if current_type is None:
            print(f"⚠️ [Ignite] 未找到 BIZ_INST_NO = {sub_request_no} 的记录，跳过恢复")
            return

        if current_type == original_type:
            print(f"ℹ️ [Ignite] 当前 RECORD_TYPE 已为 {original_type}，无需恢复")
            return

        # ✅ 执行恢复操作
        update_sql = """
            UPDATE CORE_ASSET_RECORD
            SET RECORD_TYPE = ?
            WHERE BIZ_INST_NO = ?
        """
        client.sql(update_sql, query_args=[original_type, sub_request_no])
        print(f"✅ [Ignite] 恢复完成：{sub_request_no} RECORD_TYPE 从 {current_type} 设回 {original_type}")

    except Exception as e:
        print(f"❌ [Ignite] 恢复失败：{e}")

    finally:
        client.close()





# ✅ 删除指定申请单编号对应的所有关联数据（包括子表、流程、主表）
def delete_approval_ignite_data(request_no: str):
    client = Client()
    client.connect('10.60.1.49', 10800)  # ✅ 连接 Apache Ignite

    try:
        print(f"\n🧹 开始删除申请单: {request_no}")

        # === 查询关键字段 ===

        # ✅ EXEC_ID（成交单编号）来自资产流水表 CORE_ASSET_RECORD
        exec_ids = []
        result = client.sql("SELECT EXEC_ID FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ? AND EXEC_ID IS NOT NULL", query_args=[request_no])
        for row in result:
            exec_ids.append(row[0])
        print(f"🔎 EXEC_ID 列表: {exec_ids}")

        # ✅ 工作流实例号 WF_INST_NO 来自申请单主表 REQUEST_BASE_INDEX
        process_id = None
        result = client.sql("SELECT WF_INST_NO FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", query_args=[request_no])
        for row in result:
            process_id = row[0]
            break
        print(f"🔎 流程实例号: {process_id}")

        # ✅ 业务指令编号 BIZ_INST_NO 来自业务指令主表 BIZ_INST_USUAL_INDEX
        biz_inst_no = None
        result = client.sql("SELECT BIZ_INST_NO FROM BIZ_INST_USUAL_INDEX WHERE REQUEST_NO = ?", query_args=[request_no])
        for row in result:
            biz_inst_no = row[0]
            break
        print(f"🔎 业务指令编号: {biz_inst_no}")

        # === 删除明细表/子表 ===

        # ✅ 删除成交单主表：TRADE_BASE_INDEX
        print("🗑 删除成交单 TRADE_BASE_INDEX")
        for exec_id in exec_ids:
            client.sql("DELETE FROM TRADE_BASE_INDEX WHERE EXEC_ID = ?", query_args=[exec_id])

        # ✅ 删除资产流水表：CORE_ASSET_RECORD
        print("🗑 删除资产流水 CORE_ASSET_RECORD")
        client.sql("DELETE FROM CORE_ASSET_RECORD WHERE REQUEST_NO = ?", query_args=[request_no])

        # ✅ 删除资金流水表：CORE_CASH_RECORD
        print("🗑 删除资金流水 CORE_CASH_RECORD")
        client.sql("DELETE FROM CORE_CASH_RECORD WHERE REQUEST_NO = ?", query_args=[request_no])

        # ✅ 删除风控检查结果表（如不使用可注释）：RISK_CHECK_RESULTS
        # print("🗑 删除风控检查 RISK_CHECK_RESULTS")
        # client.sql("DELETE FROM RISK_CHECK_RESULTS WHERE REQUEST_NO = ?", query_args=[request_no])

        # ✅ 删除业务指令及其关联明细表
        if biz_inst_no:
            print(f"🗑 删除业务指令及明细，编号: {biz_inst_no}")

            # ✅ 1.删除业务指令与成交单核对表：BIZ_INST_TRADE_CHECK_RECORD
            client.sql("DELETE FROM BIZ_INST_TRADE_CHECK_RECORD WHERE BIZ_INST_NO = ?", query_args=[biz_inst_no])

            for exec_id in exec_ids:
                # ✅ 2.删除成交资产明细表：BIZ_TRADE_ASSET_DETAIL（使用 UNIQUE_NO）
                client.sql("DELETE FROM BIZ_TRADE_ASSET_DETAIL WHERE UNIQUE_NO IN (?, ?)", query_args=[biz_inst_no, exec_id])

                # ✅ 3.删除费用明细表：BIZ_INST_FEE_DETAIL（使用 UNIQUE_NO）
                client.sql("DELETE FROM BIZ_INST_FEE_DETAIL WHERE UNIQUE_NO IN (?, ?)", query_args=[biz_inst_no, exec_id])

                # ✅ 4.删除资产分配明细表：BIZ_ASSET_ASSIGN_DETAIL（使用 UNIQUE_NO）
                client.sql("DELETE FROM BIZ_ASSET_ASSIGN_DETAIL WHERE UNIQUE_NO IN (?, ?)", query_args=[biz_inst_no, exec_id])

                # ✅ 5.删除接口对接信息映射表：BIZ_API_CONTACT_DETAIL（使用 UNIQUE_NO）
                client.sql("DELETE FROM BIZ_API_CONTACT_DETAIL WHERE UNIQUE_NO IN (?, ?)", query_args=[biz_inst_no, exec_id])

            # ✅ 6.删除资金分配账户表：BIZ_CASH_ASSIGN_DETAIL（使用 BIZ_INST_NO）
            client.sql("DELETE FROM BIZ_CASH_ASSIGN_DETAIL WHERE BIZ_INST_NO = ?", query_args=[biz_inst_no])

            # ✅ 7.删除业务指令主表：BIZ_INST_USUAL_INDEX
            client.sql("DELETE FROM BIZ_INST_USUAL_INDEX WHERE BIZ_INST_NO = ?", query_args=[biz_inst_no])

        # === 删除流程相关表（以流程实例号为键） ===
        if process_id:
            print(f"🗑 删除流程 WF_* 表，流程号: {process_id}")
            client.sql("DELETE FROM WF_ACTIVITIES WHERE PROCESSINSTANCEID = ?", query_args=[process_id])             # 流程活动表
            client.sql("DELETE FROM WF_ACTIVITYUSERS WHERE PROCESSINSTANCEID = ?", query_args=[process_id])         # 活动用户表
            client.sql("DELETE FROM WF_EXTENSION WHERE PROCESSINSTANCEID = ?", query_args=[process_id])             # 扩展信息表
            client.sql("DELETE FROM WF_LATESTTODOACTIVITYUSER WHERE PROCESS_INSTANCE_ID = ?", query_args=[process_id]) # 最新待办
            client.sql("DELETE FROM WF_TRACKINGS WHERE PROCESSINSTANCEID = ?", query_args=[process_id])             # 追踪表
            client.sql("DELETE FROM WF_USERS WHERE PROCESSINSTANCEID = ?", query_args=[process_id])                 # 用户记录表
            client.sql("DELETE FROM WF_VARIANTS WHERE PROCESSINSTANCEID = ?", query_args=[process_id])             # 变体表
            client.sql("DELETE FROM WF_PROCESSINSTANCE WHERE PROCESSINSTANCEID = ?", query_args=[process_id])       # 流程主表

        # ✅ 删除申请单主表：REQUEST_BASE_INDEX
        print("🗑 删除申请单主表 REQUEST_BASE_INDEX")
        client.sql("DELETE FROM REQUEST_BASE_INDEX WHERE REQUEST_NO = ?", query_args=[request_no])

        print(f"✅ 成功删除申请单 {request_no} 的所有相关数据")

    except Exception as e:
        print(f"❌ 删除失败：{e}")
    finally:
        client.close()
        print("🔚 Ignite 连接已关闭")
