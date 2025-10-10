"""
executors/base.py
执行器接口（“单组”用例如何执行）：
- run_submit：导航→新建→填单→触发风控并提交→提交阶段断言 → 返回 (risk_engine, approval_number)
- run_approve：待办列表→审批→审批阶段断言 → 返回 risk_engine
说明：Executor 只处理“一组”的执行；跨组编排交给 Scenario（scenarios/*）。
"""

from typing import Tuple


class ExecutorBase:
    """单组用例的执行器接口：提交(含断言) + 审批(含断言)。"""
    def run_submit(self, context, group_key: str, group: dict, expected_count: int) -> Tuple[object, str]:
        """
        参数：
          - context：ScenarioContext，上下文依赖（page/navigator/flow/dispatcher/engine_cls）
          - group_key：用例编号
          - group：该组的数据包（form_data / checks / form_data_list）
          - expected_count：预期风控条数（用于数量校验）
        返回：
          - risk_engine：提交阶段用到的断言引擎实例
          - approval_number：生成的审批号
        """
        raise NotImplementedError

    def run_approve(self, context, group_key: str, group: dict, expected_count: int, approval_number: str):
        """
        参数：
          - approval_number：run_submit 产生的审批号
        返回：
          - risk_engine：审批阶段的断言引擎实例（可与提交阶段不同）
        """
        raise NotImplementedError
