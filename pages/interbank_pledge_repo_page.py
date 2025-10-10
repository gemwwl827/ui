from ._mixins import BankCommonFormMixin

class InterbankPledgeRepoPage(BankCommonFormMixin):
    """银行间质押式回购（正/逆）"""
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()
        # 质押式回购特有元素
        self.bank_pledge_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限（天）")
        #回购利率
        self.pledge_repo_rate_click_area = self.page.locator(".el-col > .el-row > div:nth-child(2) > .el-form-item > .el-form-item__content > .el-input > .el-input__wrapper")
        self.pledge_repo_rate_input = self.page.locator("xpath=/html/body/div[7]/div/div/div/div/div/form/div[2]/div/div/div[8]/div/div[2]/div/div/div[1]/div[1]/input")

        self.bank_pledge_repo_amount_input = self.page.get_by_role("textbox", name="* 回购金额（元）")
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")


        self.add_bank_pledge_bond_button_repo = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 折算比例（%） 组合 质押面额（万元）").get_by_role("button").nth(1)
        self.add_bank_pledge_bond_button_repo_reverse_repo = self.page.get_by_role("row", name="债券代码 债券简称 估值净价 债项评级/主体评级 折算比例（%） 质押面额（万元）").get_by_role("button")
        self.pledge_bond_code_input = self.page.get_by_role("textbox", name="请输入")
        #点击表格组合输入框
        self.pledge_combination_select = self.page.locator(".cell > .w-full > .el-input > .el-input__wrapper")
        #表格：交易面额(万)
        # self.bank_pledge_face_amount = self.page.locator(".el-table_4_column_47 > .cell > .el-input > .el-input__wrapper")
        # self.bank_pledge_face_amount_input = self.page.locator("div.el-dialog__body table input.el-input__inner").nth(-1)

        self.bank_pledge_face_amount = self.page.locator(
            ".el-table_3_column_31 > .cell > .el-input > .el-input__wrapper")  # 表格中质押面额容器
        self.bank_pledge_face_amount_input = self.page.locator("div.el-dialog__body table input.el-input__inner").nth(
            -1)  # 表格最后一个质押面额输入框

    def fill_form(self, data: dict):
        direction = data.get("transaction_direction", "逆回购").strip()
        (self.repo_button if direction=="正回购" else self.reverse_repo_button).click()

        # 对手方/日期
        self.set_trade_date(data["trade_date"])
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])

        # 回购参数
        self.bank_pledge_repo_days_input.fill(str(data["repo_days"]))
        self.pledge_repo_rate_click_area.click()
        self.pledge_repo_rate_input.fill(data["repo_rate"])
        self.bank_pledge_repo_amount_input.fill(str(data["repo_amount"]))

        # 资金分配（正回购会走组合）
        if data.get("combination"):
            self.fund_allocation_input.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.locator("//legend[span[contains(text(),'资金分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(data["face_value"])
            self.page.get_by_role("button", name="确定").click()

        # 添加质押券
        (self.add_bank_pledge_bond_button_repo if direction=="正回购" else self.add_bank_pledge_bond_button_repo_reverse_repo).click()
        self.pledge_bond_code_input.fill(data["pledge_bond_code"])
        self.select_option(data["pledge_bond_name"])

        if direction == "正回购":
            if data.get("combination"):
                self.pledge_combination_select.click()
                self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
                self.page.locator("//legend[span[contains(text(),'组合分配')]]/following::input[contains(@class,'el-input__inner')][1]").fill(data["face_value"])
                self.page.get_by_role("button", name="确定").click()
        else:
            self.bank_pledge_face_amount.click()
            self.bank_pledge_face_amount_input.fill(data["face_value"])

        self.click_join_list()
