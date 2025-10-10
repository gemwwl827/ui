# engine/entries/exchange_entry.py
# -*- coding: utf-8 -*-
from playwright.sync_api import Page
from .common_entry import goto_entry_list, set_date_range, open_row_by_approval, click_entry

def confirm_entry_exchange_bond_trade(page_obj, approval_number: str):
    """交易所现券买卖：入仓确认"""
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # 仅本业务特有字段在这里填写
    page.get_by_role("textbox", name="* 净价(元)").fill("100")
    page.get_by_role("textbox", name="* 收付金额(元)").fill("1000000")
    page.get_by_role("textbox", name="* 交易费用(元)").fill("100")

    click_entry(page)
    print("✅ 入仓成功（交易所现券）")

def confirm_entry_exchange_protocol(page_obj, approval_number: str):
    """交易所协议式回购：入仓确认"""
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)
    # 如有本业务特有字段，补在这里
    click_entry(page)
    print("✅ 入仓成功（交易所协议）")

def confirm_entry_exchange_pledge(page_obj, approval_number: str):
    """交易所质押式回购：入仓确认"""
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)
    # 如有本业务特有字段，补在这里
    click_entry(page)
    print("✅ 入仓成功（交易所质押）")

def confirm_entry_exchange_lending(page_obj, approval_number: str):
    """交易所债券借贷：入仓确认"""
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2090-12-01")
    open_row_by_approval(page, approval_number)
    # 如有本业务特有字段，补在这里
    click_entry(page)
    print("✅ 入仓成功（交易所债券借贷）")
