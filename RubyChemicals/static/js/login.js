// Admin Login Page State
let admin_auth_url = null
let csrf_token = null

// Initialize Admin Login Page
async function initAdminLogin(auth_url_param, csrf_token_param) {
  admin_auth_url = auth_url_param
  csrf_token = csrf_token_param

  setupAdminLoginForm()

  // Check if already logged in
  await checkAdminLoginStatus()
}

function setupAdminLoginForm() {
  const loginForm = document.getElementById("adminLoginForm")

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault()
    await adminLogin()
  })

  // Handle Enter key on inputs
  document.getElementById("username").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault()
      document.getElementById("password").focus()
    }
  })

  document.getElementById("password").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault()
      adminLogin()
    }
  })
}

// Check if admin is already logged in
async function checkAdminLoginStatus() {
  const [success, response] = await callApi("GET", admin_auth_url, null, csrf_token)

  if (success && response.success && response.data.logged_in) {
    // Already logged in, redirect to admin dashboard
    window.location.href = "/admin-dashboard/"
  }
}

// Admin Login
async function adminLogin() {
  const usernameInput = document.getElementById("username")
  const passwordInput = document.getElementById("password")
  const loginBtn = document.getElementById("loginBtn")

  const username = usernameInput.value.trim()
  const password = passwordInput.value.trim()

  if (!username) {
    showAlert("Please enter your username", "danger")
    usernameInput.focus()
    return
  }

  if (!password) {
    showAlert("Please enter your password", "danger")
    passwordInput.focus()
    return
  }

  setButtonLoading(loginBtn, true)
  hideAlert()

  const requestData = {
    email: username,
    password: password,
  }

  const [success, response] = await callApi("POST", admin_auth_url, requestData, csrf_token)

  setButtonLoading(loginBtn, false)

  if (success && response.success) {
    showAlert("Login successful! Redirecting...", "success")

    // Clear form
    usernameInput.value = ""
    passwordInput.value = ""

    // Redirect to admin dashboard
    setTimeout(() => {
      window.location.href = "/admin-dashboard/"
    }, 1000)
  } else {
    const errorMessage = response.error || "Login failed. Please try again."
    showAlert(errorMessage, "danger")
    passwordInput.value = ""
    passwordInput.focus()
  }
}

// UI Helper Functions
function setButtonLoading(button, isLoading) {
  const btnText = button.querySelector(".btn-text")
  const spinner = button.querySelector(".spinner-border")

  if (isLoading) {
    btnText.textContent = "Logging in..."
    spinner.classList.remove("d-none")
    button.disabled = true
  } else {
    btnText.textContent = "Login to Admin Portal"
    spinner.classList.add("d-none")
    button.disabled = false
  }
}

function showAlert(message, type) {
  const alertContainer = document.getElementById("alertContainer")
  alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `
}

function hideAlert() {
  const alertContainer = document.getElementById("alertContainer")
  alertContainer.innerHTML = ""
}
