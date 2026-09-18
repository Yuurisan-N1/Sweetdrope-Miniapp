import os
import re
import sys
import json
import time
import signal
import asyncio
import aiohttp

from urllib.parse import parse_qs, unquote, quote

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "SweetDrope Miniapp"

BASE_URL = "https://botsmother.com/api/command/MjI4Mw=="
CMD_HOME = "MTg0OTQ="
CMD_CHECKIN = "MTg0OTY="
CMD_AD_START = "MTg1MDA="
CMD_AD_CLAIM = "MTg0OTU="
CMD_VERIFY = "MTg1MDc="
CMD_SOCIAL = "MTg1MDY="

REF_CODE = "6004380466"

CALL_ATTEMPTS = 3
CALL_RETRY_SECONDS = 4
ROUND_PAUSE_SECONDS = 2
RATE_LIMIT_PAUSE_SECONDS = 8
AD_WAIT_SECONDS = 11
TASK_NAME_LIMIT = 20
NAME_LIMIT = 18
CHANNEL_LIMIT = 22
NOTE_LIMIT = 22
AD_ROUND_LIMIT = 15
DEFAULT_HOURLY_LIMIT = 15

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

PAGE_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
)

ALREADY_WORDS = (
    "already claimed",
    "already completed",
    "already checked",
    "already checked in",
)

JOIN_WORDS = (
    "please join the channel",
    "must join",
    "not joined",
)

LIMIT_WORDS = (
    "limit reached",
    "hourly limit",
    "daily limit",
)

WAIT_WORDS = (
    "not waited",
    "wait for",
)


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def unit_word(value, singular, plural):
    return singular if int(value) == 1 else plural


def format_usdt(value):
    try:
        number = float(value)
    except Exception:
        return "0"
    if number != number or number == 0:
        return "0"
    if abs(number) >= 1:
        text = f"{number:.6f}"
    else:
        text = f"{number:.8f}"
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def load_config():
    defaults = {
        "settings": {
            "sleep_seconds": 3600,
        }
    }
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            loaded = json.load(handle)
    except Exception:
        return defaults
    settings = loaded.get("settings")
    if not isinstance(settings, dict):
        return defaults
    merged = dict(defaults["settings"])
    merged.update(settings)
    return {"settings": merged}


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines


def parse_init_data(line):
    value = line.strip()
    if "|" in value:
        value = value.rsplit("|", 1)[0].strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0].split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
        "lastName": str(profile.get("last_name") or ""),
        "startParam": str((fields.get("start_param") or [""])[0]),
    }


def display_name(account):
    for candidate in (account.get("firstName"), account.get("username")):
        if candidate:
            return candidate
    return "account"


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def countdown(seconds, label):
    total = int(seconds)
    if total < 1:
        return
    line = ""
    for remaining in range(total, 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        line = f"{clean_text(label, 'item')} {hours:02d}:{minutes:02d}:{rest:02d}"
        print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * (len(line) + 6) + "\r", end="", flush=True)


def api_error(payload):
    if isinstance(payload, dict):
        message = payload.get("error") or payload.get("message")
        if message:
            return str(message)
    return ""


def error_key(payload):
    return clean_text(api_error(payload), "").lower()


def matches(key, words):
    return any(word in key for word in words)


async def api_get(session, command, proxy, account=None, **params):
    url = f"{BASE_URL}/{command}"
    query = {"initData": account["initData"] if account else ""}
    query.update({name: str(value) for name, value in params.items()})
    last_status = 0
    last_body = ""
    for attempt in range(1, CALL_ATTEMPTS + 1):
        pause = CALL_RETRY_SECONDS * attempt
        try:
            request = session.get(
                url,
                params=query,
                headers={
                    "accept": "application/json, text/plain, */*",
                    "origin": "https://botsmother.com",
                    "referer": "https://botsmother.com/",
                    "user-agent": PAGE_AGENT,
                },
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=40),
            )
            async with request as response:
                last_status = response.status
                last_body = await response.text()
                if response.status < 500 and response.status != 429:
                    return last_status, last_body
                if response.status == 429:
                    pause = RATE_LIMIT_PAUSE_SECONDS * attempt
        except Exception:
            last_status = 0
            last_body = ""
        if attempt < CALL_ATTEMPTS:
            countdown(pause, "Retry in")
    return last_status, last_body


def parse_payload(body):
    if not body:
        return {}
    stripped = body.strip()
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except Exception:
            return {}
    return {}


def state_block(html):
    marker = "appState = {"
    start = html.find(marker)
    if start < 0:
        return ""
    start = html.index("{", start)
    depth = 0
    quote_char = None
    position = start
    while position < len(html):
        char = html[position]
        if quote_char:
            if char == "\\":
                position += 2
                continue
            if char == quote_char:
                quote_char = None
        else:
            if char in "\"'":
                quote_char = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
        position += 1
    return html[start:position + 1]


def parse_state(html):
    block = state_block(html)
    if not block:
        return {}
    body = re.sub(r"//[^\n]*", "", block)
    body = re.sub(r"([{,\s])(\w+)\s*:", r'\1"\2":', body)
    body = body.replace("'", '"')
    body = re.sub(r",\s*([}\]])", r"\1", body)
    try:
        loaded = json.loads(body)
    except Exception:
        loaded = {}
    user = loaded.get("userData")
    if isinstance(user, dict):
        return user
    fallback = {}
    for key in ("balance", "total_earning", "streak",
                "totalEarned", "tasksCompleted", "referralEarnings",
                "todayTasks", "dailyTaskLimit", "hourlyTasks", "hourlyTaskLimit",
                "lifetimeTasks"):
        found = re.search(rf"{key}\s*:\s*([0-9]+(?:\.[0-9]+)?)", block)
        if found:
            fallback[key] = found.group(1)
    flag = re.search(r"isDayClaimable\s*:\s*(true|false)", block)
    if flag:
        fallback["isDayClaimable"] = flag.group(1) == "true"
    friends = re.search(r"referredUsers\s*:\s*\[", block)
    fallback["friendCount"] = block.count("{", friends.end()) if friends else 0
    return fallback


def parse_tasks(html):
    joins = []
    pattern = (r'<a href="https://t\.me/([A-Za-z0-9_]+)"[^>]*>'
               r'(?:\s*<i[^>]*>.*?</i>)?[^<]*</a>\s*<button[^>]*data-task-id="(\d+)"')
    for found in re.finditer(pattern, html):
        joins.append({"channel": found.group(1), "id": found.group(2)})
    socials = []
    pattern = r'<a href="(https?://[^"]+)"[^>]*onclick="startSocialTimer\((\d+)\)"'
    for found in re.finditer(pattern, html):
        socials.append({"url": found.group(1), "id": found.group(2)})
    return joins, socials


def number_of(state, key, fallback=0):
    try:
        return float(state.get(key))
    except Exception:
        return fallback


def read_balance(state):
    value = state.get("balance")
    return number_of(state, "balance", None) if value is not None else None


async def fetch_state(session, proxy, account):
    status, body = await api_get(session, CMD_HOME, proxy, account)
    if status != 200:
        return None, ""
    return parse_state(body), body


async def run_check_in(session, proxy, account, state):
    if not state.get("isDayClaimable"):
        log_yellow("The daily bonus was already collected earlier")
        return
    status, body = await api_get(session, CMD_CHECKIN, proxy, account)
    payload = parse_payload(body)
    if payload.get("status"):
        amount = payload.get("todaysamount")
        if amount is None:
            amount = 0
        log_green(f"Daily bonus credited {clean_text(format_usdt(amount), 0)} USDT")
        return
    key = error_key(payload)
    if matches(key, ALREADY_WORDS):
        log_yellow("The daily bonus was already collected earlier")
        return
    note = shorten(api_error(payload), "the server refused the claim", NOTE_LIMIT)
    log_red(f"Daily bonus failed because {clean_text(note, 'refused')}")


async def run_join_tasks(session, proxy, account, state, joins):
    if not joins:
        log_yellow("No channel task was listed by the server")
        return
    for task in joins:
        channel = shorten(task.get("channel"), "channel", CHANNEL_LIMIT)
        label = clean_text(channel, "channel")
        status, body = await api_get(session, CMD_VERIFY, proxy, account, task_id=task.get("id"))
        payload = parse_payload(body)
        if payload.get("status"):
            before = number_of(state, "balance", 0)
            after = number_of(payload, "balance", before)
            state["balance"] = after
            credited = after - before
            log_green(f"Channel {clean_text(label, 'channel')} credited "
                      f"{clean_text(format_usdt(credited), 0)} USDT")
            await asyncio.sleep(ROUND_PAUSE_SECONDS)
            continue
        key = error_key(payload)
        if matches(key, ALREADY_WORDS):
            log_yellow(f"Channel {clean_text(label, 'channel')} was verified earlier")
            continue
        if matches(key, JOIN_WORDS):
            log_yellow(f"Channel {clean_text(label, 'channel')} still needs a real join")
            continue
        note = shorten(api_error(payload), "the server refused it", NOTE_LIMIT)
        log_red(f"Channel {clean_text(label, 'channel')} refused because "
                f"{clean_text(note, 'refused')}")
        await asyncio.sleep(ROUND_PAUSE_SECONDS)


async def run_social_tasks(session, proxy, account, state, socials):
    if not socials:
        log_yellow("No social task was listed by the server")
        return
    for task in socials:
        host = shorten(re.sub(r"^[a-z]+://", "", task.get("url") or "").split("/")[0],
                       "link", CHANNEL_LIMIT)
        label = clean_text(host, "link")
        status, body = await api_get(session, CMD_SOCIAL, proxy, account, task_id=task.get("id"))
        payload = parse_payload(body)
        if payload.get("status"):
            before = number_of(state, "balance", 0)
            after = number_of(payload, "balance", before)
            state["balance"] = after
            credited = after - before
            if credited > 0:
                log_green(f"Social {clean_text(label, 'link')} credited "
                          f"{clean_text(format_usdt(credited), 0)} USDT")
            else:
                log_yellow(f"Social {clean_text(label, 'link')} gave no verified credit")
            await asyncio.sleep(ROUND_PAUSE_SECONDS)
            continue
        key = error_key(payload)
        if matches(key, ALREADY_WORDS):
            log_yellow(f"Social {clean_text(label, 'link')} was claimed earlier")
            continue
        note = shorten(api_error(payload), "the server refused it", NOTE_LIMIT)
        log_red(f"Social {clean_text(label, 'link')} refused because "
                f"{clean_text(note, 'refused')}")
        await asyncio.sleep(ROUND_PAUSE_SECONDS)


async def run_ad_tasks(session, proxy, account, state):
    hourly_limit = int(number_of(state, "hourlyTaskLimit", DEFAULT_HOURLY_LIMIT))
    done = int(number_of(state, "hourlyTasks", 0))
    remaining = hourly_limit - done
    if remaining <= 0:
        log_yellow("The hourly ad allowance is used up for now")
        return
    rounds = min(remaining, AD_ROUND_LIMIT)
    claimed = 0
    for _ in range(rounds):
        status, body = await api_get(session, CMD_AD_START, proxy, account)
        payload = parse_payload(body)
        task_id = payload.get("task_id")
        if not task_id:
            note = shorten(api_error(payload), "no ad slot was offered", NOTE_LIMIT)
            log_yellow(f"The ad server offered no slot because {clean_text(note, 'busy')}")
            break
        countdown(AD_WAIT_SECONDS, "Ad reward in")
        status, body = await api_get(session, CMD_AD_CLAIM, proxy, account, task_id=task_id)
        payload = parse_payload(body)
        if payload.get("status"):
            before = number_of(state, "balance", 0)
            after = number_of(payload, "balance", before)
            state["balance"] = after
            credited = after - before
            state["hourlyTasks"] = number_of(payload, "hourlyTasks", done + 1)
            state["todayTasks"] = number_of(payload, "todayTasks", 0)
            claimed += 1
            log_green(f"Ad reward credited {clean_text(format_usdt(credited), 0)} USDT")
            await asyncio.sleep(ROUND_PAUSE_SECONDS)
            continue
        key = error_key(payload)
        if matches(key, WAIT_WORDS):
            countdown(AD_WAIT_SECONDS, "Ad reward in")
            continue
        if matches(key, LIMIT_WORDS):
            log_yellow("The hourly ad allowance is used up for now")
            break
        note = shorten(api_error(payload), "the server refused the claim", NOTE_LIMIT)
        log_red(f"Ad reward failed because {clean_text(note, 'refused')}")
        break
    if claimed:
        log_yellow(f"Ad rewards collected this pass {clean_text(claimed, 0)}")


async def run_referral(session, proxy, account, state):
    friends = int(number_of(state, "friendCount", 0))
    earned = number_of(state, "referralEarnings", 0)
    code = account["id"] or REF_CODE
    log_yellow(f"Referral friends on this account {clean_text(friends, 0)} "
               f"earning {clean_text(format_usdt(earned), 0)} USDT")


async def process_account(line, proxy, index, settings, args):
    account = parse_init_data(line)
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        state, html = await fetch_state(session, proxy, account)
        if state is None:
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        name = shorten(display_name(account), "account", NAME_LIMIT)
        balance = read_balance(state)
        log_green(f"Signed in {clean_text(name, 'account')} with "
                  f"{clean_text(format_usdt(balance), 0)} USDT")
        streak = int(number_of(state, "streak", 0))
        log_yellow(f"Check in streak sits at {clean_text(streak, 0)} "
                   f"{clean_text(unit_word(streak, 'day', 'days'), 'days')}")

        joins, socials = parse_tasks(html)

        await run_check_in(session, proxy, account, state)
        await run_join_tasks(session, proxy, account, state, joins)
        await run_social_tasks(session, proxy, account, state, socials)
        await run_ad_tasks(session, proxy, account, state)
        await run_referral(session, proxy, account, state)

        final_state, _ = await fetch_state(session, proxy, account)
        if isinstance(final_state, dict):
            closing = read_balance(final_state)
        else:
            closing = state.get("balance")
        log_yellow(f"Closing balance on this account "
                   f"{clean_text(format_usdt(closing), 0)} USDT")


async def main_async(accounts, proxies, sleep_secs, settings, args):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1, settings, args)
            countdown(ROUND_PAUSE_SECONDS, "Next account in")

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = load_config().get("settings", {})
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, settings["sleep_seconds"], settings, None))


if __name__ == "__main__":
    main()
