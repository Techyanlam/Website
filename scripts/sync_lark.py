#!/usr/bin/env python3
"""
Sync Lark Bitable records into the shipment label HTML.
Run inside GitHub Actions with LARK_APP_ID and LARK_APP_SECRET env vars.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
import time

APP_TOKEN = "SWSQbZibjaHSTqsWlbqlB4sHg9e"
TABLE_ID = "tblmmHsnTTzufnUq"  # Outbound Record
API_ENDPOINT = "https://open.larksuite.com/open-apis"
APP_ID = os.environ.get("LARK_APP_ID", "")
APP_SECRET = ***"LARK_APP_SECRET", "")


def get_access_token():
    url = f"{API_ENDPOINT}/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Token request failed: {e.code} {e.read().decode()}")
        sys.exit(1)

    if data.get("code") != 0:
        print(f"Token request failed: {data.get('msg')}")
        sys.exit(1)

    return data["tenant_access_token"]


def fetch_base_records(token):
    all_records = []
    page_token = None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    while True:
        params = "page_size=50"
        if page_token:
            params += f"&page_token={page_token}"

        url = f"{API_ENDPOINT}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records?{params}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
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
        time.sleep(0.5)

    return all_records


def convert_record(record):
    fields = record.get("fields", {})

    def get_text(field):
        if isinstance(field, list) and len(field) > 0:
            return field[0].get("text", "")
        return str(field) if field else ""

    addr = get_text(fields.get("送貨地址", ""))
    if not addr:
        addr = get_text(fields.get("Location", ""))

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
        ***"Error: LARK_APP_ID and LARK_APP_SECRET must be set")
        sys.exit(1)

    token=***
    print("Access token obtained")

    records = fetch_base_records(token)
    print(f"Fetched {len(records)} records")

    records_data = [convert_record(r) for r in records]

    # Save JSON snapshot
    with open("lark_shipment_data.json", "w", encoding="utf-8") as f:
        json.dump(records_data, f, ensure_ascii=False, indent=2)
    print("Saved lark_shipment_data.json")

    # Update HTML
    html_file = "UPGLShipmentlabel.html"
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found")
        sys.exit(1)

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Replace or add embedded data
    embedded_data = f"const LARK_EMBEDDED_DATA = {json.dumps(records_data, ensure_ascii=False)};"
    
    if "const LARK_EMBEDDED_DATA" in html_content:
        html_content = re.sub(
            r"const LARK_EMBEDDED_DATA = \[[\s\S]*?\];",
            embedded_data,
            html_content,
            count=1,
        )
    else:
        html_content = html_content.replace(
            "<script>",
            f"<script>\n        {embedded_data}\n",
            1,
        )

    # Update localStorage initialization
    init_code = """
        // Auto-load embedded data on page load
        if (typeof LARK_EMBEDDED_DATA !== 'undefined' && LARK_EMBEDDED_DATA.length > 0) {
            localStorage.setItem('lark_shipment_data', JSON.stringify(LARK_EMBEDDED_DATA));
            console.log(\`已載入 \${LARK_EMBEDDED_DATA.length} 筆 Lark 記錄\`);
        }
    """
    
    if "// Auto-load embedded data on page load" in html_content:
        html_content = re.sub(
            r"// Auto-load embedded data on page load[\s\S]*?console\.log\([^)]+\);\s*\}",
            init_code.strip(),
            html_content,
        )
    else:
        html_content = html_content.replace(
            "</script>",
            f"{init_code}\n    </script>",
            1,
        )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Updated {html_file}")

    print("Sync completed successfully")


if __name__ == "__main__":
    main()
