const loginView = document.getElementById("adminLogin");
const appView = document.getElementById("adminApp");
const toast = document.getElementById("adminToast");
const loginMessage = document.getElementById("adminLoginMessage");
const loginButton = document.getElementById("adminLoginButton");
const isLoginPage = Boolean(document.getElementById("adminLoginForm"));
const isDashboardPage = Boolean(document.getElementById("adminApp")) && !isLoginPage;
let adminProductsCache = [];

function showAdminToast(message, type = "success") {
  if (!toast) return;
  toast.textContent = message;
  toast.className = `admin-toast ${type}`;
  toast.hidden = false;
  window.setTimeout(() => { toast.hidden = true; }, 2500);
}

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
  } catch (err) {
    throw new Error(`Cannot reach backend at ${API_BASE}. Start Flask with: python app.py`);
  }
  const data = await res.json().catch(() => ({ success: false, message: "Backend returned an invalid response" }));
  if (res.status === 401 && !path.includes("/admin/login")) {
    if (isDashboardPage) window.location.href = "admin.html";
    if (loginView) loginView.hidden = false;
    if (appView && !isDashboardPage) appView.hidden = true;
  }
  if (!data.success) throw new Error(data.message || "Request failed");
  return data;
}

function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

function boolValue(value) {
  return value === true || value === 1 || value === "1";
}

function setPanel(panelId) {
  document.querySelectorAll(".admin-nav").forEach(btn => btn.classList.toggle("active", btn.dataset.panel === panelId));
  document.querySelectorAll(".admin-panel").forEach(panel => panel.classList.toggle("active", panel.id === panelId));
}

async function checkAdmin() {
  try {
    const data = await api("/admin/me");
    if (isLoginPage && data.logged_in) {
      window.location.href = "admin-dashboard.html";
      return;
    }
    if (isDashboardPage && !data.logged_in) {
      window.location.href = "admin.html";
      return;
    }
    if (loginView) loginView.hidden = data.logged_in;
    if (appView && !isDashboardPage) appView.hidden = !data.logged_in;
    if (isDashboardPage && data.logged_in) await loadAll();
  } catch {
    if (isDashboardPage) window.location.href = "admin.html";
    if (loginView) loginView.hidden = false;
    if (appView && !isDashboardPage) appView.hidden = true;
  }
}

async function loadDashboard() {
  const data = await api("/admin/dashboard");
  const labels = [
    ["total_products", "Total products"], ["active_products", "Active products"],
    ["total_customers", "Total customers"], ["total_orders", "Total orders"],
    ["today_orders", "Today's orders"], ["total_sales", "Total sales", true],
    ["today_sales", "Today's sales", true], ["pending_orders", "Pending orders"],
    ["delivered_orders", "Delivered orders"], ["low_stock_products", "Low stock"],
    ["out_of_stock_products", "Out of stock"]
  ];
  document.getElementById("statsGrid").innerHTML = labels.map(([key, label, currency]) => `
    <article class="admin-stat"><span>${label}</span><strong>${currency ? money(data.stats[key]) : Number(data.stats[key] || 0)}</strong></article>
  `).join("");
}

function productPayload() {
  const rawWeight = document.getElementById("productWeight").value.trim();
  const weightMatch = rawWeight.match(/^([\d.]+)\s*([a-zA-Z]+)$/);
  return {
    name: document.getElementById("productName").value.trim(),
    category: document.getElementById("productCategory").value.trim(),
    price: document.getElementById("productPrice").value,
    compare_price: document.getElementById("productComparePrice").value,
    weight: weightMatch ? weightMatch[1] : rawWeight,
    unit: weightMatch ? weightMatch[2] : "",
    stock: document.getElementById("productStock").value,
    low_stock_limit: document.getElementById("productLowStock").value,
    image_url: document.getElementById("productImage").value.trim() || "/images/default-product.jpg",
    description: document.getElementById("productDescription").value.trim(),
    is_featured: document.getElementById("productFeatured").checked,
    is_best_seller: document.getElementById("productBestSeller").checked,
    is_active: document.getElementById("productActive").checked
  };
}

function resetProductForm() {
  document.getElementById("productForm").reset();
  document.getElementById("productId").value = "";
  document.getElementById("productLowStock").value = 10;
  document.getElementById("productActive").checked = true;
}

function fillProductForm(product) {
  document.getElementById("productId").value = product.id;
  document.getElementById("productName").value = product.name || "";
  document.getElementById("productCategory").value = product.category || "";
  document.getElementById("productPrice").value = product.price || "";
  document.getElementById("productComparePrice").value = product.original_price || "";
  document.getElementById("productWeight").value = `${product.weight || ""}${product.unit ? product.unit : ""}`;
  document.getElementById("productStock").value = product.stock || 0;
  document.getElementById("productLowStock").value = product.low_stock_limit || 10;
  document.getElementById("productImage").value = product.image_url || "";
  document.getElementById("productDescription").value = product.description || "";
  document.getElementById("productFeatured").checked = boolValue(product.is_featured);
  document.getElementById("productBestSeller").checked = boolValue(product.is_best_seller);
  document.getElementById("productActive").checked = boolValue(product.is_active);
  setPanel("productsPanel");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadProducts() {
  const search = encodeURIComponent(document.getElementById("productSearch").value.trim());
  const category = encodeURIComponent(document.getElementById("productCategoryFilter").value);
  const data = await api(`/admin/products?search=${search}&category=${category}`);
  adminProductsCache = data.products || [];
  const cats = ["all", ...new Set(adminProductsCache.map(item => item.category).filter(Boolean))];
  const current = document.getElementById("productCategoryFilter").value;
  document.getElementById("productCategoryFilter").innerHTML = cats.map(cat => `<option value="${cat}">${cat === "all" ? "All categories" : cat}</option>`).join("");
  document.getElementById("productCategoryFilter").value = cats.includes(current) ? current : "all";
  document.getElementById("productsTable").innerHTML = `
    <table><thead><tr><th>Product</th><th>Price</th><th>Stock</th><th>Status</th><th></th></tr></thead><tbody>
    ${adminProductsCache.map(product => `
      <tr>
        <td><strong>${product.name}</strong><span>${product.category || ""}</span></td>
        <td>${money(product.price)}${Number(product.original_price || 0) > Number(product.price || 0) ? `<span>MRP ${money(product.original_price)}</span>` : ""}</td>
        <td>${product.stock}<span>Low at ${product.low_stock_limit || 10}</span></td>
        <td>${boolValue(product.is_active) ? "Active" : "Hidden"}</td>
        <td><button data-edit-product="${product.id}">Edit</button></td>
      </tr>`).join("")}
    </tbody></table>`;
}

async function loadOrders() {
  const q = encodeURIComponent(document.getElementById("orderSearch").value.trim());
  const status = encodeURIComponent(document.getElementById("orderStatusFilter").value);
  const data = await api(`/admin/orders?q=${q}&status=${status}`);
  document.getElementById("ordersTable").innerHTML = `
    <table><thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Status</th></tr></thead><tbody>
    ${(data.orders || []).map(order => `
      <tr>
        <td><strong>${order.order_number}</strong><span>${new Date(order.created_at).toLocaleString()}</span></td>
        <td><strong>${order.customer_phone}</strong><span>${[order.house, order.street, order.area, order.city, order.pincode].filter(Boolean).join(", ")}</span></td>
        <td>${(order.items || []).map(item => `${item.product_name} x${item.quantity}`).join("<br>")}</td>
        <td>${money(order.grand_total)}<span>${order.payment_method} / ${order.payment_status}</span></td>
        <td><select data-order-status="${order.id}">
          ${["CONFIRMED", "PACKING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"].map(status => `<option ${order.order_status === status ? "selected" : ""}>${status}</option>`).join("")}
        </select></td>
      </tr>`).join("")}
    </tbody></table>`;
}

async function loadCustomers() {
  const data = await api("/admin/customers");
  document.getElementById("customersTable").innerHTML = `
    <table><thead><tr><th>Phone</th><th>Orders</th><th>Purchase value</th><th>Status</th></tr></thead><tbody>
    ${(data.customers || []).map(customer => `
      <tr>
        <td><strong>${customer.phone}</strong><span>Joined ${new Date(customer.created_at).toLocaleDateString()}</span></td>
        <td>${customer.total_orders || 0}<span>${customer.most_recent_order_date ? `Last ${new Date(customer.most_recent_order_date).toLocaleDateString()}` : "No orders"}</span></td>
        <td>${money(customer.total_purchase_value)}</td>
        <td><button data-block-customer="${customer.id}" data-blocked="${boolValue(customer.is_blocked) ? "1" : "0"}">${boolValue(customer.is_blocked) ? "Unblock" : "Block"}</button></td>
      </tr>`).join("")}
    </tbody></table>`;
}

async function loadAll() {
  await Promise.all([loadDashboard(), loadProducts(), loadOrders(), loadCustomers()]);
}

document.getElementById("adminLoginForm")?.addEventListener("submit", async event => {
  event.preventDefault();
  loginMessage.textContent = "";
  loginButton.disabled = true;
  loginButton.textContent = "Logging in...";
  try {
    await api("/admin/login", {
      method: "POST",
      body: JSON.stringify({
        username: document.getElementById("adminUsername").value.trim(),
        password: document.getElementById("adminPassword").value.trim()
      })
    });
    window.location.href = "admin-dashboard.html";
  } catch (err) {
    loginMessage.textContent = err.message || "Admin login failed";
  } finally {
    loginButton.disabled = false;
    loginButton.textContent = "Login";
  }
});

document.querySelectorAll(".admin-nav").forEach(btn => btn.addEventListener("click", () => setPanel(btn.dataset.panel)));
document.getElementById("refreshDashboard")?.addEventListener("click", () => loadAll().then(() => showAdminToast("Dashboard refreshed")));
document.getElementById("resetProductForm")?.addEventListener("click", resetProductForm);
document.getElementById("productSearch")?.addEventListener("input", loadProducts);
document.getElementById("productCategoryFilter")?.addEventListener("change", loadProducts);
document.getElementById("orderSearch")?.addEventListener("input", loadOrders);
document.getElementById("orderStatusFilter")?.addEventListener("change", loadOrders);
document.getElementById("adminLogout")?.addEventListener("click", async () => {
  await api("/admin/logout", { method: "POST" });
  window.location.href = "admin.html";
});

document.getElementById("productForm")?.addEventListener("submit", async event => {
  event.preventDefault();
  const id = document.getElementById("productId").value;
  await api(id ? `/admin/products/${id}` : "/admin/products", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(productPayload())
  });
  resetProductForm();
  await Promise.all([loadDashboard(), loadProducts()]);
  showAdminToast("Product saved");
});

document.addEventListener("click", async event => {
  const editButton = event.target.closest("[data-edit-product]");
  const blockButton = event.target.closest("[data-block-customer]");
  if (editButton) {
    const product = adminProductsCache.find(item => Number(item.id) === Number(editButton.dataset.editProduct));
    if (product) fillProductForm(product);
  }
  if (blockButton) {
    const blocked = blockButton.dataset.blocked === "1";
    await api(`/admin/customers/${blockButton.dataset.blockCustomer}/block`, {
      method: "PATCH",
      body: JSON.stringify({ is_blocked: !blocked })
    });
    await loadCustomers();
    showAdminToast("Customer updated");
  }
});

document.addEventListener("change", async event => {
  const statusSelect = event.target.closest("[data-order-status]");
  if (!statusSelect) return;
  if (statusSelect.value === "CANCELLED" && !confirm("Cancel this order and restore stock?")) {
    await loadOrders();
    return;
  }
  await api(`/admin/orders/${statusSelect.dataset.orderStatus}/status`, {
    method: "PATCH",
    body: JSON.stringify({ order_status: statusSelect.value })
  });
  await Promise.all([loadDashboard(), loadOrders(), loadProducts()]);
  showAdminToast("Order status updated");
});

checkAdmin();
