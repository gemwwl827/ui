# pages/exchange_bond_lending_page.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from ._mixins import BankCommonFormMixin


class ExchangeBondLendingPage(BankCommonFormMixin):
    """
    交易所债券借贷（融入 / 融出）
    路由参考：/traderequest/exchange/seclend   （如不同，改成你们实际地址）
    结构：方向(融入/融出) + 基本信息 + 债券表格
    """

    # ------------------------- 元素定义 -------------------------
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()  # 对手方、交易日期、加入列表/提交 等通用元素

        # 方向切换（融入/融出）
        self.lend_in_button  = self.page.locator("label:has-text('融入') span").nth(1)
        self.lend_out_button = self.page.locator("label:has-text('融出') span").nth(1)

        # 对手方（有的项目写“交易对手方”，有的写“对手方”）
        self.counterparty_input = (
            self.page.get_by_role("textbox", name=re.compile(r"\*\s*(交易)?对手方"))
        )

        # 交易员（可能是下拉/输入框，统一 click+select 兜底）
        self.counterparty_trader_select = self.page.get_by_role("combobox", name="对手方交易员")
        self.our_trader_select          = self.page.get_by_role("combobox", name="本方交易员")

        # 页面上方“债券”输入（若你们页面没有这行，可注释掉）
        # BankCommonFormMixin 里通常已有 self.bond_input
        # 若没有可打开下面两行
        # self.bond_input = self.page.get_by_role("textbox", name=re.compile(r"\*\s*债券"))

        # 金额/期限/费率
        self.exchange_lending_amount_input = self.page.get_by_role("textbox", name=re.compile(r"\*\s*借贷(面额|金额)（万元）"))
        self.exchange_lending_days_input   = self.page.get_by_role("textbox", name="* 借贷期限（天）")
        self.exchange_lending_rate_input   = self.page.get_by_role("textbox", name="* 借贷费率（%）")

        # 常见下拉（如需使用，直接在编排里打开）
        self.clearing_speed_select      = self.page.get_by_role("combobox", name=re.compile("清算速度"))
        self.quote_method_select        = self.page.get_by_role("combobox", name=re.compile("报价方式"))
        self.first_settle_select        = self.page.get_by_role("combobox", name=re.compile("首次结算方式"))
        self.maturity_settle_select     = self.page.get_by_role("combobox", name=re.compile("到期结算方式"))
        self.dispute_method_select      = self.page.get_by_role("combobox", name=re.compile("争议解决方式"))
        self.collateral_exchange_select = self.page.get_by_role("combobox", name=re.compile("质押券置换安排"))

        # ===== 表格：添加债券 =====
        # 行头可能是“交易金额（万元）”或“交易面额（万元）”，用正则兜底
        self.add_exchange_lending_bond_button = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 组合 交易面额（万元）").get_by_role("button").nth(1)

        self.add_exchange_lending_bond_button_out = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 交易面额（万元）").get_by_role("button")
        self.table_bond_code_input = self.page.get_by_role("textbox", name="请输入")

        # 表格：组合点击区域（融入场景会出组合弹窗）
        self.table_combination_click = self.page.locator(".cell > .w-full > .el-input > .el-input__wrapper")


        # 表格：交易面额(万)
        self.exchange_lending_face_amount = self.page.locator(".cell > .el-input > .el-input__wrapper")
        self.exchange_lending_face_amount_input = self.page.locator("div.multiple-bond-table .el-table__body-wrapper tbody tr.el-table__row td:last-child input.el-input__inner")

    # ------------------------- 编排入口 -------------------------
    def fill_form(self, data: dict):
        direction = data.get("transaction_direction", "融出").strip()
        (self.lend_in_button if direction == "融入" else self.lend_out_button).click()

        # 对手方/日期
        self.set_trade_date(data["trade_date"])
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])

        #债券
        self.bond_input.fill(data["bond_code"])
        self.page.wait_for_timeout(1000)
        self.select_option(data["bond_full_name"])

        # 借贷参数（借贷天数、借贷利率）
        self.exchange_lending_days_input.fill(str(data["lending_days"]))

        self.exchange_lending_rate_input.click()
        self.exchange_lending_rate_input.fill(data["lending_rate"])

        # self.bank_pledge_repo_amount_input.fill(str(data["repo_amount"]))
        # 输入组合
        self.fill_combination(data)
        #输入交收方式
        self.select_settlement_method(data.get("settlement_speed", "T+0"))


        # 添加质押券
        (self.add_exchange_lending_bond_button if direction == "融入" else self.add_exchange_lending_bond_button_out).click()
        self.table_bond_code_input.fill(data["pledge_bond_code"])
        self.select_option(data["pledge_bond_name"])

        if direction == "融入":
            if data.get("combination"):
                self.table_combination_click .click()
                self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
                self.page.locator(
                    "//legend[span[contains(text(),'组合分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(
                    data["face_value"])
                self.page.get_by_role("button", name="确定").click()
        else:
            self.exchange_lending_face_amount.click()
            self.exchange_lending_face_amount_input.fill(data["face_value"])


