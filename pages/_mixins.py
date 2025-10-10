# ✅ 将“通用字段填写”按业务族拆成 Mixin，页面类多重继承使用
import re
from .base_page import BasePage
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

class BankCommonFormMixin(BasePage):
    """银行间通用：对手方、债券、清算速度、组合等"""
    def init_bank_elements(self):
        self.counterparty_input = self.page.get_by_role("textbox", name="* 交易对手方")
        self.counterparty_input_short = self.page.get_by_role("textbox", name="* 对手方")
        self.bond_input = self.page.get_by_role("textbox", name="* 债券")
        # 清算速度：“现券买卖”组里的 “T+”

        self.settlement_speed_input = self.page.get_by_text("清算速度T+")
        # 交易所：交收方式
        self.settlement_method_input = self.page.get_by_text("交收方式T+")

        self.combination_button_bond = self.page.get_by_role("textbox", name="* 组合")

    def fill_bank_common_fields(self, data: dict):
        self.set_trade_date(data["trade_date"])
        # 对手方
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        # 债券
        self.bond_input.click()
        self.bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])
        # 净价
        self.clean_price_input.click()
        self.clean_price_input.fill(str(data["price"]))
        self.page.wait_for_timeout(1000)

    def select_settlement_speed(self, speed_text: str):
        """银行间清算速度选择"""
        if not speed_text:
            return
        self.settlement_speed_input.click()
        self.page.wait_for_timeout(1000)
        try:
            self.page.get_by_role("option", name=speed_text).locator("span").click()
            self.page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            print(f"❌ 清算速度 '{speed_text}' 未找到")

    def select_settlement_method(self, method_text: str):
        """交易所交收方式选择"""
        if not method_text:
            return
        self.settlement_method_input.click()
        self.page.wait_for_timeout(3000)
        try:
            self.page.get_by_role("option", name=method_text).locator("span").click()
            self.page.wait_for_timeout(3000)
        except PlaywrightTimeoutError:
            print(f"❌ 交收方式 '{method_text}' 未找到")

    def fill_combination(self, data: dict):
        if not data.get("combination"):
            return
        self.combination_button_bond.click()
        self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
        # 组合分配面额
        self.page.locator(
            "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class,'el-input__inner')][1]"
        ).fill(data["face_value"])
        self.page.get_by_role("button", name="确定").click()











class ExchangeCommonFormMixin(BasePage):
    """交易所通用"""
    def init_exchange_elements(self):
        self.counterparty_input_exchange_ag = self.page.get_by_role("textbox", name="* 交易对手方")
        self.counterparty_input_exchange = self.page.get_by_role("textbox", name="* 对手方")
        self.bond_input = self.page.get_by_role("textbox", name="* 债券")

    def fill_exchange_common_fields(self, data: dict):
        # 债券
        self.bond_input.click()
        self.bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])
        # 日期
        self.set_trade_date(data["trade_date"])
        # 对手方
        self.counterparty_input_exchange.click()
        self.counterparty_input_exchange.fill(data["counterparty"])
        self.select_option(data["full_name"])
        # 净价
        self.clean_price_input.click()
        self.clean_price_input.fill(str(data["price"]))

class FundCommonFormMixin(BasePage):
    """基金通用（场内/场外共用）"""
    def init_fund_elements(self):
        self.subscribe_radio = self.page.locator("label:has-text('申购') span").nth(1)
        self.redeem_radio   = self.page.locator("label").filter(has_text=re.compile(r"^赎回$")).locator("span").nth(1)
        self.purchase_radio = self.page.locator("label").filter(has_text="认购").locator("span").nth(1)

        self.fund_input   = self.page.get_by_role("textbox", name="* 基金")
        self.combination_input = self.page.get_by_role("textbox", name="* 组合")
        self.counterparty_fund_input = self.page.get_by_role("textbox", name="对手方")
        self.fund_price_input  = self.page.get_by_role("textbox", name="* 交易价格(元)")
        self.fund_amount_input = self.page.get_by_role("textbox", name="* 交易金额(元)")
        self.fund_volume_input = self.page.get_by_role("textbox", name="* 份额")
        self.redemption_time_input = self.page.get_by_role("combobox", name="计划赎回时间")
        self.custody_account = self.page.get_by_role("combobox", name="* 托管账户信息")
        self.custody_account_select = self.page.get_by_role("option", name="深交所02_深交所_0899035728")

        # 场外赎回弹窗
        self.fund_popup_button = self.page.locator(".wrapper > i > svg")
        self.fund_redeem_select_button = self.page.get_by_role("button", name="确定")

    def fill_fund_common(self, data: dict):
        self.set_trade_date(data["trade_date"])
        # 基金
        self.fund_input.click()
        self.fund_input.fill(data["fund_code"])
        self.select_option(data["fund_full_name"])
        # 组合
        if data.get("combination"):
            self.combination_input.click()
            self.page.get_by_role("treeitem", name=data["combination"]).locator("span").nth(1).click()
            self.page.get_by_role("button", name="确定").click()
        # 对手方
        self.counterparty_fund_input.click()
        self.counterparty_fund_input.fill(data["counterparty"])
        self.select_option(data["full_name"])

    # 场外基金赎回：弹窗选择
    def select_fund_from_popup(self, fund_code: str):
        self.fund_popup_button.click()
        self.page.get_by_role("heading", name="选择基金").wait_for(timeout=5000)
        self.page.locator(f"text={fund_code}").wait_for(state="visible", timeout=10000)
        row = self.page.get_by_role("row", name=re.compile(f"^{fund_code}"))
        row.locator("span").nth(1).click()
        self.fund_redeem_select_button.click()
