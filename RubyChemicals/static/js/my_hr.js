/* My HR page: the signed-in employee's own profile, check in/out, attendance and leaves.
   Entry point: initMyHR(csrf, endpoints) — called from templates/my_hr.html */

let MY_CSRF = ''
let MY_ENDPOINTS = {}

let profileData = null
let leaveData = null
let applyModal = null
let claimModal = null
let backdateLimitDays = 7

const ROLE_LABELS = { accounts: 'Accounts', factory: 'Factory', accountant: 'Accountant', office: 'Office', hr: 'HR', admin: 'Admin' }

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

const APPLICATION_STATUS = {
    pending:   'pill-pending',
    approved:  'pill-approved',
    rejected:  'pill-rejected',
    cancelled: 'pill-cancelled',
}

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

function fmtMoney(value) {
    const n = Number(value || 0)
    return '\u20B9' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function api(method, url, body = null, media = false) {
    try {
        const result = await callApi(method, url, body, MY_CSRF, media)
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

function fmtDays(n) {
    const value = Number(n || 0)
    return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function initials(name) {
    return (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('')
}

function isImage(url) {
    return /\.(png|jpe?g|gif|webp|bmp)(\?|$)/i.test(url || '')
}

function fileLink(url, label) {
    if (!url) return '<span class="text-muted">Not uploaded</span>'
    return `<span class="file-link"><a href="${esc(url)}" target="_blank" rel="noopener"><i class="fas fa-file me-1"></i>${esc(label)}</a></span>`
}

function detailItem(label, value) {
    return `<div class="detail-item"><div class="k">${esc(label)}</div><div class="v">${value || '-'}</div></div>`
}

function statCard(icon, color, value, label, sub = '') {
    return `
        <div class="stat-card">
            <div class="stat-icon" style="color:${color}"><i class="fas ${icon}"></i></div>
            <div class="stat-content">
                <h3>${value}</h3>
                <p>${esc(label)}</p>
                ${sub ? `<small>${esc(sub)}</small>` : ''}
            </div>
        </div>`
}

/* ── Init ────────────────────────────────────────────────────────────────── */

async function initMyHR(csrf, endpoints) {
    MY_CSRF = csrf
    MY_ENDPOINTS = endpoints
    applyModal = new bootstrap.Modal(el('applyModal'))
    claimModal = new bootstrap.Modal(el('claimModal'))
    el('btnNewClaim').addEventListener('click', openClaimModal)
    el('claimForm').addEventListener('submit', submitClaim)

    document.querySelectorAll('.hr-tabs [data-tab]').forEach(btn => {
        btn.addEventListener('click', () => showTab(btn.dataset.tab))
    })
    el('btnApplyLeave').addEventListener('click', openApplyModal)
    el('applyForm').addEventListener('submit', submitApplication)
    el('applyFrom').addEventListener('change', () => {
        const to = el('applyTo')
        if (!to.value || to.value < el('applyFrom').value) to.value = el('applyFrom').value
    })
    el('applyDayType').addEventListener('change', syncHalfDay)
    el('applyTo').addEventListener('change', syncHalfDay)

    el('btnCheckIn').addEventListener('click', () => postAttendance(MY_ENDPOINTS.checkIn))
    el('btnCheckOut').addEventListener('click', () => postAttendance(MY_ENDPOINTS.checkOut))

    el('btnAttLoad').addEventListener('click', loadAttendance)
    el('btnAttThisMonth').addEventListener('click', () => setAttendanceRange(0))
    el('btnAttLastMonth').addEventListener('click', () => setAttendanceRange(-1))

    tickClock()
    setInterval(tickClock, 15000)

    const startTab = (location.hash || '').replace('#', '')
    showTab(['overview', 'details', 'attendance', 'leaves', 'pay'].includes(startTab) ? startTab : 'overview')

    setAttendanceRange(0)
    await Promise.all([loadProfile(), loadLeaves(), loadCheckStatus(), loadMonthSummary(), loadPayslips(), loadClaims()])
}

function showTab(name) {
    document.querySelectorAll('.hr-tabs [data-tab]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === name)
    })
    document.querySelectorAll('[data-pane]').forEach(pane => {
        pane.hidden = pane.dataset.pane !== name
    })
    history.replaceState(null, '', `#${name}`)
}

function tickClock() {
    const now = new Date()
    el('liveClock').textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
    el('liveDate').textContent = now.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })
}

/* ── Check in / out ────────────────────────���─────────────────────────────── */

async function loadCheckStatus() {
    const res = await api('GET', MY_ENDPOINTS.checkStatus)
    if (!res.success) {
        el('checkStatus').textContent = res.error || 'Could not load attendance status.'
        return
    }
    const info = res.data || {}
    const today = info.today
    const inBtn = el('btnCheckIn')
    const outBtn = el('btnCheckOut')

    if (info.has_checked_out_today) {
        el('checkStatus').innerHTML = `Checked in at <b>${fmtTime(today.check_in_time)}</b> and out at <b>${fmtTime(today.check_out_time)}</b>. Done for today.`
        inBtn.disabled = true
        outBtn.disabled = true
    } else if (info.has_checked_in_today) {
        el('checkStatus').innerHTML = `Checked in at <b>${fmtTime(today.check_in_time)}</b>. Remember to check out.`
        inBtn.disabled = true
        outBtn.disabled = false
    } else {
        el('checkStatus').textContent = 'You have not checked in today.'
        inBtn.disabled = false
        outBtn.disabled = true
    }
}

async function postAttendance(url) {
    el('btnCheckIn').disabled = true
    el('btnCheckOut').disabled = true
    const res = await api('POST', url, {})
    if (!res.success) {
        toast(res.error || 'Could not update attendance.', 'err')
        await loadCheckStatus()
        return
    }
    toast('Attendance updated.')
    // The side nav has its own check in/out widget, so reload to keep both in sync.
    setTimeout(() => location.reload(), 600)
}

/* ── Profile ─────────────────────────────────────────────────────────────── */

async function loadProfile() {
    const res = await api('GET', MY_ENDPOINTS.profile)
    if (!res.success) {
        el('pageSub').textContent = 'Could not load your profile.'
        el('detailsBody').innerHTML = `<div class="empty-state">${esc(res.error)}</div>`
        return
    }
    profileData = res.data
    const { user, employee } = profileData
    el('pageSub').textContent = `${user.name} · ${user.user_code} · ${ROLE_LABELS[user.role] || user.role}`
    renderBalance(profileData.balance, profileData.month_label)
    renderDetails(employee, user)
}

function renderDetails(emp, user) {
    const missing = emp.missing_fields && emp.missing_fields.length
        ? `<div class="alert alert-warning py-2" style="font-size:0.85rem;"><i class="fas fa-triangle-exclamation me-1"></i>HR is still missing: ${esc(emp.missing_fields.join(', '))}</div>`
        : ''
    const contacts = emp.emergency_contacts && emp.emergency_contacts.length
        ? emp.emergency_contacts.map(c => `<div>${esc(c.name)} <span class="text-muted">(${esc(c.relation)})</span> &middot; ${esc(c.mobile)}</div>`).join('')
        : ''
    const avatar = emp.photo && isImage(emp.photo)
        ? `<img class="profile-avatar" src="${esc(emp.photo)}" alt="${esc(user.name)}">`
        : `<span class="profile-avatar">${esc(initials(user.name))}</span>`

    el('detailsBody').innerHTML = `
        ${missing}
        <div class="form-section">
            <div class="profile-top">
                ${avatar}
                <div>
                    <div class="fw-bold" style="font-size:1.1rem;color:#1e293b;">${esc(emp.full_name || user.name)}</div>
                    <div class="text-muted small">${esc(emp.position) || '-'} · ${esc(emp.department) || '-'}</div>
                </div>
            </div>
            <div class="form-section-title">Basic Details</div>
            <div class="detail-grid">
                ${detailItem('Name', esc(emp.full_name || user.name))}
                ${detailItem('Employee ID', esc(user.user_code))}
                ${detailItem('Employee Code', esc(emp.employee_code))}
                ${detailItem('Email', esc(emp.email))}
                ${detailItem('Role', esc(ROLE_LABELS[user.role] || user.role))}
                ${detailItem('Joining Date', fmtDate(emp.joining_date))}
                ${detailItem('Department', esc(emp.department))}
                ${detailItem('Position', esc(emp.position))}
                ${detailItem('Reporting To', esc(emp.reporting_to_name))}
                ${detailItem('Personal Mobile', esc(emp.personal_mobile))}
                ${detailItem('Current Address', esc(emp.current_address))}
                ${detailItem('Permanent Address', esc(emp.permanent_address))}
                ${detailItem('CV / Resume', fileLink(emp.cv_file, 'View CV'))}
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

/* ── Leave balance ───────────────────────────────────────────────────────── */

const BALANCE_META = {
    casual: { label: 'Casual leave', icon: 'fa-mug-hot', color: '#3b82f6' },
    sick:   { label: 'Sick leave', icon: 'fa-notes-medical', color: '#ef4444' },
}

function renderBalance(balance, monthLabel) {
    el('balanceMonth').textContent = monthLabel ? `· ${monthLabel}` : ''
    const cards = Object.entries(BALANCE_META).map(([type, meta]) => {
        const b = balance[type] || { quota: 0, used: 0, available: 0 }
        return statCard(
            meta.icon, meta.color,
            `${fmtDays(b.available)} <span class="text-muted" style="font-size:0.95rem;font-weight:500;">/ ${fmtDays(b.quota)}</span>`,
            `${meta.label} available`,
            `${fmtDays(b.used)} used this month`,
        )
    }).join('')
    el('balanceCards').innerHTML = cards
    el('leaveBalanceCards').innerHTML = cards
}

/* ── Attendance ──────────────────────────────────────────────────────────── */

function setAttendanceRange(monthOffset) {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1)
    const end = monthOffset === 0 ? now : new Date(now.getFullYear(), now.getMonth() + monthOffset + 1, 0)
    el('attFrom').value = toISODate(start)
    el('attTo').value = toISODate(end)
    loadAttendance()
}

async function fetchAttendance(from, to) {
    return api('GET', `${MY_ENDPOINTS.attendance}?from_date=${from}&to_date=${to}`)
}

async function loadMonthSummary() {
    const now = new Date()
    const res = await fetchAttendance(toISODate(new Date(now.getFullYear(), now.getMonth(), 1)), toISODate(now))
    if (!res.success) {
        el('monthSummary').innerHTML = `<div class="empty-state">${esc(res.error)}</div>`
        return
    }
    el('monthSummary').innerHTML = summaryCards(res.data.summary)
}

function summaryCards(s) {
    return [
        statCard('fa-circle-check', '#10b981', s.present, 'Present'),
        statCard('fa-clock', '#f59e0b', s.half_day, 'Half days', 'Late check-in'),
        statCard('fa-circle-xmark', '#ef4444', s.absent, 'Absent'),
        statCard('fa-umbrella-beach', '#3b82f6', fmtDays(s.leave_days), 'Leave days'),
        statCard('fa-triangle-exclamation', '#dc2626', s.forgot_checkout, 'Forgot check-out'),
        statCard('fa-hourglass-half', '#6366f1', fmtMinutes(s.worked_minutes), 'Hours worked'),
    ].join('')
}

async function loadAttendance() {
    const from = el('attFrom').value
    const to = el('attTo').value
    if (!from || !to) {
        toast('Choose both a from and a to date.', 'err')
        return
    }
    if (to < from) {
        toast('To date cannot be before from date.', 'err')
        return
    }
    el('attBody').innerHTML = '<tr><td colspan="7" class="empty-state">Loading...</td></tr>'
    const res = await fetchAttendance(from, to)
    if (!res.success) {
        el('attBody').innerHTML = `<tr><td colspan="7" class="empty-state">${esc(res.error)}</td></tr>`
        el('attSummary').innerHTML = ''
        return
    }
    const { rows, summary } = res.data
    el('attSummary').innerHTML = summaryCards(summary)

    if (!rows.length) {
        el('attBody').innerHTML = '<tr><td colspan="7" class="empty-state">No days in this range.</td></tr>'
        return
    }
    el('attBody').innerHTML = [...rows].reverse().map(r => {
        const [label, cls] = ATT_STATUS[r.status] || [r.status, 'pill-pending']
        const remarks = []
        if (r.forgot_checkout) remarks.push('<span class="forgot-flag"><i class="fas fa-triangle-exclamation me-1"></i>Forgot to check out</span>')
        if (r.in_progress) remarks.push('<span class="in-progress-flag">In progress</span>')
        if (r.holiday) remarks.push(esc(r.holiday))
        if (r.leave) remarks.push(`${esc(r.leave.type)}${r.leave.reason ? ': ' + esc(r.leave.reason) : ''}`)
        const muted = ['weekly_off', 'holiday'].includes(r.status) ? 'row-muted' : ''
        return `
            <tr class="${r.forgot_checkout ? 'row-forgot' : muted}">
                <td>${fmtDate(r.date)}</td>
                <td>${esc(r.weekday || fmtWeekday(r.date))}</td>
                <td>${fmtTime(r.check_in)}</td>
                <td>${fmtTime(r.check_out)}</td>
                <td>${fmtMinutes(r.worked_minutes)}</td>
                <td><span class="pill ${cls}">${esc(label)}</span></td>
                <td>${remarks.join(' · ') || '-'}</td>
            </tr>`
    }).join('')
}

/* ── Leaves ──────────────────────────────────────────────────────────────── */

async function loadLeaves() {
    const res = await api('GET', MY_ENDPOINTS.leave)
    if (!res.success) {
        el('applicationsBody').innerHTML = `<tr><td colspan="8" class="empty-state">${esc(res.error)}</td></tr>`
        return
    }
    leaveData = res.data
    renderBalance(leaveData.balance, leaveData.month_label)
    renderApplications()
    renderLeaves()
}

function renderApplications() {
    const apps = leaveData.applications
    if (!apps.length) {
        el('applicationsBody').innerHTML = '<tr><td colspan="8" class="empty-state">You have not applied for any leave yet.</td></tr>'
        return
    }
    el('applicationsBody').innerHTML = apps.map(a => {
        const dates = a.from_date === a.to_date ? fmtDate(a.from_date) : `${fmtDate(a.from_date)} - ${fmtDate(a.to_date)}`
        const reviewed = a.reviewed_by_name ? `<div class="text-muted" style="font-size:0.72rem;">by ${esc(a.reviewed_by_name)}</div>` : ''
        const withdraw = a.status === 'pending'
            ? `<button type="button" class="btn btn-outline-danger btn-sm" data-withdraw="${a.id}"><i class="fas fa-xmark me-1"></i>Withdraw</button>`
            : ''
        return `
            <tr>
                <td>${fmtDate((a.created_at || '').substring(0, 10))}</td>
                <td>${dates}${a.day_type === 'half' ? ' <span class="text-muted">(half)</span>' : ''}</td>
                <td><span class="pill pill-leave">${esc(a.leave_type_display)}</span></td>
                <td>${fmtDays(a.days)}</td>
                <td>${esc(a.reason)}</td>
                <td><span class="pill ${APPLICATION_STATUS[a.status] || 'pill-pending'}">${esc(a.status_display)}</span>${reviewed}</td>
                <td>${esc(a.review_note) || '-'}</td>
                <td>${withdraw}</td>
            </tr>`
    }).join('')
    el('applicationsBody').querySelectorAll('[data-withdraw]').forEach(btn => {
        btn.addEventListener('click', () => withdrawApplication(btn.dataset.withdraw))
    })
}

function renderLeaves() {
    const leaves = leaveData.leaves
    if (!leaves.length) {
        el('leavesBody').innerHTML = '<tr><td colspan="5" class="empty-state">No leave days recorded.</td></tr>'
        return
    }
    el('leavesBody').innerHTML = leaves.map(l => `
        <tr>
            <td>${fmtDate(l.date)}</td>
            <td>${fmtWeekday(l.date)}</td>
            <td><span class="pill pill-leave">${esc(l.leave_type_display)}</span></td>
            <td>${l.day_type === 'half' ? 'Half day' : 'Full day'}</td>
            <td>${esc(l.reason) || '-'}</td>
        </tr>`).join('')
}

async function withdrawApplication(id) {
    if (!confirm('Withdraw this leave application?')) return
    const res = await api('DELETE', `${MY_ENDPOINTS.leave}${id}/`)
    if (!res.success) {
        toast(res.error || 'Could not withdraw the application.', 'err')
        return
    }
    toast('Application withdrawn.')
    await loadLeaves()
}

/* ── Apply for leave ─────────────────────────────────────────────────────── */

function openApplyModal() {
    const today = new Date()
    const earliest = new Date(today.getFullYear(), today.getMonth(), today.getDate() - backdateLimitDays)
    el('applyForm').reset()
    el('applyFrom').min = toISODate(earliest)
    el('applyTo').min = toISODate(earliest)
    el('applyFrom').value = toISODate(today)
    el('applyTo').value = toISODate(today)
    el('applyError').hidden = true

    const balance = (leaveData && leaveData.balance) || (profileData && profileData.balance)
    el('applyBalance').innerHTML = balance
        ? Object.entries(BALANCE_META).map(([type, meta]) => {
            const b = balance[type]
            return `<div><b>${meta.label}:</b> ${fmtDays(b.available)} of ${fmtDays(b.quota)} available</div>`
        }).join('')
        : ''
    syncHalfDay()
    applyModal.show()
}

function syncHalfDay() {
    const half = el('applyDayType').value === 'half'
    if (half) el('applyTo').value = el('applyFrom').value
    el('applyTo').disabled = half
}

async function submitApplication(event) {
    event.preventDefault()
    const error = el('applyError')
    error.hidden = true

    const payload = {
        from_date: el('applyFrom').value,
        to_date: el('applyTo').value || el('applyFrom').value,
        leave_type: el('applyType').value,
        day_type: el('applyDayType').value,
        reason: el('applyReason').value.trim(),
    }
    if (!payload.from_date) {
        error.textContent = 'Choose the leave date.'
        error.hidden = false
        return
    }
    if (!payload.reason) {
        error.textContent = 'Please give a reason for the leave.'
        error.hidden = false
        return
    }

    const submit = el('applySubmit')
    submit.disabled = true
    const res = await api('POST', MY_ENDPOINTS.leave, payload)
    submit.disabled = false

    if (!res.success) {
        error.textContent = res.error || 'Could not submit the application.'
        error.hidden = false
        return
    }
    applyModal.hide()
    toast('Leave application submitted. HR will review it.')
    showTab('leaves')
    await Promise.all([loadLeaves(), loadProfile()])
}

/* ── Pay & reimbursements ────────────────────────────────────────────────── */

async function loadPayslips() {
    const res = await api('GET', MY_ENDPOINTS.payslips)
    if (!res.success) {
        el('payslipsBody').innerHTML = `<tr><td colspan="8" class="empty-state">${esc(res.error)}</td></tr>`
        return
    }
    el('payslipsBody').innerHTML = res.data.length ? res.data.map(p => `
        <tr>
            <td><strong>${esc(p.month_label)}</strong></td>
            <td>${fmtMoney(p.total_salary)}</td>
            <td>${p.leave_deduction ? '&minus; ' + fmtMoney(p.leave_deduction) : '-'}</td>
            <td>${p.tds_deducted ? '&minus; ' + fmtMoney(p.tds_deducted) : '-'}</td>
            <td>${p.reimbursement_total ? '+ ' + fmtMoney(p.reimbursement_total) : '-'}</td>
            <td><strong>${fmtMoney(p.net_payable)}</strong></td>
            <td>${p.paid_on ? fmtDate(p.paid_on) : '-'}</td>
            <td><a class="btn btn-sm btn-outline-primary" href="${MY_ENDPOINTS.payslips}${p.id}/slip/">
                <i class="fas fa-file-pdf me-1"></i>Download</a></td>
        </tr>`).join('')
        : '<tr><td colspan="8" class="empty-state">No salary slips yet. They appear here once HR marks a month as paid.</td></tr>'
}

async function loadClaims() {
    const res = await api('GET', MY_ENDPOINTS.reimbursements)
    if (!res.success) {
        el('claimsBody').innerHTML = `<tr><td colspan="6" class="empty-state">${esc(res.error)}</td></tr>`
        return
    }
    el('claimSummary').textContent = res.unpaid_count
        ? `${res.unpaid_count} claim${res.unpaid_count === 1 ? '' : 's'} not yet paid, totalling ${fmtMoney(res.unpaid_total)}.`
        : 'No unpaid claims.'

    el('claimsBody').innerHTML = res.data.length ? res.data.map(r => {
        const status = r.payroll
            ? `<span class="pill ${r.is_paid ? 'pill-approved' : 'pill-pending'}">${r.is_paid ? 'Paid' : 'In payroll'} ${esc(r.payroll_period || '')}</span>`
            : '<span class="pill pill-pending">Pending</span>'
        return `
        <tr>
            <td>${fmtDate(r.expense_date)}</td>
            <td>${esc(r.description)}</td>
            <td><strong>${fmtMoney(r.amount)}</strong></td>
            <td>${r.receipt_url ? fileLink(r.receipt_url, 'View') : '-'}</td>
            <td>${status}</td>
            <td>${r.payroll ? '' : `<button type="button" class="btn btn-sm btn-outline-danger" aria-label="Withdraw claim" onclick="withdrawClaim(${r.id})">Withdraw</button>`}</td>
        </tr>`
    }).join('') : '<tr><td colspan="6" class="empty-state">You have not made any claims.</td></tr>'
}

function openClaimModal() {
    el('claimForm').reset()
    el('claimDate').value = toISODate(new Date())
    el('claimError').hidden = true
    claimModal.show()
}

async function submitClaim(event) {
    event.preventDefault()
    const error = el('claimError')
    error.hidden = true

    const amount = el('claimAmount').value
    const description = el('claimDesc').value.trim()
    const file = el('claimReceipt').files[0]
    const problem = !el('claimDate').value ? 'Choose the expense date.'
        : !amount || Number(amount) <= 0 ? 'Enter a valid amount.'
        : !description ? 'Say what the expense was for.'
        : !file ? 'Attach a photo of the receipt.'
        : ''
    if (problem) {
        error.textContent = problem
        error.hidden = false
        return
    }

    const form = new FormData()
    form.append('expense_date', el('claimDate').value)
    form.append('amount', amount)
    form.append('description', description)
    form.append('receipt', file)

    const submit = el('claimSubmit')
    submit.disabled = true
    const res = await api('POST', MY_ENDPOINTS.reimbursements, form, true)
    submit.disabled = false

    if (!res.success) {
        error.textContent = res.error || 'Could not submit the claim.'
        error.hidden = false
        return
    }
    claimModal.hide()
    toast('Claim submitted. HR will include it in a payroll.')
    await loadClaims()
}

async function withdrawClaim(id) {
    if (!confirm('Withdraw this claim?')) return
    const res = await api('DELETE', `${MY_ENDPOINTS.reimbursements}${id}/`)
    if (!res.success) { toast(res.error || 'Could not withdraw the claim.', 'err'); return }
    toast('Claim withdrawn.')
    await loadClaims()
}
