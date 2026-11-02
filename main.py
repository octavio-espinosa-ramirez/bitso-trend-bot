import logging, threading, time
from bot.config import Config
from bot.state import State
from bot.engine import Engine
from bot import telegram_ui

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    cfg = Config()
    if not cfg.token:
        raise SystemExit("Falta TOKEN de Telegram en .env")
    st = State(cfg.state_file, cfg.paper_capital)
    engine = Engine(cfg, st, lambda t: None)
    bot, notify = telegram_ui.build(cfg, st, engine)
    engine.notify = notify
    threading.Thread(target=engine.run_forever, daemon=True).start()
    notify("🤖 Bot v4 iniciado. " + ("Modo REAL habilitado por entorno." if cfg.live_enabled else "Modo PAPER."))
    while True:
        try:
            bot.delete_webhook(drop_pending_updates=True)
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logging.exception("polling")
            time.sleep(5)


if __name__ == "__main__":
    main()
