import random
import os
import string
import sys
import time # 引入 time 模块

# --- 配置常量 (Configuration Constants) ---
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

# --- 指令列表 (Command Lists) ---
HW9_COMMANDS = [
    "ap", "ar", "mr", "at", "dt", "att", "dft",
    "qv", "qci", "qts", "qtav", "qba", "ln"
]
HW10_NEW_COMMANDS = [
    "coa", "doa", "ca", "da", "foa",
    "qsp", "qbc", "qra", "qtvs", "qcs"
]
COMMANDS = HW9_COMMANDS + HW10_NEW_COMMANDS

# --- 指令分类 (Command Categories for Strategies) ---
PERF_QUERY_COMMANDS = ["qts", "qci", "qsp", "qcs", "qtvs", "qbc", "qra", "qba", "qv"]
TAG_COMMANDS = ["at", "dt", "att", "dft", "qtav", "qtvs"]
REL_COMMANDS = ["ar", "mr", "qv", "qba", "qci", "qsp", "qts", "qcs"]
ACCOUNT_ARTICLE_COMMANDS = ["coa", "doa", "ca", "da", "foa", "qbc", "qra"]
EXCEPTION_TARGET_COMMANDS = [
    "ap", "ar", "mr", "at", "dt", "att", "dft", "qv", "qci", "qtav", "qba",
    "coa", "doa", "ca", "da", "foa"
]
STATE_BUILDING_COMMANDS = ["ap", "coa", "ar", "ln"] # ln 也是状态建立

# --- 状态变量 (State Variables) ---
persons = set(); person_details = {}; relations = set(); relation_values = {}
person_tags = {}; tag_members = {}; official_accounts = set(); account_details = {}
followers = {}; articles = set(); article_details = {}; account_articles = {}
contributions = {}

# --- 运行时变量 (Runtime variables) ---
instructions_generated_total = 0
max_instr = 0
max_p = 0
mode = ''
current_file_instruction_count = 0

# --- 辅助函数 (Helper Functions) ---
def generate_random_string(length=5): return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
def generate_random_age(): return random.randint(1, 1999)
def generate_random_value(): return random.randint(1, 1999)
def generate_random_m_value(): return random.randint(-200, 2000)
def generate_unique_id(existing_ids, min_val=-10000, max_val=10000):
    attempts=0; max_attempts=2000
    while attempts<max_attempts:
        new_id=random.randint(min_val,max_val)
        if new_id not in existing_ids: return new_id
        attempts+=1
    print(f"Warning: Could not generate unique ID easily in range [{min_val}, {max_val}]. Using max+1 fallback.", file=sys.stderr)
    fallback_id=0
    if existing_ids:
        try:
            numeric_ids={id_ for id_ in existing_ids if isinstance(id_,(int, float))}
            if numeric_ids: fallback_id=max(numeric_ids)+1
            else: fallback_id=min_val
        except ValueError: fallback_id=random.randint(max_val+1,max_val+1000)
    else: fallback_id=min_val
    while fallback_id in existing_ids: fallback_id+=1
    return fallback_id
def get_random_existing_person():
    if not persons: return None
    return random.choice(tuple(persons))
def get_two_random_existing_persons():
    if len(persons)<2: return None, None
    try: return random.sample(persons,2)
    except: return None, None
def get_random_tag_for_person(person_id):
    tags_set=person_tags.get(person_id)
    if not tags_set: return None
    return random.choice(tuple(tags_set))
def get_random_member_for_tag(owner_id,tag_id):
    members_set=tag_members.get((owner_id,tag_id))
    if not members_set: return None
    return random.choice(tuple(members_set))
def get_random_existing_account():
    if not official_accounts: return None
    return random.choice(tuple(official_accounts))
def get_random_existing_article():
    if not articles: return None
    return random.choice(tuple(articles))
def get_random_follower(account_id):
    follower_set=followers.get(account_id)
    if not follower_set: return None
    return random.choice(tuple(follower_set))
def get_random_contributor(account_id):
    contrib_dict=contributions.get(account_id)
    if not contrib_dict: return None
    contributor_list=list(contrib_dict.keys())
    if not contributor_list: return None
    return random.choice(contributor_list)

# --- 状态更新函数 (State Update Functions) ---
def add_person_state(pid, name, age):
    if pid in persons: return
    persons.add(pid); person_details[pid] = {'name': name, 'age': age}; person_tags[pid] = set()
def add_relation_state(id1, id2, value):
    p1, p2 = min(id1, id2), max(id1, id2)
    if (p1, p2) in relations: return
    relations.add((p1, p2)); relation_values[(p1, p2)] = value
def modify_relation_state(id1, id2, m_value):
    p1, p2 = min(id1, id2), max(id1, id2); key = (p1, p2)
    if key in relation_values:
        new_value = relation_values[key] + m_value
        if new_value > 0: relation_values[key] = new_value
        else: relations.discard(key); relation_values.pop(key, None)
def add_tag_state(person_id, tag_id):
    if person_id not in person_tags: return
    person_tags[person_id].add(tag_id); tag_members.setdefault((person_id, tag_id), set())
def del_tag_state(person_id, tag_id):
    if person_id in person_tags: person_tags[person_id].discard(tag_id); tag_members.pop((person_id, tag_id), None)
def add_to_tag_state(person_id1, person_id2, tag_id):
    key = (person_id2, tag_id)
    if person_id2 in person_tags and tag_id in person_tags[person_id2]: tag_members.setdefault(key, set()).add(person_id1)
def del_from_tag_state(person_id1, person_id2, tag_id):
    key = (person_id2, tag_id)
    if key in tag_members: tag_members[key].discard(person_id1)
def add_account_state(acc_id, owner_id, name):
    if acc_id in official_accounts: return
    official_accounts.add(acc_id); account_details[acc_id] = {'owner': owner_id, 'name': name}; followers[acc_id] = set(); account_articles[acc_id] = set(); contributions[acc_id] = {}
def del_account_state(acc_id):
    if acc_id not in official_accounts: return
    articles_to_delete = list(account_articles.get(acc_id, set()))
    for art_id in articles_to_delete: del_article_state(art_id)
    official_accounts.discard(acc_id); account_details.pop(acc_id, None); followers.pop(acc_id, None); account_articles.pop(acc_id, None); contributions.pop(acc_id, None)
def add_article_state(art_id, acc_id, person_id, name):
    if art_id in articles: return
    if acc_id not in official_accounts: return
    articles.add(art_id); article_details[art_id] = {'account': acc_id, 'contributor': person_id, 'name': name}
    account_articles.setdefault(acc_id, set()).add(art_id)
    contrib_for_acc = contributions.setdefault(acc_id, {}); contrib_for_acc[person_id] = contrib_for_acc.get(person_id, 0) + 1
def del_article_state(art_id):
    if art_id not in articles: return
    details = article_details.pop(art_id, None)
    if not details: articles.discard(art_id); return
    acc_id = details['account']; person_id = details['contributor']
    articles.discard(art_id)
    if acc_id in account_articles: account_articles[acc_id].discard(art_id)
    if acc_id in contributions and person_id in contributions[acc_id]:
        contributions[acc_id][person_id] -= 1
        if contributions[acc_id][person_id] <= 0:
            contributions[acc_id].pop(person_id, None)
            if not contributions[acc_id]: contributions.pop(acc_id, None)
def add_follower_state(person_id, acc_id):
    if acc_id in official_accounts: followers.setdefault(acc_id, set()).add(person_id)


# --- 辅助函数: 尝试生成参数 (Helper: Try generating params) ---
def _try_generate_command_params(command):
    """尝试为单个命令生成参数。成功则返回指令列表，否则返回 []。"""
    generated = []
    # --- Add Person ---
    if command == "ap":
        if len(persons) < max_p:
            pid_to_add = generate_unique_id(persons)
            name = generate_random_string(); age = generate_random_age()
            generated.append(f"ap {pid_to_add} {name} {age}")
            add_person_state(pid_to_add, name, age)
    # --- Add Relation ---
    elif command == "ar":
        if len(persons) >= 2:
            p1, p2 = get_two_random_existing_persons()
            if p1 is not None: # Check if sample returned valid persons
                key = (min(p1, p2), max(p1, p2))
                if key not in relations:
                    val = generate_random_value()
                    generated.append(f"ar {p1} {p2} {val}")
                    add_relation_state(p1, p2, val)
    # --- Modify Relation ---
    elif command == "mr":
        if relations:
             p1, p2 = random.choice(list(relations))
             m_val = generate_random_m_value()
             generated.append(f"mr {p1} {p2} {m_val}")
             modify_relation_state(p1, p2, m_val)
    # --- Add Tag ---
    elif command == "at":
        p_id = get_random_existing_person()
        if p_id is not None:
            existing_person_tags = person_tags.get(p_id, set())
            t_id = generate_unique_id(existing_person_tags, -500, 500)
            generated.append(f"at {p_id} {t_id}")
            add_tag_state(p_id, t_id)
    # --- Delete Tag ---
    elif command == "dt":
        p_id = get_random_existing_person()
        if p_id is not None:
            t_id = get_random_tag_for_person(p_id)
            if t_id is not None:
                generated.append(f"dt {p_id} {t_id}")
                del_tag_state(p_id, t_id)
    # --- Add Person To Tag ---
    elif command == "att":
        # Need p1, p2, t_id, link(p1,p2), p2 has t_id, p1 not in tag
        p2 = get_random_existing_person()
        if p2 is not None:
            t_id = get_random_tag_for_person(p2)
            if t_id is not None:
                p1 = get_random_existing_person()
                if p1 is not None and p1 != p2:
                    key = (min(p1, p2), max(p1, p2))
                    if key in relations and p1 not in tag_members.get((p2, t_id), set()):
                        generated.append(f"att {p1} {p2} {t_id}")
                        add_to_tag_state(p1, p2, t_id)
    # --- Delete Person From Tag ---
    elif command == "dft":
        # Need p2 has t_id, p1 in tag
        p2 = get_random_existing_person()
        if p2 is not None:
            t_id = get_random_tag_for_person(p2)
            if t_id is not None:
                 p1 = get_random_member_for_tag(p2, t_id)
                 if p1 is not None:
                     generated.append(f"dft {p1} {p2} {t_id}")
                     del_from_tag_state(p1, p2, t_id)

    # ===================== BUG FIX AREA START =====================
    # --- Query Value ---
    elif command == "qv":
        if relations: # Case 1: Relation exists
            p1, p2 = random.choice(list(relations))
            generated.append(f"qv {p1} {p2}")
        elif len(persons) >= 2 : # Case 2: Try querying non-existent link
            p1_try, p2_try = get_two_random_existing_persons()
            if p1_try is not None: # Check if we got two persons
                 generated.append(f"qv {p1_try} {p2_try}")
        # Case 3: Not enough people or no relations -> generates nothing
    # --- Query Circle ---
    elif command == "qci":
        if len(persons) >= 2:
            p1_try, p2_try = get_two_random_existing_persons()
            if p1_try is not None: # Check if we got two persons
                generated.append(f"qci {p1_try} {p2_try}")
    # --- Query Shortest Path ---
    elif command == "qsp":
        if len(persons) >= 2:
            p1_try, p2_try = get_two_random_existing_persons()
            if p1_try is not None: # Check if we got two persons
                generated.append(f"qsp {p1_try} {p2_try}")
    # ===================== BUG FIX AREA END =====================

    # --- Query Triple Sum ---
    elif command == "qts": generated.append("qts")
    # --- Query Tag Age Var ---
    elif command == "qtav":
        p_id = get_random_existing_person()
        if p_id is not None:
            t_id = get_random_tag_for_person(p_id)
            if t_id is not None: generated.append(f"qtav {p_id} {t_id}")
    # --- Query Best Acquaintance ---
    elif command == "qba":
        p_id = get_random_existing_person()
        if p_id is not None: generated.append(f"qba {p_id}")
    # --- Create Official Account ---
    elif command == "coa":
        p_id = get_random_existing_person()
        if p_id is not None:
            acc_id = generate_unique_id(official_accounts); acc_name = generate_random_string(10)
            generated.append(f"coa {p_id} {acc_id} {acc_name}"); add_account_state(acc_id, p_id, acc_name)
    # --- Delete Official Account ---
    elif command == "doa":
        acc_id = get_random_existing_account()
        if acc_id is not None:
            owner_id = account_details.get(acc_id, {}).get('owner')
            if owner_id is not None:
                generated.append(f"doa {owner_id} {acc_id}"); del_account_state(acc_id)
    # --- Contribute Article ---
    elif command == "ca":
        acc_id = get_random_existing_account(); p_id = get_random_existing_person()
        if acc_id is not None and p_id is not None:
            art_id = generate_unique_id(articles); art_name = generate_random_string(15)
            generated.append(f"ca {p_id} {acc_id} {art_id} {art_name}"); add_article_state(art_id, acc_id, p_id, art_name)
    # --- Delete Article ---
    elif command == "da":
        art_id = get_random_existing_article()
        if art_id is not None:
            details = article_details.get(art_id)
            if details:
                acc_id = details['account']; contributor_id = details['contributor']; owner_id = account_details.get(acc_id, {}).get('owner')
                if owner_id is not None:
                    p_id_to_use = random.choice([contributor_id, owner_id]) if owner_id != contributor_id else owner_id
                    generated.append(f"da {p_id_to_use} {acc_id} {art_id}"); del_article_state(art_id)
    # --- Follow Official Account ---
    elif command == "foa":
        p_id = get_random_existing_person(); acc_id = get_random_existing_account()
        if p_id is not None and acc_id is not None:
             if p_id not in followers.get(acc_id, set()):
                 generated.append(f"foa {p_id} {acc_id}"); add_follower_state(p_id, acc_id)
    # --- Query Best Contributor ---
    elif command == "qbc":
        acc_id = get_random_existing_account()
        if acc_id is not None: generated.append(f"qbc {acc_id}")
    # --- Query Received Articles ---
    elif command == "qra":
        p_id = get_random_existing_person()
        if p_id is not None: generated.append(f"qra {p_id}")
    # --- Query Tag Value Sum ---
    elif command == "qtvs":
        p_id = get_random_existing_person()
        if p_id is not None:
            t_id = get_random_tag_for_person(p_id)
            if t_id is not None: generated.append(f"qtvs {p_id} {t_id}")
    # --- Query Couple Sum ---
    elif command == "qcs": generated.append("qcs")
    # --- Load Network ---
    elif command == "ln":
        n = random.randint(1, min(max_p, 50))
        if n > 0:
            generated.append(f"ln {n}"); ln_ids = [generate_unique_id(persons|set(range(-n*2, n*2)), -20000, 20000) for _ in range(n)]
            ln_names=[generate_random_string() for _ in range(n)]; ln_ages=[generate_random_age() for _ in range(n)]
            generated.append(" ".join(map(str, ln_ids))); generated.append(" ".join(ln_names)); generated.append(" ".join(map(str, ln_ages)))
            for i in range(n): add_person_state(ln_ids[i], ln_names[i], ln_ages[i])
            for i in range(n - 1):
                row_values=[];
                for j in range(i + 1):
                    if random.random()<0.5: value=generate_random_value(); row_values.append(str(value)); add_relation_state(ln_ids[i+1], ln_ids[j], value)
                    else: row_values.append("0")
                generated.append(" ".join(row_values))

    return generated

# --- 健壮的随机策略 (Robust Random Strategy) ---
def strategy_random(commands_list):
    """策略：持续随机选择并尝试生成指令，直到成功一个或达到尝试上限。"""
    if not commands_list: return []

    max_tries = len(commands_list) * 3 + 10 # 增加尝试次数
    tries = 0
    while tries < max_tries:
        command = random.choice(commands_list)
        generated_lines = _try_generate_command_params(command)
        if generated_lines:
            return generated_lines # 成功则返回
        tries += 1

    # 尝试次数耗尽仍失败
    # print(f"Debug: strategy_random exceeded max_tries ({max_tries}) without success.", file=sys.stderr)
    return []

# --- 其他策略 (Other Strategies) ---
def strategy_query_heavy(commands_list):
    """策略：优先尝试生成查询指令。"""
    preferred_cmds = [cmd for cmd in PERF_QUERY_COMMANDS if cmd in commands_list]
    if preferred_cmds:
        # 尝试生成优先指令，如果失败则 strategy_random 返回空
        result = strategy_random(preferred_cmds) # 调用健壮版 random
        if result: return result
    # 如果优先指令失败或没有优先指令，进行全局随机尝试
    return strategy_random(commands_list) # 调用健壮版 random

def strategy_account_focus(commands_list):
    """策略：优先尝试生成账号和文章相关指令。"""
    preferred_cmds = [cmd for cmd in ACCOUNT_ARTICLE_COMMANDS if cmd in commands_list]
    if preferred_cmds:
        result = strategy_random(preferred_cmds) # 调用健壮版 random
        if result: return result
    return strategy_random(commands_list) # 调用健壮版 random

def strategy_exception_focus(commands_list):
    """策略：尝试生成一个可能导致异常的指令，如果失败则回退到随机。"""
    possible_targets = [cmd for cmd in EXCEPTION_TARGET_COMMANDS if cmd in commands_list]
    if not possible_targets: return strategy_random(commands_list) # 回退
    target_command = random.choice(possible_targets)

    generated = [] # 初始化为空列表

    # --- 开始修正 ---
    if target_command == "ap" and persons: # EqualPersonIdException
        existing_pid = get_random_existing_person()
        if existing_pid is not None: # 确保成功获取到 ID
            name = generate_random_string()
            age = generate_random_age()
            # 使用获取到的 existing_pid 来生成 ap 指令，目的是触发异常
            generated.append(f"ap {existing_pid} {name} {age}")
        # 如果 persons 非空但无法获取 existing_pid (理论上不应发生)，则 generated 保持为空

    elif target_command in ["ar", "mr", "qv", "qci", "at", "att", "dft", "dt", "qtav", "qba", "coa", "doa", "ca", "da", "foa", "qra", "qtvs"]: # PersonIdNotFoundException
        non_existing_pid = generate_unique_id(persons)
        existing_pid = get_random_existing_person()
        existing_aid = get_random_existing_account()
        existing_tid = get_random_tag_for_person(existing_pid) or 0 if existing_pid else 0
        existing_artid = get_random_existing_article()

        # ... (生成各种指令，尝试使用 non_existing_pid - 这部分逻辑不变) ...
        if target_command in ["ar", "mr", "qv", "qci"] and existing_pid:
             args = [non_existing_pid, existing_pid]
             if target_command == "ar": args.append(generate_random_value())
             if target_command == "mr": args.append(generate_random_m_value())
             generated.append(f"{target_command} {' '.join(map(str, args))}")
        elif target_command in ["at", "dt", "qtav", "qba", "qra", "qtvs"]:
             generated.append(f"{target_command} {non_existing_pid}" + (f" {existing_tid}" if target_command in ["at", "dt", "qtav", "qtvs"] else ""))
        elif target_command == "coa":
             generated.append(f"coa {non_existing_pid} {generate_unique_id(official_accounts)} {generate_random_string()}")
        elif target_command in ["att", "dft"] and existing_pid:
             generated.append(f"{target_command} {non_existing_pid} {existing_pid} {existing_tid}")
        elif target_command in ["doa", "ca", "da", "foa"]:
            if target_command == "doa" and existing_aid: generated.append(f"doa {non_existing_pid} {existing_aid}")
            elif target_command == "ca" and existing_aid: generated.append(f"ca {non_existing_pid} {existing_aid} {generate_unique_id(articles)} {generate_random_string()}")
            elif target_command == "da" and existing_aid and existing_artid: generated.append(f"da {non_existing_pid} {existing_aid} {existing_artid}")
            elif target_command == "foa" and existing_aid: generated.append(f"foa {non_existing_pid} {existing_aid}")

    # ... (其他 target_command 的 elif 块保持不变) ...
    elif target_command == "ar" and relations:
        p1, p2 = random.choice(list(relations)); val = generate_random_value(); generated.append(f"ar {p1} {p2} {val}")
    # ... (省略其他 elif 块) ...
    elif target_command == "foa":
        p_id = get_random_existing_person();
        if p_id is None: return [] # Need person
        choice = random.random()
        if choice < 0.5: generated.append(f"foa {p_id} {generate_unique_id(official_accounts)}")
        elif official_accounts:
            acc_id = get_random_existing_account()
            if acc_id:
                follower_id = get_random_follower(acc_id)
                if follower_id is not None: generated.append(f"foa {follower_id} {acc_id}")


    # --- 结束修正 ---
    # 最后的错误 if 检查已被移除

    # 如果这个策略未能生成特定的异常指令
    if not generated:
        # print(f"Debug: Exception strategy for {target_command} failed, falling back.")
        return strategy_random(commands_list) # 回退到健壮的随机
    return generated # 返回成功生成的异常指令

def strategy_tag_focus(commands_list):
    """策略：优先尝试生成标签相关指令。"""
    preferred_cmds = [cmd for cmd in TAG_COMMANDS if cmd in commands_list]
    if preferred_cmds:
        result = strategy_random(preferred_cmds) # 调用健壮版 random
        if result: return result
    return strategy_random(commands_list) # 调用健壮版 random

def strategy_load_network(commands_list):
     """策略：尝试生成 ln 指令（仅在开头）。"""
     global current_file_instruction_count
     if current_file_instruction_count == 0 and 'ln' in commands_list:
         return _try_generate_command_params('ln')
     else:
         return [] # 非开头则此策略无效

# --- 主生成逻辑 (Main Generation Logic) ---
def generate_test_case(filename_prefix, mode_choice, strategy_func):
    """生成单个测试用例文件，文件名包含策略名"""
    global persons, person_details, relations, relation_values, person_tags, tag_members
    global official_accounts, account_details, followers, articles, article_details, account_articles, contributions
    global max_instr, max_p, mode
    global current_file_instruction_count # 使用文件级计数器

    # 重置状态 (Reset state)
    persons.clear(); person_details.clear(); relations.clear(); relation_values.clear()
    person_tags.clear(); tag_members.clear()
    official_accounts.clear(); account_details.clear(); followers.clear(); articles.clear()
    article_details.clear(); account_articles.clear(); contributions.clear()
    current_file_instruction_count = 0 # 重置文件级计数器

    mode = mode_choice
    max_instr = MAX_INSTRUCTIONS[mode]
    max_p = MAX_PERSONS[mode]

    allowed_commands = [c for c in COMMANDS if c != "lnl"]

    strategy_name = strategy_func.__name__.replace("strategy_", "")
    filename = f"{filename_prefix}_{strategy_name}.txt"
    filepath = os.path.join("data", filename)

    print(f"Generating {filename} using primary strategy {strategy_name}...")

    # 打开文件准备写入
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            while current_file_instruction_count < max_instr:
                # --- 获取当前可用指令 ---
                current_allowed = [cmd for cmd in allowed_commands if not (cmd == 'ln' and current_file_instruction_count > 0)]
                if not current_allowed:
                    print(f"Warning: No commands possible at instruction {current_file_instruction_count} for {filename}.", file=sys.stderr)
                    break

                # --- 调用指定策略 ---
                generated_lines = strategy_func(current_allowed)

                # --- 处理生成结果 ---
                if generated_lines:
                    for line in generated_lines:
                        if current_file_instruction_count < max_instr:
                            f.write(line + '\n')
                            current_file_instruction_count += 1
                        else: break
                else: # 如果指定的策略（包括其内部回退）最终返回了 []
                      # 这通常意味着健壮的 strategy_random 也找不到可执行指令
                      print(f"Warning: Strategy {strategy_name} (incl. potential fallback) produced 0 lines. Stopping generation for {filename} at {current_file_instruction_count} instructions.", file=sys.stderr)
                      break # 无法继续生成

                # 检查是否达到上限
                if current_file_instruction_count >= max_instr:
                    break
    except IOError as e:
        print(f"Error opening or writing to file {filepath}: {e}", file=sys.stderr)
        return None # 返回 None 表示生成失败

    print(f"Generated {filepath} with {current_file_instruction_count} instructions.")
    return filename # 返回生成的文件名

# --- 主执行块 (Main Execution Block) ---
if __name__ == "__main__":
    while True:
        mode_input = input(f"Choose mode: Public Test ({MODE_PUBLIC}) or Mutual Test ({MODE_MUTUAL}): ").lower()
        if mode_input in [MODE_PUBLIC, MODE_MUTUAL]: break
        else: print("Invalid input. Please enter 's' or 'm'.")

    while True:
        try:
            num_files_total = int(input("How many test cases do you want to generate in total? "))
            if num_files_total > 0: break
            else: print("Please enter a positive integer.")
        except ValueError: print("Invalid input. Please enter a number.")

    if not os.path.exists("data"):
        os.makedirs("data"); print("Created directory: data")

    strategies_to_use = [
        strategy_load_network, strategy_random, strategy_account_focus,
        strategy_query_heavy, strategy_exception_focus, strategy_tag_focus,
        strategy_random, strategy_account_focus, strategy_query_heavy,
        strategy_random,
    ]
    num_strategies = len(strategies_to_use)

    generated_files_count = 0
    file_base_index = 1
    start_time_total = time.time() # 记录总开始时间

    while generated_files_count < num_files_total:
        start_time_file = time.time() # 记录单个文件开始时间
        current_strategy_func = strategies_to_use[generated_files_count % num_strategies]
        filename_prefix = f"testcase_{file_base_index}"
        try:
             generated_filename = generate_test_case(filename_prefix, mode_input, current_strategy_func)
             if generated_filename: # 检查是否成功生成文件
                 generated_files_count += 1
                 file_base_index += 1
                 end_time_file = time.time()
                 print(f"    Time taken for {generated_filename}: {end_time_file - start_time_file:.2f}s")
             else:
                 # 生成失败，可能需要处理
                 print(f"Error: Failed to generate file starting with {filename_prefix}.")
                 # 决定是否继续或停止
                 cont = input("File generation failed. Continue? (y/n): ").lower()
                 if cont != 'y': break
                 file_base_index += 1 # 增加索引避免下次冲突

        except Exception as e:
             import traceback
             print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
             print(f"Critical Error generating test case starting with {filename_prefix} using strategy {current_strategy_func.__name__}:", file=sys.stderr)
             traceback.print_exc(file=sys.stderr)
             print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n", file=sys.stderr)
             cont = input("A critical error occurred. Continue generating? (y/n): ").lower()
             if cont != 'y': break
             file_base_index += 1

    end_time_total = time.time()
    print(f"\nData generation finished. Generated {generated_files_count} files.")
    print(f"Total time taken: {end_time_total - start_time_total:.2f}s")