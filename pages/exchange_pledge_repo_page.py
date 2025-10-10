from ._mixins import ExchangeCommonFormMixin

class ExchangePledgeRepoPage(ExchangeCommonFormMixin):
    """交易所质押式回购"""
    def __init__(self, page):
        super().__init__(page)
        self.init_exchange_elements()
        self.exchange_pledge_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限(天)")
        self.exchange_pledge_repo_rate_input = self.page.get_by_role("textbox", name="* 回购利率(%)")
        self.max_amount_input = self.page.get_by_role("textbox", name="* 上限金额(万元)")
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")

    def fill_form(self, data: dict):
        (self.repo_button if data.get("transaction_direction","逆回购")=="正回购" else self.reverse_repo_button).click()
        self.set_trade_date(data["trade_date"])
        self.exchange_pledge_repo_rate_input.fill(data["repo_rate"])
        self.max_amount_input.fill(str(data["max_amount"]))
        if data.get("combination"):
            self.fund_allocation_input.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.get_by_role("button", name="确定").click()
        self.click_join_list()
