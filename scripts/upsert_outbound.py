#!/usr/bin/env python3
"""Upsert 一筆 Outbound Record：按「HKSLI no」搜尋，找到就更新，唔存在就新增。

輸入（環境變數）：
    LARK_APP_ID / LARK_APP_SECRET —— Lark 自建應用憑證（GitHub Secrets）
    HKSLI_NO        —— Invoice No.（必填）
    CUSTOMER_NAME   —— Ship To 公司名（選填）
    SHIP_ADDRESS    —— 送貨地址，寫入「送貨地址」欄（選填）
    CONTACT_NAME    —— Ship To Attn，寫入「Contact Name」欄（選填）

行為：
    - 用 records/search 以 HKSLI no 精確搜尋
    - 有命中 → PUT 更新該記錄（只寫入有提供嘅欄位）
    - 無命中 → POST 新增記錄
"""
import json
import os
import sys
import time
import urllib.request

APP_ID = os.environ["LARK_APP_ID"]
APP_SECRET = os.environ["LARK_APP_SECRET"]
APP_TOKEN = "SWSQbZibjaHSTqsWlbqlB4sHg9e"   # Labware Outbound Record V3.0
TABLE_ID = "tblmmHsnTTzufnUq"               # Outbound Record
API = "https://open.larksuite.com/open-apis"

DOC_NO = os.environ.get("HKSLI_NO", "").strip()
CUSTOMER_NAME = os.environ.get("CUSTOMER_NAME", "").strip()
SHIP_ADDRESS = os.environ.get("SHIP_ADDRESS", "").strip()
CONTACT_NAME = os.environ.get("CONTACT_NAME", "").strip()

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


def main():
    token = api(
        "POST",
        "/auth/v3/tenant_access_token/internal",
        {"app_id": APP_ID, "app_secret": APP_SECRET},
    )["tenant_access_token"]

    fields = {"HKSLI no": DOC_NO}
    if CUSTOMER_NAME:
        fields["Customer Name"] = CUSTOMER_NAME
    if SHIP_ADDRESS:
        fields["送貨地址"] = SHIP_ADDRESS
    if CONTACT_NAME:
        fields["Contact Name"] = CONTACT_NAME

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
            updated += 1
        print(
            json.dumps(
                {"action": "updated", "doc_no": DOC_NO, "records": updated},
                ensure_ascii=False,
            )
        )
    else:
        created = api(
            "POST",
            f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            {"fields": fields},
            token=token,
        )["data"]["record"]["record_id"]
        print(
            json.dumps(
                {"action": "created", "doc_no": DOC_NO, "record_id": created},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
