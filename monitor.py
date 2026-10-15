"""Telegram bot that DMs you when new Kalshi markets are listed, filtered to the categories you pick."""
import json, os, time, urllib.parse, urllib.request

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "60"))
HERE = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE, USERS_FILE = os.path.join(HERE, "seen.json"), os.path.join(HERE, "users.json")

CATEGORIES = ["Politics", "Elections", "Economics", "Financials", "Sports", "Entertainment",
              "Science and Technology", "Climate and Weather", "Health", "World", "Companies", "Social"]

HELP = """Kalshi New Market Scanner

I message you when a new market is listed on Kalshi, only for the categories you choose.

/topics - pick which categories you want
/frequency - how often you get alerts (instant, or 5 min / 15 min / hourly digests)
/filters - only alert if the market has a real bid: min Yes bid, max spread, min size
/all - turn on every category
/none - turn off every category
/pause - stop alerts (keeps your settings)
/resume - start alerts again
/status - see what you're subscribed to
/help - show this message"""


def http(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "kalshi-new-market-scanner"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def tg(method, **params):
    return http(f"https://api.telegram.org/bot{TOKEN}/{method}", urllib.parse.urlencode(
        {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in params.items()}).encode())


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def save(path, obj):
    json.dump(obj, open(path, "w"))


DEFAULTS = {"cats": [], "paused": False, "freq": 0, "min_bid": 0, "max_spread": 100, "min_depth": 0,
            "pending": [], "last_sent": 0}
FREQ = [("⚡ Instant", 0), ("Every 5 min", 300), ("Every 15 min", 900), ("Hourly", 3600)]
FILTERS = {  # key: (question, [(button label, value)])
    "min_bid": ("Minimum Yes bid? Skips markets nobody is bidding on yet.",
                [("Any", 0), ("1¢+", 1), ("5¢+", 5), ("10¢+", 10), ("25¢+", 25)]),
    "max_spread": ("Maximum spread (ask minus bid)? Smaller means tighter, more liquid markets.",
                   [("Any", 100), ("2¢", 2), ("5¢", 5), ("10¢", 10), ("20¢", 20)]),
    "min_depth": ("Minimum contracts sitting at the best bid? A simple liquidity check.",
                  [("Any", 0), ("10+", 10), ("100+", 100), ("500+", 500), ("1000+", 1000)]),
}

users = load(USERS_FILE, {})  # chat_id -> settings (see DEFAULTS)
for _u in users.values():
    for _k, _v in DEFAULTS.items():
        _u.setdefault(_k, list(_v) if isinstance(_v, list) else _v)


def user(chat):
    if chat not in users:
        users[chat] = {k: list(v) if isinstance(v, list) else v for k, v in DEFAULTS.items()}
    return users[chat]


def keyboard(chat):
    on = set(users[chat]["cats"])
    rows = [[{"text": ("✅ " if c in on else "⬜ ") + c, "callback_data": "cat:" + c}] for c in CATEGORIES]
    return {"inline_keyboard": rows}


def choice_keyboard(chat, key, options, per_row=2):
    cur = users[chat][key]
    btns = [{"text": ("✅ " if v == cur else "") + label, "callback_data": f"{key}:{v}"} for label, v in options]
    return {"inline_keyboard": [btns[i:i + per_row] for i in range(0, len(btns), per_row)]}


def keyboard_for(chat, key):
    if key == "cat":
        return keyboard(chat)
    if key == "freq":
        return choice_keyboard(chat, "freq", FREQ)
    return choice_keyboard(chat, key, FILTERS[key][1], per_row=3)


def topics_prompt(chat):
    tg("sendMessage", chat_id=chat, text="Which markets are you most interested in? Tap to toggle.\n"
       "You'll only get alerts for the ones with a ✅.", reply_markup=keyboard(chat))


def frequency_prompt(chat):
    tg("sendMessage", chat_id=chat, text="How often do you want alerts?\n"
       "Instant sends each one right away. The others bundle new markets into one digest message.",
       reply_markup=keyboard_for(chat, "freq"))


def filters_prompt(chat):
    for key, (question, _) in FILTERS.items():
        tg("sendMessage", chat_id=chat, text=question, reply_markup=keyboard_for(chat, key))


def label(options, value):
    return next((l for l, v in options if v == value), str(value))


def status_text(chat):
    u = users[chat]
    cats = ", ".join(u["cats"]) or "none yet (use /topics)"
    return (f"Alerts: {'paused' if u['paused'] else 'on'}\nCategories: {cats}\n"
            f"Frequency: {label(FREQ, u['freq'])}\n"
            f"Min Yes bid: {label(FILTERS['min_bid'][1], u['min_bid'])}\n"
            f"Max spread: {label(FILTERS['max_spread'][1], u['max_spread'])}\n"
            f"Min size at bid: {label(FILTERS['min_depth'][1], u['min_depth'])}")


def handle_message(msg):
    chat, text = str(msg["chat"]["id"]), (msg.get("text") or "").strip().lower()
    new = chat not in users
    user(chat)
    cmd = text.split("@")[0].split()[0].lstrip("/") if text else ""
    if cmd == "start" or new:
        tg("sendMessage", chat_id=chat, text="Hey! I'll alert you when new Kalshi markets go live.\n"
           "A few quick questions to keep it from getting noisy. Send /help any time.")
        topics_prompt(chat)
        frequency_prompt(chat)
        filters_prompt(chat)
    elif cmd in ("topics", "categories", "markets"):
        topics_prompt(chat)
    elif cmd in ("frequency", "freq"):
        frequency_prompt(chat)
    elif cmd in ("filters", "filter", "threshold", "liquidity"):
        filters_prompt(chat)
    elif cmd == "all":
        users[chat]["cats"] = list(CATEGORIES)
        tg("sendMessage", chat_id=chat, text="All categories on. Use /topics to trim.")
    elif cmd == "none":
        users[chat]["cats"] = []
        tg("sendMessage", chat_id=chat, text="All categories off. Use /topics to pick some.")
    elif cmd == "pause":
        users[chat]["paused"] = True
        tg("sendMessage", chat_id=chat, text="Paused. Send /resume to turn alerts back on.")
    elif cmd == "resume":
        users[chat]["paused"] = False
        tg("sendMessage", chat_id=chat, text="Alerts back on.\n" + status_text(chat))
    elif cmd in ("status", "settings"):
        tg("sendMessage", chat_id=chat, text=status_text(chat))
    else:  # help, or anything unrecognised
        tg("sendMessage", chat_id=chat, text=HELP)
    save(USERS_FILE, users)


def handle_callback(cb):
    chat, data = str(cb["message"]["chat"]["id"]), cb.get("data") or ""
    u, (key, _, val) = user(chat), data.partition(":")
    if key == "cat" and val in CATEGORIES:
        cats = u["cats"]
        cats.remove(val) if val in cats else cats.append(val)
    elif key == "freq" and any(str(v) == val for _, v in FREQ):
        u["freq"] = int(val)
    elif key in FILTERS and any(str(v) == val for _, v in FILTERS[key][1]):
        u[key] = int(val)
    else:
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        return
    save(USERS_FILE, users)
    try:
        tg("editMessageReplyMarkup", chat_id=chat, message_id=cb["message"]["message_id"],
           reply_markup=keyboard_for(chat, key))
    except Exception:
        pass  # Telegram errors when nothing changed
    tg("answerCallbackQuery", callback_query_id=cb["id"])


def fetch_new_markets(since):
    markets, cursor = [], ""
    while True:
        q = {"status": "open", "limit": 1000, "mve_filter": "exclude", "min_created_ts": since}
        if cursor:
            q["cursor"] = cursor
        data = http(f"{KALSHI}/markets?{urllib.parse.urlencode(q)}")
        markets += data.get("markets", [])
        cursor = data.get("cursor")
        if not cursor:
            return markets


def quote(m):
    """(bid cents, ask cents, contracts at best bid)"""
    return (round(float(m.get("yes_bid_dollars") or 0) * 100), round(float(m.get("yes_ask_dollars") or 0) * 100),
            float(m.get("yes_bid_size_fp") or 0))


def price(m):
    bid, ask, _ = quote(m)
    return f"Yes {bid}¢ bid / {ask}¢ ask" if bid or ask else "No quotes yet"


def passes(u, m):
    bid, ask, size = quote(m)
    if bid < u["min_bid"] or size < u["min_depth"]:
        return False
    if u["max_spread"] < 100 and not (bid and ask and ask - bid <= u["max_spread"]):
        return False
    return True


def render(item):
    more = f"\n+{item['more']} more markets in this event" if item["more"] else ""
    return f"🆕 [{item['cat']}] {item['event']}\n{item['market']}\n{item['price']}{more}\n{item['url']}"


def send_batch(chat, items):
    text = ""
    for it in items:
        piece = render(it)
        if text and len(text) + len(piece) > 3800:
            tg("sendMessage", chat_id=chat, text=text, disable_web_page_preview=True)
            text = ""
        text += ("\n\n" if text else "") + piece
    if text:
        tg("sendMessage", chat_id=chat, text=text, disable_web_page_preview=len(items) > 1)


def alert(category, event, markets):
    for chat, u in users.items():
        if u["paused"] or category not in u["cats"]:
            continue
        ok = [m for m in markets if passes(u, m)]
        if not ok:
            continue
        m = ok[0]
        u["pending"].append({"cat": category, "event": event.get("title") or m.get("title"),
                             "market": m.get("title"), "price": price(m), "more": len(ok) - 1,
                             "url": f"https://kalshi.com/markets/{m.get('event_ticker')}"})
    flush()


def flush():
    """Send each user's pending alerts if their chosen frequency has elapsed."""
    now = time.time()
    for chat, u in users.items():
        if u["pending"] and (u["freq"] == 0 or now - u["last_sent"] >= u["freq"]) and not u["paused"]:
            try:
                send_batch(chat, u["pending"][:50])
                u["pending"], u["last_sent"] = u["pending"][50:], now
            except Exception as e:
                print("send failed:", chat, e)
    save(USERS_FILE, users)


def scan(seen):
    markets = fetch_new_markets(int(time.time()) - 3600)
    fresh = [m for m in markets if m["ticker"] not in seen]
    by_event = {}
    if seen:  # first scan only records a baseline
        for m in fresh:
            by_event.setdefault(m["event_ticker"], []).append(m)
        for ev, ms in by_event.items():
            try:
                event = http(f"{KALSHI}/events/{ev}").get("event", {})
            except Exception as e:
                print("event lookup failed:", ev, e)
                continue
            alert(event.get("category", "Other"), event, ms)
    seen.update(m["ticker"] for m in markets)
    save(SEEN_FILE, sorted(seen))


def main():
    seen, offset, last_scan = set(load(SEEN_FILE, [])), 0, 0.0
    first = not seen
    print("running; Ctrl+C to stop")
    while True:
        try:
            for upd in tg("getUpdates", offset=offset, timeout=10).get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    handle_message(upd["message"])
                elif "callback_query" in upd:
                    handle_callback(upd["callback_query"])
        except Exception as e:
            print("telegram error:", e)
            time.sleep(5)
        flush()
        if time.time() - last_scan >= POLL_SECONDS:
            try:
                scan(seen if not first else set())
                if first:
                    seen, first = set(load(SEEN_FILE, [])), False
            except Exception as e:
                print("kalshi error:", e)
            last_scan = time.time()


if __name__ == "__main__":
    main()
