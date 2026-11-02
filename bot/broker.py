"""Brokers. PaperBroker simula con comisión y slippage; BitsoBroker manda órdenes de mercado reales."""
import hashlib, hmac, json, time
import requests
from .data import BASE


class PaperBroker:
    def __init__(self, cfg):
        self.cfg = cfg

    def buy(self, book, mxn, ref_price):
        px = ref_price * (1 + self.cfg.slippage)
        qty = mxn * (1 - self.cfg.fee) / px
        return {"price": px, "qty": qty, "spent": mxn}

    def sell(self, book, qty, ref_price):
        px = ref_price * (1 - self.cfg.slippage)
        return {"price": px, "qty": qty, "proceeds": qty * px * (1 - self.cfg.fee)}


class BitsoBroker:
    def __init__(self, cfg):
        self.cfg = cfg

    def _req(self, method, path, payload=None):
        nonce = str(int(time.time() * 1000))
        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        sig = hmac.new(self.cfg.api_secret.encode(), (nonce + method + path + body).encode(), hashlib.sha256).hexdigest()
        h = {"Authorization": f"Bitso {self.cfg.api_key}:{nonce}:{sig}", "Content-Type": "application/json"}
        r = requests.request(method, BASE + path, headers=h, data=body or None, timeout=15)
        j = r.json()
        if not j.get("success"):
            raise RuntimeError(f"Bitso: {j.get('error')}")
        return j["payload"]

    def balance(self, cur):
        for b in self._req("GET", "/v3/balance/")["balances"]:
            if b["currency"] == cur:
                return float(b["available"])
        return 0.0

    def _fill(self, oid, tries=6):
        for _ in range(tries):
            time.sleep(1)
            trades = self._req("GET", f"/v3/order_trades/{oid}")
            if trades:
                qty = sum(float(t["major"]) for t in trades)          # +compra / -venta
                mxn = sum(float(t["minor"]) for t in trades)
                fee_mxn = sum(float(t["fees_amount"]) for t in trades if t["fees_currency"] == "mxn")
                fee_base = sum(float(t["fees_amount"]) for t in trades if t["fees_currency"] != "mxn")
                return abs(qty), abs(mxn), fee_mxn, fee_base
        raise RuntimeError(f"Orden {oid} sin ejecuciones confirmadas; revisa Bitso manualmente")

    def buy(self, book, mxn, ref_price):
        oid = self._req("POST", "/v3/orders", {"book": book, "side": "buy", "type": "market", "minor": f"{mxn:.2f}"})["oid"]
        qty, spent, fee_mxn, fee_base = self._fill(oid)
        net = qty - fee_base
        return {"price": spent / qty, "qty": net, "spent": spent + fee_mxn, "oid": oid}

    def sell(self, book, qty, ref_price):
        major = f"{qty:.8f}"
        oid = self._req("POST", "/v3/orders", {"book": book, "side": "sell", "type": "market", "major": major})["oid"]
        q, got, fee_mxn, _ = self._fill(oid)
        return {"price": got / q, "qty": q, "proceeds": got - fee_mxn, "oid": oid}
