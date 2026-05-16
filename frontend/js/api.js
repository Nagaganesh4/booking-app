/* ═══════════════════════════════════════════════════════════════════════════
   API Wrapper — centralized fetch with JWT injection
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin + "/api";

const api = {
  getToken() {
    return localStorage.getItem("cinebook_token");
  },

  setToken(token) {
    localStorage.setItem("cinebook_token", token);
  },

  getUser() {
    const u = localStorage.getItem("cinebook_user");
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    localStorage.setItem("cinebook_user", JSON.stringify(user));
  },

  logout() {
    localStorage.removeItem("cinebook_token");
    localStorage.removeItem("cinebook_user");
    window.location.href = "/login.html";
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  isAdmin() {
    const u = this.getUser();
    return u && u.role === "admin";
  },

  async request(method, path, body = null, isFormData = false) {
    const headers = {};
    const token = this.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!isFormData) headers["Content-Type"] = "application/json";

    const options = { method, headers };
    if (body) {
      options.body = isFormData ? body : JSON.stringify(body);
    }

    const res = await fetch(`${API_BASE}${path}`, options);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body, isFormData = false) { return this.request("POST", path, body, isFormData); },
  put(path, body) { return this.request("PUT", path, body); },
  delete(path) { return this.request("DELETE", path); },
};

/* ── Toast Notification ───────────────────────────────────────────────────── */
function showToast(message, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ── Navbar Auth State ────────────────────────────────────────────────────── */
function updateNavbar() {
  const authLinks = document.getElementById("auth-links");
  if (!authLinks) return;

  if (api.isLoggedIn()) {
    const user = api.getUser();
    authLinks.innerHTML = `
      <a href="/my_bookings.html">My Bookings</a>
      <span style="color:var(--text-muted); font-size:0.85rem;">Hi, ${user?.name || "User"}</span>
      <button class="btn btn-sm btn-ghost" onclick="api.logout()">Logout</button>
    `;
  } else {
    authLinks.innerHTML = `
      <a href="/login.html" class="btn btn-sm btn-outline">Login</a>
      <a href="/register.html" class="btn btn-sm btn-primary">Sign Up</a>
    `;
  }
}

document.addEventListener("DOMContentLoaded", updateNavbar);
