import random
import string


class DataSet:
    """
    一个用于存储表格数据的类，支持动态添加行和列。
    """

    def __init__(self):
        """
        初始化一个空的数据集。
        """
        self._columns = []  # 存储列名，包括隐式添加的列
        self._rows = []  # 存储所有行数据（列表的列表）

    @staticmethod
    def _generate_ast_set_name() -> str:
        """
        内部静态方法，用于生成符合规则的$ast_set_name列的值。
        格式：数据_{由大小写字母+数字组成的5位长度的字符}
        """
        # 定义随机字符的来源：大小写字母 + 数字
        chars = string.ascii_letters + string.digits
        # 生成一个5位的随机字符串
        random_str = ''.join(random.choices(chars, k=5))
        return f"数据_{random_str}"

    def set_columns(self, col_definitions: list[str]):
        """
        设置数据集的列，并隐式添加'$ast_set_name'列。

        Args:
            col_definitions (list[str]): 用户定义的列名列表。
        """
        if not isinstance(col_definitions, list):
            raise TypeError("列定义必须是一个列表 (list)。")
        # 复制列表以避免修改外部传入的原始列表
        self._columns = list(col_definitions) + ['$ast_set_name']

    def add_row(self, row: list):
        """
        向数据集中添加一行数据。
        - 如果行数据不足，用None补充。
        - 如果行数据超出，忽略多余部分。
        - 自动生成'$ast_set_name'列的值。

        Args:
            row (list): 要添加的行数据列表。
        """
        if not self._columns:
            raise ValueError("请在使用 add_row 之前，先通过 set_columns 设置列。")

        if not isinstance(row, list):
            raise TypeError("行数据必须是一个列表 (list)。")

        # 计算用户需要提供的列的数量（不包括隐式列）
        num_expected_cols = len(self._columns) - 1

        # 复制行数据以进行处理
        processed_row = list(row)

        # 6. 容错处理
        # 如果超过了，就忽略多余的数据
        if len(processed_row) > num_expected_cols:
            processed_row = processed_row[:num_expected_cols]
        # 如果不够，就补充None
        elif len(processed_row) < num_expected_cols:
            padding = [None] * (num_expected_cols - len(processed_row))
            processed_row.extend(padding)

        # 4. 自动生成并添加隐式列的值
        ast_set_name_value = self._generate_ast_set_name()
        processed_row.append(ast_set_name_value)

        # 将处理好的完整行添加到数据集中
        self._rows.append(processed_row)

    def get_data(self) -> list[dict]:
        """
        5. 内部函数，返回所有行的数据。
        每行是一个字典，键是列名，值是对应的数据。
        """
        all_data = []
        for row_values in self._rows:
            # 使用zip将列名和行数据配对，然后转换为字典
            row_dict = dict(zip(self._columns, row_values))
            all_data.append(row_dict)
        return all_data

    def __iter__(self):
        """
        使DataSet实例成为一个可迭代对象。
        迭代时，将产生与_get_data()格式相同的每行字典。
        """
        yield from self.get_data()





# --- 使用示例 ---
if __name__ == "__main__":
    col_definitions = ["name", "age", "gender", "nickname"]
    # 包含了正常、过长、过短三种情况的行数据
    row_matrix_data = [
        ["Sheldon", 18, "male", "shelly"],  # 正常
        ["Cindy", 16, "female"],  # 过短
        ["Leonard", 19, "male", "leo", "physicist"]  # 过长
    ]

    # 实例化
    dataset = DataSet()
    print(f"初始化的对象: {dataset!r}")

    # 设置列
    dataset.set_columns(col_definitions)

    # 循环添加行
    for row in row_matrix_data:
        dataset.add_row(row)

    print("\n--- DataSet 内容预览 ---")
    print(dataset)

    print("\n--- 内部 get_data() 方法的输出 ---")
    internal_data = dataset.get_data()
    # 为了美观，我们逐行打印
    for item in internal_data:
        print(item)

    print("\n--- 测试迭代功能 (for item in dataset) ---")
    # 因为DataSet是可迭代的，所以可以直接在for循环中使用
    for row_dict in dataset:
        print(f"迭代得到: name={row_dict.get('name')}, ast_name={row_dict.get('$ast_set_name')}")