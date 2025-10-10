from ._mixins import ExchangeCommonFormMixin

class ExchangeAgreementRepoPage(ExchangeCommonFormMixin):
    """交易所协议式回购 正/逆"""
    def __init__(self, page):
        super().__init__(page)
        self.init_exchange_elements()
        self.exchange_agreement_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限(天)")
        self.exchange_agreement_repo_rate_input = self.page.get_by_role("textbox", name="* 回购利率(%)")
        self.exchange_agreement_repo_amount_input = self.page.get_by_role("textbox", name="* 回购金额(万元)")
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")
        self.add_pledge_bond_button_repo = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 折算比例（%） 组合 券面总额（万元）").get_by_role("button").nth(1)
        self.add_pledge_bond_button_repo_reverse_repo = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 债项评级/主体评级 折算比例（%） 券面总额（万元）").get_by_role("button")
        self.pledge_bond_code_input = self.page.get_by_role("textbox", name="请输入")
        self.pledge_combination_select = self.page.locator(".cell > .w-full > .el-input > .el-input__wrapper")
        self.pledge_face_amount = self.page.locator("td:nth-child(7) > .cell")
        self.pledge_face_amount_input = self.page.locator("table input.el-input__inner").nth(-1)

    def fill_form(self, data: dict):
        (self.repo_button if data.get("transaction_direction","逆回购")=="正回购" else self.reverse_repo_button).click()
        self.set_trade_date(data["trade_date"])
        # 对手方
        self.counterparty_input_exchange_ag.click()
        self.counterparty_input_exchange_ag.fill(data["counterparty"])
        self.select_option(data["full_name"])
        # 回购参数
        self.exchange_agreement_repo_days_input.fill(str(data["repo_days"]))
        self.exchange_agreement_repo_rate_input.fill(data["repo_rate"])
        self.exchange_agreement_repo_amount_input.fill(str(data["repo_amount"]))
        # 资金分配
        if data.get("combination"):
            self.fund_allocation_input.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.get_by_role("button", name="确定").click()

        # 添加质押券
        add_btn = self.add_pledge_bond_button_repo if data.get("transaction_direction")=="正回购" else self.add_pledge_bond_button_repo_reverse_repo
        add_btn.click()
        self.pledge_bond_code_input.fill(data["pledge_bond_code"])
        self.select_option(data["pledge_bond_name"])

        if data.get("transaction_direction")=="正回购" and data.get("combination"):
            self.pledge_combination_select.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.locator("//legend[span[contains(text(),'组合分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(data["face_value"])
            self.page.get_by_role("button", name="确定").click()
        else:
            self.pledge_face_amount.click()
            self.pledge_face_amount_input.fill(data["face_value"])
