let csrf, endpoints

function init(csrfToken, eps){
  csrf = csrfToken
  endpoints = eps
  loadHeads()
  loadExpenses()
}

async function loadHeads(){
  const [ok, res] = await callApi("GET", endpoints.heads)
  if(ok){
    document.getElementById("expenseHead").innerHTML =
      res.data.map(h => `<option value="${h.id}">${h.name}</option>`).join("")
  }
}

async function createHead(){
  const name = document.getElementById("newHead").value
  await callApi("POST", endpoints.heads, {name}, csrf)
  loadHeads()
}

async function createExpense(){
  const payload = {
    expense_head_id: document.getElementById("expenseHead").value,
    amount: document.getElementById("expenseAmount").value,
    expense_date: document.getElementById("expenseDate").value,
    notes: document.getElementById("expenseNotes").value
  }

  await callApi("POST", endpoints.cash, payload, csrf)
  loadExpenses()
}

async function loadExpenses(){
  const [ok, res] = await callApi("GET", endpoints.cash)
  if(ok){
    const table = document.getElementById("expenseTable")
    const headers = `<thead><tr><th><i class="fas fa-calendar"></i> Date</th><th><i class="fas fa-tag"></i> Head</th><th><i class="fas fa-rupee-sign"></i> Amount</th><th><i class="fas fa-notes-medical"></i> Notes</th></tr></thead>`
    const rows = res.data.map(e => `
      <tr>
        <td>${e.expense_date}</td>
        <td><span style="background: #f3e8ff; color: #7e22ce; padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;">${e.expense_head_name}</span></td>
        <td><strong style="color: #059669;">₹ ${parseFloat(e.amount).toFixed(2)}</strong></td>
        <td>${e.notes || "<em style='color: #94a3b8;'>—</em>"}</td>
      </tr>
    `).join("")
    table.innerHTML = headers + `<tbody>${rows}</tbody>`
  }
}
