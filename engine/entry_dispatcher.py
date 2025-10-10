# engine/entry_dispatcher.py
# -*- coding: utf-8 -*-
"""
入仓分发器：根据业务类型关键词，把入仓动作路由到对应的入仓实现函数。
✅ 兼容两种调用方式：
   - confirm_entry(self.page, approval_number, business_type)           # 直接传 Page
   - confirm_entry(self, approval_number, business_type)                # 传带 .page 的对象
"""

from typing import Any
from playwright.sync_api import Page

# ====== 各业务入仓实现（保持你原来的导入）======
from engine.entries.interbank_entry import (
    confirm_entry_interbank,
    confirm_entry_interbank_pledge,
    confirm_entry_interbank_outright,
    confirm_entry_interbank_lending, #银行间债券借贷
    confirm_entry_interbank_credit_loan # 银行间信用拆借

)

from engine.entries.exchange_entry import (
    confirm_entry_exchange_bond_trade,
    confirm_entry_exchange_protocol,
    confirm_entry_exchange_pledge,
    confirm_entry_exchange_lending,
)

from engine.entries.fund_entry import (
    confirm_entry_exchange_fund_business,
    confirm_entry_exchange_fund_redeem,
    confirm_entry_otc_fund_redeem,
)

from engine.entries.other_entry import confirm_entry_distribution_trading


# ---------- 改动点①：适配器，统一“页面宿主” ----------
def _ensure_host(page_or_host: Any):
    """
    允许传入：
      - Page 实例
      - 带 .page 属性的对象
    统一返回一个“宿主”对象 host，使得后续都能用 host.page 拿到 Page。
    """
    if isinstance(page_or_host, Page):
        # 把 Page 包装成带 .page 的“宿主”
        from types import SimpleNamespace
        return SimpleNamespace(page=page_or_host)
    if hasattr(page_or_host, "page"):
        return page_or_host
    raise TypeError("confirm_entry() 需要传 Page 或者带 .page 属性的对象")


# ---------- 改动点②：主分发函数，使用适配器统一入参 ----------
def confirm_entry(page_obj: Any, approval_number: str, business_type: str):
    """
    根据业务类型关键词智能分发对应入仓逻辑。
    兼容 page_obj 为 Page 或 带 .page 的对象。
    """
    host = _ensure_host(page_obj)                     # ✅ 统一为 host（一定有 host.page）
    business_type = (business_type or "").strip()

    # ✅ 关键词 ➜ 入仓函数 的映射（保留你原有的）
    mapping = {
        "银行间现券":  confirm_entry_interbank,
        "银行间质押":  confirm_entry_interbank_pledge,
        "银行间买断":  confirm_entry_interbank_outright,
        "银行间债券借贷": confirm_entry_interbank_lending,
        "银行间信用拆借": confirm_entry_interbank_credit_loan,

        "交易所现券":  confirm_entry_exchange_bond_trade,
        "交易所协议":  confirm_entry_exchange_protocol,
        "交易所质押":  confirm_entry_exchange_pledge,
        "交易所债券借贷": confirm_entry_exchange_lending,

        "分销买卖":    confirm_entry_distribution_trading,

        "场内基金买卖": confirm_entry_exchange_fund_business,
        "场内基金申赎": confirm_entry_exchange_fund_redeem,
        "场外基金申赎": confirm_entry_otc_fund_redeem,
    }

    for keyword, func in mapping.items():
        if keyword in business_type:
            # ✅ 统一把 “host”（带 .page）传给具体入仓函数
            return func(host, approval_number)

    raise Exception(f"❌ 无法识别业务类型: {business_type}")
