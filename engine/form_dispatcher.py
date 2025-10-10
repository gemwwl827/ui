# engine/form_dispatcher.py
# =============================================================================
# ✅ 表单调度器（统一版 + 调试日志）
#
# 目标：
#   - 统一：所有业务在调用页面类前，先把 form_data 扁平化为 entry
#   - 优先：走“模块化页面类”；找不到再回退“旧方法映射”（保持兼容）
#   - 多指令：无论模块化/回退，全部走统一的多指令编排（新建/加入列表/提交）
#
# 说明：
#   1) 你在各页面类里只需实现“单条指令”的 fill_form(entry) 即可；
#      多条指令时的“编排”（新建/加入列表/提交）由本调度器统一处理。
#   2) 本版本仅新增了大量 print 调试信息，方便排查“没跳到业务页/没有点击按钮”的问题；
#      行为与之前一致。
# =============================================================================

from typing import List, Dict, Optional
from utils.data_utils import normalize_entry  # 扁平化/字段归一
from pages.base_page import BasePage  # ✅ 引入封装好的点击函数

# ---- 模块化页面类（若导入失败，自动回退旧逻辑） ----
MODULAR: bool = True
try:
    from pages.base_page import BasePage
    from pages.interbank_cashbond_page import InterbankCashBondPage
    from pages.interbank_pledge_repo_page import InterbankPledgeRepoPage
    from pages.interbank_outright_repo_page import InterbankOutrightRepoPage
    from pages.exchange_cashbond_page import ExchangeCashBondPage
    from pages.exchange_agreement_repo_page import ExchangeAgreementRepoPage
    from pages.exchange_pledge_repo_page import ExchangePledgeRepoPage
    from pages.fund_exchange_buy_sell_page import FundExchangeBuySellPage
    from pages.fund_exchange_redeem_page import FundExchangeRedeemPage
    from pages.otc_fund_redeem_page import OtcFundRedeemPage
    from pages.distribution_trading_page import DistributionTradingPage  # 分销买卖
    from pages.interbank_bond_lending_page import InterbankBondLendingPage  # 银行间债券借贷
    from pages.interbank_credit_loan_page import InterbankCreditLoanPage  # 银行间信用拆借
    from pages.exchange_bond_lending_page import ExchangeBondLendingPage  # 交易所债券借贷
except Exception:
    MODULAR = False  # 无法导入模块化页面类 → 回退旧方法


# ---- 业务关键词 → 模块化页面类（子串匹配）----
BUSINESS_REGISTRY: Dict[str, object] = {}
if MODULAR:
    BUSINESS_REGISTRY = {
        # 债券类（银行间）
        "银行间现券": InterbankCashBondPage,
        "银行间质押": InterbankPledgeRepoPage,
        "银行间买断": InterbankOutrightRepoPage,
        "银行间债券借贷": InterbankBondLendingPage,
        "银行间信用拆借": InterbankCreditLoanPage,

        # 债券类（交易所）
        "交易所现券": ExchangeCashBondPage,
        "交易所协议": ExchangeAgreementRepoPage,
        "交易所质押": ExchangePledgeRepoPage,
        "交易所债券借贷": ExchangeBondLendingPage,

        # 其他
        "分销买卖": DistributionTradingPage,

        # 基金类
        "场内基金买卖": FundExchangeBuySellPage,
        "场内基金申赎": FundExchangeRedeemPage,
        "场外基金申赎": OtcFundRedeemPage,
    }


# --- DEBUG 工具：打印 entry 的关键字段摘要，避免刷屏 ---
def _brief_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {"_type": type(entry).__name__}
    keys = [
        "business_type", "submit_mode", "指令模式", "instruction_index",
        "transaction_direction", "direction",
        "bond_code", "bond_name", "asset_code", "asset_name",
        "group", "组合",
        "trade_amount", "成交金额",
        "settlement_speed", "清算速度",
    ]
    out = {}
    for k in keys:
        v = entry.get(k)
        if v not in (None, "", []):
            out[k] = v
    return out


class FormDispatcher:
    """
    ✅ 表单调度器：根据 business_type 自动把 entry 交给对应页面类去“填表”。
    用法：
        FormDispatcher().dispatch(page_or_ctx, data)

      - page_or_ctx：Playwright Page 或带 .page 的上下文对象
      - data：dict。来自 data_loader 的该组用例，通常形如：
              {
                'business_type': '交易所现券买卖',
                'form_data': {...} 或 [ {...}, {...} ],
                'checks': [...]
              }
    """

    # ---- 回退用：业务关键词 → 旧页面类的方法名（单条）----
    # 说明：回退路径下我们仍然调用“单条填表”的老方法；多指令编排由本模块完成。
    keyword_to_method: Dict[str, str] = {
        "银行间现券": "fill_interbank_cashbond_form",
        "银行间质押": "fill_interbank_pledge_repo_form",
        "银行间买断": "fill_interbank_outright_repo_form",
        "交易所现券": "fill_exchange_cashbond_form",
        "交易所协议": "fill_exchange_agreement_repo_form",
        "交易所质押": "fill_exchange_pledge_repo_form",
        "分销买卖": "fill_other_distribution_trading_form",
        "银行间债券借贷": "fill_other_distribution_trading_form",  # 若你有专用方法可替换
        # 基金等需要可继续扩展
    }

    # ---------- 工具：拿到 Page ----------
    def _get_page(self, page_or_ctx):
        """拿到 Playwright Page（兼容传 ctx 或直接传 Page）"""
        return getattr(page_or_ctx, "page", page_or_ctx)

    # ---------- 工具：模块化类匹配 ----------
    def _match_business_class(self, business_type: str):
        """根据业务类型子串匹配模块化页面类"""
        for kw, cls in BUSINESS_REGISTRY.items():
            if kw in (business_type or ""):
                return cls
        return None

    # ---------- 工具：回退方法匹配 ----------
    def _match_legacy_method(self, page_obj, business_type: str):
        """回退路径：找到页面对象上的旧方法"""
        for kw, method_name in self.keyword_to_method.items():
            if kw in (business_type or ""):
                return getattr(page_obj, method_name, None)
        return None

    # ---------- 工具：统一 submit_mode ----------
    @staticmethod
    def _norm_submit_mode(entry: Dict) -> str:
        """
        把 Excel/entry 上各种写法统一成 '加入列表' / '新建'
        优先级：submit_mode > submit_modes > multi_mode > 操作模式(多个指令)
        """
        return (
            entry.get("submit_mode")
            or entry.get("submit_modes")
            or entry.get("multi_mode")
            or entry.get("操作模式(多个指令)")
            or ""
        ).strip() or "加入列表"

    # =========================================================================
    # ✅ 统一的“多指令编排”
    #    - 第二条起，如该条模式为『新建』则先点击新建清空页面
    #    - 每条根据模式决定是否点『加入列表』
    #    - 末尾如有必要点击一次『提交』（出现过『加入列表』或最后一条不是『新建』）
    # =========================================================================



    def fill_and_submit_multiple_instructions(
            self,
            page_or_ctx,
            business_type: str,
            form_data_list: List[Dict],
    ):
        """
        ✅ 多指令统一编排（按 2.0 的最简节奏）：
           - 第 1 条：正常填写 → 根据模式点击（通常『加入列表』）
           - 第 2 条起：先点【新建】 → 填写 → 根据模式点击
           - 末尾：只要出现过『加入列表』，统一点一次【提交】

        ✅ 本版本仅将【新建】与【加入列表】替换为 BasePage 中封装的点击方法，增强稳健性。
        """
        page = self._get_page(page_or_ctx)
        base = BasePage(page)  # ✅ 实例化 base，用于调用封装的点击方法

        entries = [normalize_entry(x) for x in (form_data_list or [])]

        def _mode_of(e: Dict) -> str:
            return (
                    e.get("submit_mode")
                    or e.get("submit_modes")
                    or e.get("multi_mode")
                    or e.get("操作模式(多个指令)")
                    or ""
            ).strip() or "加入列表"

        modes = [_mode_of(e) for e in entries]

        print("========== [MULTI-2.0] START ==========")
        print(f"[MULTI-2.0] business_type={business_type!r} | total={len(entries)} | modes={modes}")

        page_cls = self._match_business_class(business_type)
        use_modular = (MODULAR and page_cls is not None)
        print(f"[MULTI-2.0] modular={use_modular} | page_cls={getattr(page_cls, '__name__', None)}")

        for i, entry in enumerate(entries):
            mode = modes[i]
            brief = {
                "idx": i + 1,
                "mode": mode,
                "direction": entry.get("transaction_direction") or entry.get("交易方向"),
                "bond_code": entry.get("bond_code") or entry.get("债券代码"),
                "settlement": entry.get("settlement_speed") or entry.get("清算速度"),
            }
            print(f"[MULTI-2.0] #{i + 1} entry={brief}")

            # ✅ 从第 2 条开始点击【新建】
            if i > 0:
                try:
                    print(f"[MULTI-2.0] #{i + 1} 点击【新建】")
                    base.safe_click_button("新建")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"[MULTI-2.0] #{i + 1} 点击【新建】异常: {e}")

            try:
                if use_modular:
                    print(f"[MULTI-2.0] #{i + 1} -> {page_cls.__name__}.fill_form(entry)")
                    page_cls(page).fill_form(entry)
                else:
                    legacy_method = self._match_legacy_method(page_or_ctx, business_type)
                    if not legacy_method:
                        raise AttributeError(f"❌ 页面对象上没有找到旧方法，business_type={business_type!r}")
                    print(f"[MULTI-2.0] #{i + 1} -> legacy_method(entry) = {legacy_method.__name__}")
                    legacy_method(entry)
            except Exception as e:
                print(f"[MULTI-2.0] #{i + 1} 填表异常: {e}")

            # ✅ 点击【加入列表】（或其他）
            if mode == "加入列表":
                try:
                    before = page.locator("table tbody tr").count()
                    print(f"[MULTI-2.0] #{i + 1} 点击【加入列表】 | rows_before={before}")
                    base.safe_click_button("加入列表")  # ✅ 封装后点击
                    page.wait_for_timeout(800)
                    after = page.locator("table tbody tr").count()
                    delta = (after - before) if (after != -1 and before != -1) else "NA"
                    print(f"[MULTI-2.0] #{i + 1} rows_after={after} | delta={delta}")
                    if isinstance(delta, int) and delta <= 0:
                        print("[MULTI-2.0] ⚠️ 加入列表后行数未增长，可能点击未生效或 DOM 重绘")
                except Exception as e:
                    print(f"[MULTI-2.0] #{i + 1} 点击【加入列表】异常: {e}")

            elif mode == "新建":
                if i < len(entries) - 1:
                    try:
                        print(f"[MULTI-2.0] #{i + 1} 模式=新建 → 本条结束后点一次【新建】为下一条准备")
                        base.safe_click_button("新建")  # ✅ 用封装的
                        page.wait_for_timeout(800)
                    except Exception as e:
                        print(f"[MULTI-2.0] #{i + 1} 模式=新建（尾部新建）点击异常: {e}")
                else:
                    print(f"[MULTI-2.0] #{i + 1} 模式=新建（最后一条）→ 不点新建，等待统一提交")

            else:
                try:
                    print(f"[MULTI-2.0] #{i + 1} ⚠️ 未识别模式{mode!r}，按『加入列表』处理")
                    base.safe_click_button("加入列表")  # ✅ 用封装的
                    page.wait_for_timeout(800)
                except Exception as e:
                    print(f"[MULTI-2.0] #{i + 1} 未识别模式下点击【加入列表】异常: {e}")

        if any(_mode_of(d) == "加入列表" for d in form_data_list):
            try:
                print("[MULTI-2.0] 统一点击【提交】")
                base.click_submit()  # ✅ 提交也用封装方法（可选）
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[MULTI-2.0] 统一点击【提交】异常: {e}")
        else:
            print("[MULTI-2.0] 未出现『加入列表』，跳过统一提交")

        print("========== [MULTI-2.0] END ==========")

    # =========================================================================
    # ✅ 核心入口：dispatch
    #    - form_data 为 list → 无脑走“多指令编排”（所有业务通用）
    #    - form_data 为 dict → 单条：走模块化 fill_form(entry)，否则回退旧方法
    # =========================================================================
    def dispatch(self, page_or_ctx, data: Dict):
        """
        :param page_or_ctx: 上下文（含 .page）或直接 Page
        :param data:        本组用例数据（必须包含 business_type；通常包含 form_data）
        """
        business_type = (data.get("business_type") or "").strip()
        if not business_type:
            raise ValueError("❌ 缺少字段 business_type，无法调度表单方法")

        page = self._get_page(page_or_ctx)
        form_data = data.get("form_data")

        print(f"[DISPATCH] business_type={business_type!r} | use_modular={MODULAR}")

        # --- 情况 A：多指令（list）→ 统一的多指令编排 ---
        if isinstance(form_data, list):
            print(f"[DISPATCH] form_data 为 list[{len(form_data)}] → 走多指令编排")
            # 打印每条的 submit_mode 摘要
            try:
                modes = [self._norm_submit_mode(normalize_entry(x)) for x in form_data]
            except Exception:
                modes = ["?"] * len(form_data)
            print(f"[DISPATCH] 多指令 submit_mode={modes}")
            return self.fill_and_submit_multiple_instructions(
                page_or_ctx, business_type, form_data
            )

        # --- 情况 B：单指令（dict / 其他）---
        # 模块化优先
        if MODULAR:
            page_cls = self._match_business_class(business_type)
            if page_cls:
                entry = normalize_entry(form_data) if isinstance(form_data, dict) else normalize_entry(data)
                print(f"[DISPATCH] 命中模块化页面类 → {page_cls.__name__}")
                print(f"[DISPATCH] 单指令 entry 摘要：{_brief_entry(entry)}")
                return page_cls(page).fill_form(entry)
            else:
                print("[DISPATCH] 未命中模块化页面类，尝试回退旧方法映射")

        # 回退路径：匹配旧方法名
        legacy_method = self._match_legacy_method(page_or_ctx, business_type)
        if legacy_method:
            entry = normalize_entry(form_data) if isinstance(form_data, dict) else normalize_entry(data)
            print(f"[DISPATCH-OLD] 命中回退旧方法 → {legacy_method.__name__}")
            print(f"[DISPATCH-OLD] 单指令 entry 摘要：{_brief_entry(entry)}")
            return legacy_method(entry)

        # 全部未命中 → 友好提示
        supported_mod = list(BUSINESS_REGISTRY.keys()) if MODULAR else []
        supported_old = list(self.keyword_to_method.keys())
        supported = "，".join(sorted(set(supported_mod + supported_old)))
        raise Exception(
            f"❌ 无法识别的业务类型：【{business_type}】。"
            f"请在 business_type 中包含以下关键词之一：{supported}"
        )
