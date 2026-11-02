"""Interfaz de Telegram. SOLO responde al CHAT_ID configurado."""
import telebot
from .data import fetch_ticker


def build(cfg, st, engine):
    bot = telebot.TeleBot(cfg.token, parse_mode=None)
    mk = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("🚀 Iniciar", "🛑 Detener", "📊 Estado", "📈 Posiciones")
    mk.add("📋 Estadísticas", "🚨 Vender todo", "💰 Activar REAL", "🟡 Volver a PAPER")

    def notify(text):
        try:
            bot.send_message(cfg.chat_id, text, reply_markup=mk)
        except Exception:
            pass

    def allowed(m):
        return m.chat.id == cfg.chat_id

    def status():
        d = st.d
        prices = {}
        for b in d["positions"]:
            try:
                prices[b] = fetch_ticker(b)["last"]
            except Exception:
                pass
        eq = engine.equity(prices)
        mode = "💰 REAL" if (d["live"] and cfg.live_enabled) else "🟡 PAPER"
        ret = (eq / d["start_capital"] - 1) * 100
        reg = ""
        if cfg.regime_enabled:
            try:
                b = engine.regime_bull()
                reg = f"\nRégimen: {'📈 ALCISTA' if b else '📉 BAJISTA'} · riesgo {(cfg.risk_bull if b else cfg.risk_bear)*100:.1f}%" + ("" if b else f" · solo {', '.join(x.upper() for x in cfg.bear_pairs)}")
            except Exception:
                pass
        return (f"{'🟢 ACTIVO' if d['active'] else '🔴 DETENIDO'} · {mode}\nPares: {', '.join(p.upper() for p in cfg.pairs)}\n"
                f"Velas: {cfg.timeframe//3600}h · Posiciones: {len(d['positions'])}/{cfg.max_open}{reg}\n"
                f"Capital: {eq:,.0f} MXN ({ret:+.2f}% vs inicio)" + ("\n⛔ Pausado por pérdida diaria" if d["halted"] else ""))

    @bot.message_handler(commands=["start", "help"])
    def _start(m):
        if allowed(m):
            bot.reply_to(m, "Bot v4 listo.\n" + status(), reply_markup=mk)

    @bot.message_handler(func=lambda m: True)
    def _all(m):
        if not allowed(m):
            return
        t, d = m.text or "", st.d
        if "Iniciar" in t:
            d["active"] = True; st.save(); bot.reply_to(m, "✅ Estrategia activa\n" + status(), reply_markup=mk)
        elif "Detener" in t:
            d["active"] = False; st.save(); bot.reply_to(m, "🛑 Detenida (las posiciones abiertas siguen; usa Vender todo para cerrarlas).", reply_markup=mk)
        elif "Estado" in t:
            bot.reply_to(m, status(), reply_markup=mk)
        elif "Posiciones" in t:
            if not d["positions"]:
                bot.reply_to(m, "Sin posiciones abiertas.", reply_markup=mk)
            for b, p in d["positions"].items():
                try:
                    px = fetch_ticker(b)["last"]
                except Exception:
                    px = p["entry"]
                stop = max(p["stop"], engine.strategy.trail(p["high"], p["atr"]))
                bot.send_message(m.chat.id, f"{b.upper()} [{p['mode']}]\nEntrada {p['entry']:,.2f} · Ahora {px:,.2f} ({(px/p['entry']-1)*100:+.2f}%)\nStop actual {stop:,.2f}", reply_markup=mk)
        elif "Estadísticas" in t:
            tr = d["trades"]
            if not tr:
                bot.reply_to(m, "Aún no hay operaciones cerradas.", reply_markup=mk)
            else:
                w = [x for x in tr if x["pnl"] > 0]; l = [x for x in tr if x["pnl"] <= 0]
                gw, gl = sum(x["mxn"] for x in w), -sum(x["mxn"] for x in l)
                bot.reply_to(m, f"Operaciones: {len(tr)}\nGanadoras: {len(w)/len(tr)*100:.0f}%\nProfit factor: {gw/gl if gl else float('inf'):.2f}\nResultado neto: {sum(x['mxn'] for x in tr):+,.0f} MXN", reply_markup=mk)
        elif "Vender todo" in t:
            engine.sell_all("manual"); bot.reply_to(m, "Listo: cierro todas las posiciones.", reply_markup=mk)
        elif "Activar REAL" in t:
            if not cfg.live_enabled:
                bot.reply_to(m, "Bloqueado: pon LIVE_TRADING=true en las variables de entorno y reinicia (candado 1 de 2).", reply_markup=mk)
            else:
                d["live_pending"] = True
                bot.reply_to(m, "⚠️ Operarás con dinero REAL en Bitso. Escribe exactamente: CONFIRMO REAL", reply_markup=mk)
        elif t.strip() == "CONFIRMO REAL" and d.get("live_pending"):
            d["live"], d["live_pending"] = True, False; st.save()
            bot.reply_to(m, "💰 Modo REAL activado. Las nuevas compras usarán dinero real.", reply_markup=mk)
        elif "Volver a PAPER" in t:
            d["live"] = False; st.save(); bot.reply_to(m, "🟡 Modo PAPER (las posiciones reales abiertas se cierran solas en modo real).", reply_markup=mk)

    return bot, notify
