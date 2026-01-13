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
  table.innerHTML = groups.map(g => `<tr><td>${g.name}</td></tr>`).join("")
}

async function createGroup(){
  const name = document.getElementById("groupName").value
  await callApi("POST", endpoints.create, {name}, csrf)
  loadGroups()
}
