# engine/entries/fund_entry.py
# -*- coding: utf-8 -*-
from playwright.sync_api import Page
from .common_entry import (
    goto_entry_list,      # 进入 清算管理 -> 核对确认 -> 申请确认入仓
    set_date_range,       # 设置查询日期范围
    open_row_by_approval, # 翻页查找申请单号并进入“编辑”页
    click_entry,          # 点击“入仓”
)

# ========== 场内基金买卖 ==========
def confirm_entry_exchange_fund_business(page_obj, approval_number: str) -> None:
    """
    场内基金买卖：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # 业务无额外必填项时，直接入仓
    click_entry(page)
    print("✅ 入仓成功（场内基金买卖）")


# ========== 场内基金申赎 ==========
def confirm_entry_exchange_fund_redeem(page_obj, approval_number: str) -> None:
    """
    场内基金申赎：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # 业务差异：可能需要填写“交易价格(元)”
    try:
        page.get_by_role("textbox", name="* 交易价格(元)").fill("100")
    except Exception:
        pass

    click_entry(page)
    print("✅ 入仓成功（场内基金申赎）")


# ========== 场外基金申赎 ==========
def confirm_entry_otc_fund_redeem(page_obj, approval_number: str) -> None:
    """
    场外基金申赎：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # 业务差异：通常需要“交易价格(元)”与“份额”
    try:
        page.get_by_role("textbox", name="* 交易价格(元)").fill("100")
    except Exception:
        pass
    try:
        page.get_by_role("textbox", name="* 份额").fill("10000")
    except Exception:
        pass

    click_entry(page)
    print("✅ 入仓成功（场外基金申赎）")
