
#pages/login_page.py
from playwright.sync_api import Page


class LoginPage:

    def __init__(self, page: Page):
        self.page = page
        #登录
        self.locator_username = page.get_by_placeholder("请输入账号")
        self.locator_password = page.get_by_placeholder("请输入密码")
        self.locator_login_btn = page.get_by_role("button", name="登录")

    def navigate(self):
        self.page.goto("login")

    def fill_username(self, username):
        self.locator_username.fill(username)

    def fill_password(self, password):
        self.locator_password.fill(password)

    def click_login_button(self):
        self.locator_login_btn.click()



    def login(self, username, password) -> None:
        """完整登录操作"""
        self.locator_username.fill(username)
        self.locator_password.fill(password)
        self.locator_login_btn.click()





