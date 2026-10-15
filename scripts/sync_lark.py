#!/usr/bin/env python3
"""
Sync Lark Bitable Outbound Record into lark_shipment_data.json.
Run inside GitHub Actions with LARK_APP_ID and LARK_APP_SECRET env vars
(stored as GitHub Secrets, never in code).

Base: Labware Outbound Record V3.0 (SWSQbZibjaHSTqsWlbqlB4sHg9e)
Table: Outbound Record (tblmmHsnTTzufnUq)

Field mapping (per owner):
    docNumber     <- "HKSLI no"
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
import time

APP_TOKEN = "SWSQbZibjaHSTqsWlbqlB4sHg9e"
TABLE_ID = "tblmmHsnTTzufnUq"  # Outbound Record
API_ENDPOINT = "https://open.larksuite.com/open-apis"
APP_ID = os.environ.get("LARK_APP_ID", "")
APP_SECRET = os.environ.get("LARK_APP_SECRET", "")


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


def fetch_base_records(token):
    all_records = []
    page_token = None
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

        records = data.get("data", {}).get("items", [])
        all_records.extend(records)

        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")
        time.sleep(0.5)

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
        "docNumber": get_text(fields.get("HKSLI no", "")),
        "customerName": get_text(fields.get("Customer Name", "")),
        "shipToAddress": addr,
        "contactName": get_text(fields.get("Contact Name", "")),
        "status": get_text(fields.get("Status", "")),
    }


def main():
    print("Starting sync from Lark Base...")

    if not APP_ID or not APP_SECRET:
        print("Error: LARK_APP_ID and LARK_APP_SECRET must be set")
        sys.exit(1)

    token = get_access_token()
    print("Access token obtained")

    records = fetch_base_records(token)
    print(f"Fetched {len(records)} records")

    records_data = [convert_record(r) for r in records]
    valid = sum(1 for r in records_data if r["docNumber"])
    print(f"Valid records with docNumber: {valid}/{len(records_data)}")
    if valid == 0:
        print("WARNING: no valid records extracted, aborting to avoid overwriting good data")
        sys.exit(1)

    with open("lark_shipment_data.json", "w", encoding="utf-8") as f:
        json.dump(records_data, f, ensure_ascii=False, indent=2)
    print("Saved lark_shipment_data.json")
    print("Sync completed successfully")


if __name__ == "__main__":
    main()
