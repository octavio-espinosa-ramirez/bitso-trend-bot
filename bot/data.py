"""Descarga de velas OHLC públicas de Bitso (no requiere llaves)."""
import time
import requests

BASE = "https://api.bitso.com"


def fetch_candles(book, bucket, start_ms=None, end_ms=None, timeout=20):
    """Devuelve velas [{t,o,h,l,c,v}] en orden cronológico."""
    params = {"book": book, "time_bucket": bucket}
    if start_ms:
        params["start"] = int(start_ms)
    if end_ms:
        params["end"] = int(end_ms)
    r = requests.get(f"{BASE}/v3/ohlc/", params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json().get("payload", [])
    out = [{"t": int(c["bucket_start_time"]), "o": float(c["first_rate"]), "h": float(c["max_rate"]),
            "l": float(c["min_rate"]), "c": float(c["last_rate"]), "v": float(c["volume"])} for c in data]
    out.sort(key=lambda x: x["t"])
    return out


def fetch_history(book, bucket, days=365, pause=0.3):
    """Descarga historial paginando por ventanas."""
    end = int(time.time() * 1000)
    start = end - days * 86400 * 1000
    step = bucket * 1000 * 400
    got, cur = {}, start
    while cur < end:
        for c in fetch_candles(book, bucket, cur, min(cur + step, end)):
            got[c["t"]] = c
        cur += step
        time.sleep(pause)
    return [got[k] for k in sorted(got)]


def fetch_ticker(book, timeout=10):
    r = requests.get(f"{BASE}/v3/ticker/", params={"book": book}, timeout=timeout)
    r.raise_for_status()
    p = r.json()["payload"]
    return {"last": float(p["last"]), "bid": float(p["bid"]), "ask": float(p["ask"])}
