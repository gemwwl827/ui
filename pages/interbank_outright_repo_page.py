from ._mixins import BankCommonFormMixin

class InterbankOutrightRepoPage(BankCommonFormMixin):
    """银行间买断式回购"""
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()
        self.first_net_price_input = self.page.get_by_role("textbox", name="* 首次净价（元）")
        self.bank_outright_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限（天）")
        self.bank_outright_repo_rate_click_area = self.page.locator(".el-col > .el-row > div:nth-child(2) > .el-form-item > .el-form-item__content > .el-input > .el-input__wrapper")
        self.bank_outright_repo_rate_input = self.page.locator("xpath=/html/body/div[1]/div/section/div/div[2]/div/form/form/div[2]/div/div[1]/div[8]/div/div[2]/div/div/div[1]/div[1]/input")
        self.bank_outright_combination_button = self.page.get_by_role("textbox", name="* 组合")

    def fill_form(self, data: dict):
        (self.repo_button if data.get("transaction_direction","逆回购")=="正回购" else self.reverse_repo_button).click()

        # 对手方/日期/债券
        self.counterparty_input.fill(data["counterparty"]); self.select_option(data["full_name"])
        self.set_trade_date(data["trade_date"])
        self.bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])

        # 回购参数
        self.bank_outright_repo_days_input.fill(str(data["repo_days"]))
        self.bank_outright_repo_rate_click_area.click(); self.bank_outright_repo_rate_input.fill(data["repo_rate"])
        self.first_net_price_input.fill(data["first_net_price"])

        # 组合
        if data.get("combination"):
            self.bank_outright_combination_button.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.locator("//legend[span[contains(text(),'组合分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(data["face_value"])
            self.page.get_by_role("button", name="确定").click()
