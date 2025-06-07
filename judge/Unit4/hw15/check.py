import subprocess
import os
import re
import datetime
import shutil
from enum import Enum
from collections import defaultdict, deque
import importlib
import random
import traceback


class PrintModeEnum(Enum):
    BRIEF = "BRIEF"
    DETAILED = "DETAILED"
    DEBUG = "DEBUG"


PRINT_MODE = PrintModeEnum.BRIEF


def print_console(message):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(f"CONSOLE: {message}")


def print_error(message):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(f"CONSOLE ERROR: {message}")


def print_warning(context_tag_or_full_message, details=""):
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
    if PRINT_MODE == PrintModeEnum.DEBUG:
        print(f"CONSOLE DEBUG {context_tag}: {message_details}")


def print_status_line(message, end="\n", flush=False):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(message, end=end, flush=flush)


def print_critical(message): print(message)


def print_traceback_info(): traceback.print_exc()


TESTJAR_DIR = "testjar"
TEST_CASES_DIR = "test_cases"
RESULTS_DIR = "results"
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
CORRECT_LOGS_DIR = os.path.join(LOGS_DIR, "correct")
ERROR_LOGS_DIR = os.path.join(LOGS_DIR, "error")
SUMMARY_FILE = os.path.join(RESULTS_DIR, "summary.txt")
DATA_GENERATOR_SCRIPT_NAME = "data_generator"

PROCESS_TIMEOUT = 10


class BookLocation(Enum):
    BOOKSHELF_NORMAL = "bs"
    BOOKSHELF_HOT = "hbs"
    BORROW_RETURN_OFFICE = "bro"
    APPOINTMENT_OFFICE = "ao"
    READING_ROOM = "rr"
    USER = "user"


class BookCategory(Enum):
    A = "A"
    B = "B"
    C = "C"


CREDIT_SCORE_INITIAL = 100
CREDIT_SCORE_MAX = 180
CREDIT_SCORE_MIN = 0
CREDIT_THRESHOLD_READ_A = 40
CREDIT_THRESHOLD_BORROW = 60
CREDIT_THRESHOLD_ORDER = 100

BOOK_DUE_DAYS = {'B': 30, 'C': 60}
APPOINTMENT_RESERVE_DAYS = 5


class BookCopy:
    def __init__(self, full_id, isbn, category):
        self.full_id = full_id
        self.isbn = isbn
        self.category = category
        self.location = BookLocation.BOOKSHELF_NORMAL
        self.holder_id = None
        self.reserved_for_user_id = None
        self.reservation_expiry_date = None
        self.movement_history = []

    def __repr__(self):
        return f"BookCopy({self.full_id}, loc={self.location.value}, holder={self.holder_id}, reserved_for={self.reserved_for_user_id})"

    def record_move(self, date_str, from_loc_enum_or_str, to_loc_enum_or_str, for_user_id_if_ao=None):
        _from = from_loc_enum_or_str.value if isinstance(from_loc_enum_or_str, Enum) else from_loc_enum_or_str
        _to = to_loc_enum_or_str.value if isinstance(to_loc_enum_or_str, Enum) else to_loc_enum_or_str
        entry = (date_str, _from, _to)
        if for_user_id_if_ao and _to == BookLocation.APPOINTMENT_OFFICE.value:
            entry = (date_str, _from, _to, for_user_id_if_ao)
        self.movement_history.append(entry)


class UserState:
    def __init__(self, student_id):
        self.student_id = student_id
        self.credit_score = CREDIT_SCORE_INITIAL
        self.held_books_info = {}
        self.active_order_isbn = None
        self.reservation_expiry_date = None  # Tracks expiry date of a fulfilled order
        self.reading_book_id_today = None

    @property
    def has_b_book(self):
        return any(info['category'] == BookCategory.B for info in self.held_books_info.values())

    def has_c_book_isbn(self, isbn_to_check):
        return any(info['isbn'] == isbn_to_check and info['category'] == BookCategory.C for info in
                   self.held_books_info.values())

    def can_borrow_b(self):
        return not self.has_b_book

    def can_borrow_c(self, isbn_to_check):
        return not self.has_c_book_isbn(isbn_to_check)

    def can_read_today(self):
        return self.reading_book_id_today is None

    def add_book(self, book_copy: BookCopy, borrow_date_obj):
        self.held_books_info[book_copy.full_id] = {
            "isbn": book_copy.isbn,
            "category": book_copy.category,
            "borrow_date": borrow_date_obj
        }

    def remove_book(self, book_copy: BookCopy):
        if book_copy.full_id in self.held_books_info:
            del self.held_books_info[book_copy.full_id]


class LibraryGroundTruth:
    def __init__(self):
        self.books = {}
        self.books_by_isbn = defaultdict(list)
        self.users = {}
        self.current_date_str = ""
        self.current_date_obj = None
        self.last_processed_penalty_date = None
        self.isbns_interacted_last_open_day = set()
        self.isbns_interacted_current_open_day_user_actions = set()

    def get_or_create_user(self, student_id):
        if student_id not in self.users:
            self.users[student_id] = UserState(student_id)
        return self.users[student_id]

    def _change_credit(self, student_id, amount):
        user = self.get_or_create_user(student_id)
        old_score = user.credit_score
        user.credit_score = max(CREDIT_SCORE_MIN, min(CREDIT_SCORE_MAX, old_score + amount))
        print_debug_structured("(GT Credit)",
                               f"User {student_id} credit: {old_score} -> {user.credit_score} (change: {amount})")

    def setup_books(self, initial_book_data_lines):
        for line in initial_book_data_lines:
            parts = line.split()
            isbn_full = parts[0];
            count = int(parts[1])
            category = BookCategory(isbn_full.split('-')[0])
            for i in range(1, count + 1):
                full_id = f"{isbn_full}-{i:02d}"
                book_copy = BookCopy(full_id, isbn_full, category)
                self.books[full_id] = book_copy
                self.books_by_isbn[isbn_full].append(book_copy)

    def _perform_open_organization_start(self):
        self.isbns_interacted_last_open_day = self.isbns_interacted_current_open_day_user_actions.copy()
        self.isbns_interacted_current_open_day_user_actions.clear()
        for user in self.users.values():
            user.reading_book_id_today = None

    def _process_penalties_up_to(self, date_limit):
        if self.last_processed_penalty_date is None:
            self.last_processed_penalty_date = date_limit - datetime.timedelta(days=1)
            return
        if date_limit <= self.last_processed_penalty_date:
            return

        one_day = datetime.timedelta(days=1)
        scan_date = self.last_processed_penalty_date + one_day
        while scan_date < date_limit:
            # Penalty for overdue books
            for user in self.users.values():
                for book_info in list(user.held_books_info.values()):
                    if book_info['category'].value not in BOOK_DUE_DAYS: continue
                    due_date = book_info['borrow_date'] + datetime.timedelta(
                        days=BOOK_DUE_DAYS[book_info['category'].value])
                    if scan_date >= due_date:
                        self._change_credit(user.student_id, -5)

            # Penalty for not picking up reserved books
            for user in self.users.values():
                if user.active_order_isbn and user.reservation_expiry_date and user.reservation_expiry_date == scan_date:
                    self._change_credit(user.student_id, -15)
                    user.active_order_isbn = None
                    user.reservation_expiry_date = None

            scan_date += one_day
        self.last_processed_penalty_date = date_limit - one_day

    def _process_end_of_day_penalties(self):
        """Processes penalties that only happen at the end of an open day (CLOSE command)."""
        for user in self.users.values():
            if user.reading_book_id_today is not None:
                self._change_credit(user.student_id, -10)

    def set_date(self, date_str):
        new_date_obj = datetime.datetime.strptime(date_str, "[%Y-%m-%d]").date()
        if self.last_processed_penalty_date is None:
            self.last_processed_penalty_date = new_date_obj - datetime.timedelta(days=1)
        self._process_penalties_up_to(new_date_obj)
        self.current_date_str = date_str
        self.current_date_obj = new_date_obj

    def _move_book(self, book_copy: BookCopy, new_location_enum: BookLocation, new_holder_id=None,
                   reserved_for_user_id=None, is_open_organization_context=True):
        old_location_enum = book_copy.location;
        old_holder_id = book_copy.holder_id
        for_user_for_move_record = reserved_for_user_id if new_location_enum == BookLocation.APPOINTMENT_OFFICE else None

        book_copy.record_move(self.current_date_str, old_location_enum.value, new_location_enum.value,
                              for_user_for_move_record)

        if old_location_enum == BookLocation.USER and old_holder_id in self.users:
            self.users[old_holder_id].remove_book(book_copy)
        elif old_location_enum == BookLocation.READING_ROOM and old_holder_id in self.users:
            self.users[old_holder_id].reading_book_id_today = None

        book_copy.location = new_location_enum;
        book_copy.holder_id = new_holder_id

        if new_location_enum == BookLocation.USER and new_holder_id in self.users:
            self.users[new_holder_id].add_book(book_copy, self.current_date_obj)
        elif new_location_enum == BookLocation.READING_ROOM and new_holder_id in self.users:
            self.users[new_holder_id].reading_book_id_today = book_copy.full_id

        if new_location_enum == BookLocation.APPOINTMENT_OFFICE and reserved_for_user_id:
            book_copy.reserved_for_user_id = reserved_for_user_id;
            start_date = self.current_date_obj
            if not is_open_organization_context: start_date += datetime.timedelta(days=1)
            expiry_date = start_date + datetime.timedelta(days=APPOINTMENT_RESERVE_DAYS - 1)
            book_copy.reservation_expiry_date = expiry_date

            user = self.get_or_create_user(reserved_for_user_id)
            if user.active_order_isbn == book_copy.isbn:
                user.reservation_expiry_date = expiry_date
        else:
            book_copy.reserved_for_user_id = None;
            book_copy.reservation_expiry_date = None

    def find_available_copies_on_shelf(self, isbn):
        return [c for c in self.books_by_isbn.get(isbn, []) if
                c.location in [BookLocation.BOOKSHELF_NORMAL, BookLocation.BOOKSHELF_HOT]]

    def handle_borrow_check(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        if user.credit_score < CREDIT_THRESHOLD_BORROW: return False, f"Credit score {user.credit_score} too low to borrow.", None
        category = BookCategory(isbn.split('-')[0])
        if category == BookCategory.A: return False, "Book is Type A, cannot be borrowed.", None
        if category == BookCategory.B and not user.can_borrow_b(): return False, "User already holds a B-type book.", None
        if category == BookCategory.C and not user.can_borrow_c(
                isbn): return False, "User already holds a copy of this C-type ISBN.", None
        available_copies = self.find_available_copies_on_shelf(isbn)
        if not available_copies: return False, f"No copy of {isbn} on any shelf.", None
        return True, "Borrow permissible.", [c.full_id for c in available_copies]

    def handle_return(self, student_id, book_full_id):
        book_copy = self.books.get(book_full_id)
        if not book_copy or book_copy.holder_id != student_id or book_copy.location != BookLocation.USER: return False, f"User {student_id} not holding {book_full_id} or book not with user.", False
        user = self.get_or_create_user(student_id);
        book_info = user.held_books_info.get(book_full_id)
        if not book_info: return False, f"GT Error: User {student_id} holds {book_full_id}, but no borrow info.", False
        category = book_info['category'];
        due_date = book_info['borrow_date'] + datetime.timedelta(days=BOOK_DUE_DAYS[category.value])
        is_overdue = self.current_date_obj > due_date
        if not is_overdue: self._change_credit(student_id, 10)
        self._move_book(book_copy, BookLocation.BORROW_RETURN_OFFICE);
        return True, f"Returned {book_full_id} to BRO.", is_overdue

    def handle_read_check(self, student_id, isbn):
        user = self.get_or_create_user(student_id);
        category = BookCategory(isbn.split('-')[0])
        if category == BookCategory.A and user.credit_score < CREDIT_THRESHOLD_READ_A: return False, f"Credit score {user.credit_score} too low for A-type.", None
        if category in [BookCategory.B,
                        BookCategory.C] and user.credit_score <= 0: return False, "Credit score must be > 0.", None
        if not user.can_read_today(): return False, "User already reading today.", None
        available_copies = self.find_available_copies_on_shelf(isbn)
        if not available_copies: return False, f"No copy of {isbn} on any shelf for reading.", None
        return True, "Read permissible.", [c.full_id for c in available_copies]

    def handle_restore(self, student_id, book_full_id):
        user = self.get_or_create_user(student_id);
        book_copy = self.books.get(book_full_id)
        if not book_copy or book_copy.location != BookLocation.READING_ROOM or book_copy.holder_id != student_id: return False, f"Book {book_full_id} not in RR or not with {student_id}."
        if user.reading_book_id_today != book_full_id: return False, f"User {student_id} state shows not reading {book_full_id}."
        self._change_credit(student_id, 10);
        self._move_book(book_copy, BookLocation.BORROW_RETURN_OFFICE);
        return True, f"Restored {book_full_id} to BRO."

    def handle_order(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        if user.credit_score < CREDIT_THRESHOLD_ORDER: return False, f"Credit score {user.credit_score} too low to order."
        book_category = BookCategory(isbn.split('-')[0])
        if book_category == BookCategory.A: return False, "Book is Type A, cannot be ordered."
        if user.active_order_isbn: return False, "User already has an active order."
        if book_category == BookCategory.B and user.has_b_book: return False, "User holds a B-type, cannot order another B."
        if book_category == BookCategory.C and user.has_c_book_isbn(
                isbn): return False, "User holds this C-type ISBN, cannot order."
        user.active_order_isbn = isbn;
        return True, "Ordered."

    def check_can_pick(self, student_id, isbn_to_pick):
        user = self.get_or_create_user(student_id);
        if not user.active_order_isbn == isbn_to_pick or not user.reservation_expiry_date:
            return False, f"User {student_id} has no fulfilled order for {isbn_to_pick}.", None
        if self.current_date_obj > user.reservation_expiry_date:
            return False, f"Reservation for {isbn_to_pick} for user {student_id} has expired.", None

        book_to_pick = None
        for book_copy in self.books_by_isbn.get(isbn_to_pick, []):
            if book_copy.location == BookLocation.APPOINTMENT_OFFICE and str(book_copy.reserved_for_user_id) == str(
                    student_id):
                book_to_pick = book_copy
                break

        if not book_to_pick: return False, f"No physical copy of {isbn_to_pick} at AO for {student_id}.", None

        category = book_to_pick.category
        if category == BookCategory.B and user.has_b_book: return False, "User would exceed B-type limit.", None
        if category == BookCategory.C and user.has_c_book_isbn(
                isbn_to_pick): return False, "User would exceed C-type limit for this ISBN.", None
        return True, "Pick permissible.", book_to_pick.full_id

    def handle_pick(self, student_id, isbn_to_pick):
        can_pick, reason, book_full_id = self.check_can_pick(student_id, isbn_to_pick)
        if not can_pick: return False, reason, None
        user = self.get_or_create_user(student_id);
        book_to_give = self.books[book_full_id]
        self._move_book(book_to_give, BookLocation.USER, new_holder_id=student_id)
        user.active_order_isbn = None;
        user.reservation_expiry_date = None
        return True, f"Picked {book_full_id}.", book_full_id

    def handle_query(self, student_id, query_str):
        if query_str == "credit score": user = self.get_or_create_user(student_id); return True, str(user.credit_score)
        book_full_id = query_str;
        book_copy = self.books.get(book_full_id)
        if not book_copy: return False, f"Book {book_full_id} not found in GT."
        expected_trace = []
        for i, trace_item in enumerate(book_copy.movement_history):
            date_str, _from, _to = trace_item[0], trace_item[1], trace_item[2]
            line = f"{i + 1} {date_str} from {_from} to {_to}";
            expected_trace.append(line)
        return True, expected_trace

    def handle_student_organization_move(self, date_str, book_full_id, from_loc_str, to_loc_str,
                                         for_student_id_str=None, is_open_organization_context=True):
        book_copy = self.books.get(book_full_id)
        if not book_copy: return "WA", f"Move non-existent book {book_full_id}"
        valid_org_locs = {loc.value for loc in BookLocation if loc != BookLocation.USER}
        if from_loc_str not in valid_org_locs or to_loc_str not in valid_org_locs: return "WA", "Invalid org location"
        if from_loc_str == to_loc_str: return "WA", "Move from/to same location"
        if book_copy.location.value != from_loc_str: return "WA", f"Book {book_full_id} is at {book_copy.location.value}, student says {from_loc_str}"

        is_reserved_and_locked = (
                book_copy.location == BookLocation.APPOINTMENT_OFFICE and
                book_copy.reserved_for_user_id and
                book_copy.reservation_expiry_date and
                (
                        self.current_date_obj < book_copy.reservation_expiry_date or
                        (self.current_date_obj == book_copy.reservation_expiry_date and is_open_organization_context)
                )
        )
        if is_reserved_and_locked:
            return "WA", f"Book {book_copy.full_id} is reserved and cannot be moved."

        if to_loc_str == 'ao':
            if not for_student_id_str: return "WA", "Move to AO must specify user"
            target_user = self.get_or_create_user(for_student_id_str)
            if target_user.active_order_isbn != book_copy.isbn: return "WA", f"User {for_student_id_str} has no active order for {book_copy.isbn}"
        self._move_book(book_copy, BookLocation(to_loc_str), reserved_for_user_id=for_student_id_str,
                        is_open_organization_context=is_open_organization_context);
        return "OK", "Move applied."

    def verify_organization_rules(self, is_open_org_context):
        if is_open_org_context:
            for book_copy in self.books.values():
                if book_copy.location in [BookLocation.BORROW_RETURN_OFFICE,
                                          BookLocation.READING_ROOM]: return "WA", f"Book {book_copy.full_id} in {book_copy.location.value} after OPEN org."
                if book_copy.location == BookLocation.APPOINTMENT_OFFICE:
                    user_id = book_copy.reserved_for_user_id
                    if user_id and str(user_id) in self.users:
                        user = self.users[str(user_id)]
                        # Check if the book in AO is expired according to the user's state
                        if user.active_order_isbn == book_copy.isbn and user.reservation_expiry_date and self.current_date_obj > user.reservation_expiry_date:
                            return "WA", f"Overdue book {book_copy.full_id} in AO after OPEN org."

                is_hot = book_copy.isbn in self.isbns_interacted_last_open_day
                if book_copy.location == BookLocation.BOOKSHELF_HOT and not is_hot: return "WA", f"Non-hot book {book_copy.full_id} on HBS."
                if book_copy.location == BookLocation.BOOKSHELF_NORMAL and is_hot: return "WA", f"Hot book {book_copy.full_id} on BS."
        return "OK", "Rules satisfied."


class StudentProcess:
    def __init__(self, jar_path):
        self.jar_path = jar_path;
        self.process = None;
        self.log_buffer = []

    def start(self):
        try:
            self.process = subprocess.Popen(['java', '-jar', self.jar_path], stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                                            errors='replace', bufsize=1);
            self.log_buffer.append(f"Harness: Started {self.jar_path}");
            return True
        except Exception as e:
            print_error(f"Failed to start {self.jar_path}: {e}");
            print_traceback_info();
            self.log_buffer.append(f"Harness ERROR: Failed to start {self.jar_path}: {e}");
            return False

    def send_input(self, line):
        if not self.process or self.process.poll() is not None: self.log_buffer.append(
            "Harness ERROR: Process not running when sending input."); return False
        try:
            print_send(line);
            self.log_buffer.append(f"Harness SEND: {line}");
            self.process.stdin.write(line + "\n");
            self.process.stdin.flush();
            return True
        except Exception as e:
            print_error(f"Failed to send input '{line}': {e}");
            print_traceback_info();
            self.log_buffer.append(f"Harness ERROR: Failed to send input '{line}': {e}");
            self.kill();
            return False

    def read_output_line(self):
        if not self.process or self.process.poll() is not None: self.log_buffer.append(
            "Harness ERROR: Process not running when reading output."); return None
        try:
            line = self.process.stdout.readline()
            if line:
                line = line.strip();
                print_recv(line);
                self.log_buffer.append(f"Student RECV: {line}");
                return line
            else:
                self.log_buffer.append(f"Student RECV: [EOF from stdout.readline()]");
                return None
        except Exception as e:
            print_error(f"Failed to read output: {e}");
            print_traceback_info();
            self.log_buffer.append(f"Harness ERROR: Failed to read output: {e}");
            self.kill();
            return None

    def read_expected_lines(self, count):
        lines = [];
        for i in range(count):
            line = self.read_output_line()
            if line is None: self.log_buffer.append(
                f"Harness ERROR: Expected {count} lines, got None at line {i + 1}."); return None
            lines.append(line)
        return lines

    def get_current_log(self):
        return "\n".join(self.log_buffer)

    def kill(self):
        if self.process and self.process.poll() is None:
            self.log_buffer.append("Harness: Attempting to terminate student process.");
            try:
                self.process.terminate();
                self.process.wait(timeout=PROCESS_TIMEOUT / 2)
            except subprocess.TimeoutExpired:
                self.log_buffer.append("Harness: Process did not terminate, killing.");
                print_console("Student process did not terminate gracefully, killing...");
                self.process.kill()
                try:
                    self.process.wait(timeout=PROCESS_TIMEOUT / 2)
                except subprocess.TimeoutExpired:
                    self.log_buffer.append("Harness: Process kill command also timed out.")
            except Exception as e:
                self.log_buffer.append(
                    f"Harness: Exception during process termination/kill: {e}");
                print_traceback_info()
        elif self.process:
            self.log_buffer.append(
                f"Harness: Student process already terminated (exit code: {self.process.returncode}).")


ACTION_RESPONSE_REGEX = re.compile(
    r"\[(\d{4}-\d{2}-\d{2})\] \[(accept|reject)\] (\S+) (\w+) (\S+)(?: (not overdue|overdue))?")
QUERY_HEADER_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] (\S+-\d{4}-\d+) moving trace: (\d+)")
QUERY_CREDIT_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] (\S+) (\d+)")
ORG_MOVE_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] move (\S+-\d{4}-\d+) from (\S+) to (\S+)(?: for (\S+))?")


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
    if len(commands_spec) != len(raw_commands_spec): print_warning("(ParseTC)",
                                                                   f"Some lines after book specs were filtered out (Original: {len(raw_commands_spec)}, Filtered: {len(commands_spec)}).")
    return initial_books_spec, commands_spec


def run_single_test_case(jar_path, test_case_file_path):
    student_proc = StudentProcess(jar_path)
    sent_inputs_for_replay = []
    log_content_on_error = ""
    try:
        if not student_proc.start():
            return "RE", student_proc.get_current_log(), "Failed to start JAR.", sent_inputs_for_replay

        log_content_on_error = student_proc.get_current_log()
        try:
            initial_books_spec, commands_spec = parse_test_case_file(test_case_file_path)
        except Exception as e_parse:
            log_content_on_error += f"\nError parsing TC {test_case_file_path}: {e_parse}"
            return "RE", log_content_on_error, f"TC Parse Error: {e_parse}", sent_inputs_for_replay

        ground_truth = LibraryGroundTruth()

        initial_book_count_str = str(len(initial_books_spec))
        if not student_proc.send_input(initial_book_count_str):
            return "RE", student_proc.get_current_log(), "Fail send book count.", sent_inputs_for_replay
        sent_inputs_for_replay.append(initial_book_count_str)

        for book_line in initial_books_spec:
            if not student_proc.send_input(book_line):
                return "RE", student_proc.get_current_log(), f"Fail send book spec: {book_line}", sent_inputs_for_replay
            sent_inputs_for_replay.append(book_line)

        ground_truth.setup_books(initial_books_spec)
        command_queue = deque(commands_spec)
        pending_today_after_user_action = deque()
        future_command_blocks = []
        borrowed_books_for_potential_return = []
        ordered_books_for_potential_pick = []
        reading_books_for_potential_restore = []
        pick_attempts_count = defaultdict(int)
        restore_attempts_count = defaultdict(int)
        harness_current_processing_date_str = None
        harness_is_library_open = False

        loop_counter = 0
        max_loops = 5000
        while loop_counter < max_loops:
            loop_counter += 1
            next_command_str = None
            current_harness_date_obj = None

            if harness_current_processing_date_str:
                try:
                    current_harness_date_obj = datetime.datetime.strptime(harness_current_processing_date_str,
                                                                          "[%Y-%m-%d]").date()
                except ValueError:
                    return "RE", student_proc.get_current_log(), f"Harness Error: Invalid date string: {harness_current_processing_date_str}", sent_inputs_for_replay

            future_command_blocks.sort(key=lambda x: x[0])

            if pending_today_after_user_action:
                next_command_str = pending_today_after_user_action.popleft()
            else:
                next_main_q_date = None
                if command_queue:
                    m = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                    if m: next_main_q_date = datetime.datetime.strptime(m.group(0), "[%Y-%m-%d]").date()

                next_future_q_date = future_command_blocks[0][0] if future_command_blocks else None

                if next_main_q_date and (
                        current_harness_date_obj is None or next_main_q_date == current_harness_date_obj):
                    next_command_str = command_queue.popleft()
                else:
                    next_op_date = None
                    if next_main_q_date and next_future_q_date:
                        next_op_date = min(next_main_q_date, next_future_q_date)
                    elif next_main_q_date:
                        next_op_date = next_main_q_date
                    elif next_future_q_date:
                        next_op_date = next_future_q_date

                    if harness_is_library_open and next_op_date and next_op_date > current_harness_date_obj:
                        next_command_str = f"{harness_current_processing_date_str} CLOSE"
                    elif next_op_date:
                        if next_main_q_date == next_op_date:
                            next_command_str = command_queue.popleft()
                        else:
                            _date, cmds = future_command_blocks.pop(0)
                            pending_today_after_user_action.extend(cmds)

            if next_command_str is None:
                if not command_queue and not future_command_blocks and not pending_today_after_user_action:
                    break
                if harness_is_library_open:
                    next_command_str = f"{harness_current_processing_date_str} CLOSE"
                else:
                    continue

            command_str_for_send = next_command_str

            date_match_proc = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_str_for_send)
            if not date_match_proc: return "RE", student_proc.get_current_log(), f"Command missing date: {command_str_for_send}", sent_inputs_for_replay
            date_from_current_cmd_str = date_match_proc.group(0)

            if harness_current_processing_date_str is None or date_from_current_cmd_str != harness_current_processing_date_str:
                if harness_is_library_open: print_warning("(Date Advance)",
                                                          f"Advancing to {date_from_current_cmd_str} but library was open.")
                harness_current_processing_date_str = date_from_current_cmd_str
                current_harness_date_obj = datetime.datetime.strptime(harness_current_processing_date_str,
                                                                      "[%Y-%m-%d]").date()
                harness_is_library_open = False
                ground_truth.set_date(harness_current_processing_date_str)
                if future_command_blocks and future_command_blocks[0][0] == current_harness_date_obj:
                    _f_date, f_cmds_for_new_day = future_command_blocks.pop(0)
                    if f_cmds_for_new_day: pending_today_after_user_action.extendleft(reversed(f_cmds_for_new_day))

            is_open_command = command_str_for_send.endswith(" OPEN")
            is_close_command = command_str_for_send.endswith(" CLOSE")

            if is_open_command:
                ground_truth._perform_open_organization_start();
                harness_is_library_open = True
            elif is_close_command:
                harness_is_library_open = False;
                pending_today_after_user_action.clear()

            if not student_proc.send_input(command_str_for_send):
                return "RE", student_proc.get_current_log(), f"Failed to send command: {command_str_for_send}", sent_inputs_for_replay
            sent_inputs_for_replay.append(command_str_for_send)
            log_content_on_error = student_proc.get_current_log()

            if is_open_command or is_close_command:
                context_str = "OPEN" if is_open_command else "CLOSE"
                if is_close_command:
                    ground_truth._process_end_of_day_penalties()

                output_k = student_proc.read_output_line()
                if output_k is None: return "RE", student_proc.get_current_log(), f"Timeout K for {context_str}", sent_inputs_for_replay
                try:
                    num_moves = int(output_k);
                    assert num_moves >= 0
                except (ValueError, AssertionError):
                    return "WA", student_proc.get_current_log(), f"{context_str}: Bad K: '{output_k}'", sent_inputs_for_replay

                if num_moves > 0:
                    move_lines = student_proc.read_expected_lines(num_moves)
                    if move_lines is None: return "RE", student_proc.get_current_log(), f"Timeout {context_str} moves", sent_inputs_for_replay
                    for move_str in move_lines:
                        match = ORG_MOVE_REGEX.match(move_str)
                        if not match: return "WA", student_proc.get_current_log(), f"{context_str}: Bad move: '{move_str}'", sent_inputs_for_replay
                        _d, b_id, _f, _t, for_s = match.groups()
                        if _d != harness_current_processing_date_str.strip("[]"):
                            return "WA", student_proc.get_current_log(), f"{context_str} move: Date mismatch", sent_inputs_for_replay
                        stat, rea = ground_truth.handle_student_organization_move(harness_current_processing_date_str,
                                                                                  b_id, _f, _t, for_s, is_open_command)
                        if stat == "WA": return "WA", student_proc.get_current_log(), f"{context_str} org move: {rea}", sent_inputs_for_replay

                log_content_on_error = student_proc.get_current_log()
                stat_rules, rea_rules = ground_truth.verify_organization_rules(is_open_org_context=is_open_command)
                if stat_rules == "WA": return "WA", student_proc.get_current_log(), f"{context_str}: Rule violation: {rea_rules}", sent_inputs_for_replay

                earliest_next_action_date = ground_truth.current_date_obj
                if is_close_command: earliest_next_action_date += datetime.timedelta(days=1)

                target_date_for_pick = None
                for cmd_peek in command_queue:
                    if " OPEN" in cmd_peek:
                        match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", cmd_peek)
                        if match:
                            d = datetime.datetime.strptime(match.group(0), "[%Y-%m-%d]").date()
                            if d >= earliest_next_action_date:
                                target_date_for_pick = d
                                break
                if target_date_for_pick:
                    new_pick_commands, remaining_orders = deque(), []
                    for s_id, isbn, o_date in ordered_books_for_potential_pick:
                        key = (s_id, isbn, o_date);
                        user = ground_truth.users.get(s_id)
                        if user and user.active_order_isbn == isbn and pick_attempts_count.get(key, 0) < 2:
                            can_pick, _, _ = ground_truth.check_can_pick(s_id, isbn)
                            if can_pick:
                                new_pick_commands.append(
                                    f"[{target_date_for_pick.strftime('%Y-%m-%d')}] {s_id} picked {isbn}")
                            else:
                                remaining_orders.append((s_id, isbn, o_date))
                        elif user and user.active_order_isbn == isbn:
                            remaining_orders.append((s_id, isbn, o_date))

                    ordered_books_for_potential_pick = remaining_orders
                    if new_pick_commands:
                        fcb_idx = next(
                            (i for i, (d, _) in enumerate(future_command_blocks) if d == target_date_for_pick), -1)
                        if fcb_idx != -1:
                            future_command_blocks[fcb_idx][1].extend(new_pick_commands)
                        else:
                            future_command_blocks.append(
                                (target_date_for_pick, new_pick_commands));
                            future_command_blocks.sort(
                                key=lambda x: x[0])
                        print_debug_structured("(DynGen PICK)",
                                               f"Scheduled {len(new_pick_commands)} picks for next open day: {target_date_for_pick}")
            else:
                parts = command_str_for_send.split()
                _d_cmd, student_id, action_verb = parts[0], parts[1], parts[2]
                book_identifier_from_input = ""
                if len(parts) > 3:
                    if parts[3] == "credit" and len(parts) > 4 and parts[4] == "score":
                        book_identifier_from_input = "credit score"
                    else:
                        book_identifier_from_input = parts[3]

                student_output_line = student_proc.read_output_line()
                if student_output_line is None: return "RE", student_proc.get_current_log(), f"Timeout resp for {action_verb}", sent_inputs_for_replay
                log_content_on_error = student_proc.get_current_log()

                if action_verb == "queried":
                    if book_identifier_from_input == "credit score":
                        query_match = QUERY_CREDIT_REGEX.match(student_output_line)
                        if not query_match: return "WA", student_proc.get_current_log(), f"queried credit score: Bad response format: '{student_output_line}'", sent_inputs_for_replay
                        s_date_q, s_id_q, s_score_str_q = query_match.groups()
                        if s_date_q != harness_current_processing_date_str.strip(
                                "[]") or s_id_q != student_id: return "WA", student_proc.get_current_log(), "queried credit score: Response date/ID mismatch.", sent_inputs_for_replay
                        gt_ok_q, gt_score_q = ground_truth.handle_query(student_id, "credit score")
                        if not gt_ok_q: return "RE", student_proc.get_current_log(), f"GT failed on credit query: {gt_score_q}", sent_inputs_for_replay
                        if s_score_str_q != gt_score_q: return "WA", student_proc.get_current_log(), f"queried credit score: Mismatch. Student:{s_score_str_q} GT:{gt_score_q}", sent_inputs_for_replay
                    else:
                        query_match_header = QUERY_HEADER_REGEX.match(student_output_line)
                        if not query_match_header: return "WA", student_proc.get_current_log(), f"queried book trace: Bad response header: '{student_output_line}'", sent_inputs_for_replay
                        s_date_q, s_book_id_q, s_num_str_q = query_match_header.groups()
                        if s_date_q != harness_current_processing_date_str.strip(
                                "[]") or s_book_id_q != book_identifier_from_input: return "WA", student_proc.get_current_log(), "queried book trace: Response header date/ID mismatch.", sent_inputs_for_replay
                        try:
                            s_num_q = int(s_num_str_q);
                            assert s_num_q >= 0
                        except (ValueError, AssertionError):
                            return "WA", student_proc.get_current_log(), f"queried book trace: Bad number of traces: '{s_num_str_q}'", sent_inputs_for_replay

                        student_lines = student_proc.read_expected_lines(s_num_q) if s_num_q > 0 else []
                        if s_num_q > 0 and student_lines is None: return "RE", student_proc.get_current_log(), "Timeout reading query traces", sent_inputs_for_replay

                        gt_ok_q, gt_lines = ground_truth.handle_query(student_id, book_identifier_from_input)
                        if not gt_ok_q: return "RE", student_proc.get_current_log(), f"GT failed on book trace query: {gt_lines}", sent_inputs_for_replay
                        if len(student_lines) != len(
                                gt_lines): return "WA", student_proc.get_current_log() + f"\nGT TRACE:\n" + "\n".join(
                            gt_lines), f"queried book trace: Trace count mismatch. S:{len(student_lines)} GT:{len(gt_lines)}", sent_inputs_for_replay
                        for i, (s_line, gt_line) in enumerate(zip(student_lines, gt_lines)):
                            if s_line.strip() != gt_line.strip(): return "WA", student_proc.get_current_log(), f"queried book trace: Line {i + 1} mismatch.\nS:'{s_line}'\nGT:'{gt_line}'", sent_inputs_for_replay
                else:
                    action_match = ACTION_RESPONSE_REGEX.match(student_output_line)
                    if not action_match: return "WA", student_proc.get_current_log(), f"{action_verb}: Bad resp format: '{student_output_line}'", sent_inputs_for_replay
                    s_date, s_status, s_student_id, s_action, s_book_details, s_overdue = action_match.groups()
                    if s_date != harness_current_processing_date_str.strip(
                            "[]") or s_student_id != student_id or s_action != action_verb: return "WA", student_proc.get_current_log(), f"{action_verb}: Mismatch in resp date/ID/action.", sent_inputs_for_replay

                    if action_verb == "borrowed":
                        gt_ok, gt_msg, gt_bids = ground_truth.handle_borrow_check(student_id,
                                                                                  book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok: return "WA", student_proc.get_current_log(), f"borrowed: S:accept, GT:reject. GT:{gt_msg}", sent_inputs_for_replay
                            if s_book_details not in gt_bids: return "WA", student_proc.get_current_log(), f"borrowed [accept]: Student chose invalid copy '{s_book_details}'. Valid: {gt_bids}", sent_inputs_for_replay
                            chosen_book = ground_truth.books[s_book_details];
                            ground_truth._move_book(chosen_book, BookLocation.USER, new_holder_id=student_id)
                            ground_truth.isbns_interacted_current_open_day_user_actions.add(book_identifier_from_input)
                            borrowed_books_for_potential_return.append(
                                (student_id, s_book_details, harness_current_processing_date_str))
                        elif s_status == "reject":
                            if gt_ok: pass
                            if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"borrowed [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "read":
                        gt_ok, gt_msg, gt_bids = ground_truth.handle_read_check(student_id, book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok: return "WA", student_proc.get_current_log(), f"read: S:accept, GT:reject. GT:{gt_msg}", sent_inputs_for_replay
                            if s_book_details not in gt_bids: return "WA", student_proc.get_current_log(), f"read [accept]: Student chose invalid copy '{s_book_details}'. Valid: {gt_bids}", sent_inputs_for_replay
                            chosen_book = ground_truth.books[s_book_details];
                            ground_truth._move_book(chosen_book, BookLocation.READING_ROOM, new_holder_id=student_id)
                            ground_truth.isbns_interacted_current_open_day_user_actions.add(book_identifier_from_input)
                            reading_books_for_potential_restore.append(
                                (student_id, s_book_details, harness_current_processing_date_str))
                        elif s_status == "reject":
                            if gt_ok: pass
                            if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"read [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "ordered":
                        gt_ok, gt_msg = ground_truth.handle_order(student_id, book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok: return "WA", student_proc.get_current_log(), f"ordered: S:accept, GT:reject. GT:{gt_msg}", sent_inputs_for_replay
                            if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"ordered [accept]: ISBN mismatch.", sent_inputs_for_replay
                            key = (student_id, book_identifier_from_input, harness_current_processing_date_str)
                            ordered_books_for_potential_pick.append(key);
                            pick_attempts_count[key] = 0
                        elif s_status == "reject":
                            if gt_ok:
                                user = ground_truth.users.get(student_id)
                                if user and user.active_order_isbn == book_identifier_from_input: user.active_order_isbn = None
                            if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"ordered [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "returned":
                        gt_ok, gt_msg, gt_is_overdue = ground_truth.handle_return(student_id,
                                                                                  book_identifier_from_input)
                        if not gt_ok: return "RE", student_proc.get_current_log(), f"Harness Bug: GT rejected dynamic return: {gt_msg}", sent_inputs_for_replay
                        if s_status != "accept": return "WA", student_proc.get_current_log(), "returned: Student rejected valid return.", sent_inputs_for_replay
                        if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), "returned [accept]: Book full_id mismatch.", sent_inputs_for_replay
                        expected_overdue = "overdue" if gt_is_overdue else "not overdue"
                        if s_overdue != expected_overdue: return "WA", student_proc.get_current_log(), f"Return overdue status mismatch. S:{s_overdue}, GT:{expected_overdue}", sent_inputs_for_replay

                    elif action_verb == "restored":
                        gt_ok, gt_msg = ground_truth.handle_restore(student_id, book_identifier_from_input)
                        if not gt_ok: return "RE", student_proc.get_current_log(), f"Harness Bug: GT rejected dynamic restore: {gt_msg}", sent_inputs_for_replay
                        if s_status != "accept": return "WA", student_proc.get_current_log(), "restored: Student rejected valid restore.", sent_inputs_for_replay
                        if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), "restored [accept]: Book full_id mismatch.", sent_inputs_for_replay

                    elif action_verb == "picked":
                        key = next((k for k in pick_attempts_count if
                                    k[0] == student_id and k[1] == book_identifier_from_input), None)
                        if key: pick_attempts_count[key] += 1

                        gt_ok, gt_msg, gt_bid = ground_truth.handle_pick(student_id, book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok: return "WA", student_proc.get_current_log(), f"picked: S:accept, GT:reject. GT:{gt_msg}", sent_inputs_for_replay
                            if s_book_details != gt_bid: return "WA", student_proc.get_current_log(), f"picked [accept]: Picked '{s_book_details}', GT expected '{gt_bid}'.", sent_inputs_for_replay
                            borrowed_books_for_potential_return.append(
                                (student_id, gt_bid, harness_current_processing_date_str))
                            ordered_books_for_potential_pick = [o for o in ordered_books_for_potential_pick if not (
                                    o[0] == student_id and o[1] == book_identifier_from_input)]
                        elif s_status == "reject":
                            if gt_ok:
                                book_to_rb = ground_truth.books.get(gt_bid);
                                user_to_rb = ground_truth.users.get(student_id)
                                if book_to_rb and user_to_rb and book_to_rb.location == BookLocation.USER:
                                    ground_truth._move_book(book_to_rb, BookLocation.APPOINTMENT_OFFICE,
                                                            reserved_for_user_id=student_id,
                                                            is_open_organization_context=True)
                                    user_to_rb.active_order_isbn = book_identifier_from_input;
                                    user_to_rb.reservation_expiry_date = book_to_rb.reservation_expiry_date
                            if s_book_details != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"picked [reject]: ISBN mismatch.", sent_inputs_for_replay
                    else:
                        return "RE", student_proc.get_current_log(), f"Harness Error: Unhandled action verb '{action_verb}'.", sent_inputs_for_replay

                if borrowed_books_for_potential_return and random.random() < 0.2:
                    next_open_day_date = None
                    for cmd_peek in command_queue:
                        if " OPEN" in cmd_peek:
                            match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", cmd_peek)
                            if match:
                                d = datetime.datetime.strptime(match.group(0), "[%Y-%m-%d]").date()
                                if d >= ground_truth.current_date_obj: next_open_day_date = d; break
                    if next_open_day_date:
                        s_id, b_id, _ = borrowed_books_for_potential_return.pop(
                            random.randrange(len(borrowed_books_for_potential_return)))
                        return_cmd = f"[{next_open_day_date.strftime('%Y-%m-%d')}] {s_id} returned {b_id}"
                        fcb_idx = next((i for i, (d, _) in enumerate(future_command_blocks) if d == next_open_day_date),
                                       -1)
                        if fcb_idx != -1:
                            future_command_blocks[fcb_idx][1].append(return_cmd)
                        else:
                            future_command_blocks.append(
                                (next_open_day_date, deque([return_cmd])));
                            future_command_blocks.sort(
                                key=lambda x: x[0])
                        print_debug_structured("(DynGen RETURN)", f"Scheduled return for next open day: {return_cmd}")

                if harness_is_library_open and reading_books_for_potential_restore and random.random() < 0.3:
                    pop_idx = -1
                    for i, (s_id, b_id, r_date_str) in enumerate(reading_books_for_potential_restore):
                        key = (s_id, b_id, r_date_str)
                        if r_date_str == harness_current_processing_date_str and restore_attempts_count.get(key, 0) < 1:
                            pop_idx = i;
                            break
                    if pop_idx != -1:
                        s_id, b_id, r_date_str = reading_books_for_potential_restore.pop(pop_idx)
                        restore_cmd = f"{harness_current_processing_date_str} {s_id} restored {b_id}"
                        pending_today_after_user_action.append(restore_cmd)
                        restore_attempts_count[(s_id, b_id, r_date_str)] += 1

        if loop_counter >= max_loops:
            return "RE", student_proc.get_current_log(), f"Max loops ({max_loops}) exceeded.", sent_inputs_for_replay

        return "AC", student_proc.get_current_log(), "All commands processed.", sent_inputs_for_replay
    except Exception as e_outer:
        print_critical(f"Outer Exception in run_single_test_case: {e_outer}")
        print_traceback_info()
        return "RE", student_proc.get_current_log() + f"\nOuter Exception: {e_outer}\n{traceback.format_exc()}", f"Harness critical error: {e_outer}", sent_inputs_for_replay
    finally:
        if student_proc: student_proc.kill()


def main():
    use_generator_choice = input(
        f"Run '{DATA_GENERATOR_SCRIPT_NAME}.py' to generate new test cases? (y/n): ").strip().lower()
    if use_generator_choice == 'y':
        try:
            print_console(f"Running {DATA_GENERATOR_SCRIPT_NAME}.py...");
            data_gen_module = importlib.import_module(DATA_GENERATOR_SCRIPT_NAME.replace('.py', ''))
            if hasattr(data_gen_module, 'main') and callable(data_gen_module.main):
                if hasattr(data_gen_module, 'TEST_CASES_DIR'): setattr(data_gen_module, 'TEST_CASES_DIR',
                                                                       TEST_CASES_DIR)
                data_gen_module.main()
            else:
                print_error(f"'{DATA_GENERATOR_SCRIPT_NAME}.py' no 'main' function.")
        except ImportError:
            print_error(f"Could not import '{DATA_GENERATOR_SCRIPT_NAME}.py'.");
            print_traceback_info()
        except Exception as e_gen:
            print_error(f"Error running '{DATA_GENERATOR_SCRIPT_NAME}.py': {e_gen}");
            print_traceback_info()
        print_status_line("-" * 30)

    REPLAY_INPUTS_DIR = os.path.join(RESULTS_DIR, "replay_inputs")

    for d in [TESTJAR_DIR, TEST_CASES_DIR, RESULTS_DIR, LOGS_DIR, CORRECT_LOGS_DIR, ERROR_LOGS_DIR,
              REPLAY_INPUTS_DIR]: os.makedirs(d, exist_ok=True)
    if not os.path.exists(TESTJAR_DIR) or not os.listdir(TESTJAR_DIR): print_console(
        f"No .jar in '{TESTJAR_DIR}'. Exiting."); return
    jar_files = [f for f in os.listdir(TESTJAR_DIR) if f.endswith(".jar")]
    if not jar_files: print_console(f"No .jar in '{TESTJAR_DIR}'. Exiting."); return
    if not os.path.exists(TEST_CASES_DIR) or not os.listdir(TEST_CASES_DIR): print_console(
        f"No test cases in '{TEST_CASES_DIR}'. Exiting."); return
    test_case_files = [os.path.join(TEST_CASES_DIR, f) for f in os.listdir(TEST_CASES_DIR) if
                       os.path.isfile(os.path.join(TEST_CASES_DIR, f)) and f.endswith(".txt")]
    if not test_case_files: print_console(f"No .txt test cases in '{TEST_CASES_DIR}'. Exiting."); return

    summary_data = []
    for jar_file_name in jar_files:
        jar_full_path = os.path.join(TESTJAR_DIR, jar_file_name)
        print_status_line(f"\nCONSOLE: --- Testing JAR: {jar_file_name} ---")
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
                log_content_tc_exc = (
                                         log_content + "\n" if log_content else "") + f"CRITICAL ERROR (main try-except for TC): {reason}\n{traceback.format_exc()}"
                print_critical(f"CRITICAL ERROR ({reason}) for TC {tc_name}");
                print_traceback_info();
                log_content = log_content_tc_exc
            print_status_line(f"{verdict} (Reason: {reason if reason else 'OK'})")
            timestamp_log = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_base_name = "_".join(
                filter(None, [jar_file_name.replace('.jar', ''), tc_name.replace('.txt', ''), timestamp_log]))
            safe_reason_log = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in str(reason)[:50])
            log_dir = CORRECT_LOGS_DIR if verdict == "AC" else ERROR_LOGS_DIR
            log_file_name = f"{log_file_base_name}_{verdict}{'_' + safe_reason_log if verdict != 'AC' and safe_reason_log else ''}.log"
            student_log_path = os.path.join(log_dir, log_file_name)

            if verdict == "AC":
                ac_count += 1
            elif verdict == "WA":
                wa_count += 1
            else:
                re_count += 1

            try:
                with open(student_log_path, 'w', encoding='utf-8') as log_f:
                    log_f.write(f"JAR: {jar_file_name}\nTest Case: {tc_name}\nVerdict: {verdict}\n")
                    if reason: log_f.write(f"Reason: {reason}\n")
                    log_f.write("-" * 20 + " Interaction Log " + "-" * 20 + "\n");
                    log_f.write(log_content if log_content else "Log content unavailable.")
            except Exception as e_log:
                print_error(f"writing log file {student_log_path}: {e_log}")

            if recorded_inputs:
                replay_file_name = f"{log_file_base_name}_{verdict}{'_' + safe_reason_log if verdict != 'AC' and safe_reason_log else ''}_replay.txt"
                replay_input_path = os.path.join(REPLAY_INPUTS_DIR, replay_file_name)
                try:
                    with open(replay_input_path, 'w', encoding='utf-8') as replay_f:
                        for line in recorded_inputs: replay_f.write(line + "\n")
                except Exception as e_replay:
                    print_error(f"writing replay file {replay_input_path}: {e_replay}")

        summary_data.append({"jar": jar_file_name, "AC": ac_count, "WA": wa_count, "RE": re_count})

    with open(SUMMARY_FILE, 'w', encoding='utf-8') as sf:
        sf.write("--- Test Summary ---\n")
        for item in summary_data: sf.write(
            f"JAR: {item['jar']}\n  AC: {item['AC']}\n  WA: {item['WA']}\n  RE: {item['RE']}\n\n")
    print_status_line("\n");
    print_console(f"Summary written to {SUMMARY_FILE}");
    print_console(f"Logs stored in {LOGS_DIR}");
    print_console(f"Replay input files stored in {REPLAY_INPUTS_DIR}")


if __name__ == "__main__":
    main()