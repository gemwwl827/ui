# pages/interbank_bond_lending_page.py
# -*- coding: utf-8 -*-
from ._mixins import BankCommonFormMixin

class InterbankBondLendingPage(BankCommonFormMixin):
    """
    银行间债券借贷（融入 / 融出）
    路由参考：/traderequest/bank/seclend
    结构：方向(融入/融出) + 基本信息 + 债券表格
    """

    # ------------------------- 元素定义 -------------------------
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()  # 通用：对手方、交易日期、按钮等

        # 方向切换（融入/融出）
        self.lend_in_button  = self.page.locator("label:has-text('融入') span").nth(1)
        self.lend_out_button = self.page.locator("label:has-text('融出') span").nth(1)

        #对手方
        self.counterparty_input = self.page.get_by_role("textbox", name="* 对手方")


        # 交易员（可能是 combobox 或输入框，统一用 click+select 封装兜底）
        self.counterparty_trader_select = self.page.get_by_role("combobox", name="对手方交易员")
        self.our_trader_select          = self.page.get_by_role("combobox", name="本方交易员")


        # 上方“组合”输入（点击唤起树）
        # self.combination_click = self.page.locator(
        #     "//label[span[normalize-space()='组合']]/following::div[contains(@class,'el-input__wrapper')][1]"
        # )

        # 金额/期限/费率
        self.lending_amount_input = self.page.get_by_role("textbox", name="* 借贷面额（万元）")
        self.lending_days_input   = self.page.get_by_role("textbox", name="* 借贷期限（天）")
        self.lending_rate_input   = self.page.get_by_role("textbox", name="* 借贷费率（%）")

        # 其它下拉（有的页面不强制；保留以便需要时直接用）
        self.clearing_speed_select     = self.page.get_by_role("combobox", name="清算速度")
        self.quote_method_select       = self.page.get_by_role("combobox", name="报价方式")
        self.first_settle_select       = self.page.get_by_role("combobox", name="* 首次结算方式")
        self.maturity_settle_select    = self.page.get_by_role("combobox", name="* 到期结算方式")
        self.dispute_method_select     = self.page.get_by_role("combobox", name="争议解决方式")
        self.collateral_exchange_select= self.page.get_by_role("combobox", name="质押券置换安排")

        # 表格：添加一行债券
        #融入：点击+
        self.add_bond_lending_button   = self.page.get_by_role(
            "row", name="债券代码 债券简称 估值净价 组合 交易面额（万元）"
        ).get_by_role("button").nth(1)
        #融出：点击+
        self.add_bond_lending_button_out = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 交易面额（万元）").get_by_role("button")

        self.table_bond_code_input     = self.page.get_by_role("textbox", name="请输入")

        #表格：点击组合
        self.table_combination_click   = self.page.locator(".cell > .w-full > .el-input > .el-input__wrapper")
        # 表格：交易面额(万)
        self.bank_lending_face_amount = self.page.locator(".cell > .el-input > .el-input__wrapper")
        self.bank_lending_face_amount_input = self.page.locator("div.multiple-bond-table .el-table__body-wrapper tbody tr.el-table__row td:last-child input.el-input__inner")

    # ------------------------- 编排入口 -------------------------
    def fill_form(self, data: dict):
        """
        表单输入
        """
        #输入交易方向
        self._set_direction(data)
        #输入对手方+日期
        self._fill_counterparty_block(data)
        #输入组合
        self.fill_combination(data)
        #输入借贷天数和借贷利率
        self._fill_lending_params(data)

        # 选择清算速度
        self.select_settlement_speed(data.get("settlement_speed", "T+0"))


        #输入表格：质押券
        self._add_bond_row(data)

    # ------------------------- 私有步骤 -------------------------
    def _set_direction(self, data: dict):
        direction = data.get("transaction_direction", "融出").strip()
        (self.lend_in_button if direction == "融入" else self.lend_out_button).click()

    def _fill_counterparty_block(self, data: dict):

        # 对手方/日期/债券
        self.set_trade_date(data["trade_date"])
        self.counterparty_input.click()

        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])

        self.bond_input.fill(data["bond_code"])
        self.page.wait_for_timeout(1000)
        self.select_option(data["bond_full_name"])

    def _fill_lending_params(self, data: dict):
        #输入借贷天数和借贷利率
        if data.get("lending_days") is not None:
            self.lending_days_input.fill(str(data["lending_days"]))
        if data.get("lending_rate") is not None:
            self.lending_rate_input.click()
            self.lending_rate_input.fill(str(data["lending_rate"]))

    # def _fill_misc_selects(self, data: dict):
    #     self._click_and_select(self.quote_method_select,        data.get("quote_method"))
    #     self._click_and_select(self.clearing_speed_select,      data.get("clearing_speed"))
    #     self._click_and_select(self.first_settle_select,        data.get("first_settle"))
    #     self._click_and_select(self.maturity_settle_select,     data.get("maturity_settle"))
    #     self._click_and_select(self.dispute_method_select,      data.get("dispute_method"))
    #     self._click_and_select(self.collateral_exchange_select, data.get("collateral_exchange"))

    def _add_bond_row(self, data: dict):
        """表格里添加债券（可选）"""
        direction = data.get("transaction_direction", "融出").strip()
        # if not data.get("pledge_bond_code"):
        #     return

        (self.add_bond_lending_button if direction == "融入" else self.add_bond_lending_button_out).click()

        self.table_bond_code_input.fill(data["pledge_bond_code"])
        self.page.wait_for_timeout(1000)
        if data.get("pledge_bond_name"):
            self.select_option(data["pledge_bond_name"])

        # 表格组合（仅融入才需要）
        if direction == "融入":
            if data.get("combination"):
                self.table_combination_click.click()
                self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
                self.page.locator(
                    "//legend[span[contains(text(),'组合分配')]]/following::input[contains(@class,'el-input__inner')][1]"
                ).fill(data["face_value"])
                self.page.get_by_role("button", name="确定").click()
        else:
            self.bank_lending_face_amount.click()
            self.bank_lending_face_amount_input.fill(data["face_value"])
            self.page.wait_for_timeout(3000)

    # ------------------------- 通用小工具 -------------------------
    # def _click_and_select(self, locator, value: str | None):
    #     """点击一个下拉并选择 value（value 为空则跳过）"""
    #     if not value:
    #         return
    #     try:
    #         locator.click()
    #         self.select_option(value)
    #     except Exception:
    #         pass  # 某些页面字段不是必填/不存在时忽略
    #
    # def _pick_combination_in_tree(self, click_locator, combination_name: str):
    #     """点击组合输入 → 树中选择 → 若有确定按钮则点确定"""
    #     try:
    #         click_locator.click()
    #         self.page.get_by_role("treeitem", name=combination_name).locator("span").nth(1).click()
    #         # 若有“确定”按钮则点击
    #         if self.page.get_by_role("button", name="确定").is_visible():
    #             self.page.get_by_role("button", name="确定").click()
    #     except Exception:
    #         pass
    #
    # def _fill_popup_amount(self, amount: str):
    #     """在‘组合分配/资金分配’弹窗里填入金额（常见弹窗兜底）"""
    #     try:
    #         input_box = self.page.locator(
    #             "//legend[span[contains(text(),'组合分配') or contains(text(),'资金分配')]]"
    #             "/following::input[contains(@class,'el-input__inner')][1]"
    #         )
    #         input_box.fill(amount)
    #         if self.page.get_by_role("button", name="确定").is_visible():
    #             self.page.get_by_role("button", name="确定").click()
    #     except Exception:
    #         pass
    #
    # def _fill_last_table_input(self, value: str):
    #     """把值填到表格里最后一个输入框（适配不同列顺序）"""
    #     try:
    #         self.page.locator("//table//input[contains(@class,'el-input__inner')]").last.fill(value)
    #     except Exception:
    #         pass
