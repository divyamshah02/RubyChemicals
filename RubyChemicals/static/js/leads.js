// leads.js — Lead Management Page
// Place at: /static/js/leads.js

let leadCsrf, leadEndpoints, leadIsAdmin
let allLeads         = []
let allSubDepts      = []
let allStockItems    = []
let currentLeadId    = null
let currentLeadSubDeptId = null   // sub-dept id of the currently viewed lead

// Quotation state
let qtItems    = []
let currentQtId = null

// SR state
let srItems    = []
let currentSRId = null

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

async function initLeads(csrfToken, endpoints, isAdmin) {
  leadCsrf      = csrfToken
  leadEndpoints = endpoints
  leadIsAdmin   = isAdmin
  await loadSubDepts()
  await loadLeads()
}

// ─────────────────────────────────────────────
// SUB-DEPARTMENTS
// ─────────────────────────────────────────────

async function loadSubDepts() {
  const [ok, res] = await callApi("GET", leadEndpoints.subDepts)
  if (ok && res.success) {
    allSubDepts = res.data || []
    populateCreateSubDeptSelect()
    populateSubDeptFilter()
  }
}

function populateCreateSubDeptSelect() {
  const sel = document.getElementById("createSubDept")
  if (!sel) return
  sel.innerHTML = '<option value="">-- Select Sub-Department --</option>'
  allSubDepts.forEach(d => {
    sel.innerHTML += `<option value="${d.id}">${d.name}</option>`
  })
}

function populateSubDeptFilter() {
  const sel = document.getElementById("subDeptFilter")
  if (!sel) return
  sel.innerHTML = '<option value="">All</option>'
  allSubDepts.forEach(d => {
    sel.innerHTML += `<option value="${d.id}">${d.name}</option>`
  })
}

// ─────────────────────────────────────────────
// LOAD LEADS
// ─────────────────────────────────────────────

async function loadLeads() {
  let params = []

  if (leadIsAdmin) {
    const userSel = document.getElementById("leadUsers")
    const sdSel   = document.getElementById("subDeptFilter")
    if (userSel && userSel.value) params.push(`user_id=${userSel.value}`)
    if (sdSel   && sdSel.value)   params.push(`sub_department=${sdSel.value}`)
  }

  const url = leadEndpoints.deptLeads + (params.length ? "?" + params.join("&") : "")
  const [ok, res] = await callApi("GET", url)
  if (ok && res.success) {
    allLeads = res.data || []
    renderLeadsTable(allLeads)
    updateKpiStats(allLeads)
    renderFollowupPanels(allLeads)
    updateSubDeptLabel()
  }
}

function applyLeadFilters() { loadLeads() }

function updateSubDeptLabel() {
  const sdSel = document.getElementById("subDeptFilter")
  const label = document.getElementById("subDeptLabel")
  if (!label) return
  if (sdSel && sdSel.value) {
    const d = allSubDepts.find(s => s.id == sdSel.value)
    label.textContent = d ? `— ${d.name}` : ""
  } else {
    label.textContent = allLeads.length > 0 && allLeads[0].sub_department_name
      ? `— ${allLeads[0].sub_department_name}` : ""
  }
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

const PARTY_LABELS = {
  dealer: "Dealer", distributor: "Distributor",
  waterproofing_applicator: "Waterproofing Applicator",
  tile_adhesive_applicator: "Tile Adhesive Applicator",
  oem: "OEM", architect: "Architect",
  interior_designer: "Interior Designer", pmc: "PMC",
  builder_project: "Builder Project", individual_project: "Individual Project",
  bungalow: "Bungalow", structural_consultant: "Structural Consultant",
  mepf_consultant: "MEPF Consultant", other: "Other",
}

const STATUS_LABELS = {
  new_lead: "New Lead", contacted: "Contacted", details_shared: "Details Shared",
  appointment_fixed: "Appointment Fixed", visit_done: "Visit Done",
  proposal_sent: "Proposal Sent", sample_to_be_done: "Sample To Be Done",
  sample_done: "Sample Done", negotiation_followup: "Negotiation / Follow-up",
  won: "Won", repeat_order: "Repeat Order", closed_lost: "Closed - Lost",
  closed_forwarded: "Closed - Forwarded", on_hold: "On Hold",
  future_potential: "Future Potential", other: "Other",
}

function statusBadge(status) {
  const label = STATUS_LABELS[status] || status
  return `<span class="status-badge status-${status}">${label}</span>`
}

function srStatusBadge(status) {
  if (status === "sent")          return '<span class="sr-badge-sent">Sent</span>'
  if (status === "partial_sent")  return '<span class="sr-badge-partial">Partial Sent</span>'
  return '<span class="sr-badge-pending">Pending</span>'
}

function formatDate(d)     { return d ? new Date(d).toLocaleDateString("en-IN")  : "—" }
function formatDateTime(d) { return d ? new Date(d).toLocaleString("en-IN")      : "—" }
function fmtCurrency(n)    { return parseFloat(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 }) }

// ─────────────────────────────────────────────
// RENDER LEADS TABLE
// ─────────────────────────────────────────────

function renderLeadsTable(leads) {
  const tbody = document.querySelector("#leadsTable tbody")
  document.getElementById("leadsCount").textContent = `${leads.length} lead${leads.length !== 1 ? "s" : ""}`

  if (leads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted py-4">No leads found. Create your first lead!</td></tr>'
    return
  }
  /* <td><span class="subdept-badge">${lead.sub_department_name || "—"}</span></td> */
  tbody.innerHTML = leads.map(lead => `
    <tr style="cursor:pointer;" onclick="viewLead(${lead.id})">
      <td><span class="lead-id-badge">${lead.lead_id || ("#" + lead.id)}</span></td>    
      <td><strong>${lead.party_name}</strong></td>
      <td><small>${PARTY_LABELS[lead.party_type] || lead.party_type}</small></td>
      <td>${lead.contact_person || "—"}</td>
      <td>${lead.mobile_number  || "—"}</td>
      <td>${lead.location       || "—"}</td>
      <td>${statusBadge(lead.lead_status)}</td>
      <td>${lead.next_followup
        ? `<span style="font-size:0.78rem; color:#92400e; font-weight:600;">${formatDateTime(lead.next_followup)}</span>`
        : '<span class="text-muted">—</span>'}</td>
      <td><span class="badge bg-primary">${lead.call_count || 0}</span></td>
      <td>${formatDate(lead.created_at)}</td>
      <td onclick="event.stopPropagation()">
        <div class="action-buttons">
          <button class="btn btn-info btn-sm" onclick="viewLead(${lead.id})" title="View">
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn btn-warning btn-sm" onclick="quickEditLead(${lead.id})" title="Edit">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-danger btn-sm" onclick="confirmDeleteLead(${lead.id})" title="Delete">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>`).join("")
}

function quickEditLead(leadId) {
  currentLeadId = leadId
  openEditLead()
}

// ─────────────────────────────────────────────
// KPI STATS
// ─────────────────────────────────────────────

function updateKpiStats(leads) {
  document.getElementById("kpiTotal").textContent     = leads.length
  document.getElementById("kpiWon").textContent       = leads.filter(l => l.lead_status === "won").length
  document.getElementById("kpiLost").textContent      = leads.filter(l => l.lead_status === "closed_lost").length
  document.getElementById("kpiContacted").textContent = leads.filter(l => l.lead_status === "contacted").length

  const now   = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  let pending = 0
  leads.forEach(l => {
    if (l.next_followup && new Date(l.next_followup) >= today) pending++
  })
  document.getElementById("kpiPending").textContent = pending
}

// ─────────────────────────────────────────────
// FOLLOW-UP PANELS
// ─────────────────────────────────────────────

function renderFollowupPanels(leads) {
  const container = document.getElementById("followupSections")
  if (!container) return

  const now      = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const todayEnd   = new Date(todayStart.getTime() + 86400000)

  const todayLeads  = leads.filter(l => l.next_followup && new Date(l.next_followup) >= todayStart && new Date(l.next_followup) < todayEnd)
  const missedLeads = leads.filter(l => l.next_followup && new Date(l.next_followup) < todayStart)

  if (todayLeads.length === 0 && missedLeads.length === 0) {
    container.innerHTML = ""
    return
  }

  const rowHtml = (l) => `
    <div class="followup-row" onclick="viewLead(${l.id})" style="cursor:pointer;">
      <div class="followup-row-info">
        <div class="party">${l.party_name}</div>
        <div class="time">${formatDateTime(l.next_followup)}</div>
        <div class="type">${l.sub_department_name || ""} &bull; ${PARTY_LABELS[l.party_type] || l.party_type}</div>
      </div>
      ${statusBadge(l.lead_status)}
    </div>`

  const todayHtml  = todayLeads.length  ? todayLeads.map(rowHtml).join("")  : '<div class="followup-empty">No follow-ups scheduled for today.</div>'
  const missedHtml = missedLeads.length ? missedLeads.map(rowHtml).join("") : '<div class="followup-empty">No missed follow-ups.</div>'

  container.innerHTML = `
    <div class="followup-panels">
      <div class="followup-panel panel-today">
        <div class="followup-panel-header">
          <span><i class="fas fa-calendar-check me-2"></i>Today's Follow-ups</span>
          <span class="badge bg-success">${todayLeads.length}</span>
        </div>
        <div class="followup-panel-body">${todayHtml}</div>
      </div>
      <div class="followup-panel panel-missed">
        <div class="followup-panel-header">
          <span><i class="fas fa-exclamation-circle me-2"></i>Missed Follow-ups</span>
          <span class="badge bg-danger">${missedLeads.length}</span>
        </div>
        <div class="followup-panel-body">${missedHtml}</div>
      </div>
    </div>`
}

// ─────────────────────────────────────────────
// FILTERS
// ─────────────────────────────────────────────

function applyFilters() {
  const q         = (document.getElementById("searchInput")?.value    || "").toLowerCase()
  const status    = document.getElementById("statusFilter")?.value    || ""
  const partyType = document.getElementById("partyTypeFilter")?.value || ""

  const filtered = allLeads.filter(l => {
    const matchQ = !q || [
      l.party_name, l.contact_person, l.mobile_number,
      l.lead_no, String(l.id), l.location, l.email
    ].some(v => v && v.toLowerCase().includes(q))
    const matchStatus    = !status    || l.lead_status === status
    const matchPartyType = !partyType || l.party_type  === partyType
    return matchQ && matchStatus && matchPartyType
  })

  renderLeadsTable(filtered)
  document.getElementById("leadsCount").textContent = `${filtered.length} lead${filtered.length !== 1 ? "s" : ""} (filtered)`
}

function clearFilters() {
  ;["searchInput", "statusFilter", "partyTypeFilter"].forEach(id => {
    const el = document.getElementById(id)
    if (el) el.value = ""
  })
  renderLeadsTable(allLeads)
  document.getElementById("leadsCount").textContent = `${allLeads.length} lead${allLeads.length !== 1 ? "s" : ""}`
}

// ─────────────────────────────────────────────
// CREATE LEAD
// Lead Type (standard/application) is NOT asked here.
// It is determined per quotation when creating one.
// ─────────────────────────────────────────────

async function createLead() {
  const subDept   = document.getElementById("createSubDept").value
  const partyType = document.getElementById("createPartyType").value
  const partyName = document.getElementById("createPartyName").value.trim()

  if (!subDept)   { alert("Please select a Sub-Department."); return }
  if (!partyType) { alert("Please select a Party Type.");     return }
  if (!partyName) { alert("Party Name is required.");         return }

  const payload = {
    sub_department:  parseInt(subDept),
    date_of_connect: document.getElementById("createDateOfConnect").value || null,
    lead_source:     document.getElementById("createLeadSource").value,
    party_type:      partyType,
    party_name:      partyName,
    location:        document.getElementById("createLocation").value,
    lead_status:     document.getElementById("createLeadStatus").value || "new_lead",
    contact_person:  document.getElementById("createContactPerson").value,
    mobile_number:   document.getElementById("createMobileNumber").value,
    email:           document.getElementById("createEmail").value,
    remarks:         document.getElementById("createRemarks").value,
  }

  const [ok, res] = await callApi("POST", leadEndpoints.deptLeads, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("createLeadModal")).hide()
    // Reset form fields
    ;["createSubDept", "createPartyType", "createLeadStatus"].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = ""
    })
    ;["createDateOfConnect", "createLeadSource", "createPartyName", "createLocation",
      "createContactPerson", "createMobileNumber", "createEmail", "createRemarks"
    ].forEach(id => { const el = document.getElementById(id); if (el) el.value = "" })
    await loadLeads()
    alert("Lead created successfully!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to create lead"))
  }
}

// ─────────────────────────────────────────────
// VIEW LEAD DETAIL
// ─────────────────────────────────────────────

async function viewLead(leadId) {
  currentLeadId = leadId
  const lead = allLeads.find(l => l.id === leadId)
  if (!lead) return

  // Store sub-dept id so quotation modal can filter stock items and app areas
  currentLeadSubDeptId = lead.sub_department
  console.log("Viewing lead", leadId, "sub-dept", currentLeadSubDeptId)
  // Pre-load stock items for this lead's sub-dept (used by quotation & SR item selects)
  await loadStockItemsForSubDept(currentLeadSubDeptId)

  document.getElementById("viewLeadIdBadge").textContent = lead.lead_no || ("#" + lead.id)

  // Parallel fetch quotations, SRs, call records
  const [[okQ, resQ], [okS, resS], [okC, resC]] = await Promise.all([
    callApi("GET", `${leadEndpoints.quotations}?lead=${leadId}`),
    callApi("GET", `${leadEndpoints.sampleReqs}?lead=${leadId}`),
    callApi("GET", `${leadEndpoints.callRecords}?lead=${leadId}`),
  ])

  const quots = (okQ && resQ.success) ? resQ.data : []
  const srs   = (okS && resS.success) ? resS.data : []
  const calls = (okC && resC.success) ? resC.data : []

  // Sort calls newest first
  const sortedCalls = [...calls].sort((a, b) => new Date(b.call_date) - new Date(a.call_date))

  // Quotations HTML
  const quotsHtml = quots.length > 0
    ? quots.map(q => `
        <div style="background:white; border:1px solid #ddd6fe; border-radius:8px; padding:0.85rem 1.1rem; margin-bottom:0.75rem;">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <strong style="color:#6d28d9;">${q.quotation_no}</strong>
              <span class="text-muted ms-2" style="font-size:0.82rem;">${formatDate(q.quotation_date)}</span>
            </div>
            <div class="d-flex gap-2 align-items-center">
              <strong style="color:#1e293b;">&#8377;${fmtCurrency(q.total_amount || 0)}</strong>
              <button class="btn btn-sm btn-warning" onclick="downloadQuotation(${q.id})" style="font-size:0.78rem;">
                <i class="fas fa-download me-1"></i>Download
              </button>
              <button class="btn btn-sm btn-warning" onclick="openEditQuotation(${q.id})" style="font-size:0.78rem;">
                <i class="fas fa-edit me-1"></i>Edit
              </button>
            </div>
          </div>
          ${q.notes ? `<small class="text-muted">${q.notes}</small>` : ""}
          <div style="margin-top:0.5rem; font-size:0.8rem; color:#475569;">
            ${(q.items || []).filter(i => i.is_active !== false).map(i => `${i.product_name} &times; ${i.quantity} ${i.uom || ""}`).join(", ") || "No items"}
          </div>
        </div>`).join("")
    : '<p class="text-muted" style="font-size:0.85rem;">No quotation yet. Click "Quotation" below to create one.</p>'

  // Sample Requisites HTML
  const srsHtml = srs.length > 0
    ? srs.map(s => `
        <div style="background:white; border:1px solid #bbf7d0; border-radius:8px; padding:0.85rem 1.1rem; margin-bottom:0.75rem;">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <strong style="color:#065f46;">${s.sr_no}</strong>
              <span class="text-muted ms-2" style="font-size:0.82rem;">${formatDate(s.sr_date)}</span>
              ${srStatusBadge(s.status)}
            </div>
            <button class="btn btn-sm btn-warning" onclick="openEditSR(${s.id})" style="font-size:0.78rem;">
              <i class="fas fa-edit me-1"></i>Edit
            </button>
          </div>
          <div style="margin-top:0.5rem; font-size:0.8rem; color:#475569;">
            ${(s.items || []).map(i => `${i.product_name} &times; ${i.quantity} ${i.uom || ""}`).join(", ") || "No items"}
          </div>
        </div>`).join("")
    : '<p class="text-muted" style="font-size:0.85rem;">No sample requisite yet. Click "Sample Req." below to create one.</p>'

  // Call records HTML
  const callsHtml = sortedCalls.length > 0
    ? `<div class="call-timeline">${sortedCalls.map(c => `
        <div class="call-item">
          <div class="call-meta">
            <span class="call-date-badge"><i class="fas fa-calendar-alt me-1"></i>${formatDate(c.call_date)}</span>
            ${c.lead_status ? statusBadge(c.lead_status) : ""}
            ${c.next_followup
              ? `<span class="followup-alert" style="display:inline-block; padding:0.15rem 0.5rem; margin:0;">
                  <i class="fas fa-bell me-1"></i>Follow-up: ${formatDateTime(c.next_followup)}
                 </span>`
              : ""}
            <div class="d-flex gap-1 ms-auto">
              <button class="btn btn-sm btn-warning" onclick="openEditCallRecord(${c.id})" title="Edit" style="padding:0.2rem 0.5rem; font-size:0.75rem;">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-danger" onclick="deleteCallRecord(${c.id})" title="Delete" style="padding:0.2rem 0.5rem; font-size:0.75rem;">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          ${c.contact_number ? `<small class="text-muted"><i class="fas fa-phone me-1"></i>${c.contact_number}</small><br>` : ""}
          <p style="color:#374151; margin:0.3rem 0 0;">${c.briefing}</p>
          ${c.forwarded_to ? `<small style="color:#9d174d;"><i class="fas fa-share me-1"></i>Forwarded to: ${c.forwarded_to}</small>` : ""}
        </div>`).join("")}</div>`
    : '<p class="text-muted" style="font-size:0.85rem;">No call records yet. Click "Add Call Record" below.</p>'

  document.getElementById("leadDetailContent").innerHTML = `
    <!-- Lead Info -->
    <div style="background:#f0f9ff; border:1px solid #bfdbfe; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
      <div class="row">
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Date of Connect</span><br>${formatDate(lead.date_of_connect)}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Lead Source</span><br>${lead.lead_source || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Party Type</span><br>${PARTY_LABELS[lead.party_type] || lead.party_type}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Party Name</span><br><strong>${lead.party_name}</strong></div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Location</span><br>${lead.location || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Contact Person</span><br>${lead.contact_person || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Mobile</span><br>${lead.mobile_number || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Email</span><br>${lead.email || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Status</span><br>${statusBadge(lead.lead_status)}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Sub-Department</span><br><span class="subdept-badge">${lead.sub_department_name || "—"}</span></div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Created By</span><br>${lead.created_by_name || "—"}</div>
        <div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Created At</span><br>${formatDateTime(lead.created_at)}</div>
        ${lead.forwarded_to ? `<div class="col-md-3 mb-2"><span class="text-muted" style="font-size:0.8rem;">Forwarded To</span><br><strong>${lead.forwarded_to}</strong></div>` : ""}
      </div>
      ${lead.remarks ? `<div class="mt-2"><span class="text-muted" style="font-size:0.8rem;">Remarks</span><br><p style="color:#374151; margin-top:0.25rem;">${lead.remarks}</p></div>` : ""}
    </div>

    <!-- Quotations -->
    <div style="background:#f5f3ff; border:1px solid #ddd6fe; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
      <h6 style="color:#6d28d9; font-weight:700; margin-bottom:1rem;"><i class="fas fa-file-invoice me-2"></i>Quotations (${quots.length})</h6>
      ${quotsHtml}
    </div>

    <!-- Sample Requisites -->
    <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
      <h6 style="color:#065f46; font-weight:700; margin-bottom:1rem;"><i class="fas fa-vial me-2"></i>Sample Requisites (${srs.length})</h6>
      ${srsHtml}
    </div>

    <!-- Call Records -->
    <h6 style="color:#1e40af; font-weight:700; margin-bottom:1rem;">
      <i class="fas fa-phone-alt me-2"></i>Call Records (${calls.length})
    </h6>
    ${callsHtml}`

  bootstrap.Modal.getOrCreateInstance(document.getElementById("viewLeadModal")).show()
}

// ─────────────────────────────────────────────
// STOCK ITEMS — load for a given sub-dept
// ─────────────────────────────────────────────

async function loadStockItemsForSubDept(subDeptId) {
  if (!subDeptId) { allStockItems = []; return }
  const [ok, res] = await callApi("GET", `${leadEndpoints.stockItems}?sub_department=${subDeptId}`)
  allStockItems = (ok && res.success) ? res.data : []
}

function buildStockItemSelect(selectId) {
  const sel = document.getElementById(selectId)
  if (!sel) return
  sel.innerHTML = '<option value="">-- Select Item --</option>'
  allStockItems.forEach(item => {
    const hsn = item.hsn_code || ""
    sel.innerHTML += `<option value="${item.id}"
      data-name="${item.product_name}"
      data-hsn="${hsn}"
      data-uom="${item.uom || ''}"
      data-rate="${item.rate || 0}"
      data-warranty="${item.warranty || ''}"
    >${item.product_name} (${item.uom || 'pcs'})${item.warranty ? ' [' + item.warranty + ']' : ''}</option>`
  })
}

// ─────────────────────────────────────────────
// QUOTATION
//
// A single quotation can contain:
//   - Items loaded from one or more Application Areas
//     (each area has system products with items, plus fixed items)
//   - Items added manually from the sub-dept stock list
//
// All items are fully editable (qty, rate, hsn, uom, warranty).
// Lead type (standard/application) is NOT stored on the lead itself —
// a single quotation simply holds both types of items together.
// ─────────────────────────────────────────────

async function openQuotationModal() {
  if (!currentLeadId) return
  currentQtId = null
  qtItems = []

  // Populate app area dropdown filtered to this lead's sub-dept
  await buildQtAppAreaSelect()

  // Check for an existing quotation on this lead
  const [ok, res] = await callApi("GET", `${leadEndpoints.quotations}?lead=${currentLeadId}`)
  if (ok && res.success && res.data.length > 0) {
    const existing = res.data[0]
    currentQtId = existing.id
    document.getElementById("quotationNumberBadge").textContent = existing.quotation_no
    document.getElementById("qtDate").value  = existing.quotation_date || ""
    document.getElementById("qtNotes").value = existing.notes || ""
    document.getElementById("qtSubmitBtnText").textContent = "Update Quotation"
    document.getElementById("qtExistingInfo").textContent  = `Editing: ${existing.quotation_no}`

    ;(existing.items || []).filter(i => i.is_active !== false).forEach(item => {
      qtItems.push({
        stock_item:    item.stock_item   || null,
        product_name:  item.product_name || "",
        hsn:           item.hsn_code     || "",
        uom:           item.uom          || "",
        qty:           parseFloat(item.quantity) || 1,
        rate:          parseFloat(item.rate)     || 0,
        warranty:      item.warranty     || "",
      })
    })
  } else {
    document.getElementById("quotationNumberBadge").textContent = "(New)"
    document.getElementById("qtDate").value  = new Date().toISOString().split("T")[0]
    document.getElementById("qtNotes").value = ""
    document.getElementById("qtSubmitBtnText").textContent = "Create Quotation"
    document.getElementById("qtExistingInfo").textContent  = ""
  }

  document.getElementById("qtAddedAreas").innerHTML = ""
  buildStockItemSelect("qtStockItemSelect")
  renderQtItems()

  bootstrap.Modal.getInstance(document.getElementById("viewLeadModal")).hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("quotationModal")).show(), 300)
}

async function downloadQuotation(qtId) {
  location.href = `${leadEndpoints.generateQuotations}?quotation_id=${qtId}`
  // const [ok, res] = await callApi("GET", `${leadEndpoints.generateQuotations}?quotation_id=${qtId}`)
  // if (!ok || !res.success) {
  //   alert("Failed to generate quotation PDF.")
  //   return
  // }
  // Handle the PDF download response
}

async function openEditQuotation(qtId) {
  currentQtId = qtId
  qtItems = []

  const [ok, res] = await callApi("GET", `${leadEndpoints.quotations}${qtId}/`)
  if (!ok || !res.success) { alert("Failed to load quotation."); return }

  const q = res.data
  document.getElementById("quotationNumberBadge").textContent = q.quotation_no
  document.getElementById("qtDate").value  = q.quotation_date || ""
  document.getElementById("qtNotes").value = q.notes || ""
  document.getElementById("qtSubmitBtnText").textContent = "Update Quotation"
  document.getElementById("qtExistingInfo").textContent  = `Editing: ${q.quotation_no}`

  ;(q.items || []).filter(i => i.is_active !== false).forEach(item => {
    qtItems.push({
      stock_item:   item.stock_item   || null,
      product_name: item.product_name || "",
      hsn:          item.hsn_code     || "",
      uom:          item.uom          || "",
      qty:          parseFloat(item.quantity) || 0,
      rate:         parseFloat(item.rate)     || 0,
      warranty:     item.warranty     || "",
      _from_area:   item.application_area,
    })
  })

  await buildQtAppAreaSelect()
  document.getElementById("qtAddedAreas").innerHTML = ""
  buildStockItemSelect("qtStockItemSelect")
  renderQtItems()

  bootstrap.Modal.getInstance(document.getElementById("viewLeadModal")).hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("quotationModal")).show(), 300)
}

// Populate the application area dropdown for the current lead's sub-dept
async function buildQtAppAreaSelect() {
  const sel = document.getElementById("qtAppAreaSelect")
  if (!sel) return
  sel.innerHTML = '<option value="">-- Select Application Area --</option>'
  if (!currentLeadSubDeptId) return

  const [ok, res] = await callApi("GET", `${leadEndpoints.appAreas}?sub_department=${currentLeadSubDeptId}`)
  if (ok && res.success) {
    res.data.forEach(a => {
      sel.innerHTML += `<option value="${a.id}" data-name="${a.name}">${a.name}</option>`
    })
  }
}

// Load all items from a selected application area into qtItems
async function addQtAppArea() {
  const sel = document.getElementById("qtAppAreaSelect")
  if (!sel.value) { alert("Please select an application area."); return }

  const areaId   = sel.value
  const areaName = sel.options[sel.selectedIndex].dataset.name

  // Fetch the full area detail (system_products + fixed_items nested in)
  const [ok, res] = await callApi("GET", `${leadEndpoints.appAreas}${areaId}/`)
  if (!ok || !res.success) { alert("Failed to load application area data."); return }

  const area = res.data
  let addedCount = 0

  // --- System product items ---
  ;(area.system_products || []).forEach(sp => {
    ;(sp.items || []).filter(i => i.is_active !== false).forEach(i => {
      const name = i.resolved_name || i.product_name || ""
      if (!name) return
      // Skip if a stock_item with this id was already added
      if (i.stock_item && qtItems.find(x => x.stock_item == i.stock_item)) return
      qtItems.push({
        stock_item:    i.stock_item || null,
        product_name:  name,
        hsn:           i.hsn_code  || "",
        uom:           i.uom       || "",
        qty:           parseFloat(i.quantity) || 1,
        rate:          parseFloat(i.rate)     || 0,
        warranty:      i.warranty  || "",
        _from_area:    areaName,
      })
      addedCount++
    })
  })

  // --- Fixed items ---
  ;(area.fixed_items || []).filter(fi => fi.is_active !== false).forEach(fi => {
    const name = fi.resolved_name || fi.product_name || ""
    if (!name) return
    if (fi.stock_item && qtItems.find(x => x.stock_item == fi.stock_item)) return
    qtItems.push({
      stock_item:   fi.stock_item || null,
      product_name: name,
      hsn:          fi.hsn_code  || "",
      uom:          fi.uom       || "",
      qty:          parseFloat(fi.quantity) || 1,
      rate:         parseFloat(fi.rate)     || 0,
      warranty:     "",
      _from_area:   areaName,
    })
    addedCount++
  })

  // Show a tag for the loaded area
  document.getElementById("qtAddedAreas").innerHTML +=
    `<span class="area-tag">${areaName} <span style="opacity:0.7;">(+${addedCount})</span></span>`

  sel.value = ""
  renderQtItems()
}

// Add a single stock item manually
function addQtItem() {
  const sel = document.getElementById("qtStockItemSelect")
  const opt = sel.options[sel.selectedIndex]
  if (!sel.value) { alert("Please select an item."); return }
  if (qtItems.find(i => i.stock_item == sel.value)) { alert("Item already added."); return }

  qtItems.push({
    stock_item:   parseInt(sel.value),
    product_name: opt.dataset.name,
    hsn:          opt.dataset.hsn      || "",
    uom:          opt.dataset.uom      || "",
    qty:          1,
    rate:         parseFloat(opt.dataset.rate) || 0,
    warranty:     opt.dataset.warranty || "",
  })
  sel.value = ""
  renderQtItems()
}

function removeQtItem(idx) {
  qtItems.splice(idx, 1)
  renderQtItems()
}

function renderQtItems() {
  const tbody = document.getElementById("qtItemsBody")
  if (qtItems.length === 0) {
    tbody.innerHTML = `<tr id="qtEmptyRow">
      <td colspan="9" class="text-center text-muted py-3">
        No items added yet. Use the sections above to add items.
      </td>
    </tr>`
    document.getElementById("qtTotal").textContent = "0.00"
    return
  }

  let total = 0
  let lastArea = "";
  tbody.innerHTML = qtItems.map((item, i) => {
    const amount = (parseFloat(item.qty) || 0) * (parseFloat(item.rate) || 0);
    total += amount;

    let html = "";

    // Only print area heading when it changes
    if (item._from_area !== lastArea) {
      lastArea = item._from_area;

      html += `
        <tr class="table-light">
          <td colspan="9">
            <span class="area-tag">${item._from_area}</span>
          </td>
        </tr>
      `;
    }

    html += `
      <tr>
        <td>${i + 1}</td>
        <td>${item.product_name}</td>
        <td>
          <input type="text" class="form-control form-control-sm" style="width:85px;"
            value="${item.hsn || ''}"
            onchange="qtItems[${i}].hsn = this.value">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm" style="width:70px;"
            value="${item.uom || ''}"
            onchange="qtItems[${i}].uom = this.value">
        </td>
        <td>
          <input type="number" class="form-control form-control-sm" style="width:80px;"
            min="0.001" step="any" value="${item.qty}"
            onchange="qtItems[${i}].qty = parseFloat(this.value) || 0; renderQtItems()">
        </td>
        <td>
          <input type="number" class="form-control form-control-sm" style="width:100px;"
            min="0" step="any" value="${item.rate}"
            onchange="qtItems[${i}].rate = parseFloat(this.value) || 0; renderQtItems()">
        </td>
        <td style="font-weight:600; white-space:nowrap;">&#8377;${fmtCurrency(amount)}</td>
        <td>
          <input type="text" class="form-control form-control-sm" style="width:90px;"
            placeholder="e.g. 1 Yr" value="${item.warranty || ''}"
            onchange="qtItems[${i}].warranty = this.value">
        </td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="removeQtItem(${i})">
            <i class="fas fa-times"></i>
          </button>
        </td>
      </tr>
    `;

    return html;
  }).join("");




  // tbody.innerHTML = qtItems.map((item, i) => {
  //   const amount = (parseFloat(item.qty) || 0) * (parseFloat(item.rate) || 0)
  //   total += amount
  //   const areaTag = item._from_area
  //     ? `<span class="area-tag ms-1">${item._from_area}</span>`
  //     : ""
  //   return `<tr><td><span class="area-tag ms-1">${item._from_area}</span></td></tr>`+`
  //     <tr>
  //       <td>${i + 1}</td>
  //       <td>${item.product_name}${areaTag}</td>
  //       <td>
  //         <input type="text" class="form-control form-control-sm" style="width:85px;"
  //           value="${item.hsn || ''}"
  //           onchange="qtItems[${i}].hsn = this.value">
  //       </td>
  //       <td>
  //         <input type="text" class="form-control form-control-sm" style="width:70px;"
  //           value="${item.uom || ''}"
  //           onchange="qtItems[${i}].uom = this.value">
  //       </td>
  //       <td>
  //         <input type="number" class="form-control form-control-sm" style="width:80px;"
  //           min="0.001" step="any" value="${item.qty}"
  //           onchange="qtItems[${i}].qty = parseFloat(this.value) || 1; renderQtItems()">
  //       </td>
  //       <td>
  //         <input type="number" class="form-control form-control-sm" style="width:100px;"
  //           min="0" step="any" value="${item.rate}"
  //           onchange="qtItems[${i}].rate = parseFloat(this.value) || 0; renderQtItems()">
  //       </td>
  //       <td style="font-weight:600; white-space:nowrap;">&#8377;${fmtCurrency(amount)}</td>
  //       <td>
  //         <input type="text" class="form-control form-control-sm" style="width:90px;"
  //           placeholder="e.g. 1 Yr" value="${item.warranty || ''}"
  //           onchange="qtItems[${i}].warranty = this.value">
  //       </td>
  //       <td>
  //         <button class="btn btn-danger btn-sm" onclick="removeQtItem(${i})">
  //           <i class="fas fa-times"></i>
  //         </button>
  //       </td>
  //     </tr>`
  // }).join("")

  document.getElementById("qtTotal").textContent = fmtCurrency(total)
}

async function submitQuotation() {
  if (!currentLeadId) return
  if (qtItems.length === 0) { alert("Add at least one item to the quotation."); return }

  const payload = {
    lead:           currentLeadId,
    quotation_date: document.getElementById("qtDate").value || new Date().toISOString().split("T")[0],
    notes:          document.getElementById("qtNotes").value,
    items: qtItems.map(i => ({
      stock_item:   i.stock_item || null,
      product_name: i.stock_item ? "" : (i.product_name || ""),
      hsn_code:     i.hsn      || "",
      quantity:     i.qty,
      rate:         i.rate,
      uom:          i.uom      || "",
      warranty:     i.warranty || "",
      application_area: i._from_area || null,
    }))
  }

  const isEdit = !!currentQtId
  const url    = isEdit ? `${leadEndpoints.quotations}${currentQtId}/` : leadEndpoints.quotations
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("quotationModal")).hide()
    qtItems = []; currentQtId = null
    await viewLead(currentLeadId)
    alert(`Quotation ${isEdit ? "updated" : "created"} successfully!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save quotation"))
  }
}

// ─────────────────────────────────────────────
// SAMPLE REQUISITE
// ─────────────────────────────────────────────

async function openSRModal() {
  if (!currentLeadId) return
  currentSRId = null
  srItems = []

  const [ok, res] = await callApi("GET", `${leadEndpoints.sampleReqs}?lead=${currentLeadId}`)
  if (ok && res.success && res.data.length > 0) {
    const existing = res.data[0]
    currentSRId = existing.id
    document.getElementById("srNumberBadge").textContent        = existing.sr_no
    document.getElementById("srDate").value                     = existing.sr_date || ""
    document.getElementById("srContactPerson").value            = existing.contact_name || ""
    document.getElementById("srContactNumber").value            = existing.contact_number || ""
    document.getElementById("srAddress").value                  = existing.delivery_address || ""
    document.getElementById("srNotes").value                    = existing.notes || ""
    document.getElementById("srSubmitBtnText").textContent      = "Update SR"
    document.getElementById("srExistingInfo").textContent       = `Editing: ${existing.sr_no}`
    document.getElementById("srCurrentStatus").innerHTML        = srStatusBadge(existing.status)
    document.getElementById("srFactorySection").style.display   = "block"
    ;(existing.items || []).forEach(item => {
      srItems.push({
        stock_item:      item.stock_item,
        product_name:    item.product_name,
        hsn:             item.hsn_code || "",
        uom:             item.uom      || "",
        qty_requested:   item.quantity,
        qty_sent:        item.qty_sent  || 0,
        dispatch_status: item.status    || "pending",
        warranty:        item.warranty  || ""
      })
    })
  } else {
    document.getElementById("srNumberBadge").textContent       = "(New)"
    document.getElementById("srDate").value                    = new Date().toISOString().split("T")[0]
    document.getElementById("srContactPerson").value           = ""
    document.getElementById("srContactNumber").value           = ""
    document.getElementById("srAddress").value                 = ""
    document.getElementById("srNotes").value                   = ""
    document.getElementById("srSubmitBtnText").textContent     = "Create SR"
    document.getElementById("srExistingInfo").textContent      = ""
    document.getElementById("srFactorySection").style.display  = "none"
  }

  buildStockItemSelect("srStockItemSelect")
  renderSrItems()

  bootstrap.Modal.getInstance(document.getElementById("viewLeadModal")).hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("srModal")).show(), 300)
}

async function openEditSR(srId) {
  currentSRId = srId
  srItems = []

  const [ok, res] = await callApi("GET", `${leadEndpoints.sampleReqs}${srId}/`)
  if (!ok || !res.success) { alert("Failed to load SR."); return }

  const s = res.data
  document.getElementById("srNumberBadge").textContent      = s.sr_no
  document.getElementById("srDate").value                   = s.sr_date || ""
  document.getElementById("srContactPerson").value          = s.contact_name || ""
  document.getElementById("srContactNumber").value          = s.contact_number || ""
  document.getElementById("srAddress").value                = s.delivery_address || ""
  document.getElementById("srNotes").value                  = s.notes || ""
  document.getElementById("srSubmitBtnText").textContent    = "Update SR"
  document.getElementById("srExistingInfo").textContent     = `Editing: ${s.sr_no}`
  document.getElementById("srCurrentStatus").innerHTML      = srStatusBadge(s.status)
  document.getElementById("srFactorySection").style.display = "block"

  ;(s.items || []).forEach(item => {
    srItems.push({
      stock_item:      item.stock_item,
      product_name:    item.product_name,
      hsn:             item.hsn_code || "",
      uom:             item.uom      || "",
      qty_requested:   item.quantity,
      qty_sent:        item.qty_sent  || 0,
      dispatch_status: item.status    || "pending",
      warranty:        item.warranty  || ""
    })
  })

  buildStockItemSelect("srStockItemSelect")
  renderSrItems()

  bootstrap.Modal.getInstance(document.getElementById("viewLeadModal")).hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("srModal")).show(), 300)
}

function addSrItem() {
  const sel = document.getElementById("srStockItemSelect")
  const opt = sel.options[sel.selectedIndex]
  if (!sel.value) { alert("Please select an item."); return }
  if (srItems.find(i => i.stock_item == sel.value)) { alert("Item already added."); return }

  srItems.push({
    stock_item:      parseInt(sel.value),
    product_name:    opt.dataset.name,
    hsn:             opt.dataset.hsn      || "",
    uom:             opt.dataset.uom      || "",
    qty_requested:   1,
    qty_sent:        0,
    dispatch_status: "pending",
    warranty:        opt.dataset.warranty || ""
  })
  sel.value = ""
  renderSrItems()
}

function removeSrItem(idx) {
  srItems.splice(idx, 1)
  renderSrItems()
}

function renderSrItems() {
  const tbody = document.getElementById("srItemsBody")
  if (srItems.length === 0) {
    tbody.innerHTML = '<tr id="srEmptyRow"><td colspan="9" class="text-center text-muted py-3">No items added yet</td></tr>'
    return
  }

  const isEdit = !!currentSRId
  tbody.innerHTML = srItems.map((item, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${item.product_name}</td>
      <td>${item.hsn || "—"}</td>
      <td>${item.uom || "—"}</td>
      <td>
        <input type="number" class="form-control form-control-sm" style="width:90px;" min="1" step="any" value="${item.qty_requested}"
          onchange="srItems[${i}].qty_requested = parseFloat(this.value) || 1; renderSrItems()">
      </td>
      <td>
        ${isEdit
          ? `<input type="number" class="form-control form-control-sm" style="width:90px;" min="0" step="any" value="${item.qty_sent}"
               onchange="srItems[${i}].qty_sent = parseFloat(this.value) || 0">`
          : '<span class="text-muted">—</span>'}
      </td>
      <td>${srStatusBadge(item.dispatch_status)}</td>
      <td><span style="font-size:0.8rem; color:#0369a1;">${item.warranty || "—"}</span></td>
      <td><button class="btn btn-danger btn-sm" onclick="removeSrItem(${i})"><i class="fas fa-times"></i></button></td>
    </tr>`).join("")
}

async function submitSR() {
  if (!currentLeadId) return
  if (srItems.length === 0) { alert("Add at least one item to the SR."); return }

  const payload = {
    lead:             currentLeadId,
    sr_date:          document.getElementById("srDate").value || new Date().toISOString().split("T")[0],
    contact_name:     document.getElementById("srContactPerson").value,
    contact_number:   document.getElementById("srContactNumber").value,
    delivery_address: document.getElementById("srAddress").value,
    notes:            document.getElementById("srNotes").value,
    items: srItems.map(i => ({
      stock_item: i.stock_item,
      quantity:   i.qty_requested,
      uom:        i.uom     || "",
      qty_sent:   i.qty_sent || 0
    }))
  }

  const isEdit = !!currentSRId
  const url    = isEdit ? `${leadEndpoints.sampleReqs}${currentSRId}/` : leadEndpoints.sampleReqs
  const method = isEdit ? "PATCH" : "POST"

  const [ok, res] = await callApi(method, url, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("srModal")).hide()
    srItems = []; currentSRId = null
    await viewLead(currentLeadId)
    alert(`Sample Requisite ${isEdit ? "updated" : "created"} successfully!`)
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to save SR"))
  }
}

async function markSRSent(sentStatus) {
  if (!currentSRId) return
  const [ok, res] = await callApi("POST", `${leadEndpoints.sampleReqs}${currentSRId}/mark-sent/`, { status: sentStatus }, leadCsrf)
  if (ok && res.success) {
    document.getElementById("srCurrentStatus").innerHTML = srStatusBadge(sentStatus)
    alert("SR status updated!")
  } else {
    alert("Error: " + (res.error || "Failed to update SR status"))
  }
}

// ─────────────────────────────────────────────
// EDIT LEAD
// ─────────────────────────────────────────────

async function openEditLead() {
  if (!currentLeadId) return
  const lead = allLeads.find(l => l.id === currentLeadId)
  if (!lead) return

  document.getElementById("editDateOfConnect").value = lead.date_of_connect || ""
  document.getElementById("editLeadSource").value    = lead.lead_source     || ""
  document.getElementById("editPartyType").value     = lead.party_type      || ""
  document.getElementById("editPartyName").value     = lead.party_name      || ""
  document.getElementById("editLocation").value      = lead.location        || ""
  document.getElementById("editLeadStatus").value    = lead.lead_status     || "new_lead"
  document.getElementById("editContactPerson").value = lead.contact_person  || ""
  document.getElementById("editMobileNumber").value  = lead.mobile_number   || ""
  document.getElementById("editEmail").value         = lead.email           || ""
  document.getElementById("editRemarks").value       = lead.remarks         || ""
  document.getElementById("editForwardedTo").value   = lead.forwarded_to    || ""

  const showFwd = lead.lead_status === "closed_forwarded"
  document.getElementById("editForwardedToGroup").style.display = showFwd ? "block" : "none"
  document.getElementById("editLeadStatus").onchange = function () {
    document.getElementById("editForwardedToGroup").style.display =
      this.value === "closed_forwarded" ? "block" : "none"
  }

  const viewModal = bootstrap.Modal.getInstance(document.getElementById("viewLeadModal"))
  if (viewModal) viewModal.hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("editLeadModal")).show(), 300)
}

async function submitEditLead() {
  if (!currentLeadId) return
  const partyType = document.getElementById("editPartyType").value
  const partyName = document.getElementById("editPartyName").value.trim()
  if (!partyType || !partyName) { alert("Party Type and Party Name are required."); return }

  const status = document.getElementById("editLeadStatus").value
  const payload = {
    date_of_connect: document.getElementById("editDateOfConnect").value || null,
    lead_source:     document.getElementById("editLeadSource").value,
    party_type:      partyType,
    party_name:      partyName,
    location:        document.getElementById("editLocation").value,
    lead_status:     status,
    contact_person:  document.getElementById("editContactPerson").value,
    mobile_number:   document.getElementById("editMobileNumber").value,
    email:           document.getElementById("editEmail").value,
    remarks:         document.getElementById("editRemarks").value,
    forwarded_to:    status === "closed_forwarded" ? document.getElementById("editForwardedTo").value : "",
  }

  const [ok, res] = await callApi("PATCH", `${leadEndpoints.deptLeads}${currentLeadId}/`, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("editLeadModal")).hide()
    currentLeadId = null
    await loadLeads()
    alert("Lead updated successfully!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to update lead"))
  }
}

// ─────────────────────────────────────────────
// DELETE LEAD
// ─────────────────────────────────────────────

async function deleteLead() {
  if (!currentLeadId) return
  confirmDeleteLead(currentLeadId)
}

async function confirmDeleteLead(leadId) {
  if (!confirm("Are you sure you want to delete this lead? This action cannot be undone.")) return
  const [ok, res] = await callApi("DELETE", `${leadEndpoints.deptLeads}${leadId}/`, {}, leadCsrf)
  if (ok && res.success) {
    ;["viewLeadModal", "editLeadModal"].forEach(id => {
      const m = bootstrap.Modal.getInstance(document.getElementById(id))
      if (m) m.hide()
    })
    currentLeadId = null
    await loadLeads()
    alert("Lead deleted successfully!")
  } else {
    alert("Error: " + (res.error || "Failed to delete lead"))
  }
}

// ─────────────────────────────────────────────
// CALL RECORDS
// ─────────────────────────────────────────────

function openAddCallRecord() {
  if (!currentLeadId) return
  document.getElementById("callDate").value            = new Date().toISOString().split("T")[0]
  document.getElementById("callContactNumber").value   = ""
  document.getElementById("callBriefing").value        = ""
  document.getElementById("callLeadStatus").value      = ""
  document.getElementById("callNextFollowup").value    = ""
  document.getElementById("callForwardedTo").value     = ""
  document.getElementById("forwardedToGroup").style.display  = "none"
  document.getElementById("nextFollowupGroup").style.display = "block"
  bootstrap.Modal.getOrCreateInstance(document.getElementById("addCallRecordModal")).show()
}

function toggleForwardedTo() {
  const status = document.getElementById("callLeadStatus").value
  document.getElementById("forwardedToGroup").style.display = status === "closed_forwarded" ? "block" : "none"
  if (["closed_forwarded", "closed_lost"].includes(status)) {
    document.getElementById("nextFollowupGroup").style.display = "none"
    document.getElementById("callNextFollowup").value = ""
  } else {
    document.getElementById("nextFollowupGroup").style.display = "block"
  }
}

async function submitCallRecord() {
  const callDate = document.getElementById("callDate").value
  const briefing = document.getElementById("callBriefing").value.trim()
  const status   = document.getElementById("callLeadStatus").value
  if (!callDate || !briefing) { alert("Call Date and Briefing are required."); return }
  if (status === "closed_forwarded" && !document.getElementById("callForwardedTo").value.trim()) {
    alert("Please specify who this lead is forwarded to."); return
  }

  const payload = {
    lead:           currentLeadId,
    call_date:      callDate,
    contact_number: document.getElementById("callContactNumber").value.trim(),
    briefing:       briefing,
    lead_status:    status || null,
    next_followup:  document.getElementById("callNextFollowup").value || null,
    forwarded_to:   document.getElementById("callForwardedTo").value.trim(),
  }

  const [ok, res] = await callApi("POST", leadEndpoints.callRecords, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("addCallRecordModal")).hide()
    await viewLead(currentLeadId)
    await loadLeads()
    alert("Call record added successfully!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to add call record"))
  }
}

async function deleteCallRecord(recordId) {
  if (!confirm("Delete this call record?")) return
  const [ok, res] = await callApi("DELETE", `${leadEndpoints.callRecords}${recordId}/`, {}, leadCsrf)
  if (ok && res.success) { await viewLead(currentLeadId); await loadLeads() }
  else { alert("Error: " + (res.error || "Failed to delete")) }
}

async function openEditCallRecord(recordId) {
  const [ok, res] = await callApi("GET", `${leadEndpoints.callRecords}${recordId}/`)
  if (!ok || !res.success) { alert("Failed to load call record."); return }

  const c = res.data
  document.getElementById("editCallRecordId").value      = c.id
  document.getElementById("editCallDate").value          = c.call_date       || ""
  document.getElementById("editCallContactNumber").value = c.contact_number  || ""
  document.getElementById("editCallBriefing").value      = c.briefing        || ""
  document.getElementById("editCallLeadStatus").value    = c.lead_status     || ""
  document.getElementById("editCallNextFollowup").value  = c.next_followup   ? c.next_followup.slice(0, 16) : ""
  document.getElementById("editCallForwardedTo").value   = c.forwarded_to    || ""
  toggleEditForwardedTo()

  const dm = bootstrap.Modal.getInstance(document.getElementById("viewLeadModal"))
  if (dm) dm.hide()
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("editCallRecordModal")).show(), 300)
}

function toggleEditForwardedTo() {
  const status = document.getElementById("editCallLeadStatus").value
  document.getElementById("editForwardedToGroup").style.display = status === "closed_forwarded" ? "block" : "none"
  if (["closed_forwarded", "closed_lost"].includes(status)) {
    document.getElementById("editNextFollowupGroup").style.display = "none"
    document.getElementById("editCallNextFollowup").value = ""
  } else {
    document.getElementById("editNextFollowupGroup").style.display = "block"
  }
}

async function submitEditCallRecord() {
  const recordId = document.getElementById("editCallRecordId").value
  const callDate = document.getElementById("editCallDate").value
  const briefing = document.getElementById("editCallBriefing").value.trim()
  const status   = document.getElementById("editCallLeadStatus").value
  if (!callDate || !briefing) { alert("Call Date and Briefing are required."); return }
  if (status === "closed_forwarded" && !document.getElementById("editCallForwardedTo").value.trim()) {
    alert("Please specify who this lead is forwarded to."); return
  }

  const payload = {
    call_date:      callDate,
    contact_number: document.getElementById("editCallContactNumber").value.trim(),
    briefing:       briefing,
    lead_status:    status || null,
    next_followup:  document.getElementById("editCallNextFollowup").value || null,
    forwarded_to:   document.getElementById("editCallForwardedTo").value.trim(),
  }

  const [ok, res] = await callApi("PUT", `${leadEndpoints.callRecords}${recordId}/`, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("editCallRecordModal")).hide()
    await viewLead(currentLeadId)
    await loadLeads()
    alert("Call record updated successfully!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to update call record"))
  }
}

// ─────────────────────────────────────────────
// TRANSFER LEAD
// ─────────────────────────────────────────────

function openLeadTransfer() {
  setTimeout(() => bootstrap.Modal.getOrCreateInstance(document.getElementById("transferLeadModal")).show(), 300)
}

async function submitTransferLead() {
  if (!currentLeadId) return
  const newOwner = document.getElementById("allLeadUsers").value
  if (!newOwner) { alert("Please select a user to transfer the lead to."); return }

  const [ok, res] = await callApi("POST", leadEndpoints.transferLeads, { lead_id: currentLeadId, new_owner_id: newOwner }, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("transferLeadModal")).hide()
    await loadLeads()
    alert("Lead transferred successfully!")
  } else {
    alert("Error: " + (res.error ? JSON.stringify(res.error) : "Failed to transfer lead"))
  }
}
