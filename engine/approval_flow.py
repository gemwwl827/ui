
# engine/approval_flow.py
# -*- coding: utf-8 -*-
"""
流程/审批相关的跨页面动作
- 负责提交 + 风控弹窗处理
"""
import re

from playwright.sync_api import Page


class ApprovalFlow:
    def __init__(self, page: Page):
        self.page = page
        from pages.base_page import BasePage
        self.base = BasePage(page)  # ✅ 提前注入 BasePage，方便调用

    # =========================
    # 提交 + 风控处理（统一入口）
    # =========================
    def submit_with_risk_popup(self, wait_ms: int = 800) -> None:
        """
        通用提交入口：
        1) 点击页面主【提交】
        2) 等待风控弹窗
        3) 优先点击【忽略警告继续提交】
        4) 否则点击【风控信息】弹窗里的【提交】
        5) 兜底点全局【提交】/【确定】
        """
        self.page.wait_for_timeout(wait_ms)

        # Step 1: 点击主页面提交
        print("🚀 [ApprovalFlow] 开始提交申请...")
        self.base.click_toolbar_submit()
        self.page.wait_for_timeout(800)

        # Step 2: 处理风控弹窗
        self._handle_risk_dialogs_and_submit()

    # =========================
    # 仅处理风控弹窗（内部工具）
    # =========================
    def _handle_risk_dialogs_and_submit(self) -> None:
        """
        仅处理风控弹窗，不再点击主提交
        """
        print("🕒 [ApprovalFlow] 等待并处理风控弹窗...")
        self.page.screenshot(path="risk-dialog-before-submit.png", full_page=True)

        try:
            ignore_btn = self.page.get_by_role("button", name="忽略警告继续提交")
            risk_submit = self.page.get_by_label("风控信息").get_by_role("button", name="提交")
            global_submit = self.page.get_by_role("button", name="提交", exact=True)
            ok_btn = self.page.get_by_role("button", name="确定")

            if ignore_btn.is_visible():
                print("✅ 点击风控弹窗中的【忽略警告继续提交】")
                ignore_btn.click()
            elif risk_submit.is_visible():
                print("✅ 点击风控弹窗中的【提交】")
                risk_submit.click()
            elif global_submit.is_visible():
                print("⚠️ 没找到风控区域提交，兜底点击全局【提交】")
                global_submit.click()
            elif ok_btn.is_visible():
                print("⚠️ 没找到提交按钮，兜底点击【确定】")
                ok_btn.click()
            else:
                raise Exception("❌ 未检测到可点击的风控提交/确定按钮")
        except Exception as e:
            print(f"⚠️ 风控提交异常: {e}")
            raise


    def extract_approval_number(self) -> str:
        """页面上读取【申请单编号:【xxx】】并返回编号"""
        elem = self.page.get_by_text("申请单编号:")
        text = elem.text_content()
        print(f"Debug: 申请单编号完整文本: {text}")
        return text.split("【")[1].split("】")[0]

    def goto_pending_approval(self, wait_ms: int = 800) -> None:
        """导航到【交易申请 -> 审批列表 -> 待办审批】"""
        self.page.get_by_role("menuitem", name="交易申请").locator("span").click()
        # self.page.get_by_text("审批列表").click()
        self.page.locator("div").filter(has_text=re.compile(r"^审批列表$")).click()
        self.page.get_by_role("link", name="待办审批").click()
        self.page.wait_for_timeout(wait_ms)


    #---------------待办审批-------------提交------------------
    # engine/approval_flow.py 里的 class ApprovalFlow 内
    def submit_risk_approval_in_approval_process(self) -> None:
        """
        审批流程中风控弹窗的提交处理：
        1) 优先点击【忽略警告继续提交】
        2) 尝试点击【风控信息】区域里的【提交】
        3) 兜底点击全局【提交】
        4) 仍无则尝试【确定】
        """
        page = self.page
        try:
            page.wait_for_timeout(300)

            # 1. 忽略警告继续提交
            try:
                ignore_btn = page.get_by_role("button", name="忽略警告并继续")
                if ignore_btn.is_visible():
                    ignore_btn.click()
                    return
            except Exception:
                pass

            # 2. 风控信息弹窗中的提交
            try:
                risk_submit = page.get_by_label("风控信息").get_by_role("button", name="提交")
                if risk_submit.is_visible():
                    risk_submit.click()
                    return
            except Exception:
                pass

            # 3. 全局提交（exact=True 避免误点）
            try:
                submit_btn = page.get_by_role("button", name="提交", exact=True)
                if submit_btn.is_visible():
                    submit_btn.click()
                    return
            except Exception:
                pass

            # 4. 兜底：确定
            try:
                ok_btn = page.get_by_role("button", name="确定")
                if ok_btn.is_visible():
                    ok_btn.click()
                    return
            except Exception:
                pass

            raise Exception("未检测到可点击的风控提交/确定按钮")

        except Exception as e:
            print(f"❌ 审批流程风控提交异常：{e}")
            raise

    # engine/approval_flow.py  —— 放在 class ApprovalFlow 里面

    def approve_request(
            self,
            approval_number: str,
            risk_engine=None,
            expected_checks=None,
            group_key=None,
            expected_count: int = 0,
            phase: str | None = None,
    ) -> None:
        """
        在待办审批列表中定位编号并完成审批（支持翻页查找）
        包含：
        - 点击【审批】
        - 审批阶段风控断言（可选）
        - 根据风控弹窗内容提交（忽略警告/风控信息提交/兜底提交/确定）
        - “流程审批”弹窗【确定】
        """

        # ✅ Step 1: 查找审批单号并点击
        while True:
            try:
                btn = self.page.get_by_role("button", name=f"{approval_number}")
                btn.wait_for(state="visible", timeout=5000)
                btn.click()
                print(f"✅ 找到审批单号 {approval_number}，开始审批流程")
                break
            except Exception:
                try:
                    next_button = self.page.get_by_label("下一页").first
                    if next_button.is_disabled():
                        print(f"❌ 未找到审批单号 {approval_number}，请检查数据或流程是否正确")
                        return
                    next_button.click()
                    self.page.wait_for_load_state("domcontentloaded")
                except Exception:
                    print(f"❌ 未找到审批单号 {approval_number}，且无“下一页”按钮")
                    return

        self.page.wait_for_timeout(900)  # 稍等页面稳定

        # ✅ Step 2: 点击“审批”按钮，触发风控弹窗
        self.page.get_by_role("button", name="审批").click()
        self.page.wait_for_timeout(1200)

        # ✅ Step 3: 等待风控弹窗表格加载（容错）
        try:
            print("🕒 等待风控弹窗表格加载...")
            self.page.wait_for_selector("div.el-overlay:visible .el-dialog__body", timeout=8000)
            print("✅ 风控弹窗表格已加载")
        except Exception as e:
            print(f"⚠️ 风控弹窗表格加载异常: {e}")

        # ✅ Step 4: 审批阶段风控断言（如传入 risk_engine/数据）
        if risk_engine and expected_checks:
            print("🔍 开始执行【审批】阶段风控断言...")
            risk_engine.print_and_assert_risk_details_multi(
                expected_checks=expected_checks,
                current_group_key=group_key,
                expected_count=int(float(expected_count or 0)),
                phase=phase or "审批",  # 统一标记审批阶段
            )
            # 将 risk_engine 的失败项并入当前实例（若存在容器）
            if hasattr(self, "failed_asserts") and hasattr(risk_engine, "failed_asserts"):
                self.failed_asserts.extend(risk_engine.failed_asserts)

        # ✅ Step 5: 提交风控弹窗（忽略警告 / 风控信息提交 / 兜底“提交或确定”）
        self.submit_risk_approval_in_approval_process()

        # ✅ Step 6: 等待风控关闭
        self.page.wait_for_timeout(700)

        # ✅ Step 7: 点击“流程审批”弹窗中的“确定”按钮（如出现）
        try:
            self.page.wait_for_selector("h4.el-dialog__title", timeout=10000)
            dialogs = self.page.locator("div.el-overlay-dialog")
            for i in range(dialogs.count()):
                dialog = dialogs.nth(i)
                title = dialog.locator("h4.el-dialog__title")
                if title.is_visible() and "流程审批" in title.inner_text().strip():
                    print("🧾 点击流程审批弹窗中的【确定】按钮")
                    dialog.locator("button:has-text('确定')").click()
                    break
        except Exception as e:
            print(f"⚠️ 流程审批弹窗处理异常：{e}")
















    def reset_to_new_request_page(self, path: str = "/traderequest/bank/cashbond") -> None:
        """页面重置到“新建”入口"""
        print("🔁 页面重置：跳回申请新建页")
        self.page.goto(path, timeout=60000)
        self.page.wait_for_timeout(600)
        try:
            self.page.get_by_role("button", name="新建").wait_for(state="visible", timeout=10000)
            print("✅ 页面恢复，准备下一笔")
        except Exception as e:
            print(f"❌ 页面未恢复，找不到【新建】按钮: {e}")
            raise
