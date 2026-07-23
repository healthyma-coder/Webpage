let whatsappUrl = null;
let instagramUrl = null;
let selectedMethod = "COD";
let selectedAddressId = null;
let latestValidation = null;
let placingOrder = false;

const addressList = document.getElementById("addressList");
const summaryBox = document.getElementById("orderSummaryBox");
const checkoutMessage = document.getElementById("checkoutMessage");
const placeOrderBtn = document.getElementById("placeOrderBtn");
const agreeOrder = document.getElementById("agreeOrder");
const codFeeText = document.getElementById("codFeeText");
const onlineStatusText = document.getElementById("onlineStatusText");

function rupee(value) {
  return `Rs.${Number(value || 0).toFixed(2)}`;
}

function setMessage(message, isError = false) {
  checkoutMessage.textContent = message;
  checkoutMessage.classList.toggle("error", isError);
}

function redirectToLogin() {
  window.location.href = "login.html";
}

function localSavedAddress() {
  const addresses = JSON.parse(localStorage.getItem("healthyma_delivery_addresses") || "[]");
  const activeId = localStorage.getItem("healthyma_active_address_id");
  return addresses.find(address => address.id === activeId)
    || JSON.parse(localStorage.getItem("healthyma_delivery_address") || "null");
}

function apiAddressFromLocal(saved) {
  if (!saved) return null;
  return {
    full_name: saved.fullName || saved.full_name || "Healthyma Customer",
    mobile: saved.phone || saved.mobile || "",
    house: saved.addressLine || saved.house || "",
    street: saved.addressLine || saved.street || "",
    area: saved.area || "",
    city: saved.city || "",
    state: saved.state || "Tamil Nadu",
    pincode: saved.pincode || "",
    delivery_instructions: saved.deliveryNote || saved.delivery_instructions || "",
    latitude: saved.latitude || "",
    longitude: saved.longitude || "",
    is_default: true
  };
}

async function migrateLocalAddressIfNeeded(addresses) {
  if (addresses.length) return addresses;
  const saved = apiAddressFromLocal(localSavedAddress());
  if (!saved || !saved.mobile || !saved.pincode) return addresses;

  const res = await fetch(`${API_BASE}/addresses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(saved)
  });
  if (res.status === 401) return redirectToLogin();
  return loadAddresses(false);
}

function renderAddresses(addresses) {
  if (!addresses.length) {
    addressList.innerHTML = `<div class="empty-address-book">No saved address found. <a href="location.html">Add delivery address</a></div>`;
    selectedAddressId = null;
    return;
  }

  selectedAddressId = selectedAddressId || (addresses.find(item => item.is_default) || addresses[0]).id;
  addressList.innerHTML = addresses.map(address => {
    const line = [address.house, address.street, address.area, address.city, address.pincode].filter(Boolean).join(", ");
    return `
      <button class="checkout-address ${Number(selectedAddressId) === Number(address.id) ? "selected" : ""}" type="button" data-id="${address.id}">
        <strong>${address.full_name}</strong>
        <span>${line}</span>
        <em>${address.mobile}${address.is_default ? " | Default" : ""}</em>
      </button>`;
  }).join("");

  document.querySelectorAll(".checkout-address").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedAddressId = Number(btn.dataset.id);
      renderAddresses(addresses);
    });
  });
}

async function loadAddresses(allowMigration = true) {
  const res = await fetch(`${API_BASE}/addresses`, { credentials: "include" });
  const data = await res.json();
  if (res.status === 401) return redirectToLogin();
  if (!data.success) throw new Error(data.message || "Could not load addresses");
  const addresses = allowMigration ? await migrateLocalAddressIfNeeded(data.addresses) : data.addresses;
  renderAddresses(addresses || []);
  return addresses || [];
}

async function validateCart() {
  const res = await fetch(`${API_BASE}/cart/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ payment_method: selectedMethod })
  });
  const data = await res.json();
  if (res.status === 401) return redirectToLogin();
  if (!data.success) throw new Error(data.message || "Could not validate cart");
  latestValidation = data;
  return data;
}

function renderSummary(data) {
  const totals = data.totals;
  codFeeText.textContent = `COD fee: ${rupee(totals.cod_fee)}`;
  onlineStatusText.textContent = data.payment_options.online_payment_enabled
    ? "Razorpay test checkout enabled."
    : "Enable Razorpay keys on backend.";
  summaryBox.innerHTML = `
    <div class="summary-lines">
      <div><span>Items</span><strong>${data.items.reduce((sum, item) => sum + Number(item.quantity), 0)}</strong></div>
      <div><span>Subtotal</span><strong>${rupee(totals.subtotal)}</strong></div>
      <div><span>Delivery fee</span><strong>${rupee(totals.delivery_fee)}</strong></div>
      ${Number(totals.cod_fee) ? `<div><span>COD fee</span><strong>${rupee(totals.cod_fee)}</strong></div>` : ""}
      ${Number(totals.tax_amount) ? `<div><span>Tax</span><strong>${rupee(totals.tax_amount)}</strong></div>` : ""}
      <div class="payable-line"><span>Payable</span><strong>${rupee(totals.grand_total)}</strong></div>
    </div>`;
}

async function refreshCheckout() {
  try {
    const data = await validateCart();
    renderSummary(data);
    await loadCheckoutLink();
  } catch (err) {
    summaryBox.textContent = err.message || "Could not load checkout.";
  }
}

async function loadCheckoutLink() {
  try {
    const res = await fetch(`${API_BASE}/checkout-link`, { credentials: "include" });
    const data = await res.json();
    if (res.status === 401) return redirectToLogin();
    if (data.success) {
      whatsappUrl = data.whatsapp_url;
      instagramUrl = data.instagram_url;
    }
  } catch (err) {
    whatsappUrl = null;
    instagramUrl = null;
  }
}

function idempotencyKey() {
  return `cod-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function placeCodOrder() {
  const res = await fetch(`${API_BASE}/orders/cod`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      address_id: selectedAddressId,
      agree: agreeOrder.checked,
      idempotency_key: idempotencyKey()
    })
  });
  const data = await res.json();
  if (res.status === 401) return redirectToLogin();
  if (!data.success) throw new Error(data.message || "Could not place order");
  if (window.HealthymaCart) HealthymaCart.clearCart();
  window.location.href = `order-success.html?order=${encodeURIComponent(data.order_number)}`;
}

async function createOnlineOrder() {
  if (!latestValidation?.payment_options?.online_payment_enabled) {
    throw new Error("Online payment is not configured yet. Please use Cash on Delivery.");
  }
  throw new Error("Razorpay checkout script can be enabled after backend test keys are added.");
}

async function placeOrder() {
  if (placingOrder) return;
  if (!selectedAddressId) return setMessage("Please select or add a delivery address.", true);
  if (!agreeOrder.checked) return setMessage("Please confirm the order before placing it.", true);

  placingOrder = true;
  placeOrderBtn.disabled = true;
  placeOrderBtn.textContent = "Placing order...";
  setMessage("");
  try {
    if (selectedMethod === "COD") await placeCodOrder();
    else await createOnlineOrder();
  } catch (err) {
    setMessage(err.message || "Could not place order.", true);
  } finally {
    placingOrder = false;
    placeOrderBtn.disabled = false;
    placeOrderBtn.textContent = "Place Order";
  }
}

document.querySelectorAll(".payment-card").forEach(card => {
  card.addEventListener("click", async () => {
    selectedMethod = card.dataset.method;
    document.querySelectorAll(".payment-card").forEach(item => item.classList.toggle("selected", item === card));
    await refreshCheckout();
  });
});

document.getElementById("whatsappBtn").addEventListener("click", () =>
  whatsappUrl ? window.open(whatsappUrl, "_blank") : alert("Order summary not ready yet.")
);
document.getElementById("instagramBtn").addEventListener("click", () =>
  instagramUrl ? window.open(instagramUrl, "_blank") : alert("Order summary not ready yet.")
);
placeOrderBtn.addEventListener("click", placeOrder);

(async function initCheckout() {
  try {
    await loadAddresses();
    await refreshCheckout();
  } catch (err) {
    setMessage(err.message || "Could not load checkout.", true);
  }
})();
