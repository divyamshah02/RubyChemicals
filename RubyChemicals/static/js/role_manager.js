/**
 * role_manager.js
 * Uses the shared callApi() from api_caller.js.
 * Initialise by calling: initRoleManager(csrfToken, endpoints)
 */

// ── Config ────────────────────────────────────────────────────────────────────

// NOTE: can_stock_items also grants Stock Inwards access — they share one permission.
const PLUGINS = [
    { key: "can_stock_items",       label: "Stock Items" },
    { key: "can_vendor_management", label: "Vendor Management" },
    { key: "can_production",        label: "Production" },
    { key: "can_dispatch",          label: "Dispatch" },
    { key: "can_client_management", label: "Client Management" },
    { key: "can_petty_cash",        label: "Petty Cash" },
    { key: "can_leads",             label: "Leads" },
];

// ── Module state ──────────────────────────────────────────────────────────────

let csrf      = '';
let endpoints = {};
let allUsers  = [];      // full list from server

// ── Bootstrap entry point ─────────────────────────────────────────────────────

function initRoleManager(csrfToken, eps) {
    csrf      = csrfToken;
    endpoints = eps;
    renderPluginCheckboxes('createPlugins');
    renderPluginCheckboxes('editPlugins');
    loadUsers();
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadUsers() {
    showTableLoader();
    const [ok, res] = await callApi("GET", endpoints.users);
    if (ok && res.success) {
        allUsers = res.data;
        updateStats();
        applyFilters();
    } else {
        showTableError("Failed to load users.");
    }
}

// ── Filters ───────────────────────────────────────────────────────────────────

function applyFilters() {
    const search  = document.getElementById('filterSearch').value.trim().toLowerCase();
    const role    = document.getElementById('filterRole').value;
    const active  = document.getElementById('filterStatus').value;
    const isSuper = document.getElementById('filterSuper').value;

    const filtered = allUsers.filter(u => {
        const matchSearch  = !search  || u.name.toLowerCase().includes(search) || u.email.toLowerCase().includes(search);
        const matchRole    = !role    || u.role === role;
        const matchActive  = !active  || String(u.active_user) === active;
        const matchSuper   = !isSuper || String(u.is_super_admin) === isSuper;
        return matchSearch && matchRole && matchActive && matchSuper;
    });

    renderTable(filtered);
}

function clearFilters() {
    document.getElementById('filterSearch').value  = '';
    document.getElementById('filterRole').value    = '';
    document.getElementById('filterStatus').value  = '';
    document.getElementById('filterSuper').value   = '';
    applyFilters();
}

// ── Render ────────────────────────────────────────────────────────────────────

function updateStats() {
    document.getElementById('statTotal').textContent  = allUsers.length;
    document.getElementById('statActive').textContent = allUsers.filter(u => u.active_user).length;
}

function renderTable(users) {
    const tbody = document.getElementById('usersBody');

    if (!users.length) {
        tbody.innerHTML = `
            <tr><td colspan="8" class="text-center text-muted py-5">
                <i class="fas fa-users-slash" style="font-size:2rem; opacity:.3;"></i>
                <p class="mt-2 mb-0">No users found</p>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = users.map(u => {
        const validRoles = ['admin', 'accounts', 'factory', 'accountant', 'office'];
        const roleCls  = `role-badge role-${validRoles.includes(u.role) ? u.role : 'admin'}`;
        const statusBadge = u.active_user
            ? '<span class="badge bg-success">Active</span>'
            : '<span class="badge bg-secondary">Inactive</span>';

        const permChips = u.is_super_admin
            ? `<span class="perm-chip super"><i class="fas fa-crown"></i> Super Admin</span>`
            : PLUGINS
                .filter(p => u[p.key])
                .map(p => `<span class="perm-chip active">${p.label}</span>`)
                .join('') || '<span class="text-muted" style="font-size:.75rem;">No access</span>';

        const created = u.created_at ? CustomformatDate(u.created_at.slice(0,10)) : '—';

        return `
        <tr>
            <td><span class="user-id-badge">${u.user_id}</span></td>
            <td><strong>${escHtml(u.name)}</strong></td>
            <td>${escHtml(u.email)}</td>
            <td><span class="${roleCls}">${u.role}</span></td>
            <td style="max-width:240px;">${permChips}</td>
            <td>${statusBadge}</td>
            <td>${created}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-warning btn-sm text-white" title="Edit" onclick="openEditModal(${u.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-info btn-sm text-white" title="Change Password" onclick="openChangePasswordModal(${u.id}, '${escHtml(u.name)}')">
                        <i class="fas fa-key"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" title="Delete" onclick="openDeleteModal(${u.id}, '${escHtml(u.name)}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function renderPluginCheckboxes(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = PLUGINS.map(p => `
        <div class="col-md-6 col-lg-4">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="${containerId}_${p.key}" name="${p.key}">
                <label class="form-check-label" for="${containerId}_${p.key}">${p.label}</label>
            </div>
        </div>`).join('');
}

// ── Toggle super-admin (disables individual checkboxes) ───────────────────────

function toggleSuperAdmin(prefix) {
    const isSuper  = document.getElementById(`${prefix}IsSuperAdmin`).checked;
    const plugins  = document.getElementById(`${prefix === 'create' ? 'createPlugins' : 'editPlugins'}`);

    plugins.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.disabled = isSuper;
        if (isSuper) cb.checked = false;
    });

    const banner = document.getElementById(`${prefix}SuperBanner`);
    if (banner) banner.style.display = isSuper ? 'block' : 'none';
}

// ── Collect permissions from a prefix ────────────────────────────────────────

function collectPermissions(prefix, pluginsId) {
    const perms = {};
    PLUGINS.forEach(p => {
        const cb = document.getElementById(`${pluginsId}_${p.key}`);
        perms[p.key] = cb ? cb.checked : false;
    });
    return perms;
}

function setPermissions(prefix, pluginsId, user) {
    document.getElementById(`${prefix}IsSuperAdmin`).checked = !!user.is_super_admin;
    PLUGINS.forEach(p => {
        const cb = document.getElementById(`${pluginsId}_${p.key}`);
        if (cb) {
            cb.checked  = !!user[p.key];
            cb.disabled = !!user.is_super_admin;
        }
    });
}

// ── CREATE ────────────────────────────────────────────────────────────────────

function openCreateModal() {
    // Reset form
    ['createName','createEmail','createPassword'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('createRole').value = 'factory';
    document.getElementById('createIsSuperAdmin').checked = false;
    document.querySelectorAll('#createPlugins input[type="checkbox"]').forEach(cb => {
        cb.checked  = false;
        cb.disabled = false;
    });
    bootstrap.Modal.getOrCreateInstance(document.getElementById('createUserModal')).show();
}

async function submitCreateUser() {
    const name     = document.getElementById('createName').value.trim();
    const email    = document.getElementById('createEmail').value.trim();
    const password = document.getElementById('createPassword').value;
    const role     = document.getElementById('createRole').value;
    const isSuper  = document.getElementById('createIsSuperAdmin').checked;

    if (!name || !email || !password || !role) {
        alert("Please fill in all required fields.");
        return;
    }

    const payload = {
        name,
        email,
        password,
        role,
        is_super_admin: isSuper,
        ...collectPermissions('create', 'createPlugins'),
    };

    const [ok, res] = await callApi("POST", endpoints.users, payload, csrf);

    if (ok && res.success) {
        bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
        showToast("User created successfully!", "success");
        loadUsers();
    } else {
        const errMsg = res && res.error
            ? (typeof res.error === 'object' ? JSON.stringify(res.error) : res.error)
            : "Failed to create user";
        alert("Error: " + errMsg);
    }
}

// ── EDIT ──────────────────────────────────────────────────────────────────────

async function openEditModal(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;

    document.getElementById('editUserId').value      = user.id;
    document.getElementById('editName').value         = user.name;
    document.getElementById('editEmail').value        = user.email;
    document.getElementById('editRole').value         = user.role;
    document.getElementById('editActiveUser').value   = String(user.active_user);

    setPermissions('edit', 'editPlugins', user);

    bootstrap.Modal.getOrCreateInstance(document.getElementById('editUserModal')).show();
}

async function submitEditUser() {
    const userId   = document.getElementById('editUserId').value;
    const name     = document.getElementById('editName').value.trim();
    const email    = document.getElementById('editEmail').value.trim();
    const role     = document.getElementById('editRole').value;
    const active   = document.getElementById('editActiveUser').value === 'true';
    const isSuper  = document.getElementById('editIsSuperAdmin').checked;

    if (!name || !email || !role) {
        alert("Please fill in all required fields.");
        return;
    }

    const payload = {
        name,
        email,
        role,
        active_user: active,
        is_super_admin: isSuper,
        ...collectPermissions('edit', 'editPlugins'),
    };

    const url = `${endpoints.userDetail}${userId}/`;
    const [ok, res] = await callApi("PATCH", url, payload, csrf);

    if (ok && res.success) {
        bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
        showToast("User updated successfully!", "success");
        loadUsers();
    } else {
        const errMsg = res && res.error
            ? (typeof res.error === 'object' ? JSON.stringify(res.error) : res.error)
            : "Failed to update user";
        alert("Error: " + errMsg);
    }
}

// ── CHANGE PASSWORD ───────────────────────────────────────────────────────────

function openChangePasswordModal(userId, userName) {
    document.getElementById('cpUserId').value      = userId;
    document.getElementById('cpUserLabel').textContent = `Changing password for: ${userName}`;
    document.getElementById('cpNewPassword').value = '';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('changePasswordModal')).show();
}

async function submitChangePassword() {
    const userId      = document.getElementById('cpUserId').value;
    const newPassword = document.getElementById('cpNewPassword').value;

    if (!newPassword || newPassword.length < 6) {
        alert("Password must be at least 6 characters.");
        return;
    }

    const url = `${endpoints.userDetail}${userId}/change-password/`;
    const [ok, res] = await callApi("POST", url, { new_password: newPassword }, csrf);

    if (ok && res.success) {
        bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
        showToast("Password changed successfully!", "success");
    } else {
        const errMsg = res && res.error
            ? (typeof res.error === 'object' ? JSON.stringify(res.error) : res.error)
            : "Failed to change password";
        alert("Error: " + errMsg);
    }
}

// ── DELETE ────────────────────────────────────────────────────────────────────

function openDeleteModal(userId, userName) {
    document.getElementById('delUserId').value   = userId;
    document.getElementById('delUserName').textContent = userName;
    bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteUserModal')).show();
}

async function submitDeleteUser() {
    const userId = document.getElementById('delUserId').value;
    const url    = `${endpoints.userDetail}${userId}/`;

    const [ok, res] = await callApi("DELETE", url, {}, csrf);

    if (ok && res.success) {
        bootstrap.Modal.getInstance(document.getElementById('deleteUserModal')).hide();
        showToast("User deleted successfully!", "danger");
        loadUsers();
    } else {
        const errMsg = res && res.error ? res.error : "Failed to delete user";
        alert("Error: " + errMsg);
    }
}

// ── Utility helpers ───────────────────────────────────────────────────────────

function showTableLoader() {
    document.getElementById('usersBody').innerHTML = `
        <tr><td colspan="8" class="text-center text-muted py-5">
            <i class="fas fa-spinner fa-spin" style="font-size:1.5rem;"></i>
        </td></tr>`;
}

function showTableError(msg) {
    document.getElementById('usersBody').innerHTML = `
        <tr><td colspan="8" class="text-center text-danger py-5">
            <i class="fas fa-exclamation-triangle"></i> ${msg}
        </td></tr>`;
}

function escHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str || '')));
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const colors = {
        success: '#10b981',
        danger:  '#ef4444',
        warning: '#f59e0b',
    };
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
        background: ${colors[type] || colors.success}; color: white;
        padding: 0.75rem 1.25rem; border-radius: 10px;
        font-weight: 600; font-size: 0.875rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideUp .3s ease;
    `;
    if (!document.getElementById('toast-anim-style')) {
        const s = document.createElement('style');
        s.id = 'toast-anim-style';
        s.innerHTML = `@keyframes slideUp { from { transform: translateY(20px); opacity:0 } to { transform: translateY(0); opacity:1 } }`;
        document.head.appendChild(s);
    }
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
