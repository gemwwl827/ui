# engine/entries/interbank_entry.py
# -*- coding: utf-8 -*-
from playwright.sync_api import Page
from .common_entry import (
    goto_entry_list,          # 进入 清算管理 -> 核对确认 -> 申请确认入仓
    set_date_range,           # 设置查询日期范围
    open_row_by_approval,     # 翻页查找申请单号并进入编辑页
    click_entry,              # 点击“入仓”
)


# ====== 仅供“银行间买断式回购”使用的补录字段 ======
def _fill_outright_required_fields(page: Page, trader_name: str | None = None) -> None:
    """
    处理买断式回购入仓前可能要求的必填项（如：本方交易员）。
    - 优先按名称/必填星号匹配下拉框
    - 如果给了 trader_name 就按名字选；否则兜底选第一项
    """
    try:
        # 下拉框定位：不同环境可能是“本方交易员 / * 本方交易员 / 交易员”
        try:
            trader_cb = page.get_by_role("combobox", name="* 本方交易员")
        except Exception:
            try:
                trader_cb = page.get_by_role("combobox", name="本方交易员")
            except Exception:
                trader_cb = page.get_by_role("combobox", name="交易员")

        trader_cb.click()

        if trader_name:
            # 有明确姓名时，精确选择
            page.get_by_role("option", name=trader_name).click()
        else:
            # 没有姓名就兜底选第一项
            page.get_by_role("listbox").get_by_role("option").first.click()

    except Exception:
        # 页面没有该字段或已经有默认值 -> 忽略即可
        pass


# ========== 银行间现券买卖 ==========
def confirm_entry_interbank(page_obj, approval_number: str) -> None:
    """
    银行间现券买卖：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2029-12-01")
    open_row_by_approval(page, approval_number)

    # 现券买卖通常无额外必填项，直接入仓
    click_entry(page)
    print("✅ 入仓成功（银行间现券买卖）")


# ========== 银行间买断式回购 ==========
def confirm_entry_interbank_outright(page_obj, approval_number: str) -> None:
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # ✅ 新增：买断式回购特有的必填字段（如本方交易员）
    _fill_outright_required_fields(page, trader_name=None)   # 想指定人就填名字，比如 "李亮"

    click_entry(page)
    print("✅ 入仓成功（银行间买断式回购）")



# ========== 银行间质押式回购 ==========
def confirm_entry_interbank_pledge(page_obj, approval_number: str) -> None:
    """
    银行间质押式回购：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2025-12-01")
    open_row_by_approval(page, approval_number)

    # 若该业务也有额外必填项，可在此处补充；否则直接入仓
    click_entry(page)
    print("✅ 入仓成功（银行间质押式回购）")
# ========== 银行间债券借贷 ==========
def confirm_entry_interbank_lending(page_obj, approval_number: str) -> None:
    """
    银行间债券借贷：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2099-12-01")
    open_row_by_approval(page, approval_number)

    # 若该业务也有额外必填项，可在此处补充；否则直接入仓
    click_entry(page)
    print("✅ 入仓成功（银行间债券借贷）")


# ========== 银行间债券借贷 ==========
def confirm_entry_interbank_credit_loan(page_obj, approval_number: str) -> None:
    """
    银行间信用拆借：入仓确认
    """
    page: Page = page_obj.page
    goto_entry_list(page)
    set_date_range(page, "2024-10-01", "2099-12-01")
    open_row_by_approval(page, approval_number)

    # 若该业务也有额外必填项，可在此处补充；否则直接入仓
    click_entry(page)
    print("✅ 入仓成功（银行间信用拆借）")