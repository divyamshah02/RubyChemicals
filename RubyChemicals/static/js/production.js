let csrf, endpoints, stockItems = []

function init(csrfToken, eps){
  csrf = csrfToken
  endpoints = eps
  loadStock()
  loadProductions()
}

async function loadStock(){
  const [ok, res] = await callApi("GET", endpoints.stock)
  if(ok){
    stockItems = res.data
    renderProductDropdown()
  }
}

function renderProductDropdown(){
  const select = document.getElementById("productSelect")
  select.innerHTML = stockItems.map(i =>
    `<option value="${i.id}">${i.name}</option>`
  ).join("")
}

function addRow(){
  const row = `
    <div class="d-flex mb-3" style="gap: 12px; align-items: flex-end;">
      <div style="flex: 1;">
        <label style="font-size: 0.85rem; margin-bottom: 6px; display: block;">Material</label>
        <select class="form-control raw-item" style="border-radius: 8px;">
          <option value="">Select Material</option>
          ${stockItems.map(i => `<option value="${i.id}">${i.name}</option>`).join("")}
        </select>
      </div>
      <div style="width: 120px;">
        <label style="font-size: 0.85rem; margin-bottom: 6px; display: block;">Quantity</label>
        <input class="form-control raw-qty" placeholder="0" style="border-radius: 8px;" autocomplete="off">
      </div>
      <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()" style="margin-bottom: 2px;"><i class="fas fa-trash"></i></button>
    </div>
  `
  document.getElementById("rawList").insertAdjacentHTML("beforeend", row)
}

async function createProduction(){
  const raws = document.querySelectorAll(".raw-item")
  const qtys = document.querySelectorAll(".raw-qty")

  let consumptions = []
  raws.forEach((r,i)=>{
    consumptions.push({
      stock_item_id: r.value,
      quantity: qtys[i].value
    })
  })

  const payload = {
    batch_code: document.getElementById("batchCode").value,
    product_stock_item_id: document.getElementById("productSelect").value,
    production_date: document.getElementById("productionDate").value,
    output_quantity: document.getElementById("outputQty").value,
    loss_quantity: document.getElementById("lossQty").value,
    consumptions
  }

  const [result, response] = await callApi("POST", endpoints.production, payload, csrf)
  if(result && response.success){
    alert("Production record created successfully!")
    loadProductions()
  }
  else {
    if (response && response.error) alert("Error: " + response.error)
    else alert("An unexpected error occurred.")
  }

}

async function loadProductions(){
  const [ok, res] = await callApi("GET", endpoints.production)
  if(ok){
    const table = document.getElementById("productionTable")
    const headers = `<thead><tr><th><i class="fas fa-barcode"></i> Batch</th><th><i class="fas fa-cube"></i> Product</th><th><i class="fas fa-arrow-up"></i> Output</th><th><i class="fas fa-exclamation-triangle"></i> Loss</th></tr></thead>`
    const rows = res.data.map(p => `
      <tr>
        <td><code style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px;">${p.batch_code}</code></td>
        <td>${p.product_name}</td>
        <td><span style="background: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 6px; font-weight: 600;">${p.output_quantity}</span></td>
        <td><span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 6px;">${p.loss_quantity}</span></td>
      </tr>
    `).join("")
    table.innerHTML = headers + `<tbody>${rows}</tbody>`
  }
}
