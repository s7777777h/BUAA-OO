# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import re
import shutil
import time
import numpy as np # Keep numpy import
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
DATA_DIR = "data"; OUT_DIR = "out"; LOG_DIR = "log"; REPORT_DIR = "report"
PLOT_FILENAME_RUNTIME = "runtime_comparison.png"; PLOT_FILENAME_POWER = "power_consumption.png"
PLOT_FILENAME_AVGTIME = "weighted_avg_time.png"; PLOT_FILENAME_TOTALSCORE = "total_score_comparison.png"
GENERATOR_SCRIPT = "data_generator.py" # Assumes HW7 generator has the same name
# --- HW7 Specific Config ---
SOFT_TIMEOUT = 220.0; HARD_TIMEOUT = 250.0; # Confirm if HW7 changed these
DEFAULT_MOVE_TIME_PER_FLOOR = 0.4; DOOR_OPEN_CLOSE_TIME = 0.4
SCHE_STOP_TIME = 1.0; UPDATE_PROCESS_TIME = 1.0; DOUBLE_CAR_SPEED = 0.2 # New HW7 speed
ELEVATOR_CAPACITY = 6; NUM_ELEVATORS = 6; EPSILON = 1e-9; POLL_INTERVAL = 0.1
# --- Power Calculation Constants ---
POWER_OPEN = 0.1; POWER_CLOSE = 0.1; POWER_MOVE = 0.4
# --- Parallelism Configuration ---
PARALLEL_MODE = 'data'; DEFAULT_WORKERS=8; MAX_WORKERS=DEFAULT_WORKERS
try: DEFAULT_WORKERS = min(32, (os.cpu_count() or 1) + 4); MAX_WORKERS = DEFAULT_WORKERS
except AttributeError: pass
# --- Floor definitions ---
FLOOR_MAP_STR_TO_INT = {"B4":-4,"B3":-3,"B2":-2,"B1":-1,"F1":1,"F2":2,"F3":3,"F4":4,"F5":5,"F6":6,"F7":7}
FLOOR_MAP_INT_TO_STR = {v: k for k, v in FLOOR_MAP_STR_TO_INT.items()}
VALID_FLOORS_INT = set(FLOOR_MAP_STR_TO_INT.values())
MIN_FLOOR_INT, MAX_FLOOR_INT = -4, 7
# --- Regular Expressions ---
RE_TIMESTAMP = re.compile(r"\[\s*([\d.]+)\s*\]")
# Inputs
RE_INPUT_PASSENGER = re.compile(r"\[\s*([\d.]+)\s*\](\d+)-PRI-(\d+)-FROM-([BF]\d+)-TO-([BF]\d+)")
RE_INPUT_SCHE = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-(\d+)-([\d.]+)-([BF]\d+)")
RE_INPUT_UPDATE = re.compile(r"\[\s*([\d.]+)\s*\]UPDATE-(\d+)-(\d+)-([BF]\d+)")
# Outputs
RE_ARRIVE = re.compile(r"\[\s*([\d.]+)\s*\]ARRIVE-([BF]\d+)-(\d+)"); RE_OPEN = re.compile(r"\[\s*([\d.]+)\s*\]OPEN-([BF]\d+)-(\d+)"); RE_CLOSE = re.compile(r"\[\s*([\d.]+)\s*\]CLOSE-([BF]\d+)-(\d+)")
RE_IN = re.compile(r"\[\s*([\d.]+)\s*\]IN-(\d+)-([BF]\d+)-(\d+)"); RE_OUT = re.compile(r"\[\s*([\d.]+)\s*\]OUT-([SF])-(\d+)-([BF]\d+)-(\d+)")
RE_RECEIVE = re.compile(r"\[\s*([\d.]+)\s*\]RECEIVE-(\d+)-(\d+)");
RE_SCHE_BEGIN = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-BEGIN-(\d+)"); RE_SCHE_END = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-END-(\d+)")
RE_SCHE_ACCEPT = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-ACCEPT-(\d+)-([\d.]+)-([BF]\d+)")
RE_UPDATE_ACCEPT = re.compile(r"\[\s*([\d.]+)\s*\]UPDATE-ACCEPT-(\d+)-(\d+)-([BF]\d+)")
RE_UPDATE_BEGIN = re.compile(r"\[\s*([\d.]+)\s*\]UPDATE-BEGIN-(\d+)-(\d+)")
RE_UPDATE_END = re.compile(r"\[\s*([\d.]+)\s*\]UPDATE-END-(\d+)-(\d+)")
RE_LOG_LINE = re.compile(r"\[LOG\]")

# --- Helper Functions ---
def floor_to_int(floor_str): return FLOOR_MAP_STR_TO_INT.get(floor_str)
def int_to_floor(floor_int):
    if floor_int is None or floor_int not in FLOOR_MAP_INT_TO_STR: return f"InvalidFloor({floor_int})"
    return FLOOR_MAP_INT_TO_STR.get(floor_int)
def floor_diff(f1_int, f2_int):
    if f1_int is None or f2_int is None: return float('inf')
    return abs(f1_int - f2_int)
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

# --- Runner Function --- (Kept original, robust version)
def stream_reader_thread(stream_pipe, output_buffer, buffer_lock):
    try:
        for chunk in iter(lambda: stream_pipe.read(8192), ''):
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

        try:
            if input_data_str: process.stdin.write(input_data_str)
            process.stdin.close()
        except (BrokenPipeError, OSError) as e:
            status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Error sending input (process likely terminated): {e}."

        process_terminated_normally = False
        if status_code != "ExecutionError":
            while True:
                current_time = time.monotonic()
                elapsed_time = current_time - start_time
                if elapsed_time > HARD_TIMEOUT:
                    if status_code != "Killed": status_code = "Killed"; full_stderr_str += f"\nChecker: Hard timeout exceeded ({HARD_TIMEOUT:.1f}s)."
                    try: process.kill()
                    except Exception: pass
                    break
                exit_code = process.poll()
                if exit_code is not None:
                    process_terminated_normally = True
                    if status_code not in ["Killed", "TLE"]: status_code = "ExecutionError" if exit_code != 0 else None
                    break
                if not tle_marked and elapsed_time > SOFT_TIMEOUT:
                    if status_code != "Killed": status_code = "TLE"; full_stderr_str += f"\nChecker: Soft timeout exceeded ({SOFT_TIMEOUT:.1f}s)."
                    tle_marked = True
                time.sleep(POLL_INTERVAL)

        if not process_terminated_normally and process.poll() is None:
            remaining_time = max(0.1, HARD_TIMEOUT - (time.monotonic() - start_time) + 2.0)
            try: process.wait(timeout=remaining_time)
            except subprocess.TimeoutExpired:
                 if status_code != "Killed": status_code = "Killed"; full_stderr_str += "\nChecker: Process wait() timed out."
                 try: process.kill()
                 except Exception: pass
            except Exception as wait_e:
                 full_stderr_str += f"\nChecker: Error during wait(): {wait_e}"
                 if status_code not in ["Killed", "TLE", "ExecutionError"]: status_code = "ExecutionError"

        thread_join_timeout = 5.0
        stdout_thread.join(timeout=thread_join_timeout)
        stderr_thread.join(timeout=thread_join_timeout)
        if stdout_thread.is_alive() or stderr_thread.is_alive(): full_stderr_str += "\nChecker: Warning - reader threads did not exit cleanly."

        with stdout_lock: full_stdout = "".join(stdout_buffer)
        with stderr_lock: full_stderr_str += "".join(stderr_buffer)

        final_exit_code = process.poll()
        if status_code not in ["Killed", "TLE", "ExecutionError", "JavaNotFound"]:
             if final_exit_code is None: status_code = "ExecutionError"; full_stderr_str += "\nChecker: Process poll() is None."
             elif final_exit_code != 0: status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Non-zero exit code: {final_exit_code}."
        elif status_code is None and final_exit_code != 0: status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Non-zero exit code: {final_exit_code} (updated)."

    except FileNotFoundError:
        exec_time = time.monotonic() - start_time if 'start_time' in locals() else 0.0
        return "", f"Error: 'java' command not found.", exec_time, "JavaNotFound"
    except Exception as popen_e:
        exec_time = time.monotonic() - start_time if 'start_time' in locals() else 0.0
        return "", f"Error starting JAR {jar_file}: {popen_e}", exec_time, "ExecutionError"
    finally:
        if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=0.5)
        if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=0.5)
        if process and process.poll() is None:
            try: process.kill(); process.wait(timeout=0.5)
            except Exception: pass

    end_time = time.monotonic()
    execution_time = end_time - start_time
    return full_stdout, full_stderr_str.strip(), execution_time, status_code


# --- Constants dependent on helper functions ---
F1_INT = floor_to_int('F1'); B1_INT = floor_to_int('B1')
VALID_SCHE_UPDATE_FLOORS_INT = {floor_to_int(f) for f in ["B2", "B1", "F1", "F2", "F3", "F4", "F5"]}
VALID_SCHE_SPEEDS = {0.2, 0.3, 0.4, 0.5}

# --- Validation Logic ---
class Validator:
    # --- __init__ (No change needed) ---
    def __init__(self, all_input_requests):
        self.errors = []
        self.all_inputs = all_input_requests
        self.passenger_requests_dict = {req['id']: req for req in all_input_requests if req['type'] == 'passenger'}
        self.sim_time = 0.0
        self.elevators = {}
        self.passengers = {}
        self.active_passenger_assignments = {}
        self.open_count = 0; self.close_count = 0; self.move_count = 0
        for i in range(1, NUM_ELEVATORS + 1):
            self.elevators[i] = {
                'id': i, 'floor': F1_INT, 'state': 'CLOSED', 'passengers': set(),
                'last_action_time': 0.0, 'last_arrive_time': 0.0, 'open_time': -1.0,
                'current_speed': DEFAULT_MOVE_TIME_PER_FLOOR,
                'min_floor': MIN_FLOOR_INT, 'max_floor': MAX_FLOOR_INT,
                'active_receives': set(),
                'sche_state': 'IDLE', 'sche_target_floor': None, 'sche_speed_override': None,
                'sche_begin_time': -1.0, 'sche_accept_time': -1.0,
                'update_state': 'IDLE', 'update_partner_id': None, 'update_transfer_floor': None,
                'update_accept_time': -1.0, 'update_begin_time': -1.0,
                'pending_update_request': None, 'initial_post_update_move_allowed': False
            }
        for req in self.passenger_requests_dict.values():
            pid = req['id']
            self.passengers[pid] = {
                'id': pid,'state': 'OUTSIDE', 'location': req['from'], 'destination': req['to'],
                'request_time': req['time'], 'priority': req['pri'],'arrival_time': -1.0,
                'current_assignment': None,'needs_pickup': False
            }

    def add_error(self, message):
        error_time_str = f"{max(0.0, self.sim_time):.4f}" if isinstance(self.sim_time, (int, float)) else "?.????"
        self.errors.append(f"[Time ~{error_time_str}] {message}")
    def _get_elevator_state(self, eid):
        if eid not in self.elevators: self.add_error(f"CRITICAL: Invalid Elevator ID {eid}"); return None
        return self.elevators[eid]
    def _get_passenger_state(self, pid):
        if pid not in self.passengers: self.add_error(f"CRITICAL: Invalid Passenger ID {pid}"); return None
        return self.passengers[pid]
    def _cancel_external_receives_for_elevator(self, eid):
        e_state = self._get_elevator_state(eid)
        if not e_state: return
        receives_to_cancel = list(e_state['active_receives'])
        for received_pid in receives_to_cancel:
            rcv_p_state = self._get_passenger_state(received_pid)
            if rcv_p_state and rcv_p_state['state'] in ['OUTSIDE', 'NEEDS_PICKUP'] and self.active_passenger_assignments.get(received_pid) == eid:
                if received_pid in e_state['active_receives']: e_state['active_receives'].remove(received_pid)
                if self.active_passenger_assignments.get(received_pid) == eid: del self.active_passenger_assignments[received_pid]
                if rcv_p_state['current_assignment'] == eid: rcv_p_state['current_assignment'] = None

    # --- validate_line --- MODIFIED IN CHECK ---
    def validate_line(self, line):
        line = line.strip();
        if not line: return True
        match_ts = RE_TIMESTAMP.match(line)
        if not match_ts: self.add_error(f"CRITICAL: Malformed line (no timestamp): {line}"); return False
        try: current_line_time = float(match_ts.group(1))
        except ValueError: self.add_error(f"CRITICAL: Malformed timestamp: {match_ts.group(1)}"); return False
        if current_line_time < 0: self.add_error(f"CRITICAL: Negative timestamp: {current_line_time}"); return False
        if current_line_time < self.sim_time - EPSILON * 100: self.add_error(f"Timestamp decreasing: {current_line_time:.4f} < {self.sim_time:.4f}")
        self.sim_time = max(self.sim_time, current_line_time)

        match_arrive=RE_ARRIVE.match(line); match_open=RE_OPEN.match(line); match_close=RE_CLOSE.match(line)
        match_in=RE_IN.match(line); match_out=RE_OUT.match(line); match_receive=RE_RECEIVE.match(line)
        match_sche_begin=RE_SCHE_BEGIN.match(line); match_sche_end=RE_SCHE_END.match(line); match_sche_accept=RE_SCHE_ACCEPT.match(line)
        match_update_accept=RE_UPDATE_ACCEPT.match(line); match_update_begin=RE_UPDATE_BEGIN.match(line); match_update_end=RE_UPDATE_END.match(line)

        try:
            # ARRIVE
            if match_arrive:
                _, floor_str, eid_str = match_arrive.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"ARRIVE Invalid (eid {eid_str} /floor {floor_str}): {line}"); return True
                if e_state['update_state'] == 'UPDATING': self.add_error(f"ARRIVE-{floor_str}-{eid}: Cannot move during UPDATE state."); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"ARRIVE-{floor_str}-{eid}: Door not CLOSED.")
                prev_floor = e_state['floor']
                if not (e_state['min_floor'] <= floor_int <= e_state['max_floor']): self.add_error(f"ARRIVE-{floor_str}-{eid}: Arrived outside valid range [{int_to_floor(e_state['min_floor'])}-{int_to_floor(e_state['max_floor'])}].")
                is_f1_b1_move = (prev_floor == F1_INT and floor_int == B1_INT) or (prev_floor == B1_INT and floor_int == F1_INT)
                is_normal_step = (not is_f1_b1_move) and (floor_diff(floor_int, prev_floor) == 1)
                is_valid_step = is_f1_b1_move or is_normal_step
                if not is_valid_step: self.add_error(f"ARRIVE-{floor_str}-{eid}: Invalid move step from {int_to_floor(prev_floor)} to {floor_str}.")
                current_move_time = e_state['sche_speed_override'] if e_state['sche_state'] == 'ACTIVE' else e_state['current_speed']
                exp_t = e_state['last_action_time'] + current_move_time
                if current_line_time < exp_t - EPSILON: self.add_error(f"ARRIVE-{floor_str}-{eid}: Move too fast (arrived {current_line_time:.4f}, expected >= {exp_t:.4f}, speed {current_move_time:.1f}s/f).")
                has_passengers = bool(e_state['passengers']); has_receives = bool(e_state['active_receives']); is_sche_active = (e_state['sche_state'] == 'ACTIVE')
                is_first_post_update_move = e_state['initial_post_update_move_allowed']
                is_double_car_leaving_transfer = (e_state['update_state'] in ['DOUBLE_CAR_A', 'DOUBLE_CAR_B'] and prev_floor == e_state['update_transfer_floor'] and e_state['update_transfer_floor'] is not None)
                can_move_idle = (has_passengers or has_receives or is_sche_active or is_first_post_update_move or is_double_car_leaving_transfer)
                if not can_move_idle: self.add_error(f"ARRIVE-{floor_str}-{eid}: Idle move (no passengers/receives, not SCHE, not initial UPDATE move, not double car leaving transfer floor).")
                partner_id = e_state['update_partner_id']
                if partner_id is not None:
                    partner_e_state = self._get_elevator_state(partner_id)
                    if partner_e_state:
                        if floor_int == partner_e_state['floor']:
                             if abs(current_line_time - partner_e_state.get('last_arrive_time', -1.0)) < EPSILON: self.add_error(f"ARRIVE-{floor_str}-{eid}: Collision risk! Arrived same floor ({floor_str}) simultaneously with partner {partner_id}.")
                             elif partner_e_state['state'] != 'CLOSED': self.add_error(f"ARRIVE-{floor_str}-{eid}: Collision risk! Arrived same floor ({floor_str}) where partner {partner_id} is stopped/open.")
                        is_A = e_state['update_state'] == 'DOUBLE_CAR_A'; is_B = e_state['update_state'] == 'DOUBLE_CAR_B'
                        partner_is_A = partner_e_state['update_state'] == 'DOUBLE_CAR_A'; partner_is_B = partner_e_state['update_state'] == 'DOUBLE_CAR_B'
                        if is_A and partner_is_B and floor_int < partner_e_state['floor']: self.add_error(f"ARRIVE-{floor_str}-{eid}: Double car order violation! Car A ({eid} @{floor_str}) below Car B ({partner_id} @{int_to_floor(partner_e_state['floor'])}).")
                        elif is_B and partner_is_A and floor_int > partner_e_state['floor']: self.add_error(f"ARRIVE-{floor_str}-{eid}: Double car order violation! Car B ({eid} @{floor_str}) above Car A ({partner_id} @{int_to_floor(partner_e_state['floor'])}).")
                e_state['floor'] = floor_int; e_state['last_action_time'] = current_line_time; e_state['last_arrive_time'] = current_line_time
                if e_state['initial_post_update_move_allowed'] and is_valid_step: e_state['initial_post_update_move_allowed'] = False
                self.move_count += 1

            # OPEN
            elif match_open:
                _, floor_str, eid_str = match_open.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"OPEN Invalid (eid/floor): {line}"); return True
                if e_state['update_state'] == 'UPDATING': self.add_error(f"OPEN-{floor_str}-{eid}: Cannot open during UPDATE state."); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"OPEN-{floor_str}-{eid}: Door not CLOSED.")
                if e_state['floor'] != floor_int: self.add_error(f"OPEN-{floor_str}-{eid}: Wrong floor (at {int_to_floor(e_state['floor'])}).")
                if not (e_state['min_floor'] <= floor_int <= e_state['max_floor']): self.add_error(f"OPEN-{floor_str}-{eid}: Opened outside valid range [{int_to_floor(e_state['min_floor'])}-{int_to_floor(e_state['max_floor'])}].")
                if e_state['sche_state'] == 'ACTIVE':
                    if floor_int != e_state['sche_target_floor']: self.add_error(f"OPEN-{floor_str}-{eid}: Cannot OPEN during SCHE before target ({int_to_floor(e_state['sche_target_floor'])}).")
                    else: e_state['sche_state'] = 'OPEN_SCHE_TARGET'
                elif e_state['sche_state'] != 'IDLE': self.add_error(f"OPEN-{floor_str}-{eid}: Invalid OPEN during SCHE state {e_state['sche_state']}.")
                e_state['state'] = 'OPEN'; e_state['open_time'] = current_line_time; e_state['last_action_time'] = current_line_time; self.open_count += 1

            # CLOSE
            elif match_close:
                _, floor_str, eid_str = match_close.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"CLOSE Invalid (eid/floor): {line}"); return True
                if e_state['update_state'] == 'UPDATING': self.add_error(f"CLOSE-{floor_str}-{eid}: Cannot close during UPDATE state."); return True
                if e_state['state'] != 'OPEN': self.add_error(f"CLOSE-{floor_str}-{eid}: Door not OPEN.")
                if e_state['floor'] != floor_int: self.add_error(f"CLOSE-{floor_str}-{eid}: Wrong floor (at {int_to_floor(e_state['floor'])}).")
                min_dur = DOOR_OPEN_CLOSE_TIME; is_sche_close = False; open_time = e_state.get('open_time', -1.0)
                if open_time < 0 : self.add_error(f"CLOSE-{floor_str}-{eid}: Internal Error - open_time not recorded.");
                if e_state['sche_state'] == 'OPEN_SCHE_TARGET':
                    min_dur = max(min_dur, SCHE_STOP_TIME); exp_t = open_time + min_dur
                    if current_line_time < exp_t - EPSILON: self.add_error(f"CLOSE-{floor_str}-{eid}: Closed too fast after SCHE OPEN (closed {current_line_time:.4f}, needed >= {exp_t:.4f}).")
                    is_sche_close = True
                else:
                    exp_t = open_time + min_dur
                    if current_line_time < exp_t - EPSILON: self.add_error(f"CLOSE-{floor_str}-{eid}: Normal door closed too fast (closed {current_line_time:.4f}, needed >= {exp_t:.4f}).")
                e_state['state'] = 'CLOSED'; e_state['open_time'] = -1.0; e_state['last_action_time'] = current_line_time; self.close_count += 1
                if is_sche_close: e_state['sche_state'] = 'CLOSED_SCHE_TARGET'

            # --- IN --- (Corrected state check)
            elif match_in:
                _, pid_s, floor_s, eid_s = match_in.groups(); pid=int(pid_s); eid=int(eid_s); floor_i=floor_to_int(floor_s)
                p_state = self._get_passenger_state(pid); e_state = self._get_elevator_state(eid)
                if floor_i is None or p_state is None or e_state is None: self.add_error(f"IN Invalid (pid/eid/floor): {line}"); return True

                # --- START IN STATE CHECK FIX ---
                # Prevent IN only during active SCHE or active UPDATE
                is_sche_blocking = e_state['sche_state'] != 'IDLE'
                is_update_blocking = e_state['update_state'] == 'UPDATING' # Allow PENDING_UPDATE

                if is_sche_blocking:
                    self.add_error(f"IN-{pid}-{floor_s}-{eid}: Cannot enter during SCHE state {e_state['sche_state']}."); return True
                if is_update_blocking:
                    self.add_error(f"IN-{pid}-{floor_s}-{eid}: Cannot enter during UPDATE state {e_state['update_state']}."); return True
                # --- END IN STATE CHECK FIX ---

                if e_state['state']!='OPEN': self.add_error(f"IN-{pid}-{floor_s}-{eid}: Door not OPEN.")
                if e_state['floor']!=floor_i: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Elevator not at passenger's floor ({int_to_floor(e_state['floor'])}).")
                if p_state['state'] not in ['OUTSIDE','NEEDS_PICKUP']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger not OUTSIDE/NEEDS_PICKUP (state: {p_state['state']}).")
                if p_state['location']!=floor_i: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger not at this floor ({int_to_floor(p_state['location'])}).")
                if len(e_state['passengers'])>=ELEVATOR_CAPACITY: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Elevator full ({len(e_state['passengers'])}).")
                if pid in e_state['passengers']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger already inside this elevator.")
                if p_state['current_assignment']!=eid: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger not assigned to this elevator via RECEIVE (assigned to {p_state['current_assignment']}).")
                if pid not in e_state['active_receives']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Elevator does not have an active (unfulfilled) RECEIVE for passenger.")
                e_state['passengers'].add(pid);
                if pid in e_state['active_receives']: e_state['active_receives'].remove(pid)
                if self.active_passenger_assignments.get(pid)==eid: del self.active_passenger_assignments[pid]
                p_state['state']='INSIDE';p_state['location']=eid;p_state['current_assignment']=None;p_state['needs_pickup']=False

            # OUT
            elif match_out:
                _, flag, pid_s, floor_s, eid_s = match_out.groups(); pid=int(pid_s); eid=int(eid_s); floor_i=floor_to_int(floor_s)
                p_state = self._get_passenger_state(pid); e_state = self._get_elevator_state(eid)
                if floor_i is None or p_state is None or e_state is None: self.add_error(f"OUT Invalid (pid/eid/floor): {line}"); return True
                allowed_out_update_states = ['IDLE', 'DOUBLE_CAR_A', 'DOUBLE_CAR_B', 'PENDING_UPDATE'] # Allow OUT during PENDING
                allowed_out_sche_states = ['IDLE', 'OPEN_SCHE_TARGET']
                if not (e_state['update_state'] in allowed_out_update_states and e_state['sche_state'] in allowed_out_sche_states):
                     self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Cannot exit during state update:{e_state['update_state']} sche:{e_state['sche_state']}."); return True
                if e_state['state']!='OPEN': self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Door not OPEN.")
                if e_state['floor']!=floor_i: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Elevator not at this floor ({int_to_floor(e_state['floor'])}).")
                if p_state['state']!='INSIDE': self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger not INSIDE (state: {p_state['state']}).")
                if p_state['location']!=eid: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger not recorded in this elevator (in {p_state['location']}).")
                if pid not in e_state['passengers']: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger consistency error (not in elevator's set).")
                dest_reached = (floor_i == p_state['destination']); outcome_state = '?'
                if flag=='S':
                    if dest_reached: outcome_state='ARRIVED'; p_state['arrival_time']=current_line_time
                    else: self.add_error(f"OUT-S-{pid}-{floor_s}-{eid}: Flag S but destination {int_to_floor(p_state['destination'])} not reached."); outcome_state='OUTSIDE'; p_state['needs_pickup']=True
                elif flag=='F':
                    if not dest_reached: outcome_state='OUTSIDE'; p_state['needs_pickup']=True
                    else: self.add_error(f"OUT-F-{pid}-{floor_s}-{eid}: Flag F but destination reached."); outcome_state='ARRIVED'; p_state['arrival_time']=current_line_time
                else: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Invalid flag '{flag}'."); outcome_state='OUTSIDE'; p_state['needs_pickup']=True
                if pid in e_state['passengers']: e_state['passengers'].remove(pid)
                p_state['state'] = outcome_state; p_state['location'] = floor_i

            # RECEIVE (Corrected state check)
            elif match_receive:
                _, pid_s, eid_s = match_receive.groups(); pid=int(pid_s); eid=int(eid_s)
                p_state=self._get_passenger_state(pid); e_state=self._get_elevator_state(eid)
                if p_state is None or e_state is None: self.add_error(f"RECEIVE Invalid (pid/eid): {line}"); return True
                is_sche_blocking = e_state['sche_state'] != 'IDLE'
                is_update_blocking = e_state['update_state'] == 'UPDATING' # Only block during UPDATING
                if is_sche_blocking: self.add_error(f"RECEIVE-{pid}-{eid}: Cannot assign during SCHE state {e_state['sche_state']}."); return True
                if is_update_blocking: self.add_error(f"RECEIVE-{pid}-{eid}: Cannot assign during UPDATE state {e_state['update_state']}."); return True
                if p_state['state'] not in ['OUTSIDE','NEEDS_PICKUP']: self.add_error(f"RECEIVE-{pid}-{eid}: Passenger not OUTSIDE/NEEDS_PICKUP (state: {p_state['state']})."); return True
                existing_assignment = self.active_passenger_assignments.get(pid)
                if existing_assignment is not None and existing_assignment != eid: self.add_error(f"RECEIVE-{pid}-{eid}: Double assignment violation (P{pid} already assigned to E{existing_assignment})."); return True
                if existing_assignment != eid:
                    if existing_assignment is not None and existing_assignment in self.elevators:
                        old_e_state = self.elevators[existing_assignment]
                        if pid in old_e_state['active_receives']: old_e_state['active_receives'].remove(pid)
                    e_state['active_receives'].add(pid); p_state['current_assignment']=eid; self.active_passenger_assignments[pid]=eid

            # SCHE-ACCEPT
            elif match_sche_accept:
                _ts, eid_s, speed_s, floor_s = match_sche_accept.groups();
                try:
                    eid=int(eid_s); speed=float(speed_s); floor_i=floor_to_int(floor_s)
                    if not (1<=eid<=NUM_ELEVATORS): self.add_error(f"SCHE-ACCEPT Invalid eid: {line}")
                    if not any(abs(speed-v)<EPSILON for v in VALID_SCHE_SPEEDS): self.add_error(f"SCHE-ACCEPT Invalid speed: {line}")
                    if floor_i not in VALID_SCHE_UPDATE_FLOORS_INT: self.add_error(f"SCHE-ACCEPT Invalid floor: {line}")
                    e_state = self._get_elevator_state(eid);
                    if e_state: e_state['sche_accept_time'] = current_line_time
                except ValueError: self.add_error(f"SCHE-ACCEPT Invalid numeric: {line}")
                except Exception as e_acc: self.add_error(f"SCHE-ACCEPT Internal check error: {e_acc}")

            # SCHE-BEGIN
            elif match_sche_begin:
                _, eid_str = match_sche_begin.groups(); eid = int(eid_str)
                e_state = self._get_elevator_state(eid)
                if e_state is None: self.add_error(f"SCHE-BEGIN Invalid eid: {line}"); return True
                if e_state['update_state'] != 'IDLE': self.add_error(f"SCHE-BEGIN-{eid}: Cannot start SCHE during UPDATE state ({e_state['update_state']})."); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"SCHE-BEGIN-{eid}: Door not CLOSED."); return True
                if e_state['sche_state'] != 'IDLE': self.add_error(f"SCHE-BEGIN-{eid}: Not in IDLE SCHE state (state: {e_state['sche_state']})."); return True
                found_sche_input = None
                for req in self.all_inputs:
                    if req.get('type') == 'sche' and req.get('eid') == eid and not req.get('claimed', False): found_sche_input = req; req['claimed'] = True; break
                if found_sche_input: e_state['sche_target_floor'] = found_sche_input['to']; e_state['sche_speed_override'] = found_sche_input['speed']
                else: self.add_error(f"SCHE-BEGIN-{eid}: WARNING - Could not find unclaimed matching SCHE input."); e_state['sche_target_floor'] = None; e_state['sche_speed_override'] = None
                e_state['sche_state'] = 'ACTIVE'; e_state['sche_begin_time'] = current_line_time; self._cancel_external_receives_for_elevator(eid)

            # SCHE-END
            elif match_sche_end:
                _, eid_s = match_sche_end.groups(); eid=int(eid_s)
                e_state=self._get_elevator_state(eid)
                if e_state is None: self.add_error(f"SCHE-END Invalid eid: {line}"); return True
                if e_state['update_state'] != 'IDLE': self.add_error(f"SCHE-END-{eid}: Cannot end SCHE during UPDATE state ({e_state['update_state']})."); return True
                if e_state['sche_state']!='CLOSED_SCHE_TARGET': self.add_error(f"SCHE-END-{eid}: Not in required CLOSED_SCHE_TARGET state (state: {e_state['sche_state']})."); return True
                if e_state['state']!='CLOSED': self.add_error(f"SCHE-END-{eid}: Door not CLOSED."); return True
                if e_state['passengers']: self.add_error(f"SCHE-END-{eid}: Elevator not empty (passengers: {e_state['passengers']})."); return True
                accept_time = e_state['sche_accept_time']
                if accept_time < 0 : self.add_error(f"SCHE-END-{eid}: Internal Error - SCHE accept time not recorded.")
                elif current_line_time > accept_time + 6.0 + EPSILON: self.add_error(f"SCHE-END-{eid}: SCHE process took too long ({current_line_time - accept_time:.4f}s > 6s).")
                e_state['sche_state']='IDLE'; e_state['sche_target_floor']=None; e_state['sche_speed_override']=None; e_state['sche_begin_time']=-1.0; e_state['sche_accept_time'] = -1.0

            # UPDATE-ACCEPT
            elif match_update_accept:
                _ts, aid_s, bid_s, floor_s = match_update_accept.groups();
                try:
                    aid=int(aid_s); bid=int(bid_s); floor_i=floor_to_int(floor_s)
                    if not (1<=aid<=NUM_ELEVATORS and 1<=bid<=NUM_ELEVATORS and aid != bid): self.add_error(f"UPDATE-ACCEPT Invalid elevator IDs ({aid},{bid}): {line}")
                    if floor_i not in VALID_SCHE_UPDATE_FLOORS_INT: self.add_error(f"UPDATE-ACCEPT Invalid target floor ({floor_s}): {line}")
                    a_state = self._get_elevator_state(aid); b_state = self._get_elevator_state(bid); valid_states = True
                    if not a_state: self.add_error(f"UPDATE-ACCEPT-{aid}-{bid}: Elevator A state not found."); valid_states = False
                    if not b_state: self.add_error(f"UPDATE-ACCEPT-{aid}-{bid}: Elevator B state not found."); valid_states = False
                    if valid_states:
                         if a_state['update_state'] != 'IDLE' or b_state['update_state'] != 'IDLE': self.add_error(f"UPDATE-ACCEPT-{aid}-{bid}: Elevators not in IDLE update state (A:{a_state['update_state']}, B:{b_state['update_state']}).")
                         if a_state['sche_state'] != 'IDLE' or b_state['sche_state'] != 'IDLE': self.add_error(f"UPDATE-ACCEPT-{aid}-{bid}: Elevators not in IDLE SCHE state (A:{a_state['sche_state']}, B:{b_state['sche_state']}).")
                         a_state['update_state'] = 'PENDING_UPDATE'; a_state['update_accept_time'] = current_line_time; b_state['update_state'] = 'PENDING_UPDATE'; b_state['update_accept_time'] = current_line_time
                except ValueError: self.add_error(f"UPDATE-ACCEPT Invalid numeric ID/value: {line}")
                except Exception as e_uacc: self.add_error(f"UPDATE-ACCEPT Internal check error: {e_uacc}")

            # UPDATE-BEGIN
            elif match_update_begin:
                _ts, aid_s, bid_s = match_update_begin.groups();
                try:
                    aid = int(aid_s); bid = int(bid_s); a_state = self._get_elevator_state(aid); b_state = self._get_elevator_state(bid)
                    if a_state is None or b_state is None: self.add_error(f"UPDATE-BEGIN Invalid elevator ID ({aid if a_state is None else bid}): {line}"); return True
                    valid_pre_begin_state = True
                    if a_state['update_state'] != 'PENDING_UPDATE' or b_state['update_state'] != 'PENDING_UPDATE': self.add_error(f"UPDATE-BEGIN-{aid}-{bid}: Elevators not in PENDING_UPDATE state."); valid_pre_begin_state = False
                    if a_state['state'] != 'CLOSED' or b_state['state'] != 'CLOSED': self.add_error(f"UPDATE-BEGIN-{aid}-{bid}: Doors not closed."); valid_pre_begin_state = False
                    if a_state['passengers'] or b_state['passengers']: self.add_error(f"UPDATE-BEGIN-{aid}-{bid}: Elevators not empty."); valid_pre_begin_state = False
                    found_update_input = None
                    for req in self.all_inputs:
                        if req.get('type') == 'update' and req.get('aid') == aid and req.get('bid') == bid and not req.get('claimed', False): found_update_input = req; req['claimed'] = True; break
                        elif req.get('type') == 'update' and req.get('aid') == bid and req.get('bid') == aid and not req.get('claimed', False): self.add_error(f"UPDATE-BEGIN-{aid}-{bid}: Output order mismatches input order ({bid}-{aid})."); valid_pre_begin_state = False; break
                    if not found_update_input and valid_pre_begin_state: self.add_error(f"UPDATE-BEGIN-{aid}-{bid}: WARNING - Could not find matching unclaimed UPDATE input.")
                    if valid_pre_begin_state:
                        a_state['pending_update_request'] = found_update_input; b_state['pending_update_request'] = found_update_input
                        a_state['update_state'] = 'UPDATING'; a_state['update_begin_time'] = current_line_time
                        b_state['update_state'] = 'UPDATING'; b_state['update_begin_time'] = current_line_time
                        self._cancel_external_receives_for_elevator(aid); self._cancel_external_receives_for_elevator(bid)
                except ValueError: self.add_error(f"UPDATE-BEGIN Invalid numeric ID: {line}"); return True
                except Exception as e_ubgn: self.add_error(f"UPDATE-BEGIN Internal check error: {e_ubgn}"); return True

            # UPDATE-END
            elif match_update_end:
                 _ts, aid_s, bid_s = match_update_end.groups();
                 try:
                    aid = int(aid_s); bid = int(bid_s); a_state = self._get_elevator_state(aid); b_state = self._get_elevator_state(bid)
                    if a_state is None or b_state is None: self.add_error(f"UPDATE-END Invalid elevator ID ({aid if a_state is None else bid}): {line}"); return True
                    valid_pre_end_state = True
                    if a_state['update_state'] != 'UPDATING' or b_state['update_state'] != 'UPDATING': self.add_error(f"UPDATE-END-{aid}-{bid}: Elevators not in UPDATING state."); valid_pre_end_state = False
                    begin_time = max(a_state.get('update_begin_time', -1.0), b_state.get('update_begin_time', -1.0))
                    if begin_time < 0 and valid_pre_end_state: self.add_error(f"UPDATE-END-{aid}-{bid}: Internal Error - Begin time not recorded."); valid_pre_end_state = False
                    elif valid_pre_end_state and current_line_time < begin_time + UPDATE_PROCESS_TIME - EPSILON: self.add_error(f"UPDATE-END-{aid}-{bid}: Update process too fast."); valid_pre_end_state = False
                    accept_time = max(a_state.get('update_accept_time', -1.0), b_state.get('update_accept_time', -1.0))
                    if accept_time < 0 and valid_pre_end_state: self.add_error(f"UPDATE-END-{aid}-{bid}: Internal Error - Accept time not recorded."); valid_pre_end_state = False
                    elif valid_pre_end_state and current_line_time > accept_time + 6.0 + EPSILON: self.add_error(f"UPDATE-END-{aid}-{bid}: Update process took too long (> 6s from ACCEPT)."); valid_pre_end_state = False
                    update_req = a_state.get('pending_update_request')
                    if not update_req and valid_pre_end_state: self.add_error(f"UPDATE-END-{aid}-{bid}: Internal Error - Pending request missing."); valid_pre_end_state = False
                    if valid_pre_end_state:
                        target_floor = update_req.get('target_floor')
                        if target_floor is None: self.add_error(f"UPDATE-END-{aid}-{bid}: Internal Error - Target floor missing."); valid_pre_end_state = False
                    if valid_pre_end_state:
                        a_state['update_state'] = 'DOUBLE_CAR_A'; a_new_floor = target_floor + 1 if target_floor != B1_INT else F1_INT; a_new_floor = max(MIN_FLOOR_INT, min(a_new_floor, MAX_FLOOR_INT));
                        if a_new_floor == 0: a_new_floor = 1
                        a_state['floor'] = a_new_floor; a_state['min_floor'] = target_floor; a_state['max_floor'] = MAX_FLOOR_INT; a_state['current_speed'] = DOUBLE_CAR_SPEED
                        a_state['update_partner_id'] = bid; a_state['update_transfer_floor'] = target_floor; a_state['initial_post_update_move_allowed'] = True; a_state['last_action_time'] = current_line_time
                        b_state['update_state'] = 'DOUBLE_CAR_B'; b_new_floor = target_floor - 1 if target_floor != F1_INT else B1_INT; b_new_floor = max(MIN_FLOOR_INT, min(b_new_floor, MAX_FLOOR_INT));
                        if b_new_floor == 0: b_new_floor = -1
                        b_state['floor'] = b_new_floor; b_state['min_floor'] = MIN_FLOOR_INT; b_state['max_floor'] = target_floor; b_state['current_speed'] = DOUBLE_CAR_SPEED
                        b_state['update_partner_id'] = aid; b_state['update_transfer_floor'] = target_floor; b_state['initial_post_update_move_allowed'] = True; b_state['last_action_time'] = current_line_time
                        a_state['pending_update_request'] = None; b_state['pending_update_request'] = None; a_state['update_accept_time'] = -1.0; b_state['update_accept_time'] = -1.0; a_state['update_begin_time'] = -1.0; b_state['update_begin_time'] = -1.0
                        if a_state['floor'] <= b_state['floor']: self.add_error(f"UPDATE-END-{aid}-{bid}: Consistency violation! Car A at/below Car B.")
                 except ValueError: self.add_error(f"UPDATE-END Invalid numeric ID: {line}"); return True
                 except Exception as e_uend: self.add_error(f"UPDATE-END Internal check error: {e_uend}"); return True

            # Unknown Line
            else: self.add_error(f"WARNING: Unrecognized output line format: {line}")

        # Exception Handling
        except ValueError as ve: self.add_error(f"CRITICAL: Invalid number conversion: {line} ({ve})"); return False
        except KeyError as ke: self.add_error(f"CRITICAL: Internal State Error (KeyError: {ke}) processing '{line}'."); return False
        except Exception as e: self.add_error(f"CRITICAL: Internal Error processing '{line}': {e}\n{traceback.format_exc(limit=3)}"); return False

        return True

    # --- final_checks (No change needed) ---
    def final_checks(self):
        for pid, p_state in self.passengers.items():
            if p_state.get('state') != 'ARRIVED':
                req = self.passenger_requests_dict.get(pid); dest_str = int_to_floor(req['to']) if req else '?'
                pri_str = p_state.get('priority','?'); state = p_state.get('state','?'); loc = 'N/A'; cur_loc = p_state.get('location')
                if state == 'INSIDE': loc_desc = f"Elevator {cur_loc}"; loc = loc_desc
                elif state in ['OUTSIDE','NEEDS_PICKUP']: loc = int_to_floor(cur_loc) if isinstance(cur_loc, int) else f'Floor?({cur_loc})'
                else: loc = f"State: {state}, Loc: {cur_loc}"
                self.add_error(f"P{pid} (Pri={pri_str}) !Reach dest {dest_str} (final: {state} at {loc}).")
        for eid, e_state in self.elevators.items():
            if e_state.get('state') != 'CLOSED': self.add_error(f"E{eid} !CLOSED at end (state: {e_state.get('state')}).")
            if e_state.get('passengers'): self.add_error(f"E{eid} finished w/ passengers: {sorted(list(e_state['passengers']))}.")
            if e_state.get('sche_state') != 'IDLE': self.add_error(f"E{eid} finished !IDLE SCHE state: {e_state.get('sche_state')}.")
            final_update_state = e_state.get('update_state')
            if final_update_state not in ['IDLE', 'DOUBLE_CAR_A', 'DOUBLE_CAR_B']: self.add_error(f"E{eid} finished in invalid UPDATE state: {final_update_state}.")
            partner_id = e_state.get('update_partner_id')
            if partner_id is not None:
                 if partner_id not in self.elevators: self.add_error(f"E{eid} has invalid partner ID {partner_id}.")
                 else:
                      partner_state = self.elevators.get(partner_id)
                      if not partner_state: self.add_error(f"E{eid} partner {partner_id} state not found.")
                      elif partner_state.get('update_partner_id') != eid: self.add_error(f"E{eid} partner inconsistency (partner {partner_id} !point back).")
                      elif e_state.get('update_transfer_floor') != partner_state.get('update_transfer_floor'): self.add_error(f"E{eid} partner transfer floor mismatch.")
                      elif final_update_state == 'DOUBLE_CAR_A' and partner_state.get('update_state') == 'DOUBLE_CAR_B':
                          if e_state.get('floor') <= partner_state.get('floor'): self.add_error(f"E{eid}(A) finished at/below E{partner_id}(B).")
                      elif final_update_state == 'DOUBLE_CAR_B' and partner_state.get('update_state') == 'DOUBLE_CAR_A':
                           if e_state.get('floor') >= partner_state.get('floor'): self.add_error(f"E{eid}(B) finished at/above E{partner_id}(A).")
        if self.active_passenger_assignments: self.add_error(f"Finished w/ active external assignments remaining: {self.active_passenger_assignments}")

    # --- get_errors, get_final_sim_time, metrics (No change needed) ---
    def get_errors(self): return self.errors
    def get_final_sim_time(self): return self.sim_time if self.sim_time > 0 else 0.0
    def get_power_consumption(self): return (POWER_OPEN * self.open_count + POWER_CLOSE * self.close_count + POWER_MOVE * self.move_count)
    def get_weighted_average_completion_time(self):
        total_weighted_time = 0; total_priority = 0;
        for pid, p_state in self.passengers.items():
            if p_state.get('state') == 'ARRIVED':
                arrival_time = p_state.get('arrival_time', -1.0); request_time = p_state.get('request_time', -1.0); priority = p_state.get('priority', 0)
                if arrival_time >= 0 and request_time >= 0 and priority > 0:
                    completion_time = arrival_time - request_time
                    if completion_time >= -EPSILON: total_weighted_time += max(0, completion_time) * priority; total_priority += priority;
                    else: self.add_error(f"WARN: P{pid} arrival < request ({arrival_time:.4f} < {request_time:.4f})")
        if total_priority > 0: return total_weighted_time / total_priority
        else: return 0.0

# --- Plotting Functions --- (No change needed)
# ... (plot_metric, plot_runtime_results, etc. remain the same) ...
def plot_metric(plot_data, data_files_sorted_with_avg, y_label, title, output_filename):
    if not MATPLOTLIB_AVAILABLE: return
    if not any(plot_data.values()): return
    valid_data_exists = any(v is not None and isinstance(v, (int, float)) for jar_data in plot_data.values() for v in jar_data.values())
    if not valid_data_exists: return
    print(f"Generating plot '{output_filename}'...")
    try:
        x_labels=[os.path.splitext(df)[0] if df!="Average" else "Average" for df in data_files_sorted_with_avg]; x_indices=range(len(x_labels))
        fig,ax=plt.subplots(figsize=(max(10,len(x_labels)*0.5),6)); jar_names=sorted(plot_data.keys())
        for jar_file in jar_names:
            jar_data=plot_data[jar_file]; y_values=[jar_data.get(df) for df in data_files_sorted_with_avg]
            valid_indices=[i for i,y in enumerate(y_values) if y is not None and isinstance(y, (int, float))]
            valid_y=[y for y in y_values if y is not None and isinstance(y, (int, float))]
            if valid_indices:
                line, = ax.plot([x_indices[i] for i in valid_indices], valid_y, marker='o', linestyle='-', label=os.path.basename(jar_file))
                if "Average" in data_files_sorted_with_avg:
                    avg_idx = data_files_sorted_with_avg.index("Average"); avg_val = jar_data.get("Average")
                    if avg_val is not None and isinstance(avg_val, (int, float)): ax.plot(avg_idx, avg_val, marker='*', markersize=10, markeredgecolor='black', markerfacecolor=line.get_color(), linestyle='None')
        ax.set_xlabel("Test Case"); ax.set_ylabel(y_label); ax.set_title(title)
        ax.set_xticks(x_indices); ax.set_xticklabels(x_labels, rotation=45, ha='right')
        if "Average" in x_labels and len(x_labels) > 1: ax.axvline(x=len(x_labels)-1.5, color='gray', linestyle='--', alpha=0.7)
        ax.legend(title="JAR Files", bbox_to_anchor=(1.04,1), loc="upper left"); ax.grid(True, axis='y', linestyle='--', alpha=0.7); ax.set_ylim(bottom=0)
        fig.tight_layout(rect=[0, 0, 0.85, 1]); plt.savefig(output_filename, bbox_inches='tight'); plt.close(fig)
        print(f"Plot '{output_filename}' saved successfully.")
    except Exception as plot_e: print(f"\nError generating plot '{output_filename}': {plot_e}", file=sys.stderr)
def plot_runtime_results(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_RUNTIME):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Completion Time (s)", "JAR Runtime Comparison (Successful Runs)", output_filename)
def plot_power_consumption(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_POWER):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Power Consumption (Units)", "JAR Power Consumption Comparison (Successful Runs)", output_filename)
def plot_weighted_avg_time(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_AVGTIME):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Weighted Avg Completion Time (s)", "JAR Weighted Avg Passenger Time (Successful Runs)", output_filename)
def plot_total_score(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_TOTALSCORE):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Total Score (Points)", "JAR Total Score Comparison (Successful Runs)", output_filename)

# --- run_single_test_case --- (No change needed)
def run_single_test_case(jar_file, data_file, data_dir, out_dir, log_dir):
    data_file_path = os.path.join(data_dir, data_file); jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    data_file_base = os.path.splitext(data_file)[0]; log_file_name = f"{jar_name_base}_{data_file_base}.log"
    log_file_path = os.path.join(log_dir, log_file_name); output_file_name = f"{jar_name_base}_{data_file_base}.out"
    output_file_path_filtered = os.path.join(out_dir, output_file_name)
    errors = []; stdout_data, stderr_data = "", ""; execution_time, run_status_code = 0, None
    result_status = "CHECKER_ERROR"; final_sim_time = 0.0; power_consumption = 0.0; weighted_avg_time = 0.0
    try:
        input_str = ""; parsed_inputs = []; parse_error = False
        try:
            with open(data_file_path, 'r', encoding='utf-8', errors='replace') as f: input_lines = f.readlines(); input_str = "".join(input_lines)
            for line_num, line in enumerate(input_lines):
                line = line.strip();
                if not line: continue
                match_p = RE_INPUT_PASSENGER.match(line); match_s = RE_INPUT_SCHE.match(line); match_u = RE_INPUT_UPDATE.match(line)
                if match_p:
                    t, p, pri, f_s, to_s = match_p.groups(); fi, toi = floor_to_int(f_s), floor_to_int(to_s)
                    if fi is None or toi is None: errors.append(f"Input L{line_num+1}: Invalid passenger floor."); parse_error = True; break
                    try: parsed_inputs.append({'type': 'passenger', 'time': float(t), 'id': int(p), 'pri': int(pri), 'from': fi, 'to': toi})
                    except ValueError as ve: errors.append(f"Input L{line_num+1}: Invalid passenger number: {ve}"); parse_error = True; break
                elif match_s:
                    t, e, spd_s, fl_s = match_s.groups(); fli = floor_to_int(fl_s)
                    if fli is None: errors.append(f"Input L{line_num+1}: Invalid SCHE floor."); parse_error = True; break
                    try:
                        eid = int(e); speed = float(spd_s)
                        if fli not in VALID_SCHE_UPDATE_FLOORS_INT: errors.append(f"Input L{line_num+1}: Invalid SCHE target floor."); parse_error = True; break
                        if not any(abs(speed - v) < EPSILON for v in VALID_SCHE_SPEEDS): errors.append(f"Input L{line_num+1}: Invalid SCHE speed."); parse_error = True; break
                        if not (1 <= eid <= NUM_ELEVATORS): errors.append(f"Input L{line_num+1}: Invalid SCHE elevator ID."); parse_error = True; break
                        parsed_inputs.append({'type': 'sche', 'time': float(t), 'eid': eid, 'speed': speed, 'to': fli, 'claimed': False})
                    except ValueError as ve: errors.append(f"Input L{line_num+1}: Invalid SCHE number: {ve}"); parse_error = True; break
                elif match_u:
                    t, a_s, b_s, fl_s = match_u.groups(); fli = floor_to_int(fl_s)
                    if fli is None: errors.append(f"Input L{line_num+1}: Invalid UPDATE floor."); parse_error = True; break
                    try:
                        aid = int(a_s); bid = int(b_s)
                        if fli not in VALID_SCHE_UPDATE_FLOORS_INT: errors.append(f"Input L{line_num+1}: Invalid UPDATE target floor."); parse_error = True; break
                        if not (1 <= aid <= NUM_ELEVATORS and 1 <= bid <= NUM_ELEVATORS and aid != bid): errors.append(f"Input L{line_num+1}: Invalid UPDATE elevator IDs."); parse_error = True; break
                        parsed_inputs.append({'type': 'update', 'time': float(t), 'aid': aid, 'bid': bid, 'target_floor': fli, 'claimed': False})
                    except ValueError as ve: errors.append(f"Input L{line_num+1}: Invalid UPDATE number: {ve}"); parse_error = True; break
                else: errors.append(f"Input L{line_num+1}: Malformed line: {line}"); parse_error = True; break
        except FileNotFoundError: raise FileNotFoundError(f"Input file not found: {data_file_path}")
        except Exception as e: raise Exception(f"Error reading/parsing input {data_file_path}: {e}")
        if parse_error: result_status = "INPUT_ERROR"
        else:
            stdout_data, stderr_data, execution_time, run_status_code = run_java_program_with_threads(jar_file, input_str)
            try:
                with open(log_file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"--- INPUT ---\n{input_str}\n\n"); f.write(f"--- STDOUT ---\n{stdout_data}")
                    if stderr_data: f.write("\n\n--- STDERR ---\n" + stderr_data)
                    f.write(f"\n\n--- EXECUTION TIME: {execution_time:.4f}s ---"); f.write(f"\n--- RUN STATUS CODE: {run_status_code} ---")
            except IOError as e: errors.append(f"Warning: Failed to write log file {log_file_path}: {e}")
            all_stdout_lines = stdout_data.splitlines(); filtered_output_lines = [line for line in all_stdout_lines if not RE_LOG_LINE.search(line)]
            clean_stdout_data_for_saving = "\n".join(filtered_output_lines)
            try:
                with open(output_file_path_filtered, 'w', encoding='utf-8', errors='replace') as f: f.write(clean_stdout_data_for_saving)
            except IOError as e: errors.append(f"Warning: Failed to write filtered output file {output_file_path_filtered}: {e}")
            initial_run_status = "OK"
            if run_status_code == "Killed": initial_run_status = "TIMEOUT_HARD"
            elif run_status_code == "TLE": initial_run_status = "TIMEOUT_SOFT"
            elif run_status_code == "ExecutionError": initial_run_status = "RUNTIME_ERROR"
            elif run_status_code == "JavaNotFound": initial_run_status = "JAVA_ERROR"
            elif run_status_code is not None: initial_run_status = "CHECKER_ERROR"; errors.append(f"Unknown run_status_code: {run_status_code}")
            if initial_run_status not in ["JAVA_ERROR", "CHECKER_ERROR", "INPUT_ERROR"]:
                if not clean_stdout_data_for_saving.strip() and parsed_inputs:
                     if initial_run_status == "OK": result_status = "WRONG_ANSWER"; errors.append("Validation Error: No non-log output for non-empty input.")
                     else: result_status = initial_run_status; errors.append("INFO: No non-log output before timeout/error.")
                else:
                    validator = Validator(parsed_inputs); validation_stopped = False
                    for line_num_val, output_line_val in enumerate(filtered_output_lines):
                        if not validator.validate_line(output_line_val):
                            validation_stopped = True; errors.append(f"Validation failed near output line {line_num_val+1}: {output_line_val.strip()}")
                            val_errors = validator.get_errors();
                            if val_errors: errors.extend([f"  -> {ve}" for ve in val_errors[-3:]]); break
                    if not validation_stopped: validator.final_checks()
                    validation_errors = validator.get_errors(); final_sim_time = validator.get_final_sim_time()
                    if not validation_stopped and initial_run_status == "OK":
                        power_consumption = validator.get_power_consumption(); weighted_avg_time = validator.get_weighted_average_completion_time()
                    if validation_errors:
                        if not validation_stopped: errors.extend(validation_errors)
                        result_status = initial_run_status if initial_run_status != "OK" else "WRONG_ANSWER"
                    elif initial_run_status == "OK": result_status = "PASSED"
                    else: result_status = initial_run_status
            else:
                 result_status = initial_run_status
                 if result_status == "JAVA_ERROR" and not any("java command not found" in e for e in errors): errors.append("Failed: Java command issue.")
                 if result_status == "INPUT_ERROR" and not any("Input Error" in e for e in errors): errors.append("Checker Error: Input data parsing error.")
    except FileNotFoundError as e: errors.append(f"Checker Error: {e}"); result_status = "CHECKER_ERROR"
    except MemoryError: errors.append(f"Checker Error: Out of memory."); result_status = "CHECKER_ERROR"
    except Exception as e: errors.append(f"Checker Error for {data_file}: {e}\n{traceback.format_exc(limit=3)}"); result_status = "CHECKER_ERROR"
    if result_status == "TIMEOUT_HARD" and not any("Hard timeout" in e for e in errors): errors.append(f"Failed: Hard timeout ({HARD_TIMEOUT:.1f}s).")
    if result_status == "TIMEOUT_SOFT" and not any("Soft timeout" in e for e in errors): errors.append(f"Warning: Soft timeout ({SOFT_TIMEOUT:.1f}s).")
    if result_status == "RUNTIME_ERROR" and not any(s in e for s in ["Runtime Error", "non-zero exit code", "terminated", "Error sending input"] for e in errors): errors.append(f"Failed: Runtime Error or Non-zero Exit.")
    if result_status == "WRONG_ANSWER" and not errors: errors.append("Failed: Wrong Answer (No specific validation errors reported).")
    if result_status == "CHECKER_ERROR" and not errors: errors.append("Checker Error: Unknown internal issue.")
    return {"data_file": data_file, "status": result_status, "sim_time": final_sim_time,
            "exec_time": execution_time, "power": power_consumption, "avg_time": weighted_avg_time, "errors": errors}

# --- test_single_jar --- (No change needed)
def test_single_jar(jar_file, all_data_files, data_dir, out_dir, log_dir, report_dir):
    jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    report_lines = []; passed_tests = 0; failed_tests = 0; total_tests = len(all_data_files)
    jar_plot_data_runtime = {}; jar_plot_data_power = {}; jar_plot_data_avgtime = {}
    print(f"\nStarting tests for {jar_file}...")
    for i, data_file in enumerate(all_data_files):
        print(f"  Running test {i+1}/{total_tests}: {data_file}...", end='\r')
        result = run_single_test_case(jar_file, data_file, data_dir, out_dir, log_dir)
        result_status = result["status"]
        report_time = result["sim_time"] if result_status in ["PASSED", "TIMEOUT_SOFT", "WRONG_ANSWER"] and result["sim_time"] > 0 else result["exec_time"]
        status_line = f"{result['data_file']:<25}: {result_status:<15} ({report_time:.2f}s)"
        report_lines.append(status_line)
        if result_status == "PASSED":
            passed_tests += 1; jar_plot_data_runtime[data_file] = result["sim_time"]; jar_plot_data_power[data_file] = result["power"]; jar_plot_data_avgtime[data_file] = result["avg_time"]
            print(status_line + " " * 10)
        else:
            failed_tests += 1; print(status_line + " " * 10)
            for err_idx, err in enumerate(result.get('errors', [])):
                 if err_idx < 3 : report_lines.append(f"    - {str(err)[:150]}{'...' if len(str(err))>150 else ''}")
            if len(result.get('errors', [])) > 3: report_lines.append(f"    - ... ({len(result['errors'])-3} more errors - see log)")
        if result_status == "JAVA_ERROR":
             print(f"\nFATAL: Java error for {jar_file}, aborting tests.", file=sys.stderr); remaining_tests = total_tests - (i + 1); failed_tests += remaining_tests
             for skipped_df in all_data_files[i+1:]: report_lines.append(f"{skipped_df:<25}: {'JAVA_ERROR':<15} (Skipped)"); break
    report_path = os.path.join(REPORT_DIR, f"{jar_name_base}.report")
    summary = f"Report: {jar_file}\nOverall: {passed_tests}/{total_tests} passed ({failed_tests} failed).\n{'='*40}"
    print(f"\nFinished {jar_file}. Results: {passed_tests}/{total_tests} passed.")
    try:
        with open(report_path, 'w', encoding='utf-8', errors='replace') as f: f.write(summary + "\n"); f.write("\n".join(report_lines) + "\n")
        print(f"Report saved to '{report_path}'")
    except IOError as e: print(f"Error writing report '{report_path}': {e}", file=sys.stderr)
    return (jar_file, passed_tests, total_tests, jar_plot_data_runtime, jar_plot_data_power, jar_plot_data_avgtime)

# --- Scoring Functions --- (No change needed)
def calculate_relative_score(value, min_val, max_val):
    if value is None or not isinstance(value, (int, float)): return 0.0
    if abs(max_val - min_val) < EPSILON: return 15.0
    clamped_value = max(min_val, min(value, max_val))
    score = 15.0 * (max_val - clamped_value) / (max_val - min_val)
    return score
def process_scores(raw_metric_results, data_files, jar_files):
    scores_power = defaultdict(dict); scores_runtime = defaultdict(dict)
    scores_avgtime = defaultdict(dict); total_scores = defaultdict(dict)
    valid_jar_files = [jf for jf in jar_files if jf in raw_metric_results.get('sim_time', {}) or jf in raw_metric_results.get('power', {}) or jf in raw_metric_results.get('avg_time', {})]
    if not valid_jar_files: print("Warning: No valid JAR results for scoring."); return {}, {}, {}, {}
    metric_keys = ['power', 'sim_time', 'avg_time']
    score_dicts = {'power': scores_power, 'sim_time': scores_runtime, 'avg_time': scores_avgtime}
    raw_data_map = {'power': raw_metric_results.get('power',{}), 'sim_time': raw_metric_results.get('sim_time',{}), 'avg_time': raw_metric_results.get('avg_time',{})}
    print("\nCalculating relative scores (0-15 points per metric)...")
    for metric_key in metric_keys:
        score_dict = score_dicts[metric_key]; raw_data = raw_data_map[metric_key]; print(f"  Processing metric: {metric_key}...")
        for data_file in data_files:
            values = [raw_data.get(jf,{}).get(data_file) for jf in valid_jar_files if isinstance(raw_data.get(jf,{}).get(data_file), (int, float))]
            if not values:
                for jf in valid_jar_files: score_dict[jf][data_file] = 0.0; continue
            try: min_v=min(values); max_v=max(values)
            except ValueError: print(f"    Error min/max {metric_key}/{data_file}. Scores=0."); min_v=max_v=None
            for jf in valid_jar_files:
                original_value = raw_data.get(jf,{}).get(data_file)
                if original_value is None or not isinstance(original_value,(int,float)) or min_v is None: score_dict[jf][data_file]=0.0
                else: score_dict[jf][data_file]=calculate_relative_score(original_value, min_v, max_v)
    print("Calculating total scores (weighted sum)...")
    for jf in valid_jar_files:
        for df in data_files:
            rp = scores_power.get(jf,{}).get(df,0.0); rr = scores_runtime.get(jf,{}).get(df,0.0); ra = scores_avgtime.get(jf,{}).get(df,0.0)
            total_scores[jf][df] = (0.4 * rp + 0.3 * rr + 0.3 * ra)
    print("Finished score calculations.")
    return scores_power, scores_runtime, scores_avgtime, total_scores
def add_averages_to_plot_data(plot_data_dict, data_files):
    if not plot_data_dict: return
    print(f"Calculating averages for plot data...")
    for jar_file, data_map in plot_data_dict.items():
        values = [data_map.get(df) for df in data_files if data_map.get(df) is not None and isinstance(data_map.get(df), (int, float))]
        if values:
            try: average = np.mean(values); plot_data_dict[jar_file]["Average"] = average
            except Exception as e: print(f"    Warn: Avg calc failed for {jar_file}: {e}"); plot_data_dict[jar_file]["Average"] = None
        else: plot_data_dict[jar_file]["Average"] = None
    print("Finished calculating averages.")

# --- Main Execution Logic --- (No change needed)
def main():
    print("Elevator Simulation Checker (HW7 Version)"); print("-" * 40)
    for dir_path in [DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR]:
        try: os.makedirs(dir_path, exist_ok=True)
        except OSError as e: print(f"Error creating directory {dir_path}: {e}", file=sys.stderr); sys.exit(1)
    enable_plotting = False
    if MATPLOTLIB_AVAILABLE:
        while True:
            try: choice = input("Enable plotting (requires matplotlib)? (y/n): ").lower().strip()
            except EOFError: print("\nNo input, disabling plotting."); choice = 'n'; break
            if choice == 'y': enable_plotting = True; print("Plotting enabled."); break
            elif choice == 'n': enable_plotting = False; print("Plotting disabled."); break
            else: print("Invalid input. Please enter 'y' or 'n'.")
    else: print("\nInfo: matplotlib unavailable. Plotting disabled.")
    use_generator = False
    if os.path.isfile(GENERATOR_SCRIPT):
        while True:
            try: choice = input(f"Generate new data using {GENERATOR_SCRIPT}? (y/n): ").lower().strip()
            except EOFError: print("\nNo input, assuming 'n'."); choice = 'n'; break
            if choice == 'y': use_generator = True; break
            elif choice == 'n': break
            else: print("Invalid input. Please enter 'y' or 'n'.")
    else: print(f"\nInfo: Data generator script '{GENERATOR_SCRIPT}' not found.")
    if use_generator:
        print(f"\nClearing old data in '{DATA_DIR}'..."); clear_directory(DATA_DIR)
        try:
            print(f"Running data generator '{GENERATOR_SCRIPT}'...")
            proc = subprocess.run([sys.executable, GENERATOR_SCRIPT], text=True, check=True, encoding='utf-8', errors='replace')
            print(f"Data generator '{GENERATOR_SCRIPT}' finished successfully.")
            generated_files = find_files(DATA_DIR, ".txt")
            if not generated_files: print(f"\nWarning: Generator ran but no '.txt' files found in '{DATA_DIR}'.", file=sys.stderr)
            else: print(f"Found {len(generated_files)} generated data file(s).")
        except FileNotFoundError: print(f"\nError: Could not execute '{sys.executable} {GENERATOR_SCRIPT}'.", file=sys.stderr); sys.exit(1)
        except subprocess.CalledProcessError as e: print(f"\nError: Data generator script failed (code {e.returncode}).", file=sys.stderr); sys.exit(1)
        except Exception as e: print(f"\nError running data generator: {e}", file=sys.stderr); sys.exit(1)
    jar_files = find_files(".", ".jar");
    try: data_files = find_files(DATA_DIR, ".txt")
    except FileNotFoundError: print(f"Error: Data dir '{DATA_DIR}' not found.", file=sys.stderr); sys.exit(1)
    if not jar_files: print("Error: No .jar files found.", file=sys.stderr); sys.exit(1)
    if not data_files: print(f"Error: No .txt data files in '{DATA_DIR}'.", file=sys.stderr); sys.exit(1)
    print(f"\nFound {len(jar_files)} JAR(s): {', '.join([os.path.basename(j) for j in jar_files])}")
    print(f"Found {len(data_files)} test case(s) in '{DATA_DIR}'.")
    print(f"\nClearing '{OUT_DIR}', '{LOG_DIR}', '{REPORT_DIR}'..."); clear_directory(OUT_DIR); clear_directory(LOG_DIR); clear_directory(REPORT_DIR)
    raw_results_runtime = defaultdict(dict); raw_results_power = defaultdict(dict); raw_results_avgtime = defaultdict(dict)
    workers = min(MAX_WORKERS, DEFAULT_WORKERS); print(f"\nExecution mode: '{PARALLEL_MODE}' with up to {workers} worker threads.")
    overall_summary = {}; start_overall_time = time.monotonic()
    if PARALLEL_MODE == 'none':
        print("Running tests sequentially...");
        for jar_file in jar_files:
            _j, p, t, jr, jp, jt = test_single_jar(jar_file, data_files, DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR); overall_summary[jar_file]=(p,t)
            if jr: raw_results_runtime[jar_file] = jr;
            if jp: raw_results_power[jar_file] = jp;
            if jt: raw_results_avgtime[jar_file] = jt
    elif PARALLEL_MODE == 'data':
        print(f"Running tests in parallel ('data' mode, max_workers={workers})...");
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for jar_file in jar_files:
                print("\n"+"="*40); print(f"Submitting tests for: {os.path.basename(jar_file)}"); print("="*40)
                jar_name_base=os.path.splitext(os.path.basename(jar_file))[0]; report_map={}; passed,failed,total=0,0,len(data_files)
                futures_map={executor.submit(run_single_test_case, jar_file, df, DATA_DIR, OUT_DIR, LOG_DIR): df for df in data_files}
                jar_raw_runtime, jar_raw_power, jar_raw_avgtime = {}, {}, {}; java_error_encountered=False; processed_count=0
                print(f"All {total} tests submitted. Processing results...")
                for future in concurrent.futures.as_completed(futures_map):
                    df_completed = futures_map[future]; processed_count += 1; print(f"  [{processed_count}/{total}] Completed {df_completed}...", end='\r')
                    try:
                        result=future.result(); report_map[df_completed]=result; status=result['status']
                        if status == "PASSED": passed+=1; jar_raw_runtime[df_completed]=result["sim_time"]; jar_raw_power[df_completed]=result["power"]; jar_raw_avgtime[df_completed]=result["avg_time"]
                        else:
                            failed+=1; rtime=result["sim_time"] if status in ["TIMEOUT_SOFT","WRONG_ANSWER"] and result["sim_time"]>0 else result["exec_time"]
                            print(f"  [{processed_count}/{total}] Failed: {df_completed:<20} - {status:<15} ({rtime:.2f}s)" + " "*5)
                            for i, err in enumerate(result.get('errors',[])):
                                if i < 2: print(f"      - {str(err).replace(chr(10),' ')[:120]}{'...' if len(str(err))>120 else ''}")
                            if len(result.get('errors',[])) > 2: print(f"      - ... ({len(result['errors'])-2} more errors - see log/report)")
                            if status == "JAVA_ERROR": java_error_encountered = True
                    except Exception as exc: print(f"\nCRITICAL Error processing result for {df_completed} ({jar_file}): {exc}", file=sys.stderr); report_map[df_completed] = {"data_file": df_completed, "status": "CHECKER_ERROR", "errors": [f"Exception: {exc}"]}; failed += 1
                print("\n"+"-"*40); summary_line = f"Finished {os.path.basename(jar_file)}. Results: {passed}/{total} passed, {failed} failed."; print(summary_line); overall_summary[jar_file]=(passed,total)
                if java_error_encountered: print(f"  (Note: JAVA_ERROR encountered)")
                if jar_raw_runtime: raw_results_runtime[jar_file] = jar_raw_runtime;
                if jar_raw_power: raw_results_power[jar_file] = jar_raw_power;
                if jar_raw_avgtime: raw_results_avgtime[jar_file] = jar_raw_avgtime
                report_path = os.path.join(REPORT_DIR, f"{jar_name_base}.report");
                try:
                    with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(f"Report: {jar_file}\nOverall: {passed}/{total} passed ({failed} failed).\n{'='*40}\n"); report_lines_for_file=[]
                        for df_rep in data_files:
                            res=report_map.get(df_rep)
                            if res: rt_rep=res.get("sim_time",0) if res.get('status') in ["PASSED","TIMEOUT_SOFT","WRONG_ANSWER"] and res.get("sim_time",0)>0 else res.get("exec_time",0); status_rep=res.get('status','UNKNOWN'); report_lines_for_file.append(f"{df_rep:<25}: {status_rep:<15} ({rt_rep:.2f}s)")
                            if status_rep != "PASSED":
                                for err_rep in res.get('errors',[]): report_lines_for_file.append(f"    - {err_rep}")
                            else: report_lines_for_file.append(f"{df_rep:<25}: {'RESULT_MISSING':<15}")
                        f.write("\n".join(report_lines_for_file)+"\n")
                    print(f"Report saved to '{report_path}'")
                except IOError as e: print(f"Error writing report '{report_path}': {e}", file=sys.stderr)
    elif PARALLEL_MODE == 'jar':
        print(f"Running tests in parallel ('jar' mode, max_workers={workers})...");
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            jar_futures = {executor.submit(test_single_jar, jar, data_files, DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR): jar for jar in jar_files}
            print(f"All {len(jar_files)} JAR suites submitted. Waiting..."); completed_jars = 0
            for future in concurrent.futures.as_completed(jar_futures):
                jar_completed = jar_futures[future]; completed_jars += 1; print(f"Completed suite for JAR: {os.path.basename(jar_completed)} ({completed_jars}/{len(jar_files)})...")
                try:
                    _j, p, t, jr, jp, jt = future.result(); overall_summary[jar_completed]=(p,t)
                    if jr: raw_results_runtime[jar_completed] = jr;
                    if jp: raw_results_power[jar_completed] = jp;
                    if jt: raw_results_avgtime[jar_completed] = jt
                except Exception as exc: print(f"\nCRITICAL Error running suite for JAR '{jar_completed}': {exc}\n{traceback.format_exc(limit=3)}", file=sys.stderr); overall_summary[jar_completed] = (0, len(data_files))
    else: print(f"Error: Unknown PARALLEL_MODE '{PARALLEL_MODE}'.", file=sys.stderr); sys.exit(1)
    print("\n"+"="*40); print("Post-processing results..."); print("="*40)
    all_raw_results = {'power': raw_results_power, 'sim_time': raw_results_runtime, 'avg_time': raw_results_avgtime}
    scores_power, scores_runtime, scores_avgtime, total_scores = process_scores(all_raw_results, data_files, list(overall_summary.keys()))
    plot_data_runtime = defaultdict(dict, {k: v.copy() for k, v in raw_results_runtime.items()})
    plot_data_power = defaultdict(dict, {k: v.copy() for k, v in raw_results_power.items()})
    plot_data_avgtime = defaultdict(dict, {k: v.copy() for k, v in raw_results_avgtime.items()})
    plot_data_total_score = defaultdict(dict, {k: v.copy() for k, v in total_scores.items()})
    all_plot_dicts_to_average = [plot_data_runtime, plot_data_power, plot_data_avgtime, plot_data_total_score]
    for plot_dict in all_plot_dicts_to_average: add_averages_to_plot_data(plot_dict, data_files)
    data_files_for_plotting = data_files + ["Average"]
    end_overall_time = time.monotonic()
    print("\n"+"="*60); print(f"{'Overall Summary':^60}"); print("="*60)
    if overall_summary:
         print(f"{'JAR File':<30} {'Tests Passed':<15} {'Avg Total Score':<15}"); print("-" * 60)
         for jar, (passed, total) in sorted(overall_summary.items(), key=lambda item: os.path.basename(item[0])):
              avg_score_val = plot_data_total_score.get(jar, {}).get("Average")
              avg_score_str = f"{avg_score_val:.2f}" if avg_score_val is not None else "N/A"
              print(f"- {os.path.basename(jar):<28} {f'{passed}/{total}':<15} {avg_score_str:<15}")
    else: print("No results collected.")
    print("-" * 60); print(f"Total execution time: {end_overall_time - start_overall_time:.2f} seconds"); print("=" * 60)
    if enable_plotting:
        if MATPLOTLIB_AVAILABLE:
             print("\nGenerating requested plots..."); plot_runtime_results(plot_data_runtime, data_files_for_plotting)
             plot_power_consumption(plot_data_power, data_files_for_plotting); plot_weighted_avg_time(plot_data_avgtime, data_files_for_plotting)
             plot_total_score(plot_data_total_score, data_files_for_plotting); print("Plot generation attempt finished.")
        else: print("\nPlotting enabled, but matplotlib unavailable.")
    else: print("\nPlotting disabled.")
    print("\n"+"="*40); print("Checker run finished.")
    print(f"- Detailed reports in: '{REPORT_DIR}'"); print(f"- Full logs in: '{LOG_DIR}'"); print(f"- Validated outputs in: '{OUT_DIR}'")
    if enable_plotting and MATPLOTLIB_AVAILABLE: print(f"- Plots saved in current directory.")
    print("="*40)

# --- Script Entry Point ---
if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n\nExecution interrupted.", file=sys.stderr); sys.exit(1)
    except Exception as main_exc: print(f"\n\nFATAL UNHANDLED EXCEPTION:\n{main_exc}\n{traceback.format_exc()}", file=sys.stderr); sys.exit(2)