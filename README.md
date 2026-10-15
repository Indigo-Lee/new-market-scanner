# New Market Scanner

Get a Telegram message the moment a new market is listed on Kalshi, only for the categories you care about.

New markets are where odds are most likely to be miscalibrated, and sometimes the same event is already trading on other prediction markets. Being first matters.

## What it does

- Polls Kalshi's free public market data API (no Kalshi account or API key needed).
- Sends **one alert per event** (not per market), with the title, Yes bid/ask and a link.
- When you first message the bot, it asks you three things so you don't get flooded:
  1. **Categories** you care about.
  2. **How often** you want alerts: instant, or a digest every 5 min / 15 min / hourly.
  3. **Quality thresholds**: minimum Yes bid, maximum bid/ask spread, and minimum contracts at the best bid (a simple liquidity check).
- Multiple people can use the same bot. Everyone has their own settings.

## Bot commands

| Command | What it does |
|---|---|
| `/topics` | Pick which categories you want (tap to toggle) |
| `/frequency` | Instant alerts, or a 5 min / 15 min / hourly digest |
| `/filters` | Set min Yes bid, max spread and min size at the bid |
| `/all` / `/none` | Turn every category on / off |
| `/pause` / `/resume` | Stop / restart alerts without losing your settings |
| `/status` | See all your current settings |
| `/help` | Show the help page (typing `help` works too) |

### How the thresholds work

New markets often have no quotes at all, so these filters are what keep junk out:

- **Min Yes bid**: skip markets where the best Yes bid is below this (e.g. `5¢+`). `Any` includes unquoted markets.
- **Max spread**: skip markets where ask minus bid is wider than this. Markets with no bid or ask are skipped when this is set.
- **Min size at bid**: skip markets with fewer contracts than this resting at the best bid.

A market only alerts you if it passes all three. If an event has several markets, you get the first one that passes plus a "+N more" count.

### How "instant" works

The scanner checks Kalshi every `POLL_SECONDS` (default 60), so instant means within about a minute of a market being listed. Lower it (e.g. `POLL_SECONDS=10`) for faster alerts; Kalshi's public API is rate limited, so don't go much below that.

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
2. Answer the quick setup questions (categories, frequency, thresholds). Change them any time with `/topics`, `/frequency`, `/filters`, or see `/help`.
3. Wait for new markets. The first scan only records existing markets as a baseline, so alerts begin with markets listed after that. A busy hour can have a few hundred new events, so pick categories to keep things quiet.

### 5. Share it (optional)

Two ways to hand this to other people:

- **Share your bot:** anyone who opens `t.me/<your_bot_username>` and presses **Start** gets their own settings. Your script has to stay running somewhere that's always on (a VPS, Raspberry Pi, Fly.io, Railway, Render, or a spare machine).
- **Share the repo:** others clone this repo, make their own bot with BotFather (steps 1-3), and run it themselves. Each person needs their own token and their own machine running it.

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
