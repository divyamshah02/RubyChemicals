// lead_sub_dept_mgmt.js — Leads Department Management
// Place at: /static/js/lead_sub_dept_mgmt.js

let mgmtCsrf, mgmtEndpoints
let allSubDepts   = []
let allStockItems = []
let allAppAreas   = []
let currentTab    = 'stock-items'
let spItems       = []             // items in the system-product modal being created/edited
let currentSpSubDeptId = null      // sub-dept id of the area whose SP modal is open

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

async function initMgmt(csrfToken, endpoints) {
  mgmtCsrf      = csrfToken
  mgmtEndpoints = endpoints
  await loadSubDepts()
  await loadStockItems()
  renderTabHeaderActions()
}

// ─────────────────────────────────────────────
// TAB SWITCHING
// ─────────────────────────────────────────────

function switchTab(tabName) {
  currentTab = tabName
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'))
  document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'))
  document.getElementById(`tab-${tabName}`).classList.add('active')
  document.querySelectorAll('.nav-tab-btn').forEach(b => {
    if (b.getAttribute('onclick').includes(`'${tabName}'`)) b.classList.add('active')
  })
  renderTabHeaderActions()

  if (tabName === 'stock-items') loadStockItems()
  if (tabName === 'app-areas')   loadAppAreas()
}

function renderTabHeaderActions() {
  const container = document.getElementById("pageHeaderActions")
  if (!container) return

  const tabActions = {
    'sub-depts':   `<button class="btn btn-primary-custom" onclick="openSubDeptModal()"><i class="fas fa-plus me-1"></i>Add Sub-Department</button>`,
    'stock-items': `<button class="btn btn-success-custom" onclick="openStockItemModal()"><i class="fas fa-plus me-1"></i>Add Stock Item</button>`,
    'app-areas':   `<button class="btn btn-teal" onclick="openAppAreaModal()" style="background:#0d9488; color:white; border:none; border-radius:8px; padding:0.625rem 1.25rem; font-weight:500;"><i class="fas fa-plus me-1"></i>Add Application Area</button>`,
  }
  container.innerHTML = tabActions[currentTab] || ""
}

// ─────────────────────────────────────────────
// SUB-DEPARTMENTS
// ─────────────────────────────────────────────

async function loadSubDepts() {
  const [ok, res] = await callApi("GET", mgmtEndpoints.subDepts)
  if (ok && res.success) {
    allSubDepts = res.data || []
    renderSubDeptsTable()
    populateSubDeptSelects()
  }
}

function renderSubDeptsTable() {
  const tbody = document.querySelector("#subDeptTable tbody")
  document.getElementById("subDeptCount").textContent =
    `${allSubDepts.length} sub-department${allSubDepts.length !== 1 ? "s" : ""}`

  if (allSubDepts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No sub-departments yet. Create one!</td></tr>'
    return
  }

  tbody.innerHTML = allSubDepts.map((d, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${d.name}</strong></td>
      <td><span class="subdept-badge">${d.code}</span></td>
      <td>${d.description || "—"}</td>
      <td><span class="badge bg-primary" style="font-size:0.78rem;">${d.stock_item_count || 0}</span></td>
      <td>
        <span class="${d.is_active ? 'badge-active' : 'badge-inactive'}">
          ${d.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td>
        <div class="action-buttons">
          <button class="btn btn-warning btn-sm" title="Edit" onclick="openEditSubDept(${d.id})">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-danger btn-sm" title="Delete" onclick="deleteSubDept(${d.id})">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>`).join("")
}

function populateSubDeptSelects() {
  const selects = ["siSubDept", "aaSubDept", "stockSubDeptFilter", "appAreaSubDeptFilter"]
  selects.forEach(id => {
    const el = document.getElementById(id)
    if (!el) return
    const isFilter = id.includes("Filter")
    el.innerHTML = isFilter
      ? '<option value="">All Sub-Departments</option>'
      : '<option value="">-- Select Sub-Department --</option>'
    allSubDepts.forEach(d => { el.innerHTML += `<option value="${d.id}">${d.name}</option>` })
  })
}

function openSubDeptModal() {
  document.getElementById("sdId").value          = ""
  document.getElementById("sdName").value        = ""
  document.getElementById("sdCode").value        = ""
  document.getElementById("sdDescription").value = ""
  document.getElementById("sdSubmitBtnText").textContent = "Create Sub-Department"
  document.getElementById("subDeptModalTitle").innerHTML =
    '<i class="fas fa-sitemap" style="color:#7c3aed; margin-right:0.5rem;"></i>New Sub-Department'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("subDeptModal")).show()
}

async function openEditSubDept(sdId) {
  const dept = allSubDepts.find(d => d.id === sdId)
  if (!dept) return
  document.getElementById("sdId").value          = dept.id
  document.getElementById("sdName").value        = dept.name
  document.getElementById("sdCode").value        = dept.code
  document.getElementById("sdDescription").value = dept.description || ""
  document.getElementById("sdSubmitBtnText").textContent = "Update Sub-Department"
  document.getElementById("subDeptModalTitle").innerHTML =
    '<i class="fas fa-sitemap" style="color:#7c3aed; margin-right:0.5rem;"></i>Edit Sub-Department'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("subDeptModal")).show()
}

async function submitSubDept() {
  const name = document.getElementById("sdName").value.trim()
  const code = document.getElementById("sdCode").value.trim().toUpperCase()
  if (!name || !code) { alert("Name and Code are required."); return }

  const sdId    = document.getElementById("sdId").value
  const isEdit  = !!sdId
  const payload = { name, code, description: document.getElementById("sdDescription").value }

  const url    = isEdit ? `${mgmtEndpoints.subDepts}${sdId}/` : mgmtEndpoints.subDepts
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, mgmtCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("subDeptModal")).hide()
    await loadSubDepts()
    alert(`Sub-Department ${isEdit ? "updated" : "created"} successfully!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save"))
  }
}

async function deleteSubDept(sdId) {
  if (!confirm("Delete this sub-department? This may affect existing leads and stock items.")) return
  const [ok, res] = await callApi("DELETE", `${mgmtEndpoints.subDepts}${sdId}/`, {}, mgmtCsrf)
  if (ok && res.success) { await loadSubDepts(); alert("Deleted successfully!") }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}

// ─────────────────────────────────────────────
// STOCK ITEMS
// ─────────────────────────────────────────────

async function loadStockItems() {
  const sdFilter = document.getElementById("stockSubDeptFilter").value
  const params   = sdFilter ? `?sub_department=${sdFilter}` : ""
  const [ok, res] = await callApi("GET", mgmtEndpoints.stockItems + params)
  if (ok && res.success) {
    allStockItems = res.data || []
    renderStockItemsTable(allStockItems)
  }
}

function filterStockItems() {
  const q = document.getElementById("stockSearchInput").value.toLowerCase()
  const filtered = allStockItems.filter(item =>
    [item.product_name, item.hsn_code, item.uom, item.warranty]
      .some(v => v && v.toLowerCase().includes(q))
  )
  renderStockItemsTable(filtered)
}

function renderStockItemsTable(items) {
  const tbody = document.querySelector("#stockItemTable tbody")
  document.getElementById("stockItemCount").textContent =
    `${items.length} item${items.length !== 1 ? "s" : ""}`

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">No stock items found.</td></tr>'
    return
  }

  tbody.innerHTML = items.map((item, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><span class="subdept-badge">${item.sub_department_name || '—'}</span></td>
      <td><strong>${item.product_name}</strong></td>
      <td>${item.hsn_code || "—"}</td>
      <td>&#8377;${parseFloat(item.rate || 0).toFixed(2)}</td>
      <td>${item.uom || "—"}</td>
      <td>${item.warranty
        ? `<span style="font-size:0.8rem; color:#0369a1;">${item.warranty}</span>`
        : '<span class="text-muted">—</span>'}</td>
      <td>
        <span class="${item.is_active ? 'badge-active' : 'badge-inactive'}">
          ${item.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td>
        <div class="action-buttons">
          <button class="btn btn-warning btn-sm" onclick="openEditStockItem(${item.id})">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteStockItem(${item.id})">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>`).join("")
}

function openStockItemModal(preSubDeptId = null) {
  document.getElementById("siId").value          = ""
  document.getElementById("siProductName").value = ""
  document.getElementById("siHsn").value         = ""
  document.getElementById("siRate").value        = ""
  document.getElementById("siUom").value         = ""
  document.getElementById("siWarranty").value    = ""
  document.getElementById("siSubDept").value     =
    preSubDeptId || document.getElementById("stockSubDeptFilter").value || ""
  document.getElementById("siSubmitBtnText").textContent = "Add Stock Item"
  document.getElementById("stockModalTitle").innerHTML =
    '<i class="fas fa-box" style="color:#10b981; margin-right:0.5rem;"></i>New Stock Item'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("stockItemModal")).show()
}

async function openEditStockItem(itemId) {
  const item = allStockItems.find(i => i.id === itemId)
  if (!item) return
  document.getElementById("siId").value          = item.id
  document.getElementById("siSubDept").value     = item.sub_department || ""
  document.getElementById("siProductName").value = item.product_name || ""
  document.getElementById("siHsn").value         = item.hsn_code || ""
  document.getElementById("siRate").value        = item.rate || ""
  document.getElementById("siUom").value         = item.uom || ""
  document.getElementById("siWarranty").value    = item.warranty || ""
  document.getElementById("siSubmitBtnText").textContent = "Update Stock Item"
  document.getElementById("stockModalTitle").innerHTML =
    '<i class="fas fa-box" style="color:#10b981; margin-right:0.5rem;"></i>Edit Stock Item'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("stockItemModal")).show()
}

async function submitStockItem() {
  const subDept = document.getElementById("siSubDept").value
  const name    = document.getElementById("siProductName").value.trim()
  if (!subDept || !name) { alert("Sub-Department and Product Name are required."); return }

  const siId    = document.getElementById("siId").value
  const isEdit  = !!siId
  const payload = {
    sub_department: parseInt(subDept),
    product_name:   name,
    hsn_code:       document.getElementById("siHsn").value.trim(),
    rate:           parseFloat(document.getElementById("siRate").value) || 0,
    uom:            document.getElementById("siUom").value.trim(),
    warranty:       document.getElementById("siWarranty").value.trim() || null,
  }

  const url    = isEdit ? `${mgmtEndpoints.stockItems}${siId}/` : mgmtEndpoints.stockItems
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, mgmtCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("stockItemModal")).hide()
    await loadStockItems()
    await loadSubDepts()   // refresh counts
    alert(`Stock item ${isEdit ? "updated" : "added"} successfully!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save"))
  }
}

async function deleteStockItem(itemId) {
  if (!confirm("Delete this stock item? It will no longer appear in new quotations.")) return
  const [ok, res] = await callApi("DELETE", `${mgmtEndpoints.stockItems}${itemId}/`, {}, mgmtCsrf)
  if (ok && res.success) { await loadStockItems(); alert("Deleted!") }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}

// ─────────────────────────────────────────────
// APPLICATION AREAS
// ─────────────────────────────────────────────
// The list endpoint now returns the full ApplicationAreaSerializer (with
// system_products[].items[] and fixed_items[]) so we can render everything
// directly without extra detail calls.
// ─────────────────────────────────────────────

async function loadAppAreas() {
  const sdFilter = document.getElementById("appAreaSubDeptFilter").value
  const params   = sdFilter ? `?sub_department=${sdFilter}` : ""
  const [ok, res] = await callApi("GET", mgmtEndpoints.appAreas + params)
  if (ok && res.success) {
    allAppAreas = res.data || []
    renderAppAreaCards()
  }
}

function renderAppAreaCards() {
  const container = document.getElementById("appAreaCards")
  document.getElementById("appAreaCount").textContent =
    `${allAppAreas.length} area${allAppAreas.length !== 1 ? "s" : ""}`

  if (allAppAreas.length === 0) {
    container.innerHTML =
      '<div class="text-center text-muted py-5">' +
      '<i class="fas fa-th-large fa-2x mb-3 d-block" style="opacity:0.3;"></i>' +
      'No application areas yet. Click "Add Application Area" to create one.' +
      '</div>'
    return
  }

  container.innerHTML = allAppAreas.map(area => {
    // sub_department field on area is the FK id; use sub_department_name for display
    const areaSubDeptId   = area.sub_department       // integer id
    const areaSubDeptName = area.sub_department_name  // display string

    const sysProds   = (area.system_products || []).filter(sp => sp.is_active !== false)
    const fixedItems = (area.fixed_items     || []).filter(fi => fi.is_active !== false)

    // ── System Products section ─────────────────────────────────────────────
    const sysProdsHtml = sysProds.length === 0
      ? '<p class="text-muted" style="font-size:0.82rem;">No system products yet.</p>'
      : sysProds.map(sp => {
          const spItems = (sp.items || []).filter(i => i.is_active !== false)
          const itemRows = spItems.length === 0
            ? '<tr><td colspan="5" class="text-muted small text-center">No items in this system product.</td></tr>'
            : spItems.map(i => `
                <tr>
                  <td style="font-size:0.8rem;">${i.resolved_name || i.product_name || '—'}</td>
                  <td style="font-size:0.8rem;">${i.hsn_code || '—'}</td>
                  <td style="font-size:0.8rem;">${i.uom || '—'}</td>
                  <td style="font-size:0.8rem;">${parseFloat(i.quantity || 1)}</td>
                  <td style="font-size:0.8rem;">&#8377;${parseFloat(i.rate || 0).toFixed(2)}</td>
                </tr>`).join('')

          return `
            <div style="background:#f5f3ff; border:1px solid #ddd6fe; border-radius:8px; padding:0.75rem; margin-bottom:0.6rem;">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                  <strong style="color:#6d28d9; font-size:0.85rem;">${sp.name}</strong>
                  <span class="ms-2 badge bg-primary" style="font-size:0.7rem;">${spItems.length} item${spItems.length !== 1 ? 's' : ''}</span>
                  ${sp.description ? `<small class="text-muted ms-2">${sp.description}</small>` : ''}
                </div>
                <div class="d-flex gap-1">
                  <button class="btn btn-sm btn-warning p-1 px-2"
                    onclick="openEditSystemProduct(${sp.id}, ${area.id}, ${areaSubDeptId})"
                    title="Edit System Product">
                    <i class="fas fa-edit" style="font-size:0.72rem;"></i>
                  </button>
                  <button class="btn btn-sm btn-danger p-1 px-2"
                    onclick="deleteSystemProduct(${sp.id})"
                    title="Delete System Product">
                    <i class="fas fa-trash" style="font-size:0.72rem;"></i>
                  </button>
                </div>
              </div>
              ${spItems.length > 0 ? `
              <div class="table-responsive">
                <table class="table table-sm table-bordered mb-0" style="font-size:0.8rem;">
                  <thead class="table-light">
                    <tr>
                      <th>Item</th><th>HSN</th><th>UOM</th><th>Qty</th><th>Rate</th>
                    </tr>
                  </thead>
                  <tbody>${itemRows}</tbody>
                </table>
              </div>` : ''}
            </div>`
        }).join('')

    // ── Fixed Items section ─────────────────────────────────────────────────
    const fixedItemsHtml = fixedItems.length === 0
      ? '<p class="text-muted" style="font-size:0.82rem;">No fixed items yet.</p>'
      : `<div class="table-responsive">
           <table class="table table-sm table-bordered mb-0" style="font-size:0.8rem;">
             <thead class="table-light">
               <tr><th>Item</th><th>HSN</th><th>UOM</th><th>Qty</th><th>Rate</th><th></th></tr>
             </thead>
             <tbody>
               ${fixedItems.map(fi => `
                 <tr>
                   <td>${fi.resolved_name || fi.product_name || '—'}</td>
                   <td>${fi.hsn_code || '—'}</td>
                   <td>${fi.uom || '—'}</td>
                   <td>${parseFloat(fi.quantity || 1)}</td>
                   <td>&#8377;${parseFloat(fi.rate || 0).toFixed(2)}</td>
                   <td>
                     <button class="btn btn-danger btn-sm p-1 px-2"
                       onclick="deleteFixedItem(${fi.id})"
                       title="Remove fixed item">
                       <i class="fas fa-times" style="font-size:0.72rem;"></i>
                     </button>
                   </td>
                 </tr>`).join('')}
             </tbody>
           </table>
         </div>`

    return `
      <div class="app-area-card">
        <div class="app-area-card-header">
          <div>
            <strong>${area.name}</strong>
            <span class="subdept-badge ms-2">${areaSubDeptName || ''}</span>
            ${area.description ? `<small class="text-muted ms-2">${area.description}</small>` : ""}
          </div>
          <div class="d-flex gap-2 flex-wrap">
            <button class="btn btn-sm btn-warning"
              onclick="openEditAppArea(${area.id})">
              <i class="fas fa-edit me-1"></i>Edit Area
            </button>
            <button class="btn btn-sm"
              style="background:#7c3aed; color:white; border:none; border-radius:6px;"
              onclick="openAddSystemProduct(${area.id}, ${areaSubDeptId})">
              <i class="fas fa-plus me-1"></i>System Product
            </button>
            <button class="btn btn-sm"
              style="background:#f59e0b; color:white; border:none; border-radius:6px;"
              onclick="openFixedItemModal(${area.id}, ${areaSubDeptId})">
              <i class="fas fa-thumbtack me-1"></i>Fixed Item
            </button>
            <button class="btn btn-sm btn-danger"
              onclick="deleteAppArea(${area.id})">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
        <div class="app-area-card-body">
          <div class="row">
            <div class="col-md-7">
              <p style="font-size:0.8rem; font-weight:700; color:#6d28d9; margin-bottom:0.6rem;">
                <i class="fas fa-cube me-2"></i>System Products (${sysProds.length})
              </p>
              ${sysProdsHtml}
            </div>
            <div class="col-md-5">
              <p style="font-size:0.8rem; font-weight:700; color:#92400e; margin-bottom:0.6rem;">
                <i class="fas fa-thumbtack me-2"></i>Fixed Items (${fixedItems.length})
              </p>
              ${fixedItemsHtml}
            </div>
          </div>
        </div>
      </div>`
  }).join("")
}

// ── App Area CRUD ──────────────────────────────────────────────────────────

function openAppAreaModal(preSubDeptId = null) {
  document.getElementById("aaId").value          = ""
  document.getElementById("aaName").value        = ""
  document.getElementById("aaDescription").value = ""
  document.getElementById("aaSubDept").value     =
    preSubDeptId || document.getElementById("appAreaSubDeptFilter").value || ""
  document.getElementById("aaSubmitBtnText").textContent = "Create Area"
  document.getElementById("appAreaModalTitle").innerHTML =
    '<i class="fas fa-th-large" style="color:#0d9488; margin-right:0.5rem;"></i>New Application Area'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("appAreaModal")).show()
}

async function openEditAppArea(areaId) {
  const area = allAppAreas.find(a => a.id === areaId)
  if (!area) return
  document.getElementById("aaId").value          = area.id
  document.getElementById("aaSubDept").value     = area.sub_department || ""
  document.getElementById("aaName").value        = area.name || ""
  document.getElementById("aaDescription").value = area.description || ""
  document.getElementById("aaSubmitBtnText").textContent = "Update Area"
  document.getElementById("appAreaModalTitle").innerHTML =
    '<i class="fas fa-th-large" style="color:#0d9488; margin-right:0.5rem;"></i>Edit Application Area'
  bootstrap.Modal.getOrCreateInstance(document.getElementById("appAreaModal")).show()
}

async function submitAppArea() {
  const subDept = document.getElementById("aaSubDept").value
  const name    = document.getElementById("aaName").value.trim()
  if (!subDept || !name) { alert("Sub-Department and Name are required."); return }

  const aaId    = document.getElementById("aaId").value
  const isEdit  = !!aaId
  const payload = {
    sub_department: parseInt(subDept),
    name,
    description: document.getElementById("aaDescription").value,
  }

  const url    = isEdit ? `${mgmtEndpoints.appAreas}${aaId}/` : mgmtEndpoints.appAreas
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, mgmtCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("appAreaModal")).hide()
    await loadAppAreas()
    alert(`Application Area ${isEdit ? "updated" : "created"}!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save"))
  }
}

async function deleteAppArea(areaId) {
  if (!confirm("Delete this application area? All associated system products and fixed items will also be removed.")) return
  const [ok, res] = await callApi("DELETE", `${mgmtEndpoints.appAreas}${areaId}/`, {}, mgmtCsrf)
  if (ok && res.success) { await loadAppAreas(); alert("Deleted!") }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}

// ── System Products ────────────────────────────────────────────────────────

/**
 * Fetch all stock items for a given sub-department and return the array.
 * Also sets currentSpSubDeptId so the SP item-add select is always scoped correctly.
 */
async function loadStockForSubDept(subDeptId) {
  if (!subDeptId) { currentSpSubDeptId = null; return [] }
  currentSpSubDeptId = subDeptId
  const [ok, res] = await callApi("GET", `${mgmtEndpoints.stockItems}?sub_department=${subDeptId}`)
  return (ok && res.success) ? (res.data || []) : []
}

/**
 * Populate the stock-item <select> inside the system-product modal.
 * stockItems[] items have: id, product_name, hsn_code, uom, rate, warranty
 */
function buildSpStockSelect(stockItems) {
  const sel = document.getElementById("spStockItemSelect")
  sel.innerHTML = '<option value="">-- Select Item --</option>'
  stockItems.forEach(i => {
    sel.innerHTML +=
      `<option value="${i.id}"
        data-name="${i.product_name}"
        data-hsn="${i.hsn_code || ''}"
        data-uom="${i.uom || ''}"
        data-rate="${i.rate || 0}"
        data-warranty="${i.warranty || ''}">
        ${i.product_name} (${i.uom || 'pcs'})
      </option>`
  })
}

async function openAddSystemProduct(areaId, subDeptId) {
  spItems = []
  document.getElementById("spId").value          = ""
  document.getElementById("spAppAreaId").value   = areaId
  document.getElementById("spName").value        = ""
  document.getElementById("spDescription").value = ""
  document.getElementById("spSubmitBtnText").textContent = "Create System Product"
  document.getElementById("spModalTitle").innerHTML =
    '<i class="fas fa-cube" style="color:#7c3aed; margin-right:0.5rem;"></i>New System Product'

  const stockItems = await loadStockForSubDept(subDeptId)
  buildSpStockSelect(stockItems)
  renderSpItems()
  bootstrap.Modal.getOrCreateInstance(document.getElementById("systemProductModal")).show()
}

async function openEditSystemProduct(spId, areaId, subDeptId) {
  const [ok, res] = await callApi("GET", `${mgmtEndpoints.systemProducts}${spId}/`)
  if (!ok || !res.success) { alert("Failed to load system product."); return }

  const sp = res.data
  // items from the serializer: id, stock_item, product_name, hsn_code, rate, uom, quantity, resolved_name
  spItems = (sp.items || []).map(i => ({
    stock_item:   i.stock_item,
    product_name: i.resolved_name || i.product_name || "",
    hsn:          i.hsn_code  || "",
    uom:          i.uom       || "",
    qty:          parseFloat(i.quantity) || 1,
    rate:         parseFloat(i.rate)     || 0,
    warranty:     i.warranty  || "",
  }))

  document.getElementById("spId").value          = sp.id
  document.getElementById("spAppAreaId").value   = areaId
  document.getElementById("spName").value        = sp.name
  document.getElementById("spDescription").value = sp.description || ""
  document.getElementById("spSubmitBtnText").textContent = "Update System Product"
  document.getElementById("spModalTitle").innerHTML =
    '<i class="fas fa-cube" style="color:#7c3aed; margin-right:0.5rem;"></i>Edit System Product'

  const stockItems = await loadStockForSubDept(subDeptId)
  buildSpStockSelect(stockItems)
  renderSpItems()
  bootstrap.Modal.getOrCreateInstance(document.getElementById("systemProductModal")).show()
}

function addSpItem() {
  const sel = document.getElementById("spStockItemSelect")
  const opt = sel.options[sel.selectedIndex]
  if (!sel.value) { alert("Please select an item."); return }
  if (spItems.find(i => i.stock_item == sel.value)) { alert("Item already added."); return }

  spItems.push({
    stock_item:   parseInt(sel.value),
    product_name: opt.dataset.name,
    hsn:          opt.dataset.hsn      || "",
    uom:          opt.dataset.uom      || "",
    qty:          1,
    rate:         parseFloat(opt.dataset.rate) || 0,
    warranty:     opt.dataset.warranty || "",
  })
  sel.value = ""
  renderSpItems()
}

function removeSpItem(idx) {
  spItems.splice(idx, 1)
  renderSpItems()
}

function renderSpItems() {
  const tbody = document.getElementById("spItemsBody")
  if (spItems.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="8" class="text-center text-muted py-3">No items yet. Select an item above and click Add.</td></tr>'
    return
  }
  tbody.innerHTML = spItems.map((item, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong style="font-size:0.85rem;">${item.product_name}</strong></td>
      <td style="font-size:0.83rem;">${item.hsn || "—"}</td>
      <td style="font-size:0.83rem;">${item.uom || "—"}</td>
      <td>
        <input type="number" class="form-control form-control-sm" style="width:80px;"
          min="0.01" step="any" value="${item.qty}"
          onchange="spItems[${i}].qty = parseFloat(this.value) || 1">
      </td>
      <td>
        <input type="number" class="form-control form-control-sm" style="width:100px;"
          min="0" step="any" value="${item.rate}"
          onchange="spItems[${i}].rate = parseFloat(this.value) || 0">
      </td>
      <td><span style="font-size:0.8rem; color:#0369a1;">${item.warranty || "—"}</span></td>
      <td>
        <button class="btn btn-danger btn-sm" onclick="removeSpItem(${i})">
          <i class="fas fa-times"></i>
        </button>
      </td>
    </tr>`).join("")
}

async function submitSystemProduct() {
  const name   = document.getElementById("spName").value.trim()
  const areaId = document.getElementById("spAppAreaId").value
  if (!name) { alert("System Product name is required."); return }
  if (spItems.length === 0) { alert("Add at least one item to the system product."); return }

  const spId    = document.getElementById("spId").value
  const isEdit  = !!spId
  const payload = {
    application_area: parseInt(areaId),
    name,
    description: document.getElementById("spDescription").value,
    items: spItems.map(i => ({
      stock_item: i.stock_item,
      qty:        i.qty,
      rate:       i.rate,
    }))
  }

  const url    = isEdit ? `${mgmtEndpoints.systemProducts}${spId}/` : mgmtEndpoints.systemProducts
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, mgmtCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("systemProductModal")).hide()
    spItems = []
    await loadAppAreas()
    alert(`System Product ${isEdit ? "updated" : "created"}!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save"))
  }
}

async function deleteSystemProduct(spId) {
  if (!confirm("Delete this system product?")) return
  const [ok, res] = await callApi("DELETE", `${mgmtEndpoints.systemProducts}${spId}/`, {}, mgmtCsrf)
  if (ok && res.success) { await loadAppAreas(); alert("Deleted!") }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}

// ── Fixed Items ────────────────────────────────────────────────────────────

async function openFixedItemModal(areaId, subDeptId) {
  document.getElementById("fiAppAreaId").value = areaId
  document.getElementById("fiId").value        = ""
  document.getElementById("fiQty").value       = 1
  document.getElementById("fiSortOrder").value = 0

  // Load stock items for this sub-dept and build the select
  const stockItems = await loadStockForSubDept(subDeptId)
  const sel = document.getElementById("fiStockItem")
  sel.innerHTML = '<option value="">-- Select Stock Item --</option>'
  stockItems.forEach(i => {
    sel.innerHTML += `<option value="${i.id}">${i.product_name} (${i.uom || 'pcs'})</option>`
  })

  bootstrap.Modal.getOrCreateInstance(document.getElementById("fixedItemModal")).show()
}

async function submitFixedItem() {
  const areaId    = document.getElementById("fiAppAreaId").value
  const stockItem = document.getElementById("fiStockItem").value
  if (!stockItem) { alert("Please select a stock item."); return }

  const payload = {
    application_area: parseInt(areaId),
    stock_item:       parseInt(stockItem),
    default_qty:      parseFloat(document.getElementById("fiQty").value) || 1,
    sort_order:       parseInt(document.getElementById("fiSortOrder").value) || 0,
  }

  const [ok, res] = await callApi("POST", mgmtEndpoints.fixedItems, payload, mgmtCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("fixedItemModal")).hide()
    await loadAppAreas()
    alert("Fixed item added!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save"))
  }
}

async function deleteFixedItem(fiId) {
  if (!confirm("Remove this fixed item from the application area?")) return
  const [ok, res] = await callApi("DELETE", `${mgmtEndpoints.fixedItems}${fiId}/`, {}, mgmtCsrf)
  if (ok && res.success) { await loadAppAreas(); alert("Removed!") }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}
