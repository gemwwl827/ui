# ✅ 文件: pages/ficc_ui_case_9_page_bond_risk.py





import datetime  # 用于获取当前时间，生成导出文件名时使用
import re  # 提供正则表达式支持
from pathlib import Path

import pandas as pd  # 用于读取和处理 Excel 数据
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError  # 引入 Playwright 同步 API，用于自动化浏览器交互

from engine.form_navigator import TradeFormNavigator  # 用于导航判断，业务是否新建

from engine.form_dispatcher import FormDispatcher



# ✅ 模块调用
from engine.data_loader import load_grouped_test_data  # 数据读取 单独整理到一个模块


# ===============================
# ✅ 页面类：自动化交易表单输入与审批操作
# ===============================
# 页面类：封装银行间及交易所多类债券交易业务的页面操作
class InterbankBondTradingPage(TradeFormNavigator):  # ✅ 继承导航基类，支持 navigate()
    def __init__(self, page: Page, test_data_file: str):
        self.page = page  # Playwright 页面实例（用于元素定位和操作）
        self.test_data_file = test_data_file  # Excel 文件路径（用于读取与反写）
        self.test_data = load_grouped_test_data(test_data_file)  # 加载并按编号-子编号分组数据
        self.failed_asserts = []  # 存储断言失败信息（用于报错输出）
        self.assertion_results = []  # 记录所有断言结果（成功、失败、未匹配）
        self.failed_cases_summary = []  # ✅【新增】用于记录失败断言的详细信息，用于集中打印或写入Allure

        # 通用元素初始化（适用于所有表单）
        #✅ 这是“初始化页面元素”的入口
        #在类的构造方法 __init__() 中调用该方法，提前完成本业务所需页面元素（如输入框、按钮、弹窗等）的绑定，避免后续反复用 self.page.get_by_role(...) 定位。

        self.init_common_elements()
        # 银行间现券买卖元素（买入/卖出、净价等）
        self.init_interbank_cashbond_elements()
        # 银行间质押式回购页面元素（资金分配、面额等）
        self.init_interbank_pledge_repo_elements()
        # 银行间买断式回购页面元素（期限、组合、净价等）
        self.init_interbank_outright_repo_elements()
        # 交易所现券买卖页面元素（仅“对手方”）
        self.init_exchange_cashbond_elements()
        # 交易所协议式回购页面元素（期限、利率、金额、面额等）
        self.init_exchange_agreement_repo_elements()
        # 交易所质押式回购页面元素（利率、上限金额、券面金额等）
        self.init_exchange_pledge_repo_elements()
        #分销买卖
        self.init_other_distribution_trading()

    # ===============================
    # ✅ 公共元素初始化方法
    # ===============================

    # ✅ 公共元素初始化（适用于大多数业务）
    def init_common_elements(self):
        # ========= 基础通用元素 =========
        self.buy_button = self.page.get_by_text("买入")
        self.sell_button = self.page.get_by_text("卖出")

        self.repo_button = self.page.locator("label").filter(has_text="正回购").locator("span").nth(1)  # 正回购单选按钮
        self.reverse_repo_button = self.page.locator("label").filter(has_text="逆回购").locator("span").nth(1)  # 逆回购单选按钮

        self.counterparty_input = self.page.get_by_role("textbox", name="* 交易对手方")
        self.bond_input = self.page.get_by_role("textbox", name="* 债券")
        self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")
        self.clean_price_input = self.page.get_by_label("净价(元)")
        # 封装下拉框元素（用于点击展开选项）
        self.settlement_speed_input = self.page.locator("div").filter(has_text=re.compile(r"^T\+0$")).nth(4)

        self.repo_days_input = self.page.get_by_role("textbox", name="* 回购期限（天）")  # 回购期限

        # ========= 实际对手方 =========
        self.actual_counterparty_input = self.page.get_by_role("textbox", name="实际对手方")
        self.actual_counterparty_option = self.page.get_by_role("option", name="华安华润信托1号")  # 可考虑参数化

        # ========= 基金通用元素 =========
        # 方向
        self.subscribe_radio = self.page.locator("label").filter(has_text="申购").locator("span").nth(1)  # 单选框：申购
        self.redeem_radio = self.page.locator("label").filter(has_text=re.compile(r"^赎回$")).locator("span").nth(1)  # 单选框：赎回

        # 基金选择
        self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")  # 必填：交易日期
        self.fund_input = self.page.get_by_role("textbox", name="* 基金")  # 必填：基金
        self.combination_input = self.page.get_by_role("textbox", name="* 组合")  # 必填：组合
        self.redemption_time_input = self.page.get_by_role("combobox", name="计划赎回时间")  # 选填：计划赎回时间
        self.counterparty_fund_input = self.page.get_by_role("textbox", name="对手方")

        # 份额输入框
        self.fund_volume_input = self.page.get_by_role("textbox", name="* 份额")  # 必填：基金份额

        # 交易金额
        self.amount_input = self.page.get_by_role("textbox", name="* 交易金额(元)")  # 必填：交易金额

        # 托管账户信息
        self.custody_account = self.page.get_by_role("combobox", name="* 托管账户信息")  # 必填：托管账户信息
        self.custody_account_select = self.page.get_by_role("option", name="深交所02_深交所_0899035728")  # 示例选项值，可参数化









        # ========= 操作按钮 =========
        self.add_to_list_button = self.page.get_by_role("button", name="加入列表", exact=True)  # 提交前加入列表
        self.add_to_list_and_continue_button = self.page.get_by_role("button", name="加入列表并继续")
        self.submit_button = self.page.get_by_role("button", name="提交")  # 提交申请
        self.risk_check = self.page.get_by_role("button", name="风控检查")  # 风控检查按钮
        self.save_button = self.page.get_by_role("link", name=" 保存")  # 保存申请

        # ========= 风控弹窗相关 =========
        self.risk_approve_button = self.page.get_by_label("风控信息").get_by_role("button", name="提交")  # 风控弹窗中的提交
        self.ignore_warning_button = self.page.get_by_role("button", name="忽略警告继续提交")  # 忽略警告按钮
        self.approve_button = self.page.get_by_role("button", name="提交", exact=True)  # 提交按钮（审批/风控）

        # ========= 审批菜单 =========
        self.menu_nav = self.page.get_by_role("menuitem", name="交易申请").locator("span")  # 主菜单 -> 交易申请
        self.approval_list = self.page.get_by_text("审批列表")  # 左侧导航 -> 审批列表
        self.pending_approval_link = self.page.get_by_role("link", name="待办审批")  # 待办审批链接

        # ========= 入仓菜单导航 =========
        self.clearing_management_menu = self.page.get_by_text("清算管理")  # 主菜单 -> 清算管理
        self.reconciliation_confirmation_menu = self.page.get_by_text("核对确认")  # 子菜单 -> 核对确认
        self.application_confirmation_link = self.page.get_by_role("link", name="申请确认入仓")  # 入仓确认链接

        # ========= 日期控件（入仓页面） =========
        self.transaction_date_group = self.page.get_by_role("group", name="交易日期")  # 日期组容器
        self.clear_date_button = self.transaction_date_group.get_by_role("img").nth(1)  # 清空按钮
        self.start_date_input = self.page.get_by_role("combobox", name="开始日期")  # 起始日期
        self.end_date_input = self.page.get_by_role("combobox", name="结束日期")  # 截止日期
        self.query_button = self.page.get_by_role("button", name="查询")  # 查询按钮


    # ✅ 银行间现券买卖特有元素
    def init_interbank_cashbond_elements(self):
        self.combination_button_bond = self.page.get_by_role("textbox", name="* 组合") # 点击组合选择

    # ✅ 银行间质押式回购特有元素（含正/逆回购）
    def init_interbank_pledge_repo_elements(self):

        self.bank_pledge_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限（天）")  # 回购期限

        self.pledge_repo_rate_click_area = self.page.locator(  # 回购利率点击激活区域
            ".el-col > .el-row > div:nth-child(2) > .el-form-item > .el-form-item__content > .el-input > .el-input__wrapper")
        self.pledge_repo_rate_input = self.page.locator(  # 回购利率输入框
            "xpath=/html/body/div[7]/div/div/div/div/div/form/div[2]/div/div/div[8]/div/div[2]/div/div/div[1]/div[1]/input")


        self.bank_pledge_repo_amount_input = self.page.get_by_role("textbox", name="* 回购金额（元）")  # 回购金额输入框
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")  # 资金分配输入框

        # 正回购添加质押券按钮
        self.add_bank_pledge_bond_button_repo = self.page.get_by_role("row",
                                                                 name="债券代码 债券简称 估值净价 折算比例（%） 组合 质押面额（万元）").get_by_role("button").nth(1)

        # 逆回购添加质押券按钮
        self.add_bank_pledge_bond_button_repo_reverse_repo = self.page.get_by_role("row",
                                                                              name="债券代码 债券简称 估值净价 债项评级/主体评级 折算比例（%） 质押面额（万元）").get_by_role( "button")
        self.pledge_bond_code_input = self.page.get_by_role("textbox", name="请输入")  # 质押债券代码输入框


        self.pledge_combination_select = self.page.locator(".cell > .w-full > .el-input > .el-input__wrapper")  # 激活组合树弹窗
        self.pledge_combination_item = lambda name: self.page.get_by_role("treeitem", name=name).locator("span").nth(1)  # 组合名称项
        self.pledge_face_value_input = self.page.locator(  # 组合分配中的质押面额输入框
            "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]")
        self.pledge_confirm_button = self.page.get_by_role("button", name="确定")  # 确认质押券选择按钮


        self.bank_pledge_face_amount = self.page.locator(".el-table_3_column_31 > .cell > .el-input > .el-input__wrapper")  # 表格中质押面额容器
        self.bank_pledge_face_amount_input = self.page.locator("div.el-dialog__body table input.el-input__inner").nth(-1)  # 表格最后一个质押面额输入框

    # ✅ 银行间买断式回购特有元素（正/逆回购 + 常规字段）
    def init_interbank_outright_repo_elements(self):

        # self.counterparty_input = self.page.get_by_role("textbox", name="* 交易对手方")  # 交易对手方
        # self.bond_input = self.page.get_by_role("textbox", name="* 债券")  # 债券代码
        # self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")  # 交易日期

        self.first_net_price_input = self.page.get_by_role("textbox", name="* 首次净价（元）")  # 封装“首次净价（元）”输入框
        self.bank_outright_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限（天）")  # 回购天数输入框
        self.bank_outright_repo_rate_click_area = self.page.locator(  # 回购利率激活区域
            ".el-col > .el-row > div:nth-child(2) > .el-form-item > .el-form-item__content > .el-input > .el-input__wrapper"
        )
        self.bank_outright_repo_rate_input = self.page.locator(  # 回购利率输入框
            "xpath=/html/body/div[1]/div/section/div/div[2]/div/form/form/div[2]/div/div[1]/div[8]/div/div[2]/div/div/div[1]/div[1]/input"
        )
        self.bank_outright_combination_button = self.page.get_by_role("textbox", name="* 组合")  # 组合选择输入框（点击后弹出树）

        # 银行间买断式回购入仓信息修改
        self.trader_selector = self.page.get_by_role("combobox", name="* 本方交易员")  # 本方交易员下拉框
        self.trader_option = self.page.get_by_text("李亮")  # 选项：李亮
    # ✅ 交易所现券买卖特有元素
    def init_exchange_cashbond_elements(self):
        self.counterparty_input_exchange = self.page.get_by_role("textbox", name="* 对手方")  # 交易所对手方输入框
    # ✅ 交易所协议式回购特有元素
    def init_exchange_agreement_repo_elements(self):
        # self.repo_button = self.page.locator("label").filter(has_text="正回购").locator("span").nth(1)  # 正回购按钮
        # self.reverse_repo_button = self.page.locator("label").filter(has_text="逆回购").locator("span").nth(
        #     1)  # 逆回购按钮
        self.counterparty_input = self.page.get_by_role("textbox", name="* 交易对手方")  # 交易对手方
        self.bond_input = self.page.get_by_role("textbox", name="* 债券")  # 债券代码
        self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")  # 交易日期


        self.exchange_agreement_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限(天)")  # 回购期限
        self.exchange_agreement_repo_rate_input = self.page.get_by_role("textbox", name="* 回购利率(%)")  # 回购利率
        self.exchange_agreement_repo_amount_input = self.page.get_by_role("textbox", name="* 回购金额(万元)")  # 回购金额（万元）
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")  # 资金分配输入框
        self.add_agreement_bond_button_repo = self.page.get_by_role("row",
                                                                 name="债券代码 债券简称 估值净价 折算比例（%） 组合 券面总额（万元）").get_by_role(
            "button").nth(1)  # 正回购添加质押券按钮
        self.add_agreement_bond_button_repo_reverse_repo = self.page.get_by_role("row",
                                                                              name="债券代码 债券简称 估值净价 债项评级/主体评级 折算比例（%） 券面总额（万元）").get_by_role(
            "button")  # 逆回购添加质押券按钮
        self.pledge_bond_code_input = self.page.get_by_role("textbox", name="请输入")  # 债券代码输入
        self.pledge_combination_select = self.page.locator(
            ".cell > .w-full > .el-input > .el-input__wrapper")  # 激活组合树
        self.pledge_combination_item = lambda name: self.page.get_by_role("treeitem", name=name).locator(
            "span").nth(1)  # 组合项
        self.pledge_face_value_input = self.page.locator(
            "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]")  # 面额输入框
        self.pledge_confirm_button = self.page.get_by_role("button", name="确定")  # 提交按钮
        self.combination_button = self.page.locator(
            ".cell > .w-full > .el-input > .el-input__wrapper > .el-input__suffix > .el-input__suffix-inner > .el-icon > svg")  # 点击组合选择按钮
        self.pledge_face_amount = self.page.locator("td:nth-child(7) > .cell")  # 券面总额容器（逆回购）
        self.pledge_face_amount_input = self.page.locator("table input.el-input__inner").nth(-1)  # 券面总额输入框（逆回购）
    # ✅ 交易所质押式回购特有元素
    def init_exchange_pledge_repo_elements(self):
        # self.repo_button = self.page.locator("label").filter(has_text="正回购").locator("span").nth(1)  # 正回购按钮
        # self.reverse_repo_button = self.page.locator("label").filter(has_text="逆回购").locator("span").nth(
        #     1)  # 逆回购按钮
        self.counterparty_input = self.page.get_by_role("textbox", name="* 交易对手方")  # 交易对手方输入框
        self.bond_input = self.page.get_by_role("textbox", name="* 债券")  # 债券代码输入框
        self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")  # 交易日期选择框



        self.exchange_pledge_repo_days_input = self.page.get_by_role("textbox", name="* 回购期限(天)")  # 回购天数输入框
        self.exchange_pledge_repo_rate_input = self.page.get_by_role("textbox", name="* 回购利率(%)")  # 回购利率输入框
        self.max_amount_input = self.page.get_by_role("textbox", name="* 上限金额(万元)")  # 上限金额输入框
        self.fund_allocation_input = self.page.get_by_role("textbox", name="* 资金分配")  # 资金分配输入框
        self.add_pledge_bond_button_repo = self.page.get_by_role("row",
                                                                 name="债券代码 债券简称 估值净价 折算比例（%） 组合 券面总额（万元）").get_by_role(
            "button")  # 正回购添加债券按钮
        self.add_pledge_bond_button_repo_reverse_repo = self.page.get_by_role("row",
                                                                              name="债券代码 债券简称 估值净价 债项评级/主体评级 折算比例（%） 券面总额（万元）").get_by_role(
            "button")  # 逆回购添加债券按钮
        self.pledge_bond_code_input = self.page.get_by_role("textbox", name="请输入")  # 债券代码输入
        self.pledge_combination_select = self.page.locator(
            ".cell > .w-full > .el-input > .el-input__wrapper")  # 激活组合树选择器
        self.pledge_combination_item = lambda name: self.page.get_by_role("treeitem", name=name).locator(
            "span").nth(1)  # 组合树中具体项
        self.pledge_face_value_input = self.page.locator(
            "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]")  # 面额输入框
        self.pledge_confirm_button = self.page.get_by_role("button", name="确定")  # 组合提交按钮
        self.combination_button = self.page.locator(
            ".cell > .w-full > .el-input > .el-input__wrapper > .el-input__suffix > .el-input__suffix-inner > .el-icon > svg")  # 点击组合按钮
        self.pledge_face_amount = self.page.locator("td:nth-child(7) > .cell")  # 券面总额容器
        self.pledge_face_amount_input = self.page.locator("table input.el-input__inner").nth(-1)  # 券面总额输入框（逆回购）

    def init_other_distribution_trading(self):
        # ✅ 缴款日期选择框
        self.payment_date_input = self.page.get_by_role("combobox", name="* 缴款日期")  # 缴款日期选择框
        # ✅ 中标利率输入框
        self.bid_rate_input = self.page.get_by_role("textbox", name="中标利率(%)")  # 中标利率输入框
        # ✅ 全价输入框
        self.full_price_input = self.page.get_by_role("textbox", name="* 全价(元)")  # 全价输入框
        # ✅ 元素封装：对手方输入框
        self.distribution_trading_counterparty_input = self.page.get_by_role("textbox", name="* 对手方")

        # ✅ 元素封装：债券输入框（精确匹配）
        self.distribution_trading_bond_input = self.page.get_by_role("textbox", name="* 债券", exact=True)


    # ✅ 场内基金买卖特有元素
    def init_exchange_fund_business_elements(self):
        self.buy_button = self.page.locator("label").filter(has_text="买入").locator("span").nth(1)
        self.sell_button = self.page.locator("label").filter(has_text="卖出").locator("span").nth(1)

        # ✅ 场内/场外基金通用字段封装

        # 交易价格输入框
        self.fund_price_input = self.page.get_by_role("textbox", name="* 交易价格(元)")  # 可填：交易价格
        # 交易金额输入框
        self.fund_amount_input = self.page.get_by_role("textbox", name="* 交易金额(元)")  # 可填：交易金额
        self.counterparty_input_fund_business = self.page.get_by_role("textbox", name="* 对手方")  # 交易所对手方输入框
    # 场内基金申赎 - 表单要素封装
    def init_exchange_fund_redeem_elements(self):
        # 场内基金申赎 - 交易方向选择
        self.subscribe_radio = self.page.locator("label").filter(has_text="申购").locator("span").nth(1)  # 单选框：申购
        self.redeem_radio = self.page.locator("label").filter(has_text=re.compile(r"^赎回$")).locator("span").nth(
            1)  # 单选框：赎回

        # 交易金额输入框
        self.fund_amount_input = self.page.get_by_role("textbox", name="* 交易金额(元)")  # 可填：交易金额

        # 赎回 点击基金 弹窗
        self.fund_popup_button = self.page.locator(".wrapper > i > svg")
    def init_otc_fund_redeem_elements(self):
        """初始化场外基金申赎页面元素"""
        self.purchase_radio = self.page.locator("label").filter(has_text="认购").locator("span").nth(1)

        # 赎回选择基金点击确定
        self.fund_redeem_select_button = self.page.get_by_role("button", name="确定")

    # ===============================
    # ✅ 表单调度方法（智能分发器）
    # ===============================
    # ✅ 新版智能分发器 ----表单填写分发逻辑，根据业务类型调用对应表单方法
    def fill_trade_form(self, data):
        # ✅ 使用统一调度器处理表单填写
        dispatcher = FormDispatcher()
        dispatcher.dispatch(self, data)

    # ==========================
    # ✅ 各业务表单填写方法
    # ==========================
    # 01---银行间现券买卖表单输入
    def fill_interbank_cashbond_form(self, data: dict):
        """
        银行间现券买卖：根据交易方向、填写通用字段、组合、实际对手方，并提交
        """
        # 判断买入/卖出
        direction = data.get("transaction_direction", "买入").strip()
        if direction == "卖出":
            print("🔁 当前为【卖出】业务，切换卖出流程")
            self.sell_button.click()
        else:
            print("🔁 当前为【买入】业务，继续买入流程")
            self.buy_button.click()
        self.page.wait_for_timeout(1000)
        # 可选：填写组合及分配金额
        self.fill_combination(data)
        # 通用字段填写：日期、对手方、债券、净价
        self.fill_common_fields(data)
        self.page.wait_for_timeout(1000)

        # 选择清算速度
        self.select_settlement_speed(data.get("settlement_speed", "T+0"))
        self.page.wait_for_timeout(1000)

        # ✅ 最后执行：根据 Excel 配置判断是否点击“加入列表”或“加入并继续”
        submit_mode = data.get("操作模式", "加入列表")
        self.submit_form_by_mode(submit_mode)



    # 02--银行间质押式回购表单要素输入
    def fill_interbank_pledge_repo_form(self, data: dict):
        """
        自动化填写银行间买断式回购业务的申请表单
        :param data: 字典格式的表单数据
        """
        direction = data.get("transaction_direction", "").strip()
        if direction == "正回购":
            print("🔁 当前为【正回购】业务（资金融入）")
            self.repo_button.click()  # ✅ 点击正回购按钮
        else:
            print("🔁 当前为【逆回购】业务（资金融出）")
            self.reverse_repo_button.click()  # ✅ 默认逆回购
        self.page.wait_for_timeout(1000)


        # 填写交易对手方并选择下拉项
        self.fill_counterparty(data)
        #填写交易日期
        self.fill_trade_date(data)
        self.page.wait_for_timeout(2000)


        # 填写回购天数

        self.bank_pledge_repo_days_input.click()
        self.bank_pledge_repo_days_input.fill(str(data['repo_days']))  # 👈 从 data 中读取回购天数字段
        self.page.wait_for_timeout(1000)
        # 回购利率
        self.pledge_repo_rate_click_area.click()
        self.pledge_repo_rate_input.fill(data['repo_rate'])
        self.page.wait_for_timeout(6000)

        # 回购金额
        self.bank_pledge_repo_amount_input.fill(str(data['repo_amount']))

        # 资金分配
        if data.get("combination"):
            self.fund_allocation_input.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            self.page.locator(
                "//legend[span[contains(text(), '资金分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)

        # 质押券相关操作元素

        # ✅ 添加质押券按钮点击：根据正/逆回购判断使用哪个按钮
        if direction == "正回购":
            print("📌 正回购 - 点击添加质押券按钮（包含组合列）")
            self.add_bank_pledge_bond_button_repo.click()
        else:
            print("📌 逆回购 - 点击添加质押券按钮（无组合列）")
            self.add_bank_pledge_bond_button_repo_reverse_repo.click()

        self.pledge_bond_code_input.click()
        self.pledge_bond_code_input.fill(data['pledge_bond_code'])
        self.select_option(data['pledge_bond_name'])

        # self.pledge_combination_select.click()

        # ✅ 判断正回购和逆回购，在不同区域填写对应字段
        if direction == "正回购":
            # 填写组合（用于质押券）
            if data.get("combination"):
                self.pledge_combination_select.click()
                item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
                item.click()

                # 填写组合分配的质押面额
                self.page.locator(
                    "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
                ).fill(data['face_value'])

                self.page.get_by_role("button", name="确定").click()
                self.page.wait_for_timeout(3000)

        elif direction == "逆回购":
            # ✅ 逆回购时填写质押面额（不走组合分配弹窗）
            print("📌 当前为逆回购，直接填写表格中的质押面额")
            self.bank_pledge_face_amount.click()
            self.bank_pledge_face_amount_input.fill(data['face_value'])  # ✅ 直接输入面额
            self.page.wait_for_timeout(5000)

        # 点击“加入列表”按钮，提交当前填写内容
        self.add_to_list_button.click()
        self.page.wait_for_timeout(5000)
    # 03--银行间买断式回购表单要素输入
    def fill_interbank_outright_repo_form(self, data: dict):
        """
        自动化填写银行间买断式回购业务的申请表单
        :param data: 字典格式的表单数据
        """
        direction = data.get("transaction_direction", "").strip()
        if direction == "正回购":
            print("🔁 当前为【正回购】业务（资金融入）")
            self.repo_button.click()  # ✅ 点击正回购按钮
        else:
            print("🔁 当前为【逆回购】业务（资金融出）")
            self.reverse_repo_button.click()  # ✅ 默认逆回购
        self.page.wait_for_timeout(1000)

        # 填写交易对手方
        # 填写交易对手方并选择下拉项
        self.counterparty_input.click()
        self.counterparty_input.fill(data['counterparty'])
        self.select_option(data['full_name'])
        self.page.wait_for_timeout(1000)

        # 填写交易日期
        self.fill_trade_date(data)
        self.page.wait_for_timeout(1000)

        # 填写债券代码并选择匹配项
        self.bond_input.click()
        self.bond_input.fill(data['bond_code'])
        self.select_option(data['bond_full_name'])
        self.page.wait_for_timeout(1000)

        # 填写回购天数
        self.bank_outright_repo_days_input.click()
        self.bank_outright_repo_days_input.fill(str(data['repo_days']))  # 👈 从 data 中读取回购天数字段
        self.page.wait_for_timeout(1000)
        # 回购利率
        self.bank_outright_repo_rate_click_area.click()
        self.bank_outright_repo_rate_input.fill(data['repo_rate'])
        self.page.wait_for_timeout(1000)

        #添加首次净价
        self.first_net_price_input.click()
        self.first_net_price_input.fill(data['first_net_price'])


        # 若配置了组合
        if data.get("combination"):
            self.bank_outright_combination_button.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            self.page.locator(
                "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)
    # 04--交易所现券买卖
    def fill_exchange_cashbond_form(self, data: dict):
        # 从 data 中获取交易方向字段，判断是“买入”还是“卖出”业务
        direction = data.get("transaction_direction", "").strip()
        if direction == "卖出":
            print("🔁 当前为【卖出】业务，切换卖出流程")
            self.sell_button.click()
            self.page.wait_for_timeout(1000)  # 等待页面状态切换完成
        else:
            print("🔁 当前为【买入】业务，继续买入流程")
            self.buy_button.click()
            self.page.wait_for_timeout(1000)

        self.fill_exchange_common_fields(data)

        # 可选：填写组合及分配金额
        self.fill_combination(data)


        # 加入列表
        # self.click_add_to_list()
        # 提交到列表
        self.submit()
    # 05-交易所协议式回购表单输入
    def fill_exchange_agreement_repo_form(self, data: dict):
        """
        自动化填写交易所协议式回购业务的申请表单
        :param data: 字典格式的表单数据
        """
        direction = data.get("transaction_direction", "").strip()
        if direction == "正回购":
            print("🔁 当前为【正回购】业务（资金融入）")
            self.repo_button.click()  # ✅ 点击正回购按钮
        else:
            print("🔁 当前为【逆回购】业务（资金融出）")
            self.reverse_repo_button.click()  # ✅ 默认逆回购
        self.page.wait_for_timeout(1000)

        # 填写交易日期
        self.fill_trade_date(data)
        # 填写交易对手方并选择下拉项
        self.fill_counterparty(data)

        # 填写回购天数
        self.exchange_agreement_repo_days_input.click()
        self.exchange_agreement_repo_days_input.fill(str(data['repo_days']))  # 👈 从 data 中读取回购天数字段
        self.page.wait_for_timeout(1000)
        # 回购利率
        self.exchange_agreement_repo_rate_input.click()
        self.exchange_agreement_repo_rate_input.fill(data['repo_rate'])
        self.page.wait_for_timeout(1000)

        # 回购金额
        self.exchange_agreement_repo_amount_input.click()
        self.exchange_agreement_repo_amount_input.fill(str(data['repo_amount']))

        # 资金分配
        if data.get("combination"):
            self.fund_allocation_input.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            # self.page.locator(
            #     "//legend[span[contains(text(), '资金分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            # ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)

        # 质押券相关操作元素

        # ✅ 添加质押券按钮点击：根据正/逆回购判断使用哪个按钮
        if direction == "正回购":
            print("📌 正回购 - 点击添加质押券按钮（包含组合列）")
            self.add_agreement_bond_button_repo.click()
        else:
            print("📌 逆回购 - 点击添加质押券按钮（无组合列）")
            self.add_agreement_bond_button_repo_reverse_repo.click()

        self.pledge_bond_code_input.click()
        self.pledge_bond_code_input.fill(data['pledge_bond_code'])
        self.select_option(data['pledge_bond_name'])

        # self.pledge_combination_select.click()

        # ✅ 判断正回购和逆回购，在不同区域填写对应字段
        if direction == "正回购":
            # 填写组合（用于质押券）
            if data.get("combination"):
                self.pledge_combination_select.click()
                item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
                item.click()

                # 填写组合分配的质押面额
                self.page.locator(
                    "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
                ).fill(data['face_value'])

                self.page.get_by_role("button", name="确定").click()
                self.page.wait_for_timeout(1000)

        elif direction == "逆回购":
            # ✅ 逆回购时填写质押面额（不走组合分配弹窗）
            print("📌 当前为逆回购，直接填写表格中的券面总额(万元)")
            self.pledge_face_amount.click()
            self.pledge_face_amount_input.fill(data['face_value'])  # ✅ 直接输入面额
            self.page.wait_for_timeout(1000)
    # 06-交易所质押式回购表单要素输入
    def fill_exchange_pledge_repo_form(self, data: dict):
        #自动化填写交易所协议式回购业务的申请表单:param data: 字典格式的表单数据
        direction = data.get("transaction_direction", "").strip()
        if direction == "正回购":
            print("🔁 当前为【正回购】业务（资金融入）")
            self.repo_button.click()  # ✅ 点击正回购按钮
        else:
            print("🔁 当前为【逆回购】业务（资金融出）")
            self.reverse_repo_button.click()  # ✅ 默认逆回购
        self.page.wait_for_timeout(1000)

        # 填写交易日期
        self.fill_trade_date(data)

        # 回购利率
        self.exchange_pledge_repo_rate_input.click()
        self.exchange_pledge_repo_rate_input.fill(data['repo_rate'])
        self.page.wait_for_timeout(3000)

        # 上限金额
        self.max_amount_input.click()
        self.max_amount_input.fill(str(data['max_amount']))
        self.page.wait_for_timeout(3000)

        # 资金分配
        if data.get("combination"):
            self.fund_allocation_input.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            # self.page.locator(
            #     "//legend[span[contains(text(), '资金分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            # ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)


    def fill_other_distribution_trading_form(self, data: dict):
        """
        分销买卖
        """
        # 判断买入/卖出
        direction = data.get("transaction_direction", "买入").strip()
        if direction == "卖出":
            print("🔁 当前为【卖出】业务，切换卖出流程")
            self.sell_button.click()
        else:
            print("🔁 当前为【买入】业务，继续买入流程")
            self.buy_button.click()
        self.page.wait_for_timeout(1000)
        # 可选：填写组合及分配金额
        self.fill_combination(data)

        self.page.wait_for_timeout(5000)

        # 填写缴费日期
        self.payment_date_input.fill(data['trade_date'])
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(2000)


        # 填写交易对手方
        # 填写交易对手方并选择下拉项
        self.distribution_trading_counterparty_input.click()
        self.distribution_trading_counterparty_input.fill(data['counterparty'])
        self.select_option(data['full_name'])
        self.page.wait_for_timeout(2000)

        # 填写债券代码并选择匹配项
        self.distribution_trading_bond_input.click()
        self.distribution_trading_bond_input.fill(data['bond_code'])
        self.select_option(data['bond_full_name'])
        self.page.wait_for_timeout(2000)


        # 填写净价字段
        self.clean_price_input.click()  # 激活输入框
        self.clean_price_input.fill(str(data['price']))



        #填写中标利率
        self.bid_rate_input.click()
        self.bid_rate_input.fill(data['bid_yield'])

        #填写全价
        self.full_price_input.click()
        self.full_price_input.fill(data['full_price'])



        # 点击“加入列表”按钮，提交当前填写内容
        self.add_to_list_button.click()








    # 07-场内基金买卖表单输入
    def fill_exchange_fund_business_form(self, data: dict):
        # 从 data 中获取交易方向字段，判断是“买入”还是“卖出”业务
        direction = data.get("transaction_direction", "").strip()
        if direction == "卖出":
            print("🔁 当前为【卖出】业务，切换卖出流程")
            self.sell_button.click()
            self.page.wait_for_timeout(1000)  # 等待页面状态切换完成
        else:
            print("🔁 当前为【买入】业务，继续买入流程")
            self.buy_button.click()
            self.page.wait_for_timeout(1000)

        # # 填写交易日期
        # self.trade_date_input.click()
        # self.trade_date_input.fill(data['trade_date'])
        #
        #
        # # 填写基金代码并选择匹配项
        # self.fund_input.click()
        # self.fund_input.fill(data['fund_code'])
        # self.select_option(data['fund_full_name'])
        # self.page.wait_for_timeout(5000)
        #
        # # # 若存在组合字段，则打开组合选择对话框并选择对应组合
        # if data['combination']:
        #     self.combination_input.click()
        #     item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
        #     item.click()  # 点击选中组合
        # #     spinbutton = self.page.locator(
        # # "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]").fill(
        # # data['face_value'])
        #     self.page.get_by_role("button", name="确定").click()
        #     self.page.wait_for_timeout(1000)
        #
        #
        # #填写计划赎回时间
        # self.redemption_time_input.click()
        #
        # self.redemption_time_input.fill(data['redemption_time'])

        #填写基金通用字段
        self.fill_fund_in_common_fields(data)

        #填写计划赎回时间
        # === 计划赎回时间：仅买入时填写
        if direction == "买入":
            print("📌 当前为【买入】→ 填写计划赎回时间")
            # self.redemption_time_input.click()
            # self.redemption_time_input.fill(data["redemption_time"])
            # self.page.keyboard.press("Enter")
            # self.page.wait_for_timeout(300)
        else:
            print("📌 当前为【卖出】→ 不填写计划赎回时间")

        # 填写交易价格字段
        self.fund_price_input.click()
        self.fund_price_input.fill(data['fund_price'])

        #填写份额
        self.fund_volume_input.click()
        self.fund_volume_input.fill(data['fund_volume'])

        # # 填写对手方并选择选项
        # self.counterparty_input.click()
        # self.counterparty_input.fill(data['actual_counterparty'])
        # self.actual_counterparty_option.click()
        # self.page.wait_for_timeout(1000)

        # 选择托管账户信息
        self.custody_account.click()
        # self.custody_account_select.fill(data["custody_account"])
        self.custody_account_select.click()
    # 08-场内基金申赎表单输入
    def fill_exchange_fund_redeem_form(self, data: dict):
        # 从 data 中获取交易方向字段，判断是“买入”还是“卖出”业务

        # === 1. 切换交易方向（申购 or 赎回）
        direction = data.get("transaction_direction", "").strip()
        if direction == "赎回":
            print("🔁 当前为【赎回】业务，切换赎回流程")
            self.redeem_radio.click()
            self.page.wait_for_timeout(1000)  # 等待页面状态切换完成
        else:
            print("🔁 当前为【申购】业务，继续申购流程")
            self.subscribe_radio.click()
            self.page.wait_for_timeout(1000)

        #填写通用方法
        self.fill_fund_in_common_fields(data)

        # === 2. 填写交易日期
        # self.trade_date_input.click()
        # self.trade_date_input.fill(data['trade_date'])

        # === 3. 输入基金代码 + 选择基金名称
        # self.fund_input.click()
        # self.fund_input.fill(data['fund_code'])
        # self.select_option(data['fund_full_name'])
        # self.page.wait_for_timeout(6000)

        # === 4. 若存在组合，填写组合 + 面额
        # if data['combination']:
        #     self.combination_input.click()
        #     item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
        #     item.click()  # 点击选中组合
        #     # spinbutton = self.page.locator(
        #     #     "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]").fill(
        #     #     data['face_value'])
        #     self.page.get_by_role("button", name="确定").click()
        #     self.page.wait_for_timeout(1000)

        # === 5. 【仅赎回时填写份额】
        if direction == "赎回":
            print(f"📌 当前为赎回 - 填写份额: {data['fund_volume']}")
            self.fund_volume_input.click()
            self.fund_volume_input.fill(data['fund_volume'])
        else:
            print("📌 当前为申购 - 不填写份额字段")

        # === 6. 仅在【申购】时填写计划赎回时间
        if direction == "申购":
            print("📌 申购 - 输入计划赎回时间")
            # self.redemption_time_input.click()
            # self.redemption_time_input.fill(data['redemption_time'])
            # self.page.keyboard.press("Enter")  # 确认输入
        else:
            print("📌 赎回 - 无需填写计划赎回时间")

        # === 6. 仅在【申购】时填写交易金额
        if direction == "申购":
            print("📌 申购 - 输入交易金额")
            self.fund_amount_input.click()
            self.fund_amount_input.fill(data['fund_amount'])
        else:
            print("📌 赎回 - 无需填写交易金额")

        if direction == "赎回":
            print("🔁 当前为【赎回】业务，切换赎回流程")
            self.redeem_radio.click()
            self.page.wait_for_timeout(1000)

            # 👉 弹出弹窗，选择基金
            self.fund_out_select_fund_from_popup(data["fund_code"])




        # === 6. 填写对手方
        #
        # self.actual_counterparty_input.click()
        # self.actual_counterparty_input.fill(data['actual_counterparty'])
        # self.actual_counterparty_option.click()
        # self.page.wait_for_timeout(1000)





        # 选择托管账户信息
        self.custody_account.click()
        self.custody_account_select.click()
    # 09-场外基金申赎回表单输入
    def fill_other_otc_fund_redeem_form(self, data: dict):
        """场外基金申赎/认购 表单填写逻辑"""
        direction = data.get("transaction_direction", "").strip()

        # === 1. 切换交易方向
        if direction == "赎回":
            print("🔁 当前为【赎回】业务，切换赎回流程")
            self.redeem_radio.click()
        elif direction == "认购":
            print("🔁 当前为【认购】业务，切换认购流程")
            self.purchase_radio.click()
        else:
            print("🔁 当前为【申购】业务，继续申购流程")
            self.subscribe_radio.click()
        self.page.wait_for_timeout(1000)

        # === 2. 输入交易日期（全部流程通用）
        self.trade_date_input.click()
        self.trade_date_input.fill(data["trade_date"])
        self.page.keyboard.press("Enter")

        # === 3. 处理基金选择方式（赎回弹窗 / 申购认购输入）
        if direction == "赎回":
            print("📌 当前为赎回 - 使用弹窗选择基金")
            self.fund_out_select_fund_from_popup(data["fund_code"])
        else:
            print(f"📌 当前为{direction} - 使用输入方式添加基金")
            self.fill_fund_out_common_fields(data)  # 包含：基金、组合、对手方等字段

        # === 4. 赎回业务：填写份额
        if direction == "赎回":
            print(f"📌 赎回 - 输入基金份额: {data['fund_volume']}")
            # self.fund_volume_input.click()
            # self.fund_volume_input.fill(data["fund_volume"])
        else:
            print("📌 非赎回 - 不填写份额")

        # === 5. 认购/申购业务：填写计划赎回时间
        if direction in ["认购", "申购"]:
            print("📌 认购/申购 - 输入计划赎回时间")
            # self.redemption_time_input.click()
            # self.redemption_time_input.fill(data["redemption_time"])
            # self.page.keyboard.press("Enter")
        else:
            print("📌 赎回 - 无需填写计划赎回时间")

        # === 6. 认购/申购业务：填写交易金额
        if direction in ["认购", "申购"]:
            print("📌 认购/申购 - 输入交易金额")
            self.fund_amount_input.click()
            self.fund_amount_input.fill(data["fund_amount"])
        else:
            print("📌 赎回 - 无需填写交易金额")

        # === 7. 认购业务：填写交易价格 + 对手方（额外字段）
        if direction == "认购":
            # print("📌 认购 - 输入交易价格")
            # self.fund_price_input.click()
            # self.fund_price_input.fill(data["fund_price"])

            print("📌 认购 - 输入对手方")
            self.counterparty_fund_input.click()
            self.counterparty_fund_input.fill(data["counterparty"])
            self.select_option(data["full_name"])
            self.page.wait_for_timeout(500)

    # ==========================
    # ✅ 通用字段填写方法（建议集中放底部）
    # ==========================
    # 01-仅用于“银行间现券类业务”
    def fill_common_fields(self, data: dict):
        """填写交易日期、对手方、债券、净价（多个业务通用）"""
        self.trade_date_input.click()
        self.trade_date_input.fill(data["trade_date"])
        # ✅ 关键：发送 Enter 键确认
        self.page.keyboard.press("Enter")
        #添加交易对手方
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(500)
        #添加债券
        self.bond_input.click()
        self.bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])
        self.page.wait_for_timeout(600)
        # 填写净价字段
        self.clean_price_input.click()
        self.clean_price_input.fill(str(data["price"]))
    # 02-清算速度选择
    def select_settlement_speed(self, speed_text: str):
        """
        选择清算速度，例如：T+0、T+1、T+2...
        """
        if not speed_text:
            print("⚠️ 未提供清算速度，跳过设置")
            return

        # 点击清算速度下拉框（已在 __init__ 中封装为 self.settlement_speed_input）
        self.settlement_speed_input.click()

        # 精确匹配对应选项并点击内部 span
        try:
            option = self.page.get_by_role("option", name=speed_text).locator("span")
            option.wait_for(state="visible", timeout=3000)
            option.click()
        except PlaywrightTimeoutError:
            print(f"❌ 清算速度选项 '{speed_text}' 未找到或超时")
    # 03-用于交易所现券买卖业务
    def fill_exchange_common_fields(self, data: dict):
        """填写交易日期、对手方、债券、净价（多个业务通用）"""

        # 添加债券
        self.bond_input.click()
        self.bond_input.fill(data["bond_code"])
        self.select_option(data["bond_full_name"])
        self.page.wait_for_timeout(600)

        #交易日期
        self.trade_date_input.click()
        self.trade_date_input.fill(data["trade_date"])
        # ✅ 关键：发送 Enter 键确认
        self.page.keyboard.press("Enter")
        # 添加对手方
        self.counterparty_input_exchange.click()
        self.counterparty_input_exchange.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(500)

        # 填写净价字段
        self.clean_price_input.click()
        self.clean_price_input.fill(str(data["price"]))
    # 04-组合
    def fill_combination(self, data: dict):
        """填写组合及面额，若存在"""
        if data['combination']:
            self.combination_button_bond.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()  # 点击选中组合
            spinbutton = self.page.locator(
                "//legend[span[contains(text(), '组合分配')]]/following::input[contains(@class, 'el-input__inner')][1]").fill(
                data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)
    # 05-实际对手方
    def fill_actual_counterparty(self, data: dict):
        """填写实际对手方，若存在"""
        actual_cp = data.get("actual_counterparty", "").strip()
        if actual_cp:
            self.actual_counterparty_input.click()
            self.actual_counterparty_input.fill(actual_cp)
            self.actual_counterparty_option.click()
            self.page.wait_for_timeout(500)

    #交易对手方+时间
    def fill_counterparty(self, data: dict):
        """通用方法：填写交易日期 + 交易对手方 + 下拉选择"""
        # 添加交易对手方
        self.counterparty_input.click()
        self.counterparty_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(500)
    #填写交易日期
    def fill_trade_date(self, data: dict):
        """通用方法：填写交易日期"""
        self.trade_date_input.click()
        trade_date = data["trade_date"]
        if isinstance(trade_date, (datetime.date, datetime.datetime)):
            trade_date = trade_date.strftime("%Y-%m-%d")  # 👈 转换为标准日期字符串
        self.trade_date_input.fill(trade_date)
        # ✅ 关键：发送 Enter 键确认
        self.page.keyboard.press("Enter")
    #加入列表
    def click_add_to_list(self):
        """
        通用操作：点击“加入列表”按钮，提交当前表单内容
        """
        print("📥 正在点击【加入列表】按钮，提交当前表单内容")
        self.add_to_list_button.click()
        self.page.wait_for_timeout(1000)  # 可调整等待时间，确保表格渲染完成
    #加入列表并继续
    def add_to_list_and_continue_button(self):
        self.add_to_list_button.click()

    def submit_form_by_mode(self, mode: str = "加入列表"):
        #根据传入的模式点击相应的按钮：- 加入列表 - 加入列表并继续

        if mode == "加入列表":
            print("📥 点击【加入列表】按钮")
            self.add_to_list_button.click()
        elif mode == "加入列表并继续":
            print("📥 点击【加入列表并继续】按钮")
            self.add_to_list_and_continue_button.click()
        else:
            raise ValueError(f"❌ 不支持的操作模式: {mode}")
        self.page.wait_for_timeout(1000)  # 等待表格刷新或下一次填写

    # 仅用于“基金业务”
    def fill_fund_in_common_fields(self, data: dict):
        """填写交易日期、基金、组合、对手方（多个业务通用）"""
        self.trade_date_input.click()
        self.trade_date_input.fill(data["trade_date"])
        self.page.keyboard.press("Enter") # ✅ 关键：发送 Enter 键确认

        # 添加基金
        self.fund_input.click()
        self.fund_input.fill(data["fund_code"])
        self.select_option(data["fund_full_name"])
        self.page.wait_for_timeout(600)

        # 填写组合
        if data.get("combination"):
            self.combination_input.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            # self.page.locator(
            #     "//legend[span[contains(text(), '资金分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            # ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)

        # 添加对手方
        self.counterparty_fund_input.click()
        self.counterparty_fund_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(500)
    #场外基金赎回 根据申购得基金 是弹窗选择申购的基金。
    def fill_fund_out_common_fields(self, data: dict):
        """填写交易日期、基金、组合、对手方（多个业务通用）"""
        self.trade_date_input.click()
        self.trade_date_input.fill(data["trade_date"])
        self.page.keyboard.press("Enter")  # ✅ 关键：发送 Enter 键确认

        # 添加基金
        self.fund_input.click()
        self.fund_input.fill(data["fund_code"])
        self.select_option(data["fund_full_name"])
        self.page.wait_for_timeout(600)

        # 填写组合
        if data.get("combination"):
            self.combination_input.click()
            item = self.page.get_by_role("treeitem", name=data['combination']).locator("span").nth(1)
            item.click()
            # self.page.locator(
            #     "//legend[span[contains(text(), '资金分配')]]/following::input[contains(@class, 'el-input__inner')][1]"
            # ).fill(data['face_value'])
            self.page.get_by_role("button", name="确定").click()
            self.page.wait_for_timeout(1000)

        # 添加对手方
        self.counterparty_fund_input.click()
        self.counterparty_fund_input.fill(data["counterparty"])
        self.select_option(data["full_name"])
        self.page.wait_for_timeout(500)
    # 场外基金赎回 根据申购得基金 是弹窗选择申购的基金。
    def fund_out_select_fund_from_popup(self,fund_code: str):
        """
        在弹窗中选择基金（通过基金代码匹配），勾选对应复选框并点击“确定”按钮。
        :param fund_code: 基金代码，例如 004695.OF
        """
        """填写交易日期、基金、组合、对手方（多个业务通用）"""

        print(f"📌 打开基金选择弹窗，准备选择基金: {fund_code}")

        # ✅ 1. 打开弹窗（前提是你之前已封装 self.fund_popup_button）
        self.fund_popup_button.click()

        # ✅ 2. 等待弹窗标题（确保弹窗出现）
        self.page.get_by_role("heading", name="选择基金").wait_for(timeout=5000)

        # ✅ 3. 等待基金代码文本出现在页面（不要再等 tr.first）
        self.page.locator(f"text={fund_code}").wait_for(state="visible", timeout=10000)


        # 4. 使用 get_by_role("row") 精确查找整行
        row = self.page.get_by_role("row", name=re.compile(f"^{fund_code}"))  # 也可使用 include 模糊匹配
        row.locator("span").nth(1).click()  # 直接点击该行的操作按钮（span 是复选框）

        print(f"✅ 已点击基金代码 {fund_code} 对应行")
        self.page.wait_for_timeout(1000)
        self.fund_redeem_select_button.click()
        self.page.wait_for_timeout(1000)
        print("✅ 基金选择完成")

    # ===============================
    # ✅ 流程与审批方法
    # ===============================

    def navigate(self, business_type: str = "银行间现券买卖"):
        self.navigate_to_business(self.page, business_type)  # ✅ 自动根据业务类型跳转

    #根据业务类型，判断是否新建
    def try_create_new_request(self, business_type: str):
        if self.should_create_new(business_type):
            self.page.get_by_role("button", name="新建").click()
        else:
            print(f"✅ 业务类型 {business_type} 不需要新建，已跳过")

    def submit(self):
        """提交表单至列表"""
        self.add_to_list_button.click()

    def select_option(self, option_name):
        # 封装通用选择下拉项方法，供多处调用
        option_locator = self.page.get_by_role("option", name=option_name)
        try:
            option_locator.wait_for(state='visible', timeout=5000)  # 等待选项可见
            option_locator.click()  # 点击选中
        except PlaywrightTimeoutError:
            print(f"选项 {option_name} 未能加载或点击超时。")

    def approve_request_with_risk_check(self):
        # 点击“提交”按钮，触发风控检查弹窗弹出
        self.page.wait_for_timeout(3000)
        self.submit_button.click()
        self.page.wait_for_timeout(8000)

    def submit_risk_approval(self):
        """
        风控弹窗提交处理：
        优先点击“忽略警告继续提交”，再尝试点击风控信息下的提交按钮，最后兜底点击全局提交按钮。
        """
        try:
            if self.ignore_warning_button.is_visible():
                print("🔁 检测到【忽略警告继续提交】按钮，点击...")
                self.ignore_warning_button.click()

            elif self.risk_approve_button.is_visible():
                print("🔁 检测到【风控信息】下的【提交】按钮，点击...")
                self.risk_approve_button.click()

            elif self.approve_button.is_visible():
                print("🔁 检测到兜底【提交】按钮，点击...")
                self.approve_button.click()

            else:
                raise Exception("❌ 未检测到任一可点击的风控提交按钮")

        except Exception as e:
            print(f"⚠️ 风控提交时发生异常: {e}")
            raise

    #获取申请单编号
    def extract_approval_number(self):
        # 使用get_by_role定位包含申请单编号的元素
        approval_number_element = self.page.get_by_text("申请单编号:")
        # 提取编号文本
        approval_number_text = approval_number_element.text_content()
        # 打印以进行调试
        print(f"Debug: 申请单编号的完整文本是: {approval_number_text}")
        # 从文本中提取实际的申请单编号
        approval_number = approval_number_text.split("【")[1].split("】")[0]
        return approval_number
    # 导航到代办审批
    def navigate_to_approval_list(self):
        # self.menu_page.navigate_to_approval_list()
        self.menu_nav.click()
        self.approval_list.click()
        self.pending_approval_link.click()
        # 设置等待时间
        self.page.wait_for_timeout(5000)
    #点击审批
    def approve_request(self, approval_number):
        # 在审批列表中查找指定编号的申请单，点击审批
        while True:
            try:
                approval_cell = self.page.get_by_role("button", name=f"{approval_number}")
                approval_cell.wait_for(state="visible", timeout=5000)
                approval_cell.click()
                print(f"找到审批单号 {approval_number}，开始审批流程")
                break
            except Exception:
                try:
                    next_button = self.page.get_by_label("下一页").first
                    if next_button.is_disabled():
                        print(f"未找到审批单号 {approval_number}，请检查数据或流程是否正确")
                        return
                    next_button.click()
                    self.page.wait_for_load_state("domcontentloaded")
                except Exception:
                    print(f"未找到审批单号 {approval_number}，且无“下一页”按钮")
                    return


        # # ✅ 点击“审批”按钮（确保元素可见）
        # self.page.get_by_role("button", name="审批").wait_for(state="visible", timeout=8000)
        # self.page.get_by_role("button", name="审批").click()
        #
        # # ✅ 精准点击风控弹窗中的“确定”按钮，防遮挡防误判
        # dialogs = self.page.locator("div.el-overlay-dialog")
        # for i in range(dialogs.count()):
        #     dialog = dialogs.nth(i)
        #     try:
        #         title = dialog.locator("h4.el-dialog__title")
        #         if title.is_visible() and "风控信息" in title.inner_text().strip():
        #             ok_btn = dialog.locator("button:has-text('确定')")
        #
        #             # 🔒 等按钮附着 + 可见
        #             ok_btn.wait_for(state="attached", timeout=5000)
        #             ok_btn.wait_for(state="visible", timeout=5000)
        #
        #             # 🚫 等遮罩层消失
        #             self.page.wait_for_selector("div.el-overlay", state="hidden", timeout=8000)
        #
        #             ok_btn.click()
        #             print("✅ 已点击风控弹窗的确定按钮")
        #             break
        #     except Exception as e:
        #         print(f"❌ 弹窗处理失败: {e}")
        #         continue
        #
        # # ✅ 找到“流程审批”弹窗并点击“确定”
        # dialogs = self.page.locator("div.el-overlay-dialog")
        # for i in range(dialogs.count()):
        #     dialog = dialogs.nth(i)
        #     try:
        #         title = dialog.locator("h4.el-dialog__title")
        #         if title.is_visible() and "流程审批" in title.inner_text().strip():
        #             ok_btn = dialog.locator("button:has-text('确定')")
        #             ok_btn.wait_for(state="visible", timeout=8000)
        #             ok_btn.click()
        #             print("✅ 审批流程完成")
        #             break
        #     except:
        #         continue
        # 等待页面完成处理（网络空闲）
        #


        self.page.wait_for_timeout(9000)
        # 点击“审批”按钮，触发风控弹窗
        self.page.get_by_role("button", name="审批").click()
        self.page.wait_for_timeout(5000)
        # 点击风控弹窗的“确定”按钮（通过“风控信息”标题精准定位）
        self.page.get_by_role("button", name="确定").click()
        # 等待风控关闭
        self.page.wait_for_timeout(7000)
        # 点击审批确定
        # 3. 等待流程审批弹窗出现
        self.page.wait_for_selector("h4.el-dialog__title", timeout=10000)

        # 4. 从弹窗中点击“确定”按钮（不要用 get_by_role 全局）
        dialogs = self.page.locator("div.el-overlay-dialog")
        for i in range(dialogs.count()):
            dialog = dialogs.nth(i)
            title = dialog.locator("h4.el-dialog__title")
            if title.is_visible() and "流程审批" in title.inner_text().strip():
                dialog.locator("button:has-text('确定')").click()
                break




    # ===============================
    # ✅ 断言与报告方法
    # ===============================
    # 将断言比对结果反写到原始 Excel 的副本中，并导出为新文件（带时间戳）
    def export_assertion_results_to_excel(self):
        """
        将断言比对结果反写到原始 Excel 的副本中，并导出为新文件（带时间戳）
        """
        df = pd.read_excel(self.test_data_file, engine="openpyxl")
        df.fillna(method="ffill", inplace=True)
        df["实际检查结果"] = ""
        df["实际结果描述"] = ""
        df["断言状态"] = ""

        for item in self.assertion_results:
            group_no, sub_no = item["group_key"].split("-")
            check_name = item["check_point_name"]

            cond = (
                    (df["编号"].astype(str).str.strip() == group_no) &
                    (df["子编号"].astype(str).str.strip() == sub_no) &
                    (df["检查点名称"].astype(str).str.strip() == check_name)
            )

            df.loc[cond, "实际检查结果"] = item["actual_result"]
            df.loc[cond, "实际结果描述"] = item["actual_description"]
            df.loc[cond, "断言状态"] = item["status"]

        # ✅ 创建输出目录（若不存在）
        output_dir = Path("report") / "assertions"
        output_dir.mkdir(parents=True, exist_ok=True)

        # ✅ 构造完整输出路径
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # out_file = output_dir / f"断言比对结果_{timestamp}.xlsx"
        out_file = output_dir / f"assertion_result_{timestamp}.xlsx"

        # ✅ 导出文件
        df.to_excel(out_file, index=False)
        print(f"✅ 已导出断言比对结果文件：{out_file}")
    # 出失败断言到 Excel，并以 Markdown + HTML 美化格式附加到 Allure 报告中
    def export_and_attach_failed_cases(self):
        """
        ✅ 导出失败断言到 Excel，并以 Markdown + HTML 美化格式附加到 Allure 报告中
        """

        if not self.failed_cases_summary:
            return  # 无失败，跳过

        import pandas as pd
        import datetime
        import allure
        import os

        # ✅ 工具函数：浮点数保留两位小数，非浮点则原样返回
        def format_float(value):
            return f"{value:.2f}" if isinstance(value, float) else value

        # ✅ 转换为 DataFrame
        df = pd.DataFrame(self.failed_cases_summary)

        # ✅ 统一格式化 expected 和 actual 列为两位小数
        df["expected"] = df["expected"].apply(format_float)
        df["actual"] = df["actual"].apply(format_float)

        # ✅ 导出 Excel 文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"report/assertions/断言比对结果_{timestamp}.xlsx"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df.to_excel(out_path, index=False)
        print(f"✅ 已导出断言比对结果 Excel 文件：{out_path}")

        # ✅ Markdown 表格美化（展示完整值）
        markdown_lines = [
            "# ❌ 风控断言失败汇总\n",
            "| 子用例编号 | 申请单号 | 资产编号 | 检查点 | 预期值 | 实际值 | 描述 |",
            "|------------|----------|----------|--------|--------|--------|------|"
        ]
        for item in self.failed_cases_summary:
            markdown_lines.append(
                f"| {item['sub_case']} | {item['request_no']} | {item['biz_no']} | {item['checkpoint']} "
                f"| {format_float(item['expected'])} | {format_float(item['actual'])} | {item['result_desc']} |"
            )

        # ✅ 注意：MARKDOWN 类型在某些环境下会报错，使用 TEXT 避免 AttributeError
        allure.attach("\n".join(markdown_lines), name="风控断言失败详情(Markdown)",
                      attachment_type=allure.attachment_type.TEXT)

        # ✅ HTML 表格美化样式（更清晰）
        html_table = df.to_html(index=False, escape=False, justify="center", border=1)
        html_wrapper = f"""
        <html><head><meta charset='utf-8'><style>
        body {{ font-family: Arial, sans-serif; }}
        h2 {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
        th, td {{ border: 1px solid #ccc; padding: 6px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        </style></head><body>
        <h2>❌ 风控断言失败详情表格</h2>
        {html_table}
        </body></html>
        """

        allure.attach(html_wrapper, name="风控断言失败详情(表格)", attachment_type=allure.attachment_type.HTML)
    ##✅【新增】当断言失败时，记录到同一数组
    def record_failed_case_summary(self, sub_case: str, request_no: str, biz_no: str, checkpoint: str, expected: float,
                                   actual: float, result_desc: str):  # ✅【新增】当断言失败时，记录到同一数组
        self.failed_cases_summary.append({
            "sub_case": sub_case,
            "request_no": request_no,
            "biz_no": biz_no,
            "checkpoint": checkpoint,
            "expected": expected,
            "actual": actual,
            "result_desc": result_desc
        })













    # ===============================
    # ✅ 用例筛选工具方法
    # ===============================

    # 封装 选择对应用例的方法
    @staticmethod
    def filter_case_groups(grouped_data: dict, prefix: str) -> dict:
        """
        根据子编号前缀（如 uac2.）筛选用例组
        :param grouped_data: load_grouped_test_data 返回的数据字典
        :param prefix: 子编号前缀（如 'uac2.'）
        :return: 筛选后的 grouped_data 子集
        """
        return {
            key: val for key, val in grouped_data.items()
            if val["form_data"].get("sub_case_no", "").startswith(prefix)
        }

        # ✅ 页面跳转逻辑，根据业务类型进入对应业务表单页



























    def reset_to_new_request_page(self):
        """
        页面重置逻辑：重新跳转到申请页面，等待“新建”按钮加载
        """
        print("🔁 页面重置中：跳转回申请新建页")
        self.page.goto("/traderequest/bank/cashbond", timeout=60000)
        self.page.wait_for_timeout(1000)
        try:
            self.page.get_by_role("button", name="新建").wait_for(state="visible", timeout=10000)
            print("✅ 页面恢复，准备下一笔交易")
        except Exception as e:
            print(f"❌ 页面未恢复，找不到新建按钮: {e}")
            raise


