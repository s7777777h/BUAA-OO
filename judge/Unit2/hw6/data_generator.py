import random
import math
import sys
import os
import collections

# --- Configuration ---
# 设置为 True 将每个测试用例写入文件 (testcase_1.txt, testcase_2.txt, ...)
WRITE_TO_FILES = True
# 设置为 True 将所有测试用例打印到控制台
PRINT_TO_CONSOLE = True
# 定义子目录名称
DATA_SUBDIR = "data" # 使用新的目录名以区分
# --- End Configuration ---

# --- Constants based on problem description (Iteration 2) ---
FLOORS = ["B4", "B3", "B2", "B1", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
NUM_FLOORS = len(FLOORS)
NUM_ELEVATORS = 6

# Iteration 2 Mutual Testing Limits & Constraints
MAX_TOTAL_INSTRUCTIONS = 70      # 乘客请求 + SCHE 请求总数上限
MIN_TOTAL_INSTRUCTIONS = 5       # 至少生成几条指令（可以调整）
# MAX_PASSENGER_REQUESTS = 100  # 基本限制，但受 MAX_TOTAL_INSTRUCTIONS 约束
MAX_SCHE_PER_ELEVATOR = 1        # 每个电梯最多一次 SCHE
MAX_TOTAL_SCHE_REQUESTS = NUM_ELEVATORS # 总 SCHE 请求上限

MIN_FIRST_TIMESTAMP = 1.0
MAX_LAST_TIMESTAMP = 50.0

# Iteration 2 SCHE specific constants
SCHE_TARGET_FLOORS = ["B2", "B1", "F1", "F2", "F3", "F4", "F5"]
SCHE_SPEEDS = [0.2, 0.3, 0.4, 0.5]

# Other generation parameters
MAX_PASSENGER_ID = 1000 # 如有需要可调整
MAX_PRIORITY = 100

# 定义请求类型的具名元组，方便处理
RequestData = collections.namedtuple('RequestData', ['timestamp', 'type', 'details'])

def generate_passenger_request_details(used_passenger_ids):
    """生成单个乘客请求的详细信息（除时间戳外）"""
    # 1. 生成唯一的乘客 ID
    passenger_id = random.randint(1, MAX_PASSENGER_ID)
    while passenger_id in used_passenger_ids:
        passenger_id = random.randint(1, MAX_PASSENGER_ID)
    used_passenger_ids.add(passenger_id)

    # 2. 生成优先级
    priority = random.randint(1, MAX_PRIORITY)

    # 3. 生成起点和终点楼层（不同）
    start_floor_index = random.randrange(NUM_FLOORS)
    end_floor_index = random.randrange(NUM_FLOORS)
    while start_floor_index == end_floor_index:
        end_floor_index = random.randrange(NUM_FLOORS)
    start_floor = FLOORS[start_floor_index]
    end_floor = FLOORS[end_floor_index]

    return {
        "id": passenger_id,
        "priority": priority,
        "from": start_floor,
        "to": end_floor
    }

def generate_sche_request_details(used_sche_elevator_ids):
    """生成单个临时调度请求的详细信息（除时间戳外）"""
    if len(used_sche_elevator_ids) >= NUM_ELEVATORS:
        return None # 无法再为新的电梯生成 SCHE 请求

    # 1. 选择一个尚未进行 SCHE 的电梯 ID
    elevator_id = random.randint(1, NUM_ELEVATORS)
    while elevator_id in used_sche_elevator_ids:
        elevator_id = random.randint(1, NUM_ELEVATORS)
    used_sche_elevator_ids.add(elevator_id)

    # 2. 选择临时速度
    speed = random.choice(SCHE_SPEEDS)

    # 3. 选择目标楼层
    target_floor = random.choice(SCHE_TARGET_FLOORS)

    return {
        "elevator_id": elevator_id,
        "speed": speed,
        "target_floor": target_floor
    }

def format_request(request_data):
    """根据请求数据格式化最终的请求字符串"""
    formatted_timestamp = f"[{request_data.timestamp:.1f}]"
    details = request_data.details

    if request_data.type == 'passenger':
        return (f"{formatted_timestamp}{details['id']}-PRI-{details['priority']}"
                f"-FROM-{details['from']}-TO-{details['to']}")
    elif request_data.type == 'sche':
        return (f"{formatted_timestamp}SCHE-{details['elevator_id']}"
                f"-{details['speed']:.1f}-{details['target_floor']}") # 确保速度也有一位小数
    else:
        return "" # 不支持的类型

def generate_test_case():
    """生成一个包含乘客请求和临时调度请求的测试用例"""
    all_requests_data = []
    used_passenger_ids = set()
    used_sche_elevator_ids = set() # 跟踪已用于SCHE的电梯

    # 1. 决定总请求数和各类请求数
    total_instructions = random.randint(MIN_TOTAL_INSTRUCTIONS, MAX_TOTAL_INSTRUCTIONS)
    # 随机决定 SCHE 请求的数量 (0 到 MAX_TOTAL_SCHE_REQUESTS，且不超过总数)
    max_possible_sche = min(MAX_TOTAL_SCHE_REQUESTS, total_instructions)
    num_sche_requests = random.randint(0, max_possible_sche)
    num_passenger_requests = total_instructions - num_sche_requests

    # 确保至少有一条乘客请求（如果总指令>0），除非只生成了SCHE请求
    if total_instructions > 0 and num_passenger_requests <= 0 and num_sche_requests < total_instructions:
         num_passenger_requests = 1
         num_sche_requests = total_instructions - 1
         if num_sche_requests < 0: # 如果总共只有1条，那就只有乘客请求
              num_sche_requests = 0
              num_passenger_requests = 1
    elif num_passenger_requests < 0: # 防止负数
         num_passenger_requests = 0


    # print(f"Generating test case with {total_instructions} total instructions: "
    #       f"{num_passenger_requests} passenger, {num_sche_requests} SCHE.") # Debug info

    # 2. 生成所有请求的时间戳
    timestamps = []
    last_timestamp = 0.0
    for i in range(total_instructions):
        time_range_available = MAX_LAST_TIMESTAMP - max(last_timestamp, MIN_FIRST_TIMESTAMP)
        remaining_requests = total_instructions - i

        # 允许时间戳相同，但后续时间戳不能小于之前的
        # 稍微增加一点随机性，允许微小的增量或者0增量
        min_increment = 0.0
        # max_possible_increment = 0.0 # 这个计算可能过于限制
        # if remaining_requests > 1:
        #     max_possible_increment = time_range_available / (remaining_requests - 1)
        # increment = random.uniform(min_increment, max(0.01, max_possible_increment * 0.5)) # 缩小范围避免过快到达上限
        increment = random.uniform(min_increment, max(0.01, time_range_available * 0.1)) # 简化增量计算

        current_timestamp = last_timestamp + increment
        current_timestamp = round(current_timestamp, 1) # 四舍五入到一位小数

        if i == 0:
            current_timestamp = max(MIN_FIRST_TIMESTAMP, current_timestamp) # 确保第一个不小于 MIN_FIRST_TIMESTAMP

        current_timestamp = min(MAX_LAST_TIMESTAMP, current_timestamp) # 确保不超过 MAX_LAST_TIMESTAMP
        current_timestamp = max(last_timestamp, current_timestamp) # 确保非递减

        timestamps.append(current_timestamp)
        last_timestamp = current_timestamp

    # 3. 生成乘客请求的详细数据
    passenger_details_list = []
    for _ in range(num_passenger_requests):
        details = generate_passenger_request_details(used_passenger_ids)
        passenger_details_list.append(details)

    # 4. 生成 SCHE 请求的详细数据
    sche_details_list = []
    for _ in range(num_sche_requests):
        details = generate_sche_request_details(used_sche_elevator_ids)
        if details: # 可能因为电梯用完而返回 None
             sche_details_list.append(details)
        else:
            # 如果无法生成更多SCHE（不太可能在限制内发生，但以防万一），
            # 我们可以选择减少总数或用乘客请求替换，这里简单忽略
            print("Warning: Could not generate a unique SCHE request, reducing SCHE count.", file=sys.stderr)
            pass


    # 5. 将时间戳与随机打乱的请求类型配对
    request_types = ['passenger'] * len(passenger_details_list) + ['sche'] * len(sche_details_list)
    # 如果因为SCHE生成失败导致总数减少，需要调整时间戳数量
    actual_total_instructions = len(request_types)
    if actual_total_instructions < total_instructions:
        print(f"Adjusting total instructions from {total_instructions} to {actual_total_instructions} due to SCHE generation limits.", file=sys.stderr)
        timestamps = timestamps[:actual_total_instructions] # 只取需要的时间戳

    random.shuffle(request_types) # 随机打乱请求类型顺序

    passenger_idx = 0
    sche_idx = 0
    for i in range(actual_total_instructions):
        req_type = request_types[i]
        timestamp = timestamps[i]
        details = None
        if req_type == 'passenger':
            details = passenger_details_list[passenger_idx]
            passenger_idx += 1
        elif req_type == 'sche':
            details = sche_details_list[sche_idx]
            sche_idx += 1

        if details: # 确保details不是None
             all_requests_data.append(RequestData(timestamp=timestamp, type=req_type, details=details))

    # 6. 格式化所有请求
    final_requests = [format_request(req_data) for req_data in all_requests_data]

    return final_requests

def main():
    """获取用户输入并生成所请求数量的测试集。"""
    num_sets = 1 # 默认值
    try:
        num_str = input("Enter the number of test sets to generate: ")
        num_sets = int(num_str)
        if num_sets <= 0:
            print("Number of sets must be positive. Defaulting to 1.")
            num_sets = 1
    except ValueError:
        print("Invalid input. Defaulting to 1 test set.")

    # --- 创建数据子目录（如果不存在） ---
    if WRITE_TO_FILES:
        try:
            os.makedirs(DATA_SUBDIR, exist_ok=True) # 创建目录，如果存在则不报错
            print(f"Ensured directory '{DATA_SUBDIR}' exists.")
        except OSError as e:
            print(f"Error creating directory {DATA_SUBDIR}: {e}", file=sys.stderr)
            print("Will attempt to write files to the current directory instead.")
            # 可选：在这里退出或设置 WRITE_TO_FILES 为 False
            # 当前行为：如果创建失败，会尝试写入当前目录
    # --- 结束创建目录部分 ---


    print(f"\nGenerating {num_sets} test set(s)...")
    print("========================================")

    for i in range(1, num_sets + 1):
        test_case = generate_test_case()

        if PRINT_TO_CONSOLE:
            print(f"--- Test Set {i} ---")
            for request in test_case:
                print(request)
            print("--------------------")

        if WRITE_TO_FILES:
            # --- 构建包含子目录的完整路径 ---
            base_filename = f"testcase_{i}.txt"
            filepath = os.path.join(DATA_SUBDIR, base_filename) # 使用 os.path.join
            # --- 结束修改 ---
            try:
                # 使用完整文件路径
                with open(filepath, 'w') as f:
                    for request in test_case:
                        f.write(request + '\n')
                # 报告正确的路径
                print(f"Test Set {i} written to {filepath}")
            except IOError as e:
                print(f"Error writing Test Set {i} to file {filepath}: {e}", file=sys.stderr)

        if PRINT_TO_CONSOLE or WRITE_TO_FILES:
            print() # 在集合输出信息之间添加一个空行

    print("========================================")
    print("Data generation complete.")

if __name__ == "__main__":
    main()