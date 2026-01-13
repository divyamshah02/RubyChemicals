let csrf, endpoints, selectedItemId = null

function init(csrfToken, eps) {
  csrf = csrfToken
  endpoints = eps
  loadGroups()
  loadItems()
}

async function loadGroups() {
  const [ok, res] = await callApi("GET", endpoints.groups)
  if(ok){
    document.getElementById("itemGroup").innerHTML =
      res.data.map(g => `<option value="${g.id}">${g.name}</option>`).join("")
  }
}

async function loadItems() {
  const [ok, res] = await callApi("GET", endpoints.items)
  if(ok) renderItems(res.data)
}

function renderItems(items){
  const table = document.getElementById("itemTable")
  table.innerHTML = `
    <tr><th>Name</th><th>Group</th><th>Qty</th><th>Action</th></tr>
    ${items.map(i => `
      <tr>
        <td>${i.name}</td>
        <td>${i.group_name}</td>
        <td>${i.current_quantity}</td>
        <td>
          <button class="btn btn-sm btn-success" onclick="openInward(${i.id})">Inward</button>
        </td>
      </tr>
    `).join("")}
  `
}

async function createItem(){
  const payload = {
    name: document.getElementById("itemName").value,
    group: document.getElementById("itemGroup").value,
    unit: document.getElementById("itemUnit").value
  }
  await callApi("POST", endpoints.items, payload, csrf)
  loadItems()
}

function openInward(id){
  selectedItemId = id
  new bootstrap.Modal(document.getElementById("inwardModal")).show()
}

async function markInward(){
  const payload = {
    stock_item_id: selectedItemId,
    quantity: document.getElementById("inwardQty").value,
    date: document.getElementById("inwardDate").value
  }
  await callApi("POST", endpoints.inward, payload, csrf)
  loadItems()
}
