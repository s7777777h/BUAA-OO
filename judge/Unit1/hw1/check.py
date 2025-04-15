import os
import subprocess
from sympy import sympify, expand, simplify
import re

def process_expr(expr):
    expr = re.sub(r'(?<!\d)([+-]?)0+(\d+)(?!\d)', r'\1\2', expr)
    return expr.replace('^', '**').replace(')(', ')*(')


def generate_answers(data_dir):
    answers = {}
    for f in os.listdir(data_dir):
        if f.endswith('.in'):
            with open(f"{data_dir}/{f}") as file:
                expr = process_expr(file.read().strip())
                answers[f] = str(expand(simplify(sympify(expr))))
    return answers


def test_jar(jar_path, answers):
    jar_name = os.path.basename(jar_path)
    jar_base = os.path.splitext(jar_name)[0]  # 移除.jar扩展名
    print(f"\nTesting JAR: {jar_name}")

    os.makedirs("bug", exist_ok=True)  # 确保bug目录存在
    results = {"correct": 0, "wrong": []}

    for case in answers:
        print(f"  Processing: {case}", end='\r')
        case_base = os.path.splitext(case)[0]  # 移除.in扩展名
        error_file = os.path.join("bug", f"{jar_base}_{case_base}.txt")

        try:
            with open(f"data/{case}") as f:
                input_data = f.read()

            p = subprocess.run(
                ['java', '-jar', jar_path],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=3
            )
            output = process_expr(p.stdout.strip())

            if sympify(answers[case]).equals(sympify(output)):
                results["correct"] += 1
            else:
                # 生成错误报告
                with open(error_file, 'w') as ef:
                    ef.write(f"[Input]\n{input_data}\n\n")
                    ef.write(f"[Expected]\n{answers[case]}\n\n")
                    ef.write(f"[Actual]\n{output}")
                results["wrong"].append(case)
                print(f"  [ERROR] {case} output mismatch")

        except Exception as e:
            # 生成错误报告
            with open(error_file, 'w') as ef:
                ef.write(f"[Input]\n{input_data}\n\n")
                ef.write(f"[Error]\n{str(e)}\n\n")
                ef.write(f"[Output]\n{p.stdout if p else 'No output'}")
            results["wrong"].append(case)
            print(f"  [ERROR] {case} failed: {str(e)[:30]}")

    print(f"  Completed: {len(answers)} cases")
    return results


def main():
    jars = [f for f in os.listdir() if f.endswith('.jar')]
    if not jars:
        print("No JAR files found")
        return

    os.makedirs("data", exist_ok=True)
    os.makedirs("bug", exist_ok=True)  # 创建bug目录
    answers = generate_answers("data")

    report = []
    for jar in jars:
        res = test_jar(jar, answers)
        status = f"Passed {res['correct']}/{len(answers)}"
        report.append(f"{os.path.basename(jar)}: {status}")

    with open("summary.txt", "w") as f:
        f.write("Test Summary:\n" + "\n".join(report))
    print("\nTest completed. See summary.txt")


if __name__ == "__main__":
    main()