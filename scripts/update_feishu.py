import os
import re
import sys
import json
import requests

APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
PAYLOAD_STR = os.environ.get("CLIENT_PAYLOAD", "{}")

# 1. 自動從已成功的 sync_base.py 中提取 APP_TOKEN 與 TABLE_ID
def extract_config_from_sync_base():
    app_token = ""
    table_id = ""
    sync_file = os.path.join(os.path.dirname(__file__), "sync_base.py")
    if os.path.exists(sync_file):
        with open(sync_file, "r", encoding="utf-8") as f:
            content = f.read()
            m_token = re.search(r'APP_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
            m_table = re.search(r'TABLE_ID\s*=\s*["\']([^"\']+)["\']', content)
            if m_token:
                app_token = m_token.group(1)
            if m_table:
                table_id = m_table.group(1)
    return app_token, table_id

APP_TOKEN, TABLE_ID = extract_config_from_sync_base()

def get_tenant_access_token():
    if not APP_ID or not APP_SECRET:
        print("❌ 錯誤：未找到 FEISHU_APP_ID 或 FEISHU_APP_SECRET 環境變數！")
        sys.exit(1)
        
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()
    if res.get("code") != 0:
        print("❌ 獲取 Feishu Token 失敗：", res)
        sys.exit(1)
    return res.get("tenant_access_token")

def clean_empty_fields(fields):
    """去除值為空或 None 的欄位，避免飛書類型校驗報錯"""
    return {k: v for k, v in fields.items() if v not in [None, "", []]}

def main():
    print(f"啟動飛書更新腳本... APP_TOKEN={APP_TOKEN[:6]}***, TABLE_ID={TABLE_ID}")
    
    if not APP_TOKEN or not TABLE_ID:
        print("❌ 錯誤：未能從 scripts/sync_base.py 自動提取到 APP_TOKEN 或 TABLE_ID！")
        sys.exit(1)

    try:
        payload = json.loads(PAYLOAD_STR)
    except Exception as e:
        print(f"⚠️ 解析 Payload 失敗: {e}")
        payload = {}

    record_fields = payload.get("fields")
    if not record_fields:
        print("ℹ️ 無前端提交的記錄內容 (No fields provided)，跳過更新。")
        return

    # 過濾空欄位
    valid_fields = clean_empty_fields(record_fields)
    print("準備寫入飛書的資料：", json.dumps(valid_fields, ensure_ascii=False))

    token = get_tenant_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    record_id = payload.get("record_id")

    if record_id:
        print(f"正在更新已有記錄：{record_id}")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
        resp = requests.put(url, headers=headers, json={"fields": valid_fields}).json()
        print("飛書更新回應：", resp)
        if resp.get("code") != 0:
            print(f"❌ 飛書更新失敗！原因：{resp.get('msg')}")
            sys.exit(1)
        print("✔️ 記錄更新成功！")
    else:
        print("正在新增記錄至飛書多維表格...")
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
        resp = requests.post(url, headers=headers, json={"fields": valid_fields}).json()
        print("飛書新增回應：", resp)
        if resp.get("code") != 0:
            print(f"❌ 飛書新增失敗！原因：{resp.get('msg')}")
            sys.exit(1)
        print("✔️ 記錄新增成功！")

if __name__ == "__main__":
    main()
