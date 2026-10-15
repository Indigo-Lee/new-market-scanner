# New Market Scanner

Get a Telegram message the moment a new market is listed on Kalshi, only for the categories you care about.

New markets are where odds are most likely to be miscalibrated, and sometimes the same event is already trading on other prediction markets. Being first matters.

## What it does

- Polls Kalshi's free public market data API (no Kalshi account or API key needed).
- Sends **one alert per event** (not per market), with the title, Yes bid/ask and a link.
- When you first message the bot, it asks **which categories you're most interested in**. You only get alerts for those.
- Multiple people can use the same bot. Everyone has their own settings.

## Bot commands

| Command | What it does |
|---|---|
| `/topics` | Pick which categories you want (tap to toggle) |
| `/all` / `/none` | Turn every category on / off |
| `/pause` / `/resume` | Stop / restart alerts without losing your settings |
| `/status` | See what you're subscribed to |
| `/help` | Show the help page (typing `help` works too) |

Categories: Politics, Elections, Economics, Financials, Sports, Entertainment, Science and Technology, Climate and Weather, Health, World, Companies, Social.

## Setup, step by step

You need Python 3.8+ (check with `python3 --version`). There are no packages to install.

### 1. Create your bot

1. In Telegram, search for **@BotFather** (the one with the blue verified checkmark) and open it.
2. Send `/newbot`.
3. Send a display name, e.g. `Kalshi New Markets`.
4. Send a username ending in `bot`, e.g. `yourname_kalshi_bot`.
5. BotFather replies with a **token** like `123456789:AAH...`. Keep it secret. Anyone with it can control your bot.

### 2. Get the code

```bash
git clone https://github.com/Indigo-Lee/new-market-scanner.git
cd new-market-scanner
```

### 3. Run it

```bash
export TELEGRAM_BOT_TOKEN="PASTE_YOUR_TOKEN_HERE"
python3 monitor.py
```

Leave this terminal open. The scanner only sends alerts while it's running.

### 4. Subscribe

1. In Telegram, open your bot (`t.me/<your_bot_username>`) and press **Start**.
2. Tap the categories you want. Send `/help` any time.
3. Wait for new markets. The first scan only records existing markets as a baseline, so alerts begin with markets listed after that. A busy hour can have a few hundred new events, so pick categories to keep things quiet.

### 5. Share it (optional)

Anyone who opens your bot and presses **Start** gets their own subscription. Just share `t.me/<your_bot_username>`. The script must be running somewhere that stays on (a VPS, Raspberry Pi, Fly.io, Railway, Render, or a spare machine).

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | required | Token from BotFather |
| `POLL_SECONDS` | `60` | How often to check Kalshi |

## Troubleshooting

- **`KeyError: 'TELEGRAM_BOT_TOKEN'`**: the `export` didn't run in this terminal window.
- **`401 Unauthorized`**: wrong or revoked token. Get a fresh one with `/token` in BotFather.
- **Bot doesn't reply**: make sure `monitor.py` is running and you pressed **Start** in the bot chat (not a channel).
- **No alerts**: check `/status` that you have categories selected and alerts aren't paused.
- **Lost your token**: send `/revoke` to BotFather to get a new one.

## Files

- `monitor.py`: the whole bot.
- `users.json`: each subscriber's settings (created automatically, git-ignored).
- `seen.json`: markets already seen (created automatically, git-ignored).
