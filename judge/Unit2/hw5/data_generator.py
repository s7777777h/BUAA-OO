import random
import math
import sys
import os  # Import the os module

# --- Configuration ---
# Set to True to write each test case to a file (testcase_1.txt, testcase_2.txt, ...)
WRITE_TO_FILES = True
# Set to True to print all test cases to the console
PRINT_TO_CONSOLE = True
# Define the subdirectory name
DATA_SUBDIR = "data"
# --- End Configuration ---

# --- Constants based on problem description ---
FLOORS = ["B4", "B3", "B2", "B1", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
NUM_FLOORS = len(FLOORS)
NUM_ELEVATORS = 3

# Mutual Testing Limits
MAX_REQUESTS_PER_ELEVATOR = 30
MAX_TOTAL_REQUESTS = 70
MIN_TOTAL_REQUESTS = 30
MIN_FIRST_TIMESTAMP = 1.0
MAX_LAST_TIMESTAMP = 25.0

# Other generation parameters
MAX_PASSENGER_ID = 1000 # Adjust if needed
MAX_PRIORITY = 100

def generate_test_case():
    """Generates a single list of valid elevator requests for one test case."""
    requests = []
    used_passenger_ids = set()
    # Index 0 for elevator 1, index 1 for elevator 2, etc.
    elevator_request_counts = [0] * NUM_ELEVATORS

    num_requests = random.randint(MIN_TOTAL_REQUESTS, MAX_TOTAL_REQUESTS)
    # print(f"Generating test case with {num_requests} requests.") # Debug info

    last_timestamp = 0.0

    for i in range(num_requests):
        # 1. Generate Timestamp
        remaining_requests = num_requests - i
        time_range_available = MAX_LAST_TIMESTAMP - max(last_timestamp, MIN_FIRST_TIMESTAMP)

        max_possible_increment = 0.0
        if remaining_requests > 1:
             max_possible_increment = time_range_available / (remaining_requests -1)
        increment = random.uniform(0.01, max(0.02, max_possible_increment * 0.8))

        current_timestamp = last_timestamp + increment

        if i == 0:
            current_timestamp = max(MIN_FIRST_TIMESTAMP, current_timestamp)
        current_timestamp = min(MAX_LAST_TIMESTAMP, current_timestamp)
        current_timestamp = max(last_timestamp, current_timestamp)

        formatted_timestamp = f"[{current_timestamp:.1f}]"
        last_timestamp = current_timestamp

        # 2. Generate Unique Passenger ID
        passenger_id = random.randint(1, MAX_PASSENGER_ID)
        while passenger_id in used_passenger_ids:
            passenger_id = random.randint(1, MAX_PASSENGER_ID)
        used_passenger_ids.add(passenger_id)

        # 3. Generate Priority
        priority = random.randint(1, MAX_PRIORITY)

        # 4. Generate Start and End Floors (different)
        start_floor_index = random.randrange(NUM_FLOORS)
        end_floor_index = random.randrange(NUM_FLOORS)
        while start_floor_index == end_floor_index:
            end_floor_index = random.randrange(NUM_FLOORS)
        start_floor = FLOORS[start_floor_index]
        end_floor = FLOORS[end_floor_index]

        # 5. Generate Elevator ID (respecting MAX_REQUESTS_PER_ELEVATOR)
        available_elevators = []
        for j in range(NUM_ELEVATORS):
            if elevator_request_counts[j] < MAX_REQUESTS_PER_ELEVATOR:
                available_elevators.append(j + 1) # Add elevator ID (1-based)

        if not available_elevators:
            print("Error: No available elevator found! Check constraints. Assigning randomly.", file=sys.stderr)
            chosen_elevator_id = random.randint(1, NUM_ELEVATORS)
            elevator_request_counts[chosen_elevator_id - 1] += 1
        else:
            chosen_elevator_id = random.choice(available_elevators)
            elevator_request_counts[chosen_elevator_id - 1] += 1

        # 6. Format Request String
        request = (f"{formatted_timestamp}{passenger_id}-PRI-{priority}"
                   f"-FROM-{start_floor}-TO-{end_floor}-BY-{chosen_elevator_id}")
        requests.append(request)

    return requests

def main():
    """Gets user input and generates the requested number of test sets."""
    num_sets = 1 # Default
    try:
        num_str = input("Enter the number of test sets to generate: ")
        num_sets = int(num_str)
        if num_sets <= 0:
            print("Number of sets must be positive. Defaulting to 1.")
            num_sets = 1
    except ValueError:
        print("Invalid input. Defaulting to 1 test set.")

    # --- Added: Create the data subdirectory if it doesn't exist ---
    if WRITE_TO_FILES:
        try:
            os.makedirs(DATA_SUBDIR, exist_ok=True) # Creates directory, no error if exists
            print(f"Ensured directory '{DATA_SUBDIR}' exists.")
        except OSError as e:
            print(f"Error creating directory {DATA_SUBDIR}: {e}", file=sys.stderr)
            print("Will attempt to write files to the current directory instead.")
            # Optionally, you could exit here or set WRITE_TO_FILES to False
            # For now, it will just try to write to the current dir if creation fails
    # --- End Added Section ---


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
            # --- Modified: Construct the full path including the subdirectory ---
            base_filename = f"testcase_{i}.txt"
            filepath = os.path.join(DATA_SUBDIR, base_filename) # Use os.path.join
            # --- End Modification ---
            try:
                # Use the full filepath here
                with open(filepath, 'w') as f:
                    for request in test_case:
                        f.write(request + '\n')
                # Report the correct path
                print(f"Test Set {i} written to {filepath}")
            except IOError as e:
                print(f"Error writing Test Set {i} to file {filepath}: {e}", file=sys.stderr)

        if PRINT_TO_CONSOLE or WRITE_TO_FILES:
            print() # Add a blank line between sets output info

    print("========================================")
    print("Data generation complete.")

if __name__ == "__main__":
    main()