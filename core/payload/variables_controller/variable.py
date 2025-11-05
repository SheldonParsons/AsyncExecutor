import json

from core.record.utils import VariableGetProcessObject, VariableSetProcessObject, \
    VariableWarningProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode


class VariableToller:

    @classmethod
    def get_variable_mapping(cls, node: MultiwayTreeNode):
        cache_mapping = {}

        # 使用迭代来替代递归，避免栈溢出和逻辑错误
        current_node = node
        # 获取临时变量
        while current_node is not None:
            if hasattr(current_node.node.metadata, 'temp_variables'):
                temp_vars = current_node.node.metadata.temp_variables
                for k, v in temp_vars.items():
                    if k not in cache_mapping:
                        cache_mapping[k] = v
            if current_node.node.metadata.type == 'child_case':
                current_node = None
            else:
                current_node = current_node.parent

        # 获取环境变量
        merged_env_variable_mapping = cls.get_env_merged_variable(node)
        for k, v in merged_env_variable_mapping.items():
            if k not in cache_mapping:
                cache_mapping[k] = v

        # 获取全局变量
        global_variable_mapping = node.node.global_option.global_cache.origin_global_variable_mapping
        for k, v in global_variable_mapping.items():
            if k not in cache_mapping:
                cache_mapping[k] = v

        return cache_mapping

    @classmethod
    def get_env_merged_variable(cls, node: MultiwayTreeNode):
        merged_env_variable_mapping = {}
        # 先获取当前的节点的项目和环境
        project_id, env = Variable._gpe(node, None)
        # 再获取根节点的项目和环境
        root_project_id, root_env = Variable._get_root_case_project_env(node, None)
        # 如果相同，则只获取一次
        if project_id == root_project_id and env == root_env:
            project_env_mapping = node.node.global_option.global_cache.origin_project_env_variable_mapping.get(
                str(project_id), None)
            merged_env_variable_mapping = project_env_mapping.get(env, {})
        else:
            # 否则，将两个变量进行融合，原本的变量优先级大于当前根用例的环境变量
            project_env_mapping = node.node.global_option.global_cache.origin_project_env_variable_mapping.get(
                str(project_id), None)
            env_variable_mapping = project_env_mapping.get(env, {})

            root_project_env_mapping = node.node.global_option.global_cache.origin_project_env_variable_mapping.get(
                str(root_project_id), None)
            root_env_variable_mapping = root_project_env_mapping.get(root_env, {})
            merged_env_variable_mapping = root_env_variable_mapping | env_variable_mapping
        return merged_env_variable_mapping


class Variable:
    class EmptyObject:
        pass

    @classmethod
    def _get_root_case_project_env(cls, node: MultiwayTreeNode, project_id=None):
        """
        获取当前运行的主用例的项目和环境
        """
        if node.node.metadata.type == 'main_case':
            env = node.node.metadata.env
            if project_id is None:
                project_id = node.node.metadata.project_id
            return project_id, env
        else:
            return cls._get_root_case_project_env(node.parent, project_id)

    @classmethod
    def _gpe(cls, node: MultiwayTreeNode, project_id=None):
        """
        获取项目和环境
        """
        if node.node.metadata.type == 'case':
            if project_id is None:
                project_id = node.node.metadata.project_id
            if node.node.metadata.env_strategy == 'self_case':
                env = node.node.metadata.env
                return project_id, env
            if node.node.metadata.env_strategy == 'current_case':
                return cls._gpe(node.parent, project_id)
            return None, None
        elif node.node.metadata.type == 'main_case':
            env = node.node.metadata.env
            if project_id is None:
                project_id = node.node.metadata.project_id
            return project_id, env
        elif node.node.metadata.type == 'interface':
            project_id = node.node.metadata.project_id
            return cls._gpe(node.parent, project_id)
        else:
            return cls._gpe(node.parent, project_id)

    def _stv(self, node: MultiwayTreeNode, key):
        """
        查询 temp_variables
        """
        if node.node.metadata.type == 'child_case':
            return node.node.metadata.temp_variables.get(key, self.EmptyObject())
        if not hasattr(node.node.metadata, 'temp_variables'):
            return self._stv(node.parent, key)
        else:
            _value = node.node.metadata.temp_variables.get(key, self.EmptyObject())
            if isinstance(_value, self.EmptyObject):
                return self._stv(node.parent, key)
            else:
                return _value

    def _gtv_node(self, node: MultiwayTreeNode) -> MultiwayTreeNode:
        """
        获取上级存在temp_variables的节点
        """
        if hasattr(node.node.metadata, 'temp_variables'):
            return node
        else:
            return self._gtv_node(node.parent)

    def _gcc_node(self, node: MultiwayTreeNode) -> MultiwayTreeNode:
        """
        获取ChildCase节点
        """
        if node.node.metadata.type == 'child_case':
            return node
        else:
            return self._gcc_node(node.parent)


class GlobalVariable(Variable):

    def __init__(self, node: MultiwayTreeNode, can_set=True):
        self.node = node
        self.can_set = can_set

    def get(self, key):
        result = self.node.node.global_option.global_cache.origin_global_variable_mapping.get(key, None)
        desc = json.dumps({
            "key": key,
            "value": result,
            'type': 'global'
        })
        self.node.node.send_step(VariableGetProcessObject(desc=desc))
        return result

    def set(self, key, value):
        if self.can_set:
            desc = json.dumps({
                "key": key,
                "value": value,
                "type": 'global'
            })
            self.node.node.send_step(VariableSetProcessObject(desc=desc))
            self.node.node.global_option.global_cache.origin_global_variable_mapping[key] = value
        else:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"当前步骤不允许使用对变量进行设置"))


class TempVariable(Variable):

    def __init__(self, node: MultiwayTreeNode, can_set=True):
        self.node = node
        self.can_set = can_set

    def get(self, key, scope='global'):
        # 向上查找temp_variables
        value = self._stv(self.node, key)
        if isinstance(value, self.EmptyObject) and scope in ['global', 'env']:
            # 获取临时变量失败，尝试从env、global中查找
            return EnvVariable(self.node).get(key, scope)
        if isinstance(value, self.EmptyObject):
            self.node.node.send_step(VariableWarningProcessObject(desc=f"没有找到该临时变量：{key}"))
            return None
        desc = json.dumps({
            "key": key,
            "value": value,
            'type': 'temp'
        })
        self.node.node.send_step(VariableGetProcessObject(desc=desc))
        return value

    def set(self, key, value, scope='case'):
        if not self.can_set:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"当前步骤不允许对变量进行设置"))
            return None
        if scope == 'case':
            pre_set_node: MultiwayTreeNode = self._gcc_node(self.node)
        else:
            pre_set_node: MultiwayTreeNode = self._gtv_node(self.node)
        pre_set_node.node.metadata.temp_variables[key] = value
        desc = json.dumps({
            "key": key,
            "value": value,
            "type": 'temp'
        })
        self.node.node.send_step(VariableSetProcessObject(desc=desc))
        return None


class EnvVariable(Variable):

    def __init__(self, node: MultiwayTreeNode, can_set=True):
        self.node = node
        self.can_set = can_set

    def set(self, key, value):
        if not self.can_set:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"当前步骤不允许使用对变量进行设置"))
            return None
        try:
            project_id, env = self._gpe(self.node, None)
        except Exception as e:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"系统警告：设置参数时查找项目、环境信息失败"))
            return None
        project_env_mapping = self.node.node.global_option.global_cache.origin_project_env_variable_mapping.get(
            str(project_id), None)
        if not project_env_mapping:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"系统警告：设置参数时获取项目环境信息失败"))
        else:
            env_variable_mapping = project_env_mapping.get(env, None)
            if not env_variable_mapping and env_variable_mapping != {}:
                self.node.node.send_step(VariableWarningProcessObject(desc=f"系统警告：设置参数时获取环境信息失败"))
            else:
                env_variable_mapping[key] = value
                desc = json.dumps({
                    "key": key,
                    "value": value,
                    "type": 'env'
                })
                self.node.node.send_step(VariableSetProcessObject(desc=desc))
        return None

    def get(self, key, scope='global'):
        merged_env_variable_mapping = VariableToller.get_env_merged_variable(self.node)

        if not merged_env_variable_mapping and merged_env_variable_mapping != {}:
            self.node.node.send_step(VariableWarningProcessObject(desc=f"系统警告：获取参数时获取环境信息失败"))
            return None
        else:
            variable = merged_env_variable_mapping.get(key, self.EmptyObject())
            if isinstance(variable, self.EmptyObject):
                if scope == ['global']:
                    variable_from_global = self.node.node.global_option.global_cache.origin_global_variable_mapping.get(
                        key, self.EmptyObject())
                    if isinstance(variable_from_global, self.EmptyObject):
                        self.node.node.send_step(
                            VariableWarningProcessObject(desc=f"系统警告：获取参数时获取环境变量失败"))
                        return None
                    else:
                        return variable_from_global
                else:
                    self.node.node.send_step(
                        VariableWarningProcessObject(desc=f"系统警告：获取参数时获取环境变量失败"))
                    return None
            else:
                desc = json.dumps({
                    "key": key,
                    "value": variable,
                    'type': 'env'
                })
                self.node.node.send_step(VariableGetProcessObject(desc=desc))
                return variable
