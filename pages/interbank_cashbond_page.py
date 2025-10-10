from ._mixins import BankCommonFormMixin

class InterbankCashBondPage(BankCommonFormMixin):
    """银行间现券买卖"""

    def __init__(self, page):
        super().__init__(page)
        self.init_bank_elements()  # 初始化通用元素（对手方、交易日期、按钮等）

    def fill_form(self, data: dict):
        """
        填写银行间现券买卖表单
        :param data: Excel 中读取的一条业务指令数据
        """
        # 1. 交易方向（买入/卖出）
        direction = data.get("transaction_direction", "买入").strip()
        (self.sell_button if direction == "卖出" else self.buy_button).click()

        # 2. 填写通用字段（债券、组合、清算速度等）
        self.fill_combination(data)
        self.fill_bank_common_fields(data)
        self.select_settlement_speed(data.get("settlement_speed", "T+0"))

        # 3. 根据多指令模式选择提交方式
        #    - 新建：点击【新建】按钮
        #    - 加入列表并继续：点击【加入列表并继续】，再自动【重置】
        #    - 加入列表：点击【加入列表】（弹窗关闭）
        submit_mode = data.get("multi_mode", "加入列表")
        if submit_mode == "新建":
            self.click_new()
        elif submit_mode == "加入列表并继续":
            self.safe_add_and_continue_bank()  # ✅ 银行间


        else:
            self.click_join_list()

        print(f"[FORM] 已完成指令录入：模式={submit_mode}，方向={direction}，债券={data.get('bond_code')}")






