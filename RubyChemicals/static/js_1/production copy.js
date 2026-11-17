let csrf, endpoints, stockItems = []

function init(csrfToken, eps){
  csrf = csrfToken
  endpoints = eps
  loadStock()
  loadBatches()
}

async function loadStock(){
  const [ok, res] = await callApi("GET", endpoints.stock)
  if(ok){
    stockItems = res.data
  }
}

function addRawMaterialRow(){
  const row = `
    <div class="d-flex mb-3" style="gap: 12px; align-items: flex-end;">
      <div style="flex: 1;">
        <select class="form-control raw-item" style="border-radius: 8px;">
          <option value="">Select Material</option>
          ${stockItems.map(i => `<option value="${i.id}">${i.name} (${i.unit})</option>`).join("")}
        </select>
      </div>
      <div style="width: 120px;">
        <input class="form-control raw-qty" placeholder="Qty" style="border-radius: 8px;" type="number" autocomplete="off">
      </div>
      <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
    </div>
  `
  document.getElementById("rawList").insertAdjacentHTML("beforeend", row)
}

function addBatchRow(){
  const row = `
    <div class="d-flex mb-3" style="gap: 10px; align-items: flex-end;">
      <div style="flex: 1; min-width: 140px;">
        <input class="form-control batch-code" placeholder="Batch Code" style="border-radius: 8px;" autocomplete="off">
      </div>
      <div style="flex: 1; min-width: 160px;">
        <select class="form-control batch-product" style="border-radius: 8px;">
          <option value="">Select Product</option>
          ${stockItems.map(i => `<option value="${i.id}">${i.name} (${i.unit})</option>`).join("")}
        </select>
      </div>
      <div style="width: 100px;">
        <input class="form-control batch-output" placeholder="Output" type="number" style="border-radius: 8px;" autocomplete="off">
      </div>
      <div style="width: 100px;">
        <input class="form-control batch-loss" placeholder="Loss" type="number" style="border-radius: 8px;" autocomplete="off">
      </div>
      <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
    </div>
  `
  document.getElementById("batchesList").insertAdjacentHTML("beforeend", row)
}

async function createProductionCardWithBatches(){
  // Collect raw materials
  const raws = document.querySelectorAll(".raw-item")
  const qtys = document.querySelectorAll(".raw-qty")
  
  let consumptions = []
  raws.forEach((r,i)=>{
    if(r.value && qtys[i].value){
      consumptions.push({
        stock_item_id: r.value,
        quantity: qtys[i].value
      })
    }
  })

  // Collect batches
  const batchCodes = document.querySelectorAll(".batch-code")
  const batchProducts = document.querySelectorAll(".batch-product")
  const batchOutputs = document.querySelectorAll(".batch-output")
  const batchLosses = document.querySelectorAll(".batch-loss")

  let batches = []
  batchCodes.forEach((code, i) => {
    if(code.value && batchProducts[i].value && batchOutputs[i].value){
      batches.push({
        batch_code: code.value,
        product_stock_item_id: batchProducts[i].value,
        output_quantity: batchOutputs[i].value,
        loss_quantity: batchLosses[i].value || 0
      })
    }
  })

  if(batches.length === 0){
    alert("Please add at least one batch")
    return
  }

  const payload = {
    production_code: document.getElementById("productionCode").value,
    production_date: document.getElementById("productionDate").value,
    total_output_quantity: document.getElementById("totalOutputQty").value,
    unit: document.getElementById("unitSelect").value,
    consumptions: consumptions,
    batches: batches
  }

  const [result, response] = await callApi("POST", endpoints.productionCard, payload, csrf)

  if(result && response.success){
    alert("Production card with batches created successfully!")
    document.getElementById("productionCode").value = ""
    document.getElementById("productionDate").value = ""
    document.getElementById("totalOutputQty").value = ""
    document.getElementById("unitSelect").value = "kg"
    document.getElementById("rawList").innerHTML = ""
    document.getElementById("batchesList").innerHTML = ""
    
    const modal = bootstrap.Modal.getInstance(document.getElementById("productionCardModal"))
    if(modal) modal.hide()
    
    loadBatches()
  }
  else {
    if (response && response.error) alert("Error: " + response.error)
    else alert("Failed to create production card")
  }
}

async function loadBatches(){
  const [ok, res] = await callApi("GET", endpoints.productionBatch)
  if(ok){
    const table = document.getElementById("batchTable")
    
    const rows = res.data.map(b => `
      <tr>
        <td><span class="production-code">${b.batch_code}</span></td>
        <td>${b.production_date || 'N/A'}</td>
        <td><strong>${b.output_quantity}</strong> ${b.product_unit}</td>
        <td><span style="background: #dcfce7; color: #15803d; padding: 0.375rem 0.75rem; border-radius: 6px; font-size: 0.875rem; font-weight: 600;">Active</span></td>
        <td>${b.created_by || 'System'}</td>
        <td>
          <div class="action-buttons">
            <button class="btn btn-info" onclick="viewProductionCard(${b.production_card_id})"><i class="fas fa-eye"></i> View</button>
            <button class="btn btn-warning" onclick="editBatch(${b.id})"><i class="fas fa-edit"></i> Edit</button>
            <button class="btn btn-danger" onclick="deleteBatch(${b.id})"><i class="fas fa-trash"></i> Delete</button>
          </div>
        </td>
      </tr>
    `).join("")
    
    const tbody = table.querySelector("tbody")
    tbody.innerHTML = rows || '<tr><td colspan="6" class="text-center text-muted py-4">No production batches found</td></tr>'
    
    // Trigger KPI rendering
    if (window.renderKPIStats) {
      window.renderKPIStats()
    }
  }
}

async function viewProductionCard(cardId){
  const [ok, res] = await callApi("GET", `${endpoints.productionCard}${cardId}/`)
  if(ok && res.data){
    const card = res.data.production_card
    const batches = res.data.batches
    const consumptions = res.data.consumptions

    let batchesHtml = batches.map(b => `
      <tr>
        <td><code style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px;">${b.batch_code}</code></td>
        <td>${b.product_name}</td>
        <td><strong>${b.output_quantity} ${b.product_unit}</strong></td>
        <td>${b.loss_quantity} ${b.product_unit}</td>
      </tr>
    `).join("")

    let consumptionsHtml = consumptions.map(c => `
      <tr>
        <td>${c.stock_item_name}</td>
        <td><strong>${c.quantity_used} ${c.stock_item_unit}</strong></td>
      </tr>
    `).join("")

    const html = `
      <div style="margin-bottom: 2rem;">
        <h6 style="color: #1e40af; font-weight: 700; margin-bottom: 1rem;"><i class="fas fa-info-circle"></i> Card Details</h6>
        <div class="row mb-3">
          <div class="col-md-6"><strong>Code:</strong> ${card.production_code}</div>
          <div class="col-md-6"><strong>Date:</strong> ${card.production_date}</div>
        </div>
        <div class="row">
          <div class="col-md-6"><strong>Total Output:</strong> ${card.total_output_quantity} ${card.unit}</div>
          <div class="col-md-6"><strong>Batches:</strong> ${batches.length}</div>
        </div>
      </div>

      <hr style="border-color: #e2e8f0;">

      <h6 style="color: #1e40af; font-weight: 700; margin-bottom: 1rem;"><i class="fas fa-cubes"></i> Batches (${batches.length})</h6>
      <div style="overflow-x: auto;">
        <table class="table table-sm">
          <thead style="background: #f0f9ff;">
            <tr><th>Batch Code</th><th>Product</th><th>Output</th><th>Loss</th></tr>
          </thead>
          <tbody>${batchesHtml || '<tr><td colspan="4" class="text-center text-muted">No batches</td></tr>'}</tbody>
        </table>
      </div>

      <hr style="border-color: #e2e8f0;">

      <h6 style="color: #1e40af; font-weight: 700; margin-bottom: 1rem;"><i class="fas fa-flask"></i> Raw Materials</h6>
      <div style="overflow-x: auto;">
        <table class="table table-sm">
          <thead style="background: #f0f9ff;">
            <tr><th>Material</th><th>Quantity Used</th></tr>
          </thead>
          <tbody>${consumptionsHtml || '<tr><td colspan="2" class="text-center text-muted">No materials</td></tr>'}</tbody>
        </table>
      </div>
    `

    document.getElementById("cardDetailsContent").innerHTML = html
    const detailModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("productionDetailModal"))
    detailModal.show()
  }
}

async function editProductionCard(cardId){
  alert("Edit functionality to be implemented")
}

async function deleteProductionCard(cardId){
  if(confirm("Are you sure you want to delete this production card?")){
    const [ok, res] = await callApi("DELETE", `${endpoints.productionCard}${cardId}/`, {}, csrf)
    if(ok && res.success){
      alert("Production card deleted successfully!")
      loadBatches()
    } else {
      alert("Error: " + (res.error || "Failed to delete"))
    }
  }
}

async function editBatch(batchId){
  alert("Edit batch functionality to be implemented")
}

async function deleteBatch(batchId){
  if(confirm("Are you sure you want to delete this batch?")){
    const [ok, res] = await callApi("DELETE", `${endpoints.productionBatch}${batchId}/`, {}, csrf)
    if(ok && res.success){
      alert("Batch deleted successfully!")
      loadBatches()
    } else {
      alert("Error: " + (res.error || "Failed to delete"))
    }
  }
}
