# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import re
import shutil
import time
# --- Parallelism Imports ---
import concurrent.futures
# --- End Parallelism Imports ---
from threading import Lock, Thread, Event # For stream readers
import math
from collections import defaultdict, deque
import traceback

# --- Plotting Import ---
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
# --- End Plotting Import ---


# --- Configuration ---
DATA_DIR = "data"
OUT_DIR = "out"
REPORT_DIR = "report"
PLOT_FILENAME_RUNTIME = "runtime_comparison.png" # Name for the runtime plot file
PLOT_FILENAME_POWER = "power_consumption.png" # Name for the power plot file
PLOT_FILENAME_AVGTIME = "weighted_avg_time.png" # Name for the weighted time plot file
GENERATOR_SCRIPT = "data_generator.py"
# JAR_EXECUTION_TIMEOUT = 150
MOVE_TIME_PER_FLOOR = 0.4 # Used by validator timing checks, NOT power calc
DOOR_OPEN_CLOSE_TIME = 0.4
ELEVATOR_CAPACITY = 6
NUM_ELEVATORS = 6
EPSILON = 1e-9
SOFT_TIMEOUT = 120.0
HARD_TIMEOUT = 150.0
POLL_INTERVAL = 0.1

# --- Power Calculation Constants ---
POWER_OPEN = 0.1
POWER_CLOSE = 0.1
POWER_MOVE = 0.4
# --- End Power Calc ---


# --- Parallelism Configuration ---
PARALLEL_MODE = 'data' # 'none', 'data', 'jar'
try: DEFAULT_WORKERS = min(32, (os.cpu_count() or 1) + 4)
except AttributeError: DEFAULT_WORKERS = 8
MAX_WORKERS = None
if MAX_WORKERS is None: MAX_WORKERS = DEFAULT_WORKERS
# --- End Parallelism Config ---


# Floor definitions (Maps)
FLOOR_MAP_STR_TO_INT = {"B4":-4,"B3":-3,"B2":-2,"B1":-1,"F1":1,"F2":2,"F3":3,"F4":4,"F5":5,"F6":6,"F7":7}
FLOOR_MAP_INT_TO_STR = {v: k for k, v in FLOOR_MAP_STR_TO_INT.items()}
MIN_FLOOR_INT, MAX_FLOOR_INT = -4, 7

# Regular Expressions for Parsing
RE_TIMESTAMP = re.compile(r"\[\s*([\d.]+)\s*\]")
RE_INPUT = re.compile(r"\[\s*([\d.]+)\s*\](\d+)-PRI-(\d+)-FROM-([BF]\d+)-TO-([BF]\d+)-BY-(\d+)") # Added Priority capture (group 3)
RE_ARRIVE = re.compile(r"\[\s*([\d.]+)\s*\]ARRIVE-([BF]\d+)-(\d+)")
RE_OPEN = re.compile(r"\[\s*([\d.]+)\s*\]OPEN-([BF]\d+)-(\d+)")
RE_CLOSE = re.compile(r"\[\s*([\d.]+)\s*\]CLOSE-([BF]\d+)-(\d+)")
RE_IN = re.compile(r"\[\s*([\d.]+)\s*\]IN-(\d+)-([BF]\d+)-(\d+)")
RE_OUT = re.compile(r"\[\s*([\d.]+)\s*\]OUT-(\d+)-([BF]\d+)-(\d+)")


# --- Helper Functions ---
def floor_to_int(floor_str): return FLOOR_MAP_STR_TO_INT.get(floor_str)
def int_to_floor(floor_int):
    if floor_int is None or floor_int not in FLOOR_MAP_INT_TO_STR: return f"InvalidFloor({floor_int})"
    return FLOOR_MAP_INT_TO_STR.get(floor_int)
def clear_directory(dir_path):
    if not os.path.isdir(dir_path): return
    for item_name in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item_name)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path): os.unlink(item_path)
            elif os.path.isdir(item_path): shutil.rmtree(item_path)
        except Exception as e: print(f"Warning: Failed to delete {item_path}. Reason: {e}", file=sys.stderr)
def find_files(directory, extension):
    if not os.path.isdir(directory): return []
    return sorted([f for f in os.listdir(directory) if f.endswith(extension) and os.path.isfile(os.path.join(directory, f))])

# --- Runner Function with Stream Consuming Threads ---
# (Keep run_java_program_with_threads and stream_reader_thread as before)
def stream_reader_thread(stream_pipe, output_buffer, buffer_lock):
    try:
        for chunk in iter(lambda: stream_pipe.read(4096), ''):
             with buffer_lock: output_buffer.append(chunk)
    except ValueError: pass
    except Exception: pass
    finally:
        try: stream_pipe.close()
        except Exception: pass

def run_java_program_with_threads(jar_file, input_data_str):
    start_time = time.monotonic()
    stdout_buffer, stderr_buffer = [], []
    stdout_lock, stderr_lock = Lock(), Lock()
    full_stderr_str, exit_code, status_code = "", None, None
    process = None
    stdout_thread, stderr_thread = None, None
    tle_marked = False

    try:
        process = subprocess.Popen(
            ['java', '-jar', jar_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', bufsize=1
        )
        stdout_thread = Thread(target=stream_reader_thread, args=(process.stdout, stdout_buffer, stdout_lock), daemon=True)
        stderr_thread = Thread(target=stream_reader_thread, args=(process.stderr, stderr_buffer, stderr_lock), daemon=True)
        stdout_thread.start(); stderr_thread.start()

        try: # Send input
            if input_data_str: process.stdin.write(input_data_str)
            process.stdin.close()
        except (BrokenPipeError, OSError) as e: status_code, full_stderr_str = "ExecutionError", full_stderr_str + f"\nError sending input/closing stdin: {e}"

        process_terminated_normally = False
        if status_code != "ExecutionError": # Only monitor if input phase ok
            while True:
                elapsed_time = time.monotonic() - start_time
                if elapsed_time > HARD_TIMEOUT:
                    if status_code != "Killed":
                        status_code = "Killed"
                        full_stderr_str += f"\nChecker: Hard timeout ({HARD_TIMEOUT}s) killed."
                        # Correctly indented try-except
                        try:
                            process.kill()
                        except Exception:
                            pass # Ignore kill errors
                    break # Exit monitoring loop

                exit_code = process.poll()
                if exit_code is not None:
                    process_terminated_normally = True
                    if status_code not in ["Killed", "TLE"]: status_code = "ExecutionError" if exit_code != 0 else None
                    elif status_code == "TLE": pass
                    break
                if not tle_marked and elapsed_time > SOFT_TIMEOUT:
                    if status_code != "Killed": status_code = "TLE"
                    tle_marked = True
                time.sleep(POLL_INTERVAL)

        # Wait for process if not naturally terminated
        if not process_terminated_normally and process.poll() is None:
             process_wait_timeout = HARD_TIMEOUT - (time.monotonic() - start_time) + 2.0
             try: process.wait(timeout=max(0.1, process_wait_timeout))
             except subprocess.TimeoutExpired:
                  if status_code != "Killed":
                      full_stderr_str += "\nChecker: Process wait() timed out, forcing kill."
                      status_code = "Killed"
                  # Correctly indented try-except
                  try:
                      process.kill()
                  except Exception:
                      pass # Ignore errors during forced kill
             except Exception as wait_e: full_stderr_str += f"\nChecker: Error during process.wait(): {wait_e}"; status_code = "ExecutionError" if status_code not in ["Killed", "TLE", "ExecutionError"] else status_code

        # Wait for reader threads
        thread_join_timeout = 5.0
        stdout_thread.join(timeout=thread_join_timeout)
        stderr_thread.join(timeout=thread_join_timeout)
        if stdout_thread.is_alive() or stderr_thread.is_alive(): full_stderr_str += "\nChecker: Warning - reader threads did not exit cleanly."

        # Construct final output
        with stdout_lock: full_stdout = "".join(stdout_buffer)
        with stderr_lock: full_stderr_str += "".join(stderr_buffer)

        # Final Status Determination
        final_exit_code = process.poll()
        if status_code not in ["Killed", "TLE", "ExecutionError", "JavaNotFound"]:
            if final_exit_code is None: status_code = "ExecutionError"; full_stderr_str += "\nChecker: Process poll() None after threads joined."
            elif final_exit_code != 0: status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Exit code {final_exit_code}."
            elif final_exit_code == 0 and tle_marked: status_code = "TLE"
        elif status_code is None and final_exit_code != 0: status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Exit code {final_exit_code} (update)."

    except FileNotFoundError: end_time = time.monotonic(); return "", f"Error: 'java' command not found...", end_time - start_time, "JavaNotFound"
    except Exception as popen_e: end_time = time.monotonic(); return "", f"Error starting {jar_file}: {popen_e}", end_time - start_time, "ExecutionError"
    finally: # Final cleanup
        if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=0.5)
        if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=0.5)
        # Correctly indented try-except
        if process and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=0.5)
            except Exception:
                pass # Ignore errors during final cleanup

    end_time = time.monotonic()
    execution_time = end_time - start_time
    return full_stdout, full_stderr_str.strip(), execution_time, status_code


# --- Define constants dependent on helper functions ---
F1_INT = floor_to_int('F1')
B1_INT = floor_to_int('B1')

# --- Validation Logic ---
class Validator:
    def __init__(self, input_requests_parsed):
        self.errors = []
        self.input_requests = {} # Store full request info: {pid: {'time': float, 'pri': int, ...}}
        self.sim_time = 0.0
        self.elevators = {}
        self.passengers = {} # {pid: {'state':..., 'location':..., 'destination':..., 'assigned_elevator':..., 'request_time':float, 'priority':int, 'arrival_time':float}}

        # --- Counters for Power Calculation ---
        self.open_count = 0
        self.close_count = 0
        self.move_count = 0 # Counts ARRIVE actions
        # ---

        # Initialize elevators
        for i in range(1, NUM_ELEVATORS + 1):
            self.elevators[i] = {'floor': F1_INT, 'state': 'CLOSED', 'passengers': set(), 'last_action_time': 0.0, 'last_arrive_time': 0.0, 'open_time': -1.0}

        # Initialize passengers, storing request time and priority
        for req in input_requests_parsed:
            pid = req['id']
            self.input_requests[pid] = req # Store full request details
            self.passengers[pid] = {
                'state': 'OUTSIDE', 'location': req['from'], 'destination': req['to'],
                'assigned_elevator': req['by'], 'request_time': req['time'],
                'priority': req['pri'], # Store priority
                'arrival_time': -1.0 # Initialize arrival time
            }

    def add_error(self, message):
        error_time_str = f"{max(0.0, self.sim_time):.4f}" if isinstance(self.sim_time, (int, float)) else "?.????"
        self.errors.append(f"[Time ~{error_time_str}] {message}")

    def validate_line(self, line):
        """Returns True if line ok or non-fatal error, False on critical parse/internal error"""
        line = line.strip();
        if not line: return True
        match_ts = RE_TIMESTAMP.match(line)
        if not match_ts: self.add_error(f"CRITICAL: Malformed line (no timestamp): {line}"); return False
        try: current_line_time = float(match_ts.group(1));
        except ValueError: self.add_error(f"CRITICAL: Malformed timestamp: {match_ts.group(1)}"); return False
        if current_line_time < 0: self.add_error(f"CRITICAL: Negative timestamp: {current_line_time}"); return False
        if current_line_time < self.sim_time - EPSILON * 10: self.add_error(f"Timestamp decreasing: {current_line_time:.4f} < {self.sim_time:.4f}")
        self.sim_time = max(self.sim_time, current_line_time)

        match_arrive, match_open, match_close, match_in, match_out = RE_ARRIVE.match(line), RE_OPEN.match(line), RE_CLOSE.match(line), RE_IN.match(line), RE_OUT.match(line)
        try:
            if match_arrive:
                _, floor_str, eid_str = match_arrive.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                if floor_int is None or eid not in self.elevators: self.add_error(f"ARRIVE Invalid floor/elevator: {line}"); return True # Non-fatal parse issue within line
                state, prev_floor = self.elevators[eid], self.elevators[eid]['floor']
                # (Validation checks using add_error)
                if state['state'] != 'CLOSED': self.add_error(f"ARRIVE-{floor_str}-{eid}: Elevator not CLOSED.")
                is_valid_move = (prev_floor == B1_INT and floor_int == F1_INT) or (prev_floor == F1_INT and floor_int == B1_INT) or (abs(floor_int - prev_floor) == 1)
                if not is_valid_move: self.add_error(f"ARRIVE-{floor_str}-{eid}: Invalid move from {int_to_floor(prev_floor)}.")
                expected_min_time = state['last_action_time'] + MOVE_TIME_PER_FLOOR
                if current_line_time < expected_min_time - EPSILON: self.add_error(f"ARRIVE-{floor_str}-{eid}: Move too fast.")
                # Update state & count
                state['floor'], state['last_action_time'], state['last_arrive_time'] = floor_int, current_line_time, current_line_time
                self.move_count += 1 # Increment move count

            elif match_open:
                _, floor_str, eid_str = match_open.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                if floor_int is None or eid not in self.elevators: self.add_error(f"OPEN Invalid floor/elevator: {line}"); return True
                state = self.elevators[eid]
                # (Validation checks using add_error)
                if state['state'] != 'CLOSED': self.add_error(f"OPEN-{floor_str}-{eid}: Elevator not CLOSED.")
                if state['floor'] != floor_int: self.add_error(f"OPEN-{floor_str}-{eid}: Elevator at wrong floor {int_to_floor(state['floor'])}.")
                # Update state & count
                state['state'], state['open_time'], state['last_action_time'] = 'OPEN', current_line_time, current_line_time
                self.open_count += 1 # Increment open count

            elif match_close:
                _, floor_str, eid_str = match_close.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                if floor_int is None or eid not in self.elevators: self.add_error(f"CLOSE Invalid floor/elevator: {line}"); return True
                state = self.elevators[eid]
                # (Validation checks using add_error)
                if state['state'] != 'OPEN': self.add_error(f"CLOSE-{floor_str}-{eid}: Elevator not OPEN.")
                if state['floor'] != floor_int: self.add_error(f"CLOSE-{floor_str}-{eid}: Elevator at wrong floor {int_to_floor(state['floor'])}.")
                if state['open_time'] >= 0:
                    expected_min_close_time = state['open_time'] + DOOR_OPEN_CLOSE_TIME
                    if current_line_time < expected_min_close_time - EPSILON: self.add_error(f"CLOSE-{floor_str}-{eid}: Door closed too fast.")
                else: self.add_error(f"CLOSE-{floor_str}-{eid}: Cannot check duration, invalid open_time.")
                # Update state & count
                state['state'], state['open_time'], state['last_action_time'] = 'CLOSED', -1.0, current_line_time
                self.close_count += 1 # Increment close count

            elif match_in:
                _, pid_str, floor_str, eid_str = match_in.groups(); pid, eid = int(pid_str), int(eid_str); floor_int = floor_to_int(floor_str)
                if floor_int is None or pid not in self.passengers or eid not in self.elevators: self.add_error(f"IN Invalid floor/pid/elevator: {line}"); return True
                p_state, e_state = self.passengers[pid], self.elevators[eid]
                # (Validation checks using add_error)
                if e_state['state'] != 'OPEN': self.add_error(f"IN-{pid}-{floor_str}-{eid}: Elevator not OPEN.")
                if e_state['floor'] != floor_int: self.add_error(f"IN-{pid}-{floor_str}-{eid}: Elevator at wrong floor {int_to_floor(e_state['floor'])}.")
                if p_state['state'] != 'OUTSIDE': self.add_error(f"IN-{pid}-{floor_str}-{eid}: Passenger not OUTSIDE.")
                if p_state['state'] == 'OUTSIDE' and p_state['location'] != floor_int: self.add_error(f"IN-{pid}-{floor_str}-{eid}: Passenger not at floor {floor_str}.")
                if p_state['assigned_elevator'] != eid: self.add_error(f"IN-{pid}-{floor_str}-{eid}: Passenger entered wrong elevator.")
                if pid not in e_state['passengers'] and len(e_state['passengers']) >= ELEVATOR_CAPACITY: self.add_error(f"IN-{pid}-{floor_str}-{eid}: Elevator full.")
                if pid in e_state['passengers']: self.add_error(f"IN-{pid}-{floor_str}-{eid}: Passenger already in elevator.")
                # Update state
                e_state['passengers'].add(pid); p_state['state'], p_state['location'] = 'INSIDE', eid

            elif match_out:
                _, pid_str, floor_str, eid_str = match_out.groups(); pid, eid = int(pid_str), int(eid_str); floor_int = floor_to_int(floor_str)
                if floor_int is None or pid not in self.passengers or eid not in self.elevators: self.add_error(f"OUT Invalid floor/pid/elevator: {line}"); return True
                p_state, e_state = self.passengers[pid], self.elevators[eid]
                # (Validation checks using add_error)
                if e_state['state'] != 'OPEN': self.add_error(f"OUT-{pid}-{floor_str}-{eid}: Elevator not OPEN.")
                if e_state['floor'] != floor_int: self.add_error(f"OUT-{pid}-{floor_str}-{eid}: Elevator at wrong floor {int_to_floor(e_state['floor'])}.")
                if p_state['state'] != 'INSIDE': self.add_error(f"OUT-{pid}-{floor_str}-{eid}: Passenger not INSIDE.")
                if p_state['state'] == 'INSIDE' and p_state['location'] != eid: self.add_error(f"OUT-{pid}-{floor_str}-{eid}: Passenger in wrong elevator {p_state['location']}.")
                if pid not in e_state['passengers']: self.add_error(f"OUT-{pid}-{floor_str}-{eid}: Passenger not in elevator list.")
                # Update state
                if pid in e_state['passengers']: e_state['passengers'].remove(pid)
                p_state['location'] = floor_int
                if floor_int == p_state['destination']:
                    p_state['state'] = 'ARRIVED'
                    p_state['arrival_time'] = current_line_time # Record arrival time
                else: p_state['state'] = 'OUTSIDE'

        except ValueError: # Catch int() conversion errors specifically
             self.add_error(f"CRITICAL: Invalid integer ID in line: {line}")
             return False
        except Exception as e:
            self.add_error(f"CRITICAL: Internal Validator Error on line '{line}': {e}")
            self.add_error(traceback.format_exc(limit=5)); return False
        return True

    def final_checks(self):
        # (final_checks logic remains the same)
        for pid, p_state in self.passengers.items():
            if p_state.get('state') != 'ARRIVED':
                req = self.input_requests.get(pid)
                if not req: self.add_error(f"Passenger {pid} (details missing) did not finish ARRIVED."); continue
                loc_desc = 'N/A'
                if p_state.get('state') == 'INSIDE': loc_desc = f"Elevator {p_state.get('location', '?')}"
                elif p_state.get('state') == 'OUTSIDE': loc_desc = int_to_floor(p_state.get('location'))
                # Add priority info to error message
                self.add_error(f"Passenger {pid} (Pri={p_state.get('priority','?')}) did not reach destination {int_to_floor(req['to'])} (final state: {p_state.get('state', '?')} at {loc_desc}).")
        for eid, e_state in self.elevators.items():
            if e_state.get('state') != 'CLOSED': self.add_error(f"Elevator {eid} not CLOSED at end.")
            if e_state.get('passengers'): self.add_error(f"Elevator {eid} finished with passengers: {sorted(list(e_state['passengers']))}.")

    def get_errors(self): return self.errors
    def get_final_sim_time(self): return self.sim_time if self.sim_time > 0 else 0.0

    # --- ADDED: Methods for new metrics ---
    def get_power_consumption(self):
        """Calculates total power consumption based on counts."""
        return (POWER_OPEN * self.open_count +
                POWER_CLOSE * self.close_count +
                POWER_MOVE * self.move_count)

    def get_weighted_average_completion_time(self):
        """Calculates weighted average completion time for passengers who arrived."""
        total_weighted_time = 0
        total_priority = 0
        passengers_arrived = 0
        for pid, p_state in self.passengers.items():
            if p_state.get('state') == 'ARRIVED':
                arrival_time = p_state.get('arrival_time', -1.0)
                request_time = p_state.get('request_time', -1.0)
                priority = p_state.get('priority', 0) # Default priority 0 if missing? Or handle error?

                if arrival_time >= 0 and request_time >= 0 and priority > 0: # Only consider valid data with positive priority
                    completion_time = arrival_time - request_time
                    if completion_time >= 0: # Sanity check
                        total_weighted_time += completion_time * priority
                        total_priority += priority
                        passengers_arrived += 1
                    else:
                         self.add_error(f"WARN: Passenger {pid} has arrival_time < request_time ({arrival_time:.2f} < {request_time:.2f})")
                # Optional: Add warnings for passengers arriving with invalid time/priority
                # elif arrival_time < 0: self.add_error(f"WARN: Passenger {pid} arrived but arrival_time is invalid.")
                # elif request_time < 0: self.add_error(f"WARN: Passenger {pid} arrived but request_time is invalid.")
                # elif priority <= 0: self.add_error(f"WARN: Passenger {pid} arrived but priority is invalid ({priority}).")


        if total_priority > 0:
            return total_weighted_time / total_priority
        elif passengers_arrived > 0: # Arrived but total priority was 0? Return simple average.
             return total_weighted_time / passengers_arrived # This case implies weighted time is 0
        else: # No passengers arrived or valid data
            return 0.0 # Or perhaps None or -1 to indicate no data? Let's use 0.0

# --- Plotting Functions ---
def plot_metric(plot_data, data_files_sorted, y_label, title, output_filename):
    """Generic plotting function."""
    if not MATPLOTLIB_AVAILABLE:
        # Warning printed by plot_results caller
        return
    if not plot_data:
        # Warning printed by plot_results caller
        return

    print(f"Generating plot '{output_filename}'...")
    try:
        fig, ax = plt.subplots(figsize=(max(10, len(data_files_sorted) * 0.5), 6))
        x_labels = [os.path.splitext(df)[0] for df in data_files_sorted]
        x_indices = range(len(x_labels))
        jar_names = sorted(plot_data.keys())
        for jar_file in jar_names:
            jar_data = plot_data[jar_file]
            y_values = [jar_data.get(data_file) for data_file in data_files_sorted]
            ax.plot(x_indices, y_values, marker='o', linestyle='-', label=os.path.basename(jar_file))

        ax.set_xlabel("Test Case")
        ax.set_ylabel(y_label)
        ax.set_title(title)
        ax.set_xticks(x_indices)
        ax.set_xticklabels(x_labels, rotation=45, ha='right')
        ax.legend(title="JAR Files", bbox_to_anchor=(1.04, 1), loc="upper left")
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        ax.set_ylim(bottom=0) # Ensure y-axis starts at 0

        fig.tight_layout(rect=[0, 0, 0.85, 1])
        plt.savefig(output_filename, bbox_inches='tight')
        plt.close(fig)
        print(f"Plot '{output_filename}' saved successfully.")
    except Exception as plot_e:
        print(f"\nError generating plot '{output_filename}': {plot_e}", file=sys.stderr)
        print("Ensure matplotlib is installed and working correctly.", file=sys.stderr)

# --- Function Wrappers for Specific Plots ---
def plot_runtime_results(plot_data, data_files_sorted, output_filename=PLOT_FILENAME_RUNTIME):
    if not plot_data: print("\nWarning: No runtime data available to plot.", file=sys.stderr); return
    if not MATPLOTLIB_AVAILABLE: print("\nWarning: matplotlib not found. Skipping runtime plot.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted, "Completion Time (s)", "JAR Runtime Comparison (Successful Runs)", output_filename)

def plot_power_consumption(plot_data, data_files_sorted, output_filename=PLOT_FILENAME_POWER):
    if not plot_data: print("\nWarning: No power data available to plot.", file=sys.stderr); return
    if not MATPLOTLIB_AVAILABLE: print("\nWarning: matplotlib not found. Skipping power plot.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted, "Power Consumption (Units)", "JAR Power Consumption Comparison (Successful Runs)", output_filename)

def plot_weighted_avg_time(plot_data, data_files_sorted, output_filename=PLOT_FILENAME_AVGTIME):
    if not plot_data: print("\nWarning: No weighted time data available to plot.", file=sys.stderr); return
    if not MATPLOTLIB_AVAILABLE: print("\nWarning: matplotlib not found. Skipping weighted time plot.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted, "Weighted Avg Completion Time (s)", "JAR Weighted Avg Passenger Time (Successful Runs)", output_filename)


# --- Function to Run a Single Test Case ---
def run_single_test_case(jar_file, data_file, data_dir, out_dir):
    """
    Runs a single data file against a single jar file using the threaded runner.
    Returns a dictionary containing results for this test case, including new metrics.
    """
    data_file_path = os.path.join(data_dir, data_file)
    jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    data_file_base = os.path.splitext(data_file)[0]
    output_file_name = f"{jar_name_base}_{data_file_base}.txt"
    output_file_path = os.path.join(out_dir, output_file_name)

    errors = []
    stdout_data, stderr_data = "", ""
    execution_time, run_status_code = 0, None
    result_status = "CHECKER_ERROR" # Default
    # Initialize metrics
    final_sim_time = 0.0
    power_consumption = 0.0
    weighted_avg_time = 0.0

    try:
        try: # Read Input
            with open(data_file_path, 'r', encoding='utf-8', errors='replace') as f: input_str = f.read()
        except FileNotFoundError: raise FileNotFoundError(f"Input file not found: {data_file_path}") # Raise specific error
        except Exception as e: raise Exception(f"Error reading input {data_file_path}: {e}") # Raise other read errors

        # Run Java Program
        stdout_data, stderr_data, execution_time, run_status_code = run_java_program_with_threads(jar_file, input_str)

        # Save Output File
        try:
            with open(output_file_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(stdout_data);
                if stderr_data: f.write("\n\n--- STDERR ---\n" + stderr_data)
        except IOError as e: errors.append(f"Warning: Failed to write output file {output_file_path}: {e}")

        # Determine Initial Status & Validate
        initial_run_status = "UNKNOWN"
        # (Status determination logic remains the same)
        if run_status_code == "Killed": initial_run_status = "TIMEOUT_HARD"
        elif run_status_code == "TLE": initial_run_status = "TIMEOUT_SOFT"
        elif run_status_code == "ExecutionError": initial_run_status = "RUNTIME_ERROR"
        elif run_status_code == "JavaNotFound": initial_run_status = "JAVA_ERROR"
        elif run_status_code is None: initial_run_status = "OK"
        else: initial_run_status = "CHECKER_ERROR"; errors.append(f"Unknown run_status_code: {run_status_code}")

        if initial_run_status not in ["JAVA_ERROR", "CHECKER_ERROR"]:
            parsed_requests, parse_error = [], False
            input_lines = input_str.strip().split('\n')
            for line_num, line in enumerate(input_lines): # Parse Input with Priority
                 line = line.strip();
                 if not line: continue
                 match = RE_INPUT.match(line) # Regex now captures priority
                 if match:
                     time_f, pid_s, pri_s, from_s, to_s, by_s = match.groups() # Get priority
                     from_i, to_i = floor_to_int(from_s), floor_to_int(to_s)
                     if from_i is None or to_i is None: errors.append(f"Input Error (L{line_num+1}): Invalid floor."); parse_error = True; break
                     try: parsed_requests.append({'time': float(time_f), 'id': int(pid_s), 'pri': int(pri_s), 'from': from_i, 'to': to_i, 'by': int(by_s)}) # Store priority
                     except ValueError as ve: errors.append(f"Input Error (L{line_num+1}): Invalid number: {ve}"); parse_error = True; break
                 else: errors.append(f"Input Error (L{line_num+1}): Malformed request."); parse_error = True; break

            if parse_error: result_status = "INPUT_ERROR"
            else: # Run Validation
                if not stdout_data.strip():
                     if initial_run_status == "OK": errors.append("Validation Error: No output produced."); result_status = "WRONG_ANSWER"
                     else: result_status = initial_run_status; errors.append("INFO: No output.") if initial_run_status in ["TIMEOUT_SOFT", "RUNTIME_ERROR"] else None
                else:
                     validator = Validator(parsed_requests)
                     validation_stopped = False
                     output_lines = stdout_data.strip().split('\n')
                     for line_no, output_line in enumerate(output_lines):
                         if not validator.validate_line(output_line): validation_stopped = True; break
                     if not validation_stopped: validator.final_checks()
                     validation_errors = validator.get_errors()
                     # --- Get metrics from validator ---
                     final_sim_time = validator.get_final_sim_time()
                     power_consumption = validator.get_power_consumption()
                     weighted_avg_time = validator.get_weighted_average_completion_time()
                     # ---

                     if validation_errors:
                         errors.extend(validation_errors)
                         if initial_run_status == "OK": result_status = "WRONG_ANSWER"; result_status = "VALIDATION_ERROR" if validation_stopped else result_status
                         else: result_status = initial_run_status
                     elif initial_run_status == "OK": result_status = "PASSED"
                     else: result_status = initial_run_status
        else: # Java Error or Checker Error from run
             result_status = initial_run_status
             if result_status == "JAVA_ERROR" and not any("Java command not found" in e for e in errors): errors.append("Execution Failed: Java command not found.")

    except FileNotFoundError as e: errors.append(f"Checker Error: {e}"); result_status = "CHECKER_ERROR" # Catch specific input file not found
    except MemoryError: errors.append(f"Checker Error: Out of memory."); result_status = "CHECKER_ERROR"
    except Exception as e: errors.append(f"Checker Error during processing for {data_file}: {e}"); errors.append(traceback.format_exc(limit=5)); result_status = "CHECKER_ERROR"

    # Add run status errors if not already added by specific logic
    if result_status == "TIMEOUT_HARD" and not any("Hard timeout" in e for e in errors): errors.append(f"Execution Failed: Hard timeout ({HARD_TIMEOUT}s).")
    if result_status == "TIMEOUT_SOFT" and not any("Soft timeout" in e for e in errors): errors.append(f"Execution Warning: Soft timeout ({SOFT_TIMEOUT}s).")
    if result_status == "RUNTIME_ERROR" and not any("Execution Failed" in e for e in errors): errors.append(f"Execution Failed (Non-zero exit/error).")
    if result_status == "CHECKER_ERROR" and not errors: errors.append("Checker Error: Final status undetermined.")

    # Return extended results dictionary
    return {
        "data_file": data_file,
        "status": result_status,
        "sim_time": final_sim_time, # Sim time (last timestamp)
        "exec_time": execution_time, # Wall clock time
        "power": power_consumption, # Added metric
        "avg_time": weighted_avg_time, # Added metric
        "errors": errors,
    }

# --- Function to Test a Single JAR (for jar parallel mode) ---
def test_single_jar(jar_file, all_data_files, data_dir, out_dir, report_dir):
    """
    Tests a single JAR file against all data files sequentially using run_single_test_case.
    Writes the report file for this JAR.
    Returns a tuple: (jar_file, passed_count, total_count, jar_plot_data_runtime, jar_plot_data_power, jar_plot_data_avgtime).
    """
    jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    report_lines = []
    passed_tests = 0
    failed_tests = 0
    total_tests = len(all_data_files)
    # Dictionaries to collect plot data for this specific JAR
    jar_plot_data_runtime = {}
    jar_plot_data_power = {}
    jar_plot_data_avgtime = {}

    print(f"Starting tests for {jar_file}...")

    for i, data_file in enumerate(all_data_files): # Already sorted
        result = run_single_test_case(jar_file, data_file, data_dir, out_dir)
        result_status = result["status"]
        # Use sim_time for report if passed, otherwise exec_time
        report_time = result["sim_time"] if result_status == "PASSED" else result["exec_time"]

        report_lines.append(f"{result['data_file']}: {result_status} ({report_time:.2f}s)")
        if result_status == "PASSED":
            passed_tests += 1
            # Collect all metrics for plotting
            jar_plot_data_runtime[data_file] = result["sim_time"]
            jar_plot_data_power[data_file] = result["power"]
            jar_plot_data_avgtime[data_file] = result["avg_time"]
        else:
            failed_tests += 1
            for err_msg in result['errors']: report_lines.append(f"    - {err_msg}")

        if result_status == "JAVA_ERROR":
             print(f"Java not found for {jar_file}, aborting its remaining tests.", file=sys.stderr)
             failed_tests += (total_tests - (i + 1)); break

    # Write the report
    report_file_path = os.path.join(report_dir, f"{jar_name_base}.report")
    try:
        with open(report_file_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(f"Report for: {jar_file}\nOverall: {passed_tests}/{total_tests} passed ({failed_tests} failed).\n{'=' * 20}\n")
            for line in report_lines: f.write(line + "\n")
        print(f"Finished tests for {jar_file}. Report saved to '{report_file_path}'")
    except IOError as e: print(f"Error writing report file '{report_file_path}' for {jar_file}: {e}", file=sys.stderr)

    # Return collected data including plot points
    return (jar_file, passed_tests, total_tests,
            jar_plot_data_runtime, jar_plot_data_power, jar_plot_data_avgtime)


# --- Main Execution Logic ---
def main():
    print("Elevator Simulation Checker"); print("-" * 30)
    for dir_path in [DATA_DIR, OUT_DIR, REPORT_DIR]:
        try: os.makedirs(dir_path, exist_ok=True)
        except OSError as e: print(f"Error creating directory {dir_path}: {e}", file=sys.stderr); sys.exit(1)

    # --- Generator Logic ---
    # (Generator logic unchanged)
    use_generator = False
    while True:
        try: choice = input(f"Generate new data using {GENERATOR_SCRIPT}? (y/n): ").lower().strip()
        except EOFError: print("\nNo input, assuming 'n'."); choice = 'n'
        if choice == 'y': use_generator = True; break
        elif choice == 'n': break
        else: print("Invalid input.")
    if use_generator:
        if not os.path.isfile(GENERATOR_SCRIPT): print(f"\nError: Generator script '{GENERATOR_SCRIPT}' not found.", file=sys.stderr); sys.exit(1)
        print(f"\nClearing directory '{DATA_DIR}'..."); clear_directory(DATA_DIR)
        print(f"Running data generator '{GENERATOR_SCRIPT}'...")
        try:
            print(f"--- Please provide input for {GENERATOR_SCRIPT} if prompted ---")
            gen_process = subprocess.run([sys.executable, GENERATOR_SCRIPT], text=True, encoding='utf-8', errors='replace', check=False)
            print(f"--- {GENERATOR_SCRIPT} finished ---")
            if gen_process.returncode != 0: print(f"\nError: Generator failed (exit code {gen_process.returncode}).", file=sys.stderr); sys.exit(1)
            if not find_files(DATA_DIR, ".txt"): print(f"\nWarning: Generator ran but no '.txt' files found in '{DATA_DIR}'.", file=sys.stderr); sys.exit(1)
            print("Data generation complete.")
        except Exception as e: print(f"\nError running generator: {e}", file=sys.stderr); sys.exit(1)

    # --- File Discovery ---
    jar_files = find_files(".", ".jar") # Sorted
    try: data_files = find_files(DATA_DIR, ".txt") # Sorted
    except FileNotFoundError: print(f"Error: Data directory '{DATA_DIR}' not found.", file=sys.stderr); sys.exit(1)
    if not jar_files: print("Error: No .jar files found.", file=sys.stderr); sys.exit(1)
    if not data_files: print(f"Error: No .txt data files found in '{DATA_DIR}'.", file=sys.stderr); sys.exit(1)
    print(f"\nFound {len(jar_files)} JAR file(s): {', '.join(jar_files)}")
    print(f"Found {len(data_files)} test case(s) in '{DATA_DIR}': {', '.join(data_files)}")

    # --- Data Structures for Plotting ---
    plot_data_runtime = defaultdict(dict)
    plot_data_power = defaultdict(dict)
    plot_data_avgtime = defaultdict(dict)

    # --- Select Execution Mode ---
    print(f"Using parallel mode: '{PARALLEL_MODE}' with max workers: {MAX_WORKERS}")
    overall_summary = {} # {jar: (passed, total)}

    if PARALLEL_MODE == 'none':
        # --- Sequential Execution ---
        print("\nRunning tests sequentially...")
        for jar_file in jar_files:
            print("\n" + "=" * 30); print(f"Testing {jar_file}..."); print("=" * 30)
            jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
            report_lines, passed_tests, failed_tests = [], 0, 0
            total_tests = len(data_files)
            # Dictionaries to hold plot data for this jar run
            current_jar_plot_runtime = {}
            current_jar_plot_power = {}
            current_jar_plot_avgtime = {}

            for i, data_file in enumerate(data_files):
                print(f"Running {data_file} ({i + 1}/{total_tests})...")
                result = run_single_test_case(jar_file, data_file, DATA_DIR, OUT_DIR)
                result_status = result["status"]
                report_time = result["sim_time"] if result_status == "PASSED" else result["exec_time"]
                errors = result["errors"]

                report_lines.append(f"{data_file}: {result_status} ({report_time:.2f}s)")
                if result_status == "PASSED":
                    passed_tests += 1
                    # Store metrics for plotting
                    current_jar_plot_runtime[data_file] = result["sim_time"]
                    current_jar_plot_power[data_file] = result["power"]
                    current_jar_plot_avgtime[data_file] = result["avg_time"]
                else:
                    failed_tests += 1
                    if result_status != "JAVA_ERROR": print(f"Failed: {data_file} - {result_status} ({report_time:.2f}s)")
                    for err_idx, err_msg in enumerate(errors):
                         if result_status != "JAVA_ERROR" and err_idx < 5:
                              console_err_msg = err_msg.replace('\n', ' '); print(f"  - {console_err_msg[:150]}{'...' if len(console_err_msg) > 150 else ''}")
                         report_lines.append(f"    - {err_msg}")
                    if result_status != "JAVA_ERROR" and len(errors) > 5: print(f"  - ... ({len(errors) - 5} more issues)"); report_lines.append(f"    - ... ({len(errors) - 5} more issues)")
                    if result_status == "JAVA_ERROR": print(f"\nError: Java not found. Aborting tests for {jar_file}.", file=sys.stderr); failed_tests += (total_tests - (i + 1)); break

            # End of tests for one JAR (Sequential)
            print("-" * 30); summary_line = f"Finished testing {jar_file}. Results: {passed_tests}/{total_tests} passed"
            if failed_tests > 0: summary_line += f", {failed_tests} failed"; print(summary_line)
            overall_summary[jar_file] = (passed_tests, total_tests)
            # Add collected plot data to the main dictionaries
            if current_jar_plot_runtime: plot_data_runtime[jar_file] = current_jar_plot_runtime
            if current_jar_plot_power: plot_data_power[jar_file] = current_jar_plot_power
            if current_jar_plot_avgtime: plot_data_avgtime[jar_file] = current_jar_plot_avgtime
            report_file_path = os.path.join(REPORT_DIR, f"{jar_name_base}.report")
            try: # Write report
                with open(report_file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"Report for: {jar_file}\nOverall: {passed_tests}/{total_tests} passed ({failed_tests} failed).\n{'=' * 20}\n"); [f.write(line + "\n") for line in report_lines]
                print(f"Report saved to '{report_file_path}'")
            except IOError as e: print(f"Error writing report file '{report_file_path}': {e}", file=sys.stderr)

    elif PARALLEL_MODE == 'data':
        # --- Parallel Data Points per JAR ---
        print(f"\nRunning tests in parallel ('data' mode, max_workers={MAX_WORKERS})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for jar_file in jar_files:
                print("\n" + "=" * 30); print(f"Submitting tests for {jar_file}..."); print("=" * 30)
                jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
                report_map = {} # Store results {data_file: result_dict}
                passed_tests, failed_tests, total_tests = 0, 0, len(data_files)
                futures_map = {executor.submit(run_single_test_case, jar_file, df, DATA_DIR, OUT_DIR): df for df in data_files}
                jar_plot_runtime, jar_plot_power, jar_plot_avgtime = {}, {}, {}
                java_error_encountered = False

                print(f"All {total_tests} tests for {jar_file} submitted, processing results...")
                for future in concurrent.futures.as_completed(futures_map):
                    data_file = futures_map[future]
                    try:
                        result = future.result(); report_map[data_file] = result
                        result_status = result['status']
                        report_time = result["sim_time"] if result_status == "PASSED" else result["exec_time"]

                        if result_status == "PASSED":
                            passed_tests += 1
                            jar_plot_runtime[data_file] = result["sim_time"]
                            jar_plot_power[data_file] = result["power"]
                            jar_plot_avgtime[data_file] = result["avg_time"]
                        else:
                            failed_tests += 1
                            print(f"Failed: {data_file} (for {jar_file}) - {result_status} ({report_time:.2f}s)")
                            for err_idx, err_msg in enumerate(result['errors']):
                                if err_idx < 5: console_err_msg = err_msg.replace('\n', ' '); print(f"  - {console_err_msg[:150]}{'...' if len(console_err_msg) > 150 else ''}")
                            if len(result['errors']) > 5: print(f"  - ... ({len(result['errors']) - 5} more issues)")
                            if result_status == "JAVA_ERROR": java_error_encountered = True
                    except Exception as exc: print(f"Error processing result for {data_file} (JAR: {jar_file}): {exc}", file=sys.stderr); report_map[data_file] = {"data_file": data_file, "status": "CHECKER_ERROR", "sim_time": 0, "exec_time": 0, "power": 0, "avg_time": 0, "errors": [f"Exception: {exc}"]}; failed_tests += 1

                # End of tests for one JAR (Data Parallel)
                print("-" * 30); summary_line = f"Finished testing {jar_file}. Results: {passed_tests}/{total_tests} passed";
                if failed_tests > 0: summary_line += f", {failed_tests} failed"; print(summary_line)
                overall_summary[jar_file] = (passed_tests, total_tests)
                if jar_plot_runtime: plot_data_runtime[jar_file] = jar_plot_runtime
                if jar_plot_power: plot_data_power[jar_file] = jar_plot_power
                if jar_plot_avgtime: plot_data_avgtime[jar_file] = jar_plot_avgtime

                # Write Report (Ordered)
                report_file_path = os.path.join(REPORT_DIR, f"{jar_name_base}.report")
                try:
                    with open(report_file_path, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(f"Report for: {jar_file}\nOverall: {passed_tests}/{total_tests} passed ({failed_tests} failed).\n{'=' * 20}\n")
                        for df in data_files:
                             result = report_map.get(df)
                             if result: report_time = result["sim_time"] if result['status'] == "PASSED" else result["exec_time"]; f.write(f"{df}: {result['status']} ({report_time:.2f}s)\n"); [f.write(f"    - {err}\n") for err in result['errors'] if result['status'] != "PASSED"]
                             else: f.write(f"{df}: RESULT_MISSING\n")
                    print(f"Report saved to '{report_file_path}'")
                except IOError as e: print(f"Error writing report file '{report_file_path}': {e}", file=sys.stderr)
                if java_error_encountered: print(f"Warning: JAVA_ERROR encountered during tests for {jar_file}.", file=sys.stderr)

    elif PARALLEL_MODE == 'jar':
        # --- Parallel JARs ---
        print(f"\nRunning tests in parallel ('jar' mode, max_workers={MAX_WORKERS})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            jar_futures = {executor.submit(test_single_jar, jar, data_files, DATA_DIR, OUT_DIR, REPORT_DIR): jar for jar in jar_files}
            print(f"All {len(jar_files)} JAR test suites submitted, waiting for completion...")

            for future in concurrent.futures.as_completed(jar_futures):
                jar_file_completed = jar_futures[future]
                try:
                    _jar, passed, total, jr, jp, jt = future.result() # Unpack results including plot data
                    overall_summary[jar_file_completed] = (passed, total)
                    if jr: plot_data_runtime[jar_file_completed] = jr # Merge plot data
                    if jp: plot_data_power[jar_file_completed] = jp
                    if jt: plot_data_avgtime[jar_file_completed] = jt
                except Exception as exc: print(f"\nCRITICAL Error running test suite for JAR '{jar_file_completed}': {exc}", file=sys.stderr); print(traceback.format_exc(), file=sys.stderr); overall_summary[jar_file_completed] = (0, len(data_files))

    else: # Invalid Mode
        print(f"Error: Unknown PARALLEL_MODE '{PARALLEL_MODE}'. Use 'none', 'data', or 'jar'.", file=sys.stderr); sys.exit(1)

    # --- Final Summary & Plotting ---
    print("\n" + "=" * 30); print("Overall Summary:"); print("=" * 30)
    if overall_summary: [print(f"- {jar}: {passed}/{total} passed") for jar, (passed, total) in sorted(overall_summary.items())]
    else: print("No JAR files were tested (or mode was invalid).")
    print("\n" + "=" * 30)
    # Generate all plots using the collected data
    plot_runtime_results(plot_data_runtime, data_files)
    plot_power_consumption(plot_data_power, data_files)
    plot_weighted_avg_time(plot_data_avgtime, data_files)
    print("All tests complete."); print("=" * 30)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n\nExecution interrupted.", file=sys.stderr); sys.exit(1)
    except Exception as main_exc: print(f"\n\nChecker script error: {main_exc}", file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)