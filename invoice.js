// 線上網站專用API位址，後續要替換成你雲端後端網址
const API_URL = "https://你的雲端後端網址/api/getBaseOrder";

// 頁面載入初始化
window.onload = function () {
    // 自動生成今日日期
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    const h = String(now.getHours()).padStart(2, "0");
    const mi = String(now.getMinutes()).padStart(2, "0");
    const localDate = `${y}/${m}/${d} ${h}:${mi}`;
    document.getElementById("inpCreateTime").value = localDate;
    document.getElementById("genCreateTime").value = localDate;
    document.getElementById("saleCreateTime").value = localDate;

    document.getElementById("invoiceType").addEventListener("change", refreshForm);
    refreshForm();
    calcRepair();
    calcGen();
    calcSale();
    refreshPreview();
};

// 切換表單+打印區塊
function refreshForm() {
    const type = document.getElementById("invoiceType").value;
    document.getElementById("repairForm").style.display = "none";
    document.getElementById("generalForm").style.display = "none";
    document.getElementById("saleForm").style.display = "none";
    document.getElementById("printRepair").style.display = "none";
    document.getElementById("printGeneral").style.display = "none";
    document.getElementById("printSale").style.display = "none";

    if (type === "repair") {
        document.getElementById("repairForm").style.display = "block";
        document.getElementById("printRepair").style.display = "block";
    } else if (type === "general") {
        document.getElementById("generalForm").style.display = "block";
        document.getElementById("printGeneral").style.display = "block";
    } else if (type === "sale") {
        document.getElementById("saleForm").style.display = "block";
        document.getElementById("printSale").style.display = "block";
    }
}

// 維修金額計算
function calcRepair() {
    const s = parseFloat(document.getElementById("inpServiceFee").value) || 0;
    const d = parseFloat(document.getElementById("inpDelFee").value) || 0;
    document.getElementById("inpTotal").value = (s + d).toFixed(2);
}

// 通用發票金額計算
function calcGen() {
    const p = parseFloat(document.getElementById("genPrice").value) || 0;
    const q = parseInt(document.getElementById("genQty").value) || 1;
    const disc = parseFloat(document.getElementById("genDisc").value) || 0;
    document.getElementById("genTotal").value = (p * q - disc).toFixed(2);
}

// 銷售金額計算
function calcSale() {
    const p = parseFloat(document.getElementById("salePrice").value) || 0;
    const q = parseInt(document.getElementById("saleQty").value) || 1;
    const disc = parseFloat(document.getElementById("saleDisc").value) || 0;
    document.getElementById("saleTotal").value = (p * q - disc).toFixed(2);
}

// 維修項目文字
function getItemText() {
    const arr = [];
    if(document.getElementById("chkDiag").checked) arr.push("☑ 專業故障診斷");
    if(document.getElementById("chkClean").checked) arr.push("☑ 深層清潔");
    if(document.getElementById("chkPart").checked) arr.push("☑ 零件更換");
    if(document.getElementById("chkOther").checked) arr.push("☑ 其他維修服務");
    return arr.join("<br>");
}

// 實時更新打印預覽
function refreshPreview() {
    const t = document.getElementById("invoiceType").value;
    if (t === "repair") {
        document.getElementById("pInvNo").innerText = document.getElementById("baseOrderNo").value || "";
        document.getElementById("pCreateTime").innerText = document.getElementById("inpCreateTime").value;
        document.getElementById("pCust").innerText = document.getElementById("inpCustName").value;
        document.getElementById("pTel").innerText = document.getElementById("inpTel").value;
        document.getElementById("pAddr").innerText = document.getElementById("inpAddr").value;
        document.getElementById("pModel").innerText = document.getElementById("inpModel").value;
        document.getElementById("pSN").innerText = document.getElementById("inpSN").value;
        document.getElementById("pWarranty").innerText = document.getElementById("inpWarranty").value;
        document.getElementById("pItemList").innerHTML = getItemText();
        document.getElementById("pServiceText").innerText = document.getElementById("inpServiceText").value;
        document.getElementById("pFee").innerText = Number(document.getElementById("inpServiceFee").value).toFixed(2);
        document.getElementById("pDelFee").innerText = Number(document.getElementById("inpDelFee").value).toFixed(2);
        document.getElementById("pTotal").innerText = document.getElementById("inpTotal").value;
        document.getElementById("pRemark").innerText = document.getElementById("inpRemark").value;
    } else if (t === "general") {
        document.getElementById("gInvNo").innerText = document.getElementById("genInvNo").value;
        document.getElementById("gCreateTime").innerText = document.getElementById("genCreateTime").value;
        document.getElementById("gCust").innerText = document.getElementById("genCustName").value;
        document.getElementById("gTel").innerText = document.getElementById("genTel").value + " / " + document.getElementById("genWhatsapp").value;
        document.getElementById("gAddr").innerText = document.getElementById("genAddr").value;
        document.getElementById("gItem").innerText = document.getElementById("genItem").value;
        document.getElementById("gSpec").innerText = document.getElementById("genSpec").value;
        const gp = Number(document.getElementById("genPrice").value).toFixed(2);
        const gq = document.getElementById("genQty").value;
        const gsub = (gp * gq).toFixed(2);
        const gdisc = Number(document.getElementById("genDisc").value).toFixed(2);
        document.getElementById("gPrice").innerText = gp;
        document.getElementById("gQty").innerText = gq;
        document.getElementById("gSub").innerText = gsub;
        document.getElementById("gDisc").innerText = gdisc;
        document.getElementById("gTotal").innerText = document.getElementById("genTotal").value;
        document.getElementById("gRemark").innerText = document.getElementById("genRemark").value;
    } else if (t === "sale") {
        document.getElementById("sInvNo").innerText = document.getElementById("saleInvNo").value;
        document.getElementById("sCreateTime").innerText = document.getElementById("saleCreateTime").value;
        document.getElementById("sCust").innerText = document.getElementById("saleCustName").value;
        document.getElementById("sTel").innerText = document.getElementById("saleTel").value + " / " + document.getElementById("saleWhatsapp").value;
        document.getElementById("sAddr").innerText = document.getElementById("saleAddr").value;
        document.getElementById("sDelMethod").innerText = document.getElementById("saleDelMethod").value;
        document.getElementById("sWarranty").innerText = document.getElementById("saleWarranty").value;
        document.getElementById("sPay").innerText = document.getElementById("salePay").value;
        document.getElementById("sModel").innerText = document.getElementById("saleModel").value;
        document.getElementById("sSpec").innerText = document.getElementById("saleSpec").value;
        const sp = Number(document.getElementById("salePrice").value).toFixed(2);
        const sq = document.getElementById("saleQty").value;
        const ssub = (sp * sq).toFixed(2);
        const sdisc = Number(document.getElementById("saleDisc").value).toFixed(2);
        document.getElementById("sPrice").innerText = sp;
        document.getElementById("sQty").innerText = sq;
        document.getElementById("sSub").innerText = ssub;
        document.getElementById("sDisc").innerText = sdisc;
        document.getElementById("sTotal").innerText = document.getElementById("saleTotal").value;
        document.getElementById("sRemark").innerText = document.getElementById("saleRemark").value;
    }
}

// 飛書載入API（只填充客戶/金額，唔覆蓋開單日期）
async function loadFromBase() {
    const orderNo = document.getElementById("baseOrderNo").value.trim();
    const tipLoad = document.getElementById("tipLoad");
    const tipErr = document.getElementById("tipErr");
    const btn = document.querySelector(".btn-green");
    tipLoad.innerText = "";
    tipErr.innerText = "";
    if (!orderNo) {
        tipErr.innerText = "請輸入單據編號";
        return;
    }
    tipLoad.innerText = "正在連接飛書Base載入訂單數據...";
    btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}?orderNo=${encodeURIComponent(orderNo)}`);
        const data = await res.json();
        if (data.code !== 0) {
            tipErr.innerText = "載入失敗：" + data.msg;
            return;
        }
        tipLoad.innerText = "✅ 載入成功，數據已自動填充（開單日期維持本地今日）";
        const type = data.type;
        document.getElementById("invoiceType").value = type;
        refreshForm();
        if (type === "repair") {
            document.getElementById("inpCustName").value = data.custName;
            document.getElementById("inpTel").value = data.custTel;
            document.getElementById("inpAddr").value = data.delAddr;
            document.getElementById("inpModel").value = data.model;
            document.getElementById("inpSN").value = data.sn;
            document.getElementById("inpServiceText").value = data.serviceText;
            document.getElementById("inpServiceFee").value = Number(data.serviceFee).toFixed(2);
            document.getElementById("inpDelFee").value = Number(data.delFee).toFixed(2);
            document.getElementById("inpWarranty").value = data.warrantyMonth;
            document.getElementById("inpRemark").value = data.remark;
            document.getElementById("chkDiag").checked = data.items.includes("專業故障診斷");
            document.getElementById("chkClean").checked = data.items.includes("深層清潔");
            document.getElementById("chkPart").checked = data.items.includes("零件更換");
            document.getElementById("chkOther").checked = data.items.includes("其他維修服務");
            calcRepair();
        } else if (type === "sale") {
            document.getElementById("saleInvNo").value = data.invNo;
            document.getElementById("saleCustName").value = data.custName;
            document.getElementById("saleTel").value = data.custTel;
            document.getElementById("saleWhatsapp").value = data.whatsapp;
            document.getElementById("saleAddr").value = data.delAddr;
            document.getElementById("saleModel").value = data.model;
            document.getElementById("saleSpec").value = data.spec;
            document.getElementById("salePrice").value = Number(data.price).toFixed(2);
            document.getElementById("saleQty").value = data.qty;
            document.getElementById("saleDisc").value = Number(data.discount).toFixed(2);
            document.getElementById("saleDelMethod").value = data.delMethod;
            document.getElementById("saleWarranty").value = data.warranty;
            document.getElementById("salePay").value = data.payMethod;
            document.getElementById("saleRemark").value = data.remark;
            calcSale();
        }
        refreshPreview();
    } catch (e) {
        tipErr.innerText = "載入失敗：伺服器錯誤，請確認後端已上線開啟CORS";
    } finally {
        btn.disabled = false;
    }
}
