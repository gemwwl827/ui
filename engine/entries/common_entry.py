# engine/entries/common_entry.py
# -*- coding: utf-8 -*-
# 银行间 / 交易所 / 基金共用“进入入仓、设日期、查编号、点入仓”四步
from playwright.sync_api import Page


def goto_entry_list(page: Page) -> None:
    """进入 清算管理 → 核对确认 → 申请确认入仓"""
    page.get_by_text("清算管理").click()
    page.get_by_text("核对确认").click()
    page.get_by_role("link", name="申请确认入仓").click()
    page.wait_for_timeout(1200)

def set_date_range(page: Page, start: str, end: str) -> None:
    """设置入仓查询的日期范围（现场定位，避免依赖 BasePage）"""
    try:
        group = page.get_by_role("group", name="交易日期")
        group.click()
        # 清空按钮（如果有）
        try:
            clear_btn = group.get_by_role("img").nth(1)
            if clear_btn.is_visible():
                clear_btn.click()
        except Exception:
            pass
    except Exception:
        pass

    start_input = page.get_by_role("combobox", name="开始日期")
    end_input   = page.get_by_role("combobox", name="结束日期")
    start_input.click(); start_input.fill(start)
    end_input.click();   end_input.fill(end)
    page.keyboard.press("Enter")

    page.get_by_role("button", name="查询").click()
    page.wait_for_timeout(1000)

def open_row_by_approval(page: Page, approval_number: str) -> None:
    """翻页查找申请单号并进入编辑页"""
    while True:
        rows = page.locator("table.el-table__body tbody tr")
        cnt = rows.count()
        for i in range(cnt):
            row = rows.nth(i)
            if approval_number in row.inner_text():
                print(f"✅ 找到申请单号 {approval_number} 在第 {i + 1} 行")
                row.get_by_role("button", name="").click()
                page.wait_for_timeout(600)
                return
        next_btn = page.get_by_role("button", name="下一页")
        if next_btn.is_disabled():
            raise Exception(f"❌ 所有分页未找到申请单号 {approval_number}")
        print("🔁 当前页未找到，翻页中...")
        next_btn.click()
        page.wait_for_load_state("domcontentloaded")

def click_entry(page: Page) -> None:
    """点击详情页上的【入仓】"""
    page.get_by_text("入仓", exact=True).click()
    page.wait_for_timeout(800)



# engine/entries/common_entry.py
# ... 你现有的 import、已有函数保持不变 ...

from playwright.sync_api import Page

def fill_trader_if_required(page: Page, trader_name: str | None = None) -> None:
    """
    通用：如果页面要求选择 “本方交易员/交易员”，则点击并选择一个选项。
    - 优先匹配：* 本方交易员 -> 本方交易员 -> 交易员
    - 指定 trader_name 则按姓名选；否则兜底选第一项
    - 没有该字段时自动忽略
    """
    try:
        # 尝试不同标签的下拉框
        try:
            cb = page.get_by_role("combobox", name="* 本方交易员")
        except Exception:
            try:
                cb = page.get_by_role("combobox", name="本方交易员")
            except Exception:
                cb = page.get_by_role("combobox", name="交易员")

        cb.click()

        if trader_name:
            # 指定了姓名：优先按 option 名称；失败则按纯文本兜底
            try:
                page.get_by_role("option", name=trader_name).click()
            except Exception:
                page.get_by_text(trader_name).click()
        else:
            # 未指定姓名：选第一项
            try:
                page.get_by_role("listbox").get_by_role("option").first.click()
            except Exception:
                page.get_by_role("option").first.click()

    except Exception:
        # 页面无该字段或已有默认值 -> 忽略即可
        pass
