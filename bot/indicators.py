"""Indicadores en Python puro (sin numpy). Listas de floats, mismo largo que la entrada (None si no hay datos)."""


def ema(values, n):
    out, k, prev = [], 2 / (n + 1), None
    for i, v in enumerate(values):
        if i < n - 1:
            out.append(None)
        elif i == n - 1:
            prev = sum(values[:n]) / n
            out.append(prev)
        else:
            prev = v * k + prev * (1 - k)
            out.append(prev)
    return out


def rsi(values, n=14):
    """RSI de Wilder."""
    out = [None] * len(values)
    if len(values) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(values)):
        d = values[i] - values[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def atr(highs, lows, closes, n=14):
    """ATR de Wilder."""
    out = [None] * len(closes)
    if len(closes) <= n:
        return out
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    prev = sum(tr[1:n + 1]) / n
    out[n] = prev
    for i in range(n + 1, len(closes)):
        prev = (prev * (n - 1) + tr[i]) / n
        out[i] = prev
    return out


def highest(values, n, i):
    """Máximo de las n velas ANTERIORES a i (sin incluir i)."""
    if i < n:
        return None
    return max(values[i - n:i])
