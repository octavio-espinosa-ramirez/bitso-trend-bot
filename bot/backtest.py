"""Backtester sobre velas reales con comisiones y slippage.

Reglas anti-trampa: la señal se calcula al CIERRE de la vela i y se ejecuta en la APERTURA de i+1;
si el stop y el mínimo se tocan en la misma vela se asume el stop (peor caso).
"""
import copy
from .strategy import Strategy


def simulate(candles, cfg, start_idx=0, end_idx=None):
    s = Strategy(cfg)
    ind = s.prepare(candles)
    n = end_idx or len(candles)
    equity, peak, max_dd = 1.0, 1.0, 0.0
    trades, pos = [], None
    for i in range(max(start_idx, 1), n):
        k = candles[i]
        if pos:
            stop = max(pos["stop"], s.trail(pos["high"], pos["atr"]))
            exit_px = None
            if k["o"] <= stop:
                exit_px = k["o"]
            elif k["l"] <= stop:
                exit_px = stop
            elif i - pos["i"] >= cfg.max_hold_candles:
                exit_px = k["c"]
            if exit_px is not None:
                px = exit_px * (1 - cfg.slippage)
                gross = px / pos["entry"] - 1
                net = (1 - cfg.fee) * (px / pos["entry"]) / (1 + cfg.fee) - 1
                equity *= 1 + pos["size"] * net
                trades.append({"pnl": net, "gross": gross, "size": pos["size"], "bars": i - pos["i"]})
                pos = None
            else:
                pos["high"] = max(pos["high"], k["h"])
        if pos is None and i + 1 < n:
            ok, a = s.entry_signal(ind, i)
            if ok:
                entry = candles[i + 1]["o"] * (1 + cfg.slippage)
                stop = s.initial_stop(entry, a)
                dist = (entry - stop) / entry
                if dist > 0:
                    size = min(cfg.risk_per_trade / (dist + 2 * cfg.fee), cfg.max_alloc_per_pair)
                    pos = {"i": i + 1, "entry": entry, "stop": stop, "high": candles[i + 1]["h"],
                           "atr": a, "size": size}
        peak = max(peak, equity)
        max_dd = max(max_dd, 1 - equity / peak)
    return summarize(trades, equity, max_dd, candles, start_idx, n)


def summarize(trades, equity, max_dd, candles, a, b):
    wins = [t["pnl"] * t["size"] for t in trades if t["pnl"] > 0]
    losses = [-t["pnl"] * t["size"] for t in trades if t["pnl"] <= 0]
    bh = candles[b - 1]["c"] / candles[max(a, 0)]["o"] - 1
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0.0,
        "profit_factor": (sum(wins) / sum(losses)) if losses and sum(losses) > 0 else (float("inf") if wins else 0.0),
        "return_pct": (equity - 1) * 100,
        "max_dd_pct": max_dd * 100,
        "avg_trade_pct": (sum(t["pnl"] for t in trades) / len(trades) * 100) if trades else 0.0,
        "buy_hold_pct": bh * 100,
    }


def walk_forward(candles, cfg, split=0.6):
    """Divide en entrenamiento / prueba para detectar sobreajuste."""
    cut = int(len(candles) * split)
    return simulate(candles, cfg, 0, cut), simulate(candles, cfg, cut, len(candles))


def with_params(cfg, **kw):
    c = copy.copy(cfg)
    for k, v in kw.items():
        setattr(c, k, v)
    return c
