"""Motor: evalúa señales al cierre de cada vela, gestiona stops en cada ciclo, aplica riesgo y persiste estado."""
import logging, threading, time
from datetime import datetime, timezone
from .broker import PaperBroker, BitsoBroker
from .data import fetch_candles, fetch_ticker
from .strategy import Strategy
from .indicators import ema

log = logging.getLogger("engine")


class Engine:
    def __init__(self, cfg, state, notify):
        self.cfg, self.st, self.notify = cfg, state, notify
        self.strategy = Strategy(cfg)
        self.paper, self.live = PaperBroker(cfg), BitsoBroker(cfg)
        self.last_candle = {}
        self.lock = threading.RLock()
        self._reg = None          # (alcista: bool, ts_consulta)

    # ---- utilidades
    @property
    def broker(self):
        return self.live if (self.st.d["live"] and self.cfg.live_enabled) else self.paper

    def equity(self, prices):
        d = self.st.d
        return d["cash"] + sum(p["qty"] * prices.get(b, p["entry"]) for b, p in d["positions"].items())

    def _candles(self, book):
        need = max(self.cfg.ema_trend, self.cfg.breakout_n, self.cfg.atr_n) + 30
        end = int(time.time() * 1000)
        c = fetch_candles(book, self.cfg.timeframe, end - (need + 5) * self.cfg.timeframe * 1000, end)
        # descarta la vela en formación
        return [x for x in c if x["t"] + self.cfg.timeframe * 1000 <= end]

    def regime_bull(self):
        """True si el cierre diario de BTC está sobre su EMA(regime_ema). Se consulta cada 10 min; si falla, usa el último valor (o bajista)."""
        now = time.time()
        if self._reg and now - self._reg[1] < 600:
            return self._reg[0]
        try:
            n = self.cfg.regime_ema + 80
            end = int(now * 1000)
            c = fetch_candles(self.cfg.regime_book, self.cfg.timeframe, end - n * self.cfg.timeframe * 1000, end)
            c = [x for x in c if x["t"] + self.cfg.timeframe * 1000 <= end]
            cl = [x["c"] for x in c]
            e = ema(cl, self.cfg.regime_ema)
            if len(cl) < self.cfg.regime_ema + 1 or e[-1] is None:
                raise ValueError("pocas velas para el régimen")
            bull = cl[-1] > e[-1]
        except Exception as ex:
            log.warning("régimen: %s", ex)
            bull = self._reg[0] if self._reg else False
            self._reg = (bull, now - 540)  # reintenta en ~1 min
            return bull
        if self._reg and self._reg[0] != bull:
            self.notify(f"🔄 Régimen: {'ALCISTA' if bull else 'BAJISTA'} ({self.cfg.regime_book.upper()} {'sobre' if bull else 'bajo'} su media de {self.cfg.regime_ema} d). "
                        f"Riesgo por operación: {(self.cfg.risk_bull if bull else self.cfg.risk_bear)*100:.1f}%")
        self._reg = (bull, now)
        return bull

    def risk_for(self, book):
        """Riesgo por operación para este par según el régimen; None = no abrir."""
        if not self.cfg.regime_enabled:
            return self.cfg.risk_per_trade
        if self.regime_bull():
            return self.cfg.risk_bull
        return self.cfg.risk_bear if book in self.cfg.bear_pairs else None

    def _risk_ok(self, prices):
        d, today = self.st.d, datetime.now(timezone.utc).strftime("%Y-%m-%d")
        eq = self.equity(prices)
        if d["day"] != today:
            d["day"], d["day_start_equity"], d["halted"] = today, eq, False
        if eq < d["day_start_equity"] * (1 - self.cfg.daily_loss_limit):
            if not d["halted"]:
                d["halted"] = True
                self.notify("⛔ Límite de pérdida diaria alcanzado. No abriré nuevas posiciones hasta mañana (UTC).")
        return not d["halted"]

    # ---- operaciones
    def open_position(self, book, a, last_close):
        d = self.st.d
        prices = {b: p["entry"] for b, p in d["positions"].items()}
        if book in d["positions"] or len(d["positions"]) >= self.cfg.max_open or not self._risk_ok(prices):
            return
        risk = self.risk_for(book)
        if risk is None:
            return
        t = fetch_ticker(book)
        entry = t["ask"]
        stop = self.strategy.initial_stop(entry, a)
        dist = (entry - stop) / entry
        eq = self.equity({b: p["entry"] for b, p in d["positions"].items()})
        mxn = min(eq * risk / (dist + 2 * self.cfg.fee), eq * self.cfg.max_alloc_per_pair, d["cash"])
        if mxn < self.cfg.min_order_mxn:
            return
        f = self.broker.buy(book, mxn, entry)
        d["cash"] -= f["spent"]
        d["positions"][book] = {"entry": f["price"], "qty": f["qty"], "stop": self.strategy.initial_stop(f["price"], a),
                                "high": f["price"], "atr": a, "opened": time.time(), "bars": 0,
                                "cost": f["spent"], "mode": "REAL" if self.broker is self.live else "PAPER"}
        self.st.save()
        self.notify(f"🟢 COMPRA {book.upper()} [{d['positions'][book]['mode']}]\nPrecio {f['price']:,.2f} · {f['spent']:,.0f} MXN\n"
                    f"Stop inicial {d['positions'][book]['stop']:,.2f}")

    def close_position(self, book, price, reason):
        d = self.st.d
        p = d["positions"].get(book)
        if not p:
            return
        broker = self.live if p["mode"] == "REAL" else self.paper
        f = broker.sell(book, p["qty"], price)
        d["cash"] += f["proceeds"]
        pnl = f["proceeds"] / p["cost"] - 1
        d["trades"].append({"book": book, "pnl": pnl, "mxn": f["proceeds"] - p["cost"], "reason": reason,
                            "closed": time.time(), "mode": p["mode"]})
        del d["positions"][book]
        self.st.save()
        self.notify(f"🔴 VENTA {book.upper()} [{p['mode']}] · {reason}\nPrecio {f['price']:,.2f} · Resultado {pnl*100:+.2f}% ({f['proceeds']-p['cost']:+,.0f} MXN)")

    def sell_all(self, reason="manual"):
        with self.lock:
            for book in list(self.st.d["positions"]):
                try:
                    self.close_position(book, fetch_ticker(book)["bid"], reason)
                except Exception as e:
                    self.notify(f"❌ No pude vender {book}: {e}")

    # ---- ciclo
    def tick(self):
        with self.lock:
            d = self.st.d
            if not d["active"]:
                return
            prices = {}
            for book in self.cfg.pairs:
                try:
                    prices[book] = fetch_ticker(book)["last"]
                except Exception as e:
                    log.warning("ticker %s: %s", book, e)
            # 1) gestionar posiciones abiertas (cada ciclo)
            for book, p in list(d["positions"].items()):
                px = prices.get(book)
                if not px:
                    continue
                p["high"] = max(p["high"], px)
                stop = max(p["stop"], self.strategy.trail(p["high"], p["atr"]))
                if px <= stop:
                    self.close_position(book, fetch_ticker(book)["bid"], "stop/trailing")
            # 2) señales nuevas (solo cuando cierra una vela nueva)
            for book in self.cfg.pairs:
                try:
                    c = self._candles(book)
                    if len(c) < self.cfg.ema_trend + 2 or self.last_candle.get(book) == c[-1]["t"]:
                        continue
                    self.last_candle[book] = c[-1]["t"]
                    if book in d["positions"]:
                        d["positions"][book]["bars"] += 1
                        if d["positions"][book]["bars"] >= self.cfg.max_hold_candles:
                            self.close_position(book, fetch_ticker(book)["bid"], "tiempo máximo")
                        continue
                    ok, a = self.strategy.entry_signal(self.strategy.prepare(c), len(c) - 1)
                    if ok:
                        self.open_position(book, a, c[-1]["c"])
                except Exception as e:
                    log.exception("señal %s", book)
                    self.notify(f"⚠️ Error en {book}: {str(e)[:150]}")
            self.st.save()

    def run_forever(self, interval=30):
        fails = 0
        while True:
            try:
                self.tick()
                fails = 0
            except Exception as e:
                fails += 1
                log.exception("tick")
                if fails in (3, 10):
                    self.notify(f"⚠️ El motor ha fallado {fails} veces seguidas: {str(e)[:150]}")
            time.sleep(interval if fails == 0 else min(300, interval * 2 ** min(fails, 4)))
