/* HR page: employees, attendance, leaves, universal leaves.
   Entry point: initHR(csrf, endpoints) — called from templates/hr.html */

let HR_CSRF = ''
let HR_ENDPOINTS = {}

let employees = []
let attendanceData = null
let leaves = []
let holidays = []
let applications = []
let quotas = []

let empSort = { key: 'user_name', dir: 'asc' }
let attSort = 'date_asc'
let leaveSort = { key: 'date', dir: 'desc' }

const DOC_FIELDS = ['photo', 'aadhar_file', 'pan_file', 'bank_proof_file']
const TEXT_FIELDS = [
    'full_name', 'joining_date', 'department', 'position', 'reporting_to',
    'current_address', 'permanent_address', 'personal_mobile',
    'aadhar_number', 'pan_number',
    'bank_name', 'bank_account_no', 'bank_branch', 'bank_ifsc',
    'office_mobile', 'device_details', 'imei_1', 'imei_2', 'sim_card_in_name_of',
    'marital_status', 'date_of_birth', 'anniversary_date', 'blood_group',
    'mother_name', 'father_name', 'spouse_name',
]
const SALARY_FIELDS = ['basic_pay', 'da', 'hra', 'lta', 'epf', 'gratuity', 'esic']
const MARITAL_LABELS = { single: 'Single', married: 'Married', divorced: 'Divorced', widowed: 'Widowed' }
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

function fmtMoney(value) {
    const n = Number(value || 0)
    return '\u20B9' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function canEditEmployee(emp) {
    return !emp.is_exited || window.HR_IS_ADMIN === true
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
    el('attDate').value = toISODate(today)
    el('attFrom').value = toISODate(new Date(today.getFullYear(), today.getMonth(), 1))
    el('attTo').value = toISODate(today)
    el('attSort').value = attSort

    setSortIcons('th[data-sort]', 'data-sort', empSort.key, empSort.dir)
    setSortIcons('th[data-leave-sort]', 'data-leave-sort', leaveSort.key, leaveSort.dir)
    setSortIcons('th[data-att-sort]', 'data-att-sort', 'date', 'asc')

    el('payMonth').value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
    el('payPaidOn').value = toISODate(today)
    el('reimbDate').value = toISODate(today)

    await Promise.all([
        loadEmployees(), loadLeaves(), loadHolidays(), loadApplications(), loadQuotas(), loadAttendance(),
        loadPayroll(), loadReimbursements(),
    ])
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
    const appFilterValue = keep('appUserFilter')
    el('attUser').innerHTML = `<option value="">All employees</option>${options}`
    el('leaveUserFilter').innerHTML = `<option value="">All employees</option>${options}`
    el('appUserFilter').innerHTML = `<option value="">All employees</option>${options}`
    el('leaveUser').innerHTML = `<option value="">Select employee</option>${options}`
    el('attUser').value = attValue
    el('leaveUserFilter').value = leaveFilterValue
    el('appUserFilter').value = appFilterValue
    el('leaveUser').value = leaveValue

    const departments = [...new Set(employees.map(e => (e.department || '').trim()).filter(Boolean))].sort()
    const deptValue = el('empDept').value
    el('empDept').innerHTML = `<option value="">All</option>${departments.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('')}`
    el('empDept').value = deptValue
    el('deptList').innerHTML = departments.map(d => `<option value="${esc(d)}"></option>`).join('')

    const reimbFilter = el('reimbUser').value
    el('reimbUser').innerHTML = `<option value="">All employees</option>${options}`
    el('reimbUser').value = reimbFilter
    const activeOptions = sorted.filter(e => !e.is_exited)
        .map(e => `<option value="${e.user}">${esc(e.user_name)} (${esc(e.user_code)})</option>`).join('')
    const reimbFormValue = el('reimbFormUser').value
    el('reimbFormUser').innerHTML = `<option value="">Select employee</option>${activeOptions}`
    el('reimbFormUser').value = reimbFormValue
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
        const exited = e.is_exited
            ? `<span class="pill pill-exited" title="Last working day ${esc(e.last_working_day || '')}">Exited</span> `
            : ''
        const profile = exited + (e.is_complete
            ? `<span class="pill pill-complete">Complete</span>`
            : `<span class="pill pill-incomplete" title="Missing: ${esc(e.missing_fields.join(', '))}">${e.missing_fields.length} missing</span>`)
        return `
        <tr${e.is_exited ? ' class="row-exited"' : ''}>
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
    if (edit && canEditEmployee(emp)) showEmployeeForm()
    else {
        showEmployeeView()
        if (edit) toast('This employee has exited. Only an admin can change their records.', 'err')
    }
    bootstrap.Modal.getOrCreateInstance(el('employeeModal')).show()
}

function syncEmployeeFooter(emp, editing) {
    const admin = window.HR_IS_ADMIN === true
    el('employeeEditBtn').style.display = !editing && canEditEmployee(emp) ? '' : 'none'
    el('employeeSaveBtn').style.display = editing ? '' : 'none'
    el('employeeExitBtn').style.display = !editing && !emp.is_exited ? '' : 'none'
    el('employeeReactivateBtn').style.display = !editing && emp.is_exited && admin ? '' : 'none'
}

function showEmployeeView() {
    const emp = currentEmployee()
    el('employeeViewBody').style.display = ''
    el('employeeForm').style.display = 'none'
    if (emp) syncEmployeeFooter(emp, false)
}

function showEmployeeForm() {
    const emp = currentEmployee()
    if (!emp) return
    if (!canEditEmployee(emp)) {
        toast('This employee has exited. Only an admin can change their records.', 'err')
        return
    }
    fillEmployeeForm(emp)
    el('employeeViewBody').style.display = 'none'
    el('employeeForm').style.display = ''
    syncEmployeeFooter(emp, true)
}

function syncMaritalFields() {
    const status = el('f_marital_status').value
    const married = status === 'married'
    el('spouseWrap').style.display = married || status === '' ? '' : 'none'
    el('f_anniversary_date').disabled = !married && status !== ''
    if (!married && status !== '') {
        el('f_anniversary_date').value = ''
        el('f_spouse_name').value = ''
    }
}

function syncTdsField() {
    const on = el('f_tds_applicable').checked
    el('tdsAmountWrap').style.display = on ? '' : 'none'
    if (!on) el('f_tds_amount').value = ''
}

function updateSalaryTotal() {
    const total = SALARY_FIELDS.reduce((sum, f) => sum + (parseFloat(el(`f_${f}`).value) || 0), 0)
    el('f_total_salary').value = fmtMoney(total)
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

    const exitInfo = emp.is_exited ? `
        <div class="alert alert-danger py-2" style="font-size:0.85rem;">
            <div class="fw-semibold mb-1"><i class="fas fa-right-from-bracket me-1"></i>Exited &middot; login disabled</div>
            <div>Last working day: <strong>${fmtDate(emp.last_working_day)}</strong> &middot; Intent: <strong>${esc(emp.exit_intent_display)}</strong>${emp.exited_by_name ? ` &middot; Marked by ${esc(emp.exited_by_name)}` : ''}</div>
            ${emp.exit_remarks ? `<div class="mt-1">Remarks: ${esc(emp.exit_remarks)}</div>` : ''}
            ${window.HR_IS_ADMIN ? '' : '<div class="mt-1">Only an admin can change this employee\'s records.</div>'}
        </div>` : ''

    const salaryRows = [
        ['Basic Pay', emp.basic_pay], ['DA', emp.da], ['HRA', emp.hra], ['LTA', emp.lta],
        ['EPF', emp.epf], ['Gratuity', emp.gratuity], ['ESIC', emp.esic],
    ].map(([label, value]) => detailItem(label, fmtMoney(value))).join('')

    el('employeeViewBody').innerHTML = `
        ${exitInfo}
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
            <div class="form-section-title">Personal &amp; Family Details</div>
            <div class="detail-grid">
                ${detailItem('Marital Status', esc(MARITAL_LABELS[emp.marital_status] || emp.marital_status))}
                ${detailItem('Date of Birth', emp.date_of_birth ? fmtDate(emp.date_of_birth) : '')}
                ${detailItem('Date of Anniversary', emp.anniversary_date ? fmtDate(emp.anniversary_date) : '')}
                ${detailItem('Blood Group', esc(emp.blood_group))}
                ${detailItem('Mother Name', esc(emp.mother_name))}
                ${detailItem('Father Name', esc(emp.father_name))}
                ${detailItem('Spouse Name', esc(emp.spouse_name))}
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
            <div class="form-section-title">Salary Structure (per month)</div>
            <div class="detail-grid">
                ${salaryRows}
                ${detailItem('Total Salary', `<strong>${fmtMoney(emp.total_salary)}</strong>`)}
                ${detailItem('Per-day rate (Total / 30)', fmtMoney((emp.total_salary || 0) / 30))}
                ${detailItem('TDS Applicable', emp.tds_applicable ? 'Yes' : 'No')}
                ${emp.tds_applicable ? detailItem('TDS per month', fmtMoney(emp.tds_amount)) : ''}
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

    SALARY_FIELDS.forEach(field => {
        const value = Number(emp[field] || 0)
        el(`f_${field}`).value = value ? value : ''
    })
    el('f_tds_applicable').checked = !!emp.tds_applicable
    el('f_tds_amount').value = Number(emp.tds_amount || 0) || ''
    syncTdsField()
    updateSalaryTotal()
    syncMaritalFields()

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
    SALARY_FIELDS.forEach(field => form.append(field, el(`f_${field}`).value.trim() || '0'))
    const tdsOn = el('f_tds_applicable').checked
    form.append('tds_applicable', tdsOn ? 'true' : 'false')
    form.append('tds_amount', tdsOn ? (el('f_tds_amount').value.trim() || '0') : '0')
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

/* ── Payroll ─────────────────────────────────────────────────────────────── */

const COMPONENT_LABELS = {
    basic_pay: 'Basic Pay', da: 'DA', hra: 'HRA', lta: 'LTA', epf: 'EPF', gratuity: 'Gratuity', esic: 'ESIC',
}
let payCtx = null

function payPeriod() {
    const [year, month] = (el('payMonth').value || '').split('-').map(Number)
    return { year, month }
}

async function loadPayroll() {
    const { year, month } = payPeriod()
    if (!year || !month) { el('payrollBody').innerHTML = ''; return }
    const res = await api('GET', `${HR_ENDPOINTS.payroll}?year=${year}&month=${month}`)
    if (!res.success) {
        el('paySummary').textContent = res.error || 'Could not load payroll.'
        return
    }
    const s = res.summary || {}
    el('paySummary').textContent =
        `${res.month_label}: ${s.generated || 0} of ${s.employees || 0} generated, ${s.paid || 0} paid, net payable ${fmtMoney(s.net_total)}`

    el('payrollBody').innerHTML = res.data.length ? res.data.map(r => {
        const p = r.payroll
        const status = p
            ? `<span class="pill ${p.status === 'paid' ? 'pill-complete' : 'pill-incomplete'}">${esc(p.status_display)}${p.paid_on ? ' &middot; ' + fmtDate(p.paid_on) : ''}</span>`
            : '<span class="text-muted">Not generated</span>'
        const salary = r.salary_set
            ? fmtMoney(r.total_salary)
            : '<span class="text-danger" title="Set the salary structure in the employee details">Not set</span>'
        const pending = r.pending_reimbursements
            ? `${r.pending_reimbursements} &middot; ${fmtMoney(r.pending_reimbursement_total)}`
            : '<span class="text-muted">None</span>'
        return `
        <tr${r.is_exited ? ' class="row-exited"' : ''}>
            <td><div class="fw-semibold">${esc(r.name)}${r.is_exited ? ' <span class="pill pill-exited">Exited</span>' : ''}</div>
                <div class="text-muted" style="font-size:0.78rem;">${esc(r.user_code)} &middot; ${esc(r.department || '-')}</div></td>
            <td>${salary}</td>
            <td>${pending}</td>
            <td>${status}</td>
            <td>${p ? '<strong>' + fmtMoney(p.net_payable) + '</strong>' : '-'}</td>
            <td class="text-nowrap">
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="openPayroll(${r.user_id})">
                    <i class="fas fa-${p ? 'eye' : 'calculator'} me-1"></i>${p ? 'Review' : 'Generate'}
                </button>
                ${p ? `<a class="btn btn-sm btn-outline-secondary ms-1" href="${HR_ENDPOINTS.payroll}${p.id}/slip/" aria-label="Download salary slip"><i class="fas fa-file-pdf"></i></a>` : ''}
            </td>
        </tr>`
    }).join('') : '<tr><td colspan="6" class="text-center text-muted py-4">No employees for this month.</td></tr>'
}

function readPayrollForm() {
    if (!payCtx) return
    const adj = el('payAdjustment'), adjNote = el('payAdjustmentNote'), notes = el('payNotes')
    if (adj) payCtx.adjustment = adj.value.trim()
    if (adjNote) payCtx.adjustmentNote = adjNote.value
    if (notes) payCtx.notes = notes.value
}

function payrollBody(initial) {
    const body = { user: payCtx.userId, year: payCtx.year, month: payCtx.month }
    if (!initial) {
        body.deduct = payCtx.deduct
        body.reimbursement_ids = payCtx.included
        body.adjustment = payCtx.adjustment === '' ? '0' : payCtx.adjustment
        body.adjustment_note = payCtx.adjustmentNote
        body.notes = payCtx.notes
    }
    return body
}

async function refreshPayrollPreview(initial = false) {
    readPayrollForm()
    const res = await api('POST', `${HR_ENDPOINTS.payroll}preview/`, payrollBody(initial))
    if (!res.success) {
        toast(res.error || 'Could not calculate payroll.', 'err')
        if (initial) bootstrap.Modal.getOrCreateInstance(el('payrollModal')).hide()
        return false
    }
    const calc = res.data
    payCtx.calc = calc
    payCtx.existing = calc.existing
    if (initial) {
        payCtx.deduct = {}
        calc.lines.forEach(l => { if (l.leave_id) payCtx.deduct[l.leave_id] = l.deduct })
        payCtx.included = calc.reimbursements.filter(r => r.included).map(r => r.id)
        payCtx.adjustment = calc.adjustment ? String(calc.adjustment) : ''
        payCtx.adjustmentNote = calc.existing ? calc.existing.adjustment_note : ''
        payCtx.notes = calc.existing ? calc.existing.notes : ''
    }
    renderPayrollModal()
    return true
}

async function openPayroll(userId) {
    const { year, month } = payPeriod()
    if (!year || !month) { toast('Choose a month first.', 'err'); return }
    const emp = employees.find(e => e.user === userId)
    payCtx = { userId, year, month, deduct: {}, included: [], adjustment: '', adjustmentNote: '', notes: '', calc: null, existing: null }
    el('payrollModalTitle').textContent = emp ? (emp.full_name || emp.user_name) : 'Payroll'
    el('payrollModalSub').textContent = new Date(year, month - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
    el('payrollModalBody').innerHTML = '<div class="text-center text-muted py-5">Calculating...</div>'
    el('payDeleteBtn').style.display = 'none'
    el('paySlipBtn').style.display = 'none'
    el('payPaidWrap').style.display = 'none'
    el('payReopenBtn').style.display = 'none'
    el('payGenerateBtn').style.display = 'none'
    bootstrap.Modal.getOrCreateInstance(el('payrollModal')).show()
    await refreshPayrollPreview(true)
}

function renderPayrollModal() {
    const c = payCtx.calc
    const existing = payCtx.existing
    const paid = !!existing && existing.status === 'paid'
    const lock = paid ? 'disabled' : ''

    const components = Object.entries(c.components).map(([key, value]) =>
        `<tr><td>${esc(COMPONENT_LABELS[key] || key)}</td><td class="text-end">${fmtMoney(value)}</td></tr>`).join('')

    const lines = c.lines.length ? c.lines.map(l => `
        <tr>
            <td>${fmtDate(l.date)}</td>
            <td>${esc(l.leave_type_display)}</td>
            <td>${l.days === 0.5 ? 'Half day' : 'Full day'}</td>
            <td>${l.is_extra ? '<span class="pill pill-exited">Extra</span>' : '<span class="pill pill-complete">Within quota</span>'}</td>
            <td class="text-muted">${esc(l.reason || '')}</td>
            <td class="text-end">${fmtMoney(l.amount)}</td>
            <td class="text-center">
                <input type="checkbox" class="form-check-input" data-leave="${l.leave_id || ''}" ${l.deduct ? 'checked' : ''}
                    ${lock || !l.leave_id ? 'disabled' : ''} aria-label="Deduct ${esc(fmtDate(l.date))} from salary"
                    onchange="toggleDeduct(${l.leave_id || 'null'}, this.checked)">
            </td>
        </tr>`).join('')
        : '<tr><td colspan="7" class="text-center text-muted py-3">No leaves this month.</td></tr>'

    const reimbs = c.reimbursements.length ? c.reimbursements.map(r => `
        <tr>
            <td>${fmtDate(r.expense_date)}</td>
            <td>${esc(r.description)}</td>
            <td>${r.receipt_url ? `<a href="${esc(r.receipt_url)}" target="_blank" rel="noopener"><i class="fas fa-image me-1"></i>Receipt</a>` : '-'}</td>
            <td class="text-end">${fmtMoney(r.amount)}</td>
            <td class="text-center">
                <input type="checkbox" class="form-check-input" ${r.included ? 'checked' : ''} ${lock}
                    aria-label="Pay ${esc(r.description)}" onchange="toggleReimbursement(${r.id}, this.checked)">
            </td>
        </tr>`).join('')
        : '<tr><td colspan="5" class="text-center text-muted py-3">No pending reimbursements.</td></tr>'

    el('payrollModalBody').innerHTML = `
        ${paid ? `<div class="alert alert-success py-2" style="font-size:0.85rem;">This payroll is marked paid and locked${window.HR_IS_ADMIN ? '. Reopen it to make changes.' : '. Only an admin can reopen it.'}</div>` : ''}
        ${c.total_salary > 0 ? '' : '<div class="alert alert-warning py-2" style="font-size:0.85rem;">No salary is set for this employee. Add it in the employee details first.</div>'}
        <div class="row g-4">
            <div class="col-lg-5">
                <div class="form-section-title">Salary Structure</div>
                <table class="table table-sm mb-3"><tbody>
                    ${components}
                    <tr class="fw-semibold"><td>Total Salary</td><td class="text-end">${fmtMoney(c.total_salary)}</td></tr>
                    <tr class="text-muted"><td>Per-day rate (Total / 30)</td><td class="text-end">${fmtMoney(c.per_day_rate)}</td></tr>
                </tbody></table>

                <div class="form-section-title">Payable</div>
                <table class="table table-sm mb-3"><tbody>
                    <tr><td>Total Salary</td><td class="text-end">${fmtMoney(c.total_salary)}</td></tr>
                    <tr><td>Less: Leave (${c.leave_days_deducted} day${c.leave_days_deducted === 1 ? '' : 's'} &times; ${fmtMoney(c.per_day_rate)})</td>
                        <td class="text-end text-danger">&minus; ${fmtMoney(c.leave_deduction)}</td></tr>
                    <tr><td>Less: TDS${c.tds_applicable ? '' : ' (not applicable)'}</td>
                        <td class="text-end text-danger">&minus; ${fmtMoney(c.tds_deducted)}</td></tr>
                    <tr class="fw-semibold"><td>Salary for the Month</td><td class="text-end">${fmtMoney(c.salary_for_month)}</td></tr>
                    <tr><td>Add: Reimbursements</td><td class="text-end">+ ${fmtMoney(c.reimbursement_total)}</td></tr>
                    <tr><td>Adjustment</td><td class="text-end">${c.adjustment >= 0 ? '+' : '&minus;'} ${fmtMoney(Math.abs(c.adjustment))}</td></tr>
                    <tr class="fw-bold table-active"><td>Net Salary Payable</td><td class="text-end">${fmtMoney(c.net_payable)}</td></tr>
                </tbody></table>

                <div class="row g-2">
                    <div class="col-5">
                        <label class="form-label" for="payAdjustment">Adjustment</label>
                        <input type="number" step="0.01" class="form-control" id="payAdjustment" value="${esc(payCtx.adjustment)}"
                            placeholder="0.00" ${lock} onchange="refreshPayrollPreview()">
                    </div>
                    <div class="col-7">
                        <label class="form-label" for="payAdjustmentNote">Adjustment note</label>
                        <input type="text" class="form-control" id="payAdjustmentNote" maxlength="200" value="${esc(payCtx.adjustmentNote)}" ${lock}>
                    </div>
                    <div class="col-12">
                        <label class="form-label" for="payNotes">Remarks on slip</label>
                        <textarea class="form-control" id="payNotes" rows="2" maxlength="500" ${lock}>${esc(payCtx.notes)}</textarea>
                    </div>
                </div>
            </div>
            <div class="col-lg-7">
                <div class="form-section-title">Leaves this month</div>
                <p class="text-muted" style="font-size:0.78rem;">Tick a leave to cut one day of salary for it. Untick it to waive the deduction. Extra leaves (beyond the monthly quota) are ticked by default.</p>
                <div class="table-responsive mb-3">
                    <table class="table table-sm align-middle mb-0">
                        <thead><tr><th>Date</th><th>Type</th><th>Day</th><th>Quota</th><th>Reason</th><th class="text-end">Amount</th><th class="text-center">Deduct</th></tr></thead>
                        <tbody>${lines}</tbody>
                    </table>
                </div>
                <div class="form-section-title">Reimbursements</div>
                <p class="text-muted" style="font-size:0.78rem;">Only ticked reimbursements are paid in this payroll. Unticked ones stay pending for a later month.</p>
                <div class="table-responsive">
                    <table class="table table-sm align-middle mb-0">
                        <thead><tr><th>Date</th><th>Description</th><th>Receipt</th><th class="text-end">Amount</th><th class="text-center">Pay</th></tr></thead>
                        <tbody>${reimbs}</tbody>
                    </table>
                </div>
            </div>
        </div>`

    const admin = window.HR_IS_ADMIN === true
    el('payGenerateBtn').style.display = paid ? 'none' : ''
    el('payGenerateBtn').innerHTML = `<i class="fas fa-calculator me-1"></i>${existing ? 'Update Payroll' : 'Generate Payroll'}`
    el('paySlipBtn').style.display = existing ? '' : 'none'
    el('payDeleteBtn').style.display = existing && !paid ? '' : 'none'
    el('payPaidWrap').style.display = existing && !paid ? '' : 'none'
    el('payReopenBtn').style.display = paid && admin ? '' : 'none'
}

function toggleDeduct(leaveId, checked) {
    if (!leaveId) return
    payCtx.deduct[leaveId] = checked
    refreshPayrollPreview()
}

function toggleReimbursement(id, checked) {
    const set = new Set(payCtx.included)
    if (checked) set.add(id)
    else set.delete(id)
    payCtx.included = [...set]
    refreshPayrollPreview()
}

async function generatePayroll() {
    readPayrollForm()
    const button = el('payGenerateBtn')
    button.disabled = true
    const res = await api('POST', `${HR_ENDPOINTS.payroll}generate/`, payrollBody(false))
    button.disabled = false
    if (!res.success) { toast(res.error || 'Could not generate payroll.', 'err'); return }
    toast('Payroll saved.')
    await Promise.all([refreshPayrollPreview(), loadPayroll(), loadReimbursements()])
}

function downloadSlip() {
    if (!payCtx || !payCtx.existing) return
    window.location.href = `${HR_ENDPOINTS.payroll}${payCtx.existing.id}/slip/`
}

async function markPayrollPaid() {
    if (!payCtx || !payCtx.existing) return
    const paidOn = el('payPaidOn').value
    if (!paidOn) { toast('Choose the paid date.', 'err'); return }
    const res = await api('POST', `${HR_ENDPOINTS.payroll}${payCtx.existing.id}/mark_paid/`, { paid_on: paidOn })
    if (!res.success) { toast(res.error || 'Could not mark paid.', 'err'); return }
    toast('Payroll marked as paid.')
    await Promise.all([refreshPayrollPreview(), loadPayroll(), loadReimbursements()])
}

async function reopenPayroll() {
    if (!payCtx || !payCtx.existing) return
    if (!confirm('Reopen this paid payroll so it can be corrected?')) return
    const res = await api('POST', `${HR_ENDPOINTS.payroll}${payCtx.existing.id}/reopen/`)
    if (!res.success) { toast(res.error || 'Could not reopen.', 'err'); return }
    toast('Payroll reopened.')
    await Promise.all([refreshPayrollPreview(), loadPayroll()])
}

async function deletePayroll() {
    if (!payCtx || !payCtx.existing) return
    if (!confirm('Delete this payroll? Its reimbursements become pending again.')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.payroll}${payCtx.existing.id}/`)
    if (!res.success) { toast(res.error || 'Could not delete payroll.', 'err'); return }
    toast('Payroll deleted.')
    bootstrap.Modal.getOrCreateInstance(el('payrollModal')).hide()
    await Promise.all([loadPayroll(), loadReimbursements()])
}

/* ── Reimbursements ──────────────────────────────────────────────────────── */

async function loadReimbursements() {
    const params = new URLSearchParams({ status: el('reimbStatus').value })
    if (el('reimbUser').value) params.set('user', el('reimbUser').value)
    const res = await api('GET', `${HR_ENDPOINTS.reimbursements}?${params}`)
    if (!res.success) { toast(res.error || 'Could not load reimbursements.', 'err'); return }

    el('reimbBody').innerHTML = res.data.length ? res.data.map(r => `
        <tr>
            <td>${fmtDate(r.expense_date)}</td>
            <td><div class="fw-semibold">${esc(r.user_name)}</div><div class="text-muted" style="font-size:0.78rem;">${esc(r.user_code)}</div></td>
            <td>${esc(r.description)}</td>
            <td><strong>${fmtMoney(r.amount)}</strong></td>
            <td>${r.receipt_url ? `<a href="${esc(r.receipt_url)}" target="_blank" rel="noopener"><i class="fas fa-image me-1"></i>View</a>` : '-'}</td>
            <td>${r.payroll
                ? `<span class="pill ${r.is_paid ? 'pill-complete' : 'pill-incomplete'}">${r.is_paid ? 'Paid' : 'In payroll'} ${esc(r.payroll_period || '')}</span>`
                : '<span class="pill pill-incomplete">Pending</span>'}</td>
            <td>${r.payroll ? '' : `<button type="button" class="btn btn-sm btn-outline-danger" aria-label="Delete reimbursement" onclick="deleteReimbursement(${r.id})"><i class="fas fa-trash"></i></button>`}</td>
        </tr>`).join('')
        : '<tr><td colspan="7" class="text-center text-muted py-4">No reimbursements found.</td></tr>'
}

function openReimbursementModal() {
    el('reimbForm').reset()
    el('reimbDate').value = toISODate(new Date())
    if (el('reimbUser').value) el('reimbFormUser').value = el('reimbUser').value
    bootstrap.Modal.getOrCreateInstance(el('reimbModal')).show()
}

async function saveReimbursement() {
    const user = el('reimbFormUser').value
    const amount = el('reimbAmount').value
    const description = el('reimbDesc').value.trim()
    const file = el('reimbReceipt').files[0]
    if (!user) { toast('Select an employee.', 'err'); return }
    if (!el('reimbDate').value) { toast('Choose the expense date.', 'err'); return }
    if (!amount || Number(amount) <= 0) { toast('Enter a valid amount.', 'err'); return }
    if (!description) { toast('Add a description.', 'err'); return }
    if (!file) { toast('Attach the receipt photo.', 'err'); return }

    const form = new FormData()
    form.append('user', user)
    form.append('expense_date', el('reimbDate').value)
    form.append('amount', amount)
    form.append('description', description)
    form.append('receipt', file)

    const button = el('reimbSaveBtn')
    button.disabled = true
    const res = await api('POST', HR_ENDPOINTS.reimbursements, form, true)
    button.disabled = false
    if (!res.success) { toast(res.error || 'Could not save the reimbursement.', 'err'); return }
    bootstrap.Modal.getOrCreateInstance(el('reimbModal')).hide()
    toast('Reimbursement added.')
    await Promise.all([loadReimbursements(), loadPayroll()])
}

async function deleteReimbursement(id) {
    if (!confirm('Delete this reimbursement?')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.reimbursements}${id}/`)
    if (!res.success) { toast(res.error || 'Could not delete.', 'err'); return }
    toast('Reimbursement deleted.')
    await Promise.all([loadReimbursements(), loadPayroll()])
}

/* ── Exit ────────────────────────────────────────────────────────────────── */

function openExitModal() {
    const emp = currentEmployee()
    if (!emp) return
    el('exitWarnName').textContent = emp.full_name || emp.user_name
    el('exitLastDay').value = toISODate(new Date())
    el('exitIntent').value = ''
    el('exitRemarks').value = ''
    bootstrap.Modal.getOrCreateInstance(el('exitModal')).show()
}

async function confirmExit() {
    const emp = currentEmployee()
    if (!emp) return
    const lastDay = el('exitLastDay').value
    const intent = el('exitIntent').value
    const remarks = el('exitRemarks').value.trim()
    if (!lastDay) { toast('Choose the last working day.', 'err'); return }
    if (!intent) { toast('Choose the exit intent.', 'err'); return }
    if (intent === 'other' && !remarks) { toast('Add remarks when the exit intent is Other.', 'err'); return }

    const button = el('exitConfirmBtn')
    button.disabled = true
    const res = await api('POST', `${HR_ENDPOINTS.employees}${emp.user}/exit/`, {
        last_working_day: lastDay, exit_intent: intent, remarks,
    })
    button.disabled = false

    if (!res.success) { toast(res.error || 'Could not mark the exit.', 'err'); return }
    applyEmployeeUpdate(res.data)
    bootstrap.Modal.getOrCreateInstance(el('exitModal')).hide()
    toast('Employee marked as exited and login disabled.')
}

async function reactivateEmployee() {
    const emp = currentEmployee()
    if (!emp) return
    if (!confirm(`Reactivate ${emp.full_name || emp.user_name}? They will be able to sign in again.`)) return
    const res = await api('POST', `${HR_ENDPOINTS.employees}${emp.user}/reactivate/`)
    if (!res.success) { toast(res.error || 'Could not reactivate the employee.', 'err'); return }
    applyEmployeeUpdate(res.data)
    toast('Employee reactivated.')
}

function applyEmployeeUpdate(data) {
    const index = employees.findIndex(e => e.user === data.user)
    if (index >= 0) employees[index] = data
    populateEmployeeSelects()
    renderEmployees()
    renderEmployeeView(data)
    el('employeeModalTitle').textContent = data.full_name || data.user_name
    showEmployeeView()
}

/* ── Attendance ──────────────────────────────────────────────────────────── */

function openAttendanceFor(userPk) {
    el('attUser').value = userPk
    bootstrap.Tab.getOrCreateInstance(document.querySelector('[data-bs-target="#paneAttendance"]')).show()
    onAttendanceUserChange()
}

// 'day' = every employee on one date (default); 'user' = one employee across a date range.
function attendanceMode() {
    return el('attUser').value ? 'user' : 'day'
}

function applyAttendanceMode() {
    const day = attendanceMode() === 'day'
    el('attDateGroup').style.display = day ? '' : 'none'
    el('attFromGroup').style.display = day ? 'none' : ''
    el('attToGroup').style.display = day ? 'none' : ''
    el('attFirstTh').textContent = day ? 'Employee' : 'Date'
    el('attDayTh').textContent = day ? 'Department' : 'Day'

    const options = el('attSort').options
    for (const option of options) {
        if (option.value === 'date_desc') option.textContent = day ? 'Name: Z to A' : 'Date: newest first'
        if (option.value === 'date_asc') option.textContent = day ? 'Name: A to Z' : 'Date: oldest first'
    }
}

function onAttendanceUserChange() {
    attSort = attendanceMode() === 'day' ? 'date_asc' : 'date_desc'
    el('attSort').value = attSort
    applyAttendanceMode()
    loadAttendance()
}

function setAttendanceToday() {
    el('attDate').value = toISODate(new Date())
    loadAttendance()
}

async function loadAttendance() {
    applyAttendanceMode()
    const day = attendanceMode() === 'day'
    const params = {}
    if (day) {
        params.user_id = 'all'
        if (el('attDate').value) params.date = el('attDate').value
    } else {
        params.user_id = el('attUser').value
        if (el('attFrom').value) params.from_date = el('attFrom').value
        if (el('attTo').value) params.to_date = el('attTo').value
    }

    el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state">Loading...</td></tr>`
    const res = await api('GET', `${HR_ENDPOINTS.attendance}?${toQueryString(params)}`)
    if (!res.success) {
        attendanceData = null
        el('attKpis').style.display = 'none'
        el('attDayKpis').style.display = 'none'
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
    upcoming:       ['Upcoming', 'pill-pending'],
    not_joined:     ['Not joined', 'pill-off'],
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
    const day = attendanceData.mode === 'day'
    const { rows } = attendanceData
    const filter = el('attStatus').value
    const [key, dir] = attSort.split('_')

    const value = r => key === 'date' ? (day ? r.user.name : r.date) : key === 'in' ? r.check_in : r.worked_minutes
    const visible = rows
        .filter(r => matchesAttendanceFilter(r, filter))
        .sort((a, b) => compare(value(a), value(b), dir))

    el('attKpis').style.display = day ? 'none' : ''
    el('attDayKpis').style.display = day ? '' : 'none'
    if (day) {
        const c = attendanceData.counts
        el('dayPresent').textContent = c.present
        el('dayHalf').textContent = c.half_day
        el('dayLeave').textContent = c.on_leave
        el('dayAbsent').textContent = c.absent
        el('dayNotIn').textContent = c.not_checked_in
        el('dayForgot').textContent = c.forgot_checkout
    } else {
        const s = attendanceData.summary
        el('kpiPresent').textContent = s.present
        el('kpiHalf').textContent = s.half_day
        el('kpiAbsent').textContent = s.absent
        el('kpiLeave').textContent = s.leave_days
        el('kpiForgot').textContent = s.forgot_checkout
        el('kpiHours').textContent = fmtMinutes(s.worked_minutes)
    }
    setSortIcons('th[data-att-sort]', 'data-att-sort', key, dir)

    if (!visible.length) {
        el('attendanceBody').innerHTML = `<tr><td colspan="7" class="empty-state">${day ? 'No employees match the filter.' : 'No days match the filter.'}</td></tr>`
        return
    }

    el('attendanceBody').innerHTML = visible.map(r => {
        const [label, cls] = ATT_STATUS[r.status] || [r.status, 'pill-pending']
        const muted = r.status === 'weekly_off' || r.status === 'holiday'
        const checkOut = r.check_out
            ? fmtTime(r.check_out)
            : (r.forgot_checkout ? '<span class="forgot-flag">Missing</span>' : '-')
        const firstCell = day
            ? `<div class="emp-name">${esc(r.user.name)}</div><div class="emp-sub">${esc(r.user.user_code)}</div>`
            : `<strong>${fmtDate(r.date)}</strong>`
        const secondCell = day
            ? `${esc(r.user.department) || '-'}${r.user.position ? `<div class="emp-sub">${esc(r.user.position)}</div>` : ''}`
            : esc(r.weekday)
        return `
        <tr class="${r.forgot_checkout ? 'row-forgot' : ''} ${muted ? 'row-muted' : ''}">
            <td>${firstCell}</td>
            <td>${secondCell}</td>
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
    loadAttendance()
    loadQuotas()
}

async function deleteLeave(id) {
    if (!confirm('Remove this leave?')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.leaves}${id}/`)
    if (!res.success) { toast(res.error || 'Could not remove leave.', 'err'); return }
    toast('Leave removed.')
    await loadLeaves()
    loadAttendance()
    loadQuotas()
}

/* ── Leave applications ──────────────────────────────────────────────────── */

const APPLICATION_STATUS = {
    pending:   'pill-pending',
    approved:  'pill-present',
    rejected:  'pill-absent',
    cancelled: 'pill-off',
}

function fmtRange(from, to) {
    return from === to ? fmtDate(from) : `${fmtDate(from)} - ${fmtDate(to)}`
}

function setPendingBadge(count) {
    const badge = el('pendingBadge')
    badge.textContent = count
    badge.style.display = count ? '' : 'none'
}

async function loadApplications() {
    const params = {}
    if (el('appStatusFilter').value) params.status = el('appStatusFilter').value
    if (el('appUserFilter').value) params.user_id = el('appUserFilter').value

    const res = await api('GET', `${HR_ENDPOINTS.applications}?${toQueryString(params)}`)
    if (!res.success) {
        toast(res.error || 'Could not load leave applications.', 'err')
        el('applicationsBody').innerHTML = `<tr><td colspan="8" class="empty-state">Could not load leave applications.</td></tr>`
        return
    }
    applications = res.data || []
    setPendingBadge(res.pending_count || 0)
    renderApplications()
}

function renderApplications() {
    if (!applications.length) {
        const pendingOnly = el('appStatusFilter').value === 'pending'
        el('applicationsBody').innerHTML = `<tr><td colspan="8" class="empty-state">${pendingOnly ? 'No pending leave applications.' : 'No leave applications found.'}</td></tr>`
        return
    }
    el('applicationsBody').innerHTML = applications.map(a => {
        const pending = a.status === 'pending'
        const left = a.left_after_approval
        const leftCell = pending && left !== null
            ? `${left} ${esc(a.leave_type_display.toLowerCase())} left this month`
            : '-'
        const reviewed = a.reviewed_by_name
            ? `<div class="emp-sub">by ${esc(a.reviewed_by_name)}${a.review_note ? `: ${esc(a.review_note)}` : ''}</div>`
            : ''
        const actions = pending
            ? `<div class="action-buttons">
                    <button class="btn btn-success" aria-label="Approve application" onclick="reviewApplication(${a.id}, 'approve')"><i class="fas fa-check"></i></button>
                    <button class="btn btn-danger" aria-label="Reject application" onclick="reviewApplication(${a.id}, 'reject')"><i class="fas fa-xmark"></i></button>
               </div>`
            : '-'
        return `
        <tr>
            <td><div class="emp-name">${esc(a.user_name)}</div><div class="emp-sub">${esc(a.user_code)}</div></td>
            <td><strong>${fmtRange(a.from_date, a.to_date)}</strong><div class="emp-sub">${a.day_type === 'half' ? 'Half day' : 'Full day'}</div></td>
            <td><span class="pill pill-leave">${esc(a.leave_type_display)}</span></td>
            <td>${a.days}</td>
            <td>${esc(a.reason) || '-'}</td>
            <td>${leftCell}</td>
            <td><span class="pill ${APPLICATION_STATUS[a.status] || 'pill-pending'}">${esc(a.status_display)}</span>${reviewed}</td>
            <td>${actions}</td>
        </tr>`
    }).join('')
}

async function reviewApplication(id, decision) {
    let note = ''
    if (decision === 'reject') {
        note = prompt('Reason for rejecting (optional):')
        if (note === null) return
    } else if (!confirm('Approve this leave application?')) {
        return
    }

    const res = await api('POST', `${HR_ENDPOINTS.applications}${id}/${decision}/`, { note: note.trim() })
    if (!res.success) { toast(res.error || 'Could not update the application.', 'err'); return }
    toast(decision === 'approve' ? 'Leave approved.' : 'Leave rejected.')
    await Promise.all([loadApplications(), loadLeaves(), loadAttendance(), loadQuotas()])
}

/* ── Leave quotas ────────────────────────────────────────────────────────── */

async function loadQuotas() {
    const res = await api('GET', HR_ENDPOINTS.quotas)
    if (!res.success) {
        toast(res.error || 'Could not load leave quotas.', 'err')
        el('quotasBody').innerHTML = `<tr><td colspan="5" class="empty-state">Could not load leave quotas.</td></tr>`
        return
    }
    quotas = res.data || []
    el('quotaMonthTh').textContent = `Used in ${res.month_label || 'This Month'}`
    renderQuotas()
}

function renderQuotas() {
    if (!quotas.length) {
        el('quotasBody').innerHTML = `<tr><td colspan="5" class="empty-state">No employees found.</td></tr>`
        return
    }
    el('quotasBody').innerHTML = quotas.map(q => `
        <tr>
            <td><div class="emp-name">${esc(q.name)}</div><div class="emp-sub">${esc(q.user_code)}${q.department ? ' · ' + esc(q.department) : ''}</div></td>
            <td><input type="number" class="form-control" style="max-width:110px;" id="quotaCasual${q.user_id}" min="0" max="31" step="0.5" value="${q.casual_quota}" aria-label="Casual leaves per month for ${esc(q.name)}"></td>
            <td><input type="number" class="form-control" style="max-width:110px;" id="quotaSick${q.user_id}" min="0" max="31" step="0.5" value="${q.sick_quota}" aria-label="Sick leaves per month for ${esc(q.name)}"></td>
            <td>Casual ${q.balance.casual.used} of ${q.balance.casual.quota}<div class="emp-sub">Sick ${q.balance.sick.used} of ${q.balance.sick.quota}</div></td>
            <td><div class="action-buttons"><button class="btn btn-primary" aria-label="Save quota for ${esc(q.name)}" onclick="saveQuota(${q.user_id})"><i class="fas fa-floppy-disk"></i></button></div></td>
        </tr>`).join('')
}

async function saveQuota(userPk) {
    const body = {
        casual: el(`quotaCasual${userPk}`).value,
        sick: el(`quotaSick${userPk}`).value,
    }
    const res = await api('PATCH', `${HR_ENDPOINTS.quotas}${userPk}/`, body)
    if (!res.success) { toast(res.error || 'Could not save leave quota.', 'err'); return }
    toast('Leave quota saved.')
    await loadQuotas()
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
    loadAttendance()
    loadQuotas()
}

async function deleteHoliday(id) {
    if (!confirm('Remove this universal leave?')) return
    const res = await api('DELETE', `${HR_ENDPOINTS.universalLeaves}${id}/`)
    if (!res.success) { toast(res.error || 'Could not remove holiday.', 'err'); return }
    toast('Universal leave removed.')
    await loadHolidays()
    loadAttendance()
    loadQuotas()
}
