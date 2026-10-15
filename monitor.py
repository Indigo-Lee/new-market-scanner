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


users = load(USERS_FILE, {})  # chat_id -> {"cats": [...], "paused": bool}


def keyboard(chat):
    on = set(users[chat]["cats"])
    rows = [[{"text": ("✅ " if c in on else "⬜ ") + c, "callback_data": c}] for c in CATEGORIES]
    return {"inline_keyboard": rows}


def topics_prompt(chat):
    tg("sendMessage", chat_id=chat, text="Which markets are you most interested in? Tap to toggle.\n"
       "You'll only get alerts for the ones with a ✅.", reply_markup=keyboard(chat))


def status_text(chat):
    u = users[chat]
    cats = ", ".join(u["cats"]) or "none yet (use /topics)"
    return f"Alerts: {'paused' if u['paused'] else 'on'}\nCategories: {cats}"


def handle_message(msg):
    chat, text = str(msg["chat"]["id"]), (msg.get("text") or "").strip().lower()
    new = chat not in users
    users.setdefault(chat, {"cats": [], "paused": False})
    cmd = text.split("@")[0].split()[0].lstrip("/") if text else ""
    if cmd == "start" or new:
        tg("sendMessage", chat_id=chat, text="Hey! I'll alert you when new Kalshi markets go live.\n"
           "Send /help any time to see what I can do.")
        topics_prompt(chat)
    elif cmd in ("topics", "categories", "markets"):
        topics_prompt(chat)
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
    elif cmd == "status":
        tg("sendMessage", chat_id=chat, text=status_text(chat))
    else:  # help, or anything unrecognised
        tg("sendMessage", chat_id=chat, text=HELP)
    save(USERS_FILE, users)


def handle_callback(cb):
    chat, cat = str(cb["message"]["chat"]["id"]), cb.get("data")
    users.setdefault(chat, {"cats": [], "paused": False})
    if cat in CATEGORIES:
        cats = users[chat]["cats"]
        cats.remove(cat) if cat in cats else cats.append(cat)
        save(USERS_FILE, users)
        tg("editMessageReplyMarkup", chat_id=chat, message_id=cb["message"]["message_id"],
           reply_markup=keyboard(chat))
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


def price(m):
    bid, ask = float(m.get("yes_bid_dollars") or 0), float(m.get("yes_ask_dollars") or 0)
    return f"Yes {bid * 100:.0f}¢ bid / {ask * 100:.0f}¢ ask" if bid or ask else "No quotes yet"


def alert(category, event, markets):
    m = markets[0]
    more = f"\n+{len(markets) - 1} more markets in this event" if len(markets) > 1 else ""
    text = (f"🆕 [{category}] {event.get('title') or m.get('title')}\n{m.get('title')}\n{price(m)}{more}\n"
            f"https://kalshi.com/markets/{m.get('event_ticker')}")
    for chat, u in users.items():
        if not u["paused"] and category in u["cats"]:
            try:
                tg("sendMessage", chat_id=chat, text=text)
            except Exception as e:
                print("send failed:", chat, e)


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
