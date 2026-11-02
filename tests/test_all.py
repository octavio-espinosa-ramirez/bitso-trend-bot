import os, sys, tempfile, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot.config import Config
from bot.indicators import rsi, ema, atr
from bot.backtest import simulate, with_params
from bot.state import State
from bot import engine as eng


def candles(n=600, drift=0.001, seed=1):
    random.seed(seed); p = 100.0; out = []
    for i in range(n):
        o = p; p *= 1 + random.gauss(drift, 0.01)
        out.append({"t": i * 14400000, "o": o, "h": max(o, p) * 1.003, "l": min(o, p) * 0.997, "c": p, "v": 1})
    return out


def test_rsi_bounds_and_known():
    up = [float(i) for i in range(1, 40)]
    assert rsi(up)[-1] == 100.0
    r = rsi(candles_close())
    assert all(0 <= x <= 100 for x in r if x is not None)


def candles_close():
    return [c["c"] for c in candles()]


def test_ema_atr_lengths():
    c = candles(); cl = [x["c"] for x in c]
    assert len(ema(cl, 50)) == len(cl) and ema(cl, 50)[48] is None and ema(cl, 50)[49] is not None
    a = atr([x["h"] for x in c], [x["l"] for x in c], cl)
    assert a[-1] > 0


def test_backtest_costs_reduce_return():
    c = candles(1500, 0.0015)
    cfg = Config()
    free = simulate(c, with_params(cfg, fee=0, slippage=0))
    paid = simulate(c, with_params(cfg, fee=0.0065))
    assert free["trades"] > 0 and free["return_pct"] > paid["return_pct"]


def test_no_lookahead():
    """Cambiar velas FUTURAS no debe alterar operaciones ya cerradas antes de ese punto."""
    c = candles(800, 0.001); cfg = Config()
    a = simulate(c, cfg, 0, 500)
    c2 = [dict(x) for x in c]
    for x in c2[500:]:
        x["c"] *= 3; x["h"] *= 3; x["l"] *= 3; x["o"] *= 3
    b = simulate(c2, cfg, 0, 500)
    assert a == b


def test_state_atomic_and_reload():
    d = tempfile.mkdtemp(); p = os.path.join(d, "s.json")
    s = State(p, 5000); s.d["cash"] = 4321; s.save()
    assert State(p, 5000).d["cash"] == 4321
    open(p, "w").write("{corrupto")
    assert State(p, 5000).d["cash"] == 5000 and os.path.exists(p + ".corrupt")


def test_engine_open_stop_close(monkeypatch=None):
    d = tempfile.mkdtemp(); cfg = Config(); cfg.pairs = ["btc_mxn"]
    msgs = []; st = State(os.path.join(d, "s.json"), 10000); st.d["active"] = True
    e = eng.Engine(cfg, st, msgs.append)
    price = {"v": 1000.0}
    eng.fetch_ticker = lambda b: {"last": price["v"], "bid": price["v"] * 0.999, "ask": price["v"] * 1.001}
    e.open_position("btc_mxn", 20.0, 1000.0)
    p = st.d["positions"]["btc_mxn"]
    assert p["qty"] > 0 and st.d["cash"] < 10000 and p["stop"] < p["entry"]
    assert p["cost"] <= 10000 * cfg.max_alloc_per_pair + 1e-6
    price["v"] = p["stop"] * 0.99          # cae bajo el stop
    e.tick()
    assert "btc_mxn" not in st.d["positions"] and len(st.d["trades"]) == 1 and st.d["trades"][0]["pnl"] < 0
    assert abs(st.d["cash"] - 10000) < 400  # pérdida acotada (riesgo ~1% + costos)


def test_daily_loss_halts():
    d = tempfile.mkdtemp(); cfg = Config(); msgs = []
    st = State(os.path.join(d, "s.json"), 10000)
    e = eng.Engine(cfg, st, msgs.append)
    assert e._risk_ok({}) is True
    st.d["cash"] = 10000 * (1 - cfg.daily_loss_limit) - 1
    assert e._risk_ok({}) is False and st.d["halted"]


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-q"]))


def test_regime_riesgo():
    import tempfile, os
    from bot.state import State
    from bot.engine import Engine
    cfg = Config(); cfg.regime_enabled = True; cfg.risk_bull = 0.02; cfg.risk_bear = 0.01
    cfg.bear_pairs = ["btc_mxn", "eth_mxn"]
    e = Engine(cfg, State(os.path.join(tempfile.mkdtemp(), "s.json"), 10000), lambda m: None)
    import time
    e._reg = (True, time.time())
    assert e.risk_for("xrp_mxn") == 0.02
    e._reg = (False, time.time())
    assert e.risk_for("btc_mxn") == 0.01 and e.risk_for("xrp_mxn") is None
    cfg.regime_enabled = False
    assert e.risk_for("xrp_mxn") == cfg.risk_per_trade
