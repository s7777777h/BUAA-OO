import random
import os
import string

# --- 配置常量 ---
MODE_PUBLIC = 's'
MODE_MUTUAL = 'm'

MAX_INSTRUCTIONS = {
    MODE_PUBLIC: 10000,
    MODE_MUTUAL: 3000
}

MAX_PERSONS = {
    MODE_PUBLIC: 300,
    MODE_MUTUAL: 100
}

# 指令简称
COMMANDS = [
    "ap", "ar", "mr", "at", "dt", "att", "dft",
    "qv", "qci", "qts", "qtav", "qba", "ln"
]

# 可能需要特殊处理或有性能问题的指令
PERF_COMMANDS = ["qts", "qci"] # qci可能涉及图遍历
TAG_COMMANDS = ["at", "dt", "att", "dft", "qtav"]
REL_COMMANDS = ["ar", "mr", "qv", "qba"]
EXCEPTION_TARGET_COMMANDS = [
    "ap", "ar", "mr", "at", "dt", "att", "dft",
    "qv", "qci", "qtav", "qba"
]


# --- 状态维护变量 ---
persons = set()
person_details = {} # id -> {'name': str, 'age': int}
relations = set() # Store as tuple (min_id, max_id)
relation_values = {} # Store as tuple (min_id, max_id) -> value
person_tags = {} # person_id -> set of tag_ids
tag_members = {} # (person_id, tag_id) -> set of member_person_ids

current_instruction_count = 0
max_instr = 0
max_p = 0
mode = ''


# --- 辅助函数 ---
def generate_random_name(length=5):
    """生成随机名字"""
    return ''.join(random.choices(string.ascii_letters, k=length))

def generate_random_age():
    """生成随机年龄 (1-1999)"""
    return random.randint(1, 1999)

def generate_random_value():
    """生成随机关系值 (1-1999)"""
    return random.randint(1, 1999)

def generate_random_m_value():
    """生成随机修改值 (-200 - 2000)"""
    return random.randint(-200, 2000)

def generate_unique_id(existing_ids):
    """生成一个当前不存在的ID"""
    while True:
        # 扩展ID范围以减少碰撞，但仍在int范围内
        new_id = random.randint(-10000, 10000)
        if new_id not in existing_ids:
            return new_id

def get_random_existing_person():
    """随机获取一个已存在的Person ID"""
    if not persons:
        return None
    return random.choice(list(persons))

def get_two_random_existing_persons():
    """随机获取两个不同的已存在的Person ID"""
    if len(persons) < 2:
        return None, None
    p1 = random.choice(list(persons))
    p2 = random.choice(list(persons - {p1}))
    return p1, p2

def get_random_tag_for_person(person_id):
    """随机获取指定person拥有的一个tag ID"""
    if person_id not in person_tags or not person_tags[person_id]:
        return None
    return random.choice(list(person_tags[person_id]))

def get_random_member_for_tag(owner_id, tag_id):
     """随机获取指定tag的一个成员ID"""
     key = (owner_id, tag_id)
     if key not in tag_members or not tag_members[key]:
         return None
     return random.choice(list(tag_members[key]))


# --- 状态更新函数 ---
def add_person_state(pid, name, age):
    persons.add(pid)
    person_details[pid] = {'name': name, 'age': age}
    person_tags[pid] = set()

def add_relation_state(id1, id2, value):
    p1, p2 = min(id1, id2), max(id1, id2)
    relations.add((p1, p2))
    relation_values[(p1, p2)] = value

def modify_relation_state(id1, id2, m_value):
    p1, p2 = min(id1, id2), max(id1, id2)
    key = (p1, p2)
    if key in relation_values:
        new_value = relation_values[key] + m_value
        if new_value > 0:
            relation_values[key] = new_value
        else:
            # Relation deleted
            relations.discard(key)
            del relation_values[key]
            # Also need to remove from tags (simplified: just clear potential members for this pair)
            # This simplification might miss edge cases, but full tracking is complex
            for owner_id, tag_id in tag_members.keys():
                 if owner_id == id1:
                     tag_members.get((owner_id, tag_id), set()).discard(id2)
                 elif owner_id == id2:
                     tag_members.get((owner_id, tag_id), set()).discard(id1)


def add_tag_state(person_id, tag_id):
    if person_id in person_tags:
        person_tags[person_id].add(tag_id)
        tag_members[(person_id, tag_id)] = set() # Initialize member set

def del_tag_state(person_id, tag_id):
    if person_id in person_tags:
        person_tags[person_id].discard(tag_id)
        if (person_id, tag_id) in tag_members:
            del tag_members[(person_id, tag_id)]

def add_to_tag_state(person_id1, person_id2, tag_id):
    # person_id1 is added to person_id2's tag_id
    key = (person_id2, tag_id)
    if key in tag_members:
        # JML has size limit 999, simplified state doesn't track size perfectly
        tag_members[key].add(person_id1)

def del_from_tag_state(person_id1, person_id2, tag_id):
    # person_id1 is removed from person_id2's tag_id
    key = (person_id2, tag_id)
    if key in tag_members:
        tag_members[key].discard(person_id1)


# --- 指令生成策略 ---

def strategy_random(commands_list):
    """策略：完全随机生成指令"""
    if not commands_list:
        # If there are no commands to choose from, we can't generate anything
        return []
    command = random.choice(commands_list)
    # Avoid ln after the first instruction
    if current_instruction_count > 0 and command == "ln":
        command = random.choice([c for c in commands_list if c != "ln"])

    generated = []
    # --- Add Person ---
    if command == "ap":
        # Occasionally try adding duplicate ID for exception testing
        if random.random() < 0.1 and persons:
             pid = get_random_existing_person()
        else:
             pid = generate_unique_id(persons)

        if len(persons) < max_p: # Only add if below limit
            name = generate_random_name()
            age = generate_random_age()
            generated.append(f"ap {pid} {name} {age}")
            if pid not in persons: # Update state only on success
                 add_person_state(pid, name, age)
        else: # If limit reached, try another command
            return strategy_random([c for c in commands_list if c != "ap" and c!= "ln"])


    # --- Add Relation ---
    elif command == "ar":
        p1, p2 = get_two_random_existing_persons()
        if p1 is not None:
            val = generate_random_value()
            # Occasionally try adding existing relation for exception
            key = (min(p1, p2), max(p1, p2))
            is_existing = key in relations
            if not is_existing or random.random() < 0.1:
                generated.append(f"ar {p1} {p2} {val}")
                if not is_existing:
                    add_relation_state(p1, p2, val)
            # else: skip generating command if trying to avoid exception

    # --- Modify Relation ---
    elif command == "mr":
         if relations:
             p1, p2 = random.choice(list(relations)) # Get existing relation
             m_val = generate_random_m_value()
             generated.append(f"mr {p1} {p2} {m_val}")
             modify_relation_state(p1, p2, m_val)
         elif len(persons) >= 2 and random.random() < 0.2: # Try non-existing for exception
             p1, p2 = get_two_random_existing_persons()
             if p1 is not None:
                m_val = generate_random_m_value()
                generated.append(f"mr {p1} {p2} {m_val}")


    # --- Add Tag ---
    elif command == "at":
        p_id = get_random_existing_person()
        if p_id is not None:
            # Occasionally try adding duplicate tag for exception
            if random.random() < 0.1 and person_tags.get(p_id):
                 t_id = get_random_tag_for_person(p_id)
            else:
                 # Generate tag id unique *for this person*
                 existing_person_tags = person_tags.get(p_id, set())
                 t_id = generate_unique_id(existing_person_tags)

            generated.append(f"at {p_id} {t_id}")
            if t_id not in person_tags.get(p_id, set()):
                add_tag_state(p_id, t_id)

    # --- Delete Tag ---
    elif command == "dt":
        p_id = get_random_existing_person()
        if p_id is not None:
            t_id = get_random_tag_for_person(p_id)
            if t_id is not None: # Delete existing tag
                generated.append(f"dt {p_id} {t_id}")
                del_tag_state(p_id, t_id)
            elif random.random() < 0.2: # Try deleting non-existing for exception
                non_existing_tid = generate_unique_id(person_tags.get(p_id, set()))
                generated.append(f"dt {p_id} {non_existing_tid}")


    # --- Add Person To Tag ---
    elif command == "att":
        p2 = get_random_existing_person() # Tag owner
        if p2 is not None:
            t_id = get_random_tag_for_person(p2)
            if t_id is not None:
                 # Find p1 who is linked to p2
                 possible_p1s = set()
                 for r_p1, r_p2 in relations:
                     if r_p1 == p2:
                         possible_p1s.add(r_p2)
                     elif r_p2 == p2:
                         possible_p1s.add(r_p1)

                 # Also consider p1 == p2 for exception
                 if random.random() < 0.05:
                      p1 = p2
                 elif possible_p1s:
                      p1 = random.choice(list(possible_p1s))
                 else:
                      p1 = None # No one linked to p2

                 if p1 is not None:
                     # Try adding existing member for exception
                     is_member = p1 in tag_members.get((p2, t_id), set())
                     if not is_member or random.random() < 0.1:
                         generated.append(f"att {p1} {p2} {t_id}")
                         if not is_member:
                              add_to_tag_state(p1, p2, t_id)


    # --- Delete Person From Tag ---
    elif command == "dft":
        p2 = get_random_existing_person() # Tag owner
        if p2 is not None:
            t_id = get_random_tag_for_person(p2)
            if t_id is not None:
                 p1 = get_random_member_for_tag(p2, t_id) # Get existing member
                 if p1 is not None:
                     generated.append(f"dft {p1} {p2} {t_id}")
                     del_from_tag_state(p1, p2, t_id)
                 elif random.random() < 0.2 and persons: # Try non-member for exception
                     non_member_p1 = random.choice(list(persons - tag_members.get((p2, t_id), set())))
                     generated.append(f"dft {non_member_p1} {p2} {t_id}")


    # --- Query Value ---
    elif command == "qv":
        if relations: # Query existing relation
            p1, p2 = random.choice(list(relations))
            generated.append(f"qv {p1} {p2}")
        elif len(persons) >= 2 and random.random() < 0.2: # Try non-existing for exception
            p1, p2 = get_two_random_existing_persons()
            if p1 is not None:
                generated.append(f"qv {p1} {p2}")

    # --- Query Circle ---
    elif command == "qci":
        p1, p2 = get_two_random_existing_persons()
        if p1 is not None:
            generated.append(f"qci {p1} {p2}")

    # --- Query Triple Sum ---
    elif command == "qts":
         generated.append("qts") # Simple command

    # --- Query Tag Age Var ---
    elif command == "qtav":
        p_id = get_random_existing_person()
        if p_id is not None:
            t_id = get_random_tag_for_person(p_id)
            if t_id is not None: # Query existing tag
                generated.append(f"qtav {p_id} {t_id}")
            elif random.random() < 0.2: # Try non-existing tag for exception
                non_existing_tid = generate_unique_id(person_tags.get(p_id, set()))
                generated.append(f"qtav {p_id} {non_existing_tid}")


    # --- Query Best Acquaintance ---
    elif command == "qba":
        p_id = get_random_existing_person()
        if p_id is not None:
             generated.append(f"qba {p_id}")

    # --- Load Network ---
    elif command == "ln":
         # Only allowed as first instruction
         if current_instruction_count == 0 and len(persons) == 0:
             n = random.randint(1, min(max_p, 50)) # Limit initial load size
             if n > 0:
                 generated.append(f"ln {n}")
                 ln_ids = [generate_unique_id(persons | set(range(-n, n))) for _ in range(n)] # Generate n unique IDs
                 ln_names = [generate_random_name() for _ in range(n)]
                 ln_ages = [generate_random_age() for _ in range(n)]

                 generated.append(" ".join(map(str, ln_ids)))
                 generated.append(" ".join(ln_names))
                 generated.append(" ".join(map(str, ln_ages)))

                 # Add persons to state
                 for i in range(n):
                     add_person_state(ln_ids[i], ln_names[i], ln_ages[i])

                 # Generate relation matrix (lower triangle)
                 for i in range(n - 1): # Row i+1 (person ln_ids[i+1])
                     row_values = []
                     for j in range(i + 1): # Col j (person ln_ids[j])
                         # Decide whether to add a relation (e.g., 50% chance)
                         if random.random() < 0.5:
                             value = generate_random_value()
                             row_values.append(str(value))
                             # Add relation to state
                             add_relation_state(ln_ids[i+1], ln_ids[j], value)
                         else:
                             row_values.append("0")
                     generated.append(" ".join(row_values))
             # else: skip if n=0

    return generated


def strategy_qts_heavy(commands_list):
    """策略：生成大量 qts 指令，可能插入少量 ar/mr"""
    if len(persons) < 3 or random.random() < 0.1: # Need at least 3 people for triangles
        # Add people and relations first
        generated = []
        if len(persons) < max_p:
            pid = generate_unique_id(persons)
            name = generate_random_name()
            age = generate_random_age()
            generated.append(f"ap {pid} {name} {age}")
            add_person_state(pid, name, age)

        if len(persons) >= 2:
            p1, p2 = get_two_random_existing_persons()
            key = (min(p1, p2), max(p1, p2))
            if p1 is not None and key not in relations:
                val = generate_random_value()
                generated.append(f"ar {p1} {p2} {val}")
                add_relation_state(p1, p2, val)
        return generated
    else:
        # Primarily generate qts
        if random.random() < 0.9:
            return ["qts"]
        else: # Occasionally add/modify relations to change triangles
             choice = random.choice(["ar", "mr"])
             if choice == "ar" and len(persons) >= 2:
                 p1, p2 = get_two_random_existing_persons()
                 key = (min(p1, p2), max(p1, p2))
                 if p1 is not None and key not in relations:
                     val = generate_random_value()
                     add_relation_state(p1, p2, val)
                     return [f"ar {p1} {p2} {val}"]
             elif choice == "mr" and relations:
                  p1, p2 = random.choice(list(relations))
                  m_val = generate_random_m_value()
                  modify_relation_state(p1, p2, m_val)
                  return [f"mr {p1} {p2} {m_val}"]
    return []


def strategy_exception_focus(commands_list):
    """策略：尝试生成导致异常的指令"""
    target_command = random.choice(EXCEPTION_TARGET_COMMANDS)
    generated = []

    # --- EqualPersonIdException (ap) ---
    if target_command == "ap" and persons:
        pid = get_random_existing_person()
        name = generate_random_name()
        age = generate_random_age()
        generated.append(f"ap {pid} {name} {age}")

    # --- PersonIdNotFoundException ---
    elif target_command in ["ar", "mr", "qv", "qci", "at", "att", "dft", "dt", "qtav", "qba"]:
        non_existing_id1 = generate_unique_id(persons)
        if target_command in ["ar", "mr", "qv", "qci", "att", "dft"]:
            existing_id2 = get_random_existing_person()
            if existing_id2 is not None:
                 args = [non_existing_id1, existing_id2]
                 if target_command == "ar": args.append(generate_random_value())
                 if target_command == "mr": args.append(generate_random_m_value())
                 if target_command in ["att", "dft"]: args.append(random.randint(0,5)) # Dummy tag id
                 generated.append(f"{target_command} {' '.join(map(str, args))}")
            # Could also try existing_id1, non_existing_id2
        elif target_command in ["at", "dt", "qtav", "qba"]:
             args = [non_existing_id1]
             if target_command in ["at", "dt", "qtav"]: args.append(random.randint(0,5)) # Dummy tag id
             generated.append(f"{target_command} {' '.join(map(str, args))}")

    # --- EqualRelationException (ar) ---
    elif target_command == "ar" and relations:
        p1, p2 = random.choice(list(relations))
        val = generate_random_value()
        generated.append(f"ar {p1} {p2} {val}")

    # --- RelationNotFoundException (mr, qv, dft for non-linked) ---
    elif target_command in ["mr", "qv", "dft"] and len(persons) >= 2:
         p1, p2 = get_two_random_existing_persons()
         key = (min(p1,p2), max(p1,p2))
         if p1 is not None and key not in relations:
             args = [p1, p2]
             if target_command == "mr": args.append(generate_random_m_value())
             if target_command == "dft": args.append(random.randint(0,5)) # Dummy tag id
             generated.append(f"{target_command} {' '.join(map(str, args))}")


    # --- EqualTagIdException (at) ---
    elif target_command == "at":
         p_id = get_random_existing_person()
         if p_id is not None:
             t_id = get_random_tag_for_person(p_id)
             if t_id is not None:
                 generated.append(f"at {p_id} {t_id}")

    # --- TagIdNotFoundException (att, qtav, dft, dt) ---
    elif target_command in ["att", "qtav", "dft", "dt"]:
         p_id = get_random_existing_person()
         if p_id is not None:
             non_existing_tid = generate_unique_id(person_tags.get(p_id, set()))
             args = []
             if target_command in ["att", "dft"]: # Need another person
                 p_other = get_random_existing_person()
                 if p_other is not None:
                      if target_command == "att": args = [p_other, p_id, non_existing_tid]
                      else: args = [p_other, p_id, non_existing_tid] # p1, p2, tagid
             elif target_command in ["qtav", "dt"]:
                 args = [p_id, non_existing_tid]

             if args:
                 generated.append(f"{target_command} {' '.join(map(str, args))}")

    # --- EqualPersonIdException (att - person1==person2 or person1 already in tag) ---
    elif target_command == "att":
        p2 = get_random_existing_person() # Tag owner
        if p2 is not None:
            t_id = get_random_tag_for_person(p2)
            if t_id is not None:
                 # Case 1: p1 == p2
                 if random.random() < 0.5:
                      p1 = p2
                      generated.append(f"att {p1} {p2} {t_id}")
                 # Case 2: p1 already in tag
                 else:
                      p1 = get_random_member_for_tag(p2, t_id)
                      if p1 is not None:
                           generated.append(f"att {p1} {p2} {t_id}")


    # --- AcquaintanceNotFoundException (qba) ---
    elif target_command == "qba":
         # Find person with no relations
         lonely_person = None
         for p in persons:
             is_lonely = True
             for r1, r2 in relations:
                 if p == r1 or p == r2:
                     is_lonely = False
                     break
             if is_lonely:
                 lonely_person = p
                 break
         if lonely_person is not None:
              generated.append(f"qba {lonely_person}")
         elif persons: # If no truly lonely person, try one recently added
             generated.append(f"qba {random.choice(list(persons))}") # May or may not trigger

    # If no specific exception case generated, fall back to random
    if not generated:
        return strategy_random(commands_list)
    return generated


def strategy_tag_focus(commands_list):
    """策略：重点生成与Tag相关的操作"""
    # Increase probability of tag-related commands
    possible_cmds = TAG_COMMANDS + ["ap", "ar"] # Need persons and relations for tags
    command = random.choice(possible_cmds)

    # Use the logic from strategy_random for the chosen command
    # This reuses the generation logic but biases the command selection
    temp_list = [command] if command != "ln" else ["ap"] # Ensure ln is not chosen here
    return strategy_random(temp_list)


def strategy_load_network(commands_list):
     """策略：使用ln指令（只能在开头）"""
     if current_instruction_count == 0 and len(persons) == 0:
         return strategy_random(["ln"]) # Force ln generation
     else:
         return strategy_random([c for c in commands_list if c != "ln"]) # Fallback if not first


# --- 主生成逻辑 ---
def generate_test_case(filename, mode_choice):
    global persons, person_details, relations, relation_values, person_tags, tag_members
    global current_instruction_count, max_instr, max_p, mode

    # Reset state for new file
    persons = set()
    person_details = {}
    relations = set()
    relation_values = {}
    person_tags = {}
    tag_members = {}
    current_instruction_count = 0

    mode = mode_choice
    max_instr = MAX_INSTRUCTIONS[mode]
    max_p = MAX_PERSONS[mode]

    # Define strategies
    strategies = [
        strategy_random,
        strategy_qts_heavy,
        strategy_exception_focus,
        strategy_tag_focus,
        strategy_load_network, # Has internal check for instruction 0
        strategy_random # Add random again to increase its weight
    ]
    # Allowed commands list (remove lnl)
    allowed_commands = [c for c in COMMANDS if c != "lnl"]

    with open(filename, 'w') as f:
        while current_instruction_count < max_instr:
            # Choose a strategy
            chosen_strategy = random.choice(strategies)

            # Generate instruction(s) using the strategy
            generated_lines = chosen_strategy(allowed_commands)

            # Write generated lines to file and update count
            lines_written = 0
            for line in generated_lines:
                 if current_instruction_count < max_instr:
                     f.write(line + '\n')
                     # Special handling for 'ln' which consumes multiple lines conceptually
                     if line.startswith("ln "):
                         n = int(line.split()[1])
                         # Account for the n IDs, n names, n ages, n-1 relation rows
                         # This count is approximate for instruction limit purposes
                         current_instruction_count += (1 + 3 + (n-1 if n>0 else 0))
                     else:
                         current_instruction_count += 1
                     lines_written += 1
                 else:
                     break # Stop if limit reached mid-generation

            # If a strategy generated nothing useful (e.g., couldn't find valid targets)
            # or we hit the limit, break or continue
            if lines_written == 0 and current_instruction_count < max_instr:
                 # Try a fallback strategy if one failed to produce output
                 fallback_lines = strategy_random(allowed_commands)
                 for line in fallback_lines:
                     if current_instruction_count < max_instr:
                         f.write(line + '\n')
                         if line.startswith("ln "):
                             n = int(line.split()[1])
                             current_instruction_count += (1 + 3 + (n-1 if n>0 else 0))
                         else:
                            current_instruction_count += 1
                     else:
                         break

            if current_instruction_count >= max_instr:
                break

    print(f"Generated {filename} with {current_instruction_count} instructions.")


# --- Main Execution ---
if __name__ == "__main__":
    while True:
        mode_input = input(f"choose mode: strong({MODE_PUBLIC}) or mutual ({MODE_MUTUAL}): ").lower()
        if mode_input in [MODE_PUBLIC, MODE_MUTUAL]:
            break
        else:
            print("invalid input,please enter 's' or 'm'.")

    while True:
        try:
            num_files = int(input("Please enter the number of testcases you want to generate: "))
            if num_files > 0:
                break
            else:
                print("Please enter an integer greater than 0.")
        except ValueError:
            print("Please enter an integer greater than 0.")

    # 创建 data 文件夹
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Creating folder: data")

    # 生成文件
    for i in range(1, num_files + 1):
        filepath = os.path.join("data", f"testcase_{i}.txt")
        generate_test_case(filepath, mode_input)

    print("Data generator finished")