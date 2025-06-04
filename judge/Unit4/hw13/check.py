import subprocess
import os
import re
import json
import datetime
import shutil
from enum import Enum
from collections import defaultdict, deque
import importlib
import random
import traceback


# --- Global Print Mode Configuration ---
class PrintModeEnum(Enum):
    BRIEF = "BRIEF"
    DETAILED = "DETAILED"
    DEBUG = "DEBUG"


# 用户可以在这里修改 PRINT_MODE 的值:
# PrintModeEnum.BRIEF : 仅输出 CONSOLE:, CONSOLE ERROR:, CONSOLE WARNING:, 以及 main 函数中的状态/结果行。
# PrintModeEnum.DETAILED : 在 BRIEF 基础上，额外输出 CONSOLE SEND --->:, CONSOLE RECV <---:。
# PrintModeEnum.DEBUG : 在 DETAILED 基础上，额外输出 CONSOLE DEBUG (...)。
PRINT_MODE = PrintModeEnum.BRIEF


def print_console(message):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(f"CONSOLE: {message}")


def print_error(message):
    # 错误信息在所有模式下都显示
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(f"CONSOLE ERROR: {message}")


def print_warning(context_tag_or_full_message, details=""):
    # 如果提供了 details，则 context_tag_or_full_message 是括号内的标签
    # 否则，context_tag_or_full_message 是 "CONSOLE WARNING " 之后的所有内容
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        if details:
            print(f"CONSOLE WARNING {context_tag_or_full_message}: {details}")
        else:
            print(f"CONSOLE WARNING {context_tag_or_full_message}")


def print_send(line_content):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED]:
        print(f"CONSOLE SEND --->: {line_content}")


def print_recv(line_content):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED]:
        print(f"CONSOLE RECV <---: {line_content}")


def print_debug_structured(context_tag, message_details):
    # 用于 "CONSOLE DEBUG (tag): details" 格式的日志
    if PRINT_MODE == PrintModeEnum.DEBUG:
        print(f"CONSOLE DEBUG {context_tag}: {message_details}")


def print_debug_raw(full_debug_message):
    # 用于已经完全格式化的调试日志行，或者不需要标准前缀的调试信息
    if PRINT_MODE == PrintModeEnum.DEBUG:
        print(full_debug_message)


def print_status_line(message, end="\n", flush=False):
    # 用于 main() 中的通用状态行或不适合特定前缀但遵循打印模式的行
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(message, end=end, flush=flush)


def print_critical(message):
    # 用于评测机本身的严重错误，必须始终可见
    print(message)


def print_traceback_info():  # 重命名以避免与模块名冲突
    # Traceback 总是打印
    traceback.print_exc()


# --- Configuration ---
TESTJAR_DIR = "testjar"
TEST_CASES_DIR = "test_cases"
RESULTS_DIR = "results"
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
CORRECT_LOGS_DIR = os.path.join(LOGS_DIR, "correct")
ERROR_LOGS_DIR = os.path.join(LOGS_DIR, "error")
SUMMARY_FILE = os.path.join(RESULTS_DIR, "summary.txt")
DATA_GENERATOR_SCRIPT_NAME = "data_generator"  # Keep for main function structure
PROCESS_TIMEOUT = 5


# --- Enums and Data Structures ---
class BookLocation(Enum):
    BOOKSHELF = "bs"
    BORROW_RETURN_OFFICE = "bro"
    APPOINTMENT_OFFICE = "ao"
    USER = "user"


class BookCategory(Enum):
    A = "A";
    B = "B";
    C = "C"


class BookCopy:
    def __init__(self, full_id, isbn, category):
        self.full_id = full_id;
        self.isbn = isbn;
        self.category = category
        self.location = BookLocation.BOOKSHELF;
        self.holder_id = None
        self.reserved_for_user_id = None;
        self.reservation_expiry_date = None
        self.movement_history = []

    def __repr__(self):
        return f"BookCopy({self.full_id}, loc={self.location}, holder={self.holder_id}, reserved_for={self.reserved_for_user_id})"

    def record_move(self, date_str, from_loc_str_val, to_loc_str_val, for_user_id_if_ao=None):
        entry = (date_str, from_loc_str_val, to_loc_str_val)
        if for_user_id_if_ao and to_loc_str_val == BookLocation.APPOINTMENT_OFFICE.value:
            entry = (date_str, from_loc_str_val, to_loc_str_val, for_user_id_if_ao)
        self.movement_history.append(entry)


class UserState:
    def __init__(self, student_id):
        self.student_id = student_id;
        self.held_books_b = set()
        self.held_books_c = defaultdict(set);
        self.active_order_isbn = None
        self.active_order_date = None

    def can_borrow_b(self):
        return not self.held_books_b

    def can_borrow_c(self, isbn_to_borrow):
        return not self.held_books_c.get(isbn_to_borrow)

    def can_order_b(self):
        return not self.held_books_b and self.active_order_isbn is None

    def can_order_c(self, isbn_to_order):
        return not self.held_books_c.get(isbn_to_order) and self.active_order_isbn is None

    def add_book(self, book_copy: BookCopy):
        if book_copy.category == BookCategory.B:
            self.held_books_b.add(book_copy.full_id)
        elif book_copy.category == BookCategory.C:
            self.held_books_c[book_copy.isbn].add(book_copy.full_id)

    def remove_book(self, book_copy: BookCopy):
        if book_copy.category == BookCategory.B:
            self.held_books_b.discard(book_copy.full_id)
        elif book_copy.category == BookCategory.C:
            if book_copy.isbn in self.held_books_c:
                self.held_books_c[book_copy.isbn].discard(book_copy.full_id)
                if not self.held_books_c[book_copy.isbn]: del self.held_books_c[book_copy.isbn]


class LibraryGroundTruth:
    def __init__(self):
        self.books = {};
        self.books_by_isbn = defaultdict(list);
        self.users = {}
        self.current_date_str = "";
        self.current_date_obj = None
        self.outstanding_orders = defaultdict(deque)

    def get_or_create_user(self, student_id):
        if student_id not in self.users: self.users[student_id] = UserState(student_id)
        return self.users[student_id]

    def setup_books(self, initial_book_data_lines):
        for line in initial_book_data_lines:
            parts = line.split();
            isbn_full = parts[0];
            count = int(parts[1])
            category = BookCategory(isbn_full.split('-')[0])
            for i in range(1, count + 1):
                full_id = f"{isbn_full}-{i:02d}";
                book_copy = BookCopy(full_id, isbn_full, category)
                self.books[full_id] = book_copy;
                self.books_by_isbn[isbn_full].append(book_copy)

    def set_date(self, date_str):
        self.current_date_str = date_str;
        self.current_date_obj = datetime.datetime.strptime(date_str, "[%Y-%m-%d]").date()
        for book_copy in self.books.values():
            if book_copy.location == BookLocation.APPOINTMENT_OFFICE and book_copy.reserved_for_user_id and book_copy.reservation_expiry_date and self.current_date_obj > book_copy.reservation_expiry_date:
                book_copy.reserved_for_user_id = None;
                book_copy.reservation_expiry_date = None

    def find_available_copy_on_shelf(self, isbn):
        for book_copy in self.books_by_isbn.get(isbn, []):
            if book_copy.location == BookLocation.BOOKSHELF: return book_copy
        return None

    def _move_book(self, book_copy: BookCopy, new_location_enum: BookLocation, new_holder_id=None,
                   reserved_for_user_id=None, reservation_days=5, is_open_organization=True):
        old_location_enum = book_copy.location;
        old_holder_id = book_copy.holder_id
        from_loc_str_for_record = "user" if old_location_enum == BookLocation.USER else old_location_enum.value
        to_loc_str_for_record = "user" if new_location_enum == BookLocation.USER else new_location_enum.value
        for_user_if_ao_for_record = reserved_for_user_id if new_location_enum == BookLocation.APPOINTMENT_OFFICE else None
        book_copy.record_move(self.current_date_str, from_loc_str_for_record, to_loc_str_for_record,
                              for_user_if_ao_for_record)
        book_copy.location = new_location_enum;
        book_copy.holder_id = new_holder_id
        if new_location_enum == BookLocation.APPOINTMENT_OFFICE and reserved_for_user_id:
            book_copy.reserved_for_user_id = reserved_for_user_id
            start_date = self.current_date_obj if is_open_organization else self.current_date_obj + datetime.timedelta(
                days=1)
            book_copy.reservation_expiry_date = start_date + datetime.timedelta(days=reservation_days - 1)
        elif new_location_enum != BookLocation.APPOINTMENT_OFFICE:
            book_copy.reserved_for_user_id = None;
            book_copy.reservation_expiry_date = None
        if old_location_enum == BookLocation.USER and old_holder_id: self.get_or_create_user(old_holder_id).remove_book(
            book_copy)
        if new_location_enum == BookLocation.USER and new_holder_id: self.get_or_create_user(new_holder_id).add_book(
            book_copy)

    def handle_borrow_check(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        gt_default_book_to_borrow = self.find_available_copy_on_shelf(isbn)
        category = BookCategory(isbn.split('-')[0])

        if not gt_default_book_to_borrow:
            return False, f"No copy of {isbn} on bookshelf.", None
        if category == BookCategory.A:
            return False, f"Book {isbn} is Type A, cannot be borrowed.", None
        if category == BookCategory.B and not user.can_borrow_b():
            return False, f"User {student_id} already holds a B-type book.", None
        if category == BookCategory.C and not user.can_borrow_c(isbn):
            return False, f"User {student_id} already holds a copy of C-type ISBN {isbn}.", None
        return True, f"Borrow request for {isbn} by {student_id} is permissible by GT rules.", gt_default_book_to_borrow.full_id

    def handle_return(self, student_id, book_full_id):
        book_copy = self.books.get(book_full_id);
        user = self.get_or_create_user(student_id)
        if not book_copy or book_copy.holder_id != student_id or book_copy.location != BookLocation.USER:
            return False, f"User {student_id} is not holding {book_full_id} or book not with user."
        self._move_book(book_copy, BookLocation.BORROW_RETURN_OFFICE)
        return True, f"Returned {book_full_id} to BRO."

    def handle_order(self, student_id, isbn):
        user = self.get_or_create_user(student_id);
        category = BookCategory(isbn.split('-')[0])
        if category == BookCategory.A: return False, f"Book {isbn} (Type A) cannot be ordered."
        if user.active_order_isbn: return False, f"User {student_id} already has an active order for {user.active_order_isbn}."
        if category == BookCategory.B and not user.can_order_b(): return False, f"User {student_id} already holds a B-type book, cannot order another B-type."
        if category == BookCategory.C and not user.can_order_c(
                isbn): return False, f"User {student_id} already holds a copy of C-type ISBN {isbn}, cannot order it."
        user.active_order_isbn = isbn;
        user.active_order_date = self.current_date_str
        self.outstanding_orders[isbn].append((student_id, self.current_date_str))
        return True, f"Ordered {isbn}."

    def handle_pick(self, student_id, isbn_to_pick):
        user = self.get_or_create_user(student_id);
        book_to_give_user = None
        for book_copy in self.books_by_isbn.get(isbn_to_pick, []):
            if book_copy.location == BookLocation.APPOINTMENT_OFFICE and book_copy.reserved_for_user_id == student_id and book_copy.isbn == isbn_to_pick:
                if book_copy.reservation_expiry_date and self.current_date_obj > book_copy.reservation_expiry_date: continue
                book_to_give_user = book_copy;
                break
        if not book_to_give_user: return False, f"No book {isbn_to_pick} found at AO reserved for {student_id} or reservation expired.", None
        category = book_to_give_user.category
        if category == BookCategory.B and not user.can_borrow_b(): return False, f"User {student_id} would exceed B-type limit by picking {isbn_to_pick}.", None
        if category == BookCategory.C and not user.can_borrow_c(
                isbn_to_pick): return False, f"User {student_id} would exceed C-type limit for ISBN {isbn_to_pick} by picking.", None
        self._move_book(book_to_give_user, BookLocation.USER, new_holder_id=student_id)
        user.active_order_isbn = None;
        user.active_order_date = None
        return True, f"Picked {book_to_give_user.full_id}.", book_to_give_user.full_id

    def handle_query(self, book_full_id):
        book_copy = self.books.get(book_full_id)
        if not book_copy: return False, f"Book {book_full_id} not found in GT."
        expected_trace = []
        for i, trace_item in enumerate(book_copy.movement_history):
            date_str, from_loc, to_loc_val_from_hist = trace_item[0], trace_item[1], trace_item[2]
            line = f"{i + 1} {date_str} from {from_loc} to {to_loc_val_from_hist}"
            expected_trace.append(line)
        return True, expected_trace

    def handle_student_organization_move(self, date_str, book_full_id, from_loc_str, to_loc_str,
                                         for_student_id_str=None, is_open_org=True):
        book_copy = self.books.get(book_full_id)
        if not book_copy: return "WA", f"Student tried to move non-existent book {book_full_id}"
        valid_org_locs = {loc.value for loc in BookLocation if loc != BookLocation.USER}
        if from_loc_str not in valid_org_locs or to_loc_str not in valid_org_locs: return "WA", f"Invalid location in student move: {from_loc_str} to {to_loc_str}"
        if from_loc_str == to_loc_str: return "WA", f"Student move from and to same location: {from_loc_str}"
        if book_copy.location.value != from_loc_str: return "WA", f"Book {book_full_id} is at {book_copy.location.value}, student says it's at {from_loc_str}"
        if book_copy.location == BookLocation.APPOINTMENT_OFFICE and book_copy.reserved_for_user_id and book_copy.reservation_expiry_date and self.current_date_obj <= book_copy.reservation_expiry_date:
            return "WA", f"Book {book_full_id} is reserved for {book_copy.reserved_for_user_id} until EOD {book_copy.reservation_expiry_date} and cannot be moved by organization."
        if to_loc_str == BookLocation.APPOINTMENT_OFFICE.value and for_student_id_str:
            target_user_state = self.get_or_create_user(for_student_id_str)
            if not (target_user_state and target_user_state.active_order_isbn == book_copy.isbn):
                return "WA", f"Student tried to reserve {book_full_id} for {for_student_id_str} who has no (active) order for ISBN {book_copy.isbn}."
        self._move_book(book_copy, BookLocation(to_loc_str), reserved_for_user_id=for_student_id_str,
                        is_open_organization=is_open_org)
        return "OK", "Move applied to ground truth."

    def verify_organization_rules(self, is_open_org):
        if is_open_org:
            for book_copy in self.books.values():
                if book_copy.location == BookLocation.BORROW_RETURN_OFFICE: return "WA", f"After OPEN organization, book {book_copy.full_id} is still in BRO."
                if book_copy.location == BookLocation.APPOINTMENT_OFFICE and book_copy.reserved_for_user_id and book_copy.reservation_expiry_date and self.current_date_obj > book_copy.reservation_expiry_date:
                    return "WA", f"After OPEN organization, book {book_copy.full_id} at AO is overdue for user {book_copy.reserved_for_user_id} (expired {book_copy.reservation_expiry_date})."
        return "OK", "Organization rules satisfied."


class StudentProcess:
    def __init__(self, jar_path):
        self.jar_path = jar_path;
        self.process = None;
        self.log_buffer = []

    def start(self):
        try:
            print_console(f"Starting student process: java -jar {self.jar_path}")
            self.process = subprocess.Popen(['java', '-jar', self.jar_path], stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                                            errors='replace', bufsize=1)
            self.log_buffer.append(f"Harness: Started {self.jar_path}");
            return True
        except Exception as e:
            print_error(f"Failed to start {self.jar_path}: {e}");
            self.log_buffer.append(f"Harness ERROR: Failed to start {self.jar_path}: {e}");
            return False

    def send_input(self, line):
        if not self.process or self.process.poll() is not None:
            self.log_buffer.append("Harness ERROR: Process not running when sending input.");
            return False
        try:
            print_send(line)
            self.log_buffer.append(f"Harness SEND: {line}")
            self.process.stdin.write(line + "\n");
            self.process.stdin.flush();
            return True
        except Exception as e:
            print_error(f"Failed to send input '{line}': {e}");
            self.log_buffer.append(f"Harness ERROR: Failed to send input '{line}': {e}");
            self.kill();
            return False

    def read_output_lines(self):
        if not self.process or self.process.poll() is not None:
            self.log_buffer.append("Harness ERROR: Process not running when reading output.");
            return None
        try:
            line = self.process.stdout.readline()
            if line:
                line = line.strip();
                print_recv(line)
                self.log_buffer.append(f"Student RECV: {line}")
            else:
                self.log_buffer.append(f"Student RECV: [EMPTY LINE or EOF]")
                if self.process.poll() is not None: return None
            return line
        except Exception as e:
            print_error(f"Failed to read output: {e}");
            self.log_buffer.append(f"Harness ERROR: Failed to read output: {e}");
            self.kill();
            return None

    def read_expected_lines(self, count):
        lines = []
        for i in range(count):
            line = self.read_output_lines()
            if line is None: self.log_buffer.append(
                f"Harness ERROR: Expected {count} lines, got None at line {i + 1}."); return None
            lines.append(line)
        return lines

    def consume_stderr(self):
        pass

    def get_current_log(self):
        return "\n".join(self.log_buffer)

    def clear_log_buffer(self):
        self.log_buffer = []

    def kill(self):
        if self.process and self.process.poll() is None:
            self.log_buffer.append("Harness: Attempting to terminate student process.")
            print_console("Terminating student process...")
            try:
                self.process.terminate();
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.log_buffer.append("Harness: Process did not terminate, killing.")
                print_console("Student process did not terminate gracefully, killing...")
                self.process.kill()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.log_buffer.append("Harness: Process kill command also timed out.")
            except Exception as e:
                self.log_buffer.append(f"Harness: Exception during process termination/kill: {e}")
        elif self.process:
            self.log_buffer.append("Harness: Student process already terminated.")


ACTION_RESPONSE_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] \[(accept|reject)\] (\S+) (\w+) (\S+)")
QUERY_HEADER_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] (\S+-\d{2}) moving trace: (\d+)")
TRACE_LINE_REGEX = re.compile(r"(\d+) \[(\d{4}-\d{2}-\d{2})\] from (\S+) to (\S+)(?: for (\S+))?")
ORG_MOVE_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] move (\S+-\d{2}) from (\S+) to (\S+)(?: for (\S+))?")


def parse_test_case_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    if not lines: raise ValueError(f"Test case file is empty: {filepath}")
    try:
        num_book_types = int(lines[0])
    except ValueError:
        raise ValueError(f"Invalid number of book types: {lines[0]} in {filepath}")
    if len(lines) < 1 + num_book_types: raise ValueError(
        f"Test case file format error: Not enough lines for book specifications.")
    initial_books_spec = lines[1:1 + num_book_types];
    raw_commands_spec = lines[1 + num_book_types:]
    commands_spec = [cmd for cmd in raw_commands_spec if cmd and cmd.startswith("[")]
    if len(raw_commands_spec) > 0 and len(commands_spec) != len(raw_commands_spec):
        print_warning("(Parse)",
                      f"Some lines after book specs were filtered out (Original: {len(raw_commands_spec)}, Filtered: {len(commands_spec)}).")
    return initial_books_spec, commands_spec


def run_single_test_case(jar_path, test_case_file_path):
    student_proc = StudentProcess(jar_path);
    sent_inputs_for_replay = [];
    log_content_on_error = ""
    try:
        if not student_proc.start(): return "RE", student_proc.get_current_log(), "Failed to start JAR.", sent_inputs_for_replay
        log_content_on_error = student_proc.get_current_log()
        try:
            initial_books_spec, commands_spec = parse_test_case_file(test_case_file_path)
        except Exception as e:
            log_content_on_error += f"\nError parsing TC {test_case_file_path}: {e}";
            return "RE", log_content_on_error, f"TC Parse Error: {e}", sent_inputs_for_replay
        ground_truth = LibraryGroundTruth()
        initial_book_count_str = str(len(initial_books_spec))
        if not student_proc.send_input(
                initial_book_count_str): return "RE", student_proc.get_current_log(), "Fail send book count.", sent_inputs_for_replay
        sent_inputs_for_replay.append(initial_book_count_str)
        for book_line in initial_books_spec:
            if not student_proc.send_input(
                    book_line): return "RE", student_proc.get_current_log(), f"Fail send book spec: {book_line}", sent_inputs_for_replay
            sent_inputs_for_replay.append(book_line)
        ground_truth.setup_books(initial_books_spec)

        command_queue = deque(commands_spec);
        borrowed_books_for_potential_return = []
        ordered_books_for_potential_pick = [];
        pick_attempts_count = defaultdict(int)
        harness_current_processing_date_str = None;
        harness_is_library_open = False
        future_command_blocks = []
        loop_counter = 0

        print_debug_structured("(Harness Init)", f"Initial MainQ: {list(command_queue)}")

        while True:
            loop_counter += 1
            current_main_q_head_debug = command_queue[0] if command_queue else "None"
            future_q_summary_debug = []
            if future_command_blocks:
                for date_f_dbg, deq_f_dbg in future_command_blocks:
                    deq_as_list_dbg = list(deq_f_dbg)
                    future_q_summary_debug.append(
                        f"({date_f_dbg.strftime('%Y-%m-%d')}: {deq_as_list_dbg[:2]}{'...' if len(deq_as_list_dbg) > 2 else ''})")
            print_debug_structured(f"(Harness Loop START Iter {loop_counter})",
                                   f"MainQ({len(command_queue)}):'{current_main_q_head_debug}', FutureQ({len(future_command_blocks)}): {', '.join(future_q_summary_debug)}, CurDate:{harness_current_processing_date_str}, LibOpen:{harness_is_library_open}")

            next_command_str = None;
            current_harness_date_obj = None
            if harness_current_processing_date_str:
                try:
                    current_harness_date_obj = datetime.datetime.strptime(harness_current_processing_date_str,
                                                                          "[%Y-%m-%d]").date()
                except ValueError:
                    return "RE", student_proc.get_current_log(), f"Harness Error: Invalid date string: {harness_current_processing_date_str}", sent_inputs_for_replay
            future_command_blocks.sort(key=lambda x: x[0])
            main_q_next_cmd_str = command_queue[0] if command_queue else None
            main_q_next_date_obj = None
            if main_q_next_cmd_str:
                main_q_match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", main_q_next_cmd_str)
                if main_q_match:
                    try:
                        main_q_next_date_obj = datetime.datetime.strptime(main_q_match.group(0), "[%Y-%m-%d]").date()
                    except ValueError:
                        main_q_next_date_obj = None
            future_block_next_date_obj = future_command_blocks[0][0] if future_command_blocks else None

            if current_harness_date_obj and main_q_next_date_obj and main_q_next_date_obj == current_harness_date_obj:
                next_command_str = command_queue.popleft()
                print_debug_structured("(Selector Path 1)", f"Took '{next_command_str}' from MainQ for current day.")
            else:
                next_processing_block_date_obj = None;
                chosen_source_is_future_block = False
                if main_q_next_date_obj and future_block_next_date_obj:
                    if main_q_next_date_obj <= future_block_next_date_obj:
                        next_processing_block_date_obj = main_q_next_date_obj
                    else:
                        next_processing_block_date_obj = future_block_next_date_obj;
                        chosen_source_is_future_block = True
                elif main_q_next_date_obj:
                    next_processing_block_date_obj = main_q_next_date_obj
                elif future_block_next_date_obj:
                    next_processing_block_date_obj = future_block_next_date_obj;
                    chosen_source_is_future_block = True

                if current_harness_date_obj and next_processing_block_date_obj and next_processing_block_date_obj > current_harness_date_obj and harness_is_library_open:
                    close_cmd_for_current_day = f"{harness_current_processing_date_str} CLOSE"
                    if not (main_q_next_cmd_str and main_q_next_cmd_str == close_cmd_for_current_day):
                        command_queue.appendleft(close_cmd_for_current_day)
                        print_debug_structured("(Selector DynCLOSE)",
                                               f"Prepended '{close_cmd_for_current_day}' to MainQ.")
                    next_command_str = command_queue.popleft()
                    print_debug_structured("(Selector DynCLOSE)", f"Took '{next_command_str}' from MainQ.")
                elif next_command_str is None and next_processing_block_date_obj is not None:
                    if chosen_source_is_future_block:
                        if current_harness_date_obj is None or future_block_next_date_obj >= current_harness_date_obj:
                            _date_obj_sel, daily_cmds_deque_sel = future_command_blocks.pop(0)
                            print_debug_structured("(Selector FutureBlock)",
                                                   f"Loading block for {_date_obj_sel.strftime('[%Y-%m-%d]')}: {list(daily_cmds_deque_sel)}")
                            command_queue.extendleft(reversed(list(daily_cmds_deque_sel)))
                            if not command_queue: break
                            next_command_str = command_queue.popleft()
                            print_debug_structured("(Selector FutureBlock)",
                                                   f"Took '{next_command_str}' from loaded block.")
                    elif main_q_next_date_obj:
                        if current_harness_date_obj is None or main_q_next_date_obj >= current_harness_date_obj:
                            next_command_str = command_queue.popleft()
                            print_debug_structured("(Selector MainQ)", f"Took '{next_command_str}' from MainQ.")

            if next_command_str is None:
                if not command_queue and not future_command_blocks:
                    print_debug_structured(f"(Harness Loop END Iter {loop_counter})",
                                           "All queues empty. Breaking loop.")
                    break
                else:
                    if harness_is_library_open and current_harness_date_obj:
                        can_advance_check_nocmd = False
                        if command_queue and re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]):
                            if datetime.datetime.strptime(
                                    re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]).group(0),
                                    "[%Y-%m-%d]").date() > current_harness_date_obj: can_advance_check_nocmd = True
                        if future_command_blocks and future_command_blocks[0][
                            0] > current_harness_date_obj: can_advance_check_nocmd = True
                        if can_advance_check_nocmd:
                            command_queue.appendleft(f"{harness_current_processing_date_str} CLOSE")
                            print_debug_structured("(Harness Loop NoCMD DynCLOSE)",
                                                   f"Prepended CLOSE for {harness_current_processing_date_str}.")
                    stuck_in_past = False
                    if command_queue and re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]):
                        if current_harness_date_obj and datetime.datetime.strptime(
                                re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]).group(0),
                                "[%Y-%m-%d]").date() < current_harness_date_obj: stuck_in_past = True
                    if future_command_blocks and current_harness_date_obj and future_command_blocks[0][
                        0] < current_harness_date_obj: stuck_in_past = True
                    if stuck_in_past:
                        print_error(
                            f"(Harness Loop NoCMD Stuck): Stuck in past. Current: {current_harness_date_obj}, MainQ: {command_queue[0] if command_queue else 'N/A'}, FutureQ: {future_command_blocks[0][0] if future_command_blocks else 'N/A'}")
                        return "RE", student_proc.get_current_log(), "Harness Error: Stuck in past date.", sent_inputs_for_replay
                    continue
            command_str = next_command_str
            print_debug_structured(f"(Harness EXEC Iter {loop_counter})",
                                   f"Executing: '{command_str}'. CurrentDate: {harness_current_processing_date_str}, LibOpen: {harness_is_library_open}")

            command_str_for_send = command_str

            date_match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_str_for_send)
            if not date_match: return "RE", student_proc.get_current_log(), f"Command no date: {command_str_for_send}", sent_inputs_for_replay
            date_from_current_cmd_str = date_match.group(0)
            current_cmd_date_obj = datetime.datetime.strptime(date_from_current_cmd_str, "[%Y-%m-%d]").date()
            if harness_current_processing_date_str is None or current_cmd_date_obj > datetime.datetime.strptime(
                    harness_current_processing_date_str, "[%Y-%m-%d]").date():
                if harness_is_library_open:
                    print_warning("(Harness Date)",
                                  f"Advancing to {date_from_current_cmd_str} but lib was open for {harness_current_processing_date_str}.")
                harness_current_processing_date_str = date_from_current_cmd_str;
                harness_is_library_open = False
            elif current_cmd_date_obj < datetime.datetime.strptime(harness_current_processing_date_str,
                                                                   "[%Y-%m-%d]").date():
                return "RE", student_proc.get_current_log(), f"Harness Error: Date倒退 from {harness_current_processing_date_str} to {date_from_current_cmd_str}", sent_inputs_for_replay
            is_open_command = " OPEN" in command_str_for_send;
            is_close_command = " CLOSE" in command_str_for_send
            if is_open_command and date_from_current_cmd_str == harness_current_processing_date_str:
                if harness_is_library_open:
                    print_warning("(Harness State)", f"Duplicate OPEN for {date_from_current_cmd_str}.")
                harness_is_library_open = True
            elif is_close_command and date_from_current_cmd_str == harness_current_processing_date_str:
                if not harness_is_library_open:
                    print_warning("(Harness State)", f"CLOSE for {date_from_current_cmd_str} but lib not open.")
                harness_is_library_open = False
            if ground_truth.current_date_str != harness_current_processing_date_str: ground_truth.set_date(
                harness_current_processing_date_str)

            if not student_proc.send_input(
                    command_str_for_send): return "RE", student_proc.get_current_log(), f"Failed send: {command_str_for_send}", sent_inputs_for_replay
            sent_inputs_for_replay.append(command_str_for_send)

            if is_open_command:
                output_line = student_proc.read_output_lines()
                if output_line is None: return "RE", student_proc.get_current_log(), "Timeout K for OPEN", sent_inputs_for_replay
                try:
                    num_moves = int(output_line);
                    assert num_moves >= 0
                except:
                    return "WA", student_proc.get_current_log(), f"OPEN: Bad K: '{output_line}'", sent_inputs_for_replay
                if num_moves > 0:
                    move_lines = student_proc.read_expected_lines(num_moves)
                    if move_lines is None: return "RE", student_proc.get_current_log(), "Timeout OPEN moves", sent_inputs_for_replay
                    for move_line_str in move_lines:
                        match = ORG_MOVE_REGEX.match(move_line_str)
                        if not match: return "WA", student_proc.get_current_log(), f"OPEN: Bad move: '{move_line_str}'", sent_inputs_for_replay
                        _d, book_id, _from, _to, for_s_id = match.groups()
                        if _d != harness_current_processing_date_str.strip(
                                "[]"): return "WA", student_proc.get_current_log(), f"OPEN move: Date mismatch", sent_inputs_for_replay
                        status_org, reason_org = ground_truth.handle_student_organization_move(
                            harness_current_processing_date_str, book_id, _from, _to, for_s_id, True)
                        if status_org == "WA": return "WA", student_proc.get_current_log(), f"OPEN org move: {reason_org}", sent_inputs_for_replay
                status_org_rules, reason_org_rules = ground_truth.verify_organization_rules(is_open_org=True)
                if status_org_rules == "WA": return "WA", student_proc.get_current_log(), f"OPEN: Rule violation: {reason_org_rules}", sent_inputs_for_replay
                generated_picked_for_today_open = [];
                new_ordered_list_open = []
                for s_id_op, isbn_op, o_date_op in ordered_books_for_potential_pick:
                    key_op = (s_id_op, isbn_op, o_date_op)
                    user_active_order_op = ground_truth.users.get(s_id_op,
                                                                  UserState("dummy")).active_order_isbn == isbn_op
                    if user_active_order_op and pick_attempts_count[key_op] < 2:
                        can_pick_gt_op = any(
                            b.location == BookLocation.APPOINTMENT_OFFICE and b.reserved_for_user_id == s_id_op and b.isbn == isbn_op and (
                                    b.reservation_expiry_date is None or ground_truth.current_date_obj <= b.reservation_expiry_date)
                            for b in ground_truth.books_by_isbn.get(isbn_op, []))
                        if can_pick_gt_op:
                            generated_picked_for_today_open.append(
                                f"{harness_current_processing_date_str} {s_id_op} picked {isbn_op}")
                        else:
                            new_ordered_list_open.append(key_op[:])
                    elif user_active_order_op:
                        new_ordered_list_open.append(key_op[:])
                ordered_books_for_potential_pick = new_ordered_list_open
                if generated_picked_for_today_open:
                    print_debug_structured(f"(GenPickAfterOpen Iter {loop_counter})",
                                           f"Generated: {generated_picked_for_today_open}")
                for cmd_today_op in reversed(generated_picked_for_today_open): command_queue.appendleft(cmd_today_op)

            elif is_close_command:
                output_line = student_proc.read_output_lines()
                if output_line is None: return "RE", student_proc.get_current_log(), "Timeout K for CLOSE", sent_inputs_for_replay
                try:
                    num_moves = int(output_line);
                    assert num_moves >= 0
                except:
                    return "WA", student_proc.get_current_log(), f"CLOSE: Bad K: '{output_line}'", sent_inputs_for_replay
                if num_moves > 0:
                    move_lines = student_proc.read_expected_lines(num_moves)
                    if move_lines is None: return "RE", student_proc.get_current_log(), "Timeout CLOSE moves", sent_inputs_for_replay
                    for move_line_str in move_lines:
                        match = ORG_MOVE_REGEX.match(move_line_str)
                        if not match: return "WA", student_proc.get_current_log(), f"CLOSE: Bad move: '{move_line_str}'", sent_inputs_for_replay
                        _d, book_id, _from, _to, for_s_id = match.groups()
                        if _d != harness_current_processing_date_str.strip(
                                "[]"): return "WA", student_proc.get_current_log(), f"CLOSE move: Date mismatch", sent_inputs_for_replay
                        status_cl, reason_cl = ground_truth.handle_student_organization_move(
                            harness_current_processing_date_str, book_id, _from, _to, for_s_id, False)
                        if status_cl == "WA": return "WA", student_proc.get_current_log(), f"CLOSE org move: {reason_cl}", sent_inputs_for_replay
                future_ops_target_date_obj_cl = ground_truth.current_date_obj + datetime.timedelta(days=1)
                if command_queue:
                    match_cl_q_peek = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                    if match_cl_q_peek:
                        main_q_next_dt_cl = datetime.datetime.strptime(match_cl_q_peek.group(0), "[%Y-%m-%d]").date()
                        if main_q_next_dt_cl > future_ops_target_date_obj_cl: future_ops_target_date_obj_cl = main_q_next_dt_cl
                future_ops_target_date_str_cl = future_ops_target_date_obj_cl.strftime("[%Y-%m-%d]")
                generated_picked_for_future_cl = [];
                new_ordered_list_cl = []
                for s_id_cl, isbn_cl, o_date_cl in ordered_books_for_potential_pick:
                    key_cl = (s_id_cl, isbn_cl, o_date_cl)
                    user_active_order_cl = ground_truth.users.get(s_id_cl,
                                                                  UserState("dummy")).active_order_isbn == isbn_cl
                    if user_active_order_cl and pick_attempts_count[key_cl] < 2:
                        can_pick_gt_cl = any(
                            b.location == BookLocation.APPOINTMENT_OFFICE and b.reserved_for_user_id == s_id_cl and b.isbn == isbn_cl and b.reservation_expiry_date and future_ops_target_date_obj_cl <= b.reservation_expiry_date
                            for b in ground_truth.books_by_isbn.get(isbn_cl, []))
                        if can_pick_gt_cl:
                            generated_picked_for_future_cl.append(
                                f"{future_ops_target_date_str_cl} {s_id_cl} picked {isbn_cl}")
                        else:
                            new_ordered_list_cl.append(key_cl[:])
                    elif user_active_order_cl:
                        new_ordered_list_cl.append(key_cl[:])
                ordered_books_for_potential_pick = new_ordered_list_cl
                if generated_picked_for_future_cl:
                    cmd_block_for_future_cl = deque()
                    if future_ops_target_date_obj_cl > ground_truth.current_date_obj:
                        open_cmd_cl = f"{future_ops_target_date_str_cl} OPEN"
                        open_already_in_fcb = any(
                            d == future_ops_target_date_obj_cl and q and q[0] == open_cmd_cl for d, q in
                            future_command_blocks)
                        if not open_already_in_fcb: cmd_block_for_future_cl.appendleft(open_cmd_cl)
                    for pick_cmd_cl in generated_picked_for_future_cl: cmd_block_for_future_cl.append(pick_cmd_cl)
                    if cmd_block_for_future_cl:
                        print_debug_structured(f"(GenPickAfterClose Iter {loop_counter})",
                                               f"Scheduling for {future_ops_target_date_str_cl}: {list(cmd_block_for_future_cl)}")
                        existing_block_idx = -1;
                        for i, (d, _) in enumerate(future_command_blocks):
                            if d == future_ops_target_date_obj_cl: existing_block_idx = i; break
                        if existing_block_idx != -1:
                            _, existing_deque = future_command_blocks[existing_block_idx]
                            if cmd_block_for_future_cl and cmd_block_for_future_cl[0].endswith(" OPEN") and not (
                                    existing_deque and existing_deque[0].endswith(" OPEN")):
                                existing_deque.appendleft(cmd_block_for_future_cl.popleft())
                            existing_deque.extend(cmd_block_for_future_cl)
                        else:
                            future_command_blocks.append((future_ops_target_date_obj_cl, cmd_block_for_future_cl))
            else:  # User actions
                if not harness_is_library_open: return "WA", student_proc.get_current_log(), f"Cmd '{command_str_for_send}' while lib closed on {harness_current_processing_date_str}.", sent_inputs_for_replay
                parts = command_str_for_send.split();
                _d_cmd, student_id, action_verb, book_identifier = parts[0], parts[1], parts[2], parts[3]
                student_output_line = student_proc.read_output_lines()
                if student_output_line is None: return "RE", student_proc.get_current_log(), f"Timeout resp for {action_verb}: {command_str_for_send}", sent_inputs_for_replay
                action_match = ACTION_RESPONSE_REGEX.match(student_output_line);
                query_match_header = QUERY_HEADER_REGEX.match(student_output_line)
                if action_verb == "queried":
                    if not query_match_header: return "WA", student_proc.get_current_log(), f"queried: Bad resp hdr: '{student_output_line}'", sent_inputs_for_replay
                    s_date_q, s_book_id_q, s_num_traces_str_q = query_match_header.groups()
                    if s_date_q != harness_current_processing_date_str.strip(
                            "[]") or s_book_id_q != book_identifier: return "WA", student_proc.get_current_log(), f"queried: Date/ID mismatch", sent_inputs_for_replay
                    try:
                        s_num_traces_q = int(s_num_traces_str_q);
                        assert s_num_traces_q >= 0
                    except:
                        return "WA", student_proc.get_current_log(), f"queried: Bad num_traces: '{s_num_traces_str_q}'", sent_inputs_for_replay
                    student_trace_lines_q = student_proc.read_expected_lines(
                        s_num_traces_q) if s_num_traces_q > 0 else []
                    if s_num_traces_q > 0 and student_trace_lines_q is None: return "RE", student_proc.get_current_log(), "Timeout query traces", sent_inputs_for_replay
                    gt_success_q, gt_trace_q_list = ground_truth.handle_query(book_identifier)
                    if not gt_success_q: return "RE", student_proc.get_current_log(), f"GT Error query {book_identifier}: {gt_trace_q_list}", sent_inputs_for_replay

                    # print_debug_raw(f"\nCONSOLE DEBUG (Harness Query): Student traces for {book_identifier} ({len(student_trace_lines_q)} lines):")
                    # for s_line_dbg in student_trace_lines_q: print_debug_raw(f"  S: {s_line_dbg}")
                    # print_debug_raw(f"CONSOLE DEBUG (Harness Query): GT traces for {book_identifier} ({len(gt_trace_q_list)} lines):")
                    # for gt_line_dbg in gt_trace_q_list: print_debug_raw(f"  GT: {gt_line_dbg}")

                    if len(student_trace_lines_q) != len(gt_trace_q_list):
                        return "WA", student_proc.get_current_log() + f"\nGT TRACE for {book_identifier}:\n" + "\n".join(
                            gt_trace_q_list), f"queried: Trace count mismatch. Student: {len(student_trace_lines_q)}, GT: {len(gt_trace_q_list)}", sent_inputs_for_replay
                    for i, (s_line, gt_line) in enumerate(zip(student_trace_lines_q, gt_trace_q_list)):
                        if s_line.strip() != gt_line.strip():
                            return "WA", student_proc.get_current_log(), f"queried: Trace line {i + 1} mismatch.", sent_inputs_for_replay
                else:
                    if not action_match: return "WA", student_proc.get_current_log(), f"{action_verb}: Bad resp format: '{student_output_line}'", sent_inputs_for_replay
                    s_date, s_status, s_student_id, s_action, s_book_details = action_match.groups()
                    if s_date != harness_current_processing_date_str.strip(
                            "[]") or s_student_id != student_id or s_action != action_verb: return "WA", student_proc.get_current_log(), f"{action_verb}: Mismatch in resp date/ID/action.", sent_inputs_for_replay
                    if action_verb == "borrowed":
                        gt_check_success, gt_check_message, _ = ground_truth.handle_borrow_check(student_id,
                                                                                                 book_identifier)
                        if s_status == "accept":
                            student_borrowed_full_id = s_book_details
                            if not gt_check_success: return "WA", student_proc.get_current_log(), f"borrowed: S:accept, GT:reject request for ISBN {book_identifier}. GT: {gt_check_message}", sent_inputs_for_replay
                            if not re.fullmatch(f"{re.escape(book_identifier)}-\\d{{2}}",
                                                student_borrowed_full_id): return "WA", student_proc.get_current_log(), f"borrowed [accept]: Bad full_id: '{student_borrowed_full_id}'", sent_inputs_for_replay
                            student_actual_book_copy_obj = ground_truth.books.get(student_borrowed_full_id)
                            if not student_actual_book_copy_obj or student_actual_book_copy_obj.isbn != book_identifier: return "WA", student_proc.get_current_log(), f"borrowed [accept]: Book '{student_borrowed_full_id}' invalid or ISBN mismatch.", sent_inputs_for_replay
                            can_borrow_student_choice = True;
                            reason_invalid_student_choice = ""
                            user_state_to_check_rules = ground_truth.get_or_create_user(student_id)
                            if student_actual_book_copy_obj.location != BookLocation.BOOKSHELF:
                                can_borrow_student_choice = False;
                                reason_invalid_student_choice = f"Book {student_borrowed_full_id} not on bookshelf."
                            elif student_actual_book_copy_obj.category == BookCategory.A:
                                can_borrow_student_choice = False;
                                reason_invalid_student_choice = "Cannot borrow Type A."
                            elif student_actual_book_copy_obj.category == BookCategory.B and not user_state_to_check_rules.can_borrow_b():
                                can_borrow_student_choice = False;
                                reason_invalid_student_choice = "User already holds B book."
                            elif student_actual_book_copy_obj.category == BookCategory.C and not user_state_to_check_rules.can_borrow_c(
                                    student_actual_book_copy_obj.isbn):
                                can_borrow_student_choice = False;
                                reason_invalid_student_choice = f"User already holds C ISBN {student_actual_book_copy_obj.isbn}."
                            if not can_borrow_student_choice: return "WA", student_proc.get_current_log(), f"borrowed [accept]: Student borrowed '{student_borrowed_full_id}', invalid by GT. Reason: {reason_invalid_student_choice}", sent_inputs_for_replay
                            ground_truth._move_book(student_actual_book_copy_obj, BookLocation.USER,
                                                    new_holder_id=student_id)
                            borrowed_books_for_potential_return.append(
                                (student_id, student_borrowed_full_id, harness_current_processing_date_str))
                            print_debug_structured(f"(AppendToReturnList BORROWED Iter {loop_counter})",
                                                   f"Added ('{student_id}', '{student_borrowed_full_id}', '{harness_current_processing_date_str}'). List size: {len(borrowed_books_for_potential_return)}")
                        elif s_status == "reject":
                            if gt_check_success: pass
                            if s_book_details != book_identifier: return "WA", student_proc.get_current_log(), f"borrowed [reject]: ISBN mismatch.", sent_inputs_for_replay
                    elif action_verb == "ordered":
                        gt_accepted, gt_message = ground_truth.handle_order(student_id, book_identifier)
                        if s_status == "accept":
                            if not gt_accepted: return "WA", student_proc.get_current_log(), f"ordered: S:accept, GT:reject. GT: {gt_message}", sent_inputs_for_replay
                            if s_book_details != book_identifier: return "WA", student_proc.get_current_log(), f"ordered [accept]: ISBN mismatch.", sent_inputs_for_replay
                            order_key = (student_id, book_identifier, harness_current_processing_date_str)
                            if order_key not in ordered_books_for_potential_pick:
                                ordered_books_for_potential_pick.append(order_key)
                                print_debug_structured(f"(AppendToPickList ORDERED Iter {loop_counter})",
                                                       f"Added ('{student_id}', '{book_identifier}', '{harness_current_processing_date_str}'). PickList size: {len(ordered_books_for_potential_pick)}")
                            pick_attempts_count[order_key] = 0
                        elif s_status == "reject":
                            if gt_accepted: return "WA", student_proc.get_current_log(), f"ordered: S:reject, GT:accept. GT: {gt_message}", sent_inputs_for_replay
                            if s_book_details != book_identifier: return "WA", student_proc.get_current_log(), f"ordered [reject]: ISBN mismatch.", sent_inputs_for_replay
                    elif action_verb == "returned":
                        gt_accepted, gt_message = ground_truth.handle_return(student_id, book_identifier)
                        if not gt_accepted: return "RE", student_proc.get_current_log(), f"GT Error on student return: {gt_message}", sent_inputs_for_replay
                        if s_status != "accept": return "WA", student_proc.get_current_log(), f"returned: Student rejected valid student return.", sent_inputs_for_replay
                        if s_book_details != book_identifier: return "WA", student_proc.get_current_log(), f"returned [accept]: Book full_id mismatch.", sent_inputs_for_replay
                        original_len_return_list = len(borrowed_books_for_potential_return)
                        borrowed_books_for_potential_return = [(s, b, d) for s, b, d in
                                                               borrowed_books_for_potential_return if
                                                               not (s == student_id and b == book_identifier)]
                        if len(borrowed_books_for_potential_return) != original_len_return_list:
                            print_debug_structured(f"(RemoveFromReturnList STUDENT_RETURNED Iter {loop_counter})",
                                                   f"Removed ('{student_id}', '{book_identifier}') due to student's return. List size now: {len(borrowed_books_for_potential_return)}")
                    elif action_verb == "picked":
                        order_key_for_pick_count = next((k for k in ordered_books_for_potential_pick if
                                                         k[0] == student_id and k[1] == book_identifier),
                                                        (student_id, book_identifier, "TEMP_PICK_KEY"))
                        pick_attempts_count[order_key_for_pick_count] += 1
                        gt_accepted, gt_message, gt_book_full_id_involved = ground_truth.handle_pick(student_id,
                                                                                                     book_identifier)
                        if s_status == "accept":
                            if not gt_accepted: return "WA", student_proc.get_current_log(), f"picked: S:accept, GT:reject. GT: {gt_message}", sent_inputs_for_replay
                            if s_book_details != gt_book_full_id_involved: return "WA", student_proc.get_current_log(), f"picked [accept]: Student picked '{s_book_details}', GT expected '{gt_book_full_id_involved}'.", sent_inputs_for_replay
                            borrowed_books_for_potential_return.append(
                                (student_id, gt_book_full_id_involved, harness_current_processing_date_str))
                            print_debug_structured(f"(AppendToReturnList PICKED Iter {loop_counter})",
                                                   f"Added ('{student_id}', '{gt_book_full_id_involved}', '{harness_current_processing_date_str}'). List size: {len(borrowed_books_for_potential_return)}")
                            ordered_books_for_potential_pick = [o for o in ordered_books_for_potential_pick if
                                                                not (o[0] == student_id and o[1] == book_identifier)]
                        elif s_status == "reject":
                            if gt_accepted: return "WA", student_proc.get_current_log(), f"picked: S:reject, GT:accept. GT gave: {gt_book_full_id_involved}. {gt_message}", sent_inputs_for_replay
                            if s_book_details != book_identifier: return "WA", student_proc.get_current_log(), f"picked [reject]: ISBN mismatch.", sent_inputs_for_replay

                if borrowed_books_for_potential_return and random.random() < 0.3:
                    print_debug_structured(f"(GenReturn Attempt Entry Iter {loop_counter})",
                                           f"Current borrowed_books_for_potential_return: {borrowed_books_for_potential_return}")
                    actual_book_to_return_info = None
                    original_list_index_to_pop = -1
                    for idx, (s_id_ret_peek, book_id_ret_peek, borrow_date_peek) in enumerate(
                            list(borrowed_books_for_potential_return)):
                        print_debug_structured(f"(GenReturn Peek Item {idx} Iter {loop_counter})",
                                               f"User='{s_id_ret_peek}', Book='{book_id_ret_peek}', BorrowDate='{borrow_date_peek}'")
                        user_state_in_gt = ground_truth.users.get(s_id_ret_peek)
                        book_copy_in_gt = ground_truth.books.get(book_id_ret_peek)
                        gt_check_user_exists = user_state_in_gt is not None
                        gt_check_book_exists = book_copy_in_gt is not None
                        gt_check_holder_matches = False;
                        gt_check_location_is_user = False
                        if gt_check_book_exists:
                            gt_check_holder_matches = (book_copy_in_gt.holder_id == s_id_ret_peek)
                            gt_check_location_is_user = (book_copy_in_gt.location == BookLocation.USER)
                            print_debug_raw(
                                f"  GT Book State for '{book_id_ret_peek}': Holder='{book_copy_in_gt.holder_id}', Location='{book_copy_in_gt.location}'")
                        else:
                            print_debug_raw(
                                f"  GT Book State: Book '{book_id_ret_peek}' not found in ground_truth.books.")
                        if gt_check_user_exists:
                            user_holds_b = list(user_state_in_gt.held_books_b);
                            user_holds_c = {k: list(v) for k, v in user_state_in_gt.held_books_c.items()}
                            print_debug_raw(
                                f"  GT User State for '{s_id_ret_peek}': Holds B: {user_holds_b}, Holds C: {user_holds_c}")
                        else:
                            print_debug_raw(
                                f"  GT User State for '{s_id_ret_peek}': User not found in ground_truth.users.")
                        if gt_check_user_exists and gt_check_book_exists and gt_check_holder_matches and gt_check_location_is_user:
                            print_debug_raw(
                                f"  GT Check PASSED for Book='{book_id_ret_peek}' by User='{s_id_ret_peek}'.")
                            actual_book_to_return_info = (s_id_ret_peek, book_id_ret_peek, borrow_date_peek)
                            original_list_index_to_pop = idx;
                            break
                        else:
                            print_debug_raw(
                                f"  GT Check FAILED for Book='{book_id_ret_peek}' by User='{s_id_ret_peek}'. Conditions: UserExists={gt_check_user_exists}, BookExists={gt_check_book_exists}, HolderMatch={gt_check_holder_matches}, LocationIsUser={gt_check_location_is_user}")
                    if actual_book_to_return_info and original_list_index_to_pop != -1:
                        s_id_ret, book_id_ret, borrow_date_ret = borrowed_books_for_potential_return.pop(
                            original_list_index_to_pop)
                        print_debug_structured(f"(GenReturn Action Iter {loop_counter})",
                                               f"Popped ('{s_id_ret}', '{book_id_ret}', '{borrow_date_ret}') from index {original_list_index_to_pop}. List now: {borrowed_books_for_potential_return}")
                        target_ret_dt_user = ground_truth.current_date_obj + datetime.timedelta(
                            days=random.randint(1, 2))
                        if target_ret_dt_user <= ground_truth.current_date_obj: target_ret_dt_user = ground_truth.current_date_obj + datetime.timedelta(
                            days=1)
                        if command_queue:
                            match_ret_q = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                            if match_ret_q:
                                main_q_next_dt_ret = datetime.datetime.strptime(match_ret_q.group(0),
                                                                                "[%Y-%m-%d]").date()
                                if main_q_next_dt_ret > target_ret_dt_user:
                                    target_ret_dt_user = main_q_next_dt_ret
                        target_ret_str_user = target_ret_dt_user.strftime("[%Y-%m-%d]")
                        cmd_block_future_ret_user = deque()
                        return_cmd_str_ret_user = f"{target_ret_str_user} {s_id_ret} returned {book_id_ret}"
                        print_debug_structured(f"(GenReturn Scheduling RETURN Iter {loop_counter})",
                                               f"Scheduling: '{return_cmd_str_ret_user}' for date {target_ret_str_user}")
                        if target_ret_dt_user > ground_truth.current_date_obj:
                            open_cmd_ret_user = f"{target_ret_str_user} OPEN"
                            open_needed_for_this_block = True
                            for d_fcb, q_fcb in future_command_blocks:
                                if d_fcb == target_ret_dt_user and q_fcb and q_fcb[
                                    0] == open_cmd_ret_user: open_needed_for_this_block = False; break
                            if open_needed_for_this_block:
                                cmd_block_future_ret_user.appendleft(open_cmd_ret_user)
                        cmd_block_future_ret_user.append(return_cmd_str_ret_user)
                        if cmd_block_future_ret_user:
                            existing_block_idx_ret = -1
                            for i_ret, (d_ret, _) in enumerate(future_command_blocks):
                                if d_ret == target_ret_dt_user: existing_block_idx_ret = i_ret; break
                            if existing_block_idx_ret != -1:
                                _, existing_deque_ret = future_command_blocks[existing_block_idx_ret]
                                if cmd_block_future_ret_user and cmd_block_future_ret_user[0].endswith(
                                        " OPEN") and not (
                                        existing_deque_ret and existing_deque_ret[0].endswith(" OPEN")):
                                    existing_deque_ret.appendleft(cmd_block_future_ret_user.popleft())
                                existing_deque_ret.extend(cmd_block_future_ret_user)
                            else:
                                future_command_blocks.append((target_ret_dt_user, cmd_block_future_ret_user))
                    else:
                        pass  # No valid book to return this time
        # ----- END OF WHILE LOOP -----

        return "AC", student_proc.get_current_log(), "All commands processed.", sent_inputs_for_replay
    except Exception as e_outer:
        err_log_detail = traceback.format_exc();
        err_log = f"Outer Exception: {e_outer}\n{err_log_detail}\n"
        current_log_from_proc = student_proc.get_current_log() if student_proc and hasattr(student_proc,
                                                                                           'log_buffer') else ""
        final_log_content = log_content_on_error
        if current_log_from_proc and current_log_from_proc != log_content_on_error:
            if final_log_content and not final_log_content.endswith("\n"): final_log_content += "\n"
            final_log_content += "Additional logs from student_proc after initial log_content_on_error:\n" + current_log_from_proc
        final_log_content += "\n" + err_log
        return "RE", final_log_content, f"Harness critical error: {e_outer}", sent_inputs_for_replay
    finally:
        if student_proc:
            student_proc.kill()


# ... (上面的代码保持不变) ...

def main():
    use_generator_choice = input(
        f"Run '{DATA_GENERATOR_SCRIPT_NAME}.py' to generate new test cases? (y/n): ").strip().lower()
    if use_generator_choice == 'y':
        try:
            print_console(f"Running {DATA_GENERATOR_SCRIPT_NAME}.py...")
            data_gen_module = importlib.import_module(DATA_GENERATOR_SCRIPT_NAME)
            if hasattr(data_gen_module, 'main') and callable(data_gen_module.main):
                data_gen_module.main()
            else:
                print_error(f"'{DATA_GENERATOR_SCRIPT_NAME}.py' no 'main' function.")
        except ImportError:
            print_error(f"Could not import '{DATA_GENERATOR_SCRIPT_NAME}.py'.")
        except Exception as e_gen:
            print_error(f"Error running '{DATA_GENERATOR_SCRIPT_NAME}.py': {e_gen}"); print_traceback_info()
        print_status_line("-" * 30)

    REPLAY_INPUTS_DIR = os.path.join(RESULTS_DIR, "replay_inputs")
    os.makedirs(REPLAY_INPUTS_DIR, exist_ok=True);
    os.makedirs(CORRECT_LOGS_DIR, exist_ok=True);
    os.makedirs(ERROR_LOGS_DIR, exist_ok=True)

    if not os.path.exists(TESTJAR_DIR) or not os.listdir(TESTJAR_DIR):
        print_console(f"No .jar in '{TESTJAR_DIR}'. Exiting."); return
    jar_files = [f for f in os.listdir(TESTJAR_DIR) if f.endswith(".jar")]
    if not jar_files:
        print_console(f"No .jar in '{TESTJAR_DIR}'. Exiting."); return
    if not os.path.exists(TEST_CASES_DIR) or not os.listdir(TEST_CASES_DIR):
        print_console(f"No test cases in '{TEST_CASES_DIR}'. Exiting."); return
    test_case_files = [os.path.join(TEST_CASES_DIR, f) for f in os.listdir(TEST_CASES_DIR) if
                       os.path.isfile(os.path.join(TEST_CASES_DIR, f)) and f.endswith(".txt")]
    if not test_case_files:
        print_console(f"No .txt test cases in '{TEST_CASES_DIR}'. Exiting."); return

    summary_data = []
    for jar_file_name in jar_files:
        # ***修正点: jar_full_path 移到循环内***
        jar_full_path = os.path.join(TESTJAR_DIR, jar_file_name)
        print_status_line(f"\nCONSOLE: --- Testing JAR: {jar_file_name} ---") # Using status_line for this format
        ac_count, wa_count, re_count = 0, 0, 0
        for tc_file_path in test_case_files:
            tc_name = os.path.basename(tc_file_path)
            print_status_line(f"CONSOLE:   Running Test Case: {tc_name} ... ", end="", flush=True)
            verdict, log_content, reason, recorded_inputs = "RE", "", "Unknown error", []
            try:
                verdict, log_content, reason, recorded_inputs = run_single_test_case(jar_full_path, tc_file_path)
            except Exception as e_run_tc:
                verdict = "RE";
                reason = f"Harness CRITICAL error in run_single_test_case call: {e_run_tc}"
                log_content = (
                                  log_content + "\n" if log_content else "") + f"CRITICAL ERROR (main try-except): {reason}\n{traceback.format_exc()}"
                print_critical(f"CRITICAL ERROR ({reason})") # This should always print
            print_status_line(f"{verdict} (Reason: {reason if reason else 'OK'})")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_base_name = "_".join(
                filter(None, [jar_file_name.replace('.jar', ''), tc_name.replace('.txt', ''), timestamp]))
            safe_reason = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in str(reason)[:50])
            log_path = os.path.join(CORRECT_LOGS_DIR if verdict == "AC" else ERROR_LOGS_DIR,
                                    f"{log_file_base_name}_{verdict}{'_' + safe_reason if verdict != 'AC' and safe_reason else ''}.log")
            replay_input_path = os.path.join(REPLAY_INPUTS_DIR,
                                             f"{log_file_base_name}_{verdict}{'_' + safe_reason if verdict != 'AC' and safe_reason else ''}_replay.txt")
            if verdict == "AC":
                ac_count += 1
            elif verdict == "WA":
                wa_count += 1
            else:
                re_count += 1
            try:
                with open(log_path, 'w', encoding='utf-8') as log_f:
                    log_f.write(f"JAR: {jar_file_name}\nTest Case: {tc_name}\nVerdict: {verdict}\n")
                    if reason: log_f.write(f"Reason: {reason}\n")
                    log_f.write("-" * 20 + " Interaction Log " + "-" * 20 + "\n")
                    log_f.write(log_content if log_content else "Log content unavailable.")
            except Exception as e_log_write:
                print_error(f"writing log file {log_path}: {e_log_write}")
            if recorded_inputs and replay_input_path:
                try:
                    with open(replay_input_path, 'w', encoding='utf-8') as replay_f:
                        for line in recorded_inputs: replay_f.write(line + "\n")
                except Exception as e_replay_write:
                    print_error(f"writing replay input file {replay_input_path}: {e_replay_write}")
        summary_data.append({"jar": jar_file_name, "AC": ac_count, "WA": wa_count, "RE": re_count})

    with open(SUMMARY_FILE, 'w', encoding='utf-8') as sf:
        sf.write("--- Test Summary ---\n")
        for item in summary_data: sf.write(
            f"JAR: {item['jar']}\n  AC: {item['AC']}\n  WA: {item['WA']}\n  RE: {item['RE']}\n\n")

    print_status_line("") # Newline before final summary
    print_console(f"Summary written to {SUMMARY_FILE}")
    print_console(f"Logs stored in {LOGS_DIR}")


if __name__ == "__main__":
    for d in [TESTJAR_DIR, TEST_CASES_DIR, RESULTS_DIR]: os.makedirs(d, exist_ok=True)
    main()
