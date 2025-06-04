import subprocess
import os
import re
import datetime  # Removed json as it wasn't used
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


PRINT_MODE = PrintModeEnum.BRIEF# Default to BRIEF, user can change to DEBUG for more console output


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


def print_debug_structured(context_tag, message_details):  # Now only prints if DEBUG mode
    if PRINT_MODE == PrintModeEnum.DEBUG:
        print(f"CONSOLE DEBUG {context_tag}: {message_details}")


def print_status_line(message, end="\n", flush=False):
    if PRINT_MODE in [PrintModeEnum.DEBUG, PrintModeEnum.DETAILED, PrintModeEnum.BRIEF]:
        print(message, end=end, flush=flush)


def print_critical(message): print(message)


def print_traceback_info(): traceback.print_exc()


# --- Configuration ---
TESTJAR_DIR = "testjar"
TEST_CASES_DIR = "test_cases"
RESULTS_DIR = "results"
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")  # For student-facing interaction logs
CORRECT_LOGS_DIR = os.path.join(LOGS_DIR, "correct")
ERROR_LOGS_DIR = os.path.join(LOGS_DIR, "error")
SUMMARY_FILE = os.path.join(RESULTS_DIR, "summary.txt")
DATA_GENERATOR_SCRIPT_NAME = "data_generator"
PROCESS_TIMEOUT = 10


# --- Enums and Data Structures ---
class BookLocation(Enum):
    BOOKSHELF_NORMAL = "bs"
    BOOKSHELF_HOT = "hbs"
    BORROW_RETURN_OFFICE = "bro"
    APPOINTMENT_OFFICE = "ao"
    READING_ROOM = "rr"
    USER = "user"


class BookCategory(Enum):
    A = "A";
    B = "B";
    C = "C"


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
        self.held_books_b = set()
        self.held_books_c = defaultdict(set)
        self.active_order_isbn = None
        self.active_order_date = None  # Date string when order was made
        self.reading_book_id_today = None  # full_id of book being read today

    def can_borrow_b(self):
        return not self.held_books_b

    def can_borrow_c(self, isbn_to_borrow):
        return not self.held_books_c.get(isbn_to_borrow)

    def can_order_b(self):
        return not self.held_books_b and self.active_order_isbn is None

    def can_order_c(self, isbn_to_order):
        return not self.held_books_c.get(isbn_to_order) and self.active_order_isbn is None

    def can_read_today(self):
        return self.reading_book_id_today is None

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
        self.books = {}  # Maps full_id to BookCopy object
        self.books_by_isbn = defaultdict(list)  # Maps isbn to list of BookCopy objects
        self.users = {}  # Maps student_id to UserState object
        self.current_date_str = ""  # e.g., "[YYYY-MM-DD]"
        self.current_date_obj = None  # datetime.date object
        self.outstanding_orders = defaultdict(deque)  # isbn -> deque of (student_id, order_date_str)
        self.isbns_interacted_last_open_day = set()  # ISBNs successfully borrowed/read in the previous open session
        self.isbns_interacted_current_open_day_user_actions = set()  # ISBNs successfully borrowed/read in the current open session

    def get_or_create_user(self, student_id):
        if student_id not in self.users:
            self.users[student_id] = UserState(student_id)
        return self.users[student_id]

    def check_can_pick(self, student_id, isbn_to_pick):
        """
        Checks if a user CAN pick a book, without changing any GT state.
        Returns: (can_pick_bool, message_str, book_full_id_if_pickable_or_None)
        """
        user = self.get_or_create_user(student_id)  # Getting user state doesn't change it for this check
        book_that_would_be_picked = None

        for book_copy_candidate in self.books_by_isbn.get(isbn_to_pick, []):
            if book_copy_candidate.location == BookLocation.APPOINTMENT_OFFICE and \
                    str(book_copy_candidate.reserved_for_user_id) == str(student_id) and \
                    book_copy_candidate.isbn == isbn_to_pick:
                if book_copy_candidate.reservation_expiry_date and self.current_date_obj > book_copy_candidate.reservation_expiry_date:
                    continue  # Overdue
                book_that_would_be_picked = book_copy_candidate
                break

        if not book_that_would_be_picked:
            return False, f"No book {isbn_to_pick} at AO validly reserved for {student_id}.", None

        category = book_that_would_be_picked.category
        if category == BookCategory.B and not user.can_borrow_b():
            return False, f"User {student_id} would exceed B-type limit by picking {isbn_to_pick}.", None
        if category == BookCategory.C and not user.can_borrow_c(isbn_to_pick):
            return False, f"User {student_id} would exceed C-type limit for ISBN {isbn_to_pick} by picking.", None

        return True, "Pick permissible.", book_that_would_be_picked.full_id

    def setup_books(self, initial_book_data_lines):
        for line in initial_book_data_lines:
            parts = line.split();
            isbn_full = parts[0];
            count = int(parts[1])
            category_char = isbn_full.split('-')[0]
            category = BookCategory(category_char)
            for i in range(1, count + 1):
                full_id = f"{isbn_full}-{i:02d}"
                book_copy = BookCopy(full_id, isbn_full, category)
                self.books[full_id] = book_copy
                self.books_by_isbn[isbn_full].append(book_copy)

    def _perform_open_organization_start(self):
        """Called at the beginning of each OPEN session (even if same day re-open)."""
        print_debug_structured("(GT)",
                               f"Performing _perform_open_organization_start for date {self.current_date_str}. Prev day's hot ISBNs (current session's actions): {self.isbns_interacted_current_open_day_user_actions}")
        self.isbns_interacted_last_open_day = self.isbns_interacted_current_open_day_user_actions.copy()
        self.isbns_interacted_current_open_day_user_actions.clear()
        print_debug_structured("(GT)",
                               f"Updated isbns_interacted_last_open_day: {self.isbns_interacted_last_open_day}. Current day actions cleared.")
        for user_id in self.users:  # Reset daily reading status for all users
            if self.users[user_id].reading_book_id_today:
                print_debug_structured("(GT UserState)",
                                       f"User {user_id} reading status reset from {self.users[user_id].reading_book_id_today}")
            self.users[user_id].reading_book_id_today = None

    def set_date(self, date_str):
        print_debug_structured("(GT)", f"Setting date from '{self.current_date_str}' to '{date_str}'")
        new_date_obj = datetime.datetime.strptime(date_str, "[%Y-%m-%d]").date()
        self.current_date_str = date_str
        self.current_date_obj = new_date_obj
        # Check for overdue books at AO (GT doesn't auto-move them, just for info)
        for book_copy in self.books.values():
            if book_copy.location == BookLocation.APPOINTMENT_OFFICE and \
                    book_copy.reserved_for_user_id and \
                    book_copy.reservation_expiry_date and \
                    self.current_date_obj > book_copy.reservation_expiry_date:
                print_debug_structured("(GT OverdueCheck)",
                                       f"Book {book_copy.full_id} for {book_copy.reserved_for_user_id} (expiry: {book_copy.reservation_expiry_date}) is now overdue on {self.current_date_obj}.")

    def find_available_copy_on_shelf(self, isbn):
        """Finds an available copy of a book with given ISBN on bs or hbs."""
        for book_copy in self.books_by_isbn.get(isbn, []):
            if book_copy.location in [BookLocation.BOOKSHELF_NORMAL, BookLocation.BOOKSHELF_HOT]:
                return book_copy
        return None

    def _move_book(self, book_copy: BookCopy, new_location_enum: BookLocation,
                   new_holder_id=None, reserved_for_user_id=None,
                   reservation_days=5, is_open_organization_context=True):
        old_location_enum = book_copy.location
        old_holder_id = book_copy.holder_id

        print_debug_structured("(GT _move_book Attempt)",
                               f"Book: {book_copy.full_id}, From: {old_location_enum.value} (Holder: {old_holder_id}, Reserved: {book_copy.reserved_for_user_id}), "
                               f"To: {new_location_enum.value} (NewHolder: {new_holder_id}, IntendedReserve: {reserved_for_user_id})")

        # Determine what 'for_user_id' to record for the move itself
        # This should be the 'intended_reserved_for_user_id' if moving TO AO.
        for_user_for_move_record = None
        if new_location_enum == BookLocation.APPOINTMENT_OFFICE and reserved_for_user_id:
            for_user_for_move_record = reserved_for_user_id

        # Record move before state changes that might affect this record
        from_loc_str_for_record = "user" if old_location_enum == BookLocation.USER else old_location_enum.value
        to_loc_str_for_record = "user" if new_location_enum == BookLocation.USER else new_location_enum.value
        book_copy.record_move(self.current_date_str, from_loc_str_for_record, to_loc_str_for_record,
                              for_user_for_move_record)

        # Update user states (removing from old holder, adding to new holder if applicable)
        if old_location_enum == BookLocation.USER and old_holder_id and old_holder_id in self.users:
            self.users[old_holder_id].remove_book(book_copy)
        elif old_location_enum == BookLocation.READING_ROOM and old_holder_id and old_holder_id in self.users:
            if self.users[old_holder_id].reading_book_id_today == book_copy.full_id:
                self.users[old_holder_id].reading_book_id_today = None

        # Set new location and holder for the book copy
        book_copy.location = new_location_enum
        book_copy.holder_id = new_holder_id

        if new_location_enum == BookLocation.USER and new_holder_id and new_holder_id in self.users:
            self.users[new_holder_id].add_book(book_copy)
        elif new_location_enum == BookLocation.READING_ROOM and new_holder_id and new_holder_id in self.users:
            self.users[new_holder_id].reading_book_id_today = book_copy.full_id
            book_copy.holder_id = new_holder_id  # Ensure holder_id is set for reading room context

        # Handle reservation attributes specifically AFTER location/holder are set
        if new_location_enum == BookLocation.APPOINTMENT_OFFICE and reserved_for_user_id:
            book_copy.reserved_for_user_id = reserved_for_user_id
            start_date_for_reservation = self.current_date_obj
            if not is_open_organization_context:
                start_date_for_reservation += datetime.timedelta(days=1)
            book_copy.reservation_expiry_date = start_date_for_reservation + datetime.timedelta(
                days=reservation_days - 1)
        else:
            # If new location is NOT AO, or if it IS AO but no 'reserved_for_user_id' was provided for THIS move
            # (e.g. an admin moving a damaged book to AO, not for a user reservation)
            # then clear any existing reservation.
            book_copy.reserved_for_user_id = None
            book_copy.reservation_expiry_date = None

        print_debug_structured("(GT _move_book Final State)",
                               f"Book: {book_copy.full_id}, Loc: {book_copy.location.value}, Holder: {book_copy.holder_id}, "
                               f"ReservedFor: {book_copy.reserved_for_user_id}, Expiry: {book_copy.reservation_expiry_date}")

    def handle_borrow_check(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        book_to_borrow = self.find_available_copy_on_shelf(isbn)
        if not book_to_borrow: return False, f"No copy of {isbn} on any shelf.", None
        category = book_to_borrow.category  # Use category from actual book type
        if category == BookCategory.A: return False, f"Book {isbn} is Type A, cannot be borrowed.", None
        if category == BookCategory.B and not user.can_borrow_b(): return False, f"User {student_id} already holds a B-type book.", None
        if category == BookCategory.C and not user.can_borrow_c(
            isbn): return False, f"User {student_id} already holds a C-type copy of ISBN {isbn}.", None
        return True, "Borrow permissible.", book_to_borrow.full_id

    def handle_return(self, student_id, book_full_id):
        book_copy = self.books.get(book_full_id)
        if not book_copy or book_copy.holder_id != student_id or book_copy.location != BookLocation.USER:
            return False, f"User {student_id} not holding {book_full_id} or book not with user."
        self._move_book(book_copy, BookLocation.BORROW_RETURN_OFFICE, new_holder_id=None)
        return True, f"Returned {book_full_id} to BRO."

    def handle_read_check(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        book_to_read = self.find_available_copy_on_shelf(isbn)
        if not book_to_read: return False, f"No copy of {isbn} on any shelf for reading.", None
        if not user.can_read_today(): return False, f"User {student_id} already reading ({user.reading_book_id_today}) or has unreturned read book.", None
        return True, "Read permissible.", book_to_read.full_id

    def handle_restore(self, student_id, book_full_id):
        user = self.get_or_create_user(student_id)
        book_copy = self.books.get(book_full_id)
        if not book_copy or book_copy.location != BookLocation.READING_ROOM or book_copy.holder_id != student_id:
            return False, f"Book {book_full_id} not in RR or not associated with {student_id}."
        if user.reading_book_id_today != book_full_id:  # Stricter check
            return False, f"User {student_id} state shows not reading {book_full_id} (currently: {user.reading_book_id_today})."
        self._move_book(book_copy, BookLocation.BORROW_RETURN_OFFICE, new_holder_id=None)
        return True, f"Restored {book_full_id} from RR to BRO."

    def handle_order(self, student_id, isbn):
        user = self.get_or_create_user(student_id)
        book_category = BookCategory(isbn.split('-')[0])
        if book_category == BookCategory.A: return False, f"Book {isbn} (Type A) cannot be ordered."
        if user.active_order_isbn: return False, f"User {student_id} already has active order for {user.active_order_isbn}."
        if book_category == BookCategory.B and not user.can_order_b(): return False, f"User {student_id} holds/ordered B-type, cannot order another B."
        if book_category == BookCategory.C and not user.can_order_c(
            isbn): return False, f"User {student_id} holds/ordered C-type ISBN {isbn}, cannot order it."

        user.active_order_isbn = isbn
        user.active_order_date = self.current_date_str
        self.outstanding_orders[isbn].append((student_id, self.current_date_str))
        print_debug_structured("(GT Order)",
                               f"User {student_id} ordered {isbn}. Active order: {user.active_order_isbn} on {user.active_order_date}. Outstanding for ISBN: {list(self.outstanding_orders[isbn])}")
        return True, f"Ordered {isbn}."

    def handle_pick(self, student_id, isbn_to_pick):
        user = self.get_or_create_user(student_id)
        book_to_give_user = None
        print_debug_structured("(GT handle_pick)",
                               f"User {student_id} trying to pick ISBN {isbn_to_pick} on {self.current_date_str}")
        print_debug_structured("(GT handle_pick PRE-CHECK)",
                               f"State of all books with ISBN {isbn_to_pick} before checking AO:")
        for book_copy_iter in self.books_by_isbn.get(isbn_to_pick, []):
            print_debug_structured("(GT handle_pick PRE-CHECK DETAIL)",
                                   f"Book: {book_copy_iter.full_id}, "
                                   f"Location: {book_copy_iter.location.value}, "
                                   f"ReservedFor: {book_copy_iter.reserved_for_user_id}, "
                                   f"Expiry: {book_copy_iter.reservation_expiry_date}")
        found_candidates_at_ao_details = []  # To store details of books found at AO for this ISBN

        for book_copy_candidate in self.books_by_isbn.get(isbn_to_pick, []):
            candidate_details_for_log = (f"Candidate: {book_copy_candidate.full_id}, "
                                         f"Location: {book_copy_candidate.location.value}, "
                                         f"ReservedFor: {book_copy_candidate.reserved_for_user_id}, "
                                         f"ISBN: {book_copy_candidate.isbn}, "
                                         f"Expiry: {book_copy_candidate.reservation_expiry_date}")
            print_debug_structured("(GT handle_pick loop)", candidate_details_for_log)

            if book_copy_candidate.location == BookLocation.APPOINTMENT_OFFICE:
                found_candidates_at_ao_details.append(candidate_details_for_log)

                # Ensure student_id is compared as string, as it comes from parsed input in harness
            # and reserved_for_user_id is also typically stored/passed as string from student output.
            if book_copy_candidate.location == BookLocation.APPOINTMENT_OFFICE and str(
                    book_copy_candidate.reserved_for_user_id) == str(
                    student_id) and book_copy_candidate.isbn == isbn_to_pick:
                print_debug_structured("(GT handle_pick loop)",
                                       f"Candidate {book_copy_candidate.full_id} matches user ({student_id}) and ISBN ({isbn_to_pick}).")
                if book_copy_candidate.reservation_expiry_date and self.current_date_obj > book_copy_candidate.reservation_expiry_date:
                    print_debug_structured("(GT Pick Check)",
                                           f"Book {book_copy_candidate.full_id} for {student_id} at AO is overdue (Expiry: {book_copy_candidate.reservation_expiry_date}, Current: {self.current_date_obj}). Cannot pick.")
                    continue
                book_to_give_user = book_copy_candidate
                print_debug_structured("(GT handle_pick loop)", f"VALID candidate found: {book_to_give_user.full_id}")
                break

        if not book_to_give_user:
            # Log all candidates found at AO for this ISBN to help debug why none matched
            all_ao_candidates_str = " ; ".join(
                found_candidates_at_ao_details) if found_candidates_at_ao_details else "None"
            print_error(
                f"(GT handle_pick FAIL): No book {isbn_to_pick} at AO validly reserved for {student_id}. Candidates for ISBN {isbn_to_pick} at AO: [ {all_ao_candidates_str} ]")
            return False, f"No book {isbn_to_pick} at AO validly reserved for {student_id}.", None

        category = book_to_give_user.category
        if category == BookCategory.B and not user.can_borrow_b():
            print_debug_structured("(GT handle_pick FAIL)",
                                   f"User {student_id} would exceed B-type limit by picking {isbn_to_pick}.")
            return False, f"User {student_id} would exceed B-type limit by picking {isbn_to_pick}.", None
        if category == BookCategory.C and not user.can_borrow_c(isbn_to_pick):
            print_debug_structured("(GT handle_pick FAIL)",
                                   f"User {student_id} would exceed C-type limit for ISBN {isbn_to_pick} by picking.")
            return False, f"User {student_id} would exceed C-type limit for ISBN {isbn_to_pick} by picking.", None

        self._move_book(book_to_give_user, BookLocation.USER, new_holder_id=student_id,
                        is_open_organization_context=True)
        print_debug_structured("(GT UserState)",
                               f"User {student_id} active order cleared after pick. Was: {user.active_order_isbn} on {user.active_order_date}")
        user.active_order_isbn = None
        user.active_order_date = None
        return True, f"Picked {book_to_give_user.full_id}.", book_to_give_user.full_id

    def handle_query(self, book_full_id):
        book_copy = self.books.get(book_full_id)
        if not book_copy: return False, f"Book {book_full_id} not found in GT."

        expected_trace = []
        print_debug_structured("(GT Query)",
                               f"Generating trace for {book_full_id}. Internal history items: {len(book_copy.movement_history)}")
        for i, trace_item in enumerate(book_copy.movement_history):
            # trace_item could be (date_str, from_loc_val, to_loc_val) OR (date_str, from_loc_val, to_loc_val, for_user_id)
            date_str = trace_item[0]
            # Ensure from_loc_val and to_loc_val are string representations (e.g., enum.value)
            # Assuming they are already stored as strings after the BookCopy.record_move change
            _from = trace_item[1]
            _to = trace_item[2]

            line = f"{i + 1} {date_str} from {_from} to {_to}"
            # Removed: for <student_id> part for query output, based on user feedback.
            # if len(trace_item) == 4:
            #    line += f" for {trace_item[3]}"
            expected_trace.append(line)
            print_debug_structured("(GT Query Gen)", f"Trace line {i + 1}: {line}")

        return True, expected_trace

    def handle_student_organization_move(self, date_str, book_full_id, from_loc_str, to_loc_str,
                                         for_student_id_str=None, is_open_organization_context=True):
        book_copy = self.books.get(book_full_id)
        if not book_copy: return "WA", f"Student tried to move non-existent book {book_full_id}"

        valid_org_loc_values = {loc.value for loc in BookLocation if loc != BookLocation.USER}
        if from_loc_str not in valid_org_loc_values or to_loc_str not in valid_org_loc_values:
            return "WA", f"Invalid location in student org move: {from_loc_str} to {to_loc_str}. Valid: {valid_org_loc_values}"
        if from_loc_str == to_loc_str: return "WA", f"Student org move from and to same location: {from_loc_str}"
        if book_copy.location.value != from_loc_str:
            return "WA", f"Book {book_full_id} is at {book_copy.location.value} (holder: {book_copy.holder_id}), student says it's at {from_loc_str}"

        if book_copy.location == BookLocation.APPOINTMENT_OFFICE and \
                book_copy.reserved_for_user_id and \
                book_copy.reservation_expiry_date and \
                self.current_date_obj <= book_copy.reservation_expiry_date:
            return "WA", f"Book {book_full_id} is reserved for {book_copy.reserved_for_user_id} until EOD {book_copy.reservation_expiry_date} at AO and cannot be moved by organization."

        if to_loc_str == BookLocation.APPOINTMENT_OFFICE.value:
            if not for_student_id_str and from_loc_str != BookLocation.APPOINTMENT_OFFICE.value:  # Moving into AO needs a user
                return "WA", f"Student org move of {book_full_id} to AO from {from_loc_str} must specify a user."
            if for_student_id_str:  # If user specified, check if they have an active order
                target_user_state = self.users.get(for_student_id_str)
                if not target_user_state or target_user_state.active_order_isbn != book_copy.isbn:
                    # Allow if it was already reserved for this user (e.g., student re-confirms existing reservation details)
                    if not (
                            book_copy.location == BookLocation.APPOINTMENT_OFFICE and book_copy.reserved_for_user_id == for_student_id_str):
                        return "WA", f"Student org move to AO for {for_student_id_str} (book {book_copy.isbn}): User has no active order for this ISBN (User order: {target_user_state.active_order_isbn if target_user_state else 'None'})."

        self._move_book(book_copy, BookLocation(to_loc_str),
                        reserved_for_user_id=for_student_id_str if to_loc_str == BookLocation.APPOINTMENT_OFFICE.value else None,
                        is_open_organization_context=is_open_organization_context)
        return "OK", "Move applied to ground truth."

    def verify_organization_rules(self, is_open_org_context):
        context_str = "OPEN org" if is_open_org_context else "CLOSE org"
        print_debug_structured("(GT Verify)", f"Verifying rules after {context_str} on {self.current_date_str}")

        if is_open_org_context:
            for book_copy in self.books.values():
                if book_copy.location == BookLocation.BORROW_RETURN_OFFICE: return "WA", f"After OPEN org, book {book_copy.full_id} in BRO."
                if book_copy.location == BookLocation.READING_ROOM: return "WA", f"After OPEN org, book {book_copy.full_id} in RR (holder: {book_copy.holder_id})."
                if book_copy.location == BookLocation.APPOINTMENT_OFFICE and \
                        book_copy.reserved_for_user_id and \
                        book_copy.reservation_expiry_date and \
                        self.current_date_obj > book_copy.reservation_expiry_date:
                    return "WA", f"After OPEN org, book {book_copy.full_id} at AO is overdue for {book_copy.reserved_for_user_id} (expiry {book_copy.reservation_expiry_date}, current {self.current_date_obj})."

                is_isbn_hot_for_this_org = book_copy.isbn in self.isbns_interacted_last_open_day
                if book_copy.location == BookLocation.BOOKSHELF_HOT and not is_isbn_hot_for_this_org:
                    return "WA", f"After OPEN org, non-hot book {book_copy.full_id} (ISBN {book_copy.isbn}) on HBS. Hot ISBNs from prev day: {self.isbns_interacted_last_open_day}"
                if book_copy.location == BookLocation.BOOKSHELF_NORMAL and is_isbn_hot_for_this_org:
                    return "WA", f"After OPEN org, hot book {book_copy.full_id} (ISBN {book_copy.isbn}) on BS. Hot ISBNs from prev day: {self.isbns_interacted_last_open_day}"

        # REMOVED: Check for books at USER location after org, as this was incorrect.
        # Books at USER location are fine and are not part of organization moves.

        print_debug_structured("(GT Verify)", f"Organization rules satisfied after {context_str}")
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
            print_traceback_info()
            self.log_buffer.append(f"Harness ERROR: Failed to start {self.jar_path}: {e}");
            return False

    def send_input(self, line):
        if not self.process or self.process.poll() is not None:
            self.log_buffer.append("Harness ERROR: Process not running when sending input.");
            return False
        try:
            print_send(line);
            self.log_buffer.append(f"Harness SEND: {line}")
            self.process.stdin.write(line + "\n");
            self.process.stdin.flush();
            return True
        except Exception as e:
            print_error(f"Failed to send input '{line}': {e}");
            print_traceback_info()
            self.log_buffer.append(f"Harness ERROR: Failed to send input '{line}': {e}");
            self.kill();
            return False

    def read_output_line(self):  # Renamed for clarity
        if not self.process or self.process.poll() is not None:
            self.log_buffer.append("Harness ERROR: Process not running when reading output.");
            return None
        try:
            line = self.process.stdout.readline()
            if line:
                line = line.strip()
                print_recv(line);
                self.log_buffer.append(f"Student RECV: {line}")
                return line
            else:  # EOF
                self.log_buffer.append(f"Student RECV: [EOF from stdout.readline()]")
                if self.process.poll() is not None: print_debug_structured("(Proc IO)",
                                                                           f"Process confirmed terminated (exit: {self.process.returncode}) during read.")
                return None
        except Exception as e:
            print_error(f"Failed to read output: {e}");
            print_traceback_info()
            self.log_buffer.append(f"Harness ERROR: Failed to read output: {e}");
            self.kill();
            return None

    def read_expected_lines(self, count):
        lines = []
        for i in range(count):
            line = self.read_output_line()
            if line is None:
                self.log_buffer.append(f"Harness ERROR: Expected {count} lines, got None at line {i + 1}.");
                return None
            lines.append(line)
        return lines

    def get_current_log(self):
        return "\n".join(self.log_buffer)

    def kill(self):
        if self.process and self.process.poll() is None:
            self.log_buffer.append("Harness: Attempting to terminate student process.");
            print_console("Terminating student process...")
            try:
                self.process.terminate();
                self.process.wait(timeout=PROCESS_TIMEOUT / 2)
            except subprocess.TimeoutExpired:
                self.log_buffer.append("Harness: Process did not terminate, killing.");
                print_console("Student process did not terminate gracefully, killing...")
                self.process.kill()
                try:
                    self.process.wait(timeout=PROCESS_TIMEOUT / 2)
                except subprocess.TimeoutExpired:
                    self.log_buffer.append("Harness: Process kill command also timed out.")
            except Exception as e:
                self.log_buffer.append(
                    f"Harness: Exception during process termination/kill: {e}"); print_traceback_info()
        elif self.process:
            self.log_buffer.append(
                f"Harness: Student process already terminated (exit code: {self.process.returncode}).")


# Regex remains the same
ACTION_RESPONSE_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] \[(accept|reject)\] (\S+) (\w+) (\S+)")
QUERY_HEADER_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] (\S+-\d{4}-\d{2}) moving trace: (\d+)")
TRACE_LINE_REGEX = re.compile(
    r"(\d+) \[(\d{4}-\d{2}-\d{2})\] from (\S+) to (\S+)(?: for (\S+))?")  # Kept for potential future use by student
ORG_MOVE_REGEX = re.compile(r"\[(\d{4}-\d{2}-\d{2})\] move (\S+-\d{4}-\d{2}) from (\S+) to (\S+)(?: for (\S+))?")


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
    if len(commands_spec) != len(raw_commands_spec):
        print_warning("(ParseTC)",
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
        if not student_proc.send_input(
            initial_book_count_str): return "RE", student_proc.get_current_log(), "Fail send book count.", sent_inputs_for_replay
        sent_inputs_for_replay.append(initial_book_count_str)
        for book_line in initial_books_spec:
            if not student_proc.send_input(
                book_line): return "RE", student_proc.get_current_log(), f"Fail send book spec: {book_line}", sent_inputs_for_replay
            sent_inputs_for_replay.append(book_line)
        ground_truth.setup_books(initial_books_spec)

        command_queue = deque(commands_spec)  # Main queue from test case file
        pending_today_after_user_action = deque()  # For dynamically generated same-day commands (restore)
        future_command_blocks = []  # Stores (datetime.date_obj, deque_of_USER_ONLY_commands_for_that_date)

        borrowed_books_for_potential_return = []
        ordered_books_for_potential_pick = []
        reading_books_for_potential_restore = []
        pick_attempts_count = defaultdict(int)
        restore_attempts_count = defaultdict(int)

        harness_current_processing_date_str = None
        harness_is_library_open = False
        harness_opened_once_today = False

        loop_counter = 0;
        max_loops = 5000

        while loop_counter < max_loops:
            loop_counter += 1
            print_debug_structured(f"(Loop {loop_counter}) Start",
                                   f"MainQ({len(command_queue)}):'{command_queue[0] if command_queue else '[]'}', "
                                   f"PendingTodayQ({len(pending_today_after_user_action)}):'{pending_today_after_user_action[0] if pending_today_after_user_action else '[]'}', "
                                   f"FutureQ({len(future_command_blocks)}): {[(d.strftime('%Y-%m-%d'), list(q)[:1]) for d, q in future_command_blocks[:1]]}, "
                                   f"HDate:{harness_current_processing_date_str}, LibOpen:{harness_is_library_open}, OpenedOnce:{harness_opened_once_today}")

            next_command_str = None
            current_harness_date_obj = None
            if harness_current_processing_date_str:
                try:
                    current_harness_date_obj = datetime.datetime.strptime(harness_current_processing_date_str,
                                                                          "[%Y-%m-%d]").date()
                except ValueError:
                    return "RE", student_proc.get_current_log(), f"Harness Error: Invalid date string: {harness_current_processing_date_str}", sent_inputs_for_replay

            future_command_blocks.sort(key=lambda x: x[0])

            # --- Command Selection ---
            # Prio 1: Dynamically generated for current open session
            if pending_today_after_user_action:
                cmd_from_pending = pending_today_after_user_action.popleft()
                cmd_date_match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", cmd_from_pending)
                if cmd_date_match and cmd_date_match.group(0) == harness_current_processing_date_str:
                    next_command_str = cmd_from_pending
                else:  # Should not happen if added correctly
                    pending_today_after_user_action.appendleft(cmd_from_pending)
                    print_warning("(Selector)",
                                  f"PendingTodayQ cmd '{cmd_from_pending}' for wrong date/state. Current: {harness_current_processing_date_str}")

            # Prio 2: MainQ commands for current established day (if library is open or about to open)
            if next_command_str is None and current_harness_date_obj:
                if command_queue:
                    main_q_peek_cmd = command_queue[0]
                    main_q_peek_match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", main_q_peek_cmd)
                    if main_q_peek_match and datetime.datetime.strptime(main_q_peek_match.group(0),
                                                                        "[%Y-%m-%d]").date() == current_harness_date_obj:
                        next_command_str = command_queue.popleft()

            # Prio 3: Determine next operational day from MainQ or FutureQ (if Prio 1 & 2 failed)
            if next_command_str is None:
                next_operational_date = None
                source_is_future_block_for_next_op_date_determination = False  # Temp flag for this block

                main_q_next_op_date = None
                if command_queue:
                    main_q_next_op_match = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                    if main_q_next_op_match: main_q_next_op_date = datetime.datetime.strptime(
                        main_q_next_op_match.group(0), "[%Y-%m-%d]").date()

                future_q_next_op_date = future_command_blocks[0][0] if future_command_blocks else None

                if main_q_next_op_date and future_q_next_op_date:
                    if main_q_next_op_date <= future_q_next_op_date:
                        next_operational_date = main_q_next_op_date
                    else:
                        next_operational_date = future_q_next_op_date; source_is_future_block_for_next_op_date_determination = True
                elif main_q_next_op_date:
                    next_operational_date = main_q_next_op_date
                elif future_q_next_op_date:
                    next_operational_date = future_q_next_op_date; source_is_future_block_for_next_op_date_determination = True

                # Auto-close current day if it was open and next operation is for a future day
                if harness_is_library_open and current_harness_date_obj and next_operational_date and next_operational_date > current_harness_date_obj:
                    auto_close_cmd = f"{harness_current_processing_date_str} CLOSE"
                    if not (pending_today_after_user_action and pending_today_after_user_action[
                        0] == auto_close_cmd):  # Avoid duplicate
                        pending_today_after_user_action.appendleft(auto_close_cmd)
                    if pending_today_after_user_action: next_command_str = pending_today_after_user_action.popleft()  # Process this auto-CLOSE now

                elif next_operational_date:

                    if current_harness_date_obj is None or next_operational_date >= current_harness_date_obj:

                        is_mainq_providing_for_next_op_date = (command_queue and

                                                               main_q_next_op_date == next_operational_date)

                        is_futureq_defining_next_op_date_alone = (
                                    source_is_future_block_for_next_op_date_determination and

                                    future_command_blocks and

                                    future_command_blocks[0][0] == next_operational_date and

                                    not is_mainq_providing_for_next_op_date)

                        if is_mainq_providing_for_next_op_date:

                            next_command_str = command_queue.popleft()

                            print_debug_structured("(Selector P3/MainQ)",
                                                   f"Selected '{next_command_str}' from MainQ for date {next_operational_date.strftime('%Y-%m-%d')}.")


                        elif is_futureq_defining_next_op_date_alone:

                            _dt_f_unserviceable, cmds_f_unserviceable = future_command_blocks.pop(0)

                            print_warning("(Selector P3/FutureQ Unserviceable)",

                                          f"Date {next_operational_date.strftime('%Y-%m-%d')} from FutureQ has no corresponding OPEN in MainQ. "

                                          f"Discarding {len(cmds_f_unserviceable)} dynamic user ops: {list(cmds_f_unserviceable)}")


                        else:

                            print_debug_structured("(Selector P3)",
                                                   f"No command selected for next_operational_date {next_operational_date.strftime('%Y-%m-%d')} by primary MainQ/FutureQ paths. "

                                                   f"MainQ date: {main_q_next_op_date}, SourceFuture: {source_is_future_block_for_next_op_date_determination}, "

                                                   f"FutureQ head date: {future_command_blocks[0][0] if future_command_blocks else 'N/A'}.")

                    else:

                        print_error(
                            f"Selector P3: Attempt to go back in time. Current: {current_harness_date_obj}, NextOp: {next_operational_date}.")
                else:

                    # This else corresponds to: (current_harness_date_obj is NOT None AND next_operational_date < current_harness_date_obj)

                    # This means going back in time, which should not happen.

                    print_error(
                        f"Selector P3: Attempt to go back in time. Current: {current_harness_date_obj}, NextOp: {next_operational_date}. This is a bug.")

                    # To prevent infinite loop in this error state, perhaps break or raise. For now, just log.
            if next_command_str is None:  # If still no command selected
                if not command_queue and not future_command_blocks and not pending_today_after_user_action:
                    print_debug_structured("(Loop End)", "All queues empty.")
                    break

                    # If library is open, but no more commands for today from any source, auto-close
                is_no_more_cmd_for_today = not pending_today_after_user_action and \
                                           (not command_queue or \
                                            (command_queue and re.match(r"\[(\d{4}-\d{2}-\d{2})\]",
                                                                        command_queue[0]) and \
                                             datetime.datetime.strptime(
                                                 re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]).group(0),
                                                 "[%Y-%m-%d]").date() > current_harness_date_obj))

                if harness_is_library_open and current_harness_date_obj and is_no_more_cmd_for_today:
                    is_last_day_overall = not command_queue and not future_command_blocks
                    next_op_day_is_future = False
                    if command_queue and datetime.datetime.strptime(
                            re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0]).group(0),
                            "[%Y-%m-%d]").date() > current_harness_date_obj:
                        next_op_day_is_future = True
                    elif future_command_blocks and future_command_blocks[0][0] > current_harness_date_obj:
                        next_op_day_is_future = True

                    if is_last_day_overall or next_op_day_is_future:
                        auto_close_cmd_final = f"{harness_current_processing_date_str} CLOSE"
                        if not (pending_today_after_user_action and pending_today_after_user_action[
                            0] == auto_close_cmd_final):
                            pending_today_after_user_action.appendleft(auto_close_cmd_final)
                            print_debug_structured("(Auto-Op)",
                                                   f"Added '{auto_close_cmd_final}' to pending_today for end-of-day.")

                print_debug_structured("(Loop Control)", "No command selected, continuing loop.")
                continue

                # --- Command Processing ---
            command_str_for_send = next_command_str
            print_debug_structured("(Command Proc)", f"Processing: '{command_str_for_send}'")

            date_match_proc = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_str_for_send)
            if not date_match_proc: return "RE", student_proc.get_current_log(), f"Command missing date: {command_str_for_send}", sent_inputs_for_replay
            date_from_current_cmd_str = date_match_proc.group(0)

            # Date advancement & FutureQ injection
            if harness_current_processing_date_str is None or date_from_current_cmd_str != harness_current_processing_date_str:
                print_debug_structured("(Date Advance)",
                                       f"Advancing from '{harness_current_processing_date_str}' to '{date_from_current_cmd_str}'.")
                if harness_is_library_open:
                    print_warning("(Date Advance)",
                                  f"Advancing to {date_from_current_cmd_str} but library was open for {harness_current_processing_date_str}.")

                harness_current_processing_date_str = date_from_current_cmd_str
                current_harness_date_obj = datetime.datetime.strptime(harness_current_processing_date_str,
                                                                      "[%Y-%m-%d]").date()  # Update this immediately
                harness_is_library_open = False
                harness_opened_once_today = False
                ground_truth.set_date(harness_current_processing_date_str)

                # Inject FutureQ commands for this new day into pending_today_after_user_action
                # They will be processed after the OPEN (if any from MainQ) for this day.
                if future_command_blocks and future_command_blocks[0][0] == current_harness_date_obj:
                    _f_date, f_cmds_for_new_day = future_command_blocks.pop(0)
                    if f_cmds_for_new_day:
                        print_debug_structured("(FutureQ Inject)",
                                               f"Injecting {len(f_cmds_for_new_day)} FutureQ user ops for {current_harness_date_obj.strftime('%Y-%m-%d')} into pending_today: {list(f_cmds_for_new_day)}")
                        # These are user actions, add to pending_today to be processed after potential OPEN
                        # Add them in order, but they'll be popped from left by Prio 1 selection.
                        # So, if f_cmds was [c1, c2], pending_today becomes [c1, c2] (if empty initially)
                        pending_today_after_user_action.extend(f_cmds_for_new_day)

            is_open_command = command_str_for_send.endswith(" OPEN")  # More robust check
            is_close_command = command_str_for_send.endswith(" CLOSE")

            if is_open_command:
                print_debug_structured("(Command Proc OPEN)",
                                       f"Harness state before OPEN: LibOpen:{harness_is_library_open}, OpenedOnce:{harness_opened_once_today}")
                # CRITICAL FIX: Call _perform_open_organization_start EVERY time an OPEN is processed.
                ground_truth._perform_open_organization_start()
                if not harness_opened_once_today:
                    harness_opened_once_today = True
                else:
                    print_debug_structured("(Command Proc OPEN)", "Library re-opening on same logical day.")
                harness_is_library_open = True
            elif is_close_command:
                harness_is_library_open = False
                pending_today_after_user_action.clear()  # Clear same-day dynamic ops

            if not student_proc.send_input(
                command_str_for_send): return "RE", student_proc.get_current_log(), f"Failed to send command: {command_str_for_send}", sent_inputs_for_replay
            sent_inputs_for_replay.append(command_str_for_send)
            log_content_on_error = student_proc.get_current_log()

            # Handle student response for OPEN/CLOSE (organization moves)
            if is_open_command:
                output_k_open = student_proc.read_output_line()
                if output_k_open is None: return "RE", student_proc.get_current_log(), "Timeout K for OPEN", sent_inputs_for_replay
                try:
                    num_moves_o = int(output_k_open); assert num_moves_o >= 0
                except:
                    return "WA", student_proc.get_current_log(), f"OPEN: Bad K: '{output_k_open}'", sent_inputs_for_replay
                if num_moves_o > 0:
                    move_lines_o = student_proc.read_expected_lines(num_moves_o)
                    if move_lines_o is None: return "RE", student_proc.get_current_log(), "Timeout OPEN moves", sent_inputs_for_replay
                    for move_str_o in move_lines_o:
                        match_o = ORG_MOVE_REGEX.match(move_str_o)
                        if not match_o: return "WA", student_proc.get_current_log(), f"OPEN: Bad move: '{move_str_o}'", sent_inputs_for_replay
                        _d_o, b_id_o, _f_o, _t_o, for_s_o = match_o.groups()
                        if _d_o != harness_current_processing_date_str.strip(
                            "[]"): return "WA", student_proc.get_current_log(), f"OPEN move: Date mismatch", sent_inputs_for_replay
                        stat_o, rea_o = ground_truth.handle_student_organization_move(
                            harness_current_processing_date_str, b_id_o, _f_o, _t_o, for_s_o, True)
                        if stat_o == "WA": return "WA", student_proc.get_current_log(), f"OPEN org move: {rea_o}", sent_inputs_for_replay
                log_content_on_error = student_proc.get_current_log()
                stat_rules_o, rea_rules_o = ground_truth.verify_organization_rules(is_open_org_context=True)
                if stat_rules_o == "WA": return "WA", student_proc.get_current_log(), f"OPEN: Rule violation: {rea_rules_o}", sent_inputs_for_replay

                # Dynamic 'picked' generation for orders that might be fulfillable now (after student's OPEN org)
                # These are for the CURRENT day.
                # Dynamic 'picked' generation for orders that might be fulfillable now (after student's OPEN org)
                new_ordered_list_after_open_pick = []  # To rebuild the list of orders still pending
                temp_pick_cmds_for_pending_today = deque()  # To collect pick commands for the current day

                print_debug_structured("(DynGen Pick/Open)",
                                       f"Checking {len(ordered_books_for_potential_pick)} potential orders for dynamic pick on current day {harness_current_processing_date_str}.")

                for s_id_pk_o, isbn_pk_o, o_date_pk_o in ordered_books_for_potential_pick:
                    key_pk_o = (s_id_pk_o, isbn_pk_o, o_date_pk_o)
                    user_pk_o = ground_truth.users.get(s_id_pk_o)  # User should exist if they placed an order

                    # Check if the order is still active for this user and pick attempts are not exceeded
                    if user_pk_o and user_pk_o.active_order_isbn == isbn_pk_o and pick_attempts_count[key_pk_o] < 2:
                        # Use the new READ-ONLY check_can_pick method
                        gt_can_pick_o_check, _, _ = ground_truth.check_can_pick(s_id_pk_o, isbn_pk_o)

                        print_debug_structured("(DynGen Pick/Open Check)",
                                               f"User {s_id_pk_o} order for {isbn_pk_o} (date {o_date_pk_o}): GT check_can_pick result: {gt_can_pick_o_check}. Attempts: {pick_attempts_count[key_pk_o]}")

                        if gt_can_pick_o_check:
                            pick_cmd_str = f"{harness_current_processing_date_str} {s_id_pk_o} picked {isbn_pk_o}"
                            temp_pick_cmds_for_pending_today.append(pick_cmd_str)
                            print_debug_structured("(DynGen Pick/Open Add)",
                                                   f"Added dynamic pick to temp_pick_cmds: {pick_cmd_str}")
                            # Do NOT remove from ordered_books_for_potential_pick here.
                            # It will be implicitly handled when the actual 'picked' command response is processed
                            # by clearing user.active_order_isbn, which will make it not schedulable again.
                            # Alternatively, we could add it to new_ordered_list_after_open_pick and rely on pick_attempts_count,
                            # but if it's scheduled, it should ideally not be rescheduled until this attempt resolves.
                            # For now, if scheduled, we don't add it back to new_ordered_list_after_open_pick.
                        else:
                            new_ordered_list_after_open_pick.append(key_pk_o)  # Still pending, could not pick now

                    elif user_pk_o and user_pk_o.active_order_isbn == isbn_pk_o:  # Order active, but max pick attempts reached
                        print_debug_structured("(DynGen Pick/Open Skip)",
                                               f"User {s_id_pk_o} order for {isbn_pk_o}: Max pick attempts ({pick_attempts_count[key_pk_o]}) reached or other non-pickable reason. Keeping order.")
                        new_ordered_list_after_open_pick.append(key_pk_o)

                    # If user_pk_o.active_order_isbn is no longer this isbn (e.g. they ordered something else, or it was picked via TC command),
                    # it will not be added to new_ordered_list_after_open_pick and thus naturally drops off.

                ordered_books_for_potential_pick = new_ordered_list_after_open_pick  # Update the master list

                if temp_pick_cmds_for_pending_today:
                    # Add to the left of pending_today so they are processed before other commands for today from MainQ
                    # that were originally after the OPEN.
                    pending_today_after_user_action.extendleft(reversed(list(temp_pick_cmds_for_pending_today)))
                    print_debug_structured("(DynGen Pick/Open Queue)",
                                           f"Extended pending_today_after_user_action with {len(temp_pick_cmds_for_pending_today)} pick commands: {list(pending_today_after_user_action)}")

            elif is_close_command:
                output_k_close = student_proc.read_output_line()
                if output_k_close is None: return "RE", student_proc.get_current_log(), "Timeout K for CLOSE", sent_inputs_for_replay
                try:
                    num_moves_c = int(output_k_close); assert num_moves_c >= 0
                except:
                    return "WA", student_proc.get_current_log(), f"CLOSE: Bad K: '{output_k_close}'", sent_inputs_for_replay
                if num_moves_c > 0:
                    move_lines_c = student_proc.read_expected_lines(num_moves_c)
                    if move_lines_c is None: return "RE", student_proc.get_current_log(), "Timeout CLOSE moves", sent_inputs_for_replay
                    for move_str_c in move_lines_c:
                        match_c = ORG_MOVE_REGEX.match(move_str_c)
                        if not match_c: return "WA", student_proc.get_current_log(), f"CLOSE: Bad move: '{move_str_c}'", sent_inputs_for_replay
                        _d_c, b_id_c, _f_c, _t_c, for_s_c = match_c.groups()
                        if _d_c != harness_current_processing_date_str.strip(
                            "[]"): return "WA", student_proc.get_current_log(), f"CLOSE move: Date mismatch", sent_inputs_for_replay
                        stat_c, rea_c = ground_truth.handle_student_organization_move(
                            harness_current_processing_date_str, b_id_c, _f_c, _t_c, for_s_c, False)
                        if stat_c == "WA": return "WA", student_proc.get_current_log(), f"CLOSE org move: {rea_c}", sent_inputs_for_replay
                log_content_on_error = student_proc.get_current_log()
                stat_rules_c, rea_rules_c = ground_truth.verify_organization_rules(is_open_org_context=False)
                if stat_rules_c == "WA": return "WA", student_proc.get_current_log(), f"CLOSE: Rule violation: {rea_rules_c}", sent_inputs_for_replay

                # Dynamic 'picked' generation for FUTURE days
                target_dt_f_pk_base = ground_truth.current_date_obj + datetime.timedelta(days=1)
                min_next_overall_dt_f_pk = None
                if command_queue:
                    match_q_f_pk = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                    if match_q_f_pk: min_next_overall_dt_f_pk = datetime.datetime.strptime(match_q_f_pk.group(0),
                                                                                           "[%Y-%m-%d]").date()
                if future_command_blocks:
                    if future_command_blocks:
                        next_f_dt_f_pk = future_command_blocks[0][0]
                        if min_next_overall_dt_f_pk is None or next_f_dt_f_pk < min_next_overall_dt_f_pk: min_next_overall_dt_f_pk = next_f_dt_f_pk

                final_target_dt_f_pk = target_dt_f_pk_base
                if min_next_overall_dt_f_pk and min_next_overall_dt_f_pk > final_target_dt_f_pk: final_target_dt_f_pk = min_next_overall_dt_f_pk
                final_target_str_f_pk = final_target_dt_f_pk.strftime("[%Y-%m-%d]")

                # Dynamic 'picked' generation for FUTURE days (after CLOSE org)
                # Target date (final_target_dt_f_pk, final_target_str_f_pk) should have been calculated before this block.

                future_pick_cmds_for_fcb = deque()  # Collects pick commands for the determined future date
                new_ordered_list_after_close_pick = []  # To rebuild the list of orders still pending

                print_debug_structured("(DynGen Pick/Close)",
                                       f"Checking {len(ordered_books_for_potential_pick)} potential orders for future dynamic pick on {final_target_str_f_pk}.")

                for s_id_f_pk, isbn_f_pk, o_date_f_pk in ordered_books_for_potential_pick:
                    key_f_pk = (s_id_f_pk, isbn_f_pk, o_date_f_pk)
                    user_f_pk = ground_truth.users.get(s_id_f_pk)

                    if user_f_pk and user_f_pk.active_order_isbn == isbn_f_pk and pick_attempts_count[key_f_pk] < 2:
                        # For future picks, checking pickability is based on current GT state推断未来.
                        # We check if a book for this order is at AO and its reservation would be valid on final_target_dt_f_pk.
                        # This does NOT call ground_truth.check_can_pick() directly because check_can_pick uses GT's current_date_obj.
                        # We need a check specific to a future date.
                        can_pick_on_future_date_check = False
                        for b_future_check in ground_truth.books_by_isbn.get(isbn_f_pk, []):
                            if b_future_check.location == BookLocation.APPOINTMENT_OFFICE and \
                                    str(b_future_check.reserved_for_user_id) == str(s_id_f_pk) and \
                                    b_future_check.isbn == isbn_f_pk and \
                                    b_future_check.reservation_expiry_date and \
                                    final_target_dt_f_pk <= b_future_check.reservation_expiry_date:  # Check if reservation is still valid on the target future date
                                can_pick_on_future_date_check = True
                                break

                        print_debug_structured("(DynGen Pick/Close Check)",
                                               f"User {s_id_f_pk} order for {isbn_f_pk} (date {o_date_f_pk}) for future target {final_target_str_f_pk}: "
                                               f"Simplified future pickability check result: {can_pick_on_future_date_check}. Attempts: {pick_attempts_count[key_f_pk]}")

                        if can_pick_on_future_date_check:
                            future_pick_cmds_for_fcb.append(f"{final_target_str_f_pk} {s_id_f_pk} picked {isbn_f_pk}")
                            print_debug_structured("(DynGen Pick/Close Add)",
                                                   f"Added future dynamic pick to temp_fcb_cmds: {future_pick_cmds_for_fcb[-1]}")
                        else:
                            new_ordered_list_after_close_pick.append(key_f_pk)

                    elif user_f_pk and user_f_pk.active_order_isbn == isbn_f_pk:  # Order active, but max pick attempts reached
                        print_debug_structured("(DynGen Pick/Close Skip)",
                                               f"User {s_id_f_pk} order for {isbn_f_pk}: Max pick attempts ({pick_attempts_count[key_f_pk]}) reached or other non-pickable reason. Keeping order for future.")
                        new_ordered_list_after_close_pick.append(key_f_pk)

                ordered_books_for_potential_pick = new_ordered_list_after_close_pick  # Update the master list

                if future_pick_cmds_for_fcb:  # These are user-only ops, NO OPEN command added by harness
                    existing_fcb_idx_f_pk = next(
                        (i for i, (d, _) in enumerate(future_command_blocks) if d == final_target_dt_f_pk), -1)
                    if existing_fcb_idx_f_pk != -1:
                        # Append to existing deque for that future date
                        print_debug_structured("(DynGen Pick/Close Queue)",
                                               f"Appending {len(future_pick_cmds_for_fcb)} future pick commands to existing FutureQ block for {final_target_dt_f_pk.strftime('%Y-%m-%d')}.")
                        future_command_blocks[existing_fcb_idx_f_pk][1].extend(future_pick_cmds_for_fcb)
                    else:
                        # Create a new entry in future_command_blocks
                        print_debug_structured("(DynGen Pick/Close Queue)",
                                               f"Creating new FutureQ block for {final_target_dt_f_pk.strftime('%Y-%m-%d')} with {len(future_pick_cmds_for_fcb)} pick commands.")
                        future_command_blocks.append((final_target_dt_f_pk, future_pick_cmds_for_fcb))

            else:  # User actions
                # ... (This part remains largely the same as your provided code, with hlog removed)
                # ... (Ensure GT state updates (like marking hot ISBNs) are correct) ...
                parts = command_str_for_send.split();
                _d_cmd, student_id, action_verb, book_identifier_from_input = parts[0], parts[1], parts[2], parts[3]
                student_output_line = student_proc.read_output_line()
                if student_output_line is None: return "RE", student_proc.get_current_log(), f"Timeout resp for {action_verb}: {command_str_for_send}", sent_inputs_for_replay
                log_content_on_error = student_proc.get_current_log()
                action_match = ACTION_RESPONSE_REGEX.match(student_output_line);
                query_match_header = None
                if action_verb == "queried": query_match_header = QUERY_HEADER_REGEX.match(student_output_line)

                if action_verb == "queried":
                    if not query_match_header: return "WA", student_proc.get_current_log(), f"queried: Bad resp hdr: '{student_output_line}' for {book_identifier_from_input}", sent_inputs_for_replay
                    s_date_q, s_book_id_q_from_output, s_num_traces_str_q = query_match_header.groups()
                    if s_date_q != harness_current_processing_date_str.strip(
                            "[]") or s_book_id_q_from_output != book_identifier_from_input:
                        return "WA", student_proc.get_current_log(), f"queried: Resp hdr date/ID mismatch.", sent_inputs_for_replay
                    try:
                        s_num_traces_q = int(s_num_traces_str_q); assert s_num_traces_q >= 0
                    except:
                        return "WA", student_proc.get_current_log(), f"queried: Bad num_traces: '{s_num_traces_str_q}'", sent_inputs_for_replay
                    student_trace_lines_q = student_proc.read_expected_lines(
                        s_num_traces_q) if s_num_traces_q > 0 else []
                    if s_num_traces_q > 0 and student_trace_lines_q is None: return "RE", student_proc.get_current_log(), "Timeout query traces", sent_inputs_for_replay
                    gt_success_q, gt_trace_q_list_or_error_msg = ground_truth.handle_query(book_identifier_from_input)
                    if not gt_success_q: return "RE", student_proc.get_current_log(), f"GT Error query {book_identifier_from_input}: {gt_trace_q_list_or_error_msg}", sent_inputs_for_replay
                    if len(student_trace_lines_q) != len(gt_trace_q_list_or_error_msg):
                        return "WA", student_proc.get_current_log() + f"\nGT TRACE:\n" + "\n".join(
                            gt_trace_q_list_or_error_msg), f"queried: Trace count mismatch. S:{len(student_trace_lines_q)} GT:{len(gt_trace_q_list_or_error_msg)}", sent_inputs_for_replay
                    for i, (s_line, gt_line) in enumerate(zip(student_trace_lines_q, gt_trace_q_list_or_error_msg)):
                        if s_line.strip() != gt_line.strip(): return "WA", student_proc.get_current_log(), f"queried: Trace line {i + 1} mismatch.\nS:'{s_line}'\nGT:'{gt_line}'", sent_inputs_for_replay
                else:  # Non-queried actions
                    if not action_match: return "WA", student_proc.get_current_log(), f"{action_verb}: Bad resp format: '{student_output_line}'", sent_inputs_for_replay
                    s_date, s_status, s_student_id, s_action, s_book_details_from_output = action_match.groups()
                    if s_date != harness_current_processing_date_str.strip(
                            "[]") or s_student_id != student_id or s_action != action_verb:
                        return "WA", student_proc.get_current_log(), f"{action_verb}: Mismatch in resp date/ID/action.", sent_inputs_for_replay

                    if action_verb == "borrowed":
                        gt_ok_b, gt_msg_b, gt_bid_b = ground_truth.handle_borrow_check(student_id,
                                                                                       book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok_b: return "WA", student_proc.get_current_log(), f"borrowed: S:accept, GT:reject. GT: {gt_msg_b}", sent_inputs_for_replay
                            if not re.fullmatch(f"{re.escape(book_identifier_from_input)}-\\d{{2}}",
                                                s_book_details_from_output): return "WA", student_proc.get_current_log(), f"borrowed [accept]: Bad full_id: '{s_book_details_from_output}'", sent_inputs_for_replay
                            s_book_obj_b = ground_truth.books.get(s_book_details_from_output)
                            if not s_book_obj_b or s_book_obj_b.isbn != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"borrowed [accept]: Book '{s_book_details_from_output}' invalid.", sent_inputs_for_replay
                            # Re-check with specific copy for GT rules
                            user_b_check = ground_truth.get_or_create_user(student_id)
                            can_b_final = True;
                            reason_b_final = ""
                            if s_book_obj_b.location not in [BookLocation.BOOKSHELF_NORMAL, BookLocation.BOOKSHELF_HOT]:
                                can_b_final = False; reason_b_final = "Not on shelf"
                            elif s_book_obj_b.category == BookCategory.A:
                                can_b_final = False; reason_b_final = "Type A"
                            elif s_book_obj_b.category == BookCategory.B and not user_b_check.can_borrow_b():
                                can_b_final = False; reason_b_final = "Holds B"
                            elif s_book_obj_b.category == BookCategory.C and not user_b_check.can_borrow_c(
                                s_book_obj_b.isbn):
                                can_b_final = False; reason_b_final = "Holds C ISBN"
                            if not can_b_final: return "WA", student_proc.get_current_log(), f"borrowed [accept]: Invalid choice {s_book_details_from_output}. GT: {reason_b_final}", sent_inputs_for_replay

                            ground_truth._move_book(s_book_obj_b, BookLocation.USER, new_holder_id=student_id)
                            ground_truth.isbns_interacted_current_open_day_user_actions.add(book_identifier_from_input)
                            borrowed_books_for_potential_return.append(
                                (student_id, s_book_details_from_output, harness_current_processing_date_str))
                        elif s_status == "reject":  # Student rejects
                            if gt_ok_b: pass  # Allowed
                            if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"borrowed [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "read":
                        gt_ok_r, gt_msg_r, gt_bid_r = ground_truth.handle_read_check(student_id,
                                                                                     book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok_r: return "WA", student_proc.get_current_log(), f"read: S:accept, GT:reject. GT: {gt_msg_r}", sent_inputs_for_replay
                            if not re.fullmatch(f"{re.escape(book_identifier_from_input)}-\\d{{2}}",
                                                s_book_details_from_output): return "WA", student_proc.get_current_log(), f"read [accept]: Bad full_id: '{s_book_details_from_output}'", sent_inputs_for_replay
                            s_book_obj_r = ground_truth.books.get(s_book_details_from_output)
                            if not s_book_obj_r or s_book_obj_r.isbn != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"read [accept]: Book '{s_book_details_from_output}' invalid.", sent_inputs_for_replay
                            user_r_check = ground_truth.get_or_create_user(student_id)
                            can_r_final = True;
                            reason_r_final = ""
                            if s_book_obj_r.location not in [BookLocation.BOOKSHELF_NORMAL, BookLocation.BOOKSHELF_HOT]:
                                can_r_final = False; reason_r_final = "Not on shelf"
                            elif not user_r_check.can_read_today():
                                can_r_final = False; reason_r_final = "Already reading"
                            if not can_r_final: return "WA", student_proc.get_current_log(), f"read [accept]: Invalid choice {s_book_details_from_output}. GT: {reason_r_final}", sent_inputs_for_replay

                            ground_truth._move_book(s_book_obj_r, BookLocation.READING_ROOM, new_holder_id=student_id)
                            ground_truth.isbns_interacted_current_open_day_user_actions.add(book_identifier_from_input)
                            reading_books_for_potential_restore.append(
                                (student_id, s_book_details_from_output, harness_current_processing_date_str))
                            restore_attempts_count[
                                (student_id, s_book_details_from_output, harness_current_processing_date_str)] = 0
                        elif s_status == "reject":
                            if gt_ok_r: pass
                            if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"read [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "ordered":
                        gt_ok_o, gt_msg_o = ground_truth.handle_order(student_id, book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok_o: return "WA", student_proc.get_current_log(), f"ordered: S:accept, GT:reject. GT: {gt_msg_o}", sent_inputs_for_replay
                            if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"ordered [accept]: ISBN mismatch.", sent_inputs_for_replay
                            o_key = (student_id, book_identifier_from_input, harness_current_processing_date_str)
                            if o_key not in ordered_books_for_potential_pick: ordered_books_for_potential_pick.append(
                                o_key)
                            pick_attempts_count[o_key] = 0
                        elif s_status == "reject":
                            if gt_ok_o:  # Student rejected a valid order, GT needs to rollback its state change
                                user_o_rb = ground_truth.users.get(student_id)
                                if user_o_rb and user_o_rb.active_order_isbn == book_identifier_from_input and user_o_rb.active_order_date == harness_current_processing_date_str:
                                    user_o_rb.active_order_isbn = None;
                                    user_o_rb.active_order_date = None
                                    if ground_truth.outstanding_orders[book_identifier_from_input] and \
                                            ground_truth.outstanding_orders[book_identifier_from_input][-1] == (
                                    student_id, harness_current_processing_date_str):
                                        ground_truth.outstanding_orders[book_identifier_from_input].pop()
                                        if not ground_truth.outstanding_orders[book_identifier_from_input]: del \
                                        ground_truth.outstanding_orders[book_identifier_from_input]
                            if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"ordered [reject]: ISBN mismatch.", sent_inputs_for_replay

                    elif action_verb == "returned":  # From dynamic gen
                        gt_ok_ret, gt_msg_ret = ground_truth.handle_return(student_id, book_identifier_from_input)
                        if not gt_ok_ret: return "RE", student_proc.get_current_log(), f"Harness Bug: GT rejected dynamic return: {gt_msg_ret}", sent_inputs_for_replay
                        if s_status != "accept": return "WA", student_proc.get_current_log(), f"returned: Student rejected valid return.", sent_inputs_for_replay
                        if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"returned [accept]: Book full_id mismatch.", sent_inputs_for_replay

                    elif action_verb == "restored":  # From dynamic gen
                        gt_ok_res, gt_msg_res = ground_truth.handle_restore(student_id, book_identifier_from_input)
                        if not gt_ok_res: return "RE", student_proc.get_current_log(), f"Harness Bug: GT rejected dynamic restore: {gt_msg_res}", sent_inputs_for_replay
                        if s_status != "accept": return "WA", student_proc.get_current_log(), f"restored: Student rejected valid restore.", sent_inputs_for_replay
                        if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"restored [accept]: Book full_id mismatch.", sent_inputs_for_replay

                    elif action_verb == "picked":  # From dynamic gen
                        key_pk_dyn = next((k for k in pick_attempts_count if
                                           k[0] == student_id and k[1] == book_identifier_from_input), None)
                        if key_pk_dyn:
                            pick_attempts_count[key_pk_dyn] += 1
                        else:
                            pick_attempts_count[
                                (student_id, book_identifier_from_input, "UNKNOWN_ORDER_DATE_FOR_PICK")] += 1

                        gt_ok_p, gt_msg_p, gt_bid_p = ground_truth.handle_pick(student_id, book_identifier_from_input)
                        if s_status == "accept":
                            if not gt_ok_p: return "WA", student_proc.get_current_log(), f"picked: S:accept, GT:reject. GT: {gt_msg_p}", sent_inputs_for_replay
                            if s_book_details_from_output != gt_bid_p: return "WA", student_proc.get_current_log(), f"picked [accept]: Picked '{s_book_details_from_output}', GT expected '{gt_bid_p}'.", sent_inputs_for_replay
                            borrowed_books_for_potential_return.append(
                                (student_id, gt_bid_p, harness_current_processing_date_str))
                            # Remove from ordered_books list
                            key_o_rem_p = None
                            for k_o_p in ordered_books_for_potential_pick:
                                if k_o_p[0] == student_id and k_o_p[
                                    1] == book_identifier_from_input: key_o_rem_p = k_o_p; break
                            if key_o_rem_p: ordered_books_for_potential_pick.remove(key_o_rem_p)
                        elif s_status == "reject":
                            if gt_ok_p:  # Student rejected a pick GT allowed. GT state was changed. Need to attempt rollback.
                                if gt_bid_p:  # Book GT thought was picked
                                    book_to_rb_p = ground_truth.books.get(gt_bid_p)
                                    user_to_rb_p = ground_truth.users.get(student_id)
                                    if book_to_rb_p and user_to_rb_p and book_to_rb_p.location == BookLocation.USER and book_to_rb_p.holder_id == student_id:
                                        # Simplified rollback: move back to AO, assume it was reserved.
                                        # This doesn't perfectly restore expiry date, but it's an attempt.
                                        # Also, user's active_order_isbn was cleared by GT.handle_pick. Try to restore it.
                                        # This rollback is complex and might not be perfect.
                                        # The key is student can reject.
                                        original_order_date_for_rollback = "UNKNOWN"  # We need this to fully rollback UserState
                                        for s_rb, i_rb, d_rb in ordered_books_for_potential_pick:  # check current list, though it might have been removed
                                            if s_rb == student_id and i_rb == book_identifier_from_input: original_order_date_for_rollback = d_rb; break

                                        print_debug_structured("(GT Rollback PICK)",
                                                               f"Attempting to rollback GT state for rejected pick by {student_id} of {gt_bid_p}.")
                                        ground_truth._move_book(book_to_rb_p, BookLocation.APPOINTMENT_OFFICE,
                                                                reserved_for_user_id=student_id,
                                                                is_open_organization_context=True)
                                        if user_to_rb_p.active_order_isbn is None and original_order_date_for_rollback != "UNKNOWN":
                                            user_to_rb_p.active_order_isbn = book_identifier_from_input
                                            user_to_rb_p.active_order_date = original_order_date_for_rollback
                            if s_book_details_from_output != book_identifier_from_input: return "WA", student_proc.get_current_log(), f"picked [reject]: ISBN mismatch.", sent_inputs_for_replay
                    else:
                        return "RE", student_proc.get_current_log(), f"Harness Error: Unhandled action verb '{action_verb}'.", sent_inputs_for_replay

                # --- Dynamic 'returned' and 'restored' generation (after user action) ---
                # 'returned' generation
                if borrowed_books_for_potential_return and random.random() < 0.2:
                    selected_return_info = None;
                    pop_idx_ret = -1
                    # ... (logic to select a book from borrowed_books_for_potential_return) ...
                    # For brevity, assume s_id_ret_dyn, book_id_ret_dyn are selected

                    # Simplified: find one to return
                    for idx, (s_id_r, b_id_r, d_r) in enumerate(borrowed_books_for_potential_return):
                        if ground_truth.books[b_id_r].location == BookLocation.USER and ground_truth.books[
                            b_id_r].holder_id == s_id_r:
                            selected_return_info = (s_id_r, b_id_r, d_r);
                            pop_idx_ret = idx;
                            break

                    if selected_return_info:
                        s_id_ret_dyn, book_id_ret_dyn, _ = borrowed_books_for_potential_return.pop(pop_idx_ret)

                        target_dt_ret_dyn = ground_truth.current_date_obj
                        is_after_today_close_dyn_ret = (
                                    harness_current_processing_date_str == ground_truth.current_date_str and not harness_is_library_open)
                        if is_after_today_close_dyn_ret:
                            target_dt_ret_dyn = ground_truth.current_date_obj + datetime.timedelta(days=1)
                        elif harness_is_library_open and random.random() < 0.3:
                            target_dt_ret_dyn = ground_truth.current_date_obj + datetime.timedelta(days=1)

                        min_next_overall_dt_dyn_ret = None  # Calculate based on MainQ and FutureQ
                        # ... (logic for min_next_overall_dt_dyn_ret) ...
                        if command_queue:
                            m = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", command_queue[0])
                            if m: min_next_overall_dt_dyn_ret = datetime.datetime.strptime(m.group(0),
                                                                                           "[%Y-%m-%d]").date()
                        if future_command_blocks and future_command_blocks[0][0] and (
                                min_next_overall_dt_dyn_ret is None or future_command_blocks[0][
                            0] < min_next_overall_dt_dyn_ret):
                            min_next_overall_dt_dyn_ret = future_command_blocks[0][0]

                        if min_next_overall_dt_dyn_ret and min_next_overall_dt_dyn_ret > target_dt_ret_dyn: target_dt_ret_dyn = min_next_overall_dt_dyn_ret

                        final_target_str_ret_dyn = target_dt_ret_dyn.strftime("[%Y-%m-%d]")
                        return_cmd_dyn = f"{final_target_str_ret_dyn} {s_id_ret_dyn} returned {book_id_ret_dyn}"

                        if final_target_str_ret_dyn == harness_current_processing_date_str:  # Schedule for current day processing
                            pending_today_after_user_action.append(return_cmd_dyn)
                        else:  # Schedule for future day
                            fcb_idx_ret = next(
                                (i for i, (d, _) in enumerate(future_command_blocks) if d == target_dt_ret_dyn), -1)
                            if fcb_idx_ret != -1:
                                future_command_blocks[fcb_idx_ret][1].append(return_cmd_dyn)
                            else:
                                future_command_blocks.append((target_dt_ret_dyn, deque([return_cmd_dyn])))

                # 'restored' generation (only for current day, if library open)
                if reading_books_for_potential_restore and random.random() < 0.3:
                    # ... (logic to select a book and user for restore) ...
                    # For brevity, assume s_id_res_dyn, book_id_res_dyn are selected
                    selected_restore_info = None;
                    pop_idx_res = -1
                    for idx_res, (s_id_rs, b_id_rs, d_rs) in enumerate(reading_books_for_potential_restore):
                        if d_rs == harness_current_processing_date_str and restore_attempts_count[
                            (s_id_rs, b_id_rs, d_rs)] < 1:
                            if ground_truth.books[b_id_rs].location == BookLocation.READING_ROOM and ground_truth.books[
                                b_id_rs].holder_id == s_id_rs:
                                selected_restore_info = (s_id_rs, b_id_rs, d_rs);
                                pop_idx_res = idx_res;
                                break

                    if selected_restore_info and harness_is_library_open:
                        s_id_res_dyn, book_id_res_dyn, date_res_dyn = reading_books_for_potential_restore.pop(
                            pop_idx_res)
                        restore_cmd_dyn = f"{harness_current_processing_date_str} {s_id_res_dyn} restored {book_id_res_dyn}"
                        pending_today_after_user_action.append(restore_cmd_dyn)
                        restore_attempts_count[(s_id_res_dyn, book_id_res_dyn, date_res_dyn)] += 1

        if loop_counter >= max_loops:
            return "RE", student_proc.get_current_log(), f"Max loops ({max_loops}) exceeded.", sent_inputs_for_replay
        return "AC", student_proc.get_current_log(), "All commands processed.", sent_inputs_for_replay
    except Exception as e_outer:
        print_critical(f"Outer Exception in run_single_test_case: {e_outer}");
        print_traceback_info()
        # ... (rest of exception logging)
        return "RE", student_proc.get_current_log() + f"\nOuter Exception: {e_outer}\n{traceback.format_exc()}", f"Harness critical error: {e_outer}", sent_inputs_for_replay
    finally:
        if student_proc: student_proc.kill()


# main() function remains the same as your provided version
def main():
    use_generator_choice = input(
        f"Run '{DATA_GENERATOR_SCRIPT_NAME}.py' to generate new test cases? (y/n): ").strip().lower()
    if use_generator_choice == 'y':
        try:
            print_console(f"Running {DATA_GENERATOR_SCRIPT_NAME}.py...")
            data_gen_module = importlib.import_module(DATA_GENERATOR_SCRIPT_NAME.replace('.py', ''))
            if hasattr(data_gen_module, 'main') and callable(data_gen_module.main):
                if hasattr(data_gen_module,
                           'TEST_CASES_DIR'):
                    setattr(data_gen_module, 'TEST_CASES_DIR', TEST_CASES_DIR)
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
    for d in [TESTJAR_DIR, TEST_CASES_DIR, RESULTS_DIR, LOGS_DIR, CORRECT_LOGS_DIR, ERROR_LOGS_DIR, REPLAY_INPUTS_DIR]:
        os.makedirs(d, exist_ok=True)

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
                print_traceback_info()
                log_content = log_content_tc_exc

            print_status_line(f"{verdict} (Reason: {reason if reason else 'OK'})")
            timestamp_log = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_base_name = "_".join(
                filter(None, [jar_file_name.replace('.jar', ''), tc_name.replace('.txt', ''), timestamp_log]))
            safe_reason_log = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in str(reason)[:50])

            student_log_path = os.path.join(CORRECT_LOGS_DIR if verdict == "AC" else ERROR_LOGS_DIR,
                                            f"{log_file_base_name}_{verdict}{'_' + safe_reason_log if verdict != 'AC' and safe_reason_log else ''}.log")

            replay_input_path = os.path.join(REPLAY_INPUTS_DIR,
                                             f"{log_file_base_name}_{verdict}{'_' + safe_reason_log if verdict != 'AC' and safe_reason_log else ''}_replay.txt")
            if verdict == "AC":
                ac_count += 1
            elif verdict == "WA":
                wa_count += 1
            else:
                re_count += 1
            try:
                with open(student_log_path, 'w', encoding='utf-8') as log_f_stud:
                    log_f_stud.write(f"JAR: {jar_file_name}\nTest Case: {tc_name}\nVerdict: {verdict}\n")
                    if reason: log_f_stud.write(f"Reason: {reason}\n")
                    log_f_stud.write("-" * 20 + " Interaction Log (Harness <-> Student) " + "-" * 20 + "\n");
                    log_f_stud.write(log_content if log_content else "Interaction log content unavailable.")
            except Exception as e_log_write_stud:
                print_error(f"writing student-facing log file {student_log_path}: {e_log_write_stud}")

            if recorded_inputs:  # Always save replay if inputs were recorded, even if path is empty
                try:
                    with open(replay_input_path, 'w', encoding='utf-8') as replay_f:
                        for line_rpl in recorded_inputs: replay_f.write(line_rpl + "\n")
                except Exception as e_replay_write:
                    print_error(f"writing replay input file {replay_input_path}: {e_replay_write}")

        summary_data.append({"jar": jar_file_name, "AC": ac_count, "WA": wa_count, "RE": re_count})

    with open(SUMMARY_FILE, 'w', encoding='utf-8') as sf:
        sf.write("--- Test Summary ---\n")
        for item in summary_data: sf.write(
            f"JAR: {item['jar']}\n  AC: {item['AC']}\n  WA: {item['WA']}\n  RE: {item['RE']}\n\n")
    print_status_line("\n")
    print_console(f"Summary written to {SUMMARY_FILE}")
    print_console(f"Student-facing logs stored in {LOGS_DIR}")
    print_console(f"Replay input files stored in {REPLAY_INPUTS_DIR}")


if __name__ == "__main__":
    main()