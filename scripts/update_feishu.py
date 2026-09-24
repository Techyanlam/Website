import os
import sys
import json
import requests

# 飛書 App 憑證
APP_ID = os.environ.get("FEISHU_APP_ID") or "cli_a94e743517781bd8"
APP_SECRET = os.environ.get("FEISHU_APP_SECRET") or "IDOrtoojYjrJTeDOg9DMsb5Z8vPuxCxH"
PAYLOAD_STR = os.environ.get("CLIENT_PAYLOAD", "{}")

# 多維表格 Base Token
APP_TOKEN = "TAG2b406ja23OHsIXH6c6Kbxndh"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()
    if res.get("code") != 0:
        print("❌ 獲取 Feishu Token 失敗：", res)
        sys.exit(1)
    return res.get("tenant_access_token")

def get_table_info(token):
    """自動取得多維表格的第一個主要資料表 ID 與現有所有欄位名稱"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers).json()
    if res.get("code") != 0 or not res.get("data", {}).get("items"):
        print("❌ 無法取得多維表格清單，請檢查權限或 APP_TOKEN：", res)
        sys.exit(1)
    
    table_id = res["data"]["items"][0]["table_id"]
    table_name = res["data"]["items"][0].get("name", "")
    print(f"✔️ 自動辨識到資料表: {table_name} (ID: {table_id})")

    # 取得該表的所有實際欄位清單
    fields_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/fields"
    fields_res = requests.get(fields_url, headers=headers).json()
    existing_fields = [f["field_name"] for f in fields_res.get("data", {}).get("items", [])]
    print(f"多維表格現有欄位: {existing_fields}")
    
    return table_id, existing_fields

def match_field_name(target_candidates, existing_fields):
    """在多維表格欄位中尋找最相近匹配的欄位名"""
    for candidate in target_candidates:
        if candidate in existing_fields:
            return candidate
    for cand in target_candidates:
        for ex in existing_fields:
            if cand.lower() in ex.lower():
                return ex
    return None

def build_feishu_fields(raw_fields, existing_fields):
    """將前端傳入的資料智慧映射到飛書的實際欄位名中"""
    field_mappings = {
        ("Number", "單據編號", "單號", "編號", "Order No"): raw_fields.get("Number"),
        ("Name", "客戶姓名", "姓名", "客戶名稱", "聯絡人"): raw_fields.get("Name"),
        ("聯絡電話 Tel", "聯絡電話", "電話", "Tel", "Phone"): raw_fields.get("聯絡電話 Tel"),
        ("Model", "設備型號", "型號"): raw_fields.get("Model"),
        ("SN", "序號", "SN序號", "Serial Number"): raw_fields.get("SN"),
        ("Address (Delivery)", "送貨地址", "地址", "Address"): raw_fields.get("Address (Delivery)"),
        ("Service", "維修內容說明", "服務項目", "服務內容"): raw_fields.get("Service"),
        ("Remark", "備註", "內部備註"): raw_fields.get("Remark"),
        ("Total Parts amount", "總金額", "合計金額", "金額", "Total"): raw_fields.get("Total Parts amount"),
    }

    result = {}
    for candidates, val in field_mappings.items():
        if val in [None, ""]:
            continue
        matched_name = match_field_name(candidates, existing_fields)
        if matched_name:
            result[matched_name] = val
        else:
            # 若無特別模糊匹配，使用預設第一個候選名稱
            result[candidates[0]] = val
    return result

def main():
    print(f"啟動飛書自動更新... APP_TOKEN={APP_TOKEN}")

    try:
        payload = json.loads(PAYLOAD_STR)
    except Exception as e:
        print(f"⚠️ 解析 Payload 失敗: {e}")
        payload = {}

    raw_fields = payload.get("fields")
    if not raw_fields:
        print("ℹ️ 無前端提交的記錄內容 (No fields provided)，跳過更新。")
        return

    token = get_tenant_access_token()
    table_id, existing_fields = get_table_info(token)
    matched_fields = build_feishu_fields(raw_fields, existing_fields)
    print("即將寫入飛書的匹配欄位資料：", json.dumps(matched_fields, ensure_ascii=False))

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    record_id = payload.get("record_id")

    if record_id:
        print(f"正在更新已有記錄：{record_id}")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records/{record_id}"
        resp = requests.put(url, headers=headers, json={"fields": matched_fields}).json()
        print("飛書更新回應：", resp)
        if resp.get("code") != 0:
            print(f"❌ 飛書更新失敗！原因：{resp.get('msg')}")
            sys.exit(1)
        print("✔️ 記錄更新成功！")
    else:
        print("正在新增記錄至飛書多維表格...")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
        resp = requests.post(url, headers=headers, json={"fields": matched_fields}).json()
        print("飛書新增回應：", resp)
        if resp.get("code") != 0:
            print(f"❌ 飛書新增失敗！原因：{resp.get('msg')}")
            sys.exit(1)
        print("✔️ 記錄新增成功！")

if __name__ == "__main__":
    main()
