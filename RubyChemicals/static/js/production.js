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
    <div class="d-flex mb-2">
      <select class="form-control me-2 raw-item">
        ${stockItems.map(i => `<option value="${i.id}">${i.name}</option>`).join("")}
      </select>
      <input class="form-control raw-qty" placeholder="Qty">
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

  await callApi("POST", endpoints.production, payload, csrf)
  loadProductions()
}

async function loadProductions(){
  const [ok, res] = await callApi("GET", endpoints.production)
  if(ok){
    const table = document.getElementById("productionTable")
    table.innerHTML = `
      <tr><th>Batch</th><th>Product</th><th>Output</th><th>Loss</th></tr>
      ${res.data.map(p => `
        <tr>
          <td>${p.batch_code}</td>
          <td>${p.product_name}</td>
          <td>${p.output_quantity}</td>
          <td>${p.loss_quantity}</td>
        </tr>
      `).join("")}
    `
  }
}
