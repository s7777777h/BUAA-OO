import os
import datetime
import subprocess
import shutil
import sys

# --- 配置 ---
FOLDERS_TO_ARCHIVE = ["data", "log", "out", "report"]
ARCHIVE_BASENAME = "snapshot"
# --- End 配置 ---

def find_rar_executable():
    """查找系统中的 rar 可执行文件路径"""
    rar_exec = shutil.which('rar') # 跨平台查找 PATH 中的 rar
    if rar_exec:
        print(f"找到 RAR 可执行文件: {rar_exec}")
        return rar_exec
    else:
        # 在 Windows 上尝试常见路径 (如果未在 PATH 中)
        if sys.platform == "win32":
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "WinRAR", "rar.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "WinRAR", "rar.exe")
            ]
            for path in common_paths:
                if os.path.isfile(path):
                    print(f"在常见路径找到 RAR 可执行文件: {path}")
                    return path
        return None

def main():
    print("--- 开始创建快照压缩包 ---")

    # 1. 查找 RAR 可执行文件
    rar_executable = find_rar_executable()
    if not rar_executable:
        print("\n错误：找不到 'rar' 可执行文件。")
        print("请确保已安装 WinRAR (Windows) 或 RAR (Linux/macOS)，")
        print("并且 'rar' 命令已添加到系统的 PATH 环境变量中。")
        sys.exit(1) # 错误退出

    # 2. 检查需要打包的文件夹是否存在
    current_directory = os.getcwd()
    existing_folders = []
    print("\n检查要打包的文件夹:")
    for folder in FOLDERS_TO_ARCHIVE:
        folder_path = os.path.join(current_directory, folder)
        if os.path.isdir(folder_path):
            print(f"  - 找到: {folder}")
            existing_folders.append(folder) # 只添加存在的文件夹名
        else:
            print(f"  - 未找到 (跳过): {folder}")

    if not existing_folders:
        print("\n警告：所有指定要打包的文件夹都不存在，无需创建压缩包。")
        sys.exit(0) # 正常退出，因为无事可做

    # 3. 生成时间戳和压缩文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"{ARCHIVE_BASENAME}_{timestamp}.rar"
    print(f"\n准备创建压缩文件: {archive_filename}")

    # 4. 构建 RAR 命令
    # 命令格式: rar a <archive_name>.rar <folder1> <folder2> ...
    command = [
        rar_executable,
        'a', # 添加到压缩文件
        archive_filename
    ]
    command.extend(existing_folders) # 将所有存在的文件夹添加到命令末尾

    print(f"执行命令: {' '.join(command)}") # 打印将要执行的命令

    # 5. 执行打包命令
    try:
        # 使用 subprocess.run 执行命令
        # check=True: 如果 rar 命令返回非零（错误）状态码，则抛出 CalledProcessError
        # capture_output=True: 捕获 rar 的标准输出和标准错误
        # text=True: 以文本模式处理输出/错误
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print("\n--- RAR 输出 ---")
        print(result.stdout)
        print("---------------")
        print(f"\n成功创建压缩文件: {archive_filename}")
        sys.exit(0) # 成功退出

    except FileNotFoundError:
        # 这个错误理论上不应该发生，因为我们已经检查过 rar_executable
        print(f"\n错误：无法执行找到的 RAR 命令 '{rar_executable}'。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        # rar 命令执行失败（返回非零状态码）
        print("\n错误：RAR 命令执行失败！")
        print(f"返回码: {e.returncode}")
        print("\n--- RAR 标准输出 ---")
        print(e.stdout)
        print("\n--- RAR 标准错误 ---")
        print(e.stderr)
        print("--------------------")
        # 尝试删除可能已部分创建的错误文件
        if os.path.exists(archive_filename):
            try:
                os.remove(archive_filename)
                print(f"(已尝试删除部分创建的压缩文件: {archive_filename})")
            except OSError as del_e:
                 print(f"(尝试删除部分创建的压缩文件失败: {del_e})")
        sys.exit(1)
    except Exception as e:
        # 其他 Python 异常
        print(f"\n发生意外错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()