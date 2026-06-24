function doGet(e) {
  var orderNo = e.parameter.orderNo;
  
  // 模擬從飛書 Base 獲取數據的邏輯
  var result = {
    "code": 0,
    "type": "repair",
    "custName": "王小明",
    "model": "Dyson V15",
    "serviceFee": 500
  };

  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON)
    // 關鍵：允許任何網域請求
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
}

// 處理瀏覽器發出的預檢請求 (Preflight)
function doOptions(e) {
  return ContentService.createTextOutput()
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS')
    .setHeader('Access-Control-Allow-Headers', 'Content-Type');
}
