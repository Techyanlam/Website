#!/usr/bin/env python3
"""Upsert 一筆 Outbound Record：按「HKSLI no」搜尋，找到就更新，唔存在就新增。

輸入（環境變數）：
    LARK_APP_ID / LARK_APP_SECRET —— Lark 自建應用憑證（GitHub Secrets）
    HKSLI_NO         —— Invoice No.（必填）            → 「HKSLI no」
    CUSTOMER_NAME    —— Ship To 公司名                → 「Customer Name」
    SHIP_ADDRESS     —— 送貨地址                      → 「送貨地址」
    CONTACT_NAME     —— Ship To Attn                  → 「Contact Name」
    DELIVERY_DEADLINE—— Invoice Date（如 22-04-2026） → 「Delivery Deadline」
    DN_NO            —— DN No.（如 HKLDN26040473）     → 「DN#」
    TOTAL_DN_QTY     —— Total Qty（如 1200）           → 「Total DN Qty」
    LOCATION         —— 地區簡稱（如 新界-粉嶺）        → 「Location」
                       （單選欄：只寫入真實存在嘅選項，否則跳過並報告）
行為：
    - 先讀取表格欄位清單，只寫入真實存在嘅欄（唔存在嘅會跳過並報告）
    - 日期型欄位（type 5）：將 DD-MM-YYYY / DD/MM/YYYY / YYYY-MM-DD 轉做毫秒 timestamp
    - 數字型欄位（type 2）：抽出數字寫入
    - 用 records/search 以 HKSLI no 精確搜尋：有命中 → PUT 更新；無 → POST 新增
    - （v13 起唔再上傳 PDF 附件，淨寫資料欄）
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

APP_ID = os.environ["LARK_APP_ID"]
APP_SECRET = os.environ["LARK_APP_SECRET"]
APP_TOKEN = "SWSQbZibjaHSTqsWlbqlB4sHg9e"   # Labware Outbound Record V3.0
TABLE_ID = "tblmmHsnTTzufnUq"               # Outbound Record
API = "https://open.larksuite.com/open-apis"
HKT = timezone(timedelta(hours=8))

# Lark bitable 欄位類型：1=文本 2=數字 3=單選 4=多選 5=日期
TYPE_TEXT, TYPE_NUMBER, TYPE_DATE = 1, 2, 5

DOC_NO = os.environ.get("HKSLI_NO", "").strip()

# (Lark 欄名, 環境變數, 處理方式)
FIELD_SPECS = [
    ("HKSLI no", "HKSLI_NO", "text"),
    ("Customer Name", "CUSTOMER_NAME", "text"),
    ("送貨地址", "SHIP_ADDRESS", "text"),
    ("Contact Name", "CONTACT_NAME", "text"),
    ("Delivery Deadline", "DELIVERY_DEADLINE", "date"),
    ("DN#", "DN_NO", "text"),
    ("Total DN Qty", "TOTAL_DN_QTY", "number"),
    ("Location", "LOCATION", "select"),
]

if not DOC_NO:
    print("ERROR: HKSLI_NO is required", file=sys.stderr)
    sys.exit(1)


def api(method, path, body=None, token=None, retries=3):
    data = json.dumps(body).encode() if body is not None else None
    last_err = None
    for attempt in range(retries):
        try:
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(
                API + path, method=method, data=data, headers=headers
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.load(resp)
            if result.get("code") != 0:
                raise RuntimeError(f"{method} {path} -> {result}")
            return result
        except Exception as e:  # noqa: BLE001 - transient network/API errors
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{method} {path} failed after {retries} retries: {last_err}")


def to_timestamp_ms(value):
    """DD-MM-YYYY / DD/MM/YYYY / YYYY-MM-DD → 毫秒 timestamp（HKT 午夜）。"""
    value = value.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d",
                "%d-%m-%y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=HKT)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def to_number(value):
    num = re.sub(r"[^\d.\-]", "", value.strip())
    if not num:
        raise ValueError(f"no number in: {value!r}")
    f = float(num)
    return int(f) if f.is_integer() else f


def main():
    token = api(
        "POST",
        "/auth/v3/tenant_access_token/internal",
        {"app_id": APP_ID, "app_secret": APP_SECRET},
    )["tenant_access_token"]

    # 讀取欄位清單：{欄名: {"type": int, "options": [單選選項名]}}
    field_meta = {}
    page_token = None
    while True:
        path = f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields?page_size=100"
        if page_token:
            path += f"&page_token={page_token}"
        data = api("GET", path, token=token)["data"]
        for f in data.get("items", []):
            meta = {"type": f.get("type"), "options": []}
            prop = f.get("property") or {}
            for opt in prop.get("options") or []:
                if isinstance(opt, dict) and opt.get("name"):
                    meta["options"].append(opt["name"])
            field_meta[f["field_name"]] = meta
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")

    fields, written, skipped = {}, [], []
    for lark_name, env_key, kind in FIELD_SPECS:
        raw = os.environ.get(env_key, "").strip()
        if not raw:
            continue
        meta = field_meta.get(lark_name)
        if meta is None:
            skipped.append(lark_name)
            continue
        ftype = meta["type"]
        try:
            if kind == "select" and ftype in (3, 4):
                # 單選／多選：只寫入真實存在嘅選項，否則成個寫入會失敗
                if raw in meta["options"]:
                    fields[lark_name] = [raw] if ftype == 4 else raw
                    written.append(lark_name)
                else:
                    print(f"WARNING: {raw!r} is not an option of {lark_name!r} — skipped",
                          file=sys.stderr)
                    skipped.append(lark_name + f"（{raw} 唔係有效選項）")
            elif kind == "date" and ftype == TYPE_DATE:
                fields[lark_name] = to_timestamp_ms(raw)
                written.append(lark_name)
            elif kind == "number" and ftype == TYPE_NUMBER:
                fields[lark_name] = to_number(raw)
                written.append(lark_name)
            else:
                fields[lark_name] = raw
                written.append(lark_name)
        except ValueError as e:
            print(f"WARNING: field {lark_name!r}: {e} — skipped", file=sys.stderr)
            skipped.append(lark_name)

    if "HKSLI no" not in fields:
        print("ERROR: HKSLI no field missing or empty", file=sys.stderr)
        sys.exit(1)

    # 精確搜尋 HKSLI no
    search_body = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "HKSLI no", "operator": "is", "value": [DOC_NO]}
            ],
        },
        "page_size": 50,
    }
    found = api(
        "POST",
        f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/search",
        search_body,
        token=token,
    )["data"].get("items", [])

    result = {
        "doc_no": DOC_NO,
        "fields_written": written,
        "fields_skipped": skipped,
    }
    record_ids = []
    if found:
        updated = 0
        for item in found:
            record_id = item["record_id"]
            api(
                "PUT",
                f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}",
                {"fields": fields},
                token=token,
            )
            record_ids.append(record_id)
            updated += 1
        result.update(action="updated", records=updated)
    else:
        created = api(
            "POST",
            f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            {"fields": fields},
            token=token,
        )["data"]["record"]["record_id"]
        record_ids.append(created)
        result.update(action="created", record_id=created)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
