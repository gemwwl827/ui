from ._mixins import FundCommonFormMixin

class OtcFundRedeemPage(FundCommonFormMixin):
    """场外基金 申赎/认购"""
    def __init__(self, page):
        super().__init__(page)
        self.init_fund_elements()

    def fill_form(self, data: dict):
        direction = data.get("transaction_direction","申购").strip()
        if direction == "赎回":
            self.redeem_radio.click()
        elif direction == "认购":
            self.purchase_radio.click()
        else:
            self.subscribe_radio.click()

        self.set_trade_date(data["trade_date"])

        if direction == "赎回":
            self.select_fund_from_popup(data["fund_code"])
            # self.fund_volume_input.fill(data["fund_volume"])  # 如需填写份额可开启
        else:
            self.fill_fund_common(data)
            if direction in ["认购","申购"]:
                self.fund_amount_input.fill(data["fund_amount"])
                # 可选：计划赎回时间
                # self.redemption_time_input.fill(data["redemption_time"]); self.press_enter()

        if direction == "认购":
            # 认购额外对手方（如有差异化逻辑可写这里）
            self.counterparty_fund_input.fill(data["counterparty"])
            self.select_option(data["full_name"])

        self.click_join_list()
