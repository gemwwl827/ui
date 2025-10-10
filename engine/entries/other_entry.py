# engine/entries/other_entry.py
# -*- coding: utf-8 -*-
from playwright.sync_api import Page
from .common_entry import (
    goto_entry_list,      # 清算管理 -> 核对确认 -> 申请确认入仓
    set_date_range,       # 设置查询日期范围
    open_row_by_approval, # 翻页查找申请单号并点“编辑”
    click_entry,          # 点击“入仓”
    fill_trader_if_required,  # ✅ 新增：通用交易员选择
)

# engine/entries/other_entry.py
from playwright.sync_api import Page
from .common_entry import (
    goto_entry_list,      # 清算管理 -> 核对确认 -> 申请确认入仓
    set_date_range,       # 设置查询日期范围
    open_row_by_approval, # 翻页查找申请单号并点“编辑”
    click_entry,          # 点击“入仓”
    fill_trader_if_required,  # ✅ 新增：通用交易员选择
)

def confirm_entry_distribution_trading(page_obj, approval_number: str) -> None:
    """
    分销买卖：入仓确认
    """
    page: Page = page_obj.page

    # 进入入仓列表 + 查询区间 + 打开对应申请单
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2026-12-01")
    open_row_by_approval(page, approval_number)

    # ✅ 新增：如该业务需要选择“本方交易员”，这里统一处理。
    #    - 传具体姓名：fill_trader_if_required(page, trader_name="李亮")
    #    - 不传：自动选择第一项
    fill_trader_if_required(page)  # 也可传 trader_name="李亮"

    # 入仓
    click_entry(page)
    print("✅ 入仓成功（分销买卖）")

