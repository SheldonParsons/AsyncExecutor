import tempfile
import os
import shutil
import uuid
from typing import Optional


class TempDirManager:
    """
    一个手动管理的临时目录工具。
    您需要手动调用 cleanup() 方法来删除文件夹。
    """

    def __init__(self):
        # 1. 在实例化时立即创建一个独立的临时文件夹
        self.base_temp_path: Optional[str] = tempfile.mkdtemp()
        print(f"临时目录管理器已初始化，根目录位于: '{self.base_temp_path}'")

    def create_unique_subdir(self) -> str:
        """
        在临时根目录内创建一个唯一的下级目录。
        返回这个唯一子目录的绝对路径。
        """
        if not self.base_temp_path:
            raise RuntimeError("临时目录已被清理，无法创建子目录。")

        # 2. 创建唯一的下级目录，避免文件名冲突
        unique_name = str(uuid.uuid4())
        unique_subdir_path = os.path.join(self.base_temp_path, unique_name)
        os.makedirs(unique_subdir_path)
        print(f"  -> 已创建唯一子目录: '{unique_subdir_path}'")
        return unique_subdir_path

    def create_file(self, content: str, subdir_path: str, filename: str) -> str:
        """
        在指定的子目录中创建文件。
        返回创建的文件的绝对路径。
        """
        file_path = os.path.join(subdir_path, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 3. 获得文件的绝对路径
        absolute_file_path = os.path.abspath(file_path)
        print(f"    -> 文件 '{filename}' 已创建，绝对路径: '{absolute_file_path}'")
        return absolute_file_path

    def cleanup(self):
        """
        手动调用此方法来删除整个临时根目录及其所有内容。
        """
        if self.base_temp_path and os.path.exists(self.base_temp_path):
            print(f"正在清理临时目录: '{self.base_temp_path}'...")
            shutil.rmtree(self.base_temp_path)
            print("清理完成。")
            self.base_temp_path = None  # 防止重复清理
        else:
            print("临时目录不存在或已被清理，无需操作。")

    def __del__(self):
        """
        对象被垃圾回收时的“安全网”。
        注意：不保证总能被执行，但能捕获大部分忘记调用 cleanup() 的情况。
        """
        if self.base_temp_path:
            print(f"警告：TempDirManager 对象被销毁，但 cleanup() 未被调用。")
            print(f"       将尝试自动清理目录: '{self.base_temp_path}'")
            self.cleanup()


# --- 使用示例 ---

def run_process():
    print("--- 进程开始 ---")
    # 在进程的开始部分创建管理器
    temp_manager = TempDirManager()

    # ... 在您的代码中自由地使用 temp_manager ...
    # 它创建的所有文件都会保留下来

    session1_dir = temp_manager.create_unique_subdir()
    path1 = temp_manager.create_file("内容1", session1_dir, "data.txt")

    # 模拟一些其他工作
    print("\n... 正在执行一些耗时任务 ...\n")

    session2_dir = temp_manager.create_unique_subdir()
    path2 = temp_manager.create_file("内容2", session2_dir, "data.txt")

    print(f"\n文件 '{path1}' 是否存在? {os.path.exists(path1)}")

    # 在进程的末尾，或者在您认为合适的任何地方，手动调用清理
    # 如果您注释掉下面这行，__del__ 方法会尝试清理（但依赖它不是好习惯）
    temp_manager.cleanup()

    print(f"\n清理后，文件 '{path1}' 是否还存在? {os.path.exists(path1)}")
    print("--- 进程结束 ---")


if __name__ == '__main__':
    run_process()