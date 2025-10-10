from playwright.sync_api import Page

class MenuPage:
    def __init__(self, page: Page):
        self.page = page
        #导航到代办审批
        self.menu_nav =page.get_by_text("交易申请", exact=True)
        self.approval_list = page.get_by_text("审批列表")
        self.pending_approval_link = page.get_by_role("link", name="待办审批")
        #导航到我的申请
        self.trade_request_nav = page.get_by_text("交易申请", exact=True)
        self.application_list = page.get_by_role("menuitem", name="申请列表").locator("span")
        self.my_application_link = page.get_by_role("link", name="我的申请")

        # page.locator("span").filter(has_text=re.compile(r"^交易申请$")).locator("span").click()
        # page.get_by_text("交易申请", exact=True).click()
        # page.locator("span").filter(has_text=re.compile(r"^交易申请$")).locator("span").click()
        # page.get_by_role("menuitem", name="申请列表 ").locator("span").nth(2).click()
        # page.get_by_text("申请列表").click()
        # page.get_by_role("link", name="我的申请").click()


    #导航到代办审批
    def navigate_to_approval_list(self):
        self.menu_nav.click()
        self.approval_list.click()
        self.pending_approval_link.click()

    def navigate_to_my_requests(self):
        self.trade_request_nav.click()















    def navigate_to_trade_request(self):
        self.page.wait_for_selector('text="交易申请"', timeout=60000)
        self.page.get_by_text("交易申请", exact=True).click()

    def navigate_to_interbank(self):
        self.page.get_by_role("menuitem", name="银行间 ").locator("span").nth(2).click()
        self.page.get_by_text("银行间").nth(4).click()

    def navigate_to_cash_bond(self):
        self.page.get_by_role("menuitem", name="现券买卖").locator("span").first.click()

    def navigate_to_pending_approvals(page):
        # 点击导航菜单中的“交易申请”
        page.locator("#nav-menu").get_by_text("交易申请", exact=True).click()

        # 点击“审批列表”链接
        page.get_by_text("审批列表").click()

        # 点击“待办审批”链接
        page.get_by_role("link", name="待办审批").click()
