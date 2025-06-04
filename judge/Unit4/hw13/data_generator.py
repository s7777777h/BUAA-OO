import random
import datetime
import os
import shutil

# --- Configuration (Adjusted for larger data scope) ---
TEST_CASES_DIR = "test_cases"
MIN_BOOK_TYPES = 8  # Increased min significantly
MAX_BOOK_TYPES = 20  # Increased significantly
MIN_COPIES_PER_ISBN = 2  # Min 2 copies for more interaction
MAX_COPIES_PER_ISBN = 10  # Max 10 as per problem spec
MIN_DAYS_TO_SIMULATE = 15  # Increased min significantly
MAX_DAYS_TO_SIMULATE = 30  # Increased significantly
MIN_STUDENT_ID = 23370001
MAX_STUDENT_ID = 23370019  # 20 students
MAX_ACTIONS_PER_DAY = 12  # Increased significantly

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
            max_day = 28
        else:
            max_day = 30
        start_day = random.randint(1, max_day)
        next_date = datetime.date(start_year, start_month, start_day)
    return next_date.strftime("[%Y-%m-%d]")


class SimplifiedLibraryState:
    def __init__(self):
        self.books_by_isbn = {}
        self.users = {}  # student_id -> {"active_order_isbn": None/isbn, "held_b_count": 0, "held_c_isbns": set(), "held_specific_books": set()}
        self.available_isbns = []
        self.all_book_full_ids = []

    def add_book_type(self, isbn, category, num_copies):
        self.books_by_isbn[isbn] = {
            "category": category, "total_copies": num_copies, "available_on_shelf": num_copies,
            "copies_details": [
                {"id": f"{isbn}-{i:02d}", "status": "shelf", "holder": None, "reserved_for": None, "isbn_val": isbn,
                 "category_val": category}
                for i in range(1, num_copies + 1)]
        }
        self.available_isbns.append(isbn)
        self.all_book_full_ids.extend([f"{isbn}-{i:02d}" for i in range(1, num_copies + 1)])

    def get_random_isbn(self, category_filter=None, must_have_shelf_copies=False):
        eligible_isbns = list(self.available_isbns)  # Work on a copy
        if category_filter:
            eligible_isbns = [isbn for isbn in eligible_isbns if
                              self.books_by_isbn[isbn]["category"] in category_filter]
        if must_have_shelf_copies:
            eligible_isbns = [isbn for isbn in eligible_isbns if
                              self.books_by_isbn.get(isbn, {}).get("available_on_shelf", 0) > 0]
        return random.choice(eligible_isbns) if eligible_isbns else None

    def get_random_full_id_for_query(self):
        return random.choice(self.all_book_full_ids) if self.all_book_full_ids else None

    def _ensure_user_data_structure(self, student_id):
        # Ensures the user entry and specifically 'held_specific_books' as a set exists
        user_entry = self.users.setdefault(student_id, {
            "active_order_isbn": None, "held_b_count": 0, "held_c_isbns": set(), "held_specific_books": set()
        })
        if not isinstance(user_entry.get("held_specific_books"), set):
            user_entry["held_specific_books"] = set()
        return user_entry

    def try_borrow(self, student_id, isbn):
        user_data = self._ensure_user_data_structure(student_id)
        book_info = self.books_by_isbn.get(isbn)

        if not book_info or book_info["available_on_shelf"] == 0: return None
        if book_info["category"] == 'A': return None
        if book_info["category"] == 'B' and user_data["held_b_count"] > 0: return None
        if book_info["category"] == 'C' and isbn in user_data["held_c_isbns"]: return None

        book_info["available_on_shelf"] -= 1
        borrowed_copy_id = None
        for copy in book_info["copies_details"]:
            if copy["status"] == "shelf":
                copy["status"] = "user";
                copy["holder"] = student_id
                borrowed_copy_id = copy["id"]
                user_data["held_specific_books"].add(borrowed_copy_id)
                break
        if borrowed_copy_id:
            if book_info["category"] == 'B': user_data["held_b_count"] += 1
            if book_info["category"] == 'C': user_data["held_c_isbns"].add(isbn)
            return borrowed_copy_id
        else:  # Should not happen if available_on_shelf was > 0, but as a fallback:
            book_info["available_on_shelf"] += 1  # Revert count if no copy found (though logic error if so)
            return None

    def try_order(self, student_id, isbn):
        user_data = self._ensure_user_data_structure(student_id)
        book_info = self.books_by_isbn.get(isbn)
        if not book_info or book_info["category"] == 'A': return False
        if user_data["active_order_isbn"] is not None: return False
        if book_info["category"] == 'B' and user_data["held_b_count"] > 0: return False
        if book_info["category"] == 'C' and isbn in user_data["held_c_isbns"]: return False
        user_data["active_order_isbn"] = isbn
        return True

    # try_return and try_pick are no longer directly used to generate commands for student input,
    # but can be kept if they help internal state tracking for other decisions, or removed.
    # For now, I'll keep them minimal as they are not primary drivers of student input.
    def _try_return_internal_state_update(self, student_id, book_full_id):  # For internal tracking if needed
        user_data = self.users.get(student_id)
        if not user_data or book_full_id not in user_data.get("held_specific_books", set()): return False
        isbn_prefix = '-'.join(book_full_id.split('-')[:2])
        book_info = self.books_by_isbn.get(isbn_prefix)
        if not book_info: return False
        for copy in book_info["copies_details"]:
            if copy["id"] == book_full_id and copy["status"] == "user" and copy["holder"] == student_id:
                copy["status"] = "bro";
                copy["holder"] = None  # Goes to BRO
                user_data["held_specific_books"].discard(book_full_id)
                if book_info["category"] == 'B': user_data["held_b_count"] = max(0, user_data["held_b_count"] - 1)
                if book_info["category"] == 'C': user_data["held_c_isbns"].discard(isbn_prefix)
                return True
        return False

    def _try_pick_internal_state_update(self, student_id, isbn_to_pick):  # For internal tracking
        user_data = self.users.get(student_id)
        if not user_data or user_data["active_order_isbn"] != isbn_to_pick: return None
        book_info = self.books_by_isbn.get(isbn_to_pick)
        if not book_info: return None
        if book_info["category"] == 'B' and user_data["held_b_count"] > 0: return None
        if book_info["category"] == 'C' and isbn_to_pick in user_data["held_c_isbns"]: return None
        picked_copy_id = None
        for copy in book_info["copies_details"]:
            if copy["isbn_val"] == isbn_to_pick and copy["status"] == "ao" and copy["reserved_for"] == student_id:
                copy["status"] = "user";
                copy["holder"] = student_id;
                copy["reserved_for"] = None
                picked_copy_id = copy["id"]
                user_data.setdefault("held_specific_books", set()).add(picked_copy_id)  # Ensure it's a set
                break
        if picked_copy_id:
            user_data["active_order_isbn"] = None
            if book_info["category"] == 'B': user_data["held_b_count"] += 1
            if book_info["category"] == 'C': user_data["held_c_isbns"].add(isbn_to_pick)
            return picked_copy_id
        return None

    def simulate_organization_moves_for_state_tracking_only(self):
        for isbn_data in self.books_by_isbn.values():
            for copy_detail in isbn_data["copies_details"]:
                if copy_detail["status"] == "bro":
                    copy_detail["status"] = "shelf";
                    isbn_data["available_on_shelf"] += 1
        users_with_fulfilled_orders_this_org = set()
        shuffled_student_ids = list(self.users.keys());
        random.shuffle(shuffled_student_ids)
        for student_id in shuffled_student_ids:
            user_data = self.users.get(student_id)
            if user_data and user_data.get(
                    "active_order_isbn") and student_id not in users_with_fulfilled_orders_this_org:
                isbn_ordered = user_data["active_order_isbn"];
                book_info = self.books_by_isbn.get(isbn_ordered)
                if book_info and book_info["available_on_shelf"] > 0:
                    can_eventually_hold = True
                    if book_info["category"] == 'B' and user_data.get("held_b_count",
                                                                      0) > 0: can_eventually_hold = False
                    if book_info["category"] == 'C' and isbn_ordered in user_data.get("held_c_isbns",
                                                                                      set()): can_eventually_hold = False
                    if can_eventually_hold:
                        for copy_detail in book_info["copies_details"]:
                            if copy_detail["status"] == "shelf":
                                copy_detail["status"] = "ao";
                                copy_detail["reserved_for"] = student_id
                                book_info["available_on_shelf"] -= 1
                                users_with_fulfilled_orders_this_org.add(student_id);
                                break


def generate_one_test_case_data():
    commands = []
    state = SimplifiedLibraryState()
    num_book_types = random.randint(MIN_BOOK_TYPES, MAX_BOOK_TYPES)
    commands.append(str(num_book_types))
    generated_isbns_this_case = set()
    for _ in range(num_book_types):
        while True:
            category = random.choice(BOOK_CATEGORIES);
            isbn = generate_isbn(category)
            if isbn not in generated_isbns_this_case: generated_isbns_this_case.add(isbn); break
        num_copies = random.randint(MIN_COPIES_PER_ISBN, MAX_COPIES_PER_ISBN)
        commands.append(f"{isbn} {num_copies}")
        state.add_book_type(isbn, category, num_copies)
    if not state.available_isbns:
        category = random.choice(BOOK_CATEGORIES);
        isbn = generate_isbn(category);
        num_copies = 1
        commands.append(f"{isbn} {num_copies}");
        state.add_book_type(isbn, category, num_copies)

    current_date = None
    num_days = random.randint(MIN_DAYS_TO_SIMULATE, MAX_DAYS_TO_SIMULATE)
    for day_idx in range(num_days):
        current_date = get_next_date_str(current_date)
        commands.append(f"{current_date} OPEN")
        state.simulate_organization_moves_for_state_tracking_only()
        num_actions_today = random.randint(0, MAX_ACTIONS_PER_DAY)
        for _ in range(num_actions_today):
            action_type = random.choices(
                ["borrowed", "ordered", "queried"], weights=[0.4, 0.4, 0.2], k=1  # Increased borrow/order probability
            )[0]
            student_id = generate_student_id()
            command_str_generated = None
            if action_type == "borrowed" and state.available_isbns:
                target_isbn = state.get_random_isbn(category_filter=['B', 'C'], must_have_shelf_copies=True)
                if target_isbn:
                    if state.try_borrow(student_id, target_isbn):  # try_borrow now returns full_id or None
                        command_str_generated = f"{current_date} {student_id} borrowed {target_isbn}"
            elif action_type == "ordered" and state.available_isbns:
                target_isbn = state.get_random_isbn(category_filter=['B', 'C'])
                if target_isbn:
                    if state.try_order(student_id, target_isbn):
                        command_str_generated = f"{current_date} {student_id} ordered {target_isbn}"
            elif action_type == "queried" and state.all_book_full_ids:
                target_full_id = state.get_random_full_id_for_query()
                if target_full_id:
                    command_str_generated = f"{current_date} {student_id} queried {target_full_id}"
            if command_str_generated: commands.append(command_str_generated)
        commands.append(f"{current_date} CLOSE")

    # Construct final list: N, then N book_specs, then commands
    final_commands = [commands[0]]
    num_book_types_val = int(commands[0])
    final_commands.extend(commands[1: 1 + num_book_types_val])
    final_commands.extend(commands[1 + num_book_types_val:])
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
        file_path = os.path.join(TEST_CASES_DIR, f"generated_case_{i + 1:03d}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            for line_idx, line in enumerate(test_case_data):
                f.write(line + "\n")
        print(f"Generated: {file_path}")
    print(f"\nSuccessfully generated {num_test_cases_to_generate} test case files in '{TEST_CASES_DIR}'.")


if __name__ == "__main__":
    main()