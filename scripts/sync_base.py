#!/usr/bin/env python3
"""Sync Feishu Bitable records into the invoice print tool HTML."""
import json
import os
import re
import sys
import urllib.error
import urllib.request

APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN", "tbl2jFGYqmMfZjNC") # Replace or pass via env
TABLE_ID = os.environ.get("FEISHU_TABLE_ID", "tbl2jFGYqmMfZjNC")
API_ENDPOINT = "https://open.feishu.cn"
APP_ID = os.environ.get("FEISHU_APP_ID", "").strip()
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "").strip()


def get_access_token():
    url = f"{API_ENDPOINT}/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"Token HTTP Error {e.code}: {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Token Network Error: {e.reason}")
        sys.exit(1)

    if data.get("code") != 0:
        print(f"Feishu Auth Error (code {data.get('code')}): {data.get('msg')}")
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
        url = f"{API_ENDPOINT}/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records?{params}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"Records HTTP Error {e.code}: {error_body}")
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Records Network Error: {e.reason}")
            sys.exit(1)

        if data.get("code") != 0:
            print(f"Feishu Bitable API Error (code {data.get('code')}): {data.get('msg')}")
            sys.exit(1)

        records = data.get("data", {}).get("items", [])
        all_records.extend(records)

        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")

    return all_records


def convert_record(record):
    fields = record.get("fields", {})

    def get_text(field):
        if isinstance(field, list) and len(field) > 0:
            item = field[0]
            if isinstance(item, dict):
                return item.get("text", "")
            return str(item)
        return str(field) if field is not None else ""

    def get_number(field):
        if isinstance(field, dict) and "value" in field:
            val = field["value"]
            if isinstance(val, list) and len(val) > 0:
                return val[0]
            return val
        if isinstance(field, (int, float)):
            return field
        try:
            return float(field)
        except (ValueError, TypeError):
            return 0

    def get_array(field):
        return field if isinstance(field, list) else []

    return {
        "number": get_text(fields.get("Number", "")),
        "name": get_text(fields.get("Name", "")),
        "phone": get_text(fields.get("聯絡電話 Tel", "")),
        "model": get_text(fields.get("Model", "")),
        "sn": get_text(fields.get("SN", "")),
        "service": get_text(fields.get("服務內容", "")),
        "serviceFee": get_number(fields.get("服務費用 1", 0)),
        "deepClean": get_number(fields.get("深層清潔費用", 0)),
        "deliveryFee": get_number(fields.get("送貨費", 0)),
        "parts": get_number(fields.get("Parts amount", 0)),
        "total": get_number(fields.get("Total Amount", 0)),
        "status": get_text(fields.get("Status", "")),
        "payment": get_array(fields.get("Payment Methods", [])),
        "remark": get_text(fields.get("Remark", "")),
        "deliveryAddr": get_text(fields.get("Address (Delivery)", "")),
    }


def main():
    print("Starting sync from Feishu Base...")

    if not APP_ID:
        print("Error: Missing FEISHU_APP_ID environment variable.")
        sys.exit(1)
    if not APP_SECRET:
        print("Error: Missing FEISHU_APP_SECRET environment variable.")
        sys.exit(1)

    print("Requesting tenant access token...")
    token = get_access_token()
    print("Access token obtained successfully.")

    print(f"Fetching records from Table ({TABLE_ID})...")
    records = fetch_base_records(token)
    print(f"Fetched {len(records)} records.")

    records_data = [convert_record(r) for r in records]

    # Save to base_data.json
    with open("base_data.json", "w", encoding="utf-8") as f:
        json.dump(records_data, f, ensure_ascii=False, indent=2)
    print("Saved base_data.json.")

    # Update newvision-print-tool.html
    html_file = "newvision-print-tool.html"
    if not os.path.exists(html_file):
        print(f"Error: Target file '{html_file}' not found in working directory.")
        sys.exit(1)

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    pattern = re.compile(r"const BASE_DATA = \[[\s\S]*?\];")
    replacement = "const BASE_DATA = " + json.dumps(records_data, ensure_ascii=False) + ";"
    html_content, count = pattern.subn(replacement, html_content, count=1)

    if count == 0:
        print("Warning: Pattern 'const BASE_DATA = [...];' not found in HTML file.")
    else:
        print("Updated BASE_DATA variable.")

    html_content = re.sub(
        r'共 <span id="recordCount">\d*</span> 筆記錄',
        f'共 <span id="recordCount">{len(records_data)}</span> 筆記錄',
        html_content,
    )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Updated {html_file}.")
    print("Sync completed successfully.")


if __name__ == "__main__":
    main()
