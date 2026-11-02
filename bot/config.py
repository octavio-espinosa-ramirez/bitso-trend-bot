"""Configuración central. Todo se puede cambiar con variables de entorno (.env)."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _f(name, default):
    return float(os.getenv(name, default))


@dataclass
class Config:
    token: str = os.getenv("TOKEN", "")
    api_key: str = os.getenv("BITSO_API_KEY", "")
    api_secret: str = os.getenv("BITSO_API_SECRET", "")
    chat_id: int = int(os.getenv("CHAT_ID", "0"))

    pairs: list = field(default_factory=lambda: os.getenv("PAIRS", "btc_mxn,eth_mxn,xrp_mxn").split(","))
    timeframe: int = int(os.getenv("TIMEFRAME", "86400"))  # segundos: 3600=1h, 14400=4h, 86400=1d (validado en backtest)

    # Estrategia (valores por defecto: se ajustan con backtest.py)
    ema_trend: int = int(os.getenv("EMA_TREND", "200"))
    breakout_n: int = int(os.getenv("BREAKOUT_N", "20"))
    atr_n: int = 14
    stop_atr: float = _f("STOP_ATR", "2.0")      # stop inicial = entrada - k*ATR
    trail_atr: float = _f("TRAIL_ATR", "3.0")    # trailing (chandelier) = máximo - k*ATR
    max_hold_candles: int = int(os.getenv("MAX_HOLD", "60"))

    # Costos
    fee: float = _f("FEE", "0.0065")             # comisión taker Bitso por lado (ajústala a tu nivel)
    slippage: float = _f("SLIPPAGE", "0.0005")

    # Riesgo
    risk_per_trade: float = _f("RISK_PER_TRADE", "0.01")   # 1% del capital en riesgo por operación
    max_alloc_per_pair: float = _f("MAX_ALLOC", "0.30")    # máx. 30% del capital en un par
    max_open: int = int(os.getenv("MAX_OPEN", "3"))
    daily_loss_limit: float = _f("DAILY_LOSS_LIMIT", "0.03")  # pausa si pierde 3% en el día
    min_order_mxn: float = _f("MIN_ORDER_MXN", "100")

    # Régimen de mercado (opcional): riesgo variable según BTC sobre/bajo su media y menos pares en mercado bajista
    regime_enabled: bool = os.getenv("REGIME", "false").lower() == "true"
    risk_bull: float = _f("RISK_BULL", "0.02")      # riesgo por operación con BTC sobre su media
    risk_bear: float = _f("RISK_BEAR", "0.01")      # riesgo por operación con BTC bajo su media
    regime_ema: int = int(os.getenv("REGIME_EMA", "200"))
    regime_book: str = os.getenv("REGIME_BOOK", "btc_mxn")
    bear_pairs: list = field(default_factory=lambda: os.getenv("BEAR_PAIRS", "btc_mxn,eth_mxn").split(","))

    paper_capital: float = _f("PAPER_CAPITAL", "10000")
    live_enabled: bool = os.getenv("LIVE_TRADING", "false").lower() == "true"  # candado 1 de 2
    state_file: str = os.getenv("STATE_FILE", "state.json")
