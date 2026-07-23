const cartItemsContainer = document.getElementById("cartItemsContainer");
const cartSummary = document.getElementById("cartSummary");
const cartTotal = document.getElementById("cartTotal");
const summaryLines = document.getElementById("summaryLines");
const emptyCartBtn = document.getElementById("emptyCartBtn");

let currentItems = [];

function rupee(value) {
  return HealthymaCart?.formatCurrency ? HealthymaCart.formatCurrency(value) : `Rs.${Number(value || 0).toFixed(2)}`;
}

function safeCartImage(item) {
  const name = (item.name || "").toLowerCase();
  const category = item.category || "";
  if (name.includes("moringa")) return "images/moringa-mix-powder.jpeg";
  if (name.includes("curry")) return "images/curry-leaf-mix.jpeg";
  if (name.includes("millet atta")) return "images/millet-atta.jpeg";
  if (name.includes("kambu") || name.includes("ragi")) return "images/kambu-ragi-mix.jpeg";
  if (name.includes("corn")) return "images/corn-flour.jpeg";
  if (category === "Health Mix") return "images/moringa-mix-powder.jpeg";
  if (category === "Millet Flour") return "images/millet-atta.jpeg";
  if (category === "Flour") return "images/corn-flour.jpeg";
  if (item.image_url?.startsWith("/images/")) return `.${item.image_url}`;
  return item.image_url || "images/default-product.jpg";
}

function showEmpty(message = "Your cart is empty.") {
  cartItemsContainer.innerHTML = `<div class="empty-state"><p>${message}</p><br><button class="primary-pill" onclick="window.location.href='products.html'">Explore Products</button></div>`;
  cartSummary.style.display = "none";
}

function redirectToLogin() {
  window.location.href = "login.html";
}

function renderSummary(totals) {
  const rows = [
    ["Subtotal", totals.subtotal],
    ["Product discount", `-${rupee(totals.product_discount)}`],
    ["Coupon discount", `-${rupee(totals.coupon_discount)}`],
    ["Delivery fee", rupee(totals.delivery_fee)],
    ["COD fee", rupee(totals.cod_fee)],
    ["Tax", rupee(totals.tax_amount)]
  ];
  summaryLines.innerHTML = rows
    .filter(([, value]) => !String(value).includes("Rs.0.00") || value === totals.delivery_fee)
    .map(([label, value]) => `<div><span>${label}</span><strong>${String(value).startsWith("Rs.") || String(value).startsWith("-") ? value : rupee(value)}</strong></div>`)
    .join("");
  cartTotal.textContent = rupee(totals.grand_total);
  cartSummary.style.display = "block";
}

function render(items, validation) {
  if (!items.length) {
    showEmpty();
    return;
  }

  cartItemsContainer.innerHTML = "";
  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "cart-item rich-cart-item";
    const unitPrice = item.unit_price || item.price;
    const lineTotal = item.line_total || (Number(unitPrice) * Number(item.quantity));
    row.innerHTML = `
      <img src="${safeCartImage(item)}" alt="${item.name}" onerror="this.onerror=null;this.src='images/default-product.jpg'">
      <div class="details">
        <h4>${item.name}</h4>
        <small>${item.package_size || [item.weight, item.unit].filter(Boolean).join(" ") || "Pack"}</small>
        <span>${rupee(unitPrice)} each</span>
        ${item.stock <= item.quantity ? `<small class="stock-warning">Only ${item.stock} available</small>` : ""}
      </div>
      <div class="qty-control">
        <button data-action="minus" data-cart-id="${item.cart_id}" data-qty="${item.quantity}">-</button>
        <strong>${item.quantity}</strong>
        <button data-action="plus" data-cart-id="${item.cart_id}" data-qty="${item.quantity}" data-stock="${item.stock || 9999}">+</button>
      </div>
      <strong class="item-total">${rupee(lineTotal)}</strong>
      <button class="remove-btn" data-action="remove" data-cart-id="${item.cart_id}">Remove</button>`;
    cartItemsContainer.appendChild(row);
  });

  document.querySelectorAll("[data-action]").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const qty = Number(btn.dataset.qty || 1);
      if (action === "minus") return updateQuantity(btn.dataset.cartId, Math.max(0, qty - 1));
      if (action === "plus") {
        const stock = Number(btn.dataset.stock || 9999);
        if (qty + 1 > stock) return alert(`Only ${stock} left in stock.`);
        return updateQuantity(btn.dataset.cartId, qty + 1);
      }
      return updateQuantity(btn.dataset.cartId, 0);
    });
  });

  renderSummary(validation.totals);
}

async function validateCart(items, paymentMethod = "") {
  const body = {
    payment_method: paymentMethod,
    items: items.map(item => ({ product_id: item.product_id, quantity: item.quantity }))
  };
  const res = await fetch(`${API_BASE}/cart/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (res.status === 401) redirectToLogin();
  if (!data.success) throw new Error(data.message || "Could not validate cart");
  return data;
}

async function loadCart() {
  cartItemsContainer.innerHTML = `<div class="empty-state"><p>Loading cart...</p></div>`;
  try {
    const res = await fetch(`${API_BASE}/cart`, { credentials: "include" });
    const data = await res.json();
    if (res.status === 401) return redirectToLogin();
    if (!data.success || !data.items.length) return showEmpty();
    currentItems = data.items;
    HealthymaCart.saveCart(currentItems.map(item => HealthymaCart.normalizeProduct(item, Number(item.quantity || 0))));
    const validation = await validateCart(currentItems);
    const validatedById = new Map(validation.items.map(item => [item.product_id, item]));
    const merged = currentItems.map(item => ({ ...item, ...(validatedById.get(item.product_id) || {}) }));
    render(merged, validation);
  } catch (err) {
    showEmpty(err.message || "Could not reach server. Please make sure backend is running.");
  }
}

async function updateQuantity(cartId, quantity) {
  const item = currentItems.find(entry => Number(entry.cart_id) === Number(cartId));
  try {
    const res = await fetch(`${API_BASE}/cart/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ cart_id: cartId, quantity })
    });
    const data = await res.json();
    if (res.status === 401) return redirectToLogin();
    if (!data.success) return alert(data.message || "Could not update cart");
    if (item) HealthymaCart.setProductQuantity(item, quantity, false);
  } catch (err) {
    return alert("Could not update cart. Please try again.");
  }
  loadCart();
}

async function emptyCart() {
  for (const item of [...currentItems]) await updateQuantity(item.cart_id, 0);
  HealthymaCart.clearCart();
}

document.getElementById("proceedBtn").addEventListener("click", () => window.location.href = "checkout.html");
emptyCartBtn.addEventListener("click", emptyCart);
loadCart();
