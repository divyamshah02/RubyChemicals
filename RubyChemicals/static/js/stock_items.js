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
  const headers = `<thead><tr><th><i class="fas fa-cube"></i> Name</th><th><i class="fas fa-layer-group"></i> Group</th><th><i class="fas fa-weight"></i> Quantity</th><th><i class="fas fa-cogs"></i> Action</th></tr></thead>`
  const rows = items.map(i => `
    <tr>
      <td>${i.name}</td>
      <td><span style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;">${i.group_name}</span></td>
      <td><strong>${i.current_quantity}</strong></td>
      <td>
        <button class="btn btn-sm btn-success" onclick="openInward(${i.id})"><i class="fas fa-arrow-down"></i> Inward</button>
      </td>
    </tr>
  `).join("")
  table.innerHTML = headers + `<tbody>${rows}</tbody>`
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
