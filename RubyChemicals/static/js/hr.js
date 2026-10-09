/* HR page: employees, attendance, leaves, universal leaves.
   Entry point: initHR(csrf, endpoints) — called from templates/hr.html */

let HR_CSRF = ''
let HR_ENDPOINTS = {}

let employees = []
let attendanceData = null
let leaves = []
let holidays = []

let empSort = { key: 'user_name', dir: 'asc' }
let attSort = 'date_desc'
let leaveSort = { key: 'date', dir: 'desc' }

const DOC_FIELDS = ['photo', 'aadhar_file', 'pan_file', 'bank_proof_file']
const TEXT_FIELDS = [
    'full_name', 'joining_date', 'department', 'position', 'reporting_to',
    'current_address', 'permanent_address', 'personal_mobile',
    'aadhar_number', 'pan_number',
    'bank_name', 'bank_account_no', 'bank_branch', 'bank_ifsc',
    'office_mobile', 'device_details', 'imei_1', 'imei_2', 'sim_card_in_name_of',
]
const ROLE_LABELS = { accounts: 'Accounts', factory: 'Factory', accountant: 'Accountant', office: 'Office', hr: 'HR', admin: 'Admin' }

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function esc(value) {
    if (value === null || value === undefined) return ''
    return String(value)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function el(id) { return document.getElementById(id) }

function toast(message, type = 'ok') {
    const node = document.createElement('div')
    node.className = `hr-toast ${type}`
    node.setAttribute('role', 'status')
    node.textContent = message
    el('toastWrap').appendChild(node)
    setTimeout(() => node.remove(), 4500)
}

async function api(method, url, body = null, media = false) {
    try {
        const result = await callApi(method, url, body, HR_CSRF, media)
        if (!result) return { success: false, error: 'Unexpected response from the server.' }
        const [ok, data] = result
        if (!ok) return { success: false, error: String(data) }
        if (data && data.success === false) return data
        if (data && data.success === undefined && data.detail) return { success: false, error: data.detail }
        return data
    } catch (e) {
        return { success: false, error: 'Request failed. Please try again.' }
    }
}

function toISODate(date) {
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${date.getFullYear()}-${m}-${d}`
}

function parseDay(iso) {
    const [y, m, d] = iso.split('-').map(Number)
    return new Date(y, m - 1, d)
}

function fmtDate(iso) {
    if (!iso) return '-'
    return parseDay(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtWeekday(iso) {
    return parseDay(iso).toLocaleDateString('en-IN', { weekday: 'short' })
}

// Reads HH:MM straight from the server's local-time ISO string so the browser timezone never shifts it.
function fmtTime(iso) {
    if (!iso) return '-'
    const [h, m] = iso.substring(11, 16).split(':').map(Number)
    const suffix = h >= 12 ? 'PM' : 'AM'
    const hour = h % 12 === 0 ? 12 : h % 12
    return `${hour}:${String(m).padStart(2, '0')} ${suffix}`
}

function fmtMinutes(minutes) {
    if (minutes === null || minutes === undefined) return '-'
    return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`
}

function initials(name) {
    return (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('')
}

function isImage(url) {
    return /\.(png|jpe?g|gif|webp|bmp)(\?|$)/i.test(url || '')
}

function fileLink(url, label) {
    if (!url) return '<span class="text-muted">Not uploaded</span>'
    return `<a href="${esc(url)}" target="_blank" rel="noopener"><i class="fas fa-file me-1"></i>${esc(label)}</a>`
}

function setSortIcons(selector, attr, activeKey, dir) {
    document.querySelectorAll(selector).forEach(th => {
        const active = th.getAttribute(attr) === activeKey
        th.classList.toggle('sorted', active)
        const icon = th.querySelector('.sort-icon')
        if (icon) icon.className = `fas ${active ? (dir === 'asc' ? 'fa-sort-up' : 'fa-sort-down') : 'fa-sort'} sort-icon`
    })
}

function compare(a, b, dir) {
    const empty = v => v === null || v === undefined || v === ''
    if (empty(a) && empty(b)) return 0
    if (empty(a)) return 1
    if (empty(b)) return -1
    const result = typeof a === 'number' && typeof b === 'number'
        ? a - b
        : String(a).localeCompare(String(b), undefined, { sensitivity: 'base' })
    return dir === 'asc' ? result : -result
}

/* ── Init ────────────────────────────────────────────────────────────────── */

async function initHR(csrf, endpoints) {
    HR_CSRF = csrf
    HR_ENDPOINTS = endpoints

    const today = new Date()
    el('attFrom').value = toISODate(new Date(today.getFullYear(), today.getMonth(), 1))
    el('attTo').value = toISODate(today)

    setSortIcons('th[data-sort]', 'data-sort', empSort.key, empSort.dir)
    setSortIcons('th[data-leave-sort]', 'data-leave-sort', leaveSort.key, leaveSort.dir)
    setSortIcons('th[data-att-sort]', 'data-att-sort', 'date', 'desc')

    await Promise.all([loadEmployees(), loadLeaves(), loadHolidays()])
}

/* ── Employees ───────────────────────────────────────────────────────────── */

async function loadEmployees() {
    const res = await api('GET', HR_ENDPOINTS.employees)
    if (!res.success) {
        toast(res.error || 'Could not load employees.', 'err')
        el('employeesBody').innerHTML = `<tr><td colspan="8" class="empty-state">Could not load employees.</td></tr>`
        return
    }
    employees = res.data || []
    populateEmployeeSelects()
    renderEmployees()
}

function populateEmployeeSelects() {
    const sorted = [...employees].sort((a, b) => compare(a.user_name, b.user_name, 'asc'))
    const options = sorted.map(e => `<option value="${e.user}">${esc(e.user_name)} (${esc(e.user_code)})</option>`).join('')

    const keep = id => el(id).value
    const attValue = keep('attUser'), leaveFilterValue = keep('leaveUserFilter'), leaveValue = keep('leaveUser')
    el('attUser').innerHTML = `<option value="">Select employee</option>${options}`
    el('leaveUserFilter').innerHTML = `<option value="">All employees</option>${options}`
    el('leaveUser').innerHTML = `<option value="">Select employee</option>${options}`
    el('attUser').value = attValue
    el('leaveUserFilter').value = leaveFilterValue
    el('leaveUser').value = leaveValue

    const departments = [...new Set(employees.map(e => (e.department || '').trim()).filter(Boolean))].sort()
    const deptValue = el('empDept').value
    el('empDept').innerHTML = `<option value="">All</option>${departments.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('')}`
    el('empDept').value = deptValue
    el('deptList').innerHTML = departments.map(d => `<option value="${esc(d)}"></option>`).join('')
}

function filteredEmployees() {
    const q = el('empSearch').value.trim().toLowerCase()
    const dept = el('empDept').value
    const role = el('empRole').value
    const completeness = el('empComplete').value

    return employees.filter(e => {
        if (dept && (e.department || '').trim() !== dept) return false
        if (role && e.role !== role) return false
        if (completeness === 'complete' && !e.is_complete) return false
        if (completeness === 'incomplete' && e.is_complete) return false
        if (q) {
            const haystack = [e.user_name, e.full_name, e.email, e.user_code, e.personal_mobile, e.office_mobile, e.position, e.department]
                .join(' ').toLowerCase()
            if (!haystack.includes(q)) return false
        }
        return true
    })
}

function renderEmployees() {
    const list = filteredEmployees().sort((a, b) => {
        const value = e => empSort.key === 'missing' ? e.missing_fields.length : e[empSort.key]
        return compare(value(a), value(b), empSort.dir)
    })

    el('kpiEmpTotal').textContent = employees.length
    el('kpiEmpComplete').textContent = employees.filter(e => e.is_complete).length
    el('kpiEmpIncomplete').textContent = employees.filter(e => !e.is_complete).length
    setSortIcons('th[data-sort]', 'data-sort', empSort.key, empSort.dir)

    if (!list.length) {
        el('employeesBody').innerHTML = `<tr><td colspan="8" class="empty-state">No employees match the filters.</td></tr>`
        return
    }

    el('employeesBody').innerHTML = list.map(e => {
        const name = e.full_name || e.user_name
        const avatar = e.photo && isImage(e.photo)
            ? `<img class="avatar" src="${esc(e.photo)}" alt="${esc(name)}">`
            : `<span class="avatar" aria-hidden="true">${esc(initials(name))}</span>`
        const profile = e.is_complete
            ? `<span class="pill pill-complete">Complete</span>`
            : `<span class="pill pill-incomplete" title="Missing: ${esc(e.missing_fields.join(', '))}">${e.missing_fields.length} missing</span>`
        return `
        <tr>
            <td><div class="emp-cell">${avatar}<div><div class="emp-name">${esc(name)}</div><div class="emp-sub">${esc(e.user_code)} &middot; ${esc(e.email)}</div></div></div></td>
            <td>${esc(e.department) || '-'}<div class="emp-sub">${esc(e.position) || ''}</div></td>
            <td>${esc(ROLE_LABELS[e.role] || e.role)}</td>
            <td>${fmtDate(e.joining_date)}</td>
            <td>${esc(e.reporting_to_name) || '-'}</td>
            <td>${esc(e.personal_mobile) || '-'}</td>
            <td>${profile}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-info" title="View details" aria-label="View details" onclick="openEmployee(${e.user}, false)"><i class="fas fa-eye"></i></button>
                    <button class="btn btn-warning" title="Edit details" aria-label="Edit details" onclick="openEmployee(${e.user}, true)"><i class="fas fa-pen"></i></button>
                    <button class="btn btn-primary-custom" style="padding:0.3rem 0.65rem;font-size:0.8rem;" title="Attendance" aria-label="Attendance" onclick="openAttendanceFor(${e.user})"><i class="fas fa-clock"></i></button>
                    <button class="btn btn-success-custom" style="padding:0.3rem 0.65rem;font-size:0.8rem;" title="Add leave" aria-label="Add leave" onclick="openLeaveModal(${e.user})"><i class="fas fa-calendar-plus"></i></button>
                </div>
            </td>
        </tr>`
    }).join('')
}

function sortEmployees(key) {
    empSort = { key, dir: empSort.key === key && empSort.dir === 'asc' ? 'desc' : 'asc' }
    renderEmployees()
}

function resetEmployeeFilters() {
    el('empSearch').value = ''
    el('empDept').value = ''
    el('empRole').value = ''
    el('empComplete').value = ''
    renderEmployees()
}

/* ── Employee modal ──────────────────────────────────────────────────────── */

function currentEmployee() {
    return employees.find(e => String(e.user) === el('empUserId').value)
}

function openEmployee(userPk, edit) {
    const emp = employees.find(e => e.user === userPk)
    if (!emp) return
    el('empUserId').value = userPk
    el('employeeModalTitle').textContent = emp.full_name || emp.user_name
    renderEmployeeView(emp)
    if (edit) showEmployeeForm()
    else showEmployeeView()
    bootstrap.Modal.getOrCreateInstance(el('employeeModal')).show()
}

function showEmployeeView() {
    el('employeeViewBody').style.display = ''
    el('employeeForm').style.display = 'none'
    el('employeeEditBtn').style.display = ''
    el('employeeSaveBtn').style.display = 'none'
}

function showEmployeeForm() {
    const emp = currentEmployee()
    if (!emp) return
    fillEmployeeForm(emp)
    el('employeeViewBody').style.display = 'none'
    el('employeeForm').style.display = ''
    el('employeeEditBtn').style.display = 'none'
    el('employeeSaveBtn').style.display = ''
}

function detailItem(label, value) {
    return `<div class="detail-item"><div class="k">${esc(label)}</div><div class="v">${value || '-'}</div></div>`
}

function renderEmployeeView(emp) {
    const missing = emp.missing_fields.length
        ? `<div class="alert alert-warning py-2" style="font-size:0.85rem;"><i class="fas fa-triangle-exclamation me-1"></i>Missing: ${esc(emp.missing_fields.join(', '))}</div>`
        : ''
    const contacts = emp.emergency_contacts.length
        ? emp.emergency_contacts.map(c => `<div>${esc(c.name)} <span class="text-muted">(${esc(c.relation)})</span> &middot; ${esc(c.mobile)}</div>`).join('')
        : ''
    const photo = emp.photo && isImage(emp.photo)
        ? `<img src="${esc(emp.photo)}" alt="${esc(emp.user_name)}" style="width:96px;height:96px;object-fit:cover;border-radius:12px;border:1px solid #e2e8f0;">`
        : ''

    el('employeeViewBody').innerHTML = `
        ${missing}
        <div class="form-section">
            <div class="form-section-title">Basic Details</div>
            ${photo ? `<div class="mb-3">${photo}</div>` : ''}
            <div class="detail-grid">
                ${detailItem('Name', esc(emp.full_name || emp.user_name))}
                ${detailItem('Employee ID', esc(emp.user_code))}
                ${detailItem('Email', esc(emp.email))}
                ${detailItem('Role', esc(ROLE_LABELS[emp.role] || emp.role))}
                ${detailItem('Joining Date', fmtDate(emp.joining_date))}
                ${detailItem('Department', esc(emp.department))}
                ${detailItem('Position', esc(emp.position))}
                ${detailItem('Reporting To', esc(emp.reporting_to_name))}
                ${detailItem('Personal Mobile', esc(emp.personal_mobile))}
                ${detailItem('Current Address', esc(emp.current_address))}
                ${detailItem('Permanent Address', esc(emp.permanent_address))}
                ${detailItem('Photo', fileLink(emp.photo, 'View photo'))}
            </div>
        </div>
        <div class="form-section">
            <div class="form-section-title">Identity Documents</div>
            <div class="detail-grid">
                ${detailItem('Aadhar Number', esc(emp.aadhar_number))}
                ${detailItem('Aadhar Document', fileLink(emp.aadhar_file, 'View Aadhar'))}
                ${detailItem('PAN Number', esc(emp.pan_number))}
                ${detailItem('PAN Document', fileLink(emp.pan_file, 'View PAN'))}
            </div>
        </div>
        <div class="form-section">
            <div class="form-section-title">Bank Details</div>
            <div class="detail-grid">
                ${detailItem('Bank Name', esc(emp.bank_name))}
                ${detailItem('Account No.', esc(emp.bank_account_no))}
                ${detailItem('Branch Name', esc(emp.bank_branch))}
                ${detailItem('IFSC', esc(emp.bank_ifsc))}
                ${detailItem('Bank Proof', fileLink(emp.bank_proof_file, 'View bank proof'))}
            </div>
        </div>
        <div class="form-section">
            <div class="form-section-title">Emergency Contacts</div>
            <div class="v">${contacts || '<span class="text-muted">None added</span>'}</div>
        </div>
        <div class="form-section">
            <div class="form-section-title">Office Device &amp; SIM</div>
            <div class="detail-grid">
                ${detailItem('Office Mobile', esc(emp.office_mobile))}
                ${detailItem('Mobile Details', esc(emp.device_details))}
                ${detailItem('IMEI 1', esc(emp.imei_1))}
                ${detailItem('IMEI 2', esc(emp.imei_2))}
                ${detailItem('SIM Card In Name Of', esc(emp.sim_card_in_name_of))}
            </div>
        </div>`
}

function reportingOptions(selfPk) {
    const users = window.REPORTING_USERS || []
    return '<option value="">None</option>' + users
        .filter(u => u.id !== selfPk)
        .map(u => `<option value="${u.id}">${esc(u.name)} (${esc(ROLE_LABELS[u.role] || u.role)})</option>`)
        .join('')
}

function fillEmployeeForm(emp) {
    el('f_reporting_to').innerHTML = reportingOptions(emp.user)
    TEXT_FIELDS.forEach(field => {
        const input = el(`f_${field}`)
        input.value = emp[field] === null || emp[field] === undefined ? '' : emp[field]
    })
    if (!el('f_full_name').value) el('f_full_name').value = emp.user_name

    DOC_FIELDS.forEach(field => {
        el(`f_${field}`).value = ''
        el(`cur_${field}`).innerHTML = emp[field]
            ? `Current: ${fileLink(emp[field], 'View file')}`
            : '<span class="text-danger">Required - not uploaded yet</span>'
    })

    el('emergencyRows').innerHTML = ''
    if (emp.emergency_contacts.length) emp.emergency_contacts.forEach(addEmergencyRow)
    else addEmergencyRow()
}

function copyCurrentAddress() {
    el('f_permanent_address').value = el('f_current_address').value
}

function addEmergencyRow(contact = {}) {
    const wrap = document.createElement('div')
    wrap.className = 'emergency-row'
    wrap.innerHTML = `
        <div class="row g-2 align-items-end">
            <div class="col-md-4"><label class="form-label">Name</label><input type="text" class="form-control em-name" maxlength="150" value="${esc(contact.name)}"></div>
            <div class="col-md-3"><label class="form-label">Relation</label><input type="text" class="form-control em-relation" maxlength="100" value="${esc(contact.relation)}"></div>
            <div class="col-md-4"><label class="form-label">Mobile Number</label><input type="tel" class="form-control em-mobile" maxlength="15" value="${esc(contact.mobile)}"></div>
            <div class="col-md-1 d-grid"><button type="button" class="btn btn-danger" aria-label="Remove contact" onclick="this.closest('.emergency-row').remove()"><i class="fas fa-trash"></i></button></div>
        </div>`
    el('emergencyRows').appendChild(wrap)
}

function collectEmergencyContacts() {
    return [...document.querySelectorAll('#emergencyRows .emergency-row')]
        .map(row => ({
            name: row.querySelector('.em-name').value.trim(),
            relation: row.querySelector('.em-relation').value.trim(),
            mobile: row.querySelector('.em-mobile').value.trim(),
        }))
        .filter(c => c.name || c.relation || c.mobile)
}

async function saveEmployee() {
    const emp = currentEmployee()
    if (!emp) return

    const form = new FormData()
    TEXT_FIELDS.forEach(field => form.append(field, el(`f_${field}`).value.trim()))
    form.set('pan_number', el('f_pan_number').value.trim().toUpperCase())
    form.set('bank_ifsc', el('f_bank_ifsc').value.trim().toUpperCase())
    form.append('emergency_contacts', JSON.stringify(collectEmergencyContacts()))

    for (const field of DOC_FIELDS) {
        const file = el(`f_${field}`).files[0]
        if (file) {
            if (file.size > 10 * 1024 * 1024) { toast(`${file.name} is larger than 10 MB.`, 'err'); return }
            form.append(field, file)
        }
    }

    const button = el('employeeSaveBtn')
    button.disabled = true
    const res = await api('PATCH', `${HR_ENDPOINTS.employees}${emp.user}/`, form, true)
    button.disabled = false

    if (!res.success) {
        toast(res.error || 'Could not save employee details.', 'err')
        return
    }
    const index = employees.findIndex(e => e.user === emp.user)
    employees[index] = res.data
    populateEmployeeSelects()
    renderEmployees()
    renderEmployeeView(res.data)
    el('employeeModalTitle').textContent = res.data.full_name || res.data.user_name
    showEmployeeView()
    toast('Employee details saved.')
}

/* ── Attendance ──────────────────────────────────────────────────────────── */

function openAttendanceFor(userPk) {
    el('attUser').value = userPk
    bootstrap.Tab.getOrCreateInstance(document.querySelector('[data-bs-target="#paneAttendance"]')).show()
    loadAttendance()
}

async function loadAttendance() {
    const user = el('attUser').value
    if (!user) {
        attendanceData = null
        el('attKpis').style.display = 'none'
        el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state">Select an employee to view attendance.</td></tr>`
        return
    }
    const params = { user_id: user }
    if (el('attFrom').value) params.from_date = el('attFrom').value
    if (el('attTo').value) params.to_date = el('attTo').value

    el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state">Loading...</td></tr>`
    const res = await api('GET', `${HR_ENDPOINTS.attendance}?${toQueryString(params)}`)
    if (!res.success) {
        attendanceData = null
        el('attKpis').style.display = 'none'
        el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state text-danger">${esc(res.error || 'Could not load attendance.')}</td></tr>`
        return
    }
    attendanceData = res.data
    renderAttendance()
}

const ATT_STATUS = {
    present:        ['Present', 'pill-present'],
    half_day:       ['Half Day', 'pill-half'],
    leave:          ['On Leave', 'pill-leave'],
    half_leave:     ['Half Leave', 'pill-leave'],
    holiday:        ['Holiday', 'pill-holiday'],
    weekly_off:     ['Weekly Off', 'pill-off'],
    absent:         ['Absent', 'pill-absent'],
    not_checked_in: ['Not in yet', 'pill-pending'],
}

function attendanceRemarks(row) {
    const notes = []
    if (row.forgot_checkout) notes.push('<span class="forgot-flag"><i class="fas fa-circle-exclamation me-1"></i>Forgot to check out</span>')
    if (row.in_progress) notes.push('<span class="in-progress-flag"><i class="fas fa-circle-play me-1"></i>Working now</span>')
    if (row.is_half_day) notes.push(`<span class="text-muted">Checked in after ${esc(formatCutoff(attendanceData.half_day_cutoff))}</span>`)
    if (row.leave) notes.push(`<span>${esc(row.leave.type)}${row.leave.reason ? ': ' + esc(row.leave.reason) : ''}</span>`)
    if (row.holiday) notes.push(`<span>${esc(row.holiday)}</span>`)
    return notes.join('<br>') || '-'
}

function formatCutoff(hhmm) {
    const [h, m] = hhmm.split(':').map(Number)
    return `${h % 12 === 0 ? 12 : h % 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`
}

function matchesAttendanceFilter(row, filter) {
    if (!filter) return true
    if (filter === 'forgot') return row.forgot_checkout
    if (filter === 'leave') return row.status === 'leave' || row.status === 'half_leave'
    return row.status === filter
}

function renderAttendance() {
    if (!attendanceData) return
    const { rows, summary } = attendanceData
    const filter = el('attStatus').value
    const [key, dir] = attSort.split('_')

    const value = r => key === 'date' ? r.date : key === 'in' ? r.check_in : r.worked_minutes
    const visible = rows
        .filter(r => matchesAttendanceFilter(r, filter))
        .sort((a, b) => compare(value(a), value(b), dir))

    el('attKpis').style.display = ''
    el('kpiPresent').textContent = summary.present
    el('kpiHalf').textContent = summary.half_day
    el('kpiAbsent').textContent = summary.absent
    el('kpiLeave').textContent = summary.leave_days
    el('kpiForgot').textContent = summary.forgot_checkout
    el('kpiHours').textContent = fmtMinutes(summary.worked_minutes)
    setSortIcons('th[data-att-sort]', 'data-att-sort', key, dir)

    if (!visible.length) {
        el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state">No days match the filter.</td></tr>`
        return
    }

    el('attendanceBody').innerHTML = visible.map(r => {
        const [label, cls] = ATT_STATUS[r.status] || [r.status, 'pill-pending']
        const muted = r.status === 'weekly_off' || r.status === 'holiday'
        const checkOut = r.check_out
            ? fmtTime(r.check_out)
            : (r.forgot_checkout ? '<span class="forgot-flag">Missing</span>' : '-')
        return `
        <tr class="${r.forgot_checkout ? 'row-forgot' : ''} ${muted ? 'row-muted' : ''}">
            <td><strong>${fmtDate(r.date)}</strong></td>
            <td>${esc(r.weekday)}</td>
            <td>${fmtTime(r.check_in)}</td>
            <td>${checkOut}</td>
            <td>${fmtMinutes(r.worked_minutes)}</td>
            <td><span class="pill ${cls}">${label}</span></td>
            <td>${attendanceRemarks(r)}</td>
        </tr>`
    }).join('')
}

function onAttendanceSortChange() {
    attSort = el('attSort').value
    renderAttendance()
}

function sortAttendanceBy(key) {
    const [currentKey, currentDir] = attSort.split('_')
    attSort = `${key}_${currentKey === key && currentDir === 'asc' ? 'desc' : 'asc'}`
    el('attSort').value = attSort
    renderAttendance()
}

/* ── Leaves ──────────────────────────────────────────────────────────────── */

async function loadLeaves() {
    const params = {}
    if (el('leaveUserFilter').value) params.user_id = el('leaveUserFilter').value
    if (el('leaveTypeFilter').value) params.leave_type = el('leaveTypeFilter').value
    if (el('leaveFromFilter').value) params.from_date = el('leaveFromFilter').value
    if (el('leaveToFilter').value) params.to_date = el('leaveToFilter').value

    const res = await api('GET', `${HR_ENDPOINTS.leaves}?${toQueryString(params)}`)
    if (!res.success) {
        toast(res.error || 'Could not load leaves.', 'err')
        el('leavesBody').innerHTML = `<tr><td colspan="7" class="empty-state">Could not load leaves.</td></tr>`
        return
    }
    leaves = res.data || []
    renderLeaves()
}

function renderLeaves() {
    const sorted = [...leaves].sort((a, b) => compare(a[leaveSort.key], b[leaveSort.key], leaveSort.dir))
    setSortIcons('th[data-leave-sort]', 'data-leave-sort', leaveSort.key, leaveSort.dir)

    if (!sorted.length) {
        el('leavesBody').innerHTML = `<tr><td colspan="7" class="empty-state">No leaves found.</td></tr>`
        return
    }
    el('leavesBody').innerHTML = sorted.map(l => `
        <tr>
            <td><strong>${fmtDate(l.date)}</strong><div class="emp-sub">${fmtWeekday(l.date)}</div></td>
            <td><div class="emp-name">${esc(l.user_name)}</div><div class="emp-sub">${esc(l.user_code)}</div></td>
            <td><span class="pill pill-leave">${esc(l.leave_type_display)}</span></td>
            <td>${l.day_type === 'half' ? 'Half day' : 'Full day'}</td>
            <td>${esc(l.reason) || '-'}</td>
            <td>${esc(l.created_by_name) || '-'}</td>
            <td><div class="action-buttons"><button class="btn btn-danger" aria-label="Delete leave" onclick="deleteLeave(${l.id})"><i class="fas fa-trash"></i></button></div></td>
        </tr>`).join('')
}

function sortLeavesBy(key) {
    leaveSort = { key, dir: leaveSort.key === key && leaveSort.dir === 'asc' ? 'desc' : 'asc' }
    renderLeaves()
}

function resetLeaveFilters() {
    el('leaveUserFilter').value = ''
    el('leaveTypeFilter').value = ''
    el('leaveFromFilter').value = ''
    el('leaveToFilter').value = ''
    loadLeaves()
}

function openLeaveModal(userPk = '') {
    el('leaveForm').reset()
    el('leaveUser').value = userPk || el('leaveUserFilter').value || ''
    el('leaveTo').disabled = false
    bootstrap.Modal.getOrCreateInstance(el('leaveModal')).show()
}

function syncLeaveDates() {
    const from = el('leaveFrom').value
    const half = el('leaveDayType').value === 'half'
    el('leaveTo').disabled = half
    if (half || (from && (!el('leaveTo').value || el('leaveTo').value < from))) el('leaveTo').value = from
}

async function saveLeave() {
    const body = {
        user_id: el('leaveUser').value,
        from_date: el('leaveFrom').value,
        to_date: el('leaveTo').value || el('leaveFrom').value,
        leave_type: el('leaveType').value,
        day_type: el('leaveDayType').value,
        reason: el('leaveReason').value.trim(),
    }
    if (!body.user_id) { toast('Choose an employee.', 'err'); return }
    if (!body.from_date) { toast('Choose the leave date.', 'err'); return }

    const button = el('leaveSaveBtn')
    button.disabled = true
    const res = await api('POST', HR_ENDPOINTS.leaves, body)
    button.disabled = false

    if (!res.success) { toast(res.error || 'Could not add leave.', 'err'); return }
    const skipped = res.data.skipped.length
    toast(`Added ${res.data.created} leave day(s)${skipped ? `, skipped ${skipped}` : ''}.`)
    bootstrap.Modal.getOrCreateInstance(el('leaveModal')).hide()
    await loadLeaves()
    if (el('attUser').value) loadAttendance()
}

async function deleteLeave(id) {
    if (!confirm('Remove this leave?')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.leaves}${id}/`)
    if (!res.success) { toast(res.error || 'Could not remove leave.', 'err'); return }
    toast('Leave removed.')
    await loadLeaves()
    if (el('attUser').value) loadAttendance()
}

/* ── Universal leaves ────────────────────────────────────────────────────── */

async function loadHolidays() {
    const res = await api('GET', HR_ENDPOINTS.universalLeaves)
    if (!res.success) {
        toast(res.error || 'Could not load universal leaves.', 'err')
        el('holidaysBody').innerHTML = `<tr><td colspan="4" class="empty-state">Could not load universal leaves.</td></tr>`
        return
    }
    holidays = res.data || []
    if (!holidays.length) {
        el('holidaysBody').innerHTML = `<tr><td colspan="4" class="empty-state">No universal leaves added.</td></tr>`
        return
    }
    el('holidaysBody').innerHTML = holidays.map(h => `
        <tr>
            <td><strong>${fmtDate(h.date)}</strong></td>
            <td>${fmtWeekday(h.date)}</td>
            <td>${esc(h.title)}</td>
            <td><div class="action-buttons"><button class="btn btn-danger" aria-label="Delete holiday" onclick="deleteHoliday(${h.id})"><i class="fas fa-trash"></i></button></div></td>
        </tr>`).join('')
}

function openHolidayModal() {
    el('holidayForm').reset()
    bootstrap.Modal.getOrCreateInstance(el('holidayModal')).show()
}

function syncHolidayDates() {
    const from = el('holidayFrom').value
    if (from && (!el('holidayTo').value || el('holidayTo').value < from)) el('holidayTo').value = from
}

async function saveHoliday() {
    const body = {
        title: el('holidayTitle').value.trim(),
        from_date: el('holidayFrom').value,
        to_date: el('holidayTo').value || el('holidayFrom').value,
    }
    if (!body.title) { toast('Title is required.', 'err'); return }
    if (!body.from_date) { toast('Choose the date.', 'err'); return }

    const button = el('holidaySaveBtn')
    button.disabled = true
    const res = await api('POST', HR_ENDPOINTS.universalLeaves, body)
    button.disabled = false

    if (!res.success) { toast(res.error || 'Could not add holiday.', 'err'); return }
    toast(`Added ${res.data.created} holiday day(s).`)
    bootstrap.Modal.getOrCreateInstance(el('holidayModal')).hide()
    await loadHolidays()
    if (el('attUser').value) loadAttendance()
}

async function deleteHoliday(id) {
    if (!confirm('Remove this universal leave?')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.universalLeaves}${id}/`)
    if (!res.success) { toast(res.error || 'Could not remove holiday.', 'err'); return }
    toast('Universal leave removed.')
    await loadHolidays()
    if (el('attUser').value) loadAttendance()
}
