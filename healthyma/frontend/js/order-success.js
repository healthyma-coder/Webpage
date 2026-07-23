const params = new URLSearchParams(window.location.search);
const orderNumber = params.get("order");
const successMessage = document.getElementById("successMessage");
const successDetails = document.getElementById("successDetails");

function rupee(value) {
  return `Rs.${Number(value || 0).toFixed(2)}`;
}

async function loadOrder() {
  if (!orderNumber) {
    successMessage.textContent = "Order number missing.";
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/orders/${encodeURIComponent(orderNumber)}`, { credentials: "include" });
    const data = await res.json();
    if (res.status === 401) {
      window.location.href = "login.html";
      return;
    }
    if (!data.success) {
      successMessage.textContent = data.message || "Order not found.";
      return;
    }
    const order = data.order;
    successMessage.textContent = `Order ${order.order_number} is confirmed.`;
    successDetails.innerHTML = `
      <div class="summary-lines">
        <div><span>Payment</span><strong>${order.payment_method}</strong></div>
        <div><span>Status</span><strong>${order.order_status}</strong></div>
        <div><span>Payable</span><strong>${rupee(order.grand_total)}</strong></div>
      </div>
      <div class="placed-items">
        ${data.items.map(item => `<p>${item.product_name} x ${item.quantity} - ${rupee(item.line_total)}</p>`).join("")}
      </div>`;
  } catch (err) {
    successMessage.textContent = "Could not load order details.";
  }
}

loadOrder();
