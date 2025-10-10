# engine/form_navigator.py
# ✅ 表单通用导航与行为辅助类（导航到业务页 + 页面就绪等待 + 新建按钮稳健点击）

class TradeFormNavigator:
    # ---------------- 路由表 ----------------
    # ⚠️ 请核对两个路径是否对：协议式 vs 质押式
    #   - 你项目里有 ExchangeAgreementRepoPage / ExchangePledgeRepoPage 两个页面类
    #   - 常识上：pledged(质押式)、agreement(协议式)
    #   - 你原代码把“协议式”映射到了 pledgedrepoes，看起来像是反了（已在注释里标注）
    ROUTES = {
        # 债券类
        "银行间现券买卖":    "/traderequest/bank/cashbond",
        "银行间质押式回购":  "/traderequest/bank/colrepo",
        "银行间买断式回购":  "/traderequest/bank/outrepoes",
        "银行间债券借贷": "/traderequest/bank/seclend",
        "银行间信用拆借": "/traderequest/bank/ibo",


        # ⚠️ 请核对这两条是否需要对调：
        "交易所现券买卖": "/traderequest/exchange/cashbond",
        "交易所协议式回购":  "/traderequest/exchange/pledgedrepoes",   # ← 多数项目这样命名
        "交易所质押式回购":  "/traderequest/exchange/colrepo",     # ← 多数项目这样命名
        "交易所债券借贷": "/traderequest/exchange/seclend",
        #其他业务
        "分销买卖": "/traderequest/other/buySell",
        # 如你后端实际是相反的，把这两行换回去即可
        # "交易所协议式回购":  "/traderequest/exchange/pledgedrepoes",
        # "交易所质押式回购":  "/traderequest/exchange/colrepo",

        # 基金类
        "场内基金申赎":      "/traderequest/exchange/redeem",
        "场内基金买卖":      "/traderequest/exchange/business",
        "场外基金申赎":      "/traderequest/other/outFund",
    }

    # ---------------- 对哪些业务需要“新建” ----------------
    def should_create_new(self, business_type: str) -> bool:
        """
        返回 True 时会在进入业务页后点击“新建”
        """
        no_create_required = {
            "银行间买断式回购",
            "银行间债券借贷",
            "交易所协议式回购",
            "交易所质押式回购",
            "交易所债券借贷",
            "场内基金申赎",
            "场内基金买卖",
            "场外基金申赎",
        }
        return business_type not in no_create_required

    # ---------------- 导航到业务页（含就绪等待） ----------------
    def navigate_to_business(self, page, business_type: str, timeout=10000):
        """
        根据业务类型导航到对应页面，并等待页面就绪（去掉全局 loading 遮罩）
        """
        path = self.ROUTES.get(business_type)
        if not path:
            raise Exception(f"❌ 未知业务类型: {business_type}")
        print(f"📌 正在跳转: {business_type} → {path}")
        page.goto(path, timeout=timeout, wait_until="networkidle")
        if business_type == "交易所现券买卖":
            print("🔄 交易所现券买卖: 刷新后等待页面元素...")
            page.reload(wait_until="networkidle")  # ✅ 刷新一次
            page.wait_for_selector("button:has-text('新建')", timeout=1000)
            # ✅ 点击新建（保证进入干净的申请单）
            self.click_new_when_ready(page)
            print("✅ 已点击『新建』，可以开始选买入/卖出")

        elif business_type == "交易所协议式回购":
            print("🔄 交易所协议式回购: 刷新后等待页面元素...")
            # 只刷新，不点新建
            # page.wait_for_selector("#app", timeout=10000)
            print("✅ 页面刷新完成，不需要点击『新建』")

        else:
            # 其他业务 → 是否需要点新建交给 try_create_new_request()
            self.try_create_new_request(page, business_type)

        # # 基本就绪
        # page.wait_for_load_state("domcontentloaded")
        # # 主体区域可见（任取一个稳定的容器）
        # page.locator("#app, #app .el-main").first.wait_for(state="visible", timeout=100)
        #
        # # 等全局 loading 遮罩消失（很多 ElementUI/ElLoading 用 el-loading-mask）
        # overlay = page.locator("div.el-loading-mask")
        # try:
        #     overlay.first.wait_for(state="detached", timeout=100)
        # except Exception:
        #     # 有的项目遮罩不移除 DOM，只是隐藏
        #     try:
        #         overlay.first.wait_for(state="hidden", timeout=80)
        #     except Exception:
        #         pass

    # ---------------- 稳健点击“新建” ----------------
    def click_new_when_ready(self, page, timeout=100):
        """
        只在页面就绪且按钮可点击时，点击“新建”
        - 过滤禁用/加载中
        - 避开遮罩拦截
        """
        # 再次确保无遮罩
        overlay = page.locator("div.el-loading-mask")
        try:
            overlay.first.wait_for(state="detached", timeout=timeout)
        except Exception:
            try:
                overlay.first.wait_for(state="hidden", timeout=1000)
            except Exception:
                pass

        new_btn = (
            page.locator("#app")
                .get_by_role("button", name="新建", exact=True)
                .filter(
                    has_not=page.locator('[aria-disabled="true"], .is-disabled, .is-loading')
                )
                .first
        )
        new_btn.wait_for(state="visible", timeout=timeout)
        new_btn.click()

    # ---------------- 入口：如果需要则“新建” ----------------
    def try_create_new_request(self, page, business_type: str):
        """
        进入业务页后，若业务需要“新建”，则稳健点击
        """
        if self.should_create_new(business_type):
            print(f"📌 业务类型 {business_type} ➜ 需要点击『新建』")
            self.click_new_when_ready(page)   # ← 使用稳健版点击
            # page.get_by_role("button", name="新建").click()
        else:
            print(f"📌 业务类型 {business_type} ➜ 不需要点击『新建』，已跳过。")
