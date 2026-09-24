#!/usr/bin/env python3
import json, os, re, urllib.request, urllib.error, sys

APP_TOKEN = "TAG2b4…xndh"
TABLE_ID = "tbl2jFGYqmMfZjNC"
API_ENDPOINT = "[https://open.feishu.cn](https://open.feishu.cn)"
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = ***"FEISHU_APP_SECRET", "")

def get_token():
    url = f"{API_ENDPOINT}/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Token request failed: {e.code} {e.read().decode()}")
        sys.exit(1)

    if data.get("code") != 0:
        print(f"Token request failed: {data.get('msg')}")
        sys.exit(1)

    return data["tenant_access_token"]

def fetch_records(token):
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
            print(f"Records request failed: {e.code} {e.read().decode()}")
            sys.exit(1)

        if data.get("code") != 0:
            print(f"Records API error: {data.get('msg')}")
            sys.exit(1)

        records = data.get("data", {}).get("items", [])
        all_records.extend(records)

        if not data.get("data", {}).get("has_more"):
            break
        page_token = data["data"].get("page_token")

    return all_records

def convert_record(record):
    fields = record.get("fields", {})

    def get_text(field):
        if isinstance(field, list) and len(field) > 0:
            return field[0].get("text", "")
        return str(field) if field else ""

    def get_number(field):
        if isinstance(field, dict) and "value" in field:
            val = field["value"]
            if isinstance(val, list) and len(val) > 0:
                return val[0]
            return val
        return field if isinstance(field, (int, float)) else 0

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

if __name__ == "__main__":
    if not APP_ID or not APP_SECRET:
        ***"Error: FEISHU_APP_ID and FEISHU_APP_SECRET must be set")
        sys.exit(1)

    token=***
    records = fetch_records(token)
    data = [convert_record(r) for r in records]

    with open("base_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} records to base_data.json")

    html_file = "newvision-print-tool.html"
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found")
        sys.exit(1)

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace BASE_DATA array
    html = re.sub(
        r"const BASE_DATA = \[[\s\S]*?\];",
        f"const BASE_DATA = {json.dumps(data, ensure_ascii=False)};",
        html,
        count=1,
    )

    # Update record count
    html = re.sub(
        r'共 <span id="recordCount">\d+</span> 筆記錄',
        f'共 <span id="recordCount">{len(data)}</span> 筆記錄',
        html,
    )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated {html_file}")
