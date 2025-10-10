# pages/interbank_credit_loan_page.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from ._mixins import BankCommonFormMixin


class InterbankCreditLoanPage(BankCommonFormMixin):
    """
    银行间信用拆借（拆入 / 拆出）
    结构：方向(拆入/拆出) + 基本信息 + 金额/期限/利率 + 资金分配 + 账户信息 + 加入列表

    """

    # ------------------------- 元素定义 -------------------------
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()  # 通用元素（对手方、交易日期、加入列表/提交/保存等）

        # 方向切换（拆入/拆出）—— radio 或 tab 都可用
        self.borrow_in_button = self. page.locator("label").filter(has_text="拆入").locator("span").nth(1)
        self.borrow_out_button = self.page.locator("label").filter(has_text="拆出").locator("span").nth(1)

        # 基础字段 / 交易员（有些页面是 combobox，有些是文本框，按需调整）
        self.counterparty_trader_select = self.page.get_by_role("combobox", name="对手方交易员")
        self.our_trader_select = self.page.get_by_role("combobox", name="本方交易员")

        # 期限/利率/金额
        self.bank_loan_days_input = self.page.get_by_role("textbox", name="* 拆借期限（天）")

        # 拆借利率
        # self.bank_loan_rate_click_area = self. page.locator(".el-col > .el-row > div:nth-child(2) > .el-form-item > .el-form-item__content > .el-input > .el-input__wrapper")
        self.bank_loan_rate_input = self. page.locator(
        "//label[contains(normalize-space(),'拆借利率')]"
        "/ancestor::div[contains(@class,'el-row')][1]"
        "//div[contains(@class,'base-input-number')]//input[contains(@class,'el-input__inner')]"
    )

        # 拆借金额
        self.bank_loan_amount_input = self.page.get_by_role("textbox", name="* 拆借金额（万元）")

        #资金分配
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")

        # 清算速度 / 资金账户
        self.clearing_speed_select = self.page.get_by_role("combobox", name=re.compile("清算速度"))
        self.bank_account_info_select = self.page.get_by_role("combobox", name=re.compile("资金账户信息"))



    # ------------------------- 编排入口 -------------------------
    def fill_form(self, data: dict):
        direction = data.get("transaction_direction", "拆出").strip()
        (self.borrow_in_button if direction == "拆入" else self.borrow_out_button).click()

        # 对手方/日期
        self.set_trade_date(data["trade_date"])
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])

        # 拆借参数
        self.bank_loan_days_input.fill(str(data["loan_days"]))
        self.bank_loan_rate_input.click()
        self.bank_loan_rate_input.fill(data["loan_rate"])
        #输入拆借金额
        self.bank_loan_amount_input.fill(str(data["loan_amount_wan"]))

        #输入清算速度
        # 选择清算速度
        self.select_settlement_speed(data.get("settlement_speed", "T+0"))

        # 资金分配（正回购会走组合）
        if data.get("combination"):
            self.fund_allocation_input.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            # self.page.locator(
            #     "//legend[span[contains(text(),'资金分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(
            #     data["face_value"])
            self.page.get_by_role("button", name="确定").click()



        self.click_join_list()
