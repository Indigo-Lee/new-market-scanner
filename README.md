# Kalshi New Market Alerts

Get a Telegram notification the moment a new market is listed on Kalshi.

New markets are where odds are most likely to be miscalibrated. Be the first to see them.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Create a Telegram channel and add your bot as an admin.
3. Run:

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="@your_channel"   # or numeric id like -100123456789
python3 monitor.py
```

No dependencies (Python 3.8+ standard library). Uses Kalshi's free public market data API; no API key needed.
The first run records existing markets as a baseline; you only get alerts for markets listed after that.
Set `POLL_SECONDS` to change the polling interval (default 60).
