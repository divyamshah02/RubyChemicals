// leads.js — Lead Management JavaScript
// Place this file at: /static/js/leads.js

let leadCsrf, leadEndpoints
let allLeads = []
let currentLeadId = null
let currentUserId = null

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

function initLeads(csrfToken, endpoints) {
  leadCsrf = csrfToken
  leadEndpoints = endpoints
  loadLeads()
}

// ─────────────────────────────────────────────
// STATUS helpers
// ─────────────────────────────────────────────

const STATUS_LABELS = {
  new_lead: "New Lead",
  contacted: "Contacted",
  details_shared: "Details Shared",
  appointment_fixed: "Appointment Fixed",
  visit_done: "Visit Done",
  proposal_sent: "Proposal Sent",
  sample_to_be_done: "Sample To Be Done",
  sample_done: "Sample Done",
  negotiation_followup: "Negotiation / Follow-up",
  won: "Won",
  repeat_order: "Repeat Order",
  closed_lost: "Closed – Lost",
  closed_forwarded: "Closed – Forwarded",
  on_hold: "On Hold",
  future_potential: "Future Potential",
  other: "Other",
}

const PARTY_LABELS = {
  dealer: "Dealer",
  distributor: "Distributor",
  waterproofing_applicator: "Waterproofing Applicator",
  tile_adhesive_applicator: "Tile Adhesive Applicator",
  oem: "OEM",
  architect: "Architect",
  interior_designer: "Interior Designer",
  pmc: "PMC",
  builder_project: "Builder Project",
  individual_project: "Individual Project",
  bungalow: "Bungalow",
  structural_consultant: "Structural Consultant",
  mepf_consultant: "MEPF Consultant",
  other: "Other",
}

function statusBadge(status) {
  const label = STATUS_LABELS[status] || status
  return `<span class="status-badge status-${status}">${label}</span>`
}

function formatDate(d) {
  if (!d) return "—"
  const dt = new Date(d)
  if (isNaN(dt)) return d
  return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
}

function formatDateTime(d) {
  if (!d) return "—"
  const dt = new Date(d)
  if (isNaN(dt)) return d
  return dt.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  })
}

function isOverdue(dateStr) {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

// ─────────────────────────────────────────────
// LOAD & RENDER
// ─────────────────────────────────────────────

async function loadLeads(user_id=null) {
  if (user_id) {
    if (user_id === 'all') {
      currentUserId = null
    } else {
      currentUserId = user_id
    }
  }
  const params = currentUserId ? { user_id: currentUserId } : {}
  const url = leadEndpoints.leads + "?" + toQueryString(params);
  const [ok, res] = await callApi("GET", url)
  if (ok && res.success) {
    allLeads = res.data
    renderLeadsTable(allLeads)
    renderKPIs(allLeads)
    renderFollowupAlerts(allLeads)
  } else {
    console.error("[leads] Failed to load leads", res)
  }
}

async function applyLeadFilters() {
  toggle_loader()
  const userId = document.getElementById("leadUsers").value
  await loadLeads(userId || 'all')
  toggle_loader()
  }

function renderKPIs(leads) {
  document.getElementById("kpiTotal").textContent = leads.length
  document.getElementById("kpiWon").textContent = leads.filter(l => l.lead_status === "won" || l.lead_status === "repeat_order").length
  document.getElementById("kpiLost").textContent = leads.filter(l => l.lead_status === "closed_lost").length
  document.getElementById("kpiContacted").textContent = leads.filter(l => l.lead_status === "contacted").length

  // Pending = has a next_followup date that is not cleared (non-closed)
  const pending = leads.filter(l => l.next_followup && !["closed_lost", "closed_forwarded"].includes(l.lead_status))
  document.getElementById("kpiPending").textContent = pending.length
}

function renderFollowupAlerts(leads) {
  const container = document.getElementById("followupSections")

  const now = new Date()
  const todayStart = new Date(now); todayStart.setHours(0, 0, 0, 0)
  const todayEnd = new Date(now); todayEnd.setHours(23, 59, 59, 999)

  const CLOSED = ["closed_lost", "closed_forwarded"]

  const todayFollowups = leads.filter(l => {
    if (!l.next_followup || CLOSED.includes(l.lead_status)) return false
    const d = new Date(l.next_followup)
    return d >= todayStart && d <= todayEnd
  })

  const missedFollowups = leads.filter(l => {
    if (!l.next_followup || CLOSED.includes(l.lead_status)) return false
    return new Date(l.next_followup) < todayStart
  })

  if (todayFollowups.length === 0 && missedFollowups.length === 0) {
    container.innerHTML = ""
    return
  }

  function buildRows(list) {
    if (list.length === 0) {
      return `<div class="followup-empty"><i class="fas fa-check-circle me-2"></i>All clear</div>`
    }
    return list.map(l => `
      <div class="followup-row">
        <div class="followup-row-info">
          <div class="party">${l.party_name}</div>
          <div class="time"><i class="fas fa-clock me-1"></i>${formatDateTime(l.next_followup)}</div>
          <div class="type">#${l.lead_id} &bull; ${PARTY_LABELS[l.party_type] || l.party_type}</div>
        </div>
        <div class="d-flex align-items-center gap-1 flex-shrink-0">
          ${statusBadge(l.lead_status)}
          <button class="btn btn-sm btn-outline-primary py-0 px-2 ms-1" style="font-size:0.75rem;" onclick="viewLead(${l.id})">
            <i class="fas fa-eye"></i>
          </button>
        </div>
      </div>
    `).join("")
  }

  container.innerHTML = `
    <div class="followup-panels">
      <div class="followup-panel panel-today">
        <div class="followup-panel-header">
          <span><i class="fas fa-calendar-day me-2"></i>Today's Follow-ups</span>
          <span class="badge bg-success">${todayFollowups.length}</span>
        </div>
        <div class="followup-panel-body">${buildRows(todayFollowups)}</div>
      </div>
      <div class="followup-panel panel-missed">
        <div class="followup-panel-header">
          <span><i class="fas fa-exclamation-triangle me-2"></i>Missed Follow-ups</span>
          <span class="badge bg-danger">${missedFollowups.length}</span>
        </div>
        <div class="followup-panel-body">${buildRows(missedFollowups)}</div>
      </div>
    </div>
  `
}

function renderLeadsTable(leads) {
  const tbody = document.querySelector("#leadsTable tbody")
  document.getElementById("leadsCount").textContent = `${leads.length} lead${leads.length !== 1 ? "s" : ""}`

  if (leads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">No leads found</td></tr>'
    return
  }

  tbody.innerHTML = leads.map(l => {
    const followupCell = l.next_followup
      ? `<span style="font-size:0.78rem; color:${isOverdue(l.next_followup) ? "#ef4444" : "#10b981"}; font-weight:600;">
           <i class="fas fa-${isOverdue(l.next_followup) ? "exclamation-circle" : "calendar-check"} me-1"></i>
           ${formatDateTime(l.next_followup)}
         </span>`
      : '<span class="text-muted" style="font-size:0.78rem;">—</span>'

    return `
      <tr>
        <td><span class="lead-id-badge">#${l.lead_id}</span></td>
        <td><strong>${l.party_name}</strong></td>
        <td><span style="font-size:0.8rem;">${PARTY_LABELS[l.party_type] || l.party_type}</span></td>
        <td>${l.contact_person || "—"}</td>
        <td>${l.mobile_number || "—"}</td>
        <td>${l.location || "—"}</td>
        <td>${statusBadge(l.lead_status)}</td>
        <td>${followupCell}</td>
        <td>
          <span class="badge bg-primary" style="font-size:0.78rem;">${l.call_count || 0}</span>
        </td>
        <td style="font-size:0.8rem; color:#94a3b8;">${formatDate(l.created_at)}</td>
        <td>
          <div class="action-buttons">
            <button class="btn btn-info btn-sm" title="View" onclick="viewLead(${l.id})">
              <i class="fas fa-eye"></i>
            </button>            
            <button class="btn btn-danger btn-sm" title="Delete" onclick="confirmDeleteLead(${l.id})">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `
  }).join("")

  // <button class="btn btn-warning btn-sm" title="Edit" onclick="quickEditLead(${l.id})">
  //             <i class="fas fa-edit"></i>
  //           </button>
}

// ─────────────────────────────────────────────
// FILTERS
// ─────────────────────────────────────────────

function applyFilters() {
  const q = document.getElementById("searchInput").value.toLowerCase()
  const statusVal = document.getElementById("statusFilter").value
  const typeVal = document.getElementById("partyTypeFilter").value

  const filtered = allLeads.filter(l => {
    const matchQ = !q || [l.party_name, l.contact_person, l.mobile_number, String(l.lead_id)]
      .some(v => v && v.toLowerCase().includes(q))
    const matchStatus = !statusVal || l.lead_status === statusVal
    const matchType = !typeVal || l.party_type === typeVal
    return matchQ && matchStatus && matchType
  })

  renderLeadsTable(filtered)
}

function clearFilters() {
  document.getElementById("searchInput").value = ""
  document.getElementById("statusFilter").value = ""
  document.getElementById("partyTypeFilter").value = ""
  renderLeadsTable(allLeads)
}

// ─────────────────────────────────────────────
// CREATE LEAD
// ─────────────────────────────────────────────

async function createLead() {
  const partyType = document.getElementById("createPartyType").value
  const partyName = document.getElementById("createPartyName").value.trim()

  if (!partyType || !partyName) {
    alert("Party Type and Party Name are required.")
    return
  }

  const payload = {
    date_of_connect: document.getElementById("createDateOfConnect").value || null,
    lead_source: document.getElementById("createLeadSource").value,
    party_type: partyType,
    party_name: partyName,
    location: document.getElementById("createLocation").value,
    lead_status: document.getElementById("createLeadStatus").value,
    contact_person: document.getElementById("createContactPerson").value,
    mobile_number: document.getElementById("createMobileNumber").value,
    email: document.getElementById("createEmail").value,
    remarks: document.getElementById("createRemarks").value,
  }

  const [ok, res] = await callApi("POST", leadEndpoints.leads, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("createLeadModal")).hide()
    resetCreateForm()
    await loadLeads()
    alert("Lead created successfully!")
  } else {
    const err = res.error ? JSON.stringify(res.error) : "Failed to create lead"
    alert("Error: " + err)
  }
}

function resetCreateForm() {
  ["createDateOfConnect", "createLeadSource", "createPartyType", "createPartyName",
    "createLocation", "createContactPerson", "createMobileNumber", "createEmail", "createRemarks"]
    .forEach(id => { document.getElementById(id).value = "" })
  document.getElementById("createLeadStatus").value = "new_lead"
}

// ─────────────────────────────────────────────
// VIEW LEAD DETAIL
// ─────────────────────────────────────────────

async function viewLead(leadId) {
  currentLeadId = leadId
  const [ok, res] = await callApi("GET", `${leadEndpoints.leads}${leadId}/`)
  if (!ok || !res.success) {
    alert("Failed to load lead details.")
    return
  }

  const lead = res.data
  document.getElementById("viewLeadIdBadge").textContent = "#" + lead.lead_id

  // Build call records timeline HTML
  let callsHtml = ""
  const calls = (lead.call_records || []).filter(c => c.is_active !== false)

  if (calls.length === 0) {
    callsHtml = '<p class="text-muted" style="font-size:0.875rem;">No call records yet.</p>'
  } else {
    callsHtml = `<div class="call-timeline">${calls.map(c => `
      <div class="call-item">
        <div class="call-meta">
          <span class="call-date-badge"><i class="fas fa-calendar me-1"></i>${formatDate(c.call_date)}</span>
          ${statusBadge(c.lead_status)}
          ${c.follow_up_done ? '<span class="badge bg-success" style="font-size:0.72rem;">Follow-up Done</span>' : ""}
        </div>
        <p style="margin:0.4rem 0; color:#374151;">${c.briefing || "—"}</p>
        ${c.contact_number ? `<small class="text-muted"><i class="fas fa-phone me-1"></i>${c.contact_number}</small><br>` : ""}
        ${c.next_followup ? `
          <small style="color:${isOverdue(c.next_followup) ? "#ef4444" : "#64748b"};">
            <i class="fas fa-calendar-alt me-1"></i>Next Follow-up: <strong>${formatDateTime(c.next_followup)}</strong>
          </small><br>` : ""}
        ${c.forwarded_to ? `<small class="text-muted"><i class="fas fa-share me-1"></i>Forwarded to: <strong>${c.forwarded_to}</strong></small><br>` : ""}
        <div class="d-flex justify-content-between align-items-center mt-2">
          <small class="text-muted">By: ${c.created_by_name || "—"} &bull; ${formatDateTime(c.created_at)}</small>
          <div class="d-flex gap-1">
            <button class="btn btn-warning btn-sm p-2" onclick="openEditCallRecord(${c.id})" title="Edit">
              <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-danger btn-sm p-2" onclick="deleteCallRecord(${c.id})" title="Delete">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    `).join("")}</div>`
  }

  // Follow-up alert banner
  const fuBanner = lead.next_followup && !["closed_lost", "closed_forwarded"].includes(lead.lead_status)
    ? `<div class="followup-alert">
         <i class="fas fa-bell me-2"></i>
         <strong>Next Follow-up:</strong> ${formatDateTime(lead.next_followup)}
         ${isOverdue(lead.next_followup) ? ' <span class="badge bg-danger ms-1">OVERDUE</span>' : ""}
       </div>`
    : ""

  document.getElementById("leadDetailContent").innerHTML = `
    ${fuBanner}

    <!-- Lead Info -->
    <div style="background:#f8fafc; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem; border:1px solid #e2e8f0;">
      <h6 style="color:#1e40af; font-weight:700; margin-bottom:1rem;"><i class="fas fa-info-circle me-2"></i>Lead Information</h6>
      <div class="row">
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Lead ID</span><br><strong>${lead.lead_id}</strong></div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Date of Connect</span><br>${formatDate(lead.date_of_connect)}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Lead Source</span><br>${lead.lead_source || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Party Type</span><br>${PARTY_LABELS[lead.party_type] || lead.party_type}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Party Name</span><br><strong>${lead.party_name}</strong></div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Location</span><br>${lead.location || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Contact Person</span><br>${lead.contact_person || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Mobile</span><br>${lead.mobile_number || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Email</span><br>${lead.email || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Status</span><br>${statusBadge(lead.lead_status)}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Created By</span><br>${lead.created_by_name || "—"}</div>
        <div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Created At</span><br>${formatDateTime(lead.created_at)}</div>
        ${lead.forwarded_to ? `<div class="col-md-4 mb-2"><span class="text-muted" style="font-size:0.8rem;">Forwarded To</span><br><strong>${lead.forwarded_to}</strong></div>` : ""}
      </div>
      ${lead.remarks ? `<div class="mt-2"><span class="text-muted" style="font-size:0.8rem;">Remarks / Briefing</span><br><p style="color:#374151; margin-top:0.25rem;">${lead.remarks}</p></div>` : ""}
    </div>

    <!-- Call Records -->
    <h6 style="color:#1e40af; font-weight:700; margin-bottom:1rem;">
      <i class="fas fa-phone-alt me-2"></i>Call Records (${calls.length})
    </h6>
    ${callsHtml}
  `

  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("viewLeadModal"))
  modal.show()
}

// ─────────────────────────────────────────────
// EDIT LEAD
// ─────────────────────────────────────────────

async function openEditLead() {
  if (!currentLeadId) return
  const lead = allLeads.find(l => l.id === currentLeadId)
  if (!lead) return

  document.getElementById("editDateOfConnect").value = lead.date_of_connect || ""
  document.getElementById("editLeadSource").value = lead.lead_source || ""
  document.getElementById("editPartyType").value = lead.party_type || ""
  document.getElementById("editPartyName").value = lead.party_name || ""
  document.getElementById("editLocation").value = lead.location || ""
  document.getElementById("editLeadStatus").value = lead.lead_status || "new_lead"
  document.getElementById("editContactPerson").value = lead.contact_person || ""
  document.getElementById("editMobileNumber").value = lead.mobile_number || ""
  document.getElementById("editEmail").value = lead.email || ""
  document.getElementById("editRemarks").value = lead.remarks || ""
  document.getElementById("editForwardedTo").value = lead.forwarded_to || ""

  const showFwd = lead.lead_status === "closed_forwarded"
  document.getElementById("editForwardedToGroup").style.display = showFwd ? "block" : "none"

  document.getElementById("editLeadStatus").onchange = function () {
    document.getElementById("editForwardedToGroup").style.display =
      this.value === "closed_forwarded" ? "block" : "none"
  }

  // Hide view modal, show edit modal
  bootstrap.Modal.getInstance(document.getElementById("viewLeadModal")).hide()
  setTimeout(() => {
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editLeadModal")).show()
  }, 300)
}

async function quickEditLead(leadId) {
  currentLeadId = leadId
  openEditLead()
}

async function submitEditLead() {
  if (!currentLeadId) return
  const partyType = document.getElementById("editPartyType").value
  const partyName = document.getElementById("editPartyName").value.trim()

  if (!partyType || !partyName) {
    alert("Party Type and Party Name are required.")
    return
  }

  const status = document.getElementById("editLeadStatus").value
  const payload = {
    date_of_connect: document.getElementById("editDateOfConnect").value || null,
    lead_source: document.getElementById("editLeadSource").value,
    party_type: partyType,
    party_name: partyName,
    location: document.getElementById("editLocation").value,
    lead_status: status,
    contact_person: document.getElementById("editContactPerson").value,
    mobile_number: document.getElementById("editMobileNumber").value,
    email: document.getElementById("editEmail").value,
    remarks: document.getElementById("editRemarks").value,
    forwarded_to: status === "closed_forwarded" ? document.getElementById("editForwardedTo").value : "",
  }

  const [ok, res] = await callApi("PUT", `${leadEndpoints.leads}${currentLeadId}/`, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("editLeadModal")).hide()
    currentLeadId = null
    await loadLeads()
    alert("Lead updated successfully!")
  } else {
    const err = res.error ? JSON.stringify(res.error) : "Failed to update lead"
    alert("Error: " + err)
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
  const [ok, res] = await callApi("DELETE", `${leadEndpoints.leads}${leadId}/`, {}, leadCsrf)
  if (ok && res.success) {
    // Close any open modals
    ["viewLeadModal", "editLeadModal"].forEach(id => {
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

  // Pre-fill today's date
  document.getElementById("callDate").value = new Date().toISOString().split("T")[0]
  document.getElementById("callContactNumber").value = ""
  document.getElementById("callBriefing").value = ""
  document.getElementById("callLeadStatus").value = ""
  document.getElementById("callNextFollowup").value = ""
  document.getElementById("callForwardedTo").value = ""
  document.getElementById("forwardedToGroup").style.display = "none"
  document.getElementById("nextFollowupGroup").style.display = "block"

  bootstrap.Modal.getOrCreateInstance(document.getElementById("addCallRecordModal")).show()
}

function toggleForwardedTo() {
  const status = document.getElementById("callLeadStatus").value
  const forwardedGroup = document.getElementById("forwardedToGroup")
  const nextFollowupGroup = document.getElementById("nextFollowupGroup")

  if (status === "closed_forwarded") {
    forwardedGroup.style.display = "block"
    nextFollowupGroup.style.display = "none"
    document.getElementById("callNextFollowup").value = ""
  } else if (["closed_lost"].includes(status)) {
    forwardedGroup.style.display = "none"
    nextFollowupGroup.style.display = "none"
    document.getElementById("callNextFollowup").value = ""
  } else {
    forwardedGroup.style.display = "none"
    nextFollowupGroup.style.display = "block"
  }
}

async function submitCallRecord() {
  const callDate = document.getElementById("callDate").value
  const briefing = document.getElementById("callBriefing").value.trim()
  const status = document.getElementById("callLeadStatus").value
  const nextFollowup = document.getElementById("callNextFollowup").value
  const forwardedTo = document.getElementById("callForwardedTo").value.trim()
  const contactNumber = document.getElementById("callContactNumber").value.trim()

  if (!callDate || !briefing) {
    alert("Call Date and Briefing are required.")
    return
  }

  if (status === "closed_forwarded" && !forwardedTo) {
    alert("Please specify who this lead is forwarded to.")
    return
  }

  const payload = {
    lead: currentLeadId,
    call_date: callDate,
    contact_number: contactNumber,
    briefing: briefing,
    lead_status: status || null,
    next_followup: nextFollowup || null,
    forwarded_to: forwardedTo,
  }

  const [ok, res] = await callApi("POST", leadEndpoints.callRecords, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("addCallRecordModal")).hide()
    // Re-open the lead detail modal with fresh data
    await viewLead(currentLeadId)
    await loadLeads()
    alert("Call record added successfully!")
  } else {
    const err = res.error ? JSON.stringify(res.error) : "Failed to add call record"
    alert("Error: " + err)
  }
}

async function deleteCallRecord(recordId) {
  if (!confirm("Delete this call record?")) return
  const [ok, res] = await callApi("DELETE", `${leadEndpoints.callRecords}${recordId}/`, {}, leadCsrf)
  if (ok && res.success) {
    await viewLead(currentLeadId)
    await loadLeads()
  } else {
    alert("Error: " + (res.error || "Failed to delete"))
  }
}

// ─────────────────────────────────────────────
// EDIT CALL RECORD
// ─────────────────────────────────────────────

async function openEditCallRecord(recordId) {
  // Fetch the single call record
  const [ok, res] = await callApi("GET", `${leadEndpoints.callRecords}${recordId}/`)
  if (!ok || !res.success) {
    alert("Failed to load call record.")
    return
  }

  const c = res.data
  document.getElementById("editCallRecordId").value = c.id
  document.getElementById("editCallDate").value = c.call_date || ""
  document.getElementById("editCallContactNumber").value = c.contact_number || ""
  document.getElementById("editCallBriefing").value = c.briefing || ""
  document.getElementById("editCallLeadStatus").value = c.lead_status || ""
  document.getElementById("editCallNextFollowup").value = c.next_followup
    ? c.next_followup.slice(0, 16)   // trim to datetime-local format
    : ""
  document.getElementById("editCallForwardedTo").value = c.forwarded_to || ""

  // Show/hide groups based on loaded status
  toggleEditForwardedTo()

  // Close detail modal, open edit modal
  const detailModal = bootstrap.Modal.getInstance(document.getElementById("viewLeadModal"))
  if (detailModal) detailModal.hide()

  setTimeout(() => {
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editCallRecordModal")).show()
  }, 300)
}

function openLeadTransfer() {
  setTimeout(() => {
    bootstrap.Modal.getOrCreateInstance(document.getElementById("transferLeadModal")).show()
  }, 300)
}

function toggleEditForwardedTo() {
  const status = document.getElementById("editCallLeadStatus").value
  const fwdGroup = document.getElementById("editForwardedToGroup")
  const fuGroup = document.getElementById("editNextFollowupGroup")

  if (status === "closed_forwarded") {
    fwdGroup.style.display = "block"
    fuGroup.style.display = "none"
    document.getElementById("editCallNextFollowup").value = ""
  } else if (status === "closed_lost") {
    fwdGroup.style.display = "none"
    fuGroup.style.display = "none"
    document.getElementById("editCallNextFollowup").value = ""
  } else {
    fwdGroup.style.display = "none"
    fuGroup.style.display = "block"
  }
}

async function submitEditCallRecord() {
  const recordId = document.getElementById("editCallRecordId").value
  const callDate = document.getElementById("editCallDate").value
  const briefing = document.getElementById("editCallBriefing").value.trim()
  const status = document.getElementById("editCallLeadStatus").value
  const nextFollowup = document.getElementById("editCallNextFollowup").value
  const forwardedTo = document.getElementById("editCallForwardedTo").value.trim()
  const contactNum = document.getElementById("editCallContactNumber").value.trim()

  if (!callDate || !briefing) {
    alert("Call Date and Briefing are required.")
    return
  }
  if (status === "closed_forwarded" && !forwardedTo) {
    alert("Please specify who this lead is forwarded to.")
    return
  }

  const payload = {
    call_date: callDate,
    contact_number: contactNum,
    briefing: briefing,
    lead_status: status || null,
    next_followup: nextFollowup || null,
    forwarded_to: forwardedTo,
  }

  const [ok, res] = await callApi("PUT", `${leadEndpoints.callRecords}${recordId}/`, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("editCallRecordModal")).hide()
    // Re-open lead detail with refreshed data
    await viewLead(currentLeadId)
    await loadLeads()
    alert("Call record updated successfully!")
  } else {
    const err = res.error ? JSON.stringify(res.error) : "Failed to update call record"
    alert("Error: " + err)
  }
}

async function submitTransferLead() {
  if (!currentLeadId) return
  const newOwner = document.getElementById("allLeadUsers").value
  if (!newOwner) {
    alert("Please select a user to transfer the lead to.")
    return
  }

  const payload = {
    lead_id: currentLeadId,
    new_owner_id: newOwner,
  }

  const [ok, res] = await callApi("POST", `${leadEndpoints.transferLeads}`, payload, leadCsrf)
  if (ok && res.success) {
    bootstrap.Modal.getInstance(document.getElementById("transferLeadModal")).hide()
    // Re-open lead detail with refreshed data
    await loadLeads()
    alert("Lead transferred successfully!")
  } else {
    const err = res.error ? JSON.stringify(res.error) : "Failed to transfer lead"
    alert("Error: " + err)
  }
}