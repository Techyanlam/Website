#!/usr/bin/env python3
# BETTEREAT sold-list sync v3 — SNAPSHOT archive.
# The Feishu C table's date field is a TODAY() formula (always "today"), so the
# website keeps its own frozen record instead: every run preserves the existing
# history in bettereat_sold_data.json and appends today's snapshot keyed by the
# RUN date (HKT). A snapshot, once written, is never changed by later runs —
# except that a re-run on the SAME day refreshes that day's snapshot (end-of-day
# state wins). If the data is identical to the latest snapshot, no new day is
# created (avoids duplicating the same list on days with no new data entry).
# Credentials from env: FEISHU_APP_ID / FEISHU_APP_SECRET (GitHub Secrets).
import json, os, urllib.request
from datetime import datetime, timezone, timedelta

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU = "https://open.feishu.cn"
APP_TOKEN = "RunBbMsGvaPacBsohCfcipJIn9e"      # BETTEREAT - Dessert base
C_TABLE = "tblaMp65e2HInaqx"                    # C_每日分配及出貨記錄
OUT = os.environ.get("OUT_PATH", "bettereat_sold_data.json")
HKT = timezone(timedelta(hours=8))
BOGUS_KEYS = {"1970-01-01", ""}

def call(method, url, token=None, payload=None):
    import time, http.client, urllib.error
    data = json.dumps(payload).encode() if payload is not None else None
    last = None
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept-Encoding", "gzip")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError) as e:
            last = e
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"request failed after 3 attempts: {last}")

def get_token():
    r = call("POST", f"{FEISHU}/open-apis/auth/v3/tenant_access_token/internal",
             payload={"app_id": APP_ID, "app_secret": APP_SECRET})
    if r.get("code") != 0:
        raise RuntimeError(f"token failed: {r.get('code')} {r.get('msg')}")
    return r["tenant_access_token"]

def list_records(token):
    # small pages + gzip + retries: long responses get cut by the egress proxy
    items, page = [], None
    while True:
        url = f"{FEISHU}/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{C_TABLE}/records?page_size=50"
        if page:
            url += f"&page_token={page}"
        r = call("GET", url, token=token)
        if r.get("code") != 0:
            raise RuntimeError(f"list records failed: {r.get('code')} {r.get('msg')}")
        d = r.get("data") or {}
        items.extend(d.get("items") or [])
        if not d.get("has_more"):
            return items
        page = d.get("page_token")

def text_of(v):
    if isinstance(v, list):
        return "".join(str(x.get("text", "")) for x in v if isinstance(x, dict))
    return "" if v is None else str(v)

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def fetch_current(token):
    rows = []
    for it in list_records(token):
        f = it.get("fields") or {}
        sold = num(f.get("已銷售"))
        if sold is None or sold <= 0:
            continue
        if sold == int(sold):
            sold = int(sold)
        rows.append({
            "store": text_of(f.get("門店代號")),
            "product_code": text_of(f.get("產品編號")),
            "product_name": text_of(f.get("產品名稱")),
            "unit": text_of(f.get("計量單位")),
            "allocated_pans": num(f.get("分配量")),
            "no_of_pcs": num(f.get("No of pcs")),
            "remaining_pcs": num(f.get("剩餘量")),
            "sold_pcs": sold,
        })
    rows.sort(key=lambda r: (r["store"], r["product_code"]))
    return rows

def main():
    run_date = datetime.now(HKT).strftime("%Y-%m-%d")
    history = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT, encoding="utf-8"))
            history = {k: v for k, v in (prev.get("history") or {}).items()
                       if k not in BOGUS_KEYS}
        except Exception:
            history = {}
    rows = fetch_current(get_token())
    if not rows:
        print("no sold records found; leaving existing JSON untouched")
        return
    latest_key = max(history) if history else None
    if latest_key and history[latest_key] == rows and latest_key != run_date:
        # data unchanged since last snapshot -> keep the archive as-is,
        # only refresh the timestamp
        out_date = latest_key
        print(f"data identical to snapshot {latest_key}; no new day created")
    else:
        history[run_date] = rows
        out_date = run_date
    out = {
        "source": "BETTEREAT-Feishu-Base",
        "date": out_date,
        "generated_at": datetime.now(HKT).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "records": history[out_date],
        "history": {d: history[d] for d in sorted(history)},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: date={out_date} run_date={run_date} "
          f"history_days={len(history)} records={len(rows)}")

if __name__ == "__main__":
    main()
