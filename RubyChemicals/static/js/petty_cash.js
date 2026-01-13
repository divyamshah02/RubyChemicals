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
    table.innerHTML = `
      <tr><th>Date</th><th>Head</th><th>Amount</th><th>Notes</th></tr>
      ${res.data.map(e => `
        <tr>
          <td>${e.expense_date}</td>
          <td>${e.expense_head_name}</td>
          <td>${e.amount}</td>
          <td>${e.notes || ""}</td>
        </tr>
      `).join("")}
    `
  }
}
