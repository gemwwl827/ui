from ._mixins import FundCommonFormMixin

class FundExchangeRedeemPage(FundCommonFormMixin):
    """场内基金申赎"""
    def __init__(self, page):
        super().__init__(page)
        self.init_fund_elements()

    def fill_form(self, data: dict):
        direction = data.get("transaction_direction","申购").strip()
        if direction == "赎回":
            self.redeem_radio.click()
        else:
            self.subscribe_radio.click()

        self.fill_fund_common(data)

        if direction == "赎回":
            self.fund_volume_input.fill(data["fund_volume"])
        else:
            # 申购：金额
            self.fund_amount_input.fill(data["fund_amount"])
            # 申购：可选计划赎回时间（留作你后续打开）
            # self.redemption_time_input.fill(data["redemption_time"]); self.press_enter()

        self.custody_account.click()
        self.custody_account_select.click()
        self.click_join_list()
