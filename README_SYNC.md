# 自動同步飛書 Base 數據

已經設定 GitHub Actions 每日自動從飛書 Base 同步數據到 `newvision-print-tool.html`。

## 已設定的 Secrets
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

## 同步時間
- 每天香港時間 08:00 和 20:00
- 也可以手動觸發

## 如何手動觸發
1. 打開 GitHub repo
2. 點擊 Actions → Sync Feishu Base Data
3. 點擊 Run workflow

## 自動更新後
- GitHub Pages 會在數分鐘內自動部署最新 HTML
- 你的網站 `https://oneder.dpdns.org/newvision-print-tool.html` 會顯示最新記錄
