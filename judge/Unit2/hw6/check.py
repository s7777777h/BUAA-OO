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


# --- Configuration --- (Keep original)
DATA_DIR = "data"; OUT_DIR = "out"; LOG_DIR = "log"; REPORT_DIR = "report"
PLOT_FILENAME_RUNTIME = "runtime_comparison.png"; PLOT_FILENAME_POWER = "power_consumption.png"
PLOT_FILENAME_AVGTIME = "weighted_avg_time.png"; PLOT_FILENAME_TOTALSCORE = "total_score_comparison.png"
GENERATOR_SCRIPT = "data_generator.py"
# --- HW6 Specific Config --- (Keep original)
SOFT_TIMEOUT = 220.0; HARD_TIMEOUT = 250.0; MOVE_TIME_PER_FLOOR = 0.4; DOOR_OPEN_CLOSE_TIME = 0.4
SCHE_STOP_TIME = 1.0; ELEVATOR_CAPACITY = 6; NUM_ELEVATORS = 6; EPSILON = 1e-9; POLL_INTERVAL = 0.1
# --- Power Calculation Constants --- (Keep original)
POWER_OPEN = 0.1; POWER_CLOSE = 0.1; POWER_MOVE = 0.4
# --- Parallelism Configuration --- (Keep original)
PARALLEL_MODE = 'data'; DEFAULT_WORKERS=8; MAX_WORKERS=DEFAULT_WORKERS # Simplified assignment
try: DEFAULT_WORKERS = min(32, (os.cpu_count() or 1) + 4); MAX_WORKERS = DEFAULT_WORKERS
except AttributeError: pass # Keep default if cpu_count fails
# --- Floor definitions --- (Keep original)
FLOOR_MAP_STR_TO_INT = {"B4":-4,"B3":-3,"B2":-2,"B1":-1,"F1":1,"F2":2,"F3":3,"F4":4,"F5":5,"F6":6,"F7":7}
FLOOR_MAP_INT_TO_STR = {v: k for k, v in FLOOR_MAP_STR_TO_INT.items()}
MIN_FLOOR_INT, MAX_FLOOR_INT = -4, 7
# --- Regular Expressions --- (Keep original including SCHE_ACCEPT, LOG_LINE)
RE_TIMESTAMP = re.compile(r"\[\s*([\d.]+)\s*\]")
RE_INPUT_PASSENGER = re.compile(r"\[\s*([\d.]+)\s*\](\d+)-PRI-(\d+)-FROM-([BF]\d+)-TO-([BF]\d+)")
RE_INPUT_SCHE = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-(\d+)-([\d.]+)-([BF]\d+)")
RE_ARRIVE = re.compile(r"\[\s*([\d.]+)\s*\]ARRIVE-([BF]\d+)-(\d+)"); RE_OPEN = re.compile(r"\[\s*([\d.]+)\s*\]OPEN-([BF]\d+)-(\d+)"); RE_CLOSE = re.compile(r"\[\s*([\d.]+)\s*\]CLOSE-([BF]\d+)-(\d+)")
RE_IN = re.compile(r"\[\s*([\d.]+)\s*\]IN-(\d+)-([BF]\d+)-(\d+)"); RE_OUT = re.compile(r"\[\s*([\d.]+)\s*\]OUT-([SF])-(\d+)-([BF]\d+)-(\d+)")
RE_RECEIVE = re.compile(r"\[\s*([\d.]+)\s*\]RECEIVE-(\d+)-(\d+)"); RE_SCHE_BEGIN = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-BEGIN-(\d+)"); RE_SCHE_END = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-END-(\d+)")
RE_SCHE_ACCEPT = re.compile(r"\[\s*([\d.]+)\s*\]SCHE-ACCEPT-(\d+)-([\d.]+)-([BF]\d+)")
RE_LOG_LINE = re.compile(r"\[LOG\]")

# --- Helper Functions --- (Keep original)
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

# --- Runner Function with Stream Consuming Threads --- (Keep original)
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
            status_code = "ExecutionError"; full_stderr_str += f"\nChecker: Error sending input: {e}."

        process_terminated_normally = False
        if status_code != "ExecutionError":
            while True:
                current_time = time.monotonic()
                elapsed_time = current_time - start_time
                if elapsed_time > HARD_TIMEOUT:
                    if status_code != "Killed": status_code = "Killed"; full_stderr_str += f"\nChecker: Hard timeout ({HARD_TIMEOUT:.1f}s)."
                    try: process.kill()
                    except Exception: pass
                    break
                exit_code = process.poll()
                if exit_code is not None:
                    process_terminated_normally = True
                    if status_code not in ["Killed", "TLE"]: status_code = "ExecutionError" if exit_code != 0 else None
                    break
                if not tle_marked and elapsed_time > SOFT_TIMEOUT:
                    if status_code != "Killed": status_code = "TLE"; full_stderr_str += f"\nChecker: Soft timeout ({SOFT_TIMEOUT:.1f}s)."
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


# --- Define constants dependent on helper functions --- (Keep original)
F1_INT = floor_to_int('F1'); B1_INT = floor_to_int('B1')
VALID_SCHE_FLOORS_INT = {floor_to_int(f) for f in ["B2", "B1", "F1", "F2", "F3", "F4", "F5"]}
VALID_SCHE_SPEEDS = {0.2, 0.3, 0.4, 0.5}
# --- Validation Logic ---
class Validator:
    # --- __init__ and helper methods remain unchanged ---
    def __init__(self, all_input_requests):
        self.errors = []
        self.all_inputs = all_input_requests # This list now contains dicts with a 'claimed' key for SCHE type
        self.passenger_requests_dict = {req['id']: req for req in all_input_requests if req['type'] == 'passenger'}
        self.sim_time = 0.0
        self.elevators = {}
        self.passengers = {}
        self.active_passenger_assignments = {}
        self.open_count = 0; self.close_count = 0; self.move_count = 0

        for i in range(1, NUM_ELEVATORS + 1):
            self.elevators[i] = {'id': i, 'floor': F1_INT, 'state': 'CLOSED', 'passengers': set(),
                                 'last_action_time': 0.0, 'last_arrive_time': 0.0, 'open_time': -1.0,
                                 'sche_state': 'IDLE', 'sche_target_floor': None, 'sche_speed': None,
                                 'sche_begin_time': -1.0, 'active_receives': set()}
        for req in self.passenger_requests_dict.values():
            pid = req['id']
            self.passengers[pid] = {'id': pid, 'state': 'OUTSIDE', 'location': req['from'], 'destination': req['to'],
                                    'request_time': req['time'], 'priority': req['pri'], 'arrival_time': -1.0,
                                    'current_assignment': None, 'needs_pickup': False}
    def add_error(self, message):
        error_time_str = f"{max(0.0, self.sim_time):.4f}" if isinstance(self.sim_time, (int, float)) else "?.????"
        self.errors.append(f"[Time ~{error_time_str}] {message}")
    def _get_elevator_state(self, eid):
        if eid not in self.elevators: self.add_error(f"CRITICAL: Invalid Elevator ID {eid}"); return None
        return self.elevators[eid]
    def _get_passenger_state(self, pid):
        if pid not in self.passengers: self.add_error(f"CRITICAL: Invalid Passenger ID {pid}"); return None
        return self.passengers[pid]

    # --- validate_line --- Modified SCHE-BEGIN logic ---
    def validate_line(self, line):
        """Validates a single NON-LOG output line. Assumes pre-filtering."""
        line = line.strip()
        if not line: return True

        match_ts = RE_TIMESTAMP.match(line)
        if not match_ts: self.add_error(f"CRITICAL: Malformed line (no timestamp): {line}"); return False
        try: current_line_time = float(match_ts.group(1))
        except ValueError: self.add_error(f"CRITICAL: Malformed timestamp: {match_ts.group(1)}"); return False

        if current_line_time < 0: self.add_error(f"CRITICAL: Negative timestamp: {current_line_time}"); return False
        if current_line_time < self.sim_time - EPSILON * 10: self.add_error(f"Timestamp decreasing: {current_line_time:.4f} < {self.sim_time:.4f}")
        self.sim_time = max(self.sim_time, current_line_time)

        match_arrive = RE_ARRIVE.match(line); match_open = RE_OPEN.match(line); match_close = RE_CLOSE.match(line)
        match_in = RE_IN.match(line); match_out = RE_OUT.match(line); match_receive = RE_RECEIVE.match(line)
        match_sche_begin = RE_SCHE_BEGIN.match(line); match_sche_end = RE_SCHE_END.match(line)
        match_sche_accept = RE_SCHE_ACCEPT.match(line)

        try:
            # --- ARRIVE --- (Keep original logic)
            if match_arrive:
                _, floor_str, eid_str = match_arrive.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"ARRIVE Invalid: {line}"); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"ARRIVE-{floor_str}-{eid}: Door not CLOSED.")
                prev_floor = e_state['floor']; is_valid = (prev_floor == B1_INT and floor_int == F1_INT) or (prev_floor == F1_INT and floor_int == B1_INT) or (floor_int is not None and abs(floor_int - prev_floor) == 1)
                if not is_valid: self.add_error(f"ARRIVE-{floor_str}-{eid}: Invalid move from {int_to_floor(prev_floor)}.")
                if e_state['sche_state'] != 'ACTIVE':
                    exp_t = e_state['last_action_time'] + MOVE_TIME_PER_FLOOR
                    if current_line_time < exp_t - EPSILON: self.add_error(f"ARRIVE-{floor_str}-{eid}: Normal move too fast.")
                if e_state['sche_state'] == 'IDLE' and not e_state['passengers'] and not e_state['active_receives']: self.add_error(f"ARRIVE-{floor_str}-{eid}: Idle move.")
                e_state['floor'] = floor_int; e_state['last_action_time'] = current_line_time; e_state['last_arrive_time'] = current_line_time; self.move_count += 1
            # --- OPEN --- (Keep original logic)
            elif match_open:
                _, floor_str, eid_str = match_open.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"OPEN Invalid: {line}"); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"OPEN-{floor_str}-{eid}: Door not CLOSED.")
                if e_state['floor'] != floor_int: self.add_error(f"OPEN-{floor_str}-{eid}: Wrong floor {int_to_floor(e_state['floor'])}.")
                if e_state['sche_state'] == 'ACTIVE':
                    # This check NOW relies on sche_target_floor being correctly set by the *right* SCHE-BEGIN
                    if floor_int != e_state['sche_target_floor']: self.add_error(f"OPEN-{floor_str}-{eid}: Cannot OPEN during SCHE before target ({int_to_floor(e_state['sche_target_floor'])}).")
                    else: e_state['sche_state'] = 'OPEN_SCHE_TARGET'
                elif e_state['sche_state'] != 'IDLE': self.add_error(f"OPEN-{floor_str}-{eid}: Invalid OPEN during SCHE state {e_state['sche_state']}.")
                e_state['state'] = 'OPEN'; e_state['open_time'] = current_line_time; e_state['last_action_time'] = current_line_time; self.open_count += 1
            # --- CLOSE --- (Keep original logic)
            elif match_close:
                _, floor_str, eid_str = match_close.groups(); eid = int(eid_str); floor_int = floor_to_int(floor_str)
                e_state = self._get_elevator_state(eid)
                if floor_int is None or e_state is None: self.add_error(f"CLOSE Invalid: {line}"); return True
                if e_state['state'] != 'OPEN': self.add_error(f"CLOSE-{floor_str}-{eid}: Door not OPEN.")
                if e_state['floor'] != floor_int: self.add_error(f"CLOSE-{floor_str}-{eid}: Wrong floor {int_to_floor(e_state['floor'])}.")
                min_dur = DOOR_OPEN_CLOSE_TIME
                if e_state['sche_state'] == 'OPEN_SCHE_TARGET':
                    min_dur = max(min_dur, SCHE_STOP_TIME); exp_t = e_state['open_time'] + min_dur
                    if current_line_time < exp_t - EPSILON: self.add_error(f"CLOSE-{floor_str}-{eid}: Closed too fast after SCHE OPEN.")
                    e_state['sche_state'] = 'CLOSED_SCHE_TARGET'
                else:
                    exp_t = e_state['open_time'] + min_dur
                    if current_line_time < exp_t - EPSILON: self.add_error(f"CLOSE-{floor_str}-{eid}: Normal door closed too fast.")
                e_state['state'] = 'CLOSED'; e_state['open_time'] = -1.0; e_state['last_action_time'] = current_line_time; self.close_count += 1
            # --- IN --- (Keep original logic)
            elif match_in:
                _, pid_s, floor_s, eid_s = match_in.groups(); pid=int(pid_s); eid=int(eid_s); floor_i=floor_to_int(floor_s)
                p_state = self._get_passenger_state(pid); e_state = self._get_elevator_state(eid)
                if floor_i is None or p_state is None or e_state is None: self.add_error(f"IN Invalid: {line}"); return True
                if e_state['state']!='OPEN': self.add_error(f"IN-{pid}-{floor_s}-{eid}: Door not OPEN.")
                if e_state['floor']!=floor_i: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Elevator wrong floor.")
                if p_state['state'] not in ['OUTSIDE','NEEDS_PICKUP']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger not OUTSIDE.")
                if p_state['location']!=floor_i: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger wrong floor.")
                if len(e_state['passengers'])>=ELEVATOR_CAPACITY: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Elevator full.")
                if pid in e_state['passengers']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Passenger already IN.")
                if p_state['current_assignment']!=eid: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Wrong assignment {p_state['current_assignment']}.")
                if pid not in e_state['active_receives']: self.add_error(f"IN-{pid}-{floor_s}-{eid}: Not in active_receives.")
                if e_state['sche_state']!='IDLE': self.add_error(f"IN-{pid}-{floor_s}-{eid}: Cannot enter during SCHE.")
                e_state['passengers'].add(pid);
                if pid in e_state['active_receives']: e_state['active_receives'].remove(pid)
                if self.active_passenger_assignments.get(pid)==eid: del self.active_passenger_assignments[pid]
                p_state['state']='INSIDE';p_state['location']=eid;p_state['current_assignment']=None;p_state['needs_pickup']=False
            # --- OUT --- (Keep original logic)
            elif match_out:
                _, flag, pid_s, floor_s, eid_s = match_out.groups(); pid=int(pid_s); eid=int(eid_s); floor_i=floor_to_int(floor_s)
                p_state = self._get_passenger_state(pid); e_state = self._get_elevator_state(eid)
                if floor_i is None or p_state is None or e_state is None: self.add_error(f"OUT Invalid: {line}"); return True
                if e_state['state']!='OPEN': self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Door not OPEN.")
                if e_state['floor']!=floor_i: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Elevator wrong floor.")
                if p_state['state']!='INSIDE': self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger not INSIDE.")
                if p_state['location']!=eid: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger wrong elevator {p_state['location']}.")
                if pid not in e_state['passengers']: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Passenger not in list.")
                if e_state['sche_state'] not in ['IDLE','OPEN_SCHE_TARGET']: self.add_error(f"OUT-{flag}-{pid}-{floor_s}-{eid}: Cannot exit during SCHE state {e_state['sche_state']}.")
                dest_reached = (floor_i == p_state['destination'])
                if flag=='S':
                    if dest_reached: p_state['state']='ARRIVED'; p_state['arrival_time']=current_line_time
                    else: self.add_error(f"OUT-S-{pid}-{floor_s}-{eid}: Flag S but dest not reached."); p_state['state']='OUTSIDE'; p_state['needs_pickup']=True
                elif flag=='F':
                    if not dest_reached: p_state['state']='OUTSIDE'; p_state['needs_pickup']=True
                    else: self.add_error(f"OUT-F-{pid}-{floor_s}-{eid}: Flag F but dest reached."); p_state['state']='ARRIVED'; p_state['arrival_time']=current_line_time
                if pid in e_state['passengers']: e_state['passengers'].remove(pid)
                p_state['location']=floor_i
            # --- RECEIVE --- (Keep original logic)
            elif match_receive:
                _, pid_s, eid_s = match_receive.groups(); pid=int(pid_s); eid=int(eid_s)
                p_state=self._get_passenger_state(pid); e_state=self._get_elevator_state(eid)
                if p_state is None or e_state is None: self.add_error(f"RECEIVE Invalid: {line}"); return True
                if p_state['state'] not in ['OUTSIDE','NEEDS_PICKUP']: self.add_error(f"RECEIVE-{pid}-{eid}: Passenger not OUTSIDE.")
                existing=self.active_passenger_assignments.get(pid)
                if existing is not None and existing!=eid: self.add_error(f"RECEIVE-{pid}-{eid}: Double assignment (prev: {existing}).")
                if e_state['sche_state']!='IDLE': self.add_error(f"RECEIVE-{pid}-{eid}: Cannot assign during SCHE.")
                if existing!=eid:
                    if existing is not None and existing in self.elevators:
                        if pid in self.elevators[existing]['active_receives']: self.elevators[existing]['active_receives'].remove(pid)
                    e_state['active_receives'].add(pid); p_state['current_assignment']=eid; self.active_passenger_assignments[pid]=eid

            # <--- MODIFICATION START: Updated SCHE-BEGIN logic ---
            elif match_sche_begin:
                _, eid_str = match_sche_begin.groups(); eid = int(eid_str)
                e_state = self._get_elevator_state(eid)
                if e_state is None: self.add_error(f"SCHE-BEGIN Invalid: {line}"); return True
                if e_state['state'] != 'CLOSED': self.add_error(f"SCHE-BEGIN-{eid}: Door not CLOSED.")
                if e_state['sche_state'] != 'IDLE': self.add_error(f"SCHE-BEGIN-{eid}: Not IDLE state.")

                # Find the FIRST UNCLAIMED SCHE input request for this elevator
                found_sche_input = None
                input_req_index = -1 # Keep track of index if needed, or just the object
                for idx, req in enumerate(self.all_inputs):
                    if req.get('type') == 'sche' and req.get('eid') == eid and not req.get('claimed', False):
                        found_sche_input = req
                        # Mark the request as claimed IN THE VALIDATOR'S COPY of inputs
                        req['claimed'] = True # Modify the dict in self.all_inputs
                        break # Found the first unclaimed one

                if found_sche_input:
                     e_state['sche_target_floor'] = found_sche_input['to']
                     e_state['sche_speed'] = found_sche_input['speed']
                     # print(f"DEBUG Validator: SCHE-BEGIN-{eid} matched to input: {found_sche_input}") # Optional Debug
                else:
                     # This might happen if SCHE-BEGIN is output without a corresponding valid input
                     # Or if all inputs for this elevator were already claimed.
                     self.add_error(f"SCHE-BEGIN-{eid}: WARNING - Could not find an unclaimed matching SCHE input request.")
                     e_state['sche_target_floor'] = None
                     e_state['sche_speed'] = None

                # Update SCHE state in validator
                e_state['sche_state'] = 'ACTIVE'
                e_state['sche_begin_time'] = current_line_time

                # Cancel active RECEIVEs for this elevator for passengers *outside* (Keep original logic)
                receives_to_cancel = list(e_state['active_receives'])
                for received_pid in receives_to_cancel:
                    rcv_p_state = self._get_passenger_state(received_pid)
                    if rcv_p_state and rcv_p_state['state'] in ['OUTSIDE', 'NEEDS_PICKUP']:
                        e_state['active_receives'].remove(received_pid)
                        if self.active_passenger_assignments.get(received_pid) == eid: del self.active_passenger_assignments[received_pid]
                        if rcv_p_state['current_assignment'] == eid: rcv_p_state['current_assignment'] = None
            # <--- MODIFICATION END ---

            # --- SCHE-END --- (Keep original logic)
            elif match_sche_end:
                _, eid_s = match_sche_end.groups(); eid=int(eid_s)
                e_state=self._get_elevator_state(eid)
                if e_state is None: self.add_error(f"SCHE-END Invalid: {line}"); return True
                if e_state['sche_state']!='CLOSED_SCHE_TARGET': self.add_error(f"SCHE-END-{eid}: Not CLOSED_SCHE_TARGET.")
                if e_state['state']!='CLOSED': self.add_error(f"SCHE-END-{eid}: Door not CLOSED.")
                if e_state['passengers']: self.add_error(f"SCHE-END-{eid}: Elevator not empty.")
                e_state['sche_state']='IDLE'; e_state['sche_target_floor']=None; e_state['sche_speed']=None; e_state['sche_begin_time']=-1.0

            # --- SCHE-ACCEPT --- (Keep original logic from previous fix)
            elif match_sche_accept:
                _ts, eid_s, speed_s, floor_s = match_sche_accept.groups();
                try:
                    eid=int(eid_s); speed=float(speed_s); floor_i=floor_to_int(floor_s)
                    if not (1<=eid<=NUM_ELEVATORS): self.add_error(f"SCHE-ACCEPT Invalid eid: {line}")
                    if not any(abs(speed-v)<EPSILON for v in VALID_SCHE_SPEEDS): self.add_error(f"SCHE-ACCEPT Invalid speed: {line}")
                    if floor_i not in VALID_SCHE_FLOORS_INT: self.add_error(f"SCHE-ACCEPT Invalid floor: {line}")
                except ValueError: self.add_error(f"SCHE-ACCEPT Invalid numeric: {line}")
                pass # Acknowledged

            # --- Unknown Line --- (Keep original logic)
            else: self.add_error(f"WARNING: Unrecognized output line format: {line}")

        except ValueError as ve: # Keep original exception handling
             self.add_error(f"CRITICAL: Invalid integer ID/value: {line} ({ve})"); return False
        except Exception as e:
            self.add_error(f"CRITICAL: Internal Validator Error on '{line}': {e}\n{traceback.format_exc(limit=3)}"); return False

        return True

    # --- final_checks, get_errors, get_final_sim_time, metric calculations remain unchanged ---
    def final_checks(self):
        for pid, p_state in self.passengers.items():
            if p_state.get('state') != 'ARRIVED':
                req = self.passenger_requests_dict.get(pid)
                if not req: self.add_error(f"P{pid} (details missing) !ARRIVED."); continue
                loc = 'N/A'; cur_loc = p_state.get('location'); state = p_state.get('state','?')
                if state == 'INSIDE': loc = f"Elevator {cur_loc}"
                elif state in ['OUTSIDE','NEEDS_PICKUP']: loc = int_to_floor(cur_loc)
                else: loc = f"State: {state}"
                self.add_error(f"P{pid} (Pri={p_state.get('priority','?')}) !Reach dest {int_to_floor(req['to'])} (final: {state} at {loc}).")
        for eid, e_state in self.elevators.items():
            if e_state.get('state') != 'CLOSED': self.add_error(f"E{eid} !CLOSED.")
            if e_state.get('passengers'): self.add_error(f"E{eid} finished w/ passengers: {sorted(list(e_state['passengers']))}.")
            if e_state.get('sche_state') != 'IDLE': self.add_error(f"E{eid} finished !IDLE SCHE state: {e_state.get('sche_state')}.")
        if self.active_passenger_assignments: self.add_error(f"Finished w/ active assignments: {self.active_passenger_assignments}")
    def get_errors(self): return self.errors
    def get_final_sim_time(self): return self.sim_time if self.sim_time > 0 else 0.0
    def get_power_consumption(self):
        return (POWER_OPEN * self.open_count + POWER_CLOSE * self.close_count + POWER_MOVE * self.move_count)
    def get_weighted_average_completion_time(self):
        total_weighted_time = 0; total_priority = 0; passengers_arrived_count = 0
        for pid, p_state in self.passengers.items():
            if p_state.get('state') == 'ARRIVED':
                arrival_time = p_state.get('arrival_time', -1.0); request_time = p_state.get('request_time', -1.0)
                priority = p_state.get('priority', 0)
                if arrival_time >= 0 and request_time >= 0 and priority > 0:
                    completion_time = arrival_time - request_time
                    if completion_time >= -EPSILON:
                        total_weighted_time += max(0, completion_time) * priority
                        total_priority += priority; passengers_arrived_count += 1
                    else: self.add_error(f"WARN: P{pid} arrival < request ({arrival_time:.4f} < {request_time:.4f})")
        if total_priority > 0: return total_weighted_time / total_priority
        else: return 0.0

# --- Plotting Functions --- (Keep original logic + average handling)
def plot_metric(plot_data, data_files_sorted_with_avg, y_label, title, output_filename):
    if not MATPLOTLIB_AVAILABLE: return
    if not any(plot_data.values()): return
    print(f"Generating plot '{output_filename}'...")
    try:
        x_labels=[os.path.splitext(df)[0] if df!="Average" else "Average" for df in data_files_sorted_with_avg]
        x_indices=range(len(x_labels))
        fig,ax=plt.subplots(figsize=(max(10,len(x_labels)*0.5),6)); jar_names=sorted(plot_data.keys())
        for jar_file in jar_names:
            jar_data=plot_data[jar_file]; y_values=[jar_data.get(df) for df in data_files_sorted_with_avg]
            valid_indices=[i for i,y in enumerate(y_values) if y is not None]; valid_y=[y for y in y_values if y is not None]
            if valid_indices:
                line, = ax.plot([x_indices[i] for i in valid_indices], valid_y, marker='o', linestyle='-', label=os.path.basename(jar_file)) # Get line object
                if "Average" in data_files_sorted_with_avg:
                    avg_idx=data_files_sorted_with_avg.index("Average")
                    if avg_idx in valid_indices:
                        avg_val=jar_data.get("Average")
                        if avg_val is not None: ax.plot(avg_idx, avg_val, marker='*', markersize=10, markeredgecolor='black', markerfacecolor=line.get_color(), linestyle='None') # Use line color
        ax.set_xlabel("Test Case"); ax.set_ylabel(y_label); ax.set_title(title)
        ax.set_xticks(x_indices); ax.set_xticklabels(x_labels, rotation=45, ha='right')
        if "Average" in x_labels: ax.axvline(x=len(x_labels)-1.5, color='gray', linestyle='--', alpha=0.7)
        ax.legend(title="JAR Files", bbox_to_anchor=(1.04,1), loc="upper left"); ax.grid(True, axis='y', linestyle='--', alpha=0.7); ax.set_ylim(bottom=0)
        fig.tight_layout(rect=[0, 0, 0.85, 1]); plt.savefig(output_filename, bbox_inches='tight'); plt.close(fig)
        print(f"Plot '{output_filename}' saved successfully.")
    except Exception as plot_e: print(f"\nError generating plot '{output_filename}': {plot_e}", file=sys.stderr)

def plot_runtime_results(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_RUNTIME):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    if not any(plot_data.values()): print("\nWarn: No runtime data.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Completion Time (s)", "JAR Runtime Comparison (Successful Runs)", output_filename)
def plot_power_consumption(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_POWER):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    if not any(plot_data.values()): print("\nWarn: No power data.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Power Consumption (Units)", "JAR Power Consumption Comparison (Successful Runs)", output_filename)
def plot_weighted_avg_time(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_AVGTIME):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    if not any(plot_data.values()): print("\nWarn: No weighted time data.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Weighted Avg Completion Time (s)", "JAR Weighted Avg Passenger Time (Successful Runs)", output_filename)
def plot_total_score(plot_data, data_files_sorted_with_avg, output_filename=PLOT_FILENAME_TOTALSCORE):
    if not MATPLOTLIB_AVAILABLE: print("\nWarn: matplotlib unavailable.", file=sys.stderr); return
    if not any(plot_data.values()): print("\nWarn: No total score data.", file=sys.stderr); return
    plot_metric(plot_data, data_files_sorted_with_avg, "Total Score (Points)", "JAR Total Score Comparison (Successful Runs)", output_filename)


# --- Function to Run a Single Test Case ---
def run_single_test_case(jar_file, data_file, data_dir, out_dir, log_dir):
    """Based on original function. Runs test, saves log/output, validates."""
    data_file_path = os.path.join(data_dir, data_file)
    jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    data_file_base = os.path.splitext(data_file)[0]
    log_file_name = f"{jar_name_base}_{data_file_base}.log"
    log_file_path = os.path.join(log_dir, log_file_name)
    output_file_name = f"{jar_name_base}_{data_file_base}.out"
    output_file_path_filtered = os.path.join(out_dir, output_file_name)

    errors = []; stdout_data, stderr_data = "", ""; execution_time, run_status_code = 0, None
    result_status = "CHECKER_ERROR"; final_sim_time = 0.0; power_consumption = 0.0; weighted_avg_time = 0.0
    # total_score removed from here

    try:
        # <--- MODIFICATION START: Add 'claimed' flag during input parsing ---
        input_str = ""; parsed_inputs = []; parse_error = False
        try:
            with open(data_file_path, 'r', encoding='utf-8', errors='replace') as f: input_lines = f.readlines(); input_str = "".join(input_lines)
            for line_num, line in enumerate(input_lines):
                line = line.strip();
                if not line: continue
                match_p = RE_INPUT_PASSENGER.match(line); match_s = RE_INPUT_SCHE.match(line)
                if match_p:
                    t, p, pri, f_s, to_s = match_p.groups(); fi, toi = floor_to_int(f_s), floor_to_int(to_s)
                    if fi is None or toi is None: errors.append(f"Input L{line_num+1}: Invalid floor."); parse_error = True; break
                    try: parsed_inputs.append({'type': 'passenger', 'time': float(t), 'id': int(p), 'pri': int(pri), 'from': fi, 'to': toi})
                    except ValueError as ve: errors.append(f"Input L{line_num+1}: Invalid number: {ve}"); parse_error = True; break
                elif match_s:
                    t, e, spd_s, fl_s = match_s.groups(); fli = floor_to_int(fl_s)
                    if fli is None: errors.append(f"Input L{line_num+1}: Invalid SCHE floor."); parse_error = True; break
                    try:
                        eid = int(e); speed = float(spd_s)
                        if fli not in VALID_SCHE_FLOORS_INT: errors.append(f"Input L{line_num+1}: Invalid SCHE target floor."); parse_error = True; break
                        if not any(abs(speed - v) < EPSILON for v in VALID_SCHE_SPEEDS): errors.append(f"Input L{line_num+1}: Invalid SCHE speed."); parse_error = True; break
                        if not (1 <= eid <= NUM_ELEVATORS): errors.append(f"Input L{line_num+1}: Invalid SCHE elevator ID."); parse_error = True; break
                        # Add the 'claimed' flag for SCHE requests
                        parsed_inputs.append({'type': 'sche', 'time': float(t), 'eid': eid, 'speed': speed, 'to': fli, 'claimed': False})
                    except ValueError as ve: errors.append(f"Input L{line_num+1}: Invalid SCHE number: {ve}"); parse_error = True; break
                else: errors.append(f"Input L{line_num+1}: Malformed line."); parse_error = True; break
        except FileNotFoundError: raise FileNotFoundError(f"Input file not found: {data_file_path}")
        except Exception as e: raise Exception(f"Error reading/parsing input {data_file_path}: {e}")
        # <--- MODIFICATION END ---

        if parse_error: result_status = "INPUT_ERROR"
        else:
            # --- Run Java Program ---
            stdout_data, stderr_data, execution_time, run_status_code = run_java_program_with_threads(jar_file, input_str)

            # --- Save Full Log File ---
            try:
                with open(log_file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"--- STDOUT ---\n{stdout_data}")
                    if stderr_data: f.write("\n\n--- STDERR ---\n" + stderr_data)
            except IOError as e: errors.append(f"Warning: Failed to write log file {log_file_path}: {e}")

            # --- Filter stdout and Save Filtered Output File (.out) ---
            all_stdout_lines = stdout_data.splitlines()
            filtered_output_lines = [line for line in all_stdout_lines if not RE_LOG_LINE.search(line)]
            clean_stdout_data_for_saving = "\n".join(filtered_output_lines)
            try:
                with open(output_file_path_filtered, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(clean_stdout_data_for_saving)
            except IOError as e: errors.append(f"Warning: Failed to write filtered output file {output_file_path_filtered}: {e}")

            # --- Determine Initial Status --- (Original logic)
            initial_run_status = "OK"
            if run_status_code == "Killed": initial_run_status = "TIMEOUT_HARD"
            elif run_status_code == "TLE": initial_run_status = "TIMEOUT_SOFT"
            elif run_status_code == "ExecutionError": initial_run_status = "RUNTIME_ERROR"
            elif run_status_code == "JavaNotFound": initial_run_status = "JAVA_ERROR"
            elif run_status_code is not None: initial_run_status = "CHECKER_ERROR"; errors.append(f"Unknown run_status_code: {run_status_code}")

            # --- Validate Output (using filtered lines) ---
            if initial_run_status not in ["JAVA_ERROR", "CHECKER_ERROR", "INPUT_ERROR"]:
                if not clean_stdout_data_for_saving.strip():
                    if initial_run_status == "OK": result_status = "WRONG_ANSWER"; errors.append("Validation Error: No non-log output.")
                    else: result_status = initial_run_status; errors.append("INFO: No non-log output before timeout/error.")
                else:
                    # Pass the modified parsed_inputs (with 'claimed' flag)
                    validator = Validator(parsed_inputs)
                    validation_stopped = False
                    for output_line in filtered_output_lines:
                        if not validator.validate_line(output_line):
                            validation_stopped = True; break
                    if not validation_stopped: validator.final_checks()

                    validation_errors = validator.get_errors()
                    final_sim_time = validator.get_final_sim_time()
                    if not validation_stopped:
                        power_consumption = validator.get_power_consumption()
                        weighted_avg_time = validator.get_weighted_average_completion_time()

                    if validation_errors:
                        errors.extend(validation_errors)
                        result_status = initial_run_status if initial_run_status != "OK" else "WRONG_ANSWER"
                    elif initial_run_status == "OK": result_status = "PASSED"
                    else: result_status = initial_run_status

            else: # Java/Checker/Input Error
                 result_status = initial_run_status
                 if result_status == "JAVA_ERROR" and not any("java" in e.lower() for e in errors): errors.append("Failed: Java command issue.")
                 if result_status == "INPUT_ERROR" and not any("Input Error" in e for e in errors): errors.append("Checker Error: Input data parsing error.")

    except FileNotFoundError as e: errors.append(f"Checker Error: {e}"); result_status = "CHECKER_ERROR"
    except MemoryError: errors.append(f"Checker Error: Out of memory."); result_status = "CHECKER_ERROR"
    except Exception as e: errors.append(f"Checker Error for {data_file}: {e}\n{traceback.format_exc(limit=3)}"); result_status = "CHECKER_ERROR"

    # Add generic status messages if needed (Original logic)
    if result_status == "TIMEOUT_HARD" and not any("Hard timeout" in e for e in errors): errors.append(f"Failed: Hard timeout ({HARD_TIMEOUT:.1f}s).")
    if result_status == "TIMEOUT_SOFT" and not any("Soft timeout" in e for e in errors): errors.append(f"Warning: Soft timeout ({SOFT_TIMEOUT:.1f}s).")
    if result_status == "RUNTIME_ERROR" and not any("Runtime Error" in e or "non-zero code" in e for e in errors): errors.append(f"Failed: Runtime Error or Non-zero Exit.")
    if result_status == "CHECKER_ERROR" and not errors: errors.append("Checker Error: Unknown internal issue.")

    # Return RAW metrics (total_score calculated later)
    return {
        "data_file": data_file, "status": result_status, "sim_time": final_sim_time,
        "exec_time": execution_time, "power": power_consumption, "avg_time": weighted_avg_time,
        "errors": errors
    }


# --- Function to Test a Single JAR ---
def test_single_jar(jar_file, all_data_files, data_dir, out_dir, log_dir, report_dir):
    """Based on original function. Tests JAR, collects RAW results."""
    jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
    report_lines = []; passed_tests = 0; failed_tests = 0; total_tests = len(all_data_files)
    jar_plot_data_runtime = {}; jar_plot_data_power = {}; jar_plot_data_avgtime = {}

    print(f"Starting tests for {jar_file}...")
    for i, data_file in enumerate(all_data_files):
        result = run_single_test_case(jar_file, data_file, data_dir, out_dir, log_dir)
        result_status = result["status"]
        report_time = result["sim_time"] if result_status in ["PASSED", "TIMEOUT_SOFT", "WRONG_ANSWER"] else result["exec_time"]
        report_lines.append(f"{result['data_file']}: {result_status} ({report_time:.2f}s)")
        if result_status == "PASSED":
            passed_tests += 1
            jar_plot_data_runtime[data_file] = result["sim_time"]
            jar_plot_data_power[data_file] = result["power"]
            jar_plot_data_avgtime[data_file] = result["avg_time"]
        else:
            failed_tests += 1; report_lines.extend([f"    - {err}" for err in result['errors']])
        if result_status == "JAVA_ERROR":
             print(f"Java error for {jar_file}, aborting.", file=sys.stderr)
             remaining = total_tests - (i + 1); failed_tests += remaining
             for skipped in all_data_files[i+1:]: report_lines.append(f"{skipped}: JAVA_ERROR (Skipped)")
             break
    report_path = os.path.join(report_dir, f"{jar_name_base}.report")
    try:
        with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(f"Report: {jar_file}\nOverall: {passed_tests}/{total_tests} passed ({failed_tests} failed).\n{'='*20}\n")
            f.write("\n".join(report_lines) + "\n")
        print(f"Finished {jar_file}. Report saved to '{report_path}'")
    except IOError as e: print(f"Error writing report '{report_path}': {e}", file=sys.stderr)
    # Return RAW data
    return (jar_file, passed_tests, total_tests, jar_plot_data_runtime, jar_plot_data_power, jar_plot_data_avgtime)


# --- Score Calculation Functions --- (Copied from previous correct version)
def calculate_relative_score(value, min_val, max_val):
    """Calculates the relative score r(d) based on min/max for a single value."""
    if value is None: return 0.0
    if abs(max_val - min_val) < EPSILON: return 15.0
    clamped_value = max(min_val, min(value, max_val))
    score = 15.0 * (max_val - clamped_value) / (max_val - min_val)
    return score

def process_scores(raw_metric_results, data_files, jar_files):
    """Calculates relative scores (r(d)) and total scores."""
    scores_power = defaultdict(dict); scores_runtime = defaultdict(dict)
    scores_avgtime = defaultdict(dict); total_scores = defaultdict(dict)
    metric_keys = ['power', 'sim_time', 'avg_time']
    score_dicts = {'power': scores_power, 'sim_time': scores_runtime, 'avg_time': scores_avgtime}
    raw_data_map = {'power': raw_metric_results.get('power',{}),
                    'sim_time': raw_metric_results.get('sim_time',{}),
                    'avg_time': raw_metric_results.get('avg_time',{})}

    for metric_key in metric_keys:
        score_dict = score_dicts[metric_key]; raw_data = raw_data_map[metric_key]
        print(f"Calculating relative scores for: {metric_key}...")
        for data_file in data_files:
            values = [raw_data.get(jf,{}).get(data_file) for jf in jar_files if isinstance(raw_data.get(jf,{}).get(data_file), (int, float))]
            if not values:
                print(f"  Warn: No valid results for {data_file}/{metric_key}. Scores=0.")
                for jf in jar_files: score_dict[jf][data_file] = 0.0
                continue
            try: min_v=min(values); max_v=max(values)
            except ValueError: print(f"  Error min/max {data_file}/{metric_key}. Scores=0."); min_v=max_v=None
            for jf in jar_files:
                orig_v = raw_data.get(jf,{}).get(data_file)
                if orig_v is None or not isinstance(orig_v,(int,float)) or min_v is None: score_dict[jf][data_file]=0.0
                else: score_dict[jf][data_file]=calculate_relative_score(orig_v, min_v, max_v)
        print(f"Finished scores for {metric_key}.")

    print("Calculating total scores...")
    for jf in jar_files:
        for df in data_files:
            rp = scores_power.get(jf,{}).get(df,0.0); rr = scores_runtime.get(jf,{}).get(df,0.0); ra = scores_avgtime.get(jf,{}).get(df,0.0)
            total_scores[jf][df] = (0.4 * rp + 0.3 * rr + 0.3 * ra)
    print("Finished total scores.")
    return scores_power, scores_runtime, scores_avgtime, total_scores

def add_averages_to_plot_data(plot_data_dict, data_files):
    """Adds an 'Average' entry to each JAR's plot data."""
    print(f"Calculating averages for plot data...")
    for jar_file, data_map in plot_data_dict.items():
        values = [data_map.get(df) for df in data_files if data_map.get(df) is not None]
        if values:
            try: average = np.mean(values); plot_data_dict[jar_file]["Average"] = average
            except Exception as e: print(f"  Warn: Avg calc failed for {jar_file}: {e}"); plot_data_dict[jar_file]["Average"] = None
        else: plot_data_dict[jar_file]["Average"] = None
    print("Finished calculating averages.")

# --- Main Execution Logic ---
def main():
    print("Elevator Simulation Checker (HW6 Version - Modified)"); print("-" * 30)
    # Ensure directories exist
    for dir_path in [DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR]:
        try: os.makedirs(dir_path, exist_ok=True)
        except OSError as e: print(f"Error creating dir {dir_path}: {e}", file=sys.stderr); sys.exit(1)

    # Plotting Switch
    enable_plotting = False
    if MATPLOTLIB_AVAILABLE:
        while True:
            try: choice = input("Enable plotting (requires matplotlib)? (y/n): ").lower().strip()
            except EOFError: print("\nNo input, disabling plotting."); choice = 'n'
            if choice == 'y': enable_plotting = True; print("Plotting enabled."); break
            elif choice == 'n': enable_plotting = False; print("Plotting disabled."); break
            else: print("Invalid input.")
    else: print("\nInfo: matplotlib unavailable. Plotting disabled.")

    # Data Generation (Original logic)
    use_generator = False; # ... (keep original generation logic) ...
    if os.path.isfile(GENERATOR_SCRIPT):
        while True:
            try: choice = input(f"Generate new data using {GENERATOR_SCRIPT}? (y/n): ").lower().strip()
            except EOFError: print("\nNo input, assuming 'n'."); choice = 'n'
            if choice == 'y': use_generator = True; break
            elif choice == 'n': break
            else: print("Invalid input.")
    else: print(f"Info: Generator script '{GENERATOR_SCRIPT}' not found.")
    if use_generator:
        print(f"\nClearing '{DATA_DIR}'..."); clear_directory(DATA_DIR)
        print(f"Running '{GENERATOR_SCRIPT}'...");
        try:
            proc = subprocess.run([sys.executable, GENERATOR_SCRIPT], text=True, check=False)
            if proc.returncode != 0: print(f"\nError: Generator failed (code {proc.returncode}).", file=sys.stderr); sys.exit(1)
            if not find_files(DATA_DIR, ".txt"): print(f"\nWarning: No '.txt' files found in '{DATA_DIR}'.", file=sys.stderr)
            else: print("Data generation complete.")
        except Exception as e: print(f"\nError running generator: {e}", file=sys.stderr); sys.exit(1)

    # File Discovery (Original logic)
    jar_files = find_files(".", ".jar")
    try: data_files = find_files(DATA_DIR, ".txt")
    except FileNotFoundError: print(f"Error: Data dir '{DATA_DIR}' not found.", file=sys.stderr); sys.exit(1)
    if not jar_files: print("Error: No .jar files found.", file=sys.stderr); sys.exit(1)
    if not data_files: print(f"Error: No .txt data files in '{DATA_DIR}'.", file=sys.stderr); sys.exit(1)
    print(f"\nFound {len(jar_files)} JAR(s): {', '.join([os.path.basename(j) for j in jar_files])}")
    print(f"Found {len(data_files)} test case(s) in '{DATA_DIR}'.")

    # Clear previous output/logs
    print(f"\nClearing '{OUT_DIR}' and '{LOG_DIR}'...")
    clear_directory(OUT_DIR); clear_directory(LOG_DIR)

    # Data Structures for RAW Results
    raw_results_runtime = defaultdict(dict)
    raw_results_power = defaultdict(dict)
    raw_results_avgtime = defaultdict(dict)

    # Select Execution Mode (Original logic)
    workers = min(MAX_WORKERS, DEFAULT_WORKERS)
    print(f"\nUsing parallel mode: '{PARALLEL_MODE}' with up to {workers} worker(s)")
    overall_summary = {}; start_overall_time = time.monotonic()

    # --- Execute Tests (Collect RAW results) ---
    if PARALLEL_MODE == 'none':
        print("Running tests sequentially...")
        for jar_file in jar_files:
            # test_single_jar returns raw results
            _jar, passed, total, jr, jp, jt = test_single_jar(jar_file, data_files, DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR)
            overall_summary[jar_file] = (passed, total)
            if jr: raw_results_runtime[jar_file] = jr
            if jp: raw_results_power[jar_file] = jp
            if jt: raw_results_avgtime[jar_file] = jt
    elif PARALLEL_MODE == 'data':
        print(f"Running tests parallel ('data' mode, workers={workers})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for jar_file in jar_files:
                print("\n"+"="*30); print(f"Submitting tests for {jar_file}..."); print("="*30)
                jar_name_base = os.path.splitext(os.path.basename(jar_file))[0]
                report_map = {}; passed, failed, total = 0, 0, len(data_files)
                futures_map = {executor.submit(run_single_test_case, jar_file, df, DATA_DIR, OUT_DIR, LOG_DIR): df for df in data_files}
                # Local dicts for RAW results
                jar_raw_runtime, jar_raw_power, jar_raw_avgtime = {}, {}, {}
                java_error = False; processed = 0
                print(f"All {total} tests for {jar_file} submitted, processing...")
                for future in concurrent.futures.as_completed(futures_map):
                    df = futures_map[future]; processed += 1
                    print(f"  Completed {df} ({processed}/{total} for {jar_file})...", end='\r')
                    try:
                        result = future.result(); report_map[df] = result; status = result['status']
                        rtime = result["sim_time"] if status in ["PASSED","TIMEOUT_SOFT","WRONG_ANSWER"] else result["exec_time"]
                        if status == "PASSED":
                            passed += 1
                            jar_raw_runtime[df] = result["sim_time"]
                            jar_raw_power[df] = result["power"]
                            jar_raw_avgtime[df] = result["avg_time"]
                        else: # Failed case
                            failed += 1; print(f"  Failed: {df} ({jar_file}) - {status} ({rtime:.2f}s)      ")
                            for i,err in enumerate(result['errors']):
                                if i<3: print(f"      - {str(err).replace(chr(10),' ')[:150]}{'...' if len(str(err))>150 else ''}")
                            if len(result['errors'])>3: print(f"      - ... ({len(result['errors'])-3} more errors)")
                            if status=="JAVA_ERROR": java_error=True
                    except Exception as exc:
                        print(f"\nCRITICAL Error result for {df} ({jar_file}): {exc}", file=sys.stderr)
                        report_map[df] = {"data_file": df, "status": "CHECKER_ERROR", "errors": [f"Exception: {exc}"]}; failed += 1
                print("\n"+"-"*30); summary = f"Finished {jar_file}. Results: {passed}/{total} passed, {failed} failed"
                print(summary); overall_summary[jar_file]=(passed,total)
                if java_error: print(f"  (Note: JAVA_ERROR encountered)")
                # Merge RAW results
                if jar_raw_runtime: raw_results_runtime[jar_file] = jar_raw_runtime
                if jar_raw_power: raw_results_power[jar_file] = jar_raw_power
                if jar_raw_avgtime: raw_results_avgtime[jar_file] = jar_raw_avgtime
                # Write Report (Original logic)
                report_path = os.path.join(REPORT_DIR, f"{jar_name_base}.report")
                try:
                    with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(f"Report: {jar_file}\nOverall: {passed}/{total} passed ({failed} failed).\n{'='*20}\n")
                        report_lines=[]
                        for df_rep in data_files:
                            res=report_map.get(df_rep)
                            if res:
                                rt_rep=res.get("sim_time",0) if res.get('status') in ["PASSED","TIMEOUT_SOFT","WRONG_ANSWER"] else res.get("exec_time",0)
                                report_lines.append(f"{df_rep}: {res.get('status','?')} ({rt_rep:.2f}s)")
                                if res.get('status')!="PASSED": report_lines.extend([f"    - {err_rep}" for err_rep in res.get('errors',[])])
                            else: report_lines.append(f"{df_rep}: RESULT_MISSING")
                        f.write("\n".join(report_lines)+"\n")
                    print(f"Report saved to '{report_path}'")
                except IOError as e: print(f"Error writing report '{report_path}': {e}", file=sys.stderr)

    elif PARALLEL_MODE == 'jar':
        print(f"Running tests parallel ('jar' mode, workers={workers})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            jar_futures = {executor.submit(test_single_jar, jar, data_files, DATA_DIR, OUT_DIR, LOG_DIR, REPORT_DIR): jar for jar in jar_files}
            print(f"All {len(jar_files)} JAR suites submitted, waiting...")
            completed = 0
            for future in concurrent.futures.as_completed(jar_futures):
                jar_done = jar_futures[future]; completed += 1
                print(f"Completed JAR: {os.path.basename(jar_done)} ({completed}/{len(jar_files)})...")
                try: # Unpack RAW results
                    _jar, passed, total, jr, jp, jt = future.result()
                    overall_summary[jar_done] = (passed, total)
                    if jr: raw_results_runtime[jar_done] = jr
                    if jp: raw_results_power[jar_done] = jp
                    if jt: raw_results_avgtime[jar_done] = jt
                except Exception as exc:
                    print(f"\nCRITICAL Error running suite for JAR '{jar_done}': {exc}\n{traceback.format_exc(limit=3)}", file=sys.stderr)
                    overall_summary[jar_done] = (0, len(data_files))

    else: print(f"Error: Unknown PARALLEL_MODE '{PARALLEL_MODE}'.", file=sys.stderr); sys.exit(1)

    # --- Post-processing: Calculate Scores and Averages ---
    print("\n" + "=" * 30); print("Post-processing results..."); print("=" * 30)
    # Prepare raw results structure for process_scores
    all_raw_results = {'power': raw_results_power, 'sim_time': raw_results_runtime, 'avg_time': raw_results_avgtime}
    scores_power, scores_runtime, scores_avgtime, total_scores = process_scores(
        all_raw_results, data_files, list(overall_summary.keys())
    )
    # Prepare plot data (use raw for originals, calculated for total score)
    plot_data_runtime = defaultdict(dict, raw_results_runtime)
    plot_data_power = defaultdict(dict, raw_results_power)
    plot_data_avgtime = defaultdict(dict, raw_results_avgtime)
    plot_data_total_score = defaultdict(dict, total_scores)
    # Add averages
    all_plot_dicts = [plot_data_runtime, plot_data_power, plot_data_avgtime, plot_data_total_score]
    for plot_dict in all_plot_dicts: add_averages_to_plot_data(plot_dict, data_files)
    data_files_for_plotting = data_files + ["Average"]

    # --- Final Summary ---
    end_overall_time = time.monotonic()
    print("\n"+"="*30); print("Overall Summary:"); print("="*30)
    if overall_summary:
         print(f"{'JAR File':<30} {'Tests Passed':<15} {'Avg Total Score':<15}")
         print("-" * 60)
         for jar, (passed, total) in sorted(overall_summary.items()):
              avg_score_val = plot_data_total_score.get(jar, {}).get("Average")
              avg_score_str = f"{avg_score_val:.2f}" if avg_score_val is not None else "N/A"
              print(f"- {os.path.basename(jar):<28} {f'{passed}/{total}':<15} {avg_score_str:<15}")
    else: print("No results collected.")
    print("-" * 30); print(f"Total execution time: {end_overall_time - start_overall_time:.2f} seconds"); print("=" * 30)

    # --- Conditional Plotting ---
    if enable_plotting:
        if MATPLOTLIB_AVAILABLE:
             print("Generating requested plots (including averages)...")
             plot_runtime_results(plot_data_runtime, data_files_for_plotting)
             plot_power_consumption(plot_data_power, data_files_for_plotting)
             plot_weighted_avg_time(plot_data_avgtime, data_files_for_plotting)
             plot_total_score(plot_data_total_score, data_files_for_plotting)
        else: print("Plotting enabled, but matplotlib unavailable.")
    else: print("Plotting disabled.")

    print("\nAll tests complete.")
    print(f"Check '{REPORT_DIR}' for reports.")
    print(f"Check '{LOG_DIR}' for full logs (.log).")
    print(f"Check '{OUT_DIR}' for validated outputs (.out).")
    if enable_plotting and MATPLOTLIB_AVAILABLE: print("Check current directory for plots (.png).")
    print("=" * 30)


# --- Script Entry Point --- (Keep original)
if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n\nExecution interrupted.", file=sys.stderr); sys.exit(1)
    except Exception as main_exc: print(f"\n\nUnhandled error: {main_exc}\n{traceback.format_exc()}", file=sys.stderr); sys.exit(2)