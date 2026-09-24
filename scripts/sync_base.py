#!/usr/bin/env python3
"""Sync Feishu Bitable records into base_data.json and invoice print tool HTML."""
import json
import os
import re
import sys
import urllib.error
import urllib.request

APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN", "TAG2b406ja23OHsIXH6c6Kbxndh")
TABLE_ID = os.environ.get("FEISHU_TABLE_ID", "tbl2jFGYqmMfZjNC")
API_ENDPOINT = "https://open.feishu.cn"
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a94e743517781bd8").strip()
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "IDOrtoojYjrJTeDOg9DMsb5Z8vPuxCxH").strip()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..")) if os.path.basename(SCRIPT_DIR) == "scripts" else SCRIPT_DIR


def get_access_token():
    url = f"{API_ENDPOINT}/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Token Error: {e}")
        sys.exit(1)

    if data.get("code") != 0:
        print(f"Feishu Auth Error: {data.get('msg')}")
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
        except Exception as e:
            print(f"Records Error: {e}")
            sys.exit(1)

        if data.get("code") != 0:
            print(f"Records API Error: {data.get('msg')}")
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
    print("Starting sync...")
    token = get_access_token()
    records = fetch_base_records(token)
    print(f"Fetched {len(records)} records from Feishu.")

    records_data = [convert_record(r) for r in records]

    # 1. 寫入 base_data.json
    json_path = os.path.join(PROJECT_ROOT, "base_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records_data, f, ensure_ascii=False, indent=2)
    print("Saved base_data.json.")

    # 2. 同步更新 newvision-print-tool.html
    html_file = os.path.join(PROJECT_ROOT, "newvision-print-tool.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        json_str = json.dumps(records_data, ensure_ascii=False)
        # 兼容替換 window.BASE_DATA 或 const BASE_DATA
        if "window.BASE_DATA = " in html:
            html = re.sub(r"window\.BASE_DATA = \[[\s\S]*?\];", f"window.BASE_DATA = {json_str};", html, count=1)
        elif "const BASE_DATA = " in html:
            html = re.sub(r"const BASE_DATA = \[[\s\S]*?\];", f"window.BASE_DATA = {json_str};", html, count=1)

        html = re.sub(
            r'共 <span id="recordCount">\d*</span> 筆記錄',
            f'共 <span id="recordCount">{len(records_data)}</span> 筆記錄',
            html
        )

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Updated {html_file} successfully.")

    print("Sync finished.")


if __name__ == "__main__":
    main()
