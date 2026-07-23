const ordersList = document.getElementById("ordersList");

function rupee(value) {
  return `Rs.${Number(value || 0).toFixed(2)}`;
}

async function loadOrders() {
  try {
    const res = await fetch(`${API_BASE}/orders`, { credentials: "include" });
    const data = await res.json();
    if (res.status === 401) {
      window.location.href = "login.html";
      return;
    }
    if (!data.success || !data.orders.length) {
      ordersList.innerHTML = `<div class="empty-state"><p>No orders yet.</p><br><a class="primary-pill" href="products.html">Start Shopping</a></div>`;
      return;
    }
    ordersList.innerHTML = data.orders.map(order => `
      <a class="order-card" href="order-success.html?order=${encodeURIComponent(order.order_number)}">
        <div>
          <strong>${order.order_number}</strong>
          <span>${order.payment_method} | ${order.payment_status} | ${order.order_status}</span>
        </div>
        <b>${rupee(order.grand_total)}</b>
      </a>`).join("");
  } catch (err) {
    ordersList.innerHTML = `<div class="empty-state"><p>Could not load orders.</p></div>`;
  }
}

loadOrders();
