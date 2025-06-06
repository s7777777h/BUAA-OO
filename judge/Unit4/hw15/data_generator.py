import random
import datetime
import os
import shutil

# --- 配置 (为第15次作业调整) ---
TEST_CASES_DIR = "test_cases"  # 恢复原目录名
MIN_BOOK_TYPES = 8
MAX_BOOK_TYPES = 25
MIN_COPIES_PER_ISBN = 3
MAX_COPIES_PER_ISBN = 35
MIN_DAYS_TO_SIMULATE = 20
MAX_DAYS_TO_SIMULATE = 300
MIN_STUDENT_ID = 23370001
MAX_STUDENT_ID = 23370019
MAX_ACTIONS_PER_DAY = 25

BOOK_CATEGORIES = ['A', 'B', 'C']

# --- 信用分系统规则 ---
CREDIT_SCORE_INITIAL = 100
CREDIT_SCORE_MAX = 180
CREDIT_SCORE_MIN = 0
CREDIT_THRESHOLD_READ_A = 40
CREDIT_THRESHOLD_BORROW = 60
CREDIT_THRESHOLD_ORDER = 100

BOOK_DUE_DAYS = {'B': 30, 'C': 60}
APPOINTMENT_RESERVE_DAYS = 5


# --- 辅助函数 ---
def generate_isbn(category):
    return f"{category}-{random.randint(0, 9999):04d}"

def generate_student_id():
    return str(random.randint(MIN_STUDENT_ID, MAX_STUDENT_ID))

def get_next_date(current_date, strategy):
    """根据策略生成下一个日期"""
    if strategy == 'sparse':
        days_to_add = random.randint(15, 45)
    else: # normal
        days_to_add = random.randint(1, 3)
    return current_date + datetime.timedelta(days=days_to_add)

def format_date_str(date_obj):
    return date_obj.strftime("[%Y-%m-%d]")

class LibraryStateSimulator:
    """
    一个完整的状态模拟器，用于跟踪所有内部状态，以生成逻辑上合理的静态指令。
    即使不输出动态指令，内部也必须模拟它们以保持状态一致性。
    """
    def __init__(self, start_date):
        self.books_by_isbn = {}
        self.users = {}
        self.all_book_copies = {} # full_id -> copy_details
        self.current_date = start_date
        self.isbns_interacted_last_open_day = set()
        self.isbns_interacted_current_open_day = set()

    def add_book_type(self, isbn, category, num_copies):
        self.books_by_isbn[isbn] = {
            "category": category,
            "copies": [f"{isbn}-{i:02d}" for i in range(1, num_copies + 1)]
        }
        for i in range(1, num_copies + 1):
            full_id = f"{isbn}-{i:02d}"
            self.all_book_copies[full_id] = {
                "id": full_id, "isbn": isbn, "category": category,
                "location": "bs", "holder_id": None, "borrow_date": None,
                "reserved_for": None, "reservation_date": None
            }

    def _ensure_user(self, student_id):
        if student_id not in self.users:
            self.users[student_id] = {
                "id": student_id, "credit_score": CREDIT_SCORE_INITIAL,
                "held_books": {}, "active_order": None, "is_reading_today": None
            }

    def _change_credit(self, student_id, amount):
        self._ensure_user(student_id)
        score = self.users[student_id]["credit_score"]
        score += amount
        self.users[student_id]["credit_score"] = max(CREDIT_SCORE_MIN, min(CREDIT_SCORE_MAX, score))

    def _get_book_copy_on_shelf(self, isbn):
        candidates = [c for c in self.all_book_copies.values() if c['isbn'] == isbn and c['location'] in ['bs', 'hbs']]
        return random.choice(candidates) if candidates else None

    # --- 内部模拟的开/闭馆处理 ---
    def process_inter_day_penalties(self, new_date):
        """处理两个开馆日之间的每日逾期罚款（内部模拟）"""
        if self.current_date >= new_date: return
            
        one_day = datetime.timedelta(days=1)
        scan_date = self.current_date + one_day

        while scan_date < new_date:
            for user_id, user_data in self.users.items():
                for full_id, book_data in list(user_data.get("held_books", {}).items()):
                    category = self.all_book_copies[full_id]["category"]
                    if category not in BOOK_DUE_DAYS: continue
                    due_date = book_data["borrow_date"] + datetime.timedelta(days=BOOK_DUE_DAYS[category])
                    if scan_date == due_date + one_day:
                         self._change_credit(user_id, -5)
                    elif scan_date > due_date + one_day:
                        self._change_credit(user_id, -5)
            scan_date += one_day
        self.current_date = new_date

    def process_end_of_day_actions(self):
        """处理闭馆时的罚款和状态更新（内部模拟）"""
        # 模拟阅读不还罚款
        for user_id, user_data in self.users.items():
            if user_data["is_reading_today"] is not None:
                self._change_credit(user_id, -10)
                # 假设系统会自动整理，书回到书架
                book_copy = self.all_book_copies[user_data["is_reading_today"]]
                book_copy['location'] = 'rr' # 留在阅览室等待整理

        # 模拟预约不取罚款
        for book_id, book_data in self.all_book_copies.items():
            if book_data["location"] == "ao" and book_data["reservation_date"]:
                if (self.current_date - book_data["reservation_date"]).days >= APPOINTMENT_RESERVE_DAYS:
                    user_id = book_data["reserved_for"]
                    self._change_credit(user_id, -15)
                    if self.users[user_id]["active_order"] and self.users[user_id]["active_order"]["isbn"] == book_data['isbn']:
                        self.users[user_id]["active_order"] = None
                    book_data['reserved_for'] = None # 失效
                    book_data['reservation_date'] = None
        
        self.isbns_interacted_last_open_day = self.isbns_interacted_current_open_day.copy()
        self.isbns_interacted_current_open_day.clear()

        for user_data in self.users.values():
            user_data["is_reading_today"] = None

    def organization_phase(self):
        """模拟开馆整理（内部模拟）"""
        for book_id, book_data in self.all_book_copies.items():
            is_hot = book_data["isbn"] in self.isbns_interacted_last_open_day
            target_shelf = 'hbs' if is_hot else 'bs'
            
            if book_data["location"] in ["bro", "rr"]:
                book_data["location"] = target_shelf
            
            if book_data["location"] == "ao" and book_data["reserved_for"] is None: # 过期预约的书
                book_data["location"] = target_shelf
        
        for book_data in self.all_book_copies.values():
             is_hot = book_data["isbn"] in self.isbns_interacted_last_open_day
             if book_data["location"] == 'bs' and is_hot: book_data['location'] = 'hbs'
             if book_data['location'] == 'hbs' and not is_hot: book_data['location'] = 'bs'

        for user_id, user_data in self.users.items():
            if user_data["active_order"] and user_data["active_order"].get("fulfilled_date") is None:
                isbn_to_order = user_data["active_order"]["isbn"]
                copy_to_move = self._get_book_copy_on_shelf(isbn_to_order)
                if copy_to_move:
                    copy_to_move["location"] = "ao"
                    copy_to_move["reserved_for"] = user_id
                    copy_to_move["reservation_date"] = self.current_date
                    user_data["active_order"]["fulfilled_date"] = self.current_date

    # --- 内部模拟的动态行为，用于更新状态 ---
    def _simulate_return(self, student_id, full_id_to_return):
        user = self.users[student_id]
        book_copy = self.all_book_copies[full_id_to_return]
        
        borrow_date = book_copy['borrow_date']
        category = book_copy['category']
        due_date = borrow_date + datetime.timedelta(days=BOOK_DUE_DAYS[category])
        
        if self.current_date <= due_date: self._change_credit(student_id, 10)

        book_copy['location'] = 'bro'
        book_copy['holder_id'] = None
        book_copy['borrow_date'] = None
        del user['held_books'][full_id_to_return]

    def _simulate_pick(self, student_id, picked_copy):
        user = self.users[student_id]
        picked_copy['location'] = 'user'
        picked_copy['holder_id'] = student_id
        picked_copy['borrow_date'] = self.current_date
        picked_copy['reserved_for'] = None
        picked_copy['reservation_date'] = None
        user['held_books'][picked_copy['id']] = picked_copy
        user['active_order'] = None

    # --- 生成静态指令的函数 ---
    def try_generate_borrow(self, student_id):
        self._ensure_user(student_id)
        user = self.users[student_id]
        if user['credit_score'] < CREDIT_THRESHOLD_BORROW: return None

        # 倾向于借B/C类书
        possible_isbns = [isbn for isbn, data in self.books_by_isbn.items() if data['category'] != 'A']
        if not possible_isbns: return None
        
        isbn = random.choice(possible_isbns)
        book_info = self.books_by_isbn[isbn]
        
        if book_info['category'] == 'B' and any(b['category'] == 'B' for b in user['held_books'].values()): return None
        if book_info['category'] == 'C' and any(b['isbn'] == isbn for b in user['held_books'].values()): return None
        
        copy = self._get_book_copy_on_shelf(isbn)
        if copy:
            # 仅更新内部状态，然后生成指令
            copy['location'] = 'user' # 假设借阅成功
            copy['holder_id'] = student_id
            copy['borrow_date'] = self.current_date
            user['held_books'][copy['id']] = copy
            self.isbns_interacted_current_open_day.add(isbn)
            return f"{self.current_date_str} {student_id} borrowed {isbn}"
        return None

    def try_generate_read(self, student_id):
        self._ensure_user(student_id)
        user = self.users[student_id]

        if user['is_reading_today']: return None
        
        isbn = random.choice(list(self.books_by_isbn.keys()))
        book_info = self.books_by_isbn[isbn]
        
        if book_info['category'] == 'A' and user['credit_score'] < CREDIT_THRESHOLD_READ_A: return None
        if book_info['category'] in ['B', 'C'] and user['credit_score'] <= 0: return None
        
        copy = self._get_book_copy_on_shelf(isbn)
        if copy:
            # 更新内部状态
            copy['location'] = 'rr' # 假设阅读成功
            user['is_reading_today'] = copy['id']
            self.isbns_interacted_current_open_day.add(isbn)
            
            # 内部随机决定是否当天归还（这会影响信用分模拟）
            if random.random() < 0.7: # 70%概率当天归还以刷分
                self._change_credit(student_id, 10)
                copy['location'] = 'bro' # 模拟归还到借还处
                user['is_reading_today'] = None

            return f"{self.current_date_str} {student_id} read {isbn}"
        return None
        
    def try_generate_order(self, student_id):
        self._ensure_user(student_id)
        user = self.users[student_id]
        if user['credit_score'] < CREDIT_THRESHOLD_ORDER or user['active_order']: return None

        possible_isbns = [isbn for isbn, data in self.books_by_isbn.items() if data['category'] != 'A']
        if not possible_isbns: return None
        isbn = random.choice(possible_isbns)
        book_info = self.books_by_isbn[isbn]

        if book_info['category'] == 'B' and any(b['category'] == 'B' for b in user['held_books'].values()): return None
        if book_info['category'] == 'C' and any(b['isbn'] == isbn for b in user['held_books'].values()): return None

        user['active_order'] = {"isbn": isbn, "fulfilled_date": None}
        return f"{self.current_date_str} {student_id} ordered {isbn}"

    @property
    def current_date_str(self):
        return format_date_str(self.current_date)


def generate_one_test_case_data(strategy):
    initial_date = datetime.date(2025, 1, 1)
    state = LibraryStateSimulator(initial_date)
    
    num_book_types = random.randint(MIN_BOOK_TYPES, MAX_BOOK_TYPES)
    book_lines = [str(num_book_types)]
    
    for _ in range(num_book_types):
        category = random.choice(BOOK_CATEGORIES)
        isbn = generate_isbn(category)
        while isbn in state.books_by_isbn:
             isbn = generate_isbn(category)
        num_copies = random.randint(MIN_COPIES_PER_ISBN, MAX_COPIES_PER_ISBN)
        book_lines.append(f"{isbn} {num_copies}")
        state.add_book_type(isbn, category, num_copies)

    action_commands = []
    current_date = initial_date
    num_days = random.randint(MIN_DAYS_TO_SIMULATE, MAX_DAYS_TO_SIMULATE)

    for day_idx in range(num_days):
        next_day_date = get_next_date(current_date, strategy)
        # 即使是同一天，也必须先处理完闭馆惩罚再开馆
        if next_day_date > current_date:
            state.process_end_of_day_actions()
            state.process_inter_day_penalties(next_day_date)
        current_date = next_day_date
        
        action_commands.append(f"{state.current_date_str} OPEN")
        state.organization_phase()
        
        num_actions_today = random.randint(1, MAX_ACTIONS_PER_DAY)
        for _ in range(num_actions_today):
            student_id = generate_student_id()
            state._ensure_user(student_id)
            user_data = state.users[student_id]

            possible_actions = ['borrow', 'order', 'read', 'query_trace', 'query_credit']
            
            # 为了刷分，信用低时多读书
            weights = [10, 8, 15, 3, 5]
            if user_data['credit_score'] < 80:
                weights[2] = 30 # 'read'

            action_type = random.choices(possible_actions, weights=weights, k=1)[0]
            
            cmd = None
            if action_type == 'borrow':
                cmd = state.try_generate_borrow(student_id)
            elif action_type == 'read':
                cmd = state.try_generate_read(student_id)
            elif action_type == 'order':
                cmd = state.try_generate_order(student_id)
            elif action_type == 'query_trace':
                book_id = random.choice(list(state.all_book_copies.keys()))
                cmd = f"{state.current_date_str} {student_id} queried {book_id}"
            elif action_type == 'query_credit':
                cmd = f"{state.current_date_str} {student_id} queried credit score"

            if cmd:
                action_commands.append(cmd)
        
        # 闭馆前的模拟操作（不生成指令）
        # 模拟评测机会在某天还书，以更新内部状态
        if strategy == 'sparse' and day_idx > num_days // 2: # 在稀疏模式的后期，模拟还书
            for user_id, user in list(state.users.items()):
                if user['held_books'] and random.random() < 0.5:
                    book_to_return = random.choice(list(user['held_books'].keys()))
                    state._simulate_return(user_id, book_to_return)

        # 模拟评测机会在某天取书
        for user_id, user in list(state.users.items()):
            if user['active_order'] and user['active_order']['fulfilled_date']:
                if random.random() < 0.5: # 50%概率取书
                    isbn_to_pick = user['active_order']['isbn']
                    picked_copy = None
                    for copy in state.all_book_copies.values():
                        if copy['location'] == 'ao' and copy['reserved_for'] == user_id and copy['isbn'] == isbn_to_pick:
                            picked_copy = copy
                            break
                    if picked_copy:
                        state._simulate_pick(user_id, picked_copy)
        
        action_commands.append(f"{state.current_date_str} CLOSE")
        
    return book_lines + action_commands

def main():
    num_total_cases = int(input("请输入要生成的测试用例总数: "))
    
    if os.path.exists(TEST_CASES_DIR):
        print(f"目录 '{TEST_CASES_DIR}' 已存在，正在清空...")
        # 为了安全，改为只删除文件，不删除目录本身
        for filename in os.listdir(TEST_CASES_DIR):
            file_path = os.path.join(TEST_CASES_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'删除文件失败 {file_path}. 原因: {e}')
    else:
        os.makedirs(TEST_CASES_DIR, exist_ok=True)

    num_sparse_cases = num_total_cases // 2
    num_normal_cases = num_total_cases - num_sparse_cases

    print(f"将生成 {num_normal_cases} 个常规策略用例和 {num_sparse_cases} 个稀疏策略用例。")

    case_counter = 1
    for i in range(num_normal_cases):
        print(f"正在生成常规用例 {i+1}/{num_normal_cases} ...")
        test_data = generate_one_test_case_data('normal')
        file_path = os.path.join(TEST_CASES_DIR, f"case_normal_{case_counter:03d}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_data))
        case_counter += 1

    for i in range(num_sparse_cases):
        print(f"正在生成稀疏用例 {i+1}/{num_sparse_cases} ...")
        test_data = generate_one_test_case_data('sparse')
        file_path = os.path.join(TEST_CASES_DIR, f"case_sparse_{case_counter:03d}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_data))
        case_counter += 1

    print(f"\n成功生成 {num_total_cases} 个测试用例到目录 '{TEST_CASES_DIR}'。")

if __name__ == "__main__":
    main()