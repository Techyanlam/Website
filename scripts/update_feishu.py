import os
import json
import requests

APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
PAYLOAD_STR = os.environ.get("CLIENT_PAYLOAD", "{}")

# 多維表格資訊 (與 sync_base.py 相同)
APP_TOKEN = "NviWb..." # 請填寫你的 Base app_token
TABLE_ID = "tbl..."   # 請填寫你的 Order 表 table_id

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()
    return res.get("tenant_access_token")

def main():
    try:
        payload = json.loads(PAYLOAD_STR)
    except:
        payload = {}

    # 如果沒有傳入具體記錄內容則略過
    record_fields = payload.get("fields")
    if not record_fields:
        print("No record fields to push to Feishu.")
        return

    token = get_tenant_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    record_id = payload.get("record_id")

    if record_id:
        # 更新已有記錄
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
        resp = requests.put(url, headers=headers, json={"fields": record_fields})
        print("Update response:", resp.json())
    else:
        # 新增記錄
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
        resp = requests.post(url, headers=headers, json={"fields": record_fields})
        print("Create response:", resp.json())

if __name__ == "__main__":
    main()
