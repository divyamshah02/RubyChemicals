let csrf, endpoints;
let currentCashType = 'office';
let headsByType = {};
let allTransactions = [];
let accounts = {};

function init(csrfToken, eps) {
  csrf = csrfToken;
  endpoints = eps;
  selectCashType('office');
}

function selectCashType(cashType) {
  currentCashType = cashType;

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
    document.getElementById("expenseHead").innerHTML = '<option value="">Select Expense Head</option>' + res.data
      .filter(h => h.is_active)
      .map(h => `<option value="${h.id}">${h.name}</option>`).join("");
  }
}

async function loadAllTransactions() {
  const [ok, res] = await callApi("GET", endpoints.cash);
  if (ok && res.data) {
    allTransactions = res.data;
    renderAllTransactionsTab();
    renderExpenseHeadsTab();
  }
}

function renderAllTransactionsTab() {
  const table = document.getElementById("allTransactionsTable");
  
  const filteredTransactions = allTransactions.filter(t => t.cash_type === currentCashType);
  
  if (filteredTransactions.length === 0) {
    table.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4">No transactions</td></tr>';
    return;
  }
  
  table.innerHTML = filteredTransactions.map(trans => `
    <tr>
      <td>${trans.expense_date}</td>
      <td>
        <strong>${trans.expense_head_name}</strong>
      </td>
      <td>${trans.to || '—'}</td>
      <td>${trans.paid_by || '—'}</td>
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
        ${trans.transaction_type === 'debit' ? `
          <button class="btn btn-sm btn-outline-primary" onclick="downloadPettyCashPDF(${trans.id})" title="Download PDF">
            <i class="fas fa-file-pdf"></i> Download Challan
          </button>
        ` : '—'}
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

  const payload = {
    cash_type: currentCashType,
    expense_head_id: parseInt(headId),
    expense_date: date,
    amount: amount,
    transaction_type: 'debit',
    notes: notes,
    to: to,
    paid_via: paidVia,
    payment_type: paymentType,
    particulars: particulars,
    paid_by: paidBy
  };

  const [ok, res] = await callApi("POST", endpoints.cash, payload, csrf);
  if (ok && res.success) {
    alert("Expense added successfully!");
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

  toggle_loader()
  window.location = `/operation-api/download-petty-cash-api/${pettyCashId}/`
  toggle_loader()  
}



