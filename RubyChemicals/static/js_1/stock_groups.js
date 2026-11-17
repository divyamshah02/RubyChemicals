let csrf, endpoints

function init(csrfToken, eps) {
  csrf = csrfToken
  endpoints = eps
  loadGroups()
}

async function loadGroups() {
  const [ok, res] = await callApi("GET", endpoints.list)
  if(ok) render(res.data)
}

function render(groups){
  const table = document.getElementById("groupTable")
  const headers = `<thead><tr><th><i class="fas fa-layer-group"></i> Group Name</th></tr></thead>`
  const rows = groups.map(g => `<tr><td>${g.name}</td></tr>`).join("")
  table.innerHTML = headers + `<tbody>${rows}</tbody>`
}

async function createGroup(){
  const name = document.getElementById("groupName").value
  await callApi("POST", endpoints.create, {name}, csrf)
  loadGroups()
}
