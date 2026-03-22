# Hybrid Crypto Bot v2

A crypto trading bot with a web dashboard and a **hybrid AI architecture**:

- **AI regime selector** chooses whether the market is trending, ranging, breaking out, or risk-off.
- **Rule-based strategy engine** picks a base strategy for that regime.
- **AI trade filter** confirms or vetoes the proposed trade.
- **Stricter risk engine** sizes trades and blocks entries when confidence, daily loss, cooldown, or loss-streak rules are violated.
- **Execution layer** runs in `paper` mode today and is wired for a guarded Hyperliquid live adapter later.

## What changed in v2

This version is materially stricter than the earlier starter:

- Added **AI confidence floors** for both regime classification and trade filtering.
- Added **required AI agreement** with the trade direction.
- Added **max trades per day** and **cooldown after closing a trade**.
- Added **kill switch** after too many consecutive losses.
- Added **estimated fees** to trade records and realized PnL.
- Added **ATR-based trailing stop** so open positions tighten risk as they move in your favor.
- Added clearer dashboard panels for the current decision reason and active risk limits.
- Added a second live-trading guard: `ENABLE_LIVE_TRADING=false` must be changed explicitly before any live executor can even try to place orders.

## Included strategies

### 1) Trend regime -> EMA trend
- Long when fast EMA is above slow EMA
- Short when fast EMA is below slow EMA
- Best for directional BTC/ETH phases

### 2) Range regime -> RSI mean reversion
- Long when RSI is oversold
- Short when RSI is overbought
- Better for sideways markets

### 3) Breakout regime -> Range breakout
- Long near recent highs
- Short near recent lows
- Better when volatility expands

### 4) Risk-off regime -> Hold cash
- No new position
- Used when the AI is not confident in current conditions

## How the hybrid flow works

1. Pull current price and candles from Hyperliquid public data.
2. Build features such as EMA, RSI, ATR, and recent range.
3. Ask the AI to classify the regime.
4. Choose the rule-based strategy for that regime.
5. Ask the AI to filter the proposed trade.
6. Apply hard risk checks.
7. Execute in paper mode, or route to the live executor later.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload
```

Then open `http://127.0.0.1:8000`.

## Notes on AI

- If `OPENAI_API_KEY` is set, the app uses OpenAI for structured JSON outputs.
- If no API key is set, the app falls back to deterministic heuristic logic so the bot still works.
- You can point `OPENAI_BASE_URL` to a compatible local endpoint later.

## Safety notes

- This is now safer for **paper trading**, but it is still not a guarantee of profitability.
- The live executor remains blocked behind both wallet credentials and `ENABLE_LIVE_TRADING=true`.
- Keep it in `paper` mode until you have verified fills, logs, and decision behavior for a while.

## Good first settings

- Symbol: `BTC`
- Interval: `1h`
- Mode: `paper`
- AI: enabled

## Suggested next upgrades

- Add a real news feed and store the latest headlines per cycle
- Add backtesting and equity-curve charts
- Add websocket market updates
- Add authenticated Hyperliquid execution through the official Python SDK
- Add per-strategy performance analytics


## Windows Git and GitHub

This project is already set up to work as a **local Git repo** and to push to **GitHub** later.

### Quick local repo setup on Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init-local-repo.ps1 -CommitMessage "Initial hybrid bot commit" -ForceMain
```

### Connect it to GitHub and push

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\connect-github-remote.ps1 -RemoteUrl "https://github.com/YOURNAME/YOURREPO.git" -Push
```

There is also a `GITHUB_WINDOWS_SETUP.md` guide and a `scripts\open-in-github-desktop.bat` helper.
