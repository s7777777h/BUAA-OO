import os
import subprocess
import sys
import time
import glob
import shutil
import filecmp
import signal
import platform

# --- Configuration ---
STD_DIR = "std"
TESTJAR_DIR = "testjar"
DATA_DIR = "data"
OUT_DIR = "out"
STDOUT_DIR = "stdout"
LOG_DIR = "log"
TIMEOUT_SECONDS = 10
DATA_GENERATOR_SCRIPT = "data_generator.py"

# --- Global Variable for Standard Run Statuses ---
std_run_statuses = {} # Stores {input_basename: status} for std.jar runs

# --- Helper Functions ---

def create_dir_if_not_exists(dir_path):
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(dir_path):
        print(f"Creating directory: {dir_path}")
        os.makedirs(dir_path)

def clear_dir(dir_path):
    """Removes all files and subdirectories within a directory."""
    if not os.path.exists(dir_path):
        return
    print(f"Clearing directory: {dir_path}")
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def run_jar(jar_path, input_path, output_path, timeout):
    """
    Runs a JAR file with specified input, saving output.
    Returns a tuple: (status, stdout_content_ignored, stderr_content)
    status can be 'AC', 'TLE', 'RE'
    stdout_content_ignored is always b'' as stdout is written to file.
    """
    status = 'AC'
    stderr_content = b''
    start_time = time.time()
    process = None

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'wb') as outfile:

            java_command = [
                'java',
                # Recommended: Add memory limits, adjust as needed
                '-Xms128m',
                '-Xmx512m',
                '-jar',
                jar_path
            ]

            # Process group handling for better termination (non-Windows)
            preexec_fn_toset = None
            start_new_session = False
            if platform.system() != "Windows":
                preexec_fn_toset = os.setsid # Create new session, become process group leader
            else:
                # On Windows, subprocess.CREATE_NEW_PROCESS_GROUP allows killing with Ctrl+Break event
                # but taskkill /T is generally more robust for killing trees.
                # We'll rely on taskkill later.
                # start_new_session = True # Alternative using Popen flag if taskkill fails
                pass


            process = subprocess.Popen(
                java_command,
                stdin=infile,
                stdout=outfile,
                stderr=subprocess.PIPE,
                preexec_fn=preexec_fn_toset,
                # creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if start_new_session else 0 # Windows specific alternative
            )

            try:
                _, stderr_content = process.communicate(timeout=timeout)

                if stderr_content:
                    status = 'RE'
                    if process.returncode is not None and process.returncode != 0:
                        stderr_content += f"\n--- Exited with code: {process.returncode} ---".encode()
                elif process.returncode != 0:
                    print(f"    Note: Process {os.path.basename(jar_path)} on {os.path.basename(input_path)} "
                          f"exited with code {process.returncode} but stderr was empty.")
                    # Status remains 'AC', comparison decides WA/AC.

            except subprocess.TimeoutExpired:
                print(f"    Timeout expired for {os.path.basename(jar_path)} on {os.path.basename(input_path)}")
                if process and process.pid is not None:
                    print(f"    Attempting to terminate process PID/Group: {process.pid}")
                    try:
                        if platform.system() != "Windows":
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL) # Kill process group
                            print(f"    Killed process group for PID {process.pid}.")
                        else:
                            # Use taskkill on Windows to terminate the process tree forcefully
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True, capture_output=True, timeout=5)
                            print(f"    Terminated process tree for PID {process.pid} using taskkill.")
                    except Exception as kill_err:
                        print(f"    Termination failed for PID {process.pid}: {kill_err}. Trying process.kill() fallback.")
                        try:
                            process.kill() # Simple fallback
                        except Exception: pass # Ignore errors on fallback kill
                status = 'TLE'
                stderr_content = b"--- PROCESS KILLED DUE TO TIMEOUT ---"

    except FileNotFoundError:
        print(f"Error: 'java' command not found. Is Java installed and in PATH?")
        status = 'RE'
        stderr_content = b"Java command not found."
    except Exception as e:
        print(f"An unexpected error occurred running {jar_path}: {e}")
        status = 'RE'
        stderr_content = str(e).encode()
        if process and process.poll() is None:
             try:
                  process.kill()
                  process.wait(timeout=0.5)
             except Exception as kill_e:
                  print(f"    Error trying to kill process after unexpected error: {kill_e}")

    end_time = time.time()
    # Note: Changed "Initial Status" to "Run Status" for clarity
    print(f"    Finished {os.path.basename(jar_path)} on {os.path.basename(input_path)} in {end_time - start_time:.2f}s - Run Status: {status}")
    return status, b'', stderr_content

def compare_outputs(std_ans_path, test_out_path):
    """
    Compares two output files, ignoring leading/trailing whitespace on each line.
    Returns True if identical, False otherwise.
    """
    try:
        if not os.path.exists(std_ans_path):
             print(f"    Error comparing: Standard answer file not found ({std_ans_path})")
             return False
        if not os.path.exists(test_out_path):
             print(f"    Error comparing: Test output file not found ({test_out_path})")
             return False

        with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f1, \
             open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f2:
            lines1 = [line.strip() for line in f1]
            lines2 = [line.strip() for line in f2]
            while lines1 and not lines1[-1]: lines1.pop()
            while lines2 and not lines2[-1]: lines2.pop()
            return lines1 == lines2
    except Exception as e:
        print(f"    Error comparing files {std_ans_path} and {test_out_path}: {e}")
        return False

def create_log_file(log_path, input_path, std_ans_path, test_out_path,
                    std_status, test_status, test_stderr_content, final_status):
    """Creates a log file for a failed test case."""
    # Added check: Don't log if the final status is implicitly AC due to skipping
    if final_status == 'AC (Skipped - Std TLE)':
         print(f"    Skipping log creation for {os.path.basename(input_path)} (Std TLE).")
         return

    print(f"    Difference detected ({final_status})! Creating log: {log_path}")
    try:
        with open(log_path, 'w', encoding='utf-8') as logfile:
            logfile.write(f"--- Test Case Failed: {final_status} ---\n")
            logfile.write(f"Standard JAR Status: {std_status}\n")
            # Only report test status if it was actually run
            if test_status: # Check if test_status is not None (it won't be None if run)
                 logfile.write(f"Test JAR Status    : {test_status}\n\n")
            else:
                 logfile.write("Test JAR Status    : Not Run (Skipped due to Std TLE)\n\n")


            logfile.write("--- Input Data ({}) ---\n".format(os.path.basename(input_path)))
            try:
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    logfile.write(f.read())
            except Exception as e:
                logfile.write(f"\n!!! Error reading input file: {e} !!!\n")
            logfile.write("\n--- End Input Data ---\n\n")


            logfile.write("--- Standard Output ({}) ---\n".format(os.path.basename(std_ans_path)))
            if os.path.exists(std_ans_path):
                try:
                    with open(std_ans_path, 'r', encoding='utf-8', errors='ignore') as f:
                        logfile.write(f.read())
                except Exception as e:
                    logfile.write(f"\n!!! Error reading standard output file: {e} !!!\n")
            else:
                 logfile.write("!!! Standard output file not found or empty !!!\n")
            logfile.write("\n--- End Standard Output ---\n\n")


            # Only include stderr if the test jar actually produced it
            if test_status == 'RE' or test_status == 'TLE':
                 logfile.write("--- Test Program Standard Error ---\n")
                 logfile.write(test_stderr_content.decode(encoding='utf-8', errors='ignore'))
                 logfile.write("\n--- End Test Program Standard Error ---\n\n")

            logfile.write("--- Test Program Output ({}) ---\n".format(os.path.basename(test_out_path)))
            if os.path.exists(test_out_path):
                 try:
                      with open(test_out_path, 'r', encoding='utf-8', errors='ignore') as f:
                           logfile.write(f.read())
                 except Exception as e:
                      logfile.write(f"\n!!! Error reading test output file: {e} !!!\n")
            else:
                 logfile.write("!!! Test output file not found or empty (possibly skipped or crashed early) !!!\n")
            logfile.write("\n--- End Test Program Output ---\n")

    except Exception as e:
        print(f"    Error creating log file {log_path}: {e}")


# --- Main Script Logic ---

if __name__ == "__main__":
    # 1. Setup and Optional Data Generation
    print("--- Setup Phase ---")
    # ... (directory creation) ...
    create_dir_if_not_exists(DATA_DIR)
    create_dir_if_not_exists(OUT_DIR)
    create_dir_if_not_exists(STDOUT_DIR)
    create_dir_if_not_exists(LOG_DIR)
    create_dir_if_not_exists(STD_DIR)
    create_dir_if_not_exists(TESTJAR_DIR)

    while True:
        gen_data = input("Generate new data using data_generator.py? (y/n): ").lower()
        if gen_data in ['y', 'n']:
            break
        print("Invalid input. Please enter 'y' or 'n'.")

    if gen_data == 'y':
        # ... (clearing directories and running data generator) ...
        if not os.path.exists(DATA_GENERATOR_SCRIPT): print(f"Error: Data generator script '{DATA_GENERATOR_SCRIPT}' not found."); sys.exit(1)
        print("Clearing ALL relevant directories...")
        clear_dir(DATA_DIR); clear_dir(OUT_DIR); clear_dir(STDOUT_DIR); clear_dir(LOG_DIR)
        std_run_statuses.clear()
        try:
            print(f"Running data generator: {DATA_GENERATOR_SCRIPT}...")
            subprocess.run([sys.executable, DATA_GENERATOR_SCRIPT], check=True)
            print("Data generation complete.")
        except Exception as e: print(f"An unexpected error occurred during data generation: {e}"); sys.exit(1)


    # Find standard JAR
    # ... (std jar finding) ...
    std_jars = glob.glob(os.path.join(STD_DIR, "*.jar"))
    if not std_jars: print(f"Error: No standard JAR file found in '{STD_DIR}'."); sys.exit(1)
    if len(std_jars) > 1: print(f"Error: Multiple JAR files found in '{STD_DIR}'."); sys.exit(1)
    std_jar_path = std_jars[0]; print(f"Found standard JAR: {std_jar_path}")


    # Find test JARs
    # ... (test jar finding) ...
    test_jar_paths = glob.glob(os.path.join(TESTJAR_DIR, "*.jar"))
    if not test_jar_paths: print(f"Warning: No test JAR files found in '{TESTJAR_DIR}'.")


    # Find input data files
    # ... (input file finding) ...
    input_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
    if not input_files: print(f"Error: No input data files (.txt) found in '{DATA_DIR}'."); sys.exit(1)
    print(f"Found {len(input_files)} input data files."); print(f"Found {len(test_jar_paths)} test JAR files.")
    print("--- End Setup Phase ---")


    # 2. Generate Standard Outputs and Record Statuses
    print("\n--- Generating Standard Outputs & Recording Statuses ---")
    std_run_statuses.clear()
    for input_path in input_files:
        input_basename = os.path.basename(input_path)
        std_ans_basename = os.path.splitext(input_basename)[0] + ".ans"
        std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)

        print(f"  Running standard JAR for {input_basename}...")
        std_status, _, std_stderr = run_jar(std_jar_path, input_path, std_ans_path, timeout=TIMEOUT_SECONDS * 3) # Give std more time
        std_run_statuses[input_basename] = std_status

        if std_status != 'AC' and not os.path.exists(std_ans_path):
             try:
                  open(std_ans_path, 'w').close()
                  print(f"    Created empty standard output file due to status: {std_status}")
             except Exception as e_create:
                  print(f"    Warning: Failed to create empty output file {std_ans_path}: {e_create}")

        if std_status == 'RE': print(f"    Warning: Standard JAR reported RE for {input_basename}.")
        elif std_status == 'TLE': print(f"    Warning: Standard JAR reported TLE for {input_basename}.")

    print("--- Standard Output Generation & Status Recording Complete ---")


    # 3. Run Comparison Testing
    print("\n--- Comparison Testing Phase ---")
    overall_results = {}

    if not test_jar_paths:
         print("No test JARs found to compare. Exiting.")
         sys.exit(0)

    for test_jar_path in test_jar_paths:
        test_jar_name = os.path.basename(test_jar_path)
        print(f"\n--- Testing JAR: {test_jar_name} ---")
        jar_results = {}
        overall_results[test_jar_name] = jar_results

        for input_path in input_files:
            input_basename = os.path.basename(input_path)
            input_name_no_ext = os.path.splitext(input_basename)[0]
            print(f"  Testing with input: {input_basename}")

            # Define paths
            test_out_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.txt"
            test_out_path = os.path.join(OUT_DIR, test_out_filename)
            log_filename = f"{os.path.splitext(test_jar_name)[0]}_{input_name_no_ext}.log"
            log_path = os.path.join(LOG_DIR, log_filename)
            std_ans_basename = input_name_no_ext + ".ans"
            std_ans_path = os.path.join(STDOUT_DIR, std_ans_basename)

            # Retrieve standard status
            std_status = std_run_statuses.get(input_basename, 'Skipped (No Std Status)')

            # --- MODIFICATION: Skip if Std TLE ---
            if std_status == 'TLE':
                print(f"    Skipping input {input_basename} because std.jar timed out.")
                final_status = 'AC (Skipped - Std TLE)' # Assign special status
                jar_results[input_basename] = final_status
                # Note: We don't create a log file here for skipped cases
                continue # Move to the next input file for this test jar
            elif std_status == 'Skipped (No Std Status)':
                 print(f"    Skipping comparison: Standard status for '{input_basename}' not found.")
                 jar_results[input_basename] = std_status
                 continue
            # --- End MODIFICATION ---

            # If std_status was not TLE or Skipped, proceed with running test jar
            test_status, _, test_stderr_content = run_jar(test_jar_path, input_path, test_out_path, TIMEOUT_SECONDS)

            # Compare Statuses and Determine Final Status
            final_status = 'Unknown'
            comparison_needed = False

            if std_status == test_status:
                if std_status == 'AC':
                    comparison_needed = True # Will set final_status after compare
                else: # Both RE
                    final_status = 'AC'
                    print(f"    Consistent non-AC behavior ({std_status}). Accepted.")
            else: # Statuses differ
                if test_status == 'AC': # Test AC, Std RE
                    final_status = 'WA'
                    print(f"    Status mismatch: Test JAR AC, but Standard JAR was {std_status}.")
                else: # Test RE/TLE, Std AC or different RE
                    final_status = test_status # Report Test JAR's failure
                    print(f"    Status mismatch: Test JAR {test_status}, Standard JAR was {std_status}.")

            # Perform comparison only if needed (both initially AC)
            if comparison_needed:
                 if compare_outputs(std_ans_path, test_out_path):
                      final_status = 'AC'
                 else:
                      final_status = 'WA'
                      print(f"    Stdout differs from standard answer.")

            # Store final result
            jar_results[input_basename] = final_status

            # Create log file ONLY if final status is not Accepted AND not the special skipped status
            if final_status != 'AC' and final_status != 'AC (Skipped - Std TLE)':
                 # Pass test_status which is relevant here
                 create_log_file(log_path, input_path, std_ans_path, test_out_path,
                                 std_status, test_status, test_stderr_content, final_status)


    # 4. Generate Reports
    print("\n--- Generating Reports ---")
    for test_jar_name, results in overall_results.items():
        report_filename = f"{os.path.splitext(test_jar_name)[0]}_report.txt"
        report_path = os.path.join(os.path.dirname(sys.argv[0]) or '.', report_filename)
        print(f"  Generating report: {report_path}")

        total_cases = len(results)
        # Initialize counts, including the new skipped status
        counts = {'AC': 0, 'WA': 0, 'TLE': 0, 'RE': 0, 'AC (Skipped - Std TLE)': 0}
        other_skipped_count = 0
        failed_or_skipped_cases = [] # Stores tuples (input_name, status)

        for input_name, status in results.items():
            if status in counts:
                counts[status] = counts.get(status, 0) + 1
            else: # Handle 'Skipped (No Std Status)' etc.
                other_skipped_count += 1
                status = status # Keep the original status string

            # List all non-plain 'AC' results for details
            if status != 'AC':
                failed_or_skipped_cases.append((input_name, status))

        failed_or_skipped_cases.sort() # Sort by input name

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"--- Test Report for {test_jar_name} ---\n\n")
                f.write(f"Total Test Cases Processed: {total_cases}\n")
                f.write("Summary:\n")
                plain_ac_count = counts.get('AC', 0)
                skipped_tle_count = counts.get('AC (Skipped - Std TLE)', 0)
                wa_count = counts.get('WA', 0)
                tle_count = counts.get('TLE', 0)
                re_count = counts.get('RE', 0)

                if plain_ac_count > 0: f.write(f"  - AC (Passed): {plain_ac_count}\n")
                if wa_count > 0: f.write(f"  - WA (Wrong Answer): {wa_count}\n")
                if tle_count > 0: f.write(f"  - TLE (Time Limit Exceeded): {tle_count}\n")
                if re_count > 0: f.write(f"  - RE (Runtime Error): {re_count}\n")
                if skipped_tle_count > 0: f.write(f"  - Skipped (Standard TLE): {skipped_tle_count}\n")
                if other_skipped_count > 0: f.write(f"  - Skipped (Other): {other_skipped_count}\n")


                if failed_or_skipped_cases:
                    f.write("\nDetailed Results (Non-AC Cases):\n")
                    for name, status in failed_or_skipped_cases:
                        f.write(f"  - {name}: {status}\n")
                # Check if all non-skipped cases passed
                elif skipped_tle_count == 0 and other_skipped_count == 0:
                     f.write("\nAll test cases passed!\n")
                else:
                     f.write("\nAll run test cases passed (or were skipped due to Std TLE).\n")

        except Exception as e:
            print(f"  Error writing report {report_path}: {e}")


    print("\n--- Comparison Testing Complete ---")