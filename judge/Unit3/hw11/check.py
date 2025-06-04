import os
import subprocess
import sys
import time
import glob
import shutil
import filecmp
import signal
import platform
from itertools import zip_longest # Used for comparing files line by line

# --- 配置 (Configuration) ---
STD_DIR = "std"
TESTJAR_DIR = "testjar"
DATA_DIR = "data"
OUT_DIR = "out"
STDOUT_DIR = "stdout"
LOG_DIR = "log"
TIMEOUT_SECONDS = 10  # Timeout for the test JAR
DATA_GENERATOR_SCRIPT = "data_generator.py"
MAX_DIFF_LINES_TO_LOG = 10 # Max number of differing lines to detail in the log
STD_TIMEOUT_FACTOR = 3 # Allow standard JAR more time (TIMEOUT_SECONDS * factor)

# --- 全局变量 (Global Variable) ---
std_run_statuses = {} # Stores the run status of std.jar {input_basename: status}

# --- 辅助函数 (Helper Functions) ---

def create_dir_if_not_exists(dir_path):
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(dir_path):
        print(f"创建目录: {dir_path}")
        os.makedirs(dir_path)

def clear_dir(dir_path):
    """Removes all files and subdirectories within a directory."""
    if not os.path.exists(dir_path): return
    print(f"清空目录: {dir_path}")
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'删除 {file_path} 失败. 原因: {e}')

def run_jar(jar_path, input_path, output_path, timeout):
    """
    Runs a JAR file, handling input redirection, output capture, and timeout.

    Args:
        jar_path (str): Path to the JAR file.
        input_path (str): Path to the input data file.
        output_path (str): Path to write the standard output to.
        timeout (int): Timeout in seconds.

    Returns:
        tuple: (status_string, stdout_content_bytes, stderr_content_bytes)
               status_string can be 'AC', 'TLE', 'RE'.
               stdout_content is usually empty as it's redirected to file.
               stderr_content contains error messages if any.
    """
    status = 'AC'  # Assume Accepted until proven otherwise
    stdout_content = b'' # Stdout is redirected, so usually empty here
    stderr_content = b''
    start_time = time.time()
    process = None
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'wb') as outfile: # Open output in binary write mode

            java_command = ['java', '-Xms128m', '-Xmx512m', '-jar', jar_path]
            # Use os.setsid for process group killing on non-Windows for better cleanup
            preexec_fn_toset = None
            if platform.system() != "Windows":
                preexec_fn_toset = os.setsid

            process = subprocess.Popen(
                java_command,
                stdin=infile,
                stdout=outfile, # Redirect stdout directly to the file
                stderr=subprocess.PIPE,
                preexec_fn=preexec_fn_toset
            )

            try:
                # Wait for process completion or timeout, capture stderr
                # stdout is being written directly to outfile, so stdout_content will be None
                _, stderr_content = process.communicate(timeout=timeout)

                # Check return code and stderr after communication
                if process.returncode != 0:
                    status = 'RE' # Non-zero exit code usually indicates Runtime Error
                    stderr_suffix = f"\n--- Exited with code: {process.returncode} ---".encode()
                    stderr_content = (stderr_content or b'') + stderr_suffix # Append exit code info
                    print(f"    Non-zero exit code {process.returncode} for {os.path.basename(jar_path)} on {os.path.basename(input_path)}.")
                elif stderr_content:
                    # Sometimes programs print errors but exit with 0, treat as RE
                    status = 'RE'
                    print(f"    Stderr content detected for {os.path.basename(jar_path)} on {os.path.basename(input_path)} (exit code 0).")


            except subprocess.TimeoutExpired:
                print(f"    Timeout: {os.path.basename(jar_path)} on {os.path.basename(input_path)} exceeded {timeout}s")
                status = 'TLE'
                stderr_content = b"--- PROCESS KILLED DUE TO TIMEOUT ---"
                if process and process.pid is not None:
                    print(f"    Attempting to terminate process PID/group: {process.pid}")
                    try:
                        if platform.system() != "Windows":
                            # Kill the entire process group on Unix-like systems
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            print(f"    Terminated process group PID {process.pid}.")
                        else:
                            # Use taskkill on Windows to terminate the process and its children
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True, capture_output=True, timeout=5)
                            print(f"    Terminated process tree PID {process.pid} using taskkill.")
                    except Exception as kill_err:
                        print(f"    Failed to terminate PID {process.pid} forcefully: {kill_err}. Attempting process.kill() fallback.")
                        try:
                            process.kill() # Fallback kill
                        except Exception:
                            pass # Ignore errors during fallback kill

            # Ensure process is cleaned up if communicate didn't handle it (e.g., early error)
            finally:
                 if process and process.poll() is None:
                     print(f"    Process {process.pid} still running after communicate/timeout. Attempting final kill.")
                     try:
                         process.kill()
                         process.wait(timeout=1) # Wait briefly for cleanup
                     except Exception as final_kill_e:
                         print(f"    Error during final process kill: {final_kill_e}")


    except FileNotFoundError:
        print(f"Error: 'java' command not found. Make sure Java is installed and in PATH.")
        status = 'RE'
        stderr_content = b"Java command not found."
    except Exception as e:
        print(f"Unexpected error running {jar_path}: {e}")
        status = 'RE'
        stderr_content = str(e).encode(errors='ignore') # Encode exception message

    end_time = time.time()
    print(f"    Finished: {os.path.basename(jar_path)} on {os.path.basename(input_path)} in {end_time - start_time:.2f}s - Status: {status}")
    # Return empty stdout as it's redirected
    return status, b'', stderr_content

def compare_outputs(std_ans_path, test_out_path):
    """Compares two output files, ignoring leading/trailing whitespace on each line."""
    try:
        if not os.path.exists(std_ans_path):
            print(f"    Comparison Error: Standard answer file not found ({std_ans_path})")
            return False
        if not os.path.exists(test_out_path):
            print(f"    Comparison Error: Test output file not found ({test_out_path})")
            return False

        # Read lines, strip whitespace, handle potential encoding errors
        with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f1, \
             open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f2:
            lines1 = [line.strip() for line in f1]
            lines2 = [line.strip() for line in f2]

            # Remove trailing empty lines which might cause false negatives
            while lines1 and not lines1[-1]: lines1.pop()
            while lines2 and not lines2[-1]: lines2.pop()

            return lines1 == lines2

    except Exception as e:
        print(f"    Error comparing files {os.path.basename(std_ans_path)} and {os.path.basename(test_out_path)}: {e}")
        return False

# ==============================================================
#  NEW HELPER FUNCTION TO MAP OUTPUT LINES TO INPUT COMMANDS
# ==============================================================
def map_output_to_input_command(input_lines):
    """
    Parses input lines to map expected output line indices to the
    starting line index of the corresponding input command. Handles 'ln'.

    Args:
        input_lines (list): A list of strings, each representing a line from the input file.

    Returns:
        list: A list where list[i] is the 0-based starting line index in
              input_lines for the command that produces the i-th output line.
    """
    output_to_input_command_start_line = []
    input_line_index = 0
    while input_line_index < len(input_lines):
        if not input_lines[input_line_index].strip(): # Skip empty lines if any
             input_line_index += 1
             continue

        command_line = input_lines[input_line_index].strip()
        command_start_index = input_line_index # Record the start line of this command

        # --- Handle 'ln' command ---
        if command_line.startswith("ln "):
            n = 0
            try:
                parts = command_line.split()
                if len(parts) == 2:
                    n = int(parts[1])
                    if n < 0: # Handle invalid n
                         print(f"Warning: Invalid N={n} in 'ln' command at input line {command_start_index + 1}. Treating as single command.", file=sys.stderr)
                         n = 0 # Treat as single line command
                else: # Malformed ln command
                    print(f"Warning: Malformed 'ln' command '{command_line}' at input line {command_start_index + 1}. Treating as single command.", file=sys.stderr)
                    n = 0 # Treat as single line command
            except (ValueError, IndexError): # Handle potential errors parsing 'ln N'
                print(f"Warning: Error parsing 'ln' command '{command_line}' at input line {command_start_index + 1}. Treating as single command.", file=sys.stderr)
                n = 0 # Treat as single line command

            if n > 0:
                 # Expected lines for ln N: 1 (ln N) + 3 (ids, names, ages) + (N-1) (matrix rows) = N + 3
                 block_size = n + 3
                 # Check if the full block exists in the input
                 if input_line_index + block_size <= len(input_lines):
                      # This ln block generates 1 output line ('Ok')
                      output_to_input_command_start_line.append(command_start_index)
                      input_line_index += block_size # Move index past the entire block
                 else:
                      # Incomplete ln block in input
                      print(f"Warning: Incomplete 'ln' block detected starting at input line {command_start_index + 1}. Expected {block_size} lines, found {len(input_lines) - input_line_index}.", file=sys.stderr)
                      # Still associate one output with the start of the command
                      output_to_input_command_start_line.append(command_start_index)
                      input_line_index += 1 # Move to next line to avoid infinite loop
            else: # n=0 or parsing error, treat 'ln' as a single line command
                 output_to_input_command_start_line.append(command_start_index)
                 input_line_index += 1

        # --- Handle other commands (assume 1 input -> 1 output) ---
        else:
            output_to_input_command_start_line.append(command_start_index)
            input_line_index += 1

    return output_to_input_command_start_line


# ==============================================================
#  日志文件创建函数 (Log File Creation Function) - MODIFIED
# ==============================================================
def create_log_file(log_path, input_path, std_ans_path, test_out_path,
                    std_status, test_status, test_stderr_content, final_status):
    """
    Creates a log file for a failed test case.
    If the status is WA, it includes a detailed line-by-line comparison
    showing the first few differences and the corresponding input command start line.
    Handles multi-line commands like 'ln'.
    """
    if final_status == 'AC (Skipped - Std TLE)':
         print(f"    Skipping log creation for {os.path.basename(input_path)} (Skipped due to Std TLE).")
         return

    print(f"    Difference detected ({final_status})! Creating log: {log_path}")
    try:
        # --- Read all file contents first ---
        input_lines_content = []
        std_lines_content = []
        test_lines_content = []
        try:
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                input_lines_content = [line.rstrip('\r\n') for line in f_in]
        except Exception as e:
            print(f"    Error reading input file {input_path} for log: {e}")
            input_lines_content = [f"!!! Error reading input file: {e} !!!"]

        if os.path.exists(std_ans_path):
            try:
                with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f_std:
                    std_lines_content = [line.rstrip('\r\n') for line in f_std]
            except Exception as e:
                print(f"    Error reading std output file {std_ans_path} for log: {e}")
                std_lines_content = [f"!!! Error reading standard output file: {e} !!!"]
        else:
             std_lines_content = ["!!! Standard output file not found or empty !!!"]

        if os.path.exists(test_out_path):
             try:
                  with open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f_test:
                       test_lines_content = [line.rstrip('\r\n') for line in f_test]
             except Exception as e:
                  print(f"    Error reading test output file {test_out_path} for log: {e}")
                  test_lines_content = [f"!!! Error reading test output file: {e} !!!"]
        # Handle case where test wasn't run (e.g., skipped) or output file wasn't created
        elif test_status is not None and test_status != 'AC':
             test_lines_content = [f"!!! Test output file not found or empty (Test Status: {test_status}) !!!"]
        else:
             test_lines_content = ["!!! Test output file not found or empty !!!"]


        # --- Write log file ---
        with open(log_path, 'w', encoding='utf-8') as logfile:
            logfile.write(f"--- Test Case Failed: {final_status} ---\n")
            logfile.write(f"Input File: {os.path.basename(input_path)}\n")
            logfile.write(f"Standard Program Status: {std_status}\n")
            if test_status: logfile.write(f"Test Program Status: {test_status}\n\n")
            else: logfile.write("Test Program Status: Not Run (Skipped due to Std TLE)\n\n")

            # Write Input Data
            logfile.write(f"--- Input Data ---\n")
            logfile.write('\n'.join(input_lines_content))
            logfile.write("\n--- End of Input Data ---\n\n")

            # Write Standard Output
            logfile.write(f"--- Standard Output ---\n")
            logfile.write('\n'.join(std_lines_content))
            logfile.write("\n--- End of Standard Output ---\n\n")

            # Write Test Program's Standard Error (if RE/TLE)
            if test_status == 'RE' or test_status == 'TLE':
                 logfile.write("--- Test Program Standard Error ---\n")
                 logfile.write(test_stderr_content.decode(encoding='utf-8', errors='replace'))
                 logfile.write("\n--- End of Test Program Standard Error ---\n\n")

            # Write Test Program's Standard Output
            logfile.write(f"--- Test Program Output ---\n")
            logfile.write('\n'.join(test_lines_content))
            logfile.write("\n--- End of Test Program Output ---\n")

            # --- Detailed Difference Comparison (Only for WA) ---
            if final_status == 'WA':
                logfile.write(f"\n\n--- Detailed Differences (First {MAX_DIFF_LINES_TO_LOG} Mismatches) ---\n")

                # Generate the mapping from output line index to input command start line index
                # Do this *after* reading input_lines_content
                output_to_input_map = map_output_to_input_command(input_lines_content)

                diff_count = 0
                # Iterate over OUTPUT lines using zip_longest
                for line_num, (std_line, test_line) in enumerate(
                    zip_longest(std_lines_content, test_lines_content, fillvalue="<EOF>"), start=1):

                    std_line_stripped = std_line.strip() if std_line != "<EOF>" else "<EOF>"
                    test_line_stripped = test_line.strip() if test_line != "<EOF>" else "<EOF>"

                    if std_line_stripped != test_line_stripped:
                        diff_count += 1
                        logfile.write(f"\n[Mismatch #{diff_count} at Output Line {line_num}]\n")

                        # Find the corresponding input command using the map
                        output_index = line_num - 1 # 0-based index for the map
                        if output_index < len(output_to_input_map):
                            input_command_start_index = output_to_input_map[output_index]
                            # Ensure the index is valid before accessing input_lines_content
                            if 0 <= input_command_start_index < len(input_lines_content):
                                command_line_text = input_lines_content[input_command_start_index]
                                logfile.write(f"  Triggering Input Command (Starts at Line {input_command_start_index + 1}): {command_line_text}\n")
                                # Add a note for 'ln' commands
                                if command_line_text.strip().startswith("ln "):
                                    logfile.write(f"    (Note: This is a multi-line 'ln' command block)\n")
                            else:
                                logfile.write(f"  Triggering Input Command: <Error: Calculated input index {input_command_start_index} out of bounds>\n")
                        else:
                            # This case means the test output has more lines than expected based on input parsing
                            logfile.write(f"  Triggering Input Command: <Output line {line_num} exceeds expected output count based on input parsing>\n")

                        # Log the differing output lines (show original for whitespace context)
                        logfile.write(f"  Standard Output Line {line_num}: {std_line}\n")
                        logfile.write(f"  Test Output Line {line_num}    : {test_line}\n")

                        if diff_count >= MAX_DIFF_LINES_TO_LOG:
                            logfile.write("\n--- (Reached max difference lines to log) ---\n")
                            break # Stop after logging max differences

                if diff_count == 0 and not compare_outputs(std_ans_path, test_out_path):
                     logfile.write("\n--- No line-by-line diff found by zip_longest, but compare_outputs reported WA (check trailing lines/whitespace?) ---\n")
                elif diff_count == 0 and final_status == 'WA': # Ensure this only prints if WA was the status
                     logfile.write("\n--- No line-by-line differences found (unexpected for WA status) ---\n")

            # --- End of Detailed Difference Comparison ---

    except Exception as e:
        print(f"    Error creating log file {log_path}: {e}")
        # Optionally re-raise or log more details
        import traceback
        traceback.print_exc()


# --- 主脚本逻辑 (Main Script Logic) ---

if __name__ == "__main__":
    start_overall_time = time.time()
    print("=== Automated Testing Script Start ===")

    # 1. Setup: Create directories
    print("\n--- Phase 1: Setup ---")
    create_dir_if_not_exists(DATA_DIR)
    create_dir_if_not_exists(OUT_DIR)
    create_dir_if_not_exists(STDOUT_DIR)
    create_dir_if_not_exists(LOG_DIR)
    create_dir_if_not_exists(STD_DIR)
    create_dir_if_not_exists(TESTJAR_DIR)
    print("Required directories ensured.")

    # 2. Optional Data Generation
    while True:
        gen_data = input("是否使用 data_generator.py 生成新数据? (y/n): ").lower()
        if gen_data in ['y', 'n']:
            break
        print("无效输入。请输入 'y' 或 'n'。")

    if gen_data == 'y':
        if not os.path.exists(DATA_GENERATOR_SCRIPT):
            print(f"错误: 未找到数据生成器脚本 '{DATA_GENERATOR_SCRIPT}'.")
            sys.exit(1)
        print("清空相关目录...")
        clear_dir(DATA_DIR)
        clear_dir(OUT_DIR)
        clear_dir(STDOUT_DIR)
        clear_dir(LOG_DIR)
        std_run_statuses.clear() # Clear previous statuses if regenerating
        try:
            print(f"运行数据生成器: {DATA_GENERATOR_SCRIPT}...")
            # Ensure using the same python interpreter that runs this script
            # Use text=True for clearer output/error handling if generator prints text
            subprocess.run([sys.executable, DATA_GENERATOR_SCRIPT], check=True, text=True, encoding='utf-8')
            print("数据生成完成。")
        except subprocess.CalledProcessError as e:
             print(f"数据生成过程中发生错误: 进程退出码 {e.returncode}")
             # Optionally print stderr: print(e.stderr)
             sys.exit(1)
        except Exception as e:
            print(f"数据生成过程中发生意外错误: {e}")
            sys.exit(1)

    # 3. Locate JARs and Input Files
    print("\n--- Phase 2: Locating Files ---")
    # Standard JAR
    std_jars = glob.glob(os.path.join(STD_DIR, "*.jar"))
    if not std_jars:
        print(f"错误: 在 '{STD_DIR}' 中未找到标准 JAR 文件。")
        sys.exit(1)
    if len(std_jars) > 1:
        print(f"错误: 在 '{STD_DIR}' 中找到多个 JAR 文件。请确保只有一个标准 JAR。")
        sys.exit(1)
    std_jar_path = std_jars[0]
    print(f"使用标准 JAR: {os.path.basename(std_jar_path)}")

    # Test JAR(s)
    test_jar_paths = glob.glob(os.path.join(TESTJAR_DIR, "*.jar"))
    if not test_jar_paths:
        print(f"警告: 在 '{TESTJAR_DIR}' 中未找到测试 JAR 文件。对比测试阶段将被跳过。")
        # Allow script to continue to potentially just run the standard JAR
    else:
        print(f"找到 {len(test_jar_paths)} 个测试 JAR: {[os.path.basename(p) for p in test_jar_paths]}")

    # Input Files
    input_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
    if not input_files:
        print(f"错误: 在 '{DATA_DIR}' 中未找到输入数据文件 (.txt)。")
        # If data wasn't generated, this is expected. Exit gracefully.
        if gen_data == 'n':
             print("请先生成数据或将数据放入 'data' 目录。")
             sys.exit(0)
        else:
             sys.exit(1) # Exit if data generation was requested but failed silently
    print(f"找到 {len(input_files)} 个输入数据文件。")

    # 4. Generate Standard Outputs
    print("\n--- Phase 3: Generating Standard Outputs ---")
    std_run_statuses.clear() # Ensure fresh status dictionary
    for input_path in input_files:
        input_basename = os.path.basename(input_path)
        # Construct standard output filename (e.g., testcase_1.ans)
        std_ans_basename = os.path.splitext(input_basename)[0] + ".ans"
        std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)

        print(f"  处理 {input_basename} 使用标准 JAR...")
        # Give standard JAR more time
        std_status, _, std_stderr = run_jar(std_jar_path, input_path, std_ans_path, timeout=(TIMEOUT_SECONDS * STD_TIMEOUT_FACTOR))
        std_run_statuses[input_basename] = std_status # Store the status

        # Create empty output file if run failed, for consistency
        if std_status != 'AC' and not os.path.exists(std_ans_path):
             try:
                 with open(std_ans_path, 'w') as f_empty: pass # Create empty file
                 print(f"    为 {input_basename} 创建了空的标准输出文件，因为状态为 {std_status}。")
             except Exception as e_create:
                 print(f"    警告: 创建空输出文件 {std_ans_path} 失败: {e_create}")

        if std_status == 'RE':
            print(f"    警告: 标准 JAR 在 {input_basename} 上报告了 RE。")
            # Optionally log std_stderr here if needed
        elif std_status == 'TLE':
            print(f"    警告: 标准 JAR 在 {input_basename} 上报告了 TLE。")

    print("标准输出生成完成。")

    # 5. Run Comparison Testing
    print("\n--- Phase 4: Comparison Testing ---")
    overall_results = {} # {jar_name: {input_name: status}}

    if not test_jar_paths:
        print("未找到测试 JAR。跳过对比测试。")
    else:
        for test_jar_path in test_jar_paths:
            test_jar_name = os.path.basename(test_jar_path)
            print(f"\n--- 测试 JAR: {test_jar_name} ---")
            jar_results = {}
            overall_results[test_jar_name] = jar_results

            for input_path in input_files:
                input_basename = os.path.basename(input_path)
                input_name_no_ext = os.path.splitext(input_basename)[0]
                print(f"  测试输入: {input_basename}")

                # Define output and log paths for this test run
                test_out_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.txt"
                test_out_path = os.path.join(OUT_DIR, test_out_filename)
                log_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.log"
                log_path = os.path.join(LOG_DIR, log_filename)

                # Standard output path
                std_ans_basename = input_name_no_ext + ".ans"
                std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)

                # Get the status of the standard run for this input
                std_status = std_run_statuses.get(input_basename, 'Skipped (Internal Error - No Std Status Found)')

                final_status = 'Unknown' # Default status

                # Skip test run if standard JAR timed out
                if std_status == 'TLE':
                    print(f"    跳过 {input_basename} 的测试运行，因为标准 JAR 超时。")
                    final_status = 'AC (Skipped - Std TLE)'
                    jar_results[input_basename] = final_status
                    # Create a minimal log indicating skip reason
                    create_log_file(log_path, input_path, std_ans_path, "", std_status, None, b"", final_status)
                    continue # Move to the next input file
                elif std_status == 'Skipped (Internal Error - No Std Status Found)':
                     print(f"    跳过对比: 未找到 '{input_basename}' 的标准运行状态。")
                     jar_results[input_basename] = std_status
                     continue

                # Run the test JAR
                test_status, _, test_stderr_content = run_jar(test_jar_path, input_path, test_out_path, TIMEOUT_SECONDS)

                # Determine final status based on comparison
                comparison_needed = False
                if std_status == test_status:
                    if std_status == 'AC':
                        comparison_needed = True # Both AC, need to compare output
                    else:
                        # Both failed in the same way (RE) - Treat as AC for comparison purposes
                        # TLE case is handled above by skipping
                        final_status = 'AC'
                        print(f"    状态匹配 ({std_status})。接受。")
                else:
                    # Statuses differ
                    if test_status == 'AC':
                        # Test JAR passed but standard failed (RE) - this is effectively WA
                        final_status = 'WA'
                        print(f"    状态不匹配: 测试 JAR 为 AC, 标准 JAR 为 {std_status}。标记为 WA。")
                        comparison_needed = True # Compare output to see the difference
                    else:
                        # Test JAR failed differently than standard JAR, or standard passed and test failed
                        final_status = test_status # Report the test JAR's failure status (TLE or RE)
                        print(f"    状态不匹配: 测试 JAR 为 {test_status}, 标准 JAR 为 {std_status}。标记为 {final_status}。")

                # Compare outputs if needed
                if comparison_needed:
                     if compare_outputs(std_ans_path, test_out_path):
                         # If outputs match, and we reached here, it means std_status was AC
                         final_status = 'AC'
                         print(f"    输出匹配。接受。")
                     else:
                         # Outputs differ
                         final_status = 'WA'
                         print(f"    输出与标准答案不同。标记为 WA。")

                # Store result and create log if not AC
                jar_results[input_basename] = final_status
                # Create log for any non-AC status, including RE, TLE, WA
                if final_status != 'AC' and final_status != 'AC (Skipped - Std TLE)':
                     create_log_file(log_path, input_path, std_ans_path, test_out_path,
                                     std_status, test_status, test_stderr_content, final_status)

    # 6. Generate Reports
    print("\n--- Phase 5: Generating Reports ---")
    if not overall_results:
        print("未运行测试 JAR。跳过报告生成。")
    else:
        for test_jar_name, results in overall_results.items():
            report_filename = f"{os.path.splitext(test_jar_name)[0]}_report.txt"
            # Place report in the same directory as the script
            report_path = os.path.join(os.path.dirname(sys.argv[0]) or '.', report_filename)
            print(f"  生成报告: {report_path}")

            total_cases = len(results)
            # Use a dictionary for counts for flexibility
            counts = {'AC': 0, 'WA': 0, 'TLE': 0, 'RE': 0, 'AC (Skipped - Std TLE)': 0, 'Other Skipped': 0}
            failed_or_skipped_cases = [] # List of tuples (input_name, status)

            for input_name, status in results.items():
                # Normalize status for counting if it's an internal skip reason
                count_status = status
                if status not in counts:
                    count_status = 'Other Skipped'

                counts[count_status] = counts.get(count_status, 0) + 1

                # Log non-AC cases for the report details, showing original status
                if status != 'AC':
                    failed_or_skipped_cases.append((input_name, status))

            # Sort failed/skipped cases for consistent reporting
            failed_or_skipped_cases.sort()

            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(f"--- 测试报告: {test_jar_name} ---\n\n")
                    f.write(f"总处理测试用例数: {total_cases}\n")
                    f.write("结果汇总:\n")

                    # Write counts for each status category if > 0
                    if counts['AC'] > 0: f.write(f"  - AC (通过):              {counts['AC']}\n")
                    if counts['WA'] > 0: f.write(f"  - WA (答案错误):          {counts['WA']}\n")
                    if counts['TLE'] > 0: f.write(f"  - TLE (超时):             {counts['TLE']}\n")
                    if counts['RE'] > 0: f.write(f"  - RE (运行时错误):        {counts['RE']}\n")
                    if counts['AC (Skipped - Std TLE)'] > 0: f.write(f"  - 跳过 (因标程TLE):     {counts['AC (Skipped - Std TLE)']}\n")
                    if counts['Other Skipped'] > 0: f.write(f"  - 跳过 (其他原因):    {counts['Other Skipped']}\n")


                    # Write details of failed/skipped cases
                    if failed_or_skipped_cases:
                        f.write("\n失败/跳过用例详情:\n")
                        for name, status in failed_or_skipped_cases:
                            f.write(f"  - {name}: {status}\n")
                    # Write overall success message if applicable
                    elif counts['AC'] == total_cases:
                         f.write("\n*** 所有测试用例通过! ***\n")
                    else: # Some skipped but no failures
                         f.write("\n*** 所有运行的测试用例通过 (部分用例可能被跳过)。 ***\n")

            except Exception as e:
                print(f"  写入报告 {report_path} 时出错: {e}")

    end_overall_time = time.time()
    print(f"\n--- 测试完成 ---")
    print(f"总执行时间: {end_overall_time - start_overall_time:.2f} 秒。")
    print("====================================")
