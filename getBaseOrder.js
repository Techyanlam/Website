export default async function handler(req, res) {
    // 解決CORS跨域錯誤
    res.setHeader('Access-Control-Allow-Origin', 'https://oneder.dpdns.org');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // 處理瀏覽器預檢OPTIONS請求
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // 只允許GET查單
    if (req.method !== 'GET') {
        return res.status(405).json({ code: -1, msg: "僅支援GET查詢訂單" });
    }

    const orderNo = req.query.orderNo;
    if (!orderNo) {
        return res.status(400).json({ code: -1, msg: "請輸入單據編號" });
    }

    // ===================== 這裡替換你原本連飛書Base拿數據邏輯 =====================
    // 測試假資料，正式使用時替換飛書API邏輯
    let resultData = {
        code: 0,
        msg: "成功",
        type: "repair",
        custName: "",
        custTel: "",
        whatsapp: "",
        delAddr: "",
        model: "",
        sn: "",
        serviceText: "",
        serviceFee: 0,
        delFee: 0,
        warrantyMonth: 0,
        invNo: "",
        price: 0,
        qty: 1,
        discount: 0,
        spec: "",
        delMethod: "",
        warranty: "",
        payMethod: "",
        remark: "",
        items: []
    };

    // 測試單號範例
    if (orderNo === "NV2026050525") {
        resultData = {
            code: 0,
            msg: "成功",
            type: "repair",
            custName: "測試客戶",
            custTel: "98761234",
            whatsapp: "",
            delAddr: "旺角彌敦道610號荷里活廣場",
            model: "Dyson V10",
            sn: "DY20260505001",
            serviceText: "深層清潔馬達同滾筒",
            serviceFee: 280,
            delFee: 30,
            warrantyMonth: 1,
            invNo: "NV2026050525",
            price: 0,
            qty: 1,
            discount: 0,
            spec: "",
            delMethod: "",
            warranty: "",
            payMethod: "",
            remark: "7日內取機",
            items: ["專業故障診斷", "深層清潔"]
        };
    }
    // =========================================================================

    return res.json(resultData);
}
