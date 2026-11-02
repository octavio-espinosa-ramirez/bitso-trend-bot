"""Uso: python research.py  -> descarga historial real y compara configuraciones (in-sample vs out-of-sample)."""
import itertools, json, sys
from bot.config import Config
from bot.data import fetch_history
from bot.backtest import simulate, walk_forward, with_params

cfg = Config()
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 540
data = {}
for tf in (3600, 14400):
    for p in cfg.pairs:
        data[(p, tf)] = fetch_history(p, tf, DAYS)
        print(p, tf, len(data[(p, tf)]), "velas", flush=True)

grid = itertools.product((3600, 14400), (50, 100, 200), (20, 40), (2.0, 3.0), (3.0, 4.5))
rows = []
for tf, ema_n, bo, st, tr in grid:
    c = with_params(cfg, ema_trend=ema_n, breakout_n=bo, stop_atr=st, trail_atr=tr)
    tr_ret = te_ret = 0; tr_n = te_n = 0; te_dd = 0
    for p in cfg.pairs:
        a, b = walk_forward(data[(p, tf)], c)
        tr_ret += a["return_pct"]; te_ret += b["return_pct"]; tr_n += a["trades"]; te_n += b["trades"]
        te_dd = max(te_dd, b["max_dd_pct"])
    rows.append(dict(tf=tf, ema=ema_n, bo=bo, stop=st, trail=tr, train=tr_ret / 3, test=te_ret / 3,
                     tr_n=tr_n, te_n=te_n, te_dd=te_dd))
rows.sort(key=lambda r: r["train"], reverse=True)
print("\nTop 12 por ENTRENAMIENTO (60% inicial) y su resultado en PRUEBA (40% final, no visto):")
for r in rows[:12]:
    print(r)
pos = [r for r in rows if r["train"] > 0 and r["test"] > 0]
print(f"\nConfigs rentables en ambos tramos: {len(pos)} de {len(rows)}")
json.dump(rows, open("research_results.json", "w"), indent=1)
