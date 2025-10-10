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
