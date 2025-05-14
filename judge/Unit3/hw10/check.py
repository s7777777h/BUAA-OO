import os
import subprocess
import sys
import time
import glob
import shutil
import filecmp
import signal
import platform
from itertools import zip_longest # <--- 新增导入

# --- 配置 (Configuration) ---
STD_DIR = "std"
TESTJAR_DIR = "testjar"
DATA_DIR = "data"
OUT_DIR = "out"
STDOUT_DIR = "stdout"
LOG_DIR = "log"
TIMEOUT_SECONDS = 10
DATA_GENERATOR_SCRIPT = "data_generator.py"
MAX_DIFF_LINES_TO_LOG = 10 # 最多记录 10 行不同的细节

# --- 全局变量 (Global Variable) ---
std_run_statuses = {} # 存储 std.jar 的运行状态 {input_basename: status}

# --- 辅助函数 (Helper Functions) ---

def create_dir_if_not_exists(dir_path):
    """如果目录不存在则创建。"""
    if not os.path.exists(dir_path):
        print(f"创建目录: {dir_path}")
        os.makedirs(dir_path)

def clear_dir(dir_path):
    """清空目录下的所有文件和子目录。"""
    if not os.path.exists(dir_path): return
    print(f"清空目录: {dir_path}")
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path): os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e: print(f'删除 {file_path} 失败. 原因: {e}')

def run_jar(jar_path, input_path, output_path, timeout):
    """运行 JAR 文件，处理输入输出和超时。"""
    status = 'AC'; stderr_content = b''; start_time = time.time(); process = None
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'wb') as outfile:
            java_command = ['java', '-Xms128m', '-Xmx512m', '-jar', jar_path]
            preexec_fn_toset = None
            if platform.system() != "Windows": preexec_fn_toset = os.setsid
            process = subprocess.Popen(java_command, stdin=infile, stdout=outfile, stderr=subprocess.PIPE, preexec_fn=preexec_fn_toset)
            try:
                _, stderr_content = process.communicate(timeout=timeout)
                if stderr_content:
                    status = 'RE'
                    if process.returncode is not None and process.returncode != 0: stderr_content += f"\n--- Exited with code: {process.returncode} ---".encode()
                elif process.returncode != 0:
                    print(f"    提示: 进程 {os.path.basename(jar_path)} 在 {os.path.basename(input_path)} 上退出码为 {process.returncode} 但 stderr 为空。")
            except subprocess.TimeoutExpired:
                print(f"    超时: {os.path.basename(jar_path)} 在 {os.path.basename(input_path)} 上超时")
                if process and process.pid is not None:
                    print(f"    尝试终止进程 PID/组: {process.pid}")
                    try:
                        if platform.system() != "Windows": os.killpg(os.getpgid(process.pid), signal.SIGKILL); print(f"    已终止进程组 PID {process.pid}.")
                        else: subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True, capture_output=True, timeout=5); print(f"    已使用 taskkill 终止进程树 PID {process.pid}.")
                    except Exception as kill_err:
                        print(f"    终止 PID {process.pid} 失败: {kill_err}. 尝试 process.kill() 回退。")
                        try: process.kill()
                        except Exception: pass
                status = 'TLE'; stderr_content = b"--- PROCESS KILLED DUE TO TIMEOUT ---"
    except FileNotFoundError: print(f"错误: 未找到 'java' 命令。"); status = 'RE'; stderr_content = b"Java command not found."
    except Exception as e: print(f"运行 {jar_path} 时发生意外错误: {e}"); status = 'RE'; stderr_content = str(e).encode()
    if process and process.poll() is None and status == 'RE': # 确保在发生 RE 时也尝试清理进程
        try: process.kill(); process.wait(timeout=0.5)
        except Exception as kill_e: print(f"    意外错误后尝试终止进程时出错: {kill_e}")
    end_time = time.time()
    print(f"    完成: {os.path.basename(jar_path)} 在 {os.path.basename(input_path)} 上耗时 {end_time - start_time:.2f}s - 运行状态: {status}")
    return status, b'', stderr_content

def compare_outputs(std_ans_path, test_out_path):
    """对比两个输出文件，忽略行首尾空白。"""
    try:
        if not os.path.exists(std_ans_path): print(f"    对比错误: 未找到标准答案文件 ({std_ans_path})"); return False
        if not os.path.exists(test_out_path): print(f"    对比错误: 未找到测试输出文件 ({test_out_path})"); return False
        with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f1, \
             open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f2:
            lines1 = [line.strip() for line in f1]; lines2 = [line.strip() for line in f2]
            while lines1 and not lines1[-1]: lines1.pop()
            while lines2 and not lines2[-1]: lines2.pop()
            return lines1 == lines2
    except Exception as e: print(f"    对比文件 {std_ans_path} 和 {test_out_path} 时出错: {e}"); return False

# ==============================================================
#  核心修改：create_log_file 函数增加详细差异对比
# ==============================================================
def create_log_file(log_path, input_path, std_ans_path, test_out_path,
                    std_status, test_status, test_stderr_content, final_status):
    """为失败的测试用例创建日志文件，并在 WA 时追加详细差异。"""
    if final_status == 'AC (Skipped - Std TLE)':
         print(f"    跳过日志创建: {os.path.basename(input_path)} (因 Std TLE 被跳过).")
         return

    print(f"    检测到差异 ({final_status})! 创建日志: {log_path}")
    try:
        with open(log_path, 'w', encoding='utf-8') as logfile:
            logfile.write(f"--- 测试用例失败: {final_status} ---\n")
            logfile.write(f"标准程序状态: {std_status}\n")
            if test_status: logfile.write(f"测试程序状态: {test_status}\n\n")
            else: logfile.write("测试程序状态: 未运行 (因 Std TLE 跳过)\n\n")

            # --- 写入输入数据 ---
            logfile.write(f"--- 输入数据 ({os.path.basename(input_path)}) ---\n")
            input_lines_content = []
            try:
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                    input_lines_content = [line.rstrip('\r\n') for line in f_in]
                    logfile.write('\n'.join(input_lines_content))
            except Exception as e: logfile.write(f"\n!!! 读取输入文件错误: {e} !!!\n")
            logfile.write("\n--- 输入数据结束 ---\n\n")

            # --- 写入标准输出 ---
            logfile.write(f"--- 标准输出 ({os.path.basename(std_ans_path)}) ---\n")
            std_lines_content = []
            if os.path.exists(std_ans_path):
                try:
                    with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f_std:
                        std_lines_content = [line.rstrip('\r\n') for line in f_std]
                        logfile.write('\n'.join(std_lines_content))
                except Exception as e: logfile.write(f"\n!!! 读取标准输出错误: {e} !!!\n")
            else: logfile.write("!!! 未找到或为空的标准输出文件 !!!\n")
            logfile.write("\n--- 标准输出结束 ---\n\n")

            # --- 写入测试程序的 stderr (如果 RE/TLE) ---
            if test_status == 'RE' or test_status == 'TLE':
                 logfile.write("--- 测试程序标准错误 ---\n")
                 logfile.write(test_stderr_content.decode(encoding='utf-8', errors='ignore'))
                 logfile.write("\n--- 测试程序标准错误结束 ---\n\n")

            # --- 写入测试程序的 stdout ---
            logfile.write(f"--- 测试程序输出 ({os.path.basename(test_out_path)}) ---\n")
            test_lines_content = []
            if os.path.exists(test_out_path):
                 try:
                      with open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f_test:
                           test_lines_content = [line.rstrip('\r\n') for line in f_test]
                           logfile.write('\n'.join(test_lines_content))
                 except Exception as e: logfile.write(f"\n!!! 读取测试输出错误: {e} !!!\n")
            else: logfile.write("!!! 未找到或为空的测试输出文件 !!!\n")
            logfile.write("\n--- 测试程序输出结束 ---\n")

            # --- 新增：详细差异对比 (仅在 WA 时进行) ---
            if final_status == 'WA':
                logfile.write(f"\n\n--- 详细差异对比 (前 {MAX_DIFF_LINES_TO_LOG} 处不同) ---\n")
                diff_count = 0
                # 使用 zip_longest 处理不等长文件
                for line_num, (input_line, std_line, test_line) in enumerate(
                    zip_longest(input_lines_content, std_lines_content, test_lines_content, fillvalue="<文件结束>"), start=1):

                    # 比较去除首尾空白后的内容
                    std_line_stripped = std_line.strip() if std_line != "<文件结束>" else "<文件结束>"
                    test_line_stripped = test_line.strip() if test_line != "<文件结束>" else "<文件结束>"

                    if std_line_stripped != test_line_stripped:
                        diff_count += 1
                        logfile.write(f"\n[差异 #{diff_count} 在 第 {line_num} 行]\n")
                        if input_line != "<文件结束>":
                            logfile.write(f"  对应输入: {input_line}\n")
                        else:
                            logfile.write(f"  对应输入: <输入在此行前已结束>\n")
                        logfile.write(f"  标准输出: {std_line}\n") # 显示原始行以便观察空白差异
                        logfile.write(f"  测试输出: {test_line}\n")

                        if diff_count >= MAX_DIFF_LINES_TO_LOG:
                            logfile.write("\n--- (已达到最大差异记录数) ---\n")
                            break
                if diff_count == 0:
                     logfile.write("\n--- 未检测到逐行差异 (可能由文件末尾空行或其他 compare_outputs 未捕获问题导致) ---\n")
            # --- 详细差异对比结束 ---

    except Exception as e:
        print(f"    创建日志文件 {log_path} 时出错: {e}")


# --- 主脚本逻辑 (Main Script Logic) ---

if __name__ == "__main__":
    # 1. 设置与可选的数据生成 (Setup & Optional Data Generation)
    print("--- 设置阶段 ---")
    # ... (创建目录) ...
    create_dir_if_not_exists(DATA_DIR); create_dir_if_not_exists(OUT_DIR); create_dir_if_not_exists(STDOUT_DIR); create_dir_if_not_exists(LOG_DIR); create_dir_if_not_exists(STD_DIR); create_dir_if_not_exists(TESTJAR_DIR)

    while True:
        gen_data = input("是否使用 data_generator.py 生成新数据? (y/n): ").lower()
        if gen_data in ['y', 'n']: break
        print("无效输入。请输入 'y' 或 'n'。")

    if gen_data == 'y':
        if not os.path.exists(DATA_GENERATOR_SCRIPT): print(f"错误: 未找到数据生成器脚本 '{DATA_GENERATOR_SCRIPT}'."); sys.exit(1)
        print("清空所有相关目录...")
        clear_dir(DATA_DIR); clear_dir(OUT_DIR); clear_dir(STDOUT_DIR); clear_dir(LOG_DIR)
        std_run_statuses.clear()
        try:
            print(f"运行数据生成器: {DATA_GENERATOR_SCRIPT}...")
            subprocess.run([sys.executable, DATA_GENERATOR_SCRIPT], check=True) # 确保使用当前 Python 环境
            print("数据生成完成。")
        except Exception as e: print(f"数据生成过程中发生意外错误: {e}"); sys.exit(1)


    # 查找标准 JAR
    std_jars = glob.glob(os.path.join(STD_DIR, "*.jar"))
    if not std_jars: print(f"错误: 在 '{STD_DIR}' 中未找到标准 JAR 文件。"); sys.exit(1)
    if len(std_jars) > 1: print(f"错误: 在 '{STD_DIR}' 中找到多个 JAR 文件。请确保只有一个标准 JAR。"); sys.exit(1)
    std_jar_path = std_jars[0]; print(f"找到标准 JAR: {std_jar_path}")

    # 查找测试 JAR
    test_jar_paths = glob.glob(os.path.join(TESTJAR_DIR, "*.jar"))
    if not test_jar_paths: print(f"警告: 在 '{TESTJAR_DIR}' 中未找到测试 JAR 文件。")

    # 查找输入数据文件
    input_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
    if not input_files: print(f"错误: 在 '{DATA_DIR}' 中未找到输入数据文件 (.txt)。"); sys.exit(1)
    print(f"找到 {len(input_files)} 个输入数据文件。"); print(f"找到 {len(test_jar_paths)} 个测试 JAR 文件。")
    print("--- 设置阶段结束 ---")

    # 2. 生成标准输出并记录状态 (Generate Standard Outputs & Record Statuses)
    print("\n--- 生成标准输出并记录状态 ---")
    std_run_statuses.clear() # 确保字典是空的
    for input_path in input_files:
        input_basename = os.path.basename(input_path)
        std_ans_basename = os.path.splitext(input_basename)[0] + ".ans"
        std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)
        print(f"  运行标准 JAR 处理 {input_basename}...")
        std_status, _, std_stderr = run_jar(std_jar_path, input_path, std_ans_path, timeout=TIMEOUT_SECONDS * 3) # 给标程更长时间
        std_run_statuses[input_basename] = std_status
        if std_status != 'AC' and not os.path.exists(std_ans_path):
             try: open(std_ans_path, 'w').close(); print(f"    因状态为 {std_status} 创建了空的标准输出文件")
             except Exception as e_create: print(f"    警告: 创建空输出文件 {std_ans_path} 失败: {e_create}")
        if std_status == 'RE': print(f"    警告: 标准 JAR 在 {input_basename} 上报告了 RE。")
        elif std_status == 'TLE': print(f"    警告: 标准 JAR 在 {input_basename} 上报告了 TLE。")
    print("--- 标准输出生成与状态记录完成 ---")

    # 3. 运行对比测试 (Run Comparison Testing)
    print("\n--- 对比测试阶段 ---")
    overall_results = {}
    if not test_jar_paths: print("未找到测试 JAR，退出对比测试。"); sys.exit(0)

    for test_jar_path in test_jar_paths:
        test_jar_name = os.path.basename(test_jar_path)
        print(f"\n--- 测试 JAR: {test_jar_name} ---")
        jar_results = {}; overall_results[test_jar_name] = jar_results
        for input_path in input_files:
            input_basename = os.path.basename(input_path); input_name_no_ext = os.path.splitext(input_basename)[0]
            print(f"  测试输入: {input_basename}")
            test_out_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.txt"; test_out_path = os.path.join(OUT_DIR, test_out_filename)
            log_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.log"; log_path = os.path.join(LOG_DIR, log_filename)
            std_ans_basename = input_name_no_ext + ".ans"; std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)
            std_status = std_run_statuses.get(input_basename, 'Skipped (No Std Status)')

            if std_status == 'TLE':
                print(f"    跳过输入 {input_basename} 因为 std.jar 超时。")
                final_status = 'AC (Skipped - Std TLE)'; jar_results[input_basename] = final_status; continue
            elif std_status == 'Skipped (No Std Status)':
                 print(f"    跳过对比: 未找到 '{input_basename}' 的标准状态。"); jar_results[input_basename] = std_status; continue

            test_status, _, test_stderr_content = run_jar(test_jar_path, input_path, test_out_path, TIMEOUT_SECONDS)

            final_status = 'Unknown'; comparison_needed = False
            if std_status == test_status:
                if std_status == 'AC': comparison_needed = True
                else: final_status = 'AC'; print(f"    行为一致 ({std_status})。接受。")
            else:
                if test_status == 'AC': final_status = 'WA'; print(f"    状态不匹配: 测试 JAR 为 AC, 但标准 JAR 为 {std_status}。")
                else: final_status = test_status; print(f"    状态不匹配: 测试 JAR 为 {test_status}, 标准 JAR 为 {std_status}。")

            if comparison_needed:
                 if compare_outputs(std_ans_path, test_out_path): final_status = 'AC'
                 else: final_status = 'WA'; print(f"    输出与标准答案不同。")

            jar_results[input_basename] = final_status
            if final_status != 'AC' and final_status != 'AC (Skipped - Std TLE)':
                 create_log_file(log_path, input_path, std_ans_path, test_out_path, std_status, test_status, test_stderr_content, final_status)

    # 4. 生成报告 (Generate Reports)
    print("\n--- 生成报告 ---")
    for test_jar_name, results in overall_results.items():
        report_filename = f"{os.path.splitext(test_jar_name)[0]}_report.txt"
        report_path = os.path.join(os.path.dirname(sys.argv[0]) or '.', report_filename)
        print(f"  生成报告: {report_path}")
        total_cases = len(results); counts = {'AC': 0, 'WA': 0, 'TLE': 0, 'RE': 0, 'AC (Skipped - Std TLE)': 0}; other_skipped_count = 0
        failed_or_skipped_cases = []
        for input_name, status in results.items():
            if status in counts: counts[status] = counts.get(status, 0) + 1
            else: other_skipped_count += 1; status = status # 保留原始状态字符串
            if status != 'AC': failed_or_skipped_cases.append((input_name, status))
        failed_or_skipped_cases.sort()
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"--- {test_jar_name} 测试报告 ---\n\n"); f.write(f"总测试用例数: {total_cases}\n"); f.write("结果汇总:\n")
                plain_ac_count=counts.get('AC', 0); skipped_tle_count=counts.get('AC (Skipped - Std TLE)', 0); wa_count=counts.get('WA', 0); tle_count=counts.get('TLE', 0); re_count=counts.get('RE', 0)
                if plain_ac_count > 0: f.write(f"  - AC (通过): {plain_ac_count}\n")
                if wa_count > 0: f.write(f"  - WA (答案错误): {wa_count}\n")
                if tle_count > 0: f.write(f"  - TLE (超时): {tle_count}\n")
                if re_count > 0: f.write(f"  - RE (运行时错误): {re_count}\n")
                if skipped_tle_count > 0: f.write(f"  - 跳过 (因标程TLE): {skipped_tle_count}\n")
                if other_skipped_count > 0: f.write(f"  - 跳过 (其他原因): {other_skipped_count}\n")
                if failed_or_skipped_cases:
                    f.write("\n失败/跳过用例详情:\n");
                    for name, status in failed_or_skipped_cases: f.write(f"  - {name}: {status}\n")
                elif skipped_tle_count == 0 and other_skipped_count == 0: f.write("\n所有测试用例通过!\n")
                else: f.write("\n所有运行的测试用例通过 (部分用例因标程TLE跳过)。\n")
        except Exception as e: print(f"  写入报告 {report_path} 时出错: {e}")
    print("\n--- 对比测试完成 ---")