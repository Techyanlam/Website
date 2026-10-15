#!/usr/bin/env python3
"""
Sync Lark Bitable Outbound Record into lark_shipment_data.json.
Run inside GitHub Actions with LARK_APP_ID and LARK_APP_SECRET env vars
(stored as GitHub Secrets, never in code).

Incremental sync: uses the native "最後修改時間" (modified-time) field to
fetch only records changed since the last sync, then merges into the
existing JSON. Falls back to full sync when: no state file, no
modified-time field, filter API fails, or last full sync > 24h ago
(safety net, also catches deletions).

Base: Labware Outbound Record V3.0 (SWSQbZibjaHSTqsWlbqlB4sHg9e)
Table: Outbound Record (tblmmHsnTTzufnUq)

Field mapping (per owner):
    docNumber     <- "HKSLI no"
    transportQty  <- "Transport Qty"
    customerName  <- "Customer Name"
    shipToAddress <- "Location" (fallback "送貨地址")
    contactName   <- "Contact Name"
    status        <- "Status"
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import time

APP_TOKEN = "SWSQbZibjaHSTqsWlbqlB4sHg9e"
TABLE_ID = "tblmmHsnTTzufnUq"  # Outbound Record
API_ENDPOINT = "https://open.larksuite.com/open-apis"
APP_ID = os.environ.get("LARK_APP_ID", "")
APP_SECRET = os.environ.get("LARK_APP_SECRET", "")

DATA_FILE = "lark_shipment_data.json"
STATE_FILE = "lark_sync_state.json"
FULL_SYNC_INTERVAL_MS = 24 * 3600 * 1000  # 每 24 小時做一次全量兜底
MOD_FIELD_NAMES = ("最後修改時間", "修改時間", "最后修改时间",
                   "Last modified time", "Modified time")


def request_json(url, method="GET", body=None, headers=None, timeout=30, retries=3, label="request"):
    """POST/GET JSON with retries for transient failures."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {},
                                         method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # HTTPError, URLError, TimeoutError...
            last_err = e
            print(f"{label}: attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(2 * attempt)
    print(f"{label}: all {retries} attempts failed: {last_err}")
    sys.exit(1)


def get_access_token():
    url = f"{API_ENDPOINT}/auth/v3/tenant_access_token/internal"
    data = request_json(
        url, method="POST",
        body={"app_id": APP_ID, "app_secret": APP_SECRET},
        headers={"Content-Type": "application/json"},
        timeout=15, retries=3, label="token",
    )
    if data.get("code") != 0:
        print(f"Token request failed: {data.get('msg')}")
        sys.exit(1)
    return data["tenant_access_token"]


def fetch_all_records(token):
    """全量分頁拉取（游標分頁，必須順序）。"""
    all_records = []
    page_token = ""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    while True:
        params = "page_size=100"
        if page_token:
            params += f"&page_token={page_token}"

        url = f"{API_ENDPOINT}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records?{params}"
        data = request_json(url, headers=headers, timeout=30,
                            retries=3, label=f"records(page_token={bool(page_token)})")
        if data.get("code") != 0:
            print(f"Records API error: {data.get('msg')}")
            sys.exit(1)

        records = data.get("data", {}).get("items") or []
        all_records.extend(records)

        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token", "")
        time.sleep(0.5)

    return all_records


def find_modified_time_field(token):
    """自動搵「最後修改時間」欄，回傳 field_id；搵唔到回 None。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = (f"{API_ENDPOINT}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields"
           f"?page_size=100")
    try:
        data = request_json(url, headers=headers, timeout=30, retries=3,
                            label="fields")
    except SystemExit:
        raise
    except Exception as e:
        print(f"Field list failed: {e}")
        return None
    if data.get("code") != 0:
        print(f"Field list API error: {data.get('msg')}")
        return None
    for f in data.get("data", {}).get("items", []):
        if f.get("field_name") in MOD_FIELD_NAMES:
            print(f"Found modified-time field: {f.get('field_name')} ({f.get('field_id')}, type={f.get('type')})")
            if f.get("type") != 1002:
                print(f"WARNING: field type is {f.get('type')}, expected 1002 (native modified-time). "
                      f"If this is a manual date field it will stay empty!")
            return f.get("field_id")
    print("Modified-time field not found (table needs a field named 最後修改時間)")
    return None


def probe_field_unit(token, field_id):
    """探測修改時間欄嘅數值係毫秒定秒，回傳 'ms' 或 's'（預設 'ms'）。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    checked = 0
    with_value = 0
    page_token = ""
    for _ in range(3):  # 最多掃 300 筆
        params = "page_size=100"
        if page_token:
            params += f"&page_token={page_token}"
        url = (f"{API_ENDPOINT}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
               f"?{params}")
        try:
            data = request_json(url, headers=headers, timeout=30, retries=3,
                                label="probe")
        except SystemExit:
            raise
        except Exception:
            break
        if data.get("code") != 0:
            break
        items = data.get("data", {}).get("items") or []
        for item in items:
            checked += 1
            v = (item.get("fields") or {}).get(field_id)
            try:
                num = float(v)
            except (TypeError, ValueError):
                continue
            if num > 0:
                with_value += 1
                if with_value == 1:
                    unit = "s" if num < 1e12 else "ms"
                    print(f"Modified-time unit probe: value={v} -> {unit} "
                          f"({with_value} of {checked} sampled have values so far)")
                    return unit
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token", "")
    print(f"Probe: {with_value}/{checked} sampled records have modified-time values; "
          f"assuming milliseconds")
    return "ms"


def fetch_changed_records(token, field_id, since_val):
    """拉自 since_val 之後有修改嘅記錄（分頁）。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    all_records = []
    page_token = ""
    filt = f"CurrentValue.[{field_id}]>{since_val}"
    while True:
        params = {"page_size": "100", "filter": filt}
        if page_token:
            params["page_token"] = page_token
        url = (f"{API_ENDPOINT}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
               f"?{urllib.parse.urlencode(params)}")
        data = request_json(url, headers=headers, timeout=30, retries=3,
                            label=f"changed(page={bool(page_token)})")
        if data.get("code") != 0:
            raise RuntimeError(f"Filter API error: {data.get('msg')}")
        items = data.get("data", {}).get("items") or []
        all_records.extend(items)
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token", "")
        time.sleep(0.3)
    return all_records


def get_text(field):
    """Lark text fields may come back as plain strings or rich-text segment lists."""
    if isinstance(field, list) and len(field) > 0:
        first = field[0]
        if isinstance(first, dict):
            return first.get("text", "")
        return str(first)
    return str(field) if field else ""


def convert_record(record):
    fields = record.get("fields", {}) or {}

    addr = get_text(fields.get("Location", ""))
    if not addr:
        addr = get_text(fields.get("送貨地址", ""))

    return {
        "recordId": record.get("record_id", ""),
        "docNumber": get_text(fields.get("HKSLI no", "")),
        "customerName": get_text(fields.get("Customer Name", "")),
        "shipToAddress": addr,
        "contactName": get_text(fields.get("Contact Name", "")),
        "status": get_text(fields.get("Status", "")),
        "transportQty": get_text(fields.get("Transport Qty", "")),
    }


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_existing_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def main():
    print("Starting sync from Lark Base...")

    if not APP_ID or not APP_SECRET:
        print("Error: LARK_APP_ID and LARK_APP_SECRET must be set")
        sys.exit(1)

    token = get_access_token()
    print("Access token obtained")

    now_ms = int(time.time() * 1000)
    state = load_state()
    existing = load_existing_data()
    has_record_ids = bool(existing) and all(r.get("recordId") for r in existing)

    mod_field_id = find_modified_time_field(token)

    do_full = False
    reason = ""
    if not existing:
        do_full, reason = True, "no existing data file"
    elif not has_record_ids:
        do_full, reason = True, "existing data lacks recordId (one-time backfill)"
    elif not mod_field_id:
        do_full, reason = True, "modified-time field not found"
    elif not state.get("last_sync_ms"):
        do_full, reason = True, "no sync state"
    elif now_ms - state.get("last_full_sync_ms", 0) > FULL_SYNC_INTERVAL_MS:
        do_full, reason = True, "24h full-sync safety net"

    if do_full:
        print(f"Full sync ({reason})")
        records = fetch_all_records(token)
        print(f"Fetched {len(records)} records")
        data = [convert_record(r) for r in records]
        state["last_full_sync_ms"] = now_ms
        state["last_sync_ms"] = now_ms
    else:
        fetch_start_ms = now_ms
        unit = probe_field_unit(token, mod_field_id)
        since_val = state["last_sync_ms"] if unit == "ms" else state["last_sync_ms"] // 1000
        print(f"Incremental sync: changes since {state['last_sync_ms']} (field unit: {unit})")
        try:
            changed = fetch_changed_records(token, mod_field_id, since_val)
        except Exception as e:
            print(f"Incremental fetch failed ({e}); falling back to full sync")
            records = fetch_all_records(token)
            print(f"Fetched {len(records)} records")
            data = [convert_record(r) for r in records]
            state["last_full_sync_ms"] = now_ms
            state["last_sync_ms"] = now_ms
        else:
            print(f"Fetched {len(changed)} changed records")
            # 按 record_id 合併，保留原有順序
            by_id = {}
            order = []
            for r in existing:
                rid = r.get("recordId")
                if rid and rid not in by_id:
                    by_id[rid] = r
                    order.append(rid)
            for raw in changed:
                rec = convert_record(raw)
                rid = rec["recordId"]
                if not rid:
                    continue
                if rid not in by_id:
                    order.append(rid)
                by_id[rid] = rec
            data = [by_id[rid] for rid in order]
            # 30 秒重疊，防漏網之魚
            state["last_sync_ms"] = fetch_start_ms - 30000

    valid = sum(1 for r in data if r["docNumber"])
    print(f"Valid records with docNumber: {valid}/{len(data)}")
    if valid == 0:
        print("WARNING: no valid records, aborting to avoid overwriting good data")
        sys.exit(1)
    # 防呆：合併後筆數唔應該比之前少超過一半
    if existing and len(data) < len(existing) // 2:
        print(f"WARNING: record count dropped {len(existing)} -> {len(data)}, aborting")
        sys.exit(1)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    save_state(state)
    print(f"Saved {DATA_FILE} ({len(data)} records) and {STATE_FILE}")
    print("Sync completed successfully")


if __name__ == "__main__":
    main()
