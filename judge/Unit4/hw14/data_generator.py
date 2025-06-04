import random
import datetime
import os
import shutil

# --- Configuration (Adjusted for larger data scope and HW14) ---
TEST_CASES_DIR = "test_cases"  # Changed directory name
MIN_BOOK_TYPES = 5
MAX_BOOK_TYPES = 30
MIN_COPIES_PER_ISBN = 2
MAX_COPIES_PER_ISBN = 15
MIN_DAYS_TO_SIMULATE = 15
MAX_DAYS_TO_SIMULATE = 30
MIN_STUDENT_ID = 23370001
MAX_STUDENT_ID = 23370019  # 19 students for variety
MAX_ACTIONS_PER_DAY = 12

BOOK_CATEGORIES = ['A', 'B', 'C']


# --- Helper Functions ---
def generate_isbn(category):
    return f"{category}-{random.randint(0, 9999):04d}"


def generate_student_id():
    return str(random.randint(MIN_STUDENT_ID, MAX_STUDENT_ID))


def get_next_date_str(current_date_str=None):
    if current_date_str:
        current_date = datetime.datetime.strptime(current_date_str, "[%Y-%m-%d]").date()
        next_date = current_date + datetime.timedelta(days=random.randint(1, 2))
    else:
        start_year = 2025
        start_month = random.randint(1, 12)
        if start_month in [1, 3, 5, 7, 8, 10, 12]:
            max_day = 31
        elif start_month == 2:
            max_day = 28  # No leap year consideration for simplicity
        else:
            max_day = 30
        start_day = random.randint(1, max_day)
        next_date = datetime.date(start_year, start_month, start_day)
    return next_date.strftime("[%Y-%m-%d]")


class SimplifiedLibraryState:
    def __init__(self):
        self.books_by_isbn = {}  # isbn -> details
        self.users = {}  # student_id -> user_data
        self.available_isbns = []  # All ISBNs existing in library
        self.all_book_full_ids = []  # All specific book copies

        # HW14 additions
        self.isbns_interacted_last_open_day = set()  # ISBNs borrowed/read in the PREVIOUS open period
        self.isbns_interacted_current_open_day = set()  # ISBNs borrowed/read in the CURRENT open period

    def add_book_type(self, isbn, category, num_copies):
        # HW14: Books start on normal bookshelf (bs)
        self.books_by_isbn[isbn] = {
            "category": category,
            "total_copies": num_copies,
            "available_on_shelf_bs": num_copies,  # Initially all on normal shelf
            "available_on_shelf_hbs": 0,  # Initially hot shelf is empty
            "copies_details": [
                {"id": f"{isbn}-{i:02d}", "status": "shelf_bs", "holder": None,
                 "reserved_for": None, "isbn_val": isbn, "category_val": category}
                for i in range(1, num_copies + 1)]
        }
        self.available_isbns.append(isbn)
        self.all_book_full_ids.extend([f"{isbn}-{i:02d}" for i in range(1, num_copies + 1)])

    def _ensure_user_data_structure(self, student_id):
        user_entry = self.users.setdefault(student_id, {
            "active_order_isbn": None,
            "held_b_count": 0,
            "held_c_isbns": set(),
            "held_specific_books": set(),
            "reading_book_id_today": None  # HW14: Tracks if user is currently reading a book today
        })
        if "reading_book_id_today" not in user_entry:  # ensure backward compatibility if old state used
            user_entry["reading_book_id_today"] = None
        if not isinstance(user_entry.get("held_specific_books"), set):
            user_entry["held_specific_books"] = set()
        return user_entry

    def get_random_isbn(self, category_filter=None, must_have_shelf_copies=False):
        eligible_isbns = list(self.available_isbns)
        if category_filter:
            eligible_isbns = [isbn for isbn in eligible_isbns if
                              self.books_by_isbn[isbn]["category"] in category_filter]
        if must_have_shelf_copies:
            eligible_isbns = [isbn for isbn in eligible_isbns if
                              self.books_by_isbn.get(isbn, {}).get("available_on_shelf_bs", 0) > 0 or
                              self.books_by_isbn.get(isbn, {}).get("available_on_shelf_hbs", 0) > 0]
        return random.choice(eligible_isbns) if eligible_isbns else None

    def get_random_full_id_for_query(self):
        return random.choice(self.all_book_full_ids) if self.all_book_full_ids else None

    def try_borrow(self, student_id, isbn):
        user_data = self._ensure_user_data_structure(student_id)
        book_info = self.books_by_isbn.get(isbn)

        if not book_info or (
                book_info["available_on_shelf_bs"] == 0 and book_info["available_on_shelf_hbs"] == 0): return None
        if book_info["category"] == 'A': return None  # A cannot be borrowed
        if book_info["category"] == 'B' and user_data["held_b_count"] > 0: return None
        if book_info["category"] == 'C' and isbn in user_data["held_c_isbns"]: return None

        borrowed_copy_id = None
        # Try borrowing from normal shelf first, then hot shelf
        shelf_types_to_try = ["shelf_bs", "shelf_hbs"]
        for shelf_type in shelf_types_to_try:
            if (shelf_type == "shelf_bs" and book_info["available_on_shelf_bs"] > 0) or \
                    (shelf_type == "shelf_hbs" and book_info["available_on_shelf_hbs"] > 0):
                for copy in book_info["copies_details"]:
                    if copy["status"] == shelf_type:
                        copy["status"] = "user"
                        copy["holder"] = student_id
                        borrowed_copy_id = copy["id"]
                        user_data["held_specific_books"].add(borrowed_copy_id)
                        if shelf_type == "shelf_bs":
                            book_info["available_on_shelf_bs"] -= 1
                        else:
                            book_info["available_on_shelf_hbs"] -= 1
                        break  # Found a copy
            if borrowed_copy_id: break  # Found a copy from one of the shelf types

        if borrowed_copy_id:
            if book_info["category"] == 'B': user_data["held_b_count"] += 1
            if book_info["category"] == 'C': user_data["held_c_isbns"].add(isbn)
            self.isbns_interacted_current_open_day.add(isbn)  # HW14: Mark as interacted
            return borrowed_copy_id
        return None

    def try_read(self, student_id, isbn):  # HW14: New method
        user_data = self._ensure_user_data_structure(student_id)
        book_info = self.books_by_isbn.get(isbn)

        if not book_info or (
                book_info["available_on_shelf_bs"] == 0 and book_info["available_on_shelf_hbs"] == 0): return None
        if user_data["reading_book_id_today"] is not None: return None  # Already reading a book today

        # A-type books can be read
        read_copy_id = None
        shelf_types_to_try = ["shelf_bs", "shelf_hbs"]
        for shelf_type in shelf_types_to_try:
            if (shelf_type == "shelf_bs" and book_info["available_on_shelf_bs"] > 0) or \
                    (shelf_type == "shelf_hbs" and book_info["available_on_shelf_hbs"] > 0):
                for copy in book_info["copies_details"]:
                    if copy["status"] == shelf_type:
                        copy["status"] = "rr"  # Moved to reading room
                        # copy["holder"] = student_id # Reading room holds it, user is associated
                        read_copy_id = copy["id"]
                        if shelf_type == "shelf_bs":
                            book_info["available_on_shelf_bs"] -= 1
                        else:
                            book_info["available_on_shelf_hbs"] -= 1
                        break
            if read_copy_id: break

        if read_copy_id:
            user_data["reading_book_id_today"] = read_copy_id  # Mark user as reading this book
            self.isbns_interacted_current_open_day.add(isbn)  # HW14: Mark as interacted
            return read_copy_id
        return None

    def try_order(self, student_id, isbn):
        user_data = self._ensure_user_data_structure(student_id)
        book_info = self.books_by_isbn.get(isbn)
        if not book_info or book_info["category"] == 'A': return False  # A cannot be ordered
        if user_data["active_order_isbn"] is not None: return False
        if book_info["category"] == 'B' and user_data["held_b_count"] > 0: return False
        if book_info["category"] == 'C' and isbn in user_data["held_c_isbns"]: return False
        user_data["active_order_isbn"] = isbn
        return True

    def simulate_organization_moves_for_state_tracking_only(self):
        # This is called right after "OPEN"
        # Step 1: Update hot ISBNs list from previous day's interactions
        self.isbns_interacted_last_open_day = self.isbns_interacted_current_open_day.copy()
        self.isbns_interacted_current_open_day.clear()

        # Step 2: Reset daily user states (e.g., reading status)
        for user_id in self.users:
            self.users[user_id]["reading_book_id_today"] = None

        # Step 3: Clear BRO and RR. Move books to appropriate shelves (bs/hbs)
        # Also, clear overdue AO books (simplified: just move them back to shelves)
        for isbn_val, isbn_data in self.books_by_isbn.items():
            is_hot_isbn = isbn_val in self.isbns_interacted_last_open_day
            target_shelf_status = "shelf_hbs" if is_hot_isbn else "shelf_bs"
            target_shelf_count_key = "available_on_shelf_hbs" if is_hot_isbn else "available_on_shelf_bs"

            for copy_detail in isbn_data["copies_details"]:
                if copy_detail["status"] in ["bro", "rr"]:  # Books from BRO and RR
                    copy_detail["status"] = target_shelf_status
                    copy_detail["holder"] = None
                    copy_detail["reserved_for"] = None
                    isbn_data[target_shelf_count_key] += 1
                # Simplified: Assume AO books not picked up in 5 days become non-reserved and are moved
                # This generator doesn't track dates for AO, so this is a rough approximation
                # of "预约处不应该有逾期的书"
                elif copy_detail["status"] == "ao":
                    # A more complex simulation would check reservation expiry.
                    # For simplicity, if it's still in AO at organization, we *could* move it back.
                    # However, the problem implies AO books remain unless picked or expired.
                    # The "逾期" part is hard to simulate perfectly without date tracking for each reservation.
                    # We'll rely on the student's implementation to handle AO expiry.
                    # This part focuses on moving books from BRO/RR and fulfilling new orders.
                    pass

        # Step 4: Fulfill pending orders from available shelf books
        # Shuffle student order to give some fairness if books are scarce
        shuffled_student_ids = list(self.users.keys())
        random.shuffle(shuffled_student_ids)
        fulfilled_orders_this_org = set()

        for student_id in shuffled_student_ids:
            user_data = self.users.get(student_id)
            if user_data and user_data.get("active_order_isbn") and student_id not in fulfilled_orders_this_org:
                ordered_isbn = user_data["active_order_isbn"]
                book_info = self.books_by_isbn.get(ordered_isbn)

                if not book_info: continue

                # Check if user can still receive this book (B/C limits)
                can_receive_ordered_book = True
                if book_info["category"] == 'B' and user_data.get("held_b_count", 0) > 0:
                    can_receive_ordered_book = False
                if book_info["category"] == 'C' and ordered_isbn in user_data.get("held_c_isbns", set()):
                    can_receive_ordered_book = False

                if not can_receive_ordered_book:
                    continue  # User cannot receive it now, order remains pending

                # Try to find a copy on bs or hbs
                found_copy_for_order = False
                shelf_types_to_try_order = ["shelf_bs", "shelf_hbs"]  # Order doesn't matter much here
                for shelf_type_order in shelf_types_to_try_order:
                    if (shelf_type_order == "shelf_bs" and book_info["available_on_shelf_bs"] > 0) or \
                            (shelf_type_order == "shelf_hbs" and book_info["available_on_shelf_hbs"] > 0):
                        for copy_detail in book_info["copies_details"]:
                            if copy_detail["status"] == shelf_type_order:
                                copy_detail["status"] = "ao"
                                copy_detail["reserved_for"] = student_id
                                if shelf_type_order == "shelf_bs":
                                    book_info["available_on_shelf_bs"] -= 1
                                else:
                                    book_info["available_on_shelf_hbs"] -= 1
                                fulfilled_orders_this_org.add(student_id)
                                found_copy_for_order = True
                                break  # Copy found for this order
                    if found_copy_for_order: break  # Order fulfilled

        # Step 5: Ensure books are on correct shelf types (bs vs hbs)
        # "热门书架不应有非热门书籍，普通书架不应有热门书籍"
        for isbn_val, isbn_data in self.books_by_isbn.items():
            is_hot_isbn = isbn_val in self.isbns_interacted_last_open_day

            # Copies on normal shelf (bs) that SHOULD be on hot shelf (hbs)
            if is_hot_isbn:
                indices_to_move = []
                for i, copy_detail in enumerate(isbn_data["copies_details"]):
                    if copy_detail["status"] == "shelf_bs":
                        indices_to_move.append(i)
                for i in indices_to_move:
                    isbn_data["copies_details"][i]["status"] = "shelf_hbs"
                    isbn_data["available_on_shelf_bs"] -= 1
                    isbn_data["available_on_shelf_hbs"] += 1

            # Copies on hot shelf (hbs) that SHOULD be on normal shelf (bs)
            else:  # not a hot_isbn
                indices_to_move = []
                for i, copy_detail in enumerate(isbn_data["copies_details"]):
                    if copy_detail["status"] == "shelf_hbs":
                        indices_to_move.append(i)
                for i in indices_to_move:
                    isbn_data["copies_details"][i]["status"] = "shelf_bs"
                    isbn_data["available_on_shelf_hbs"] -= 1
                    isbn_data["available_on_shelf_bs"] += 1


def generate_one_test_case_data():
    commands = []
    state = SimplifiedLibraryState()  # HW14 state
    num_book_types = random.randint(MIN_BOOK_TYPES, MAX_BOOK_TYPES)
    commands.append(str(num_book_types))
    generated_isbns_this_case = set()

    for _ in range(num_book_types):
        while True:
            category = random.choice(BOOK_CATEGORIES)
            isbn = generate_isbn(category)
            if isbn not in generated_isbns_this_case:
                generated_isbns_this_case.add(isbn)
                break
        num_copies = random.randint(MIN_COPIES_PER_ISBN, MAX_COPIES_PER_ISBN)
        commands.append(f"{isbn} {num_copies}")
        state.add_book_type(isbn, category, num_copies)

    if not state.available_isbns:  # Ensure at least one book type
        category = random.choice(BOOK_CATEGORIES)
        isbn = generate_isbn(category)
        num_copies = 1
        commands.append(f"{isbn} {num_copies}")
        state.add_book_type(isbn, category, num_copies)

    current_date = None
    num_days = random.randint(MIN_DAYS_TO_SIMULATE, MAX_DAYS_TO_SIMULATE)

    for day_idx in range(num_days):
        current_date = get_next_date_str(current_date)
        commands.append(f"{current_date} OPEN")
        # Simulate organization based on previous day's interactions and rules
        state.simulate_organization_moves_for_state_tracking_only()

        num_actions_today = random.randint(0, MAX_ACTIONS_PER_DAY)
        for _ in range(num_actions_today):
            # HW14: Add "read" action. Adjust weights as needed.
            # Queried is less frequent. Borrow/Order/Read are main interactions.
            action_type = random.choices(
                ["borrowed", "ordered", "read", "queried"],
                weights=[0.30, 0.30, 0.30, 0.10], k=1
            )[0]
            student_id = generate_student_id()
            state._ensure_user_data_structure(student_id)  # Ensure user exists for tracking
            command_str_generated = None

            if action_type == "borrowed" and state.available_isbns:
                # Borrow B or C books
                target_isbn = state.get_random_isbn(category_filter=['B', 'C'], must_have_shelf_copies=True)
                if target_isbn:
                    borrowed_copy_full_id = state.try_borrow(student_id, target_isbn)
                    if borrowed_copy_full_id:
                        command_str_generated = f"{current_date} {student_id} borrowed {target_isbn}"
                        # The checker will determine the actual full_id, generator doesn't output it for borrow
            elif action_type == "ordered" and state.available_isbns:
                # Order B or C books
                target_isbn = state.get_random_isbn(category_filter=['B', 'C'])
                if target_isbn:
                    if state.try_order(student_id, target_isbn):
                        command_str_generated = f"{current_date} {student_id} ordered {target_isbn}"
            elif action_type == "read" and state.available_isbns:  # HW14
                # Read any type of book A, B, C
                target_isbn = state.get_random_isbn(must_have_shelf_copies=True)
                if target_isbn:
                    read_copy_full_id = state.try_read(student_id, target_isbn)
                    if read_copy_full_id:
                        command_str_generated = f"{current_date} {student_id} read {target_isbn}"
                        # Checker determines actual full_id
            elif action_type == "queried" and state.all_book_full_ids:
                target_full_id = state.get_random_full_id_for_query()
                if target_full_id:
                    command_str_generated = f"{current_date} {student_id} queried {target_full_id}"

            if command_str_generated:
                commands.append(command_str_generated)
        commands.append(f"{current_date} CLOSE")

    # Construct final list: N, then N book_specs, then commands
    final_commands = [commands[0]]  # N
    num_book_types_val = int(commands[0])
    final_commands.extend(commands[1: 1 + num_book_types_val])  # Book specs
    final_commands.extend(commands[1 + num_book_types_val:])  # Actual commands
    return final_commands


def main():
    num_test_cases_to_generate = int(input("Enter the number of test case files to generate: "))
    if os.path.exists(TEST_CASES_DIR):
        print(f"'{TEST_CASES_DIR}' directory already exists. Clearing its contents.")
        for filename in os.listdir(TEST_CASES_DIR):
            file_path = os.path.join(TEST_CASES_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    os.makedirs(TEST_CASES_DIR, exist_ok=True)

    for i in range(num_test_cases_to_generate):
        test_case_data = generate_one_test_case_data()
        file_path = os.path.join(TEST_CASES_DIR, f"generated_case{i + 1:03d}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            for line in test_case_data:
                f.write(line + "\n")
        print(f"Generated: {file_path}")
    print(f"\nSuccessfully generated {num_test_cases_to_generate} test case files in '{TEST_CASES_DIR}'.")


if __name__ == "__main__":
    main()