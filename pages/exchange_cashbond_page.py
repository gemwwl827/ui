#pages/exchange_cashbond_page.py

from ._mixins import ExchangeCommonFormMixin, BankCommonFormMixin

class ExchangeCashBondPage(ExchangeCommonFormMixin, BankCommonFormMixin):
    """交易所现券买卖"""
    def __init__(self, page):
        super().__init__(page)
        self.init_exchange_elements()
        self.init_bank_elements()  # 复用组合/净价等

    def fill_form(self, data: dict):
        direction = data.get("transaction_direction", "买入").strip()
        (self.sell_button if direction == "卖出" else self.buy_button).click()

        # 通用字段
        self.fill_exchange_common_fields(data)
        self.fill_combination(data)

        # 3. 根据多指令模式选择提交方式
        #    - 新建：点击【新建】按钮
        #    - 加入列表并继续：点击【加入列表并继续】，再自动【重置】
        #    - 加入列表：点击【加入列表】（弹窗关闭）
        submit_mode = data.get("multi_mode", "加入列表")
        if submit_mode == "新建":
            self.click_new()
        elif submit_mode == "加入并继续":
            self.safe_add_and_continue_exchange()  # ✅ 交易所

        else:
            self.click_join_list()

        print(f"[FORM] 已完成指令录入：模式={submit_mode}，方向={direction}，债券={data.get('bond_code')}")
