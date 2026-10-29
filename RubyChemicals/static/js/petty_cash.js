let csrf, endpoints;
let currentCashType = 'office';
let headsByType = {};
let allTransactions = [];
let pageTransactions = [];
let accounts = {};
let currentPage = 1;
let currentVoucher = null;
let filterDebounce = null;

function init(csrfToken, eps) {
  csrf = csrfToken;
  endpoints = eps;
  selectCashType('office');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatVoucherDate(value) {
  if (!value) return '';
  const [y, m, d] = String(value).split('-');
  return `${d}-${m}-${y}`;
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : '';
}

function selectCashType(cashType) {
  currentCashType = cashType;
  currentPage = 1;

  // Update button styles
  document.getElementById('officeBtn').className = cashType === 'office' ? 'btn btn-primary' : 'btn btn-outline-primary';
  document.getElementById('factoryBtn').className = cashType === 'factory' ? 'btn btn-primary' : 'btn btn-outline-secondary';
  document.getElementById('officeBtn').style.borderWidth = '2px';
  document.getElementById('factoryBtn').style.borderWidth = '2px';

  loadAccountBalance();
  loadHeads();
  loadAllTransactions();
}

async function loadAccountBalance() {
  const [ok, res] = await callApi("GET", endpoints.accounts);
  if (ok && res.data) {
    accounts = {};
    res.data.forEach(acc => {
      accounts[acc.cash_type] = acc;
    });

    const account = accounts[currentCashType];
    if (account) {
      document.getElementById('currentBalance').textContent = '₹ ' + parseFloat(account.current_balance).toFixed(2);
      document.getElementById('creditBalance').textContent = '₹ ' + parseFloat(account.credit_balance).toFixed(2);
    }
  }
}

async function loadHeads() {
  const [ok, res] = await callApi("GET", endpoints.heads);
  if (ok && res.data) {
    const heads = res.data.filter(h => h.is_active !== false);
    document.getElementById("expenseHead").innerHTML = '<option value="">Select Expense Head</option>' + heads
      .map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");

    const headFilter = document.getElementById("headFilter");
    const selected = headFilter.value;
    headFilter.innerHTML = '<option value="">All</option>' + heads
      .map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");
    headFilter.value = selected;
  }
}

function getFilterParams() {
  const params = new URLSearchParams();
  params.set('cash_type', currentCashType);

  const map = {
    transaction_type: 'transactionTypeFilter',
    expense_head_id: 'headFilter',
    paid_via: 'paidViaFilter',
    payment_type: 'paymentTypeFilter',
    date_from: 'dateFromFilter',
    date_to: 'dateToFilter',
    search: 'searchFilter',
  };
  Object.entries(map).forEach(([key, id]) => {
    const value = (document.getElementById(id)?.value || '').trim();
    if (value) params.set(key, value);
  });
  return params;
}

function applyFilters() {
  currentPage = 1;
  loadTransactionsPage();
}

function debouncedApplyFilters() {
  clearTimeout(filterDebounce);
  filterDebounce = setTimeout(applyFilters, 350);
}

function resetFilters() {
  ['transactionTypeFilter', 'headFilter', 'paidViaFilter', 'paymentTypeFilter',
    'dateFromFilter', 'dateToFilter', 'searchFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  applyFilters();
}

function goToPage(page) {
  currentPage = page;
  loadTransactionsPage();
}

async function loadAllTransactions() {
  // Full list for the selected cash type (expense heads tab and Excel export)
  const [ok, res] = await callApi("GET", `${endpoints.cash}?cash_type=${currentCashType}`);
  if (ok && res.data) {
    allTransactions = res.data;
    renderExpenseHeadsTab();
  }
  await loadTransactionsPage();
}

async function loadTransactionsPage() {
  const params = getFilterParams();
  params.set('page', currentPage);
  params.set('page_size', document.getElementById('pageSizeSelect')?.value || 20);

  const [ok, res] = await callApi("GET", `${endpoints.cash}?${params.toString()}`);
  if (ok && res.data) {
    pageTransactions = res.data;
    renderAllTransactionsTab();
    renderPagination(res.pagination, res.totals);
  }
}

function renderPagination(pagination, totals) {
  const info = document.getElementById('paginationInfo');
  const controls = document.getElementById('paginationControls');
  const totalsEl = document.getElementById('transactionTotals');

  if (!pagination) {
    info.textContent = '';
    controls.innerHTML = '';
    totalsEl.innerHTML = '';
    return;
  }

  const { page, page_size, total_pages, total_items } = pagination;
  currentPage = page;

  if (total_items === 0) {
    info.textContent = 'No results';
  } else {
    const start = (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total_items);
    info.textContent = `Showing ${start}-${end} of ${total_items}`;
  }

  totalsEl.innerHTML = totals ? `
    <span class="badge" style="background:#dcfce7;color:#15803d;font-size:0.8rem;">Credit: ₹ ${parseFloat(totals.credit).toFixed(2)}</span>
    <span class="badge" style="background:#fee2e2;color:#991b1b;font-size:0.8rem;">Debit: ₹ ${parseFloat(totals.debit).toFixed(2)}</span>
  ` : '';

  if (total_pages <= 1) {
    controls.innerHTML = '';
    return;
  }

  const pages = new Set([1, total_pages, page - 1, page, page + 1]);
  if (page <= 3) { pages.add(2); pages.add(3); pages.add(4); }
  if (page >= total_pages - 2) { pages.add(total_pages - 1); pages.add(total_pages - 2); pages.add(total_pages - 3); }
  const sorted = [...pages].filter(p => p >= 1 && p <= total_pages).sort((a, b) => a - b);

  let html = `<li class="page-item ${page === 1 ? 'disabled' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(${page - 1})">Prev</a></li>`;
  let prev = 0;
  sorted.forEach(p => {
    if (p - prev > 1) html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
    html += `<li class="page-item ${p === page ? 'active' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(${p})">${p}</a></li>`;
    prev = p;
  });
  html += `<li class="page-item ${page === total_pages ? 'disabled' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(${page + 1})">Next</a></li>`;
  controls.innerHTML = html;
}

function renderAllTransactionsTab() {
  const table = document.getElementById("allTransactionsTable");

  if (pageTransactions.length === 0) {
    table.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">No transactions</td></tr>';
    return;
  }

  table.innerHTML = pageTransactions.map(trans => `
    <tr>
      <td>#${trans.id}${trans.bill_url ? ' <i class="fas fa-paperclip text-muted" title="Bill attached"></i>' : ''}</td>
      <td>${trans.expense_date}</td>
      <td>
        <strong>${escapeHtml(trans.expense_head_name)}</strong>
      </td>
      <td>${escapeHtml(trans.to) || '—'}</td>
      <td>${escapeHtml(trans.paid_by) || '—'}</td>
      <td>
        <span style="background: ${trans.cash_type === 'office' ? '#dbeafe' : '#fef3c7'}; color: ${trans.cash_type === 'office' ? '#1e40af' : '#92400e'}; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 600;">
          ${trans.cash_type === 'office' ? 'Office' : 'Factory'}
        </span>
      </td>
      <td>
        <span style="background: ${trans.transaction_type === 'credit' ? '#dcfce7' : '#fee2e2'}; color: ${trans.transaction_type === 'credit' ? '#15803d' : '#991b1b'}; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 600;">
          ${trans.transaction_type === 'credit' ? 'Credit' : 'Debit'}
        </span>
      </td>
      <td><strong>₹ ${parseFloat(trans.amount).toFixed(2)}</strong></td>
      <td>
        <span style="background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">
          ${trans.paid_via ? trans.paid_via.charAt(0).toUpperCase() + trans.paid_via.slice(1) : '—'}
        </span>
      </td>
      <td>
        <span style="background: #f3e8ff; color: #6d28d9; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">
          ${trans.payment_type ? trans.payment_type.charAt(0).toUpperCase() + trans.payment_type.slice(1) : '—'}
        </span>
      </td>
      <td>
        <div class="d-flex flex-wrap gap-1">
          <button class="btn btn-sm btn-outline-dark" onclick="viewTransaction(${trans.id})" title="View voucher">
            <i class="fas fa-eye"></i> View
          </button>
          ${trans.transaction_type === 'debit' ? `
            <button class="btn btn-sm btn-outline-primary" onclick="downloadPettyCashPDF(${trans.id})" title="Download PDF">
              <i class="fas fa-file-pdf"></i> PDF
            </button>
          ` : ''}
          <button class="btn btn-sm btn-outline-warning" onclick="editTransaction(${trans.id})" title="Edit transaction">
            <i class="fas fa-edit"></i> Edit
          </button>
          <button class="btn btn-sm btn-outline-danger" onclick="deleteTransaction(${trans.id})" title="Delete transaction">
            <i class="fas fa-trash"></i> Delete
          </button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderExpenseHeadsTab() {
  const filteredTransactions = allTransactions.filter(t => t.cash_type === currentCashType);

  // Group by expense head
  const groupedByHead = {};
  filteredTransactions.forEach(trans => {
    if (!groupedByHead[trans.expense_head_name]) {
      groupedByHead[trans.expense_head_name] = [];
    }
    groupedByHead[trans.expense_head_name].push(trans);
  });

  const accordion = document.getElementById("expenseHeadsAccordion");

  if (Object.keys(groupedByHead).length === 0) {
    accordion.innerHTML = '<div class="text-center text-muted" style="padding: 2rem;"><p>No expense heads yet</p></div>';
    return;
  }

  accordion.innerHTML = Object.entries(groupedByHead).map(([headName, transactions], idx) => {
    const totalAmount = transactions.reduce((sum, t) => sum + parseFloat(t.amount), 0);

    return `
      <div style="border-bottom: 1px solid #e2e8f0;">
        <button class="collapse-header" data-bs-toggle="collapse" data-bs-target="#head-${idx}" aria-expanded="false">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <i class="fas fa-chevron-down collapse-icon"></i>
            <div>
              <div style="font-size: 1rem; font-weight: 700;">${headName}</div>
              <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">${transactions.length} transactions</div>
            </div>
          </div>
          <div style="background: #e0e7ff; color: #3730a3; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 700;">₹ ${parseFloat(totalAmount).toFixed(2)}</div>
        </button>
        
        <div id="head-${idx}" class="collapse" style="padding: 1.5rem; background: #f8fafc;">
          <table class="table table-sm" style="margin: 0;">
            <thead style="background: white; border-bottom: 2px solid #e2e8f0;">
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              ${transactions.map(trans => `
                <tr>
                  <td>${trans.expense_date}</td>
                  <td>
                    <span style="background: ${trans.transaction_type === 'credit' ? '#dcfce7' : '#fee2e2'}; color: ${trans.transaction_type === 'credit' ? '#15803d' : '#991b1b'}; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">
                      ${trans.transaction_type === 'credit' ? 'Credit' : 'Debit'}
                    </span>
                  </td>
                  <td><strong style="color: ${trans.transaction_type === 'credit' ? '#15803d' : '#991b1b'};">₹ ${parseFloat(trans.amount).toFixed(2)}</strong></td>
                  <td style="font-size: 0.85rem; color: #64748b;">${trans.notes || '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join("");
}

async function addBalance() {
  const amount = parseFloat(document.getElementById("balanceAmount").value);
  const date = document.getElementById("balanceDate").value;
  const notes = document.getElementById("balanceNotes").value;

  if (!amount || !date) {
    alert("Please fill all required fields");
    return;
  }

  const payload = {
    cash_type: currentCashType,
    expense_head_id: null,
    expense_date: date,
    amount: amount,
    transaction_type: 'credit',
    notes: notes || 'Balance Addition'
  };

  const [ok, res] = await callApi("POST", endpoints.cash, payload, csrf);
  if (ok && res.success) {
    alert("Balance added successfully!");
    document.getElementById("balanceAmount").value = "";
    document.getElementById("balanceDate").value = "";
    document.getElementById("balanceNotes").value = "";
    const modal = bootstrap.Modal.getInstance(document.getElementById("addBalanceModal"));
    if (modal) modal.hide();
    loadAccountBalance();
    loadAllTransactions();
  } else {
    alert("Error: " + (res.error || "Failed to add balance"));
  }
}

const BILL_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp'];
const BILL_MAX_BYTES = 10 * 1024 * 1024;

function validateBillFile(file) {
  if (!file) return null;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!BILL_EXTENSIONS.includes(ext)) return "Bill must be a PDF or an image (JPG, PNG, WEBP).";
  if (file.size > BILL_MAX_BYTES) return "Bill must be 10 MB or smaller.";
  return null;
}

async function createExpense() {
  const headId = document.getElementById("expenseHead").value;
  const amount = parseFloat(document.getElementById("expenseAmount").value);
  const date = document.getElementById("expenseDate").value;
  const notes = document.getElementById("expenseNotes").value;

  // New fields
  const to = document.getElementById("expenseTo").value;
  const paidVia = document.getElementById("expensePaidVia").value;
  const paymentType = document.getElementById("expensePaymentType").value;
  const particulars = document.getElementById("expenseParticulars").value;
  const paidBy = document.getElementById("expensePaidBy").value;

  if (!headId || !amount || !date) {
    alert("Please fill all required fields");
    return;
  }

  const billInput = document.getElementById("expenseBill");
  const billFile = billInput.files[0];
  const billError = validateBillFile(billFile);
  if (billError) {
    alert(billError);
    return;
  }

  const payload = new FormData();
  payload.append("cash_type", currentCashType);
  payload.append("expense_head_id", parseInt(headId));
  payload.append("expense_date", date);
  payload.append("amount", amount);
  payload.append("transaction_type", "debit");
  payload.append("notes", notes);
  payload.append("to", to);
  payload.append("paid_via", paidVia);
  payload.append("payment_type", paymentType);
  payload.append("particulars", particulars);
  payload.append("paid_by", paidBy);
  if (billFile) payload.append("bill", billFile);

  const [ok, res] = await callApi("POST", endpoints.cash, payload, csrf, true);
  if (ok && res.success) {
    alert("Expense added successfully!");
    billInput.value = "";
    document.getElementById("expenseAmount").value = "";
    document.getElementById("expenseDate").value = "";
    document.getElementById("expenseNotes").value = "";
    document.getElementById("expenseHead").value = "";
    document.getElementById("expenseTo").value = "";
    document.getElementById("expensePaidVia").value = "";
    document.getElementById("expensePaymentType").value = "";
    document.getElementById("expenseParticulars").value = "";
    document.getElementById("expensePaidBy").value = "";
    const modal = bootstrap.Modal.getInstance(document.getElementById("expenseModal"));
    if (modal) modal.hide();
    loadAccountBalance();
    loadAllTransactions();
  } else {
    alert("Error: " + (res.error || "Failed to add expense"));
  }
}

async function createHead() {
  const name = document.getElementById("newHead").value;
  if (!name) {
    alert("Please enter head name");
    return;
  }

  const [ok, res] = await callApi("POST", endpoints.heads, { name }, csrf);
  if (ok && res.success) {
    alert("Expense head added successfully!");
    document.getElementById("newHead").value = "";
    const modal = bootstrap.Modal.getInstance(document.getElementById("headModal"));
    if (modal) modal.hide();
    loadHeads();
  } else {
    alert("Error: " + (res.error || "Failed to add head"));
  }
}

async function downloadPettyCashPDF(pettyCashId) {
  window.location = `/operation-api/download-petty-cash-api/${pettyCashId}/`;
}

function buildVoucherHtml(t) {
  const isDebit = t.transaction_type === 'debit';
  const amount = parseFloat(t.amount).toFixed(2);
  const dateText = formatVoucherDate(t.expense_date);
  const toText = isDebit ? t.to : 'Balance Addition';
  const particulars = isDebit ? t.particulars : (t.notes || 'Balance added to petty cash');
  const remarks = isDebit ? t.notes : '';

  return `
    <div class="voucher-head">
      <h2 class="voucher-title">${isDebit ? 'EXPENSE VOUCHER' : 'BALANCE ADDITION VOUCHER'}</h2>
      <div class="voucher-brand">
        <img src="/static/ruby_logo.png" alt="Ruby Chemicals">
        <small>(A Unit of Ruby Build Care LLP)</small>
      </div>
    </div>
    <div class="voucher-row">
      <div class="voucher-field"><label>Challan No.:</label><span class="v-line">${escapeHtml(t.id)}</span></div>
      <div class="voucher-field"><label>Date:</label><span class="v-line">${escapeHtml(dateText)}</span></div>
    </div>
    <div class="voucher-row">
      <div class="voucher-field"><label>To:</label><span class="v-line">${escapeHtml(toText)}</span></div>
    </div>
    <div class="voucher-row">
      <div class="voucher-field"><label>Expense Head:</label><span class="v-line">${escapeHtml(isDebit ? t.expense_head_name : 'Balance Addition')}</span></div>
    </div>
    <div class="voucher-row">
      <div class="voucher-field"><label>Paid Via:</label><span class="v-line">${escapeHtml(capitalize(t.paid_via))}</span></div>
      <div class="voucher-field"><label>Payment Type:</label><span class="v-line">${escapeHtml(capitalize(t.payment_type))}</span></div>
    </div>
    <table class="voucher-table">
      <thead><tr><th>PARTICULARS</th><th style="width: 170px;">AMOUNT</th></tr></thead>
      <tbody>
        <tr><td class="particulars-cell">${escapeHtml(particulars)}</td><td>${amount}</td></tr>
        <tr><td class="total-label">TOTAL</td><td>${amount}</td></tr>
      </tbody>
    </table>
    <div class="voucher-remarks">
      <div class="voucher-field"><label>Remarks:</label><span class="v-line">${escapeHtml(remarks)}</span></div>
      <div class="v-line"></div>
    </div>
    <div class="voucher-row" style="margin-top: 28px;">
      <div class="voucher-field"><label>${isDebit ? 'PAID BY:' : 'ADDED BY:'}</label><span class="v-line">${escapeHtml(t.paid_by || t.created_by)}</span></div>
      <div class="voucher-field"><label>DATE:</label><span class="v-line">${escapeHtml(dateText)}</span></div>
    </div>
  `;
}

function renderVoucherBill(t) {
  const section = document.getElementById('voucherBillSection');
  const preview = document.getElementById('voucherBillPreview');
  if (!t.bill_url) {
    section.style.display = 'none';
    preview.innerHTML = '';
    return;
  }

  const url = encodeURI(t.bill_url);
  document.getElementById('voucherBillOpen').href = url;
  preview.innerHTML = t.bill_type === 'pdf'
    ? `<iframe src="${url}" title="Attached bill"></iframe>`
    : `<img src="${url}" alt="Attached bill">`;
  section.style.display = '';
}

async function viewTransaction(transactionId) {
  const [ok, res] = await callApi("GET", `${endpoints.cash}${transactionId}/`);
  if (!(ok && res.data)) {
    alert("Error: " + ((res && res.error) || "Failed to load transaction"));
    return;
  }

  currentVoucher = res.data;
  document.getElementById('voucherModalTitle').textContent =
    `${currentVoucher.transaction_type === 'debit' ? 'Expense' : 'Balance Addition'} #${currentVoucher.id}`;
  document.getElementById('voucherSheet').innerHTML = buildVoucherHtml(currentVoucher);
  document.getElementById('voucherPdfBtn').style.display = currentVoucher.transaction_type === 'debit' ? '' : 'none';
  renderVoucherBill(currentVoucher);
  bootstrap.Modal.getOrCreateInstance(document.getElementById('viewVoucherModal')).show();
}

function downloadCurrentVoucherPdf() {
  if (currentVoucher) downloadPettyCashPDF(currentVoucher.id);
}

async function downloadCurrentVoucherImage() {
  if (!currentVoucher) return;
  if (typeof html2canvas === 'undefined') {
    alert("Image export library failed to load. Please check your connection and try again.");
    return;
  }

  const sheet = document.getElementById('voucherSheet');
  try {
    const canvas = await html2canvas(sheet, { scale: 2, backgroundColor: '#ffffff', useCORS: true });
    const link = document.createElement('a');
    link.download = `petty_cash_${currentVoucher.id}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (err) {
    alert("Failed to create image: " + err.message);
  }
}

async function editTransaction(transactionId) {
  // Fetch transaction details
  const [ok, res] = await callApi("GET", `${endpoints.cash}${transactionId}/`);
  
  if (ok && res.data) {
    const trans = res.data;
    
    // Populate edit modal with transaction data
    document.getElementById("editTransactionId").value = transactionId;
    document.getElementById("editExpenseHead").value = trans.expense_head_id || "";
    document.getElementById("editExpenseAmount").value = trans.amount;
    document.getElementById("editExpenseDate").value = trans.expense_date;
    document.getElementById("editExpenseTo").value = trans.to || "";
    document.getElementById("editExpensePaidVia").value = trans.paid_via || "";
    document.getElementById("editExpensePaymentType").value = trans.payment_type || "";
    document.getElementById("editExpensePaidBy").value = trans.paid_by || "";
    document.getElementById("editExpenseParticulars").value = trans.particulars || "";
    document.getElementById("editExpenseNotes").value = trans.notes || "";

    document.getElementById("editExpenseBill").value = "";
    document.getElementById("editRemoveBill").checked = false;
    const currentBill = document.getElementById("editCurrentBill");
    const removeWrap = document.getElementById("editRemoveBillWrap");
    if (trans.bill_url) {
      currentBill.innerHTML = `<i class="fas fa-paperclip"></i> <a href="${encodeURI(trans.bill_url)}" target="_blank" rel="noopener">${escapeHtml(trans.bill_name)}</a>`;
      removeWrap.style.display = "";
    } else {
      currentBill.innerHTML = '<span class="text-muted">No bill attached</span>';
      removeWrap.style.display = "none";
    }
    
    // Load expense heads for dropdown
    const [headsOk, headsRes] = await callApi("GET", endpoints.heads);
    if (headsOk && headsRes.data) {
      document.getElementById("editExpenseHead").innerHTML = '<option value="">Select Expense Head</option>' + headsRes.data
        .filter(h => h.is_active)
        .map(h => `<option value="${h.id}">${h.name}</option>`).join("");
      document.getElementById("editExpenseHead").value = trans.expense_head_id || "";
    }
    
    // Open modal
    new bootstrap.Modal(document.getElementById("editExpenseModal")).show();
  } else {
    alert("Error: " + (res.error || "Failed to load transaction"));
  }
}

async function updateTransaction() {
  const transactionId = document.getElementById("editTransactionId").value;
  const headId = document.getElementById("editExpenseHead").value;
  const amount = parseFloat(document.getElementById("editExpenseAmount").value);
  const date = document.getElementById("editExpenseDate").value;
  const notes = document.getElementById("editExpenseNotes").value;
  
  // New fields
  const to = document.getElementById("editExpenseTo").value;
  const paidVia = document.getElementById("editExpensePaidVia").value;
  const paymentType = document.getElementById("editExpensePaymentType").value;
  const particulars = document.getElementById("editExpenseParticulars").value;
  const paidBy = document.getElementById("editExpensePaidBy").value;
  
  if (!headId || !amount || !date) {
    alert("Please fill all required fields");
    return;
  }
  
  const billFile = document.getElementById("editExpenseBill").files[0];
  const billError = validateBillFile(billFile);
  if (billError) {
    alert(billError);
    return;
  }

  const payload = new FormData();
  payload.append("expense_head_id", parseInt(headId));
  payload.append("amount", amount);
  payload.append("expense_date", date);
  payload.append("transaction_type", "debit");
  payload.append("notes", notes);
  payload.append("to", to);
  payload.append("paid_via", paidVia);
  payload.append("payment_type", paymentType);
  payload.append("particulars", particulars);
  payload.append("paid_by", paidBy);
  if (billFile) payload.append("bill", billFile);
  if (document.getElementById("editRemoveBill").checked) payload.append("remove_bill", "true");
  
  const [ok, res] = await callApi("PUT", `${endpoints.cash}${transactionId}/`, payload, csrf, true);
  if (ok && res.success) {
    alert("Expense updated successfully!");
    const modal = bootstrap.Modal.getInstance(document.getElementById("editExpenseModal"));
    if (modal) modal.hide();
    loadAccountBalance();
    loadAllTransactions();
  } else {
    alert("Error: " + (res.error || "Failed to update expense"));
  }
}

async function deleteTransaction(transactionId) {
  if (confirm("Are you sure you want to delete this transaction? This action cannot be undone.")) {
    const [ok, res] = await callApi("DELETE", `${endpoints.cash}${transactionId}/`, {}, csrf);
    if (ok && res.success) {
      alert("Transaction deleted successfully!");
      loadAccountBalance();
      loadAllTransactions();
    } else {
      alert("Error: " + (res.error || "Failed to delete transaction"));
    }
  }
}


function openOldBalanceModal() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('oldBalanceDate').value = today;
  document.getElementById('oldBalanceResults').innerHTML = '';
  new bootstrap.Modal(document.getElementById('oldBalanceModal')).show();
}

async function searchOldBalance() {
  const date = document.getElementById('oldBalanceDate').value;

  if (!date) {
    alert('Please select a date');
    return;
  }

  const resultsDiv = document.getElementById('oldBalanceResults');
  resultsDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> Loading...';

  const [ok, res] = await callApi("GET", `${endpoints.pettyCashLog}${date}/`);

  if (ok && res.data && res.data.cash_data) {
    const cashData = res.data.cash_data;
    const expenses = res.data.expenses || [];

    // Filter for current cash type only
    if (currentCashType in cashData) {
      const data = cashData[currentCashType];
      
      // Build balance summary
      let balanceHtml = `
        <div style="background: #f8fafc; border-radius: 8px; padding: 1.5rem; border: 1px solid #e2e8f0; margin-bottom: 1.5rem;">
          <h6 style="color: #64748b; font-size: 0.875rem; margin-bottom: 1rem; text-transform: uppercase;">Balance Summary on ${date}</h6>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div>
              <div style="font-size: 0.875rem; color: #64748b; margin-bottom: 0.25rem;">Opening Balance</div>
              <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;">₹ ${parseFloat(data.opening_balance).toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size: 0.875rem; color: #64748b; margin-bottom: 0.25rem;">Closing Balance</div>
              <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">₹ ${parseFloat(data.closing_balance).toFixed(2)}</div>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="background: #fee2e2; padding: 1rem; border-radius: 6px;">
              <div style="font-size: 0.75rem; color: #991b1b; margin-bottom: 0.25rem;">Total Debit (Expense)</div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #991b1b;">₹ ${parseFloat(data.total_debit).toFixed(2)}</div>
            </div>
            <div style="background: #dcfce7; padding: 1rem; border-radius: 6px;">
              <div style="font-size: 0.75rem; color: #15803d; margin-bottom: 0.25rem;">Total Credit (Addition)</div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #15803d;">₹ ${parseFloat(data.total_credit).toFixed(2)}</div>
            </div>
          </div>
        </div>
      `;
      
      // Build expenses table
      let expensesHtml = '';
      if (expenses.length > 0) {
        expensesHtml = `
          <div style="margin-top: 1.5rem;">
            <h6 style="color: #64748b; font-size: 0.875rem; margin-bottom: 1rem; text-transform: uppercase;">Expenses on ${date}</h6>
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; max-height: 400px; overflow-y: auto;">
              <table class="table mb-0" style="font-size: 0.875rem;">
                <thead style="background: #f8fafc; position: sticky; top: 0;">
                  <tr>
                    <th>Head</th>
                    <th>To</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Paid Via</th>
                    <th>Payment Type</th>
                    <th>Paid By</th>
                  </tr>
                </thead>
                <tbody>
                  ${expenses.map(exp => `
                    <tr>
                      <td><strong>${exp.expense_head}</strong></td>
                      <td>${exp.to}</td>
                      <td>
                        <span style="background: ${exp.transaction_type === 'credit' ? '#dcfce7' : '#fee2e2'}; color: ${exp.transaction_type === 'credit' ? '#15803d' : '#991b1b'}; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">
                          ${exp.transaction_type === 'credit' ? 'Credit' : 'Debit'}
                        </span>
                      </td>
                      <td><strong>₹ ${parseFloat(exp.amount).toFixed(2)}</strong></td>
                      <td>
                        <span style="background: #e0e7ff; color: #3730a3; padding: 2px 4px; border-radius: 3px; font-size: 0.75rem;">
                          ${exp.paid_via}
                        </span>
                      </td>
                      <td>
                        <span style="background: #f3e8ff; color: #6d28d9; padding: 2px 4px; border-radius: 3px; font-size: 0.75rem;">
                          ${exp.payment_type}
                        </span>
                      </td>
                      <td>${exp.paid_by}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
      } else {
        expensesHtml = '<div class="alert alert-info mt-3">No expenses recorded for this date.</div>';
      }
      
      resultsDiv.innerHTML = balanceHtml + expensesHtml;
    } else {
      resultsDiv.innerHTML = '<div class="alert alert-info">No data available for this date and cash type.</div>';
    }
  } else {
    resultsDiv.innerHTML = '<div class="alert alert-warning">No log found for this date. Balance data will be calculated from transactions.</div>';
  }
}

function handleExpenseSummaryExport() {
    const startDate = document.getElementById('expense_export_start_date').value || null;
    const endDate = document.getElementById('expense_export_end_date').value || null;
    let expensesData = allTransactions.filter(t => t.cash_type === currentCashType);
    exportExpenseSummary(
        expensesData, // replace with your expenses array variable
        startDate,
        endDate
    );

    bootstrap.Modal
        .getInstance(document.getElementById('exportExpenseSummaryModal'))
        ?.hide();
}


function exportExpenseSummary(expensesData, startDate = null, endDate = null) {

    let filteredData = expensesData;

    // Filter dates
    if (startDate || endDate) {
        filteredData = expensesData.filter(item => {
            const expenseDate = new Date(item.expense_date);

            if (startDate && expenseDate < new Date(startDate)) {
                return false;
            }

            if (endDate && expenseDate > new Date(endDate)) {
                return false;
            }

            return true;
        });
    }

    // Only debit entries
    filteredData = filteredData.filter(
        item => item.transaction_type === "debit"
    );

    // Sort by date ascending
    filteredData.sort(
        (a, b) => new Date(a.expense_date) - new Date(b.expense_date)
    );

    // =========================
    // SHEET 1 - EXPENSE DETAILS
    // =========================

    const expenseRows = filteredData.map(item => ({
        "DATE": CustomformatDate(item.expense_date),
        "EXP HEAD": item.expense_head_name || "",
        "PARTICULARS": item.particulars || "",
        "TO": item.to || "",
        "PAID BY": item.paid_by || "",
        "AMOUNT": Number(item.amount || 0),
        "PAYMENT METHOD": item.paid_via || "",
        "PAYMENT TYPE": item.payment_type || ""
    }));


    // =========================
    // SHEET 2 - EXPENSE TOTALS
    // =========================

    const expenseTotals = {};

    filteredData.forEach(item => {
        const head = item.expense_head_name || "Unknown";

        if (!expenseTotals[head]) {
            expenseTotals[head] = 0;
        }

        expenseTotals[head] += Number(item.amount || 0);
    });

    const summaryRows = Object.entries(expenseTotals)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([head, total]) => ({
            "EXPENSE HEAD": head,
            "TOTAL AMOUNT": total.toFixed(2)
        }));


    // =========================
    // WORKBOOK
    // =========================

    const workbook = XLSX.utils.book_new();

    const detailsSheet = XLSX.utils.json_to_sheet(expenseRows);
    XLSX.utils.book_append_sheet(
        workbook,
        detailsSheet,
        "Expense Details"
    );

    const summarySheet = XLSX.utils.json_to_sheet(summaryRows);
    XLSX.utils.book_append_sheet(
        workbook,
        summarySheet,
        "Expense Summary"
    );


    // =========================
    // FILE NAME
    // =========================

    const today = new Date().toISOString().split('T')[0];

    let fileName;

    if (startDate || endDate) {
        fileName = `${currentCashType}_Expense_Summary_${startDate || 'START'}_to_${endDate || 'END'}.xlsx`;
    } else {
        fileName = `${currentCashType}_All_Expense_Summary_As_On_${today}.xlsx`;
    }

    XLSX.writeFile(workbook, fileName);
}

