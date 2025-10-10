"""
scenarios/base.py
- ScenarioContext：把 Page、Navigator、Dispatcher、ApprovalFlow、RiskEngine 类装进上下文，
  供场景（Scenario）与执行器（Executor）共享。
- ScenarioBase：所有场景的抽象基类；只定义“跨组编排”的入口 run()。
  子类负责决定多组的执行顺序（例如 normal：逐组 提交→审批；214：A→B→回批A）。

规范统一返回值（便于汇总/导出/统计）：
{
  'assertion_results': list[dict],  # 所有断言记录（提交/审批阶段）
  'failed_groups': list[str],       # 断言失败的组键（用例编号）
  'generated_approvals': list[str]  # 执行过程中产生的审批号
}

说明：
- Scenario 只负责“跨组编排”；单/多指令的差异放在 Executor（Single/Multi）里处理。
"""

from typing import List, Dict, Any, TypedDict


class ScenarioResult(TypedDict):
    assertion_results: List[Dict[str, Any]]
    failed_groups: List[str]
    generated_approvals: List[str]


class ScenarioContext:
    """
    执行上下文：把所有外部依赖集中起来，子模块通过 context 直接使用。
    - page: Playwright Page
    - test_data_file: Excel 路径
    - navigator: TradeFormNavigator 实例
    - flow: ApprovalFlow 实例
    - dispatcher: FormDispatcher 实例
    - engine_cls: RiskAssertionEngine “类”（注意：是类，不是实例）
    """
    def __init__(self, page, test_data_file, navigator, flow, dispatcher, engine_cls):
        self.page = page
        self.test_data_file = test_data_file
        self.navigator = navigator
        self.flow = flow
        self.dispatcher = dispatcher
        self.engine_cls = engine_cls


class ScenarioBase:
    """场景抽象类：定义跨组编排的统一接口。"""
    name = "base"

    def run(
        self,
        context: ScenarioContext,
        grouped_data: Dict[str, Dict[str, Any]],  # data_loader 产出：每组含 form_data / checks (/ form_data_list)
        group_keys: List[str],                    # 本次要执行的组键（用例编号列表）
    ) -> ScenarioResult:
        """执行给定的 group_keys 并返回统一结果；具体编排由子类实现。"""
        raise NotImplementedError
