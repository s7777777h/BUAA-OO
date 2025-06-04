import random
import os
import string
import sys
import time
import math  # For potential calculations

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
HW11_NEW_COMMANDS = [
    "am", "aem", "arem", "afm", "sm", "sei", "dce",
    "qsv", "qrm", "qp", "qm"
]
COMMANDS = HW9_COMMANDS + HW10_NEW_COMMANDS + HW11_NEW_COMMANDS

# --- 指令分类 (Command Categories for Strategies) ---
QUERY_COMMANDS = ["qv", "qci", "qts", "qtav", "qba", "qsp", "qbc", "qra", "qtvs", "qcs", "qsv", "qrm", "qp", "qm"]
STATE_MODIFY_COMMANDS = ["mr", "dt", "att", "dft", "doa", "da", "sm", "dce"]
STATE_ADD_COMMANDS = ["ap", "ar", "at", "coa", "ca", "foa", "am", "aem", "arem", "afm", "sei", "ln"]
TAG_COMMANDS = ["at", "dt", "att", "dft", "qtav", "qtvs"]
REL_COMMANDS = ["ar", "mr", "qv", "qba", "qci", "qsp", "qts", "qcs"]  # For relation focus
ACCOUNT_ARTICLE_COMMANDS = ["coa", "doa", "ca", "da", "foa", "qbc", "qra", "afm"]  # Added afm
MESSAGE_COMMANDS = ["am", "aem", "arem", "afm", "sm", "sei", "dce", "qsv", "qrm", "qp", "qm"]
EXCEPTION_TARGET_COMMANDS = [  # Commands potentially causing exceptions (needs refinement)
    "ap", "ar", "mr", "at", "dt", "att", "dft", "qv", "qci", "qtav", "qba", "qsp",
    "coa", "doa", "ca", "da", "foa", "qbc", "qra", "qtvs", "qcs",
    "am", "aem", "arem", "afm", "sm", "sei", "dce", "qsv", "qrm", "qp", "qm"
]

# --- 状态变量 (State Variables) ---
# (State variables remain the same as the previous hw11 version)
persons = set()
person_details = {}  # {pid: {'name': str, 'age': int, 'social_value': int, 'money': int}}
relations = set()  # {(p1, p2) with p1 < p2}
relation_values = {}  # {(p1, p2): value}
person_tags = {}  # {pid: set_of_tag_ids}
tag_members = {}  # {(owner_pid, tag_id): set_of_member_pids}
official_accounts = set()
account_details = {}  # {acc_id: {'owner': pid, 'name': str}}
followers = {}  # {acc_id: set_of_follower_pids}
articles = set()  # art_id
article_details = {}  # {art_id: {'account': acc_id, 'contributor': pid, 'name': str}}
account_articles = {}  # {acc_id: set_of_art_ids}
contributions = {}  # {acc_id: {contrib_pid: count}}
network_messages_store = {}  # {msg_id: details_dict}
person_received_message_ids = {}  # {pid: list_of_msg_ids}
network_emoji_ids = set()  # Stored emoji IDs by 'sei'
network_emoji_heat = {}  # {emoji_id: heat_count}
next_message_id = 0

# --- 运行时变量 (Runtime variables) ---
instructions_generated_total = 0
max_instr = 0
max_p = 0
mode = ''
current_file_instruction_count = 0


# --- 辅助函数 (Helper Functions) ---
# (Helper functions remain the same as the previous hw11 version)
def generate_random_string(length=5): return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_age(): return random.randint(1, 1999)


def generate_random_value(): return random.randint(1, 1999)


def generate_random_m_value(): return random.randint(-200, 2000)


def generate_random_social_value_param(): return random.randint(-1000, 1000)


def generate_random_money_param(): return random.randint(0, 200)


def generate_random_message_delivery_type(): return random.randint(0, 1)


def generate_random_limit(): return random.randint(0, 100)


def generate_unique_id(existing_ids, min_val=-10000, max_val=10000):
    if not isinstance(existing_ids, set):
        try:
            existing_ids = set(existing_ids)
        except TypeError:
            temp_set = set()
            if isinstance(existing_ids, dict):
                temp_set.update(existing_ids.keys())
            elif isinstance(existing_ids, (list, tuple)):
                temp_set.update(existing_ids)
            else:
                print(f"Warning: generate_unique_id received unhandled type {type(existing_ids)}", file=sys.stderr)
            existing_ids = temp_set

    attempts = 0
    max_attempts = len(existing_ids) + 2000
    while attempts < max_attempts:
        new_id = random.randint(min_val, max_val)
        if new_id not in existing_ids: return new_id
        attempts += 1
    fallback_id = max_val + 1
    if existing_ids:
        numeric_ids = {id_ for id_ in existing_ids if isinstance(id_, (int, float))}
        if numeric_ids: fallback_id = max(numeric_ids) + 1
    while fallback_id in existing_ids: fallback_id += 1
    if fallback_id > max_val + 100000:
        print(f"Warning: Unique ID generation struggling significantly. Current fallback: {fallback_id}",
              file=sys.stderr)
    return fallback_id


def get_random_existing_person():
    if not persons: return None
    try:
        return random.choice(tuple(persons))
    except IndexError:
        return None


def get_two_random_existing_persons():
    if len(persons) < 2: return None, None
    try:
        return random.sample(list(persons), 2)
    except ValueError:
        return None, None


def get_random_tag_for_person(person_id):
    tags_set = person_tags.get(person_id)
    if not tags_set: return None
    try:
        return random.choice(tuple(tags_set))
    except IndexError:
        return None


def get_random_member_for_tag(owner_id, tag_id):
    members_set = tag_members.get((owner_id, tag_id))
    if not members_set: return None
    try:
        return random.choice(tuple(members_set))
    except IndexError:
        return None


def get_random_existing_account():
    if not official_accounts: return None
    try:
        return random.choice(tuple(official_accounts))
    except IndexError:
        return None


def get_random_existing_article():
    if not articles: return None
    try:
        return random.choice(tuple(articles))
    except IndexError:
        return None


def get_random_follower(account_id):
    follower_set = followers.get(account_id)
    if not follower_set: return None
    try:
        return random.choice(tuple(follower_set))
    except IndexError:
        return None


def get_random_existing_message_id(sent_status=None):
    possible_messages = [
        msg_id for msg_id, details in network_messages_store.items()
        if sent_status is None or details['is_sent'] == sent_status
    ]
    if not possible_messages: return None
    try:
        return random.choice(possible_messages)
    except IndexError:
        return None


def get_random_stored_emoji_id():
    if not network_emoji_ids: return None
    try:
        return random.choice(tuple(network_emoji_ids))
    except IndexError:
        return None


# --- 状态更新函数 (State Update Functions) ---
# (State update functions remain the same as the previous hw11 version)
def add_person_state(pid, name, age):
    if pid in persons: return
    persons.add(pid)
    person_details[pid] = {'name': name, 'age': age, 'social_value': 0, 'money': 0}
    person_tags[pid] = set()
    person_received_message_ids[pid] = []


def add_relation_state(id1, id2, value):
    p1, p2 = min(id1, id2), max(id1, id2)
    if (p1, p2) in relations: return
    relations.add((p1, p2));
    relation_values[(p1, p2)] = value


def modify_relation_state(id1, id2, m_value):
    p1, p2 = min(id1, id2), max(id1, id2);
    key = (p1, p2)
    if key in relation_values:
        new_value = relation_values[key] + m_value
        if new_value > 0:
            relation_values[key] = new_value
        else:
            relations.discard(key); relation_values.pop(key, None)


def add_tag_state(person_id, tag_id):
    person_tags.setdefault(person_id, set()).add(tag_id)
    tag_members.setdefault((person_id, tag_id), set())


def del_tag_state(person_id, tag_id):
    if person_id in person_tags: person_tags[person_id].discard(tag_id)
    tag_members.pop((person_id, tag_id), None)


def add_to_tag_state(person_id1, person_id2, tag_id):
    key = (person_id2, tag_id)
    if person_id2 in person_tags and tag_id in person_tags[person_id2]:
        tag_members.setdefault(key, set()).add(person_id1)


def del_from_tag_state(person_id1, person_id2, tag_id):
    key = (person_id2, tag_id)
    if key in tag_members: tag_members[key].discard(person_id1)


def add_account_state(acc_id, owner_id, name):
    if acc_id in official_accounts: return
    official_accounts.add(acc_id)
    account_details[acc_id] = {'owner': owner_id, 'name': name}
    followers[acc_id] = set()
    account_articles[acc_id] = set()
    contributions[acc_id] = {}


def del_account_state(acc_id):
    if acc_id not in official_accounts: return
    articles_to_delete = list(account_articles.get(acc_id, set()))
    for art_id in articles_to_delete: del_article_state(art_id)
    official_accounts.discard(acc_id)
    account_details.pop(acc_id, None)
    followers.pop(acc_id, None)
    account_articles.pop(acc_id, None)
    contributions.pop(acc_id, None)


def add_article_state(art_id, acc_id, person_id, name):
    if art_id in articles: return
    if acc_id not in official_accounts: return
    articles.add(art_id)
    article_details[art_id] = {'account': acc_id, 'contributor': person_id, 'name': name}
    account_articles.setdefault(acc_id, set()).add(art_id)
    contrib_for_acc = contributions.setdefault(acc_id, {})
    contrib_for_acc[person_id] = contrib_for_acc.get(person_id, 0) + 1


def del_article_state(art_id):
    if art_id not in articles: return
    details = article_details.pop(art_id, None)
    if not details:
        articles.discard(art_id);
        return
    acc_id = details['account'];
    person_id = details['contributor']
    articles.discard(art_id)
    if acc_id in account_articles: account_articles[acc_id].discard(art_id)
    if acc_id in contributions and person_id in contributions[acc_id]:
        contributions[acc_id][person_id] -= 1
        if contributions[acc_id][person_id] <= 0:
            contributions[acc_id].pop(person_id, None)
            if not contributions[acc_id]: contributions.pop(acc_id, None)


def add_follower_state(person_id, acc_id):
    if acc_id in official_accounts and person_id in persons:
        followers.setdefault(acc_id, set()).add(person_id)


def add_message_to_store_state(msg_id, msg_class, social_value_base, derived_social_value, sender_id, delivery_type,
                               receiver_id_or_tag_id, emoji_id_val=None, money_val=None, forward_article_id_val=None):
    if msg_id in network_messages_store: return
    details = {
        'id': msg_id, 'msg_class': msg_class, 'social_value_base': social_value_base,
        'derived_social_value': derived_social_value, 'sender_id': sender_id,
        'delivery_type': delivery_type, 'is_sent': False,
        'emoji_id_val': emoji_id_val, 'money_val': money_val,
        'forward_article_id_val': forward_article_id_val
    }
    if delivery_type == 0:
        details['receiver_id'] = receiver_id_or_tag_id
    else:
        details['tag_id'] = receiver_id_or_tag_id
    network_messages_store[msg_id] = details


def send_message_state(msg_id_to_send):
    if msg_id_to_send not in network_messages_store: return False  # Indicate failure
    msg = network_messages_store[msg_id_to_send]
    if msg['is_sent']: return False  # Indicate failure (already sent)

    sender_id = msg['sender_id']
    if sender_id not in person_details: return False  # Sender doesn't exist

    sender_details = person_details[sender_id]
    actual_recipients = []
    message_sent_successfully = False  # Track if the message could be delivered to anyone

    if msg['delivery_type'] == 0:  # To person
        receiver_id = msg['receiver_id']
        if receiver_id in person_details and receiver_id != sender_id:
            p1_link, p2_link = min(sender_id, receiver_id), max(sender_id, receiver_id)
            if (p1_link, p2_link) in relations:  # Check link
                receiver_details = person_details[receiver_id]
                receiver_details['social_value'] += msg['derived_social_value']
                actual_recipients.append(receiver_id)
                if msg['msg_class'] == 'red_envelope':
                    # Check money *before* deducting
                    if sender_details['money'] >= msg['money_val']:
                        sender_details['money'] -= msg['money_val']
                        receiver_details['money'] += msg['money_val']
                        message_sent_successfully = True
                    else:
                        return False  # Not enough money, send fails
                else:
                    message_sent_successfully = True  # Other messages send if linked
            # else: RelationNotFound - send technically fails per JML, but we mark as sent in generator state
            # Let's return False if relation not found, as sm command would fail.
            else:
                return False  # Send fails if not linked

    elif msg['delivery_type'] == 1:  # To tag
        tag_owner_id = msg['sender_id']  # Sender must own the tag
        tag_id_val = msg['tag_id']
        if tag_owner_id in person_tags and tag_id_val in person_tags[tag_owner_id]:
            paid_for_red_envelope_group = False
            members = tag_members.get((tag_owner_id, tag_id_val), set())
            # Check money for red envelope *before* iterating members
            if msg['msg_class'] == 'red_envelope' and sender_details['money'] < msg['money_val']:
                return False  # Not enough money for even one recipient

            for member_id in members:
                if member_id == tag_owner_id: continue  # Skip self
                if member_id not in person_details: continue  # Skip non-existent member

                p1_link, p2_link = min(tag_owner_id, member_id), max(tag_owner_id, member_id)
                if (p1_link, p2_link) in relations:  # Check link
                    member_details = person_details[member_id]
                    member_details['social_value'] += msg['derived_social_value']
                    actual_recipients.append(member_id)
                    if msg['msg_class'] == 'red_envelope':
                        if not paid_for_red_envelope_group:
                            sender_details['money'] -= msg['money_val']  # Deduct once
                            paid_for_red_envelope_group = True
                        member_details['money'] += msg['money_val']  # Each gets full amount
                    message_sent_successfully = True  # At least one recipient possible
            # If tag exists but has no valid linked members, send still "succeeds" from network perspective (message removed)
            if not members or not message_sent_successfully:
                # If red envelope and no one received, refund? JML implies money deducted if tag exists.
                # Let's assume money deducted if tag exists, even if no valid recipients.
                if msg['msg_class'] == 'red_envelope' and not paid_for_red_envelope_group:
                    sender_details['money'] -= msg['money_val']  # Deduct even if no one receives
                message_sent_successfully = True  # Mark as "sent" even if no one got it

        else:
            return False  # TagIdNotFound - send fails

    if not message_sent_successfully:
        # If type 0 failed due to relation or money, or type 1 failed due to tag not found or money
        return False

    # Common updates only if message was successfully processed at least partially
    sender_details['social_value'] += msg['derived_social_value']  # Sender always gets social value if send initiated

    for rec_id in actual_recipients:
        person_received_message_ids.setdefault(rec_id, []).insert(0, msg_id_to_send)

    if msg['msg_class'] == 'emoji':
        emoji_id_val = msg['emoji_id_val']
        if emoji_id_val in network_emoji_ids:
            network_emoji_heat[emoji_id_val] = network_emoji_heat.get(emoji_id_val, 0) + 1

    msg['is_sent'] = True
    return True  # Indicate success


def store_emoji_id_state(emoji_id_to_store):
    network_emoji_ids.add(emoji_id_to_store)
    if emoji_id_to_store not in network_emoji_heat:
        network_emoji_heat[emoji_id_to_store] = 0


def delete_cold_emoji_state(limit_val):
    emojis_to_remove_from_store = {eid for eid, heat in network_emoji_heat.items() if heat < limit_val}
    if not emojis_to_remove_from_store: return  # Nothing to delete

    for eid in emojis_to_remove_from_store:
        network_emoji_ids.discard(eid)
        network_emoji_heat.pop(eid, None)

    message_ids_to_delete = {
        msg_id for msg_id, details in network_messages_store.items()
        if details['msg_class'] == 'emoji' and details['emoji_id_val'] in emojis_to_remove_from_store
    }

    for msg_id in message_ids_to_delete:
        network_messages_store.pop(msg_id, None)
        for pid in list(person_received_message_ids.keys()):  # Iterate over keys copy
            if msg_id in person_received_message_ids.get(pid, []):
                # Create new list excluding the deleted message ID
                person_received_message_ids[pid] = [m for m in person_received_message_ids[pid] if m != msg_id]


# --- 辅助函数: 尝试生成参数 (Helper: Try generating params) ---
# --- 返回生成的指令列表，如果无法生成有效指令则返回 [] ---
def _try_generate_command_params(command):
    global next_message_id
    generated = []

    # --- Add Person ---
    if command == "ap":
        if len(persons) < max_p:  # Check limit
            pid_to_add = generate_unique_id(persons)
            name = generate_random_string();
            age = generate_random_age()
            generated.append(f"ap {pid_to_add} {name} {age}")
            add_person_state(pid_to_add, name, age)
    # --- Add Relation ---
    elif command == "ar":
        if len(persons) >= 2:  # Check precondition
            p1, p2 = get_two_random_existing_persons()
            if p1 is not None and p2 is not None:
                key = (min(p1, p2), max(p1, p2))
                if key not in relations:  # Ensure relation doesn't exist
                    val = generate_random_value()
                    generated.append(f"ar {p1} {p2} {val}")
                    add_relation_state(p1, p2, val)
    # --- Modify Relation ---
    elif command == "mr":
        if relations:  # Check precondition
            p1_mr, p2_mr = random.choice(list(relations))
            m_val = generate_random_m_value()
            generated.append(f"mr {p1_mr} {p2_mr} {m_val}")
            modify_relation_state(p1_mr, p2_mr, m_val)
    # --- Add Tag ---
    elif command == "at":
        p_id_at = get_random_existing_person()
        if p_id_at is not None:  # Check person exists
            existing_person_tags_at = person_tags.get(p_id_at, set())
            t_id_at = generate_unique_id(existing_person_tags_at, -500, 500)  # Ensure unique tag ID for person
            generated.append(f"at {p_id_at} {t_id_at}")
            add_tag_state(p_id_at, t_id_at)
    # --- Delete Tag ---
    elif command == "dt":
        p_id_dt = get_random_existing_person()
        if p_id_dt is not None:
            t_id_dt = get_random_tag_for_person(p_id_dt)  # Check tag exists for person
            if t_id_dt is not None:
                generated.append(f"dt {p_id_dt} {t_id_dt}")
                del_tag_state(p_id_dt, t_id_dt)
    # --- Add Person To Tag ---
    elif command == "att":
        if len(persons) >= 2 and relations and person_tags:  # Check general state
            p2_att_owner = get_random_existing_person()  # Tag owner
            if p2_att_owner is not None:
                t_id_att = get_random_tag_for_person(p2_att_owner)  # Check owner has tags
                if t_id_att is not None:
                    p1_att_member = get_random_existing_person()  # Person to be added
                    if p1_att_member is not None and p1_att_member != p2_att_owner:
                        key_rel_att = (min(p1_att_member, p2_att_owner), max(p1_att_member, p2_att_owner))
                        if key_rel_att in relations:  # Check link
                            current_members = tag_members.get((p2_att_owner, t_id_att), set())
                            if p1_att_member not in current_members:  # Check not already member
                                generated.append(f"att {p1_att_member} {p2_att_owner} {t_id_att}")
                                add_to_tag_state(p1_att_member, p2_att_owner, t_id_att)
    # --- Delete Person From Tag ---
    elif command == "dft":
        p2_dft_owner = get_random_existing_person()
        if p2_dft_owner is not None:
            t_id_dft = get_random_tag_for_person(p2_dft_owner)
            if t_id_dft is not None:
                p1_dft_member = get_random_member_for_tag(p2_dft_owner, t_id_dft)  # Check member exists in tag
                if p1_dft_member is not None:
                    generated.append(f"dft {p1_dft_member} {p2_dft_owner} {t_id_dft}")
                    del_from_tag_state(p1_dft_member, p2_dft_owner, t_id_dft)
    # --- Query Value ---
    elif command == "qv":
        if relations:  # Prefer existing relations for meaningful query
            p1_qv, p2_qv = random.choice(list(relations))
            generated.append(f"qv {p1_qv} {p2_qv}")
        elif len(persons) >= 2:  # Query non-existent if no relations exist but people do
            p1_try_qv, p2_try_qv = get_two_random_existing_persons()
            if p1_try_qv is not None and p2_try_qv is not None:
                generated.append(f"qv {p1_try_qv} {p2_try_qv}")
    # --- Query Circle / Shortest Path ---
    elif command in ["qci", "qsp"]:
        if len(persons) >= 2:  # Need at least two people
            p1_try, p2_try = get_two_random_existing_persons()
            if p1_try is not None and p2_try is not None:
                generated.append(f"{command} {p1_try} {p2_try}")
    # --- Query Triple Sum / Couple Sum ---
    elif command in ["qts", "qcs"]:
        if len(persons) >= 2:  # Need people for these sums to be potentially non-zero
            generated.append(command)
    # --- Query Tag Age Var / Value Sum ---
    elif command in ["qtav", "qtvs"]:
        p_id_qt = get_random_existing_person()
        if p_id_qt is not None:
            t_id_qt = get_random_tag_for_person(p_id_qt)  # Need tag
            if t_id_qt is not None:
                # More effective if tag has members
                if tag_members.get((p_id_qt, t_id_qt)):
                    generated.append(f"{command} {p_id_qt} {t_id_qt}")
    # --- Query Best Acquaintance ---
    elif command == "qba":
        p_id_qba = get_random_existing_person()
        if p_id_qba is not None:
            # Check if person has acquaintances
            has_acquaintance = any(
                min(p_id_qba, p2) == p_id_qba or max(p_id_qba, p1) == p_id_qba for p1, p2 in relations)
            if has_acquaintance:
                generated.append(f"qba {p_id_qba}")
    # --- Create Official Account ---
    elif command == "coa":
        p_id_coa = get_random_existing_person()  # Need owner
        if p_id_coa is not None:
            acc_id_coa = generate_unique_id(official_accounts)
            acc_name_coa = generate_random_string(10)
            generated.append(f"coa {p_id_coa} {acc_id_coa} {acc_name_coa}")
            add_account_state(acc_id_coa, p_id_coa, acc_name_coa)
    # --- Delete Official Account ---
    elif command == "doa":
        acc_id_doa = get_random_existing_account()  # Need account
        if acc_id_doa is not None:
            owner_id_doa = account_details.get(acc_id_doa, {}).get('owner')
            if owner_id_doa is not None:  # Need owner (should always exist if acc exists)
                generated.append(f"doa {owner_id_doa} {acc_id_doa}")
                del_account_state(acc_id_doa)
    # --- Contribute Article ---
    elif command == "ca":
        acc_id_ca = get_random_existing_account()  # Need account
        p_id_ca_contrib = get_random_existing_person()  # Need contributor
        if acc_id_ca is not None and p_id_ca_contrib is not None:
            # Check if contributor is a follower (required by JML)
            if p_id_ca_contrib in followers.get(acc_id_ca, set()):
                art_id_ca = generate_unique_id(articles)
                art_name_ca = generate_random_string(15)
                generated.append(f"ca {p_id_ca_contrib} {acc_id_ca} {art_id_ca} {art_name_ca}")
                add_article_state(art_id_ca, acc_id_ca, p_id_ca_contrib, art_name_ca)
    # --- Delete Article ---
    elif command == "da":
        art_id_da = get_random_existing_article()  # Need article
        if art_id_da is not None:
            details_da = article_details.get(art_id_da)
            if details_da:
                acc_id_da = details_da['account']
                # contributor_id_da = details_da['contributor'] # Not needed for DA permission check
                owner_id_da = account_details.get(acc_id_da, {}).get('owner')
                if owner_id_da is not None:  # Account must exist
                    # Person deleting must be owner
                    generated.append(f"da {owner_id_da} {acc_id_da} {art_id_da}")
                    del_article_state(art_id_da)
    # --- Follow Official Account ---
    elif command == "foa":
        p_id_foa = get_random_existing_person()  # Need person
        acc_id_foa = get_random_existing_account()  # Need account
        if p_id_foa is not None and acc_id_foa is not None:
            current_followers = followers.get(acc_id_foa, set())
            if p_id_foa not in current_followers:  # Check not already follower
                generated.append(f"foa {p_id_foa} {acc_id_foa}")
                add_follower_state(p_id_foa, acc_id_foa)
    # --- Query Best Contributor ---
    elif command == "qbc":
        acc_id_qbc = get_random_existing_account()  # Need account
        if acc_id_qbc is not None:
            # Check if account has contributors
            if contributions.get(acc_id_qbc):
                generated.append(f"qbc {acc_id_qbc}")
    # --- Query Received Articles ---
    elif command == "qra":
        p_id_qra = get_random_existing_person()  # Need person
        if p_id_qra is not None:
            # Check if person follows any accounts
            follows_any = any(p_id_qra in followers.get(acc_id, set()) for acc_id in official_accounts)
            if follows_any:  # More likely to have received articles
                generated.append(f"qra {p_id_qra}")
    # --- Store Emoji ID ---
    elif command == "sei":
        new_emoji_id = generate_unique_id(network_emoji_ids, 0, 1000)
        generated.append(f"sei {new_emoji_id}")
        store_emoji_id_state(new_emoji_id)
    # --- Add Message Base Logic ---
    elif command in ["am", "aem", "arem", "afm"]:
        msg_id = next_message_id
        msg_delivery_type = generate_random_message_delivery_type()
        p1_sender = get_random_existing_person()
        if p1_sender is None: return []  # Need sender

        p2_or_tag_id = -1
        valid_target = False
        # target_person = None # Not strictly needed here
        # target_tag = None # Not strictly needed here

        # Find valid target (person or tag)
        if msg_delivery_type == 0 and len(persons) >= 2:  # To person
            attempts = 0
            # Try to find a valid linked receiver. Max attempts to avoid infinite loop.
            max_target_attempts = len(persons) * 2 + 5
            while attempts < max_target_attempts:
                p2_receiver = get_random_existing_person()
                if p2_receiver is not None and p1_sender != p2_receiver:
                    key_rel = (min(p1_sender, p2_receiver), max(p1_sender, p2_receiver))
                    if key_rel in relations:  # Check link
                        p2_or_tag_id = p2_receiver
                        # target_person = p2_receiver # Not strictly needed here
                        valid_target = True
                        break
                attempts += 1
        elif msg_delivery_type == 1:  # To tag
            tag_id_target = get_random_tag_for_person(p1_sender)
            if tag_id_target is not None:
                p2_or_tag_id = tag_id_target
                # target_tag = tag_id_target # Not strictly needed here
                valid_target = True

        if valid_target:
            # Generate specific message type
            if command == "am":
                social_val = generate_random_social_value_param()
                generated.append(f"am {msg_id} {social_val} {msg_delivery_type} {p1_sender} {p2_or_tag_id}")
                add_message_to_store_state(msg_id, 'plain', social_val, social_val, p1_sender, msg_delivery_type,
                                           p2_or_tag_id)
                next_message_id += 1
            elif command == "aem":
                emoji_to_send = get_random_stored_emoji_id()
                if emoji_to_send is not None:  # Check prerequisite: emoji must be stored
                    derived_sv_aem = emoji_to_send  # socialValue = emojiId
                    generated.append(f"aem {msg_id} {emoji_to_send} {msg_delivery_type} {p1_sender} {p2_or_tag_id}")
                    add_message_to_store_state(msg_id, 'emoji', emoji_to_send, derived_sv_aem, p1_sender,
                                               msg_delivery_type, p2_or_tag_id, emoji_id_val=emoji_to_send)
                    next_message_id += 1
            elif command == "arem":
                money_val = generate_random_money_param()
                # JML for sendMessage implies money check before sending.
                # For addRedEnvelopeMessage, the check is on sendMessage.
                # Here, we just add it to store. Actual money check in send_message_state.
                derived_sv_arem = money_val * 5  # socialValue = money * 5
                generated.append(f"arem {msg_id} {money_val} {msg_delivery_type} {p1_sender} {p2_or_tag_id}")
                add_message_to_store_state(msg_id, 'red_envelope', money_val, derived_sv_arem, p1_sender,
                                           msg_delivery_type, p2_or_tag_id, money_val=money_val)
                next_message_id += 1
            elif command == "afm":
                article_to_fwd = get_random_existing_article()
                if article_to_fwd is not None:  # Check prerequisite: article exists
                    # JML for addMessage(ForwardMessage) requires sender to have received the article.
                    # This is hard to track perfectly in generator without simulating Person.receivedArticles.
                    # For simplicity, we assume it's possible if article exists.
                    # The actual social value for ForwardMessage is abs(articleId) % 200 per spec.
                    derived_sv_afm = abs(article_to_fwd) % 200
                    generated.append(f"afm {msg_id} {article_to_fwd} {msg_delivery_type} {p1_sender} {p2_or_tag_id}")
                    add_message_to_store_state(msg_id, 'forward', article_to_fwd, derived_sv_afm, p1_sender,
                                               msg_delivery_type, p2_or_tag_id, forward_article_id_val=article_to_fwd)
                    next_message_id += 1
    # --- Send Message ---
    elif command == "sm":
        msg_to_send_id = get_random_existing_message_id(sent_status=False)  # Need unsent message
        if msg_to_send_id is not None:
            # Simulate send success/fail based on current state for state update
            # This ensures we only generate 'sm' if it's likely to be valid according to JML.
            success = send_message_state(msg_to_send_id)  # send_message_state now returns True/False
            if success:  # Only generate command if state update indicates it should succeed
                generated.append(f"sm {msg_to_send_id}")
            # else: If send_message_state returns False, don't generate 'sm' command, let strategy retry.
    # --- Delete Cold Emoji ---
    elif command == "dce":
        if network_emoji_heat:  # Need emojis to delete
            limit_dce = generate_random_limit()
            generated.append(f"dce {limit_dce}")
            delete_cold_emoji_state(limit_dce)
    # --- Query Social Value / Money ---
    elif command in ["qsv", "qm"]:
        p_id_q = get_random_existing_person()  # Need person
        if p_id_q is not None: generated.append(f"{command} {p_id_q}")
    # --- Query Received Messages ---
    elif command == "qrm":
        p_id_qrm = get_random_existing_person()  # Need person
        if p_id_qrm is not None:
            # Check if person likely received messages (stateful check)
            if person_received_message_ids.get(p_id_qrm):
                generated.append(f"qrm {p_id_qrm}")
    # --- Query Popularity ---
    elif command == "qp":
        emoji_id_qp = get_random_stored_emoji_id()  # Need stored emoji
        if emoji_id_qp is not None: generated.append(f"qp {emoji_id_qp}")
    # --- Load Network ---
    elif command == "ln":
        # Only allow if no persons exist yet and it's the first instruction
        if not persons and current_file_instruction_count == 0:
            n_ln = random.randint(1, min(max_p, 50))  # Limit ln size
            if n_ln > 0:
                generated.append(f"ln {n_ln}")
                ln_ids = [generate_unique_id(set(), -20000, 20000) for _ in
                          range(n_ln)]  # Start with empty set for ln IDs
                ln_names = [generate_random_string() for _ in range(n_ln)]
                ln_ages = [generate_random_age() for _ in range(n_ln)]
                generated.append(" ".join(map(str, ln_ids)))
                generated.append(" ".join(ln_names))
                generated.append(" ".join(map(str, ln_ages)))
                # Add persons to state *after* generating ID list
                for i in range(n_ln): add_person_state(ln_ids[i], ln_names[i], ln_ages[i])

                for i in range(n_ln - 1):
                    row_values = []
                    for j in range(i + 1):
                        if random.random() < 0.5:  # Add relation with 50% chance
                            value_ln = generate_random_value()
                            row_values.append(str(value_ln))
                            add_relation_state(ln_ids[i + 1], ln_ids[j], value_ln)
                        else:
                            row_values.append("0")
                    generated.append(" ".join(row_values))

    return generated


# --- 策略 (Strategies) ---

def get_command_probabilities(current_instr_count, max_instr_count):
    """ dynamically adjust command probabilities based on progress """
    progress = current_instr_count / max_instr_count if max_instr_count > 0 else 0
    probs = {}

    # Early phase (0% - 25%): Focus on building state
    if progress < 0.25:
        probs.update({cmd: 5 for cmd in STATE_ADD_COMMANDS if cmd != 'ln'})  # High weight for adding
        if 'ln' in COMMANDS and current_instr_count == 0 and not persons: probs[
            'ln'] = 50  # Very high weight for ln at start if no persons
        probs.update({cmd: 1 for cmd in STATE_MODIFY_COMMANDS})
        probs.update({cmd: 0.5 for cmd in QUERY_COMMANDS})  # Low weight for queries
        probs.update({cmd: 0.2 for cmd in EXCEPTION_TARGET_COMMANDS})  # Low weight for exceptions
    # Mid phase (25% - 75%): Mix of building, modifying, querying, exceptions
    elif progress < 0.75:
        probs.update({cmd: 2 for cmd in STATE_ADD_COMMANDS if cmd != 'ln'})  # Moderate weight for adding
        probs.update({cmd: 3 for cmd in STATE_MODIFY_COMMANDS})  # Higher weight for modifying
        probs.update({cmd: 3 for cmd in QUERY_COMMANDS})  # Higher weight for querying
        probs.update({cmd: 2 for cmd in EXCEPTION_TARGET_COMMANDS})  # Moderate weight for exceptions
    # Late phase (75% - 100%): Focus on querying, modifying, exceptions
    else:
        probs.update({cmd: 0.5 for cmd in STATE_ADD_COMMANDS if cmd != 'ln'})  # Low weight for adding
        probs.update({cmd: 4 for cmd in STATE_MODIFY_COMMANDS})  # High weight for modifying
        probs.update({cmd: 5 for cmd in QUERY_COMMANDS})  # High weight for querying
        probs.update({cmd: 3 for cmd in EXCEPTION_TARGET_COMMANDS})  # High weight for exceptions

    # Ensure essential commands are possible if state allows
    if not persons and 'ap' in COMMANDS: probs['ap'] = probs.get('ap', 0) + 10  # Boost 'ap' if no persons
    if not network_emoji_ids and 'sei' in COMMANDS: probs['sei'] = probs.get('sei', 0) + 5  # Boost 'sei' if no emojis

    # Filter out commands with zero or negative probability before returning
    valid_commands = [cmd for cmd, weight in probs.items() if weight > 0 and cmd in COMMANDS]
    valid_weights = [probs[cmd] for cmd in valid_commands]

    if not valid_commands:  # Fallback if all weights ended up zero (should be rare)
        return list(COMMANDS), [1] * len(COMMANDS)

    return valid_commands, valid_weights


def strategy_dynamic_random(commands_list):
    """
    Improved random strategy with state checks and dynamic command weighting.
    """
    global current_file_instruction_count, max_instr

    # Get weighted command list based on progress
    possible_commands, weights = get_command_probabilities(current_file_instruction_count, max_instr)

    # Filter based on current allowed commands (e.g., no 'ln' after start)
    allowed_set = set(commands_list)
    filtered_commands = [cmd for cmd in possible_commands if cmd in allowed_set]

    # Adjust weights based on the filtered list
    current_weights = []
    for cmd in filtered_commands:
        try:
            current_weights.append(weights[possible_commands.index(cmd)])
        except ValueError:  # Should not happen if logic is correct
            current_weights.append(1)  # Default weight if cmd somehow not in original weighted list

    if not filtered_commands:
        return strategy_simple_random_with_checks(commands_list)

    # Attempt to generate commands based on weighted choice
    max_tries = len(filtered_commands) * 2 + 15  # More attempts for weighted
    attempts = 0
    while attempts < max_tries:
        try:
            if not filtered_commands or not current_weights or sum(
                    current_weights) == 0:  # Guard against empty/all-zero weights
                return strategy_simple_random_with_checks(commands_list)
            chosen_command = random.choices(filtered_commands, weights=current_weights, k=1)[0]
        except (IndexError, ValueError):  # Handle empty lists or weight issues
            return strategy_simple_random_with_checks(commands_list)  # Fallback

        # State checks are now primarily within _try_generate_command_params
        generated_lines = _try_generate_command_params(chosen_command)
        if generated_lines:
            return generated_lines  # Success

        attempts += 1
    return strategy_simple_random_with_checks(commands_list)


def strategy_simple_random_with_checks(commands_list):
    """ A simpler random strategy with basic state checks. """
    if not commands_list: return []

    possible_commands_list = list(commands_list)  # Create a mutable list
    random.shuffle(possible_commands_list)  # Shuffle for randomness

    max_tries = len(possible_commands_list) + 5  # Try each command once on average

    for attempt in range(max_tries):
        if not possible_commands_list: break  # No more commands to try

        command_index = random.randrange(len(possible_commands_list))
        command = possible_commands_list[command_index]

        # _try_generate_command_params now handles more detailed state checks
        generated_lines = _try_generate_command_params(command)
        if generated_lines:
            return generated_lines  # Success
        else:
            # If a command fails to generate, remove it from consideration for this round
            # to avoid repeatedly trying impossible commands.
            possible_commands_list.pop(command_index)

    return []  # Failed to generate anything


def strategy_build_state(commands_list):
    """Prioritize commands that add elements or relations."""
    preferred_cmds = [cmd for cmd in STATE_ADD_COMMANDS if cmd in commands_list]
    if 'ln' in preferred_cmds and current_file_instruction_count > 0:
        preferred_cmds.remove('ln')  # Only allow ln at the start

    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    return strategy_dynamic_random(commands_list)


def strategy_query_focus(commands_list):
    """Improved query strategy: checks state first, falls back to build state."""
    # Check if the state is rich enough for queries
    if len(persons) < 5 or len(relations) < 3:  # Arbitrary thresholds, adjust as needed
        # print("Query strategy: State not rich enough, falling back to build state.", file=sys.stderr)
        return strategy_build_state(commands_list)

    preferred_cmds = [cmd for cmd in QUERY_COMMANDS if cmd in commands_list]
    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    # print("Query strategy: No query generated, falling back to build state.", file=sys.stderr)
    return strategy_build_state(commands_list)


def strategy_stress_test(commands_list):
    """Focus on modifications and complex queries, assuming state is built."""
    if len(persons) < 10 or len(relations) < 5:  # Needs a reasonably built state
        # print("Stress test strategy: State not rich enough, falling back to build state.", file=sys.stderr)
        return strategy_build_state(commands_list)

    stress_commands = STATE_MODIFY_COMMANDS + QUERY_COMMANDS
    preferred_cmds = [cmd for cmd in stress_commands if cmd in commands_list]

    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    return strategy_dynamic_random(commands_list)


def strategy_exception_focus(commands_list):
    """Tries to generate commands likely to cause exceptions."""
    possible_targets = [cmd for cmd in EXCEPTION_TARGET_COMMANDS if cmd in commands_list]
    if not possible_targets: return strategy_dynamic_random(commands_list)

    target_command = random.choice(possible_targets)

    # Attempt to generate a valid version first, then try to make it invalid
    # This is a placeholder for more sophisticated exception generation.
    # For now, it's similar to dynamic_random but with a slight bias.
    generated = _try_generate_command_params(target_command)
    if generated and random.random() < 0.7:  # Higher chance to return a valid command
        return generated

    # Crude attempt to force an exception (example: non-existent ID)
    if random.random() < 0.5:  # Try to make it invalid
        if target_command in ["sm", "qp", "qsv", "qm", "qrm", "qba", "doa", "da", "foa", "qbc", "qra", "dt", "dft",
                              "att", "qtav", "qtvs"]:
            non_existent_pid = generate_unique_id(persons, -20000, -10001)
            non_existent_msg_id = generate_unique_id(network_messages_store.keys(), -20000, -10001)
            non_existent_emoji_id = generate_unique_id(network_emoji_ids, -20000, -10001)
            non_existent_tag_id = generate_unique_id(set(), -600, -501)  # Tags can be small negatives

            # Simplistic: just use a non-existent ID for the first parameter if applicable
            # This needs to be much more targeted per command for reliable exception triggering.
            if target_command == "sm":
                return [f"sm {non_existent_msg_id}"]
            elif target_command == "qp":
                return [f"qp {non_existent_emoji_id}"]
            elif target_command in ["qsv", "qm", "qrm", "qba", "qra"]:
                return [f"{target_command} {non_existent_pid}"]
            elif target_command == "dt" and persons:
                return [f"dt {get_random_existing_person()} {non_existent_tag_id}"]
            # This is a very basic attempt and likely won't hit many specific exceptions.
            # True exception testing requires crafting inputs that violate specific JML preconditions.

    return strategy_dynamic_random(commands_list)  # Fallback


# --- ADDED STRATEGY DEFINITIONS ---
def strategy_message_focus(commands_list):
    """Prioritizes commands related to messages."""
    preferred_cmds = [cmd for cmd in MESSAGE_COMMANDS if cmd in commands_list]
    # Ensure 'sei' is tried if no emojis exist, and 'ap'/'ar' if needed for sending
    if not network_emoji_ids and 'sei' in preferred_cmds:
        result_sei = _try_generate_command_params('sei')
        if result_sei: return result_sei
    if (len(persons) < 2 or not relations) and any(cmd in ["am", "aem", "arem", "afm", "sm"] for cmd in preferred_cmds):
        result_build = strategy_build_state(commands_list)  # Try to build persons/relations
        if result_build: return result_build

    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    return strategy_dynamic_random(commands_list)


def strategy_account_focus(commands_list):
    """Prioritizes commands related to official accounts and articles."""
    preferred_cmds = [cmd for cmd in ACCOUNT_ARTICLE_COMMANDS if cmd in commands_list]
    # Ensure persons exist for coa, ca, foa
    if not persons and any(cmd in ["coa", "ca", "foa"] for cmd in preferred_cmds):
        result_ap = _try_generate_command_params('ap')
        if result_ap: return result_ap

    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    return strategy_dynamic_random(commands_list)


def strategy_tag_focus(commands_list):
    """Prioritizes commands related to tags."""
    preferred_cmds = [cmd for cmd in TAG_COMMANDS if cmd in commands_list]
    # Ensure persons exist for at, att, dft
    if not persons and any(cmd in ["at", "att", "dft"] for cmd in preferred_cmds):
        result_ap = _try_generate_command_params('ap')
        if result_ap: return result_ap
    if len(persons) < 2 and any(cmd in ["att", "dft"] for cmd in preferred_cmds):  # att/dft need two people
        result_build = strategy_build_state(commands_list)
        if result_build: return result_build

    if preferred_cmds:
        result = strategy_dynamic_random(preferred_cmds)
        if result: return result
    return strategy_dynamic_random(commands_list)


# --- 主生成逻辑 (Main Generation Logic) ---
def generate_test_case(filename_prefix, mode_choice, strategy_func):
    global persons, person_details, relations, relation_values, person_tags, tag_members
    global official_accounts, account_details, followers, articles, article_details, account_articles, contributions
    global network_messages_store, person_received_message_ids, network_emoji_ids, network_emoji_heat, next_message_id
    global max_instr, max_p, mode
    global current_file_instruction_count

    # 重置状态 (Reset state)
    persons.clear();
    person_details.clear();
    relations.clear();
    relation_values.clear()
    person_tags.clear();
    tag_members.clear()
    official_accounts.clear();
    account_details.clear();
    followers.clear();
    articles.clear()
    article_details.clear();
    account_articles.clear();
    contributions.clear()
    network_messages_store.clear();
    person_received_message_ids.clear()
    network_emoji_ids.clear();
    network_emoji_heat.clear()
    next_message_id = 0
    current_file_instruction_count = 0  # Reset for each file

    mode = mode_choice
    max_instr = MAX_INSTRUCTIONS[mode]
    max_p = MAX_PERSONS[mode]

    # Allowed commands for this run (excluding lnl)
    allowed_commands = [c for c in COMMANDS if c != "lnl"]

    strategy_name = strategy_func.__name__.replace("strategy_", "")
    filename = f"{filename_prefix}_{strategy_name}.txt"
    filepath = os.path.join("data", filename)

    print(f"Generating {filename} using primary strategy {strategy_name}...")

    instructions_written_this_file = 0  # Use this for instruction counting within a file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            while instructions_written_this_file < max_instr:
                # Update global counter for strategies that might use it (like get_command_probabilities)
                current_file_instruction_count = instructions_written_this_file

                # Determine allowed commands for this specific iteration (e.g., handle 'ln')
                current_allowed_for_iteration = [cmd for cmd in allowed_commands if
                                                 not (cmd == 'ln' and instructions_written_this_file > 0)]
                if not current_allowed_for_iteration:
                    # print(f"Warning: No commands possible at instruction {instructions_written_this_file + 1} for {filename}.", file=sys.stderr)
                    break  # Cannot generate further

                generated_lines = strategy_func(current_allowed_for_iteration)

                if not generated_lines:
                    generated_lines = strategy_dynamic_random(current_allowed_for_iteration)  # Fallback

                if generated_lines:
                    # Check if the block fits; if not, break before writing
                    num_lines_in_block = len(generated_lines)
                    if instructions_written_this_file + num_lines_in_block > max_instr:
                        # print(f"Command block ({generated_lines[0].split()[0] if generated_lines else 'N/A'}) too large to fit. Stopping.", file=sys.stderr)
                        break

                    for line in generated_lines:
                        f.write(line + '\n')
                    instructions_written_this_file += num_lines_in_block  # Count all lines written from a successful generation
                else:
                    # print(f"Warning: All strategies failed. Stopping for {filename} at {instructions_written_this_file} instructions.", file=sys.stderr)
                    break

    except IOError as e:
        print(f"Error opening or writing to file {filepath}: {e}", file=sys.stderr)
        return None

    print(f"Generated {filepath} with {instructions_written_this_file} instructions.")
    return filename


# --- 主执行块 (Main Execution Block) ---
if __name__ == "__main__":
    while True:
        mode_input = input(f"Choose mode: Public Test ({MODE_PUBLIC}) or Mutual Test ({MODE_MUTUAL}): ").lower()
        if mode_input in [MODE_PUBLIC, MODE_MUTUAL]:
            break
        else:
            print("Invalid input. Please enter 's' or 'm'.")

    while True:
        try:
            num_files_total = int(input("How many test cases do you want to generate in total? "))
            if num_files_total > 0:
                break
            else:
                print("Please enter a positive integer.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    if not os.path.exists("data"):
        os.makedirs("data");
        print("Created directory: data")

    # Define the sequence of primary strategies to cycle through
    strategies_to_use = [
        strategy_build_state,  # Start by building some state
        strategy_dynamic_random,  # General random behavior
        strategy_message_focus,  # Focus on messages
        strategy_account_focus,  # Focus on accounts/articles
        strategy_query_focus,  # Focus on queries (improved version)
        strategy_tag_focus,  # Focus on tags
        strategy_stress_test,  # Stress test with modifications/queries
        strategy_exception_focus,  # Try to cause exceptions
        strategy_dynamic_random,  # More general random
        strategy_build_state,  # Build more state if needed
        strategy_stress_test,  # Another stress phase
    ]
    num_strategies = len(strategies_to_use)

    generated_files_count = 0
    file_base_index = 1
    start_time_total = time.time()

    while generated_files_count < num_files_total:
        start_time_file = time.time()
        # Cycle through the defined primary strategies
        current_primary_strategy = strategies_to_use[generated_files_count % num_strategies]
        filename_prefix = f"testcase_{file_base_index}"

        try:
            # Pass the chosen *primary* strategy to generate_test_case
            generated_filename = generate_test_case(filename_prefix, mode_input, current_primary_strategy)

            if generated_filename:
                generated_files_count += 1
                file_base_index += 1
                end_time_file = time.time()
                print(f"    Time taken for {generated_filename}: {end_time_file - start_time_file:.2f}s")
            else:
                # Handle generation failure
                print(
                    f"Error: Failed to generate file starting with {filename_prefix} using primary strategy {current_primary_strategy.__name__}.")
                # Optionally ask to continue or break
                # cont = input("File generation failed. Continue? (y/n): ").lower()
                # if cont != 'y': break
                file_base_index += 1  # Increment index to avoid retrying same prefix immediately

        except Exception as e:
            # Handle critical errors during generation
            import traceback

            print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
            print(
                f"Critical Error generating test case starting with {filename_prefix} using strategy {current_primary_strategy.__name__}:",
                file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n", file=sys.stderr)
            cont = input("A critical error occurred. Continue generating other files? (y/n): ").lower()
            if cont != 'y': break
            file_base_index += 1  # Move to next file prefix

    end_time_total = time.time()
    print(f"\nData generation finished. Generated {generated_files_count} files.")
    print(f"Total time taken: {end_time_total - start_time_total:.2f}s")
