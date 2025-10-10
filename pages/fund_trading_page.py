# ✅ 文件: pages/fund_trading_page.py
from pages.base_page import BasePage

class FundTradingPage(BasePage):
    def __init__(self, page):
        super().__init__(page)

    def fill_form(self, data: dict):
        direction = data.get("交易方向", "买入").strip()
        if direction == "赎回":
            self.page.get_by_text("赎回").click()
        elif direction == "申购":
            self.page.get_by_text("申购").click()
        elif direction == "卖出":
            self.page.get_by_text("卖出").click()
        else:
            self.page.get_by_text("买入").click()

        self.page.wait_for_timeout(1000)

        self.fill_trade_date(data["交易日期"])

        self.page.get_by_role("textbox", name="* 基金代码").click()
        self.page.get_by_role("textbox", name="* 基金代码").fill(data["基金代码"])
        self.select_option(data["基金名称"])

        self.page.get_by_role("textbox", name="* 数量").fill(str(data["数量"]))

        if data.get("组合"):
            self.page.get_by_role("textbox", name="* 组合").click()
            self.select_option(data["组合"])
            self.page.locator("//legend[span[contains(text(), '组合分配')]]/following::input").fill(data['面额'])
            self.page.get_by_role("button", name="确定").click()

        # 托管账户
        if data.get("托管账户"):
            self.page.get_by_role("textbox", name="* 托管账户").click()
            self.select_option(data["托管账户"])

        # 计划赎回时间（申赎类）
        if data.get("计划赎回时间"):
            self.page.get_by_role("textbox", name="计划赎回时间").fill(data["计划赎回时间"])

        self.submit_form_by_mode(data.get("操作模式(多个指令)", "加入列表"))
