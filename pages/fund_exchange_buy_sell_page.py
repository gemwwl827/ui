from ._mixins import FundCommonFormMixin

class FundExchangeBuySellPage(FundCommonFormMixin):
    """场内基金买卖"""
    def __init__(self, page):
        super().__init__(page)
        self.init_fund_elements()

    def fill_form(self, data: dict):
        (self.sell_button if data.get("transaction_direction","买入")=="卖出" else self.buy_button).click()
        self.fill_fund_common(data)
        self.fund_price_input.fill(data["fund_price"])
        self.fund_volume_input.fill(data["fund_volume"])
        self.custody_account.click()
        self.custody_account_select.click()
        self.click_join_list()
