from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, Union, Any

from core.record.utils import ProcessObject, ExceptionProcessObject, ErrorWarningProcessObject
from core.task_object.child_case_list import ChildCase
from core.task_object.step_mapping import Case, ChildMultitasker, ChildStepCase
from core.task_object.case_list import Case as GlobalCase
from core.enums.executor import ErrorStrategyMixinEnum, NodeStatusEnum, RaiseErrorTypeEnum, NodeResultEnum

if TYPE_CHECKING:
    from core.task_object.galobal_mapping import MultiwayTreeNode
    from core.payload.step_exec import RunStepExecutor


class SkippedParentController:

    def __init__(self, node: MultiwayTreeNode):
        self.node: MultiwayTreeNode[RunStepExecutor] = node
        self.exec_runner = self.node.node
        self.in_case = self.exec_runner.in_case

    def exec(self) -> str:
        node, child_iter = self.get_real_error_strategy(self.node)
        return self.change_parent_status(node, child_iter)

    def change_parent_status(self, error_strategy_node: MultiwayTreeNode, child_iter):
        error_strategy = error_strategy_node.node.metadata.error_strategy
        if error_strategy == ErrorStrategyMixinEnum.TASK:
            task_node = self.get_task_node(self.node)
            task_node.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.CURRENT_STEP:
            pass
        elif error_strategy == ErrorStrategyMixinEnum.CASE:
            if not self.in_case:
                main_case_node: MultiwayTreeNode = self.get_mian_case_node(self.node)
                main_case_node.node.status = NodeStatusEnum.SKIPPED
            else:
                # 发现是结束用例，但是现在需要判断是结束内部用例中的用例，还是结束当前主用例当中的用例
                # 通过拿到内部用例的Case metadata节点，获取它是由子用例自己决定还是其他
                # 如果是由子用例自己决定，那么可以断言，这个结束用例就是把Case直接结束
                # 如果是其他的，也就是说结束case这个动作一定是针对当前主用例的
                case_node = self.exec_runner.search_node(self.node, lambda node: isinstance(node.node.metadata, Case))
                if case_node.node.metadata.error_strategy == ErrorStrategyMixinEnum.REF_CASE_INNER:
                    case_node.node.status = NodeStatusEnum.SKIPPED
                else:
                    main_case_node: MultiwayTreeNode = self.get_mian_case_node(self.node)
                    main_case_node.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.CURRENT_CASE:
            if not self.in_case:
                main_child_case_node: MultiwayTreeNode = self.get_main_child_case_node(self.node)
                main_child_case_node.node.status = NodeStatusEnum.SKIPPED
            else:
                # 发现是结束当前子用例，依然是需要知道是结束子用例中的当前用例，还是结束主用例中的子用例
                case_node = self.exec_runner.search_node(self.node, lambda node: isinstance(node.node.metadata, Case))
                if case_node.node.metadata.error_strategy == ErrorStrategyMixinEnum.REF_CASE_INNER:
                    # 重新通过parent找到ChildStepCase，然后跳过它
                    inner_child_case_node = self.get_inner_child_case_node(self.node)
                    inner_child_case_node.node.status = NodeStatusEnum.SKIPPED
                else:
                    main_child_case_node: MultiwayTreeNode = self.get_main_child_case_node(self.node)
                    main_child_case_node.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.MULTITASKER:
            # 如果是结束执行器，那么它肯定会经过子执行器，也就是说child_iter一定有值，并且就是希望结束执行器的步骤的子虚拟步骤
            # 那么现在就直接将这个虚拟子执行器的parent拿到，然后设置为skipped即可
            # 并且这个操作是不分在不在子用例里面的，因为要么是穿透了子用例来到了上层的执行器，要么是没穿透在子用例内部的执行器，反正现在是要结束掉执行器，已经必定存储在child_iter里面了，直接设置为skipped即可
            child_iter.parent.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.CURRENT_MULTITASKER:
            # 和MULTITASKER一样，直接设置为skipped即可
            child_iter.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.REF_CHILD_CASE:
            # 结束掉引用的子用例，也就是说这个步骤一定是在子用例里面的，我们在子用例里面找到引用子用例即可
            inner_child_case_node = self.get_inner_child_case_node(self.node)
            inner_child_case_node.node.status = NodeStatusEnum.SKIPPED
        elif error_strategy == ErrorStrategyMixinEnum.REF_CASE:
            inner_case_node: MultiwayTreeNode = self.get_inner_case_node(self.node)
            inner_case_node.node.status = NodeStatusEnum.SKIPPED
        return error_strategy

    def get_real_error_strategy(self, node: MultiwayTreeNode = None, child_iter=None, is_first_node=True):
        if hasattr(node.node.metadata,
                   'error_strategy') and node.node.metadata.error_strategy != ErrorStrategyMixinEnum.RAISE and is_first_node:
            if node.node.metadata.error_strategy == ErrorStrategyMixinEnum.CURRENT_MULTITASKER:
                return node, node.parent
            elif node.node.metadata.error_strategy == ErrorStrategyMixinEnum.MULTITASKER:
                return node, node.parent
            else:
                return node, child_iter
        parent_node = node.parent
        if isinstance(parent_node.node.metadata, ChildMultitasker):
            child_iter = parent_node

        if parent_node.node.metadata.error_strategy == ErrorStrategyMixinEnum.RAISE:
            return self.get_real_error_strategy(parent_node, child_iter, is_first_node=False)
        elif parent_node.node.metadata.error_strategy == ErrorStrategyMixinEnum.REF_CASE_INNER:
            if parent_node.node.metadata.case_error_strategy == ErrorStrategyMixinEnum.RAISE:
                return self.get_real_error_strategy(parent_node, child_iter, is_first_node=False)
            else:
                return parent_node, child_iter
        else:
            return parent_node, child_iter

    def get_inner_case_node(self, node: MultiwayTreeNode):
        parent_node = node.parent
        if isinstance(node.node.metadata, Case):
            return node
        elif isinstance(parent_node.node.metadata, Case):
            return parent_node
        else:
            return self.get_inner_case_node(parent_node)

    def get_inner_child_case_node(self, node: MultiwayTreeNode):
        parent_node = node.parent
        if isinstance(node.node.metadata, ChildStepCase):
            return node
        elif isinstance(parent_node.node.metadata, ChildStepCase):
            return parent_node
        else:
            return self.get_inner_child_case_node(parent_node)

    def get_main_child_case_node(self, node: MultiwayTreeNode):
        parent_node = node.parent
        if isinstance(node.node.metadata, ChildCase):
            return node
        elif isinstance(parent_node.node.metadata, ChildCase):
            return parent_node
        else:
            return self.get_main_child_case_node(parent_node)

    def get_mian_case_node(self, node: MultiwayTreeNode):
        parent_node = node.parent
        if isinstance(node.node.metadata, GlobalCase):
            return node
        elif isinstance(parent_node.node.metadata, GlobalCase):
            return parent_node
        else:
            return self.get_mian_case_node(parent_node)

    def get_task_node(self, node: MultiwayTreeNode):
        parent_node = node.parent
        if parent_node is None:
            return node
        elif parent_node.parent is None:
            return parent_node
        else:
            return self.get_task_node(parent_node)


class ProcessErrorTarget:

    def __init__(self, node: MultiwayTreeNode, exception_process_object: ExceptionProcessObject, step_executor):
        self.node = node
        self.exception_process_object = exception_process_object
        self.step_executor = step_executor

    async def exec(self) -> Tuple[
        NodeStatusEnum, NodeResultEnum, Union[
            ErrorWarningProcessObject, ExceptionProcessObject]]:
        """
        error_exec异常处理工具类，到了这里就已经表示命中了自定义异常了
        :return:
        """
        is_raise_exception = self.exception_process_object.raise_object.is_raise_exception
        if is_raise_exception:
            status = NodeStatusEnum.ERROR
            result = NodeResultEnum.ERROR_SELF
            process_object = self.exception_process_object
        else:
            status = NodeStatusEnum.END
            result = NodeResultEnum.SUCCESS
            process_object = ErrorWarningProcessObject(f"命中错误：[{self.node.node.metadata.label}]，不抛出错误")

        return status, result, process_object


def is_error_step_target(process_object: ProcessObject):
    if isinstance(process_object, ExceptionProcessObject):
        if process_object.error_type in [RaiseErrorTypeEnum.FAST, RaiseErrorTypeEnum.SCRIPT]:
            return True
    return False
