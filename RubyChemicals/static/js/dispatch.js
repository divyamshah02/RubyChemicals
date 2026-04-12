let csrf, endpoints, stockItems = []

function init(csrfToken, eps){
  csrf = csrfToken
  endpoints = eps
  loadStock()
  loadDispatches()
}

async function loadStock(){
  const [ok, res] = await callApi("GET", endpoints.stock)
  if(ok){
    stockItems = res.data
    document.getElementById("dispatchItem").innerHTML =
      stockItems.map(i => `<option value="${i.id}">${i.name}</option>`).join("")
  }
}

async function createDispatch(){
  const payload = {
    stock_item_id: document.getElementById("dispatchItem").value,
    quantity: document.getElementById("dispatchQty").value,
    customer_name: document.getElementById("dispatchCustomer").value,
    dispatch_date: document.getElementById("dispatchDate").value
  }

  await callApi("POST", endpoints.dispatch, payload, csrf)
  loadDispatches()
}

async function loadDispatches(){
  const [ok, res] = await callApi("GET", endpoints.dispatch)
  if(ok){
    const table = document.getElementById("dispatchTable")
    const headers = `<thead><tr><th><i class="fas fa-calendar"></i> Date</th><th><i class="fas fa-user"></i> Customer</th><th><i class="fas fa-cube"></i> Product</th><th><i class="fas fa-weight"></i> Quantity</th></tr></thead>`
    const rows = res.data.map(d => `
      <tr>
        <td>${d.dispatch_date}</td>
        <td><strong>${d.customer_name}</strong></td>
        <td>${d.stock_item_name}</td>
        <td><span style="background: #bfdbfe; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-weight: 600;">${d.quantity}</span></td>
      </tr>
    `).join("")
    table.innerHTML = headers + `<tbody>${rows}</tbody>`
  }
}
