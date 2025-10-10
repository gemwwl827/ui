# pages/base_page.py
# ✅ 通用基类：定位/点击/选择/输入/等待（稳健版）
import re

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
import datetime
import time


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.init_common_elements()

    # ====== 公共元素（菜单/按钮/风控弹窗等）======
    def init_common_elements(self):
        """
        说明：
        - 下方少量 locator 作为“字段/菜单”补充使用；真正的点击动作请尽量走封装方法。
        - “提交/新建/加入列表”这类按钮，推荐用封装方法，不要直接使用缓存 locator，避免 stale。
        """
        # —— 新建按钮
        self.new_button = self.page.get_by_role("button", name="新建")

        # —— 方向类（仅供表单填写时用）
        self.buy_button  = self.page.locator("label:has-text('买入') span").first
        self.sell_button = self.page.locator("label:has-text('卖出') span").first
        self.repo_button = self.page.locator("label:has-text('正回购') span").nth(1)
        self.reverse_repo_button = self.page.locator("label:has-text('逆回购') span").nth(1)

        # —— 常用字段
        self.trade_date_input = self.page.get_by_role("combobox", name="* 交易日期")
        self.clean_price_input = self.page.get_by_label("净价(元)")

        # —— 常用按钮（缓存版）
        self.add_to_list_button = self.page.get_by_role("button", name="加入列表", exact=True)
        self.add_and_continue_button = self.page.get_by_role("button", name="加入列表并继续", exact=True)
        self.add_and_continue_button_exchange = self.page.get_by_role("button", name="加入并继续")
        self.reset_button = self.page.get_by_role("button", name="重置", exact=True)

        self.submit_button = self.page.get_by_role("button", name="提交")  # 注意：可能匹配多个
        self.save_button = self.page.get_by_role("link", name=" 保存")

        # —— 风控弹窗相关
        self.risk_dialog_by_role = self.page.get_by_role("dialog", name="风控信息")
        self.risk_dialog_by_label = self.page.get_by_label("风控信息")
        self.ignore_warning_button = self.page.get_by_role("button", name="忽略警告继续提交")

        # —— 菜单（审批相关）
        self.menu_nav = self.page.get_by_role("menuitem", name="交易申请").locator("span")
        # self.approval_list = self.page.get_by_text("审批列表")
        self.approval_list = self.page.locator("div").filter(has_text=re.compile(r"^审批列表$"))
        self.pending_approval_link = self.page.get_by_role("link", name="待办审批")

    # ====== 通用小工具 ======



    def press_enter(self):
        self.page.keyboard.press("Enter")

    def select_option(self, option_name: str, timeout=5000):
        """选择下拉选项：等待可见 → 点击"""
        loc = self.page.get_by_role("option", name=option_name)
        try:
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
        except PlaywrightTimeoutError:
            print(f"⚠️ 下拉选项超时: {option_name}")

    def set_trade_date(self, value):
        """设置交易日期：支持 date/datetime/str，回车确认。"""
        self.trade_date_input.click()
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = value.strftime("%Y-%m-%d")
        self.trade_date_input.fill(str(value))
        self.press_enter()



    # =======================
    #  三、对外暴露的标准动作
    # =======================
    def click_new(self):
        """点击【新建】"""
        self.page.get_by_role("button", name="新建", exact=True)

    def click_join_list(self, prefer_safe: bool = True):
        """点击【加入列表】"""
        self.add_to_list_button.click()

    def safe_add_and_continue_bank(self):
        """银行间 → 点击【加入列表并继续】 → 点击【重置】"""
        try:
            self.add_and_continue_button.click()
            print("✅ 银行间：点击【加入列表并继续】成功")

            self.reset_button.click()
            print("✅ 点击【重置】成功")
        except Exception as e:
            print(f"[ERROR] 银行间加入并继续失败: {e}")

    def safe_add_and_continue_exchange(self):
        """交易所 → 点击【加入并继续】 → 点击【重置】"""
        try:
            self.add_and_continue_button_exchange.click()
            print("✅ 交易所：点击【加入并继续】成功")

            self.reset_button.click()
            print("✅ 点击【重置】成功")
        except Exception as e:
            print(f"[ERROR] 交易所加入并继续失败: {e}")

    def wait_form_ready(self, timeout: int = 500):
        """等待表单加载/重置完成"""
        try:
            self.page.get_by_role("textbox", name="* 交易对手方").wait_for(
                state="visible", timeout=timeout
            )
            print("✅ 表单已重置完毕，可以继续填写")
        except Exception as e:
            print(f"⚠️ 等待表单就绪超时: {e}")

    def click_toolbar_submit(self):
        """点击页面顶部工具栏上的【提交】"""
        self.page.locator("#app .b-panel-buttons").get_by_role(
            "button", name="提交", exact=True
        ).click()

    def click_risk_dialog_submit(self):
        """点击风控信息弹窗里的【提交】"""
        self.page.locator(".el-overlay-dialog").get_by_role(
            "button", name="提交", exact=True
        ).click()

