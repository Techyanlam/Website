#!/usr/bin/env python3
# BETTEREAT sold-list sync: Feishu Base C table -> bettereat_sold_data.json
# Reads C_每日分配及出貨記錄 via Feishu Open API, keeps records of the LATEST
# date with 已銷售 > 0, writes the JSON the web page reads.
# Credentials come from env: FEISHU_APP_ID / FEISHU_APP_SECRET (GitHub Secrets in Actions).
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU = "https://open.feishu.cn"
APP_TOKEN = "RunBbMsGvaPacBsohCfcipJIn9e"      # BETTEREAT - Dessert base
C_TABLE = "tblaMp65e2HInaqx"                    # C_每日分配及出貨記錄
OUT = os.environ.get("OUT_PATH", "bettereat_sold_data.json")
HKT = timezone(timedelta(hours=8))

def call(method, url, token=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def get_token():
    r = call("POST", f"{FEISHU}/open-apis/auth/v3/tenant_access_token/internal",
             payload={"app_id": APP_ID, "app_secret": APP_SECRET})
    if r.get("code") != 0:
        raise RuntimeError(f"token failed: {r.get('code')} {r.get('msg')}")
    return r["tenant_access_token"]

def list_records(token):
    items, page = [], None
    while True:
        url = f"{FEISHU}/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{C_TABLE}/records?page_size=500"
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

def date_of(v):
    # date fields arrive as ms epoch; text fields as string
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, tz=HKT).strftime("%Y-%m-%d")
    s = text_of(v)
    return s.replace("/", "-")[:10]

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def main():
    token = get_token()
    by_date = {}
    for it in list_records(token):
        f = it.get("fields") or {}
        sold = num(f.get("已銷售"))
        if sold is None or sold <= 0:
            continue
        d = date_of(f.get("日期"))
        if not d:
            continue
        if sold == int(sold):
            sold = int(sold)
        by_date.setdefault(d, []).append({
            "store": text_of(f.get("門店代號")),
            "product_code": text_of(f.get("產品編號")),
            "product_name": text_of(f.get("產品名稱")),
            "unit": text_of(f.get("計量單位")),
            "allocated_pans": num(f.get("分配量")),
            "no_of_pcs": num(f.get("No of pcs")),
            "remaining_pcs": num(f.get("剩餘量")),
            "sold_pcs": sold,
        })
    if not by_date:
        print("no sold records found; leaving existing JSON untouched")
        return
    for d in by_date:
        by_date[d].sort(key=lambda r: (r["store"], r["product_code"]))
    latest = max(by_date)
    out = {
        "source": "BETTEREAT-Feishu-Base",
        "date": latest,
        "generated_at": datetime.now(HKT).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "records": by_date[latest],
        "history": {d: by_date[d] for d in sorted(by_date)},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: latest={latest} dates={len(by_date)} "
          f"total_records={sum(len(v) for v in by_date.values())}")

if __name__ == "__main__":
    main()
