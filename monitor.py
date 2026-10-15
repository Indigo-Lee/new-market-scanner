"""Send a Telegram message whenever a new Kalshi market is listed."""
import json, os, time, urllib.parse, urllib.request

API = "https://api.elections.kalshi.com/trade-api/v2/markets"
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]  # e.g. @mychannel or -100123456789
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "60"))
STATE = os.path.join(os.path.dirname(__file__), "seen.json")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kalshi-new-markets-alert"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_open_markets(min_created_ts):
    markets, cursor = [], ""
    while True:
        q = {"status": "open", "limit": 1000, "mve_filter": "exclude", "min_created_ts": min_created_ts}
        if cursor:
            q["cursor"] = cursor
        data = get(f"{API}?{urllib.parse.urlencode(q)}")
        markets += data.get("markets", [])
        cursor = data.get("cursor")
        if not cursor:
            return markets


def price(m):
    bid, ask = float(m.get("yes_bid_dollars") or 0), float(m.get("yes_ask_dollars") or 0)
    return f"Yes {bid * 100:.0f}¢ bid / {ask * 100:.0f}¢ ask" if bid or ask else "No quotes yet"


def notify(m):
    text = (
        f"🆕 {m.get('title')}\n"
        f"{m.get('subtitle') or ''}\n"
        f"{price(m)}\n"
        f"https://kalshi.com/markets/{m.get('event_ticker')}"
    ).replace("\n\n", "\n")
    body = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", body, timeout=30)


def main():
    seen = set(json.load(open(STATE))) if os.path.exists(STATE) else None
    since = int(time.time()) - 3600
    while True:
        try:
            markets = fetch_open_markets(since)
            fresh = [m for m in markets if seen is None or m["ticker"] not in seen]
            if seen is not None:  # first run only records a baseline
                for m in {m["event_ticker"]: m for m in fresh}.values():  # one alert per event
                    notify(m)
                    time.sleep(1)
            seen = (seen or set()) | {m["ticker"] for m in markets}
            json.dump(sorted(seen), open(STATE, "w"))
            since = int(time.time()) - 3600  # overlap window so nothing slips through
        except Exception as e:
            print("error:", e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
