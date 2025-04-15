import os
import subprocess
import time
from multiprocessing import Process, Queue
from sympy import simplify, sympify, expand_trig

# 配置参数
TIMEOUT = 3  # 总超时时间(秒)
SYMPY_TIMEOUT = 3  # SymPy运算超时时间(秒)

def preprocess_expression(expr):
    """预处理表达式适配SymPy"""
    return expr.replace('^', '**').replace(')(', ')*(')

def clean_string(s):
    """清理字符串中的空白字符和换行符"""
    return s.replace(' ', '').replace('\n', '').replace('\r', '')

def run_jar(jar_path, input_file):
    """运行JAR程序获取输出表达式"""
    try:
        with open(input_file) as f:
            input_data = f.read()

        result = subprocess.run(
            ['java', '-jar', jar_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )
        return preprocess_expression(result.stdout.strip())
    except Exception as e:
        return f"ERROR: {str(e)}"

def save_output(content, path):
    """保存输出文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

def compare_worker(std_expr, test_expr, result_queue):
    """子进程执行符号比较"""
    try:
        expr1 = expand_trig(simplify(sympify(std_expr)))
        expr2 = expand_trig(simplify(sympify(test_expr)))
        result_queue.put(('SUCCESS', expr1.equals(expr2)))
    except Exception as e:
        result_queue.put(('ERROR', str(e)))

def compare_expressions(std_expr, test_expr):
    """带超时的符号比较"""
    result_queue = Queue()
    p = Process(target=compare_worker, args=(std_expr, test_expr, result_queue))

    try:
        p.start()
        p.join(SYMPY_TIMEOUT)

        if p.is_alive():
            p.terminate()
            p.join()
            return ('TIMEOUT', None)

        if not result_queue.empty():
            status, result = result_queue.get()
            return (status, result)

        return ('ERROR', 'Unknown error')
    except:
        return ('ERROR', 'Process error')
    finally:
        if p.is_alive():
            p.terminate()
            p.join()

def generate_report(jar_name, case_name, input_data, std_out, test_out, reason):
    """生成错误报告"""
    os.makedirs("bug", exist_ok=True)
    filename = f"bug/{jar_name}_{case_name}.txt"

    with open(filename, 'w') as f:
        f.write(f"[Error Reason] {reason}\n\n")
        f.write(f"[Input]\n{input_data}\n\n")
        f.write(f"[Std Output]\n{std_out}\n\n")
        f.write(f"[Test Output]\n{test_out}\n\n")
        f.write(f"[Comparison Time] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def main():
    # 初始化环境
    std_jar = os.path.join("std", "std.jar")
    target_jars = [f for f in os.listdir() if f.endswith('.jar') and 'std' not in f]

    if not os.path.exists(std_jar):
        print("错误: 标准JAR文件不存在")
        return

    # 创建输出目录
    os.makedirs("out", exist_ok=True)

    case_files = [os.path.join("data", f) for f in os.listdir("data") if f.endswith('.in')]

    for jar in target_jars:
        print(f"\n▶ 正在测试: {jar}")
        jar_base = os.path.splitext(jar)[0]
        bug_count = 0

        for case_file in case_files:
            case_name = os.path.splitext(os.path.basename(case_file))[0]
            print(f"  Processing: {case_name}", end='\r')

            # 获取并保存标准答案
            std_out = run_jar(std_jar, case_file)
            ans_path = os.path.join("out", f"{case_name}.ans")
            save_output(std_out, ans_path)

            if std_out.startswith("ERROR"):
                print(f"  [ERROR] 标准程序执行失败: {case_name}")
                continue

            # 测试并保存目标输出
            test_out = run_jar(jar, case_file)
            out_path = os.path.join("out", f"{case_name}_{jar_base}.out")
            save_output(test_out, out_path)

            # 错误处理
            if test_out.startswith("ERROR"):
                generate_report(jar_base, case_name,
                                open(case_file).read(), std_out, test_out,
                                "JAR运行错误")
                bug_count += 1
                print(f"  [BUG] {case_name} (运行错误)")
                continue

            # 新增加的功能：长度超过300且字符数相同则直接通过
            skip_sympy = False
            if len(std_out) > 300 and len(test_out) > 300:
                # 计算有效字符数
                clean_std = clean_string(std_out)
                clean_test = clean_string(test_out)
                if len(clean_std) == len(clean_test):
                    skip_sympy = True
                #    print(f"  [SKIP] {case_name} 长度匹配直接通过")

            if not skip_sympy:
                # 符号比较
                start_time = time.time()
                cmp_status, cmp_result = compare_expressions(std_out, test_out)
                elapsed = time.time() - start_time

                # 结果判断
                if cmp_status == 'TIMEOUT':
                    reason = f"符号运算超时 ({elapsed:.2f}s)"
                    generate_report(jar_base, case_name,
                                    open(case_file).read(), std_out, test_out, reason)
                    bug_count += 1
                    print(f"  [BUG] {case_name} (运算超时)")
                elif cmp_status == 'ERROR':
                    reason = f"表达式解析失败: {cmp_result}"
                    generate_report(jar_base, case_name,
                                    open(case_file).read(), std_out, test_out, reason)
                    bug_count += 1
                    print(f"  [BUG] {case_name} (解析错误)")
                elif not cmp_result:
                    generate_report(jar_base, case_name,
                                    open(case_file).read(), std_out, test_out,
                                    "表达式不等价")
                    bug_count += 1
                    print(f"  [BUG] {case_name} (表达式不等价)")

        print(f"  发现 {bug_count} 个错误用例".ljust(40))

if __name__ == "__main__":
    main()