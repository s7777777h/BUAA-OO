import os
import shutil # 导入用于文件操作的模块

# --- 配置 ---
source_filename = "src.txt"  # 源文件名
output_directory = "out"     # 存放复制文件的子目录名称
# --- 配置结束 ---

def copy_file_multiple_times():
    """
    读取用户输入的份数 n，并将 source_filename 复制 n 次到 output_directory 目录中，
    命名为 1.txt, 2.txt, ..., n.txt。
    """
    # 1. 获取用户输入的份数 n
    while True:
        try:
            n_str = input("请输入要复制的份数 (一个正整数 n): ")
            n = int(n_str)
            if n > 0:
                break  # 输入有效，跳出循环
            else:
                print("错误：请输入一个大于 0 的整数。")
        except ValueError:
            print("错误：输入无效，请输入一个数字。")
        except EOFError: # 处理 Ctrl+D 或类似中断输入的情况
             print("\n输入被中断。退出。")
             return # 直接退出函数

    # 2. 检查源文件是否存在
    #    os.path.abspath 获取绝对路径，使得错误信息更清晰
    script_dir = os.path.dirname(os.path.abspath(__file__)) # 获取脚本所在目录
    source_path = os.path.join(script_dir, source_filename) # 源文件的完整路径

    if not os.path.exists(source_path):
        print(f"错误：源文件 '{source_filename}' 在目录 '{script_dir}' 中未找到。")
        return # 文件不存在，退出函数

    # 3. 准备输出目录
    output_path = os.path.join(script_dir, output_directory) # 输出目录的完整路径
    try:
        # exist_ok=True 表示如果目录已存在，不会抛出错误
        os.makedirs(output_path, exist_ok=True)
        print(f"输出目录 '{output_directory}' 已准备好（如果不存在则已创建）。")
    except OSError as e:
        print(f"错误：无法创建或访问输出目录 '{output_directory}'。原因: {e}")
        return # 无法处理输出目录，退出函数

    print(f"\n准备将 '{source_filename}' 复制 {n} 份到 '{output_directory}' 目录中...")

    # 4. 执行复制操作
    copied_count = 0
    errors_occurred = False
    for i in range(1, n + 1):
        destination_filename = f"{i}.txt"
        # 使用 os.path.join 来构建跨平台兼容的目标路径
        destination_path = os.path.join(output_path, destination_filename)

        try:
            # 使用 shutil.copy2 可以保留更多元数据（如修改时间），如果只需要内容，shutil.copy 也可以
            shutil.copy2(source_path, destination_path)
            # 打印相对路径，更简洁
            print(f"  成功: '{source_filename}' -> '{os.path.join(output_directory, destination_filename)}'")
            copied_count += 1
        except Exception as e:
            print(f"  失败: 无法复制到 '{os.path.join(output_directory, destination_filename)}'。原因: {e}")
            errors_occurred = True
            # 你可以选择在这里停止，或者继续尝试复制其他文件
            # break # 如果希望遇到错误就停止，取消此行注释

    # 5. 显示最终结果
    print("\n--- 复制完成 ---")
    print(f"尝试复制总份数: {n}")
    print(f"成功复制文件数: {copied_count}")
    print(f"文件被复制到子目录: '{output_directory}'")
    if errors_occurred:
        print("复制过程中发生了一些错误。")
    else:
        print("所有文件均已成功复制。")

# --- 主程序入口 ---
if __name__ == "__main__":
    copy_file_multiple_times()
    # 可选：在脚本执行完毕后暂停，以便用户查看输出 (在某些IDE或直接运行时有用)
    # input("\n按 Enter 键退出...")