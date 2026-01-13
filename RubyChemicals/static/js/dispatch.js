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
    table.innerHTML = `
      <tr><th>Date</th><th>Customer</th><th>Product</th><th>Qty</th></tr>
      ${res.data.map(d => `
        <tr>
          <td>${d.dispatch_date}</td>
          <td>${d.customer_name}</td>
          <td>${d.stock_item_name}</td>
          <td>${d.quantity}</td>
        </tr>
      `).join("")}
    `
  }
}
