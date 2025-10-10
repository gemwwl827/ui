# pages/distribution_trading_page.py
# ✅ 分销买卖独立页面类（兼容你现有数据结构/字段名）
from ._mixins import BankCommonFormMixin  # 复用方向按钮、组合、净价、通用工具

class DistributionTradingPage(BankCommonFormMixin):
    """分销买卖"""
    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()  # 复用组合按钮等

        # === 分销买卖特有元素 ===
        self.payment_date_input = self.page.get_by_role("combobox", name="* 缴款日期")
        self.bid_rate_input = self.page.get_by_role("textbox", name="中标利率(%)")
        self.full_price_input = self.page.get_by_role("textbox", name="* 全价(元)")
        self.distribution_trading_counterparty_input = self.page.get_by_role("textbox", name="* 对手方")
        self.distribution_trading_bond_input = self.page.get_by_role("textbox", name="* 债券", exact=True)

    def fill_form(self, data: dict):
        # 方向
        direction = data.get("transaction_direction", "买入").strip()
        (self.sell_button if direction == "卖出" else self.buy_button).click()
        self.page.wait_for_timeout(300)

        # 组合（可选）
        self.fill_combination(data)

        # 缴款日期
        self.payment_date_input.fill(data["trade_date"])
        self.press_enter()
        self.page.wait_for_timeout(200)

        # 对手方
        self.distribution_trading_counterparty_input.click()
        self.distribution_trading_counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(200)

        # 债券
        self.distribution_trading_bond_input.click()
        self.distribution_trading_bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])
        self.page.wait_for_timeout(200)

        # 净价
        self.clean_price_input.click()
        self.clean_price_input.fill(str(data["price"]))

        # 中标利率（可选）
        bid_yield = data.get("bid_yield")
        if bid_yield not in (None, ""):
            try:
                self.bid_rate_input.click()
                self.bid_rate_input.fill(str(bid_yield))
            except Exception as e:
                print(f"⚠️ 中标利率填充跳过：{e}")

        # 全价
        self.full_price_input.click()
        self.full_price_input.fill(str(data["full_price"]))

        # 入列表
        self.click_join_list()
