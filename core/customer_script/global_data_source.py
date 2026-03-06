from core.task_object.global_cache import GlobalCache
from typing import List, Dict, Any, Union, Optional


class GlobalDataSource:
    def __init__(self, global_cache: GlobalCache):
        """
        初始化时将分块的原始数据扁平化为一个完整的列表 (Table Map)。
        对应需求 1 & 2
        """
        self._origin_case_global_data_source_mapping = global_cache.origin_case_global_data_source_mapping
        self._table_rows = []
        # 遍历所有 key (如 "293", "304")，将它们内部的列表合并
        for group_key, rows in self._origin_case_global_data_source_mapping.items():
            for row in rows:
                # 可以在这里保留原始的 group_key 以备后用，如果不需要可忽略
                # row['_source_group'] = group_key
                self._table_rows.append(row)

    def get_column(self, column_name: str) -> List[Any]:
        """
        获取某一列的所有值。如果某行没有该字段，则自动跳过（不返回空）。
        对应需求 3
        """
        return [
            row[column_name]
            for row in self._table_rows
            if column_name in row
        ]

    def query_rows(self,
                   key: str,
                   value: Any,
                   match_type: str = 'equals',
                   return_index: Optional[int] = None) -> Union[List[Dict], Dict, None]:
        """
        根据 key 和 value 查询行。
        对应需求 4

        :param key: 要匹配的字段名
        :param value: 要匹配的值
        :param match_type: 'equals' (相等) 或 'contains' (包含)
        :param return_index: 如果不为 None，则只返回结果列表中的第 n 个元素
        """
        results = []
        for row in self._table_rows:
            # 如果行里没有这个 key，直接跳过
            if key not in row:
                continue

            row_val = row[key]

            is_match = False
            if match_type == 'equals':
                # 强制转字符串比较，防止整数和字符串 "18" vs 18 匹配失败，可根据实际情况调整
                is_match = str(row_val) == str(value)
            elif match_type == 'contains':
                # 只有当 row_val 是字符串或列表时 'in' 操作才安全
                is_match = str(value) in str(row_val)

            if is_match:
                results.append(row)

        # 如果指定了下标，返回单个对象
        if return_index is not None:
            if 0 <= return_index < len(results):
                return results[return_index]
            return None  # 下标越界返回 None

        return results

    def query_by_intersection(self,
                              external_list: List[Dict],
                              external_key: str,
                              data_key: str) -> List[Dict]:
        """
        传入一个外部列表，只要外部列表某元素的 external_key 值出现在当前数据的 data_key 中，
        就返回当前数据的这一行。
        对应需求 5
        """
        # 1. 先提取外部列表中所有的目标值，存为 Set 以提高查找效率 (O(1))
        target_values = {
            str(item.get(external_key))
            for item in external_list
            if external_key in item
        }

        # 2. 遍历内部数据，查找匹配项
        matched_rows = []
        for row in self._table_rows:
            if data_key in row and str(row[data_key]) in target_values:
                matched_rows.append(row)

        return matched_rows

    @property
    def all_data(self):
        """查看完整扁平化后的数据"""
        return self._table_rows

#
# # 1. 定义你的原始数据
# raw_data = {
#     "293": [
#         {"name": "Sheldon", "$ast_set_name": "数据_hu7Xe", "age": "18"},
#         {"$ast_set_name": "数据_QtZIW", "name": "Tom", "age": "29"}
#     ],
#     "304": [
#         {"$ast_set_name": "数据_HXU2d", "private_name": "Jone", "private_age": "18岁"},
#         {"$ast_set_name": "数据_XvkQF", "private_name": "Yuki", "private_age": "100岁"}
#     ],
#     "305": [
#         {"$ast_set_name": "数据_SA7Zn", "name": "Sheldon", "index": "1"},
#         {"name": "Tom", "$ast_set_name": "数据_BvSJq", "index": "1990"},
#         {"$ast_set_name": "数据_vkSMU", "name": "Yummy", "index": "-10"}
#     ]
# }
# #
# # # 2. 初始化类
# # ds = GlobalDataSource(raw_data)
# #
# # # --- 测试需求 3: 获取 name 这一列 ---
# # # 预期: 304 组的数据没有 name 字段，应该被跳过
# # names = ds.get_column("name")
# # print(f"需求3 (Name列): {names}")
# # # 输出: ['Sheldon', 'Tom', 'Sheldon', 'Tom', 'Yummy']
# #
# #
# # # --- 测试需求 4: 行查询 ---
# # # 场景 A: 查找 name=Sheldon 的所有行
# # sheldons = ds.query_rows(key="name", value="Sheldon")
# # print(sheldons)
# # print(f"\n需求4 (查找 Sheldon): 找到 {len(sheldons)} 条数据")
# #
# # # 场景 B: 查找 index 包含 '99' 的行 (模糊匹配)
# # match_contains = ds.query_rows(key="index", value="99", match_type="contains")
# # print(f"需求4 (包含匹配 '99'): {match_contains}")
# #
# # # 场景 C: 查找 name=Sheldon 并只取第 1 个 (index=1)
# # second_sheldon = ds.query_rows(key="name", value="Sheldon", return_index=1)
# # print(f"需求4 (指定下标返回): {second_sheldon}")
# #
# # # --- 测试需求 5: 列表交叉匹配 ---
# # # 外部列表：比如我想找 assigneeName 是 "Yummy" 或 "Jone" 的数据
# # external_list = [
# #     {"assigneeName": "Yummy", "task": "A"},
# #     {"assigneeName": "Jone", "task": "B"},  # Jone 在 name 字段中不存在(他在private_name里)，所以不会匹配
# #     {"assigneeName": "Nobody", "task": "C"}
# # ]
# #
# # # 逻辑：只要 external_list 里的 assigneeName 等于 我们数据里的 name，就返回我们数据的那一行
# # intersection_results = ds.query_by_intersection(
# #     external_list=external_list,
# #     external_key="assigneeName",
# #     data_key="name"
# # )
# #
# # print(f"\n需求5 (交叉匹配): {intersection_results}")
# # # 预期输出: 应该只返回 name="Yummy" 的那一行数据
