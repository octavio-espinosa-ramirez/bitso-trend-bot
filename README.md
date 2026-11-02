# Bitso Trend Bot

[![tests](https://github.com/octavio-espinosa-ramirez/bitso-trend-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/octavio-espinosa-ramirez/bitso-trend-bot/actions/workflows/tests.yml)

A modular Python trading bot for the [Bitso](https://bitso.com) crypto exchange (MXN pairs), controlled from Telegram.
It starts in **paper trading** mode by default, and real money sits behind a **double safety lock**.

> Educational project. Not financial advice. The default parameters in this repo are generic examples, not a tuned strategy.

## Features
- **Trend-following strategy**: breakout entries with a trend filter, ATR-based initial stop and trailing stop, and a maximum holding period.
- **Risk management**: risk per trade, max allocation per pair, max open positions and a daily loss limit.
- **Paper trading by default**: simulated fills including fees and slippage.
- **Double safety lock for real money**: requires `LIVE_TRADING=true` **and** an explicit confirmation typed in Telegram.
- **Telegram control panel** (UI in Spanish): start/stop, status, open positions, stats, an emergency "sell all" button and switching between paper and live mode.
- **Backtesting and research**: downloads real historical candles and compares configurations with a train/test split.
- **Persistent state** in a JSON file, so restarts and redeploys don't lose open positions.
- **Tests + CI**: pytest suite running on GitHub Actions.
- **Deploy-ready**: Dockerfile and Railway config.

## Project structure
```
main.py              # entry point
research.py          # historical data download + configuration comparison (train/test)
bot/
  config.py          # all settings, read from environment variables
  broker.py          # Bitso REST API client (paper and live)
  data.py            # market data (candles)
  indicators.py      # EMA, RSI, ATR, highest high
  strategy.py        # entry / exit rules
  engine.py          # main loop: signals, sizing, risk limits, orders
  backtest.py        # backtesting engine
  state.py           # persistent state (JSON)
  telegram_ui.py     # Telegram bot interface
tests/
  test_all.py        # unit tests
```

## Quick start
```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your own values
python main.py            # runs in paper trading mode
python research.py 540    # download ~540 days of history and compare configurations
python -m pytest tests -q
```

## Configuration
All settings come from environment variables (see `.env.example`). Main ones:

| Variable | Description |
|---|---|
| `TOKEN`, `CHAT_ID` | Telegram bot token and your chat id |
| `BITSO_API_KEY`, `BITSO_API_SECRET` | Bitso API credentials (only needed for live trading) |
| `PAIRS`, `TIMEFRAME` | Traded pairs and candle size in seconds (3600 / 14400 / 86400) |
| `FEE` | Your real fee per side |
| `RISK_PER_TRADE`, `MAX_ALLOC`, `MAX_OPEN`, `DAILY_LOSS_LIMIT` | Risk limits |
| `PAPER_CAPITAL` | Starting capital for paper trading |
| `STATE_FILE` | Path of the persistent state file |
| `LIVE_TRADING` | First lock for real money (`false` by default) |

## Real money (double lock)
1. Set `LIVE_TRADING=true` and restart.
2. In Telegram, press **💰 Activar REAL** and type the confirmation phrase `CONFIRMO REAL`.

Before going live, place a minimum manual order and check that the order-trades endpoint returns what you expect.

## Deploy (Railway)
The repo includes a `Dockerfile` and `railway.json`. Mount a volume and point `STATE_FILE` to it, otherwise state is lost on every deploy. See `DEPLOY_RAILWAY.md`.

## Author
**Octavio Espinosa Ramírez** · [LinkedIn](https://www.linkedin.com/in/octavio-espinosa-ramirez) · [landify.lat](https://landify.lat)
