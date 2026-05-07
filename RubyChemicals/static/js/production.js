let csrf, endpoints, stockItems = [], currentCardId = null

function init(csrfToken, eps) {
  csrf = csrfToken
  endpoints = eps
  loadStock()
  loadBatches()
}

async function loadStock() {
  const [ok, res] = await callApi("GET", endpoints.stock)
  if (ok) {
    stockItems = res.data
  }
}

function addRawMaterialRow() {
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

function addBatchRow() {
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

async function createProductionCardWithBatches() {
  // Collect raw materials
  const raws = document.querySelectorAll(".raw-item")
  const qtys = document.querySelectorAll(".raw-qty")

  let consumptions = []
  raws.forEach((r, i) => {
    if (r.value && qtys[i].value) {
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
    if (code.value && batchProducts[i].value && batchOutputs[i].value) {
      batches.push({
        batch_code: code.value,
        product_stock_item_id: batchProducts[i].value,
        output_quantity: batchOutputs[i].value,
        loss_quantity: batchLosses[i].value || 0
      })
    }
  })

  if (batches.length === 0) {
    alert("Please add at least one batch")
    return
  }

  const payload = {
    production_code: document.getElementById("productionCode").value,
    production_date: document.getElementById("productionDate").value,
    product_name: document.getElementById("productName").value,
    production_incharge: document.getElementById("productionIncharge").value,
    total_output_quantity: document.getElementById("totalOutputQty").value,
    total_loss: document.getElementById("totalLoss").value || 0,
    unit: document.getElementById("unitSelect").value,
    remarks: document.getElementById("remarks").value,
    consumptions: consumptions,
    batches: batches
  }

  const [result, response] = await callApi("POST", endpoints.productionCard, payload, csrf)

  if (result && response.success) {
    alert("Production card with batches created successfully!")
    document.getElementById("productionCode").value = ""
    document.getElementById("productionDate").value = ""
    document.getElementById("productName").value = ""
    document.getElementById("totalOutputQty").value = ""
    document.getElementById("totalLoss").value = ""
    document.getElementById("remarks").value = ""
    document.getElementById("unitSelect").value = "kg"
    document.getElementById("rawList").innerHTML = ""
    document.getElementById("batchesList").innerHTML = ""

    const modal = bootstrap.Modal.getInstance(document.getElementById("productionCardModal"))
    if (modal) modal.hide()

    loadBatches()
  }
  else {
    if (response && response.error) alert("Error: " + response.error)
    else alert("Failed to create production card")
  }
}

async function loadBatches() {
  const [ok, res] = await callApi("GET", endpoints.productionBatch)
  if (ok) {
    const table = document.getElementById("batchTable")

    const rows = res.data.map(b => `
      <tr>
        <td><span class="production-code">${b.batch_code}</span></td>
        <td class="is_a_prod_code">${b.production_code || 'N/A'}</td>
        <td>${CustomformatDate(b.production_date) || 'N/A'}</td>
        <td>${b.product_name}</td>
        <td><strong>${b.output_quantity}</strong> ${b.product_unit}</td>        
        <td><strong>${b.loss_quantity}</strong> ${b.product_unit}</td>              
        <td>
          <div class="action-buttons">
            <button class="btn btn-info" onclick="viewProductionCard(${b.production_card_id})"><i class="fas fa-eye"></i> View</button>            
            
          </div>
        </td>
      </tr>
    `).join("")

    // <button class="btn btn-warning" onclick="editBatch(${b.id})"><i class="fas fa-edit"></i> Edit</button>
    // <button class="btn btn-danger" onclick="deleteBatch(${b.id})"><i class="fas fa-trash"></i> Delete</button>

    const tbody = table.querySelector("tbody")
    tbody.innerHTML = rows || '<tr><td colspan="6" class="text-center text-muted py-4">No production batches found</td></tr>'

    // Trigger KPI rendering
    if (window.renderKPIStats) {
      window.renderKPIStats()
    }
  }
}

async function viewProductionCard(cardId) {
  currentCardId = cardId
  const [ok, res] = await callApi("GET", `${endpoints.productionCard}${cardId}/`)
  if (ok && res.data) {
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
        <div class="col-md-6"><strong>Date:</strong> ${CustomformatDate(card.production_date)}</div>
        <div class="col-md-6"><strong>Code:</strong> ${card.production_code}</div>
        </div>
        <div class="row mb-3">
        <div class="col-md-6"><strong>Product Name:</strong> ${card.product_name || 'N/A'}</div>
          <div class="col-md-6"><strong>Batches:</strong> ${batches.length}</div>
          </div>
          <div class="row">
          <div class="col-md-6"><strong>Total Output:</strong> ${card.total_output_quantity} ${card.unit}</div>
          <div class="col-md-6"><strong>Total Loss:</strong> ${card.total_loss} ${card.unit}</div>
          <div class="col-md-6"><strong>Production Incharge:</strong> ${card.production_incharge}</div>
        </div>        
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

      ${card.remarks ? `<div class="row mt-3"><div class="col-12"><strong>Remarks:</strong> <p style="margin-top: 0.5rem; color: #64748b;">${card.remarks}</p></div></div>` : ''}
    `

    document.getElementById("cardDetailsContent").innerHTML = html
    const detailModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("productionDetailModal"))
    detailModal.show()
  }
}

async function editProductionCard() {
  if (!currentCardId) return
  
  const [ok, res] = await callApi("GET", `${endpoints.productionCard}${currentCardId}/`)
  if (ok && res.data) {
    const card = res.data.production_card
    const batches = res.data.batches
    const consumptions = res.data.consumptions

    // Populate form fields
    document.getElementById("editProductionCode").value = card.production_code
    document.getElementById("editProductionDate").value = card.production_date
    document.getElementById("editProductName").value = card.product_name || ""
    document.getElementById("editProductionIncharge").value = card.production_incharge || ""
    document.getElementById("editTotalLoss").value = card.total_loss || 0
    document.getElementById("editTotalOutputQty").value = card.total_output_quantity
    document.getElementById("editUnitSelect").value = card.unit
    document.getElementById("editRemarks").value = card.remarks || ""

    // Populate raw materials
    document.getElementById("editRawList").innerHTML = ""
    consumptions.forEach(c => {
      const row = `
        <div class="d-flex mb-3" style="gap: 12px; align-items: flex-end;">
          <div style="flex: 1;">
            <select class="form-control edit-raw-item" style="border-radius: 8px;">
              <option value="">Select Material</option>
              ${stockItems.map(i => `<option value="${i.id}" ${i.id == c.stock_item_id ? 'selected' : ''}>${i.name} (${i.unit})</option>`).join("")}
            </select>
          </div>
          <div style="width: 120px;">
            <input class="form-control edit-raw-qty" placeholder="Qty" value="${c.quantity_used}" style="border-radius: 8px;" type="number" autocomplete="off">
          </div>
          <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
        </div>
      `
      document.getElementById("editRawList").insertAdjacentHTML("beforeend", row)
    })

    // Populate batches
    document.getElementById("editBatchesList").innerHTML = ""
    batches.forEach(b => {
      const row = `
        <div class="d-flex mb-3" style="gap: 10px; align-items: flex-end;">
          <div style="flex: 1; min-width: 140px;">
            <input class="form-control edit-batch-code" placeholder="Batch Code" value="${b.batch_code}" style="border-radius: 8px;" autocomplete="off">
          </div>
          <div style="flex: 1; min-width: 160px;">
            <select class="form-control edit-batch-product" style="border-radius: 8px;">
              <option value="">Select Product</option>
              ${stockItems.map(i => `<option value="${i.id}" ${i.id == b.product_id ? 'selected' : ''}>${i.name} (${i.unit})</option>`).join("")}
            </select>
          </div>
          <div style="width: 100px;">
            <input class="form-control edit-batch-output" placeholder="Output" type="number" value="${b.output_quantity}" style="border-radius: 8px;" autocomplete="off">
          </div>
          <div style="width: 100px;">
            <input class="form-control edit-batch-loss" placeholder="Loss" type="number" value="${b.loss_quantity}" style="border-radius: 8px;" autocomplete="off">
          </div>
          <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
        </div>
      `
      document.getElementById("editBatchesList").insertAdjacentHTML("beforeend", row)
    })

    // Close detail modal and open edit modal
    bootstrap.Modal.getInstance(document.getElementById("productionDetailModal")).hide()
    const editModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("editProductionCardModal"))
    editModal.show()
  }
}

function addEditRawMaterial() {
  const row = `
    <div class="d-flex mb-3" style="gap: 12px; align-items: flex-end;">
      <div style="flex: 1;">
        <select class="form-control edit-raw-item" style="border-radius: 8px;">
          <option value="">Select Material</option>
          ${stockItems.map(i => `<option value="${i.id}">${i.name} (${i.unit})</option>`).join("")}
        </select>
      </div>
      <div style="width: 120px;">
        <input class="form-control edit-raw-qty" placeholder="Qty" style="border-radius: 8px;" type="number" autocomplete="off">
      </div>
      <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
    </div>
  `
  document.getElementById("editRawList").insertAdjacentHTML("beforeend", row)
}

function addEditBatch() {
  const row = `
    <div class="d-flex mb-3" style="gap: 10px; align-items: flex-end;">
      <div style="flex: 1; min-width: 140px;">
        <input class="form-control edit-batch-code" placeholder="Batch Code" style="border-radius: 8px;" autocomplete="off">
      </div>
      <div style="flex: 1; min-width: 160px;">
        <select class="form-control edit-batch-product" style="border-radius: 8px;">
          <option value="">Select Product</option>
          ${stockItems.map(i => `<option value="${i.id}">${i.name} (${i.unit})</option>`).join("")}
        </select>
      </div>
      <div style="width: 100px;">
        <input class="form-control edit-batch-output" placeholder="Output" type="number" style="border-radius: 8px;" autocomplete="off">
      </div>
      <div style="width: 100px;">
        <input class="form-control edit-batch-loss" placeholder="Loss" type="number" style="border-radius: 8px;" autocomplete="off">
      </div>
      <button class="btn btn-danger btn-sm" type="button" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
    </div>
  `
  document.getElementById("editBatchesList").insertAdjacentHTML("beforeend", row)
}

async function submitEditProductionCard() {
  if (!currentCardId) return

  const consumptions = []
  document.querySelectorAll(".edit-raw-item").forEach((el, i) => {
    const qty = document.querySelectorAll(".edit-raw-qty")[i]
    if (el.value && qty.value) {
      consumptions.push({
        stock_item_id: el.value,
        quantity: qty.value
      })
    }
  })

  const batches = []
  document.querySelectorAll(".edit-batch-code").forEach((el, i) => {
    const product = document.querySelectorAll(".edit-batch-product")[i]
    const output = document.querySelectorAll(".edit-batch-output")[i]
    const loss = document.querySelectorAll(".edit-batch-loss")[i]
    if (el.value && product.value && output.value) {
      batches.push({
        batch_code: el.value,
        product_stock_item_id: product.value,
        output_quantity: output.value,
        loss_quantity: loss.value || 0
      })
    }
  })

  const payload = {
    production_code: document.getElementById("editProductionCode").value,
    production_date: document.getElementById("editProductionDate").value,
    product_name: document.getElementById("editProductName").value,
    production_incharge: document.getElementById("editProductionIncharge").value,
    total_output_quantity: document.getElementById("editTotalOutputQty").value,
    total_loss: document.getElementById("editTotalLoss").value || 0,
    unit: document.getElementById("editUnitSelect").value,
    remarks: document.getElementById("editRemarks").value,
    consumptions: consumptions,
    batches: batches
  }

  const [result, response] = await callApi("PUT", `${endpoints.productionCard}${currentCardId}/`, payload, csrf)

  if (result && response.success) {
    alert("Production card updated successfully!")
    bootstrap.Modal.getInstance(document.getElementById("editProductionCardModal")).hide()
    currentCardId = null
    loadBatches()
  } else {
    if (response && response.error) alert("Error: " + response.error)
    else alert("Failed to update production card")
  }
}

async function deleteProductionCard() {
  if (!currentCardId) return
  if (confirm("Are you sure you want to delete this production card?")) {
    const [ok, res] = await callApi("DELETE", `${endpoints.productionCard}${currentCardId}/`, {}, csrf)
    if (ok && res.success) {
      alert("Production card deleted successfully!")
      bootstrap.Modal.getInstance(document.getElementById("productionDetailModal")).hide()
      currentCardId = null
      loadBatches()
    } else {
      alert("Error: " + (res.error || "Failed to delete"))
    }
  }
}

async function editBatch(batchId) {
  alert("Edit batch functionality to be implemented")
}

async function deleteBatch(batchId) {
  if (confirm("Are you sure you want to delete this batch?")) {
    const [ok, res] = await callApi("DELETE", `${endpoints.productionBatch}${batchId}/`, {}, csrf)
    if (ok && res.success) {
      alert("Batch deleted successfully!")
      loadBatches()
    } else {
      alert("Error: " + (res.error || "Failed to delete"))
    }
  }
}



async function generatePDF_old() {
    const { jsPDF } = window.jspdf;

    const original = document.getElementById("cardDetailsContent");

    // Clone
    const clone = original.cloneNode(true);

    // Force clean PDF styles
    clone.querySelectorAll("*").forEach(el => {
        el.style.color = "#000 !important"; // force black text
        el.style.backgroundColor = "transparent"; // remove weird blends
    });

    clone.querySelectorAll("th, td").forEach(el => {
        el.style.color = "#000 !important";
        el.style.borderColor = "#000 !important";
    });

    clone.querySelectorAll("thead").forEach(el => {
        el.style.background = "#e5e5e5"; // solid header
    });

    clone.querySelectorAll("tbody tr td").forEach(el => {
        el.style.setProperty("color", "#000", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("font-weight", "500", "important");
    });


    clone.style.width = "800px";
    clone.style.padding = "20px";
    clone.style.background = "#fff";

    // Mount offscreen
    const container = document.createElement("div");
    container.style.position = "fixed";
    container.style.top = "-9999px";
    container.appendChild(clone);
    document.body.appendChild(container);

    await new Promise(r => setTimeout(r, 300));

    const canvas = await html2canvas(clone, {
        scale: 2,
        useCORS: true
    });

    const pdf = new jsPDF("p", "mm", "a4");

    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    const marginTop = 20;

    const imgWidth = pageWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 🔥 Calculate page height in canvas pixels
    const pageHeightPx = (canvasWidth * (pageHeight - marginTop)) / pageWidth;

    let currentPosition = 0;

    const addHeader = () => {
        pdf.setFontSize(14);
        pdf.text("Production Report", pageWidth / 2, 10, { align: "center" });
    };

    while (currentPosition < canvasHeight) {

        // Create a temporary canvas for each page
        const pageCanvas = document.createElement("canvas");
        const context = pageCanvas.getContext("2d");

        pageCanvas.width = canvasWidth;
        pageCanvas.height = Math.min(pageHeightPx, canvasHeight - currentPosition);

        context.drawImage(
            canvas,
            0,
            currentPosition,
            canvasWidth,
            pageCanvas.height,
            0,
            0,
            canvasWidth,
            pageCanvas.height
        );

        const imgData = pageCanvas.toDataURL("image/png");

        if (currentPosition > 0) pdf.addPage();

        addHeader();

        const imgHeightMM = (pageCanvas.height * imgWidth) / canvasWidth;

        pdf.addImage(imgData, "PNG", 0, marginTop, imgWidth, imgHeightMM);

        currentPosition += pageHeightPx;
    }

    pdf.save("report.pdf");

    document.body.removeChild(container);
}


async function generatePDF() {
  toggle_loader()
  window.location = `/operation-api/download-production-card-api/${currentCardId}/`
  toggle_loader()
}

