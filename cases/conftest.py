

# ✅ 修复 pytest 不识别 dmpython 的问题
# import sys
# import os
#
# venv_site = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages")
# if os.path.exists(venv_site) and venv_site not in sys.path:
#     sys.path.insert(0, venv_site)


import pytest
import io
import sys
import allure






# ✅ 屏蔽 pyignite 的 DEBUG 日志输出
import logging
logging.getLogger("pyignite").setLevel(logging.WARNING)

import re
import pytest
from pages.login_page import LoginPage
from typing import Dict

USERNAME = "uaczy"
PASSWORD = "admin123"
@pytest.fixture(scope="session", autouse=True)
def login_save_auth(browser, base_url, pytestconfig) -> None:
    """登录，保存cookies"""
    context = browser.new_context(base_url=base_url, no_viewport=True,ignore_https_errors=True,viewport=None)
    print("base_url----", base_url)
    page = context.new_page()

    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(USERNAME, PASSWORD)
    # LoginPage(page).navigate()
    # LoginPage(page).login("祝杨", "1")

    # 打印当前URL以调试
    print("Current URL after login:", page.url)

    # 等待登录成功页面重定向，增加超时时间并使用正则表达式匹配
    page.wait_for_url("http://10.60.1.49:8091/", timeout=90000)

    # 保存storage state 到指定的文件
    storage_path = pytestconfig.rootpath.joinpath("auth/state.json")
    context.storage_state(path=storage_path)
    context.close()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright, pytestconfig) -> Dict:  # noqa
    """
    添加context 上下文参数，默认每个页面加载cookies
    :param browser_context_args:
    :param playwright:
    :return:
    """
    return {
        "storage_state": pytestconfig.rootpath.joinpath("auth/state.json"),
        "no_viewport": True,
        **browser_context_args,
    }


@pytest.fixture(scope="module")
def login_context(browser, base_url, pytestconfig):
    """
    登录页面单独创建独立的page对象
    避免全局先登录加载cookie，导致有些打开登录页直接跳到首页去了
    :return:
    """
    context = browser.new_context(base_url=base_url, no_viewport=True)
    yield context
    context.close()




def pytest_addoption(parser):
    parser.addoption("--group", action="store", default="", help="指定要运行的用例组编号")
    parser.addoption("--case_key", action="store", default="", help="指定要运行的用例子编号")






@pytest.fixture(autouse=True)
def capture_stdout():
    old_stdout = sys.stdout
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        yield
    finally:
        sys.stdout = old_stdout
        output = buffer.getvalue()
        allure.attach(output, name="stdout", attachment_type=allure.attachment_type.TEXT)





















































