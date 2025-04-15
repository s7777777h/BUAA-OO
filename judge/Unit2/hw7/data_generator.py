import random
import math
import sys
import os
import collections

# --- Configuration ---
WRITE_TO_FILES = True
PRINT_TO_CONSOLE = True
DATA_SUBDIR = "data"
# --- End Configuration ---

# --- Constants ---
FLOORS = ["B4", "B3", "B2", "B1", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
FLOOR_MAP = {floor: i for i, floor in enumerate(FLOORS)}
NUM_FLOORS = len(FLOORS)
NUM_ELEVATORS = 6
MIN_FIRST_TIMESTAMP = 1.0
MAX_LAST_TIMESTAMP = 50.0
MAX_PASSENGER_ID = 1000
MAX_PRIORITY = 100
MIN_PASSENGER_REQUESTS = 1
SCHE_TARGET_FLOORS = ["B2", "B1", "F1", "F2", "F3", "F4", "F5"]
SCHE_SPEEDS = [0.2, 0.3, 0.4, 0.5]
UPDATE_TARGET_FLOORS = ["B2", "B1", "F1", "F2", "F3", "F4", "F5"]
SCHE_MIN_INTERVAL = 8.0
UPDATE_MIN_INTERVAL = 8.0 # Same interval applies

# Mutual Mode Limits
MAX_TOTAL_INSTRUCTIONS_MUTUAL = 70
MAX_SCHE_PER_ELEVATOR_MUTUAL = 1
MAX_UPDATE_INVOLVEMENT_MUTUAL = 1
max_total_sche_mutual = NUM_ELEVATORS * MAX_SCHE_PER_ELEVATOR_MUTUAL
max_total_update_mutual = (NUM_ELEVATORS // 2) * MAX_UPDATE_INVOLVEMENT_MUTUAL
min_total_instructions_mutual = 5

# Strong Mode Limits
MAX_PASSENGER_REQUESTS_STRONG = 100
MAX_TOTAL_SCHE_STRONG = 20
MAX_TOTAL_UPDATE_STRONG = 20
MAX_TOTAL_INSTRUCTIONS_STRONG = 150
min_total_instructions_strong = MIN_PASSENGER_REQUESTS

RequestData = collections.namedtuple('RequestData', ['timestamp', 'type', 'details'])

# --- Helper Functions ---
# (generate_passenger_request_details, generate_sche_request_details,
#  generate_update_request_details, format_request remain the same as before)
def generate_passenger_request_details(used_passenger_ids):
    passenger_id = random.randint(1, MAX_PASSENGER_ID)
    while passenger_id in used_passenger_ids:
        passenger_id = random.randint(1, MAX_PASSENGER_ID)
    used_passenger_ids.add(passenger_id)
    priority = random.randint(1, MAX_PRIORITY)
    start_floor_index = random.randrange(NUM_FLOORS)
    end_floor_index = random.randrange(NUM_FLOORS)
    while start_floor_index == end_floor_index:
        end_floor_index = random.randrange(NUM_FLOORS)
    start_floor = FLOORS[start_floor_index]
    end_floor = FLOORS[end_floor_index]
    return {"id": passenger_id, "priority": priority, "from": start_floor, "to": end_floor}

def generate_sche_request_details(available_elevator_ids):
    if not available_elevator_ids:
        return None, None
    elevator_id = random.choice(list(available_elevator_ids))
    speed = random.choice(SCHE_SPEEDS)
    target_floor = random.choice(SCHE_TARGET_FLOORS)
    details = {"elevator_id": elevator_id, "speed": speed, "target_floor": target_floor}
    return details, elevator_id

def generate_update_request_details(available_elevator_ids):
    if len(available_elevator_ids) < 2:
        return None, None, None
    id_a, id_b = random.sample(list(available_elevator_ids), 2)
    target_floor = random.choice(UPDATE_TARGET_FLOORS)
    details = {"elevator_id_a": id_a, "elevator_id_b": id_b, "target_floor": target_floor}
    return details, id_a, id_b

def format_request(request_data):
    formatted_timestamp = f"[{request_data.timestamp:.1f}]"
    details = request_data.details
    if request_data.type == 'passenger':
        return (f"{formatted_timestamp}{details['id']}-PRI-{details['priority']}"
                f"-FROM-{details['from']}-TO-{details['to']}")
    elif request_data.type == 'sche':
        return (f"{formatted_timestamp}SCHE-{details['elevator_id']}"
                f"-{details['speed']:.1f}-{details['target_floor']}")
    elif request_data.type == 'update':
         return (f"{formatted_timestamp}UPDATE-{details['elevator_id_a']}"
                 f"-{details['elevator_id_b']}-{details['target_floor']}")
    else: return ""
# --- End Helper Functions ---


# --- Main Generation Logic ---
def generate_test_case(mode):
    """Generates a test case respecting mode-specific constraints."""
    print(f"Generating test case in '{mode}' mode...")

    # 1. Set limits based on mode
    if mode == 'mutual':
        max_total_instructions = MAX_TOTAL_INSTRUCTIONS_MUTUAL
        max_sche_per_elevator = MAX_SCHE_PER_ELEVATOR_MUTUAL
        max_update_involvement = MAX_UPDATE_INVOLVEMENT_MUTUAL
        max_total_sche = max_total_sche_mutual
        max_total_update = max_total_update_mutual
        min_total_instructions = min_total_instructions_mutual
    elif mode == 'strong':
        max_total_instructions = MAX_TOTAL_INSTRUCTIONS_STRONG
        max_passenger_requests = MAX_PASSENGER_REQUESTS_STRONG # Use this later if needed
        max_total_sche = MAX_TOTAL_SCHE_STRONG
        max_total_update = MAX_TOTAL_UPDATE_STRONG
        min_total_instructions = min_total_instructions_strong
        max_sche_per_elevator = float('inf') # No per-elevator limit for strong
        max_update_involvement = float('inf') # No per-elevator limit for strong
    else:
        raise ValueError(f"Unknown mode: {mode}") # Should not happen

    # 2. Determine number of requests (initial plan)
    total_instructions = random.randint(min_total_instructions, max_total_instructions)
    num_sche_requests_planned = random.randint(0, min(max_total_sche, total_instructions))
    remaining_slots = total_instructions - num_sche_requests_planned
    effective_max_update = min(max_total_update, remaining_slots, NUM_ELEVATORS // 2) # Also limited by pairs
    num_update_requests_planned = random.randint(0, effective_max_update)
    num_passenger_requests_planned = total_instructions - num_sche_requests_planned - num_update_requests_planned

    # Adjust if minimum passenger requests not met
    if total_instructions > 0 and num_passenger_requests_planned < MIN_PASSENGER_REQUESTS:
        num_passenger_requests_planned = MIN_PASSENGER_REQUESTS
        needed_reduction = MIN_PASSENGER_REQUESTS - (total_instructions - num_sche_requests_planned - num_update_requests_planned)
        reduced_update = min(num_update_requests_planned, needed_reduction)
        num_update_requests_planned -= reduced_update
        needed_reduction -= reduced_update
        if needed_reduction > 0:
            reduced_sche = min(num_sche_requests_planned, needed_reduction)
            num_sche_requests_planned -= reduced_sche
        total_instructions = num_passenger_requests_planned + num_sche_requests_planned + num_update_requests_planned
        print(f"Adjusted planned counts: P={num_passenger_requests_planned}, S={num_sche_requests_planned}, U={num_update_requests_planned}", file=sys.stderr)

    if num_passenger_requests_planned < 0: num_passenger_requests_planned = 0
    if num_sche_requests_planned < 0: num_sche_requests_planned = 0
    if num_update_requests_planned < 0: num_update_requests_planned = 0
    total_instructions = num_passenger_requests_planned + num_sche_requests_planned + num_update_requests_planned

    if total_instructions == 0:
        print("Warning: Generating an empty test case.", file=sys.stderr)
        return []

    print(f"  Planned counts: P={num_passenger_requests_planned}, S={num_sche_requests_planned}, U={num_update_requests_planned} (Total={total_instructions})")

    # 3. Generate Timestamps (initial distribution)
    timestamps = []
    last_timestamp = 0.0
    time_range = MAX_LAST_TIMESTAMP - MIN_FIRST_TIMESTAMP
    avg_interval = time_range / total_instructions if total_instructions > 1 else time_range
    for i in range(total_instructions):
        increment = max(0.0, random.uniform(0, avg_interval * 1.5))
        current_timestamp = last_timestamp + increment
        current_timestamp = round(current_timestamp, 1)
        if i == 0: current_timestamp = max(MIN_FIRST_TIMESTAMP, current_timestamp)
        current_timestamp = max(last_timestamp, current_timestamp)
        timestamps.append(current_timestamp)
        last_timestamp = current_timestamp

    # 4. Prepare for detail generation and assignment
    all_requests_data = []
    used_passenger_ids = set()
    # Track elevator usage and last event time
    elevator_sche_counts = collections.defaultdict(int) # For mutual check mainly
    elevator_update_involvement = set() # Store IDs involved in update
    last_elevator_special_event_time = collections.defaultdict(lambda: -float('inf')) # Tracks last SCHE/UPDATE time per elevator

    request_types_planned = (['passenger'] * num_passenger_requests_planned +
                             ['sche'] * num_sche_requests_planned +
                             ['update'] * num_update_requests_planned)
    random.shuffle(request_types_planned)

    # 5. Generate details and create RequestData objects, applying constraints during generation
    actual_sche_count = 0
    actual_update_count = 0
    actual_passenger_count = 0
    timestamps_copy = list(timestamps) # Use timestamps in generated order

    for i in range(len(request_types_planned)):
        req_type = request_types_planned[i]
        if not timestamps_copy: break # Should not happen if counts match
        timestamp = timestamps_copy.pop(0) # Get the planned timestamp

        details = None
        generated_successfully = False

        if req_type == 'passenger':
            details = generate_passenger_request_details(used_passenger_ids)
            if details:
                all_requests_data.append(RequestData(timestamp=timestamp, type=req_type, details=details))
                actual_passenger_count += 1
                generated_successfully = True

        elif req_type == 'sche':
            # --- SCHE Generation Logic ---
            # Identify elevators currently available for SCHE
            current_available_sche = set(range(1, NUM_ELEVATORS + 1)) - elevator_update_involvement

            # Apply mode-specific filtering
            if mode == 'mutual':
                # Keep only those not yet used for SCHE
                current_available_sche = {e_id for e_id in current_available_sche if elevator_sche_counts[e_id] < max_sche_per_elevator}
            elif mode == 'strong':
                # Keep only those whose last event was >= 8 seconds ago
                current_available_sche = {e_id for e_id in current_available_sche if timestamp - last_elevator_special_event_time[e_id] >= SCHE_MIN_INTERVAL}

            # Attempt to generate details using the filtered set
            details, used_id = generate_sche_request_details(current_available_sche)

            if details:
                all_requests_data.append(RequestData(timestamp=timestamp, type=req_type, details=details))
                actual_sche_count += 1
                generated_successfully = True

                # Update tracking state
                elevator_sche_counts[used_id] += 1
                last_elevator_special_event_time[used_id] = timestamp
                # Note: In strong mode, elevator *might* be available for SCHE again later.
                # In mutual mode, the count check prevents reuse.
                # An elevator receiving SCHE cannot be part of UPDATE later.
                elevator_update_involvement.add(used_id) # Prevent future UPDATE

            else:
                print(f"Warning: Could not generate SCHE request for timestamp {timestamp:.1f}, no suitable elevator respecting constraints.", file=sys.stderr)


        elif req_type == 'update':
            # --- UPDATE Generation Logic ---
            # Identify elevators available for UPDATE (not involved in previous UPDATE or SCHE)
            current_available_update = set(range(1, NUM_ELEVATORS + 1)) - elevator_update_involvement

            # Apply mode-specific filtering (redundant due to elevator_update_involvement set, but safe)
            if mode == 'mutual':
                 pass # Already filtered by the set subtraction

            # Check if at least 2 elevators are available
            if len(current_available_update) < 2:
                 print(f"Warning: Could not generate UPDATE request for timestamp {timestamp:.1f}, less than 2 elevators available.", file=sys.stderr)
                 continue # Skip to next request type

            # Attempt to generate details
            details, used_id_a, used_id_b = generate_update_request_details(current_available_update)

            if details:
                 # Additional check for strong mode (though unlikely to fail due to availability check): Check 8s interval for both elevators
                 if mode == 'strong':
                     if not (timestamp - last_elevator_special_event_time[used_id_a] >= UPDATE_MIN_INTERVAL and \
                             timestamp - last_elevator_special_event_time[used_id_b] >= UPDATE_MIN_INTERVAL):
                         print(f"Warning: Could not generate UPDATE for {used_id_a}-{used_id_b} at {timestamp:.1f}, violates 8s rule for involved elevator.", file=sys.stderr)
                         details = None # Prevent adding this request

            if details: # If still valid after checks
                all_requests_data.append(RequestData(timestamp=timestamp, type=req_type, details=details))
                actual_update_count += 1
                generated_successfully = True

                # Update tracking state: Mark both elevators as permanently involved/unavailable
                elevator_update_involvement.add(used_id_a)
                elevator_update_involvement.add(used_id_b)
                last_elevator_special_event_time[used_id_a] = timestamp
                last_elevator_special_event_time[used_id_b] = timestamp

            else:
                 # Failure might be due to generate_update_request_details or the 8s check
                 if len(current_available_update) >= 2: # Only print if failure wasn't due to lack of elevators
                     print(f"Warning: Could not generate UPDATE request for timestamp {timestamp:.1f} (possible internal issue or 8s violation).", file=sys.stderr)


    # Report actual counts generated
    print(f"  Actual counts generated: P={actual_passenger_count}, S={actual_sche_count}, U={actual_update_count} (Total={len(all_requests_data)})")

    # 6. Sort by timestamp and enforce GLOBAL 8s interval between ANY SCHE/UPDATE
    all_requests_data.sort(key=lambda r: r.timestamp)

    last_global_special_timestamp = -float('inf') # Timestamp of the last SCHE or UPDATE globally
    final_adjusted_requests = []
    latest_overall_timestamp = 0.0 # Track latest timestamp overall for non-decreasing check

    for request in all_requests_data:
        current_timestamp = request.timestamp
        current_timestamp = max(current_timestamp, latest_overall_timestamp) # Ensure non-decreasing initially

        if request.type in ['sche', 'update']:
            # Apply GLOBAL 8s interval check
            required_timestamp = last_global_special_timestamp + SCHE_MIN_INTERVAL
            if current_timestamp < required_timestamp:
                current_timestamp = required_timestamp
                current_timestamp = math.ceil(current_timestamp * 10) / 10.0 # Round up

            if current_timestamp > MAX_LAST_TIMESTAMP:
                 print(f"Warning: Adjusted GLOBAL timestamp {current_timestamp:.1f} for {request.type} exceeds MAX_LAST_TIMESTAMP. Capping.", file=sys.stderr)
                 current_timestamp = MAX_LAST_TIMESTAMP

            last_global_special_timestamp = current_timestamp # Update global tracker

        else: # Passenger request
             # Ensure passenger request doesn't happen before the preceding adjusted special request's time
             current_timestamp = max(current_timestamp, last_global_special_timestamp if last_global_special_timestamp > -float('inf') else -float('inf'))
             if current_timestamp > MAX_LAST_TIMESTAMP:
                 print(f"Warning: Timestamp {current_timestamp:.1f} for passenger request exceeds MAX_LAST_TIMESTAMP. Capping.", file=sys.stderr)
                 current_timestamp = MAX_LAST_TIMESTAMP

        current_timestamp = round(current_timestamp, 1)
        latest_overall_timestamp = current_timestamp # Update overall tracker

        adjusted_request = RequestData(timestamp=current_timestamp, type=request.type, details=request.details)
        final_adjusted_requests.append(adjusted_request)


    # 7. Format final requests
    output_requests = [format_request(req_data) for req_data in final_adjusted_requests]
    output_requests = [req for req in output_requests if req] # Filter out potential empty strings

    return output_requests

# --- Main Execution ---
def main():
    """Get parameters via console prompts, generate test sets, and write/print them."""
    num_sets = 0
    while num_sets <= 0:
        try:
            num_str = input("Enter the number of test sets to generate (positive integer): ")
            num_sets = int(num_str)
            if num_sets <= 0: print("Number must be positive.")
        except ValueError: print("Invalid input. Please enter an integer.")

    mode = ""
    allowed_inputs = {'m', 's', 'mutual', 'strong'}
    mode_map = {'m': 'mutual', 's': 'strong', 'mutual': 'mutual', 'strong': 'strong'}
    while True:
        user_input = input("Enter the generation mode ('m' for mutual, 's' for strong): ").lower()
        if user_input in allowed_inputs:
            mode = mode_map[user_input]
            break
        else: print("Invalid mode. Please enter 'm' or 's'.")

    write_to_files = WRITE_TO_FILES
    print_to_console = PRINT_TO_CONSOLE
    output_dir = DATA_SUBDIR

    if write_to_files:
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Ensured output directory '{output_dir}' exists.")
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}", file=sys.stderr)
            print("Disabling file writing.")
            write_to_files = False

    print(f"\nGenerating {num_sets} test set(s) in '{mode}' mode...")
    print("========================================")

    for i in range(1, num_sets + 1):
        print(f"--- Generating Set {i} ---")
        test_case = generate_test_case(mode)

        if not test_case:
             print(f"--- Test Set {i} (EMPTY) ---")
             continue

        if print_to_console:
            print(f"--- Test Set {i} ({mode} mode) ---")
            for request in test_case:
                print(request)
            print("-----------------------------")

        if write_to_files:
            base_filename = f"{mode}_test_{i}.txt"
            filepath = os.path.join(output_dir, base_filename)
            try:
                with open(filepath, 'w') as f:
                    for request in test_case:
                        f.write(request + '\n')
                print(f"Test Set {i} written to {filepath}")
            except IOError as e:
                print(f"Error writing Test Set {i} to file {filepath}: {e}", file=sys.stderr)

        if print_to_console or write_to_files: print()

    print("========================================")
    print("Data generation complete.")

if __name__ == "__main__":
    main()