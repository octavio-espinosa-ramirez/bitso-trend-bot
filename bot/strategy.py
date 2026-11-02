"""Estrategia: ruptura (breakout) a favor de la tendencia, con salida por ATR.

Entrada (al cierre de una vela):
  - cierre > EMA(ema_trend)               -> solo a favor de la tendencia
  - cierre > máximo de las últimas N velas -> ruptura
  - ATR disponible
Salida (evaluada en cada vela/tick):
  - stop inicial   = entrada - stop_atr * ATR
  - trailing       = máximo alcanzado - trail_atr * ATR(entrada)   (solo sube)
  - tiempo máximo  = max_hold_candles velas
La salida por ATR deja correr las ganancias y corta pérdidas pequeñas; con comisiones de ~0.65% por lado
una estrategia de reversión de 8 velas (la anterior) casi nunca puede ganar.
"""
from .indicators import ema, atr, highest


class Strategy:
    def __init__(self, cfg):
        self.cfg = cfg

    def prepare(self, candles):
        c = [x["c"] for x in candles]
        h = [x["h"] for x in candles]
        l = [x["l"] for x in candles]
        return {"c": c, "h": h, "l": l, "ema": ema(c, self.cfg.ema_trend),
                "atr": atr(h, l, c, self.cfg.atr_n)}

    def entry_signal(self, ind, i):
        """True si al cierre de la vela i hay que comprar. Devuelve (bool, atr)."""
        e, a = ind["ema"][i], ind["atr"][i]
        hh = highest(ind["h"], self.cfg.breakout_n, i)
        if e is None or a is None or hh is None:
            return False, None
        return (ind["c"][i] > e and ind["c"][i] > hh), a

    def initial_stop(self, entry, a):
        return entry - self.cfg.stop_atr * a

    def trail(self, high_since_entry, a):
        return high_since_entry - self.cfg.trail_atr * a
