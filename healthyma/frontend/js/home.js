const exploreBtn = document.getElementById("exploreBtn");
const logoutBtn = document.getElementById("logoutBtn");
const logoutLink = document.getElementById("logoutLink");
const popularProducts = document.getElementById("popularProducts");
const goToCartBtn = document.getElementById("goToCartBtn");

let homeProducts = [];

async function requireAuth() {
  try {
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    const data = await res.json();
    if (!data.logged_in) {
      window.location.href = "login.html";
      return false;
    }
    return true;
  } catch (err) {
    window.location.href = "login.html";
    return false;
  }
}

function renderHomeQuantityControl(product) {
  const qty = HealthymaCart.getProductQuantity(product.id);
  const stock = Number(product.stock || 0);
  if (stock <= 0) return `<button class="product-add-btn disabled" type="button" disabled>Out of Stock</button>`;
  if (qty > 0) {
    return `
      <div class="product-qty-control" data-product-id="${product.id}">
        <button type="button" data-action="decrease" aria-label="Decrease ${product.name} quantity">-</button>
        <span data-qty-value>${qty}</span>
        <button type="button" data-action="increase" data-stock="${stock}" aria-label="Increase ${product.name} quantity" ${qty >= stock ? "disabled" : ""}>+</button>
      </div>`;
  }
  return `<button class="product-add-btn" type="button" data-action="add" aria-label="Add ${product.name} to cart">Add</button>`;
}

function renderHomeProductCard(product) {
  const discount = HealthymaCart.discount(product);
  const original = Number(product.original_price || 0);
  const price = Number(product.price || 0);
  const stock = Number(product.stock || 0);
  return `
    <article class="product-card premium-product-card compact-product-card" data-product-id="${product.id}">
      <div class="premium-badge-row">
        <span class="premium-quality-badge">Premium Quality</span>
        ${discount > 0 && original > price ? `<span class="discount-badge">${discount}% OFF</span>` : ""}
      </div>
      <img class="compact-product-image" src="${HealthymaCart.safeImage(product)}" alt="${product.name}" onerror="this.onerror=null;this.src='images/default-product.jpg'">
      <div class="info">
        <h3>${product.name}</h3>
        <p class="desc">${product.description || "Pure Healthyma product for daily use."}</p>
        <span class="package-size">${HealthymaCart.packageSize(product)}</span>
        <div class="product-buy-row">
          <div class="price-stack">
            <strong>${HealthymaCart.formatCurrency(price)}</strong>
            ${original > price ? `<del>${HealthymaCart.formatCurrency(original)}</del>` : ""}
            <small class="${stock > 0 ? "stock-ok" : "stock-out"}">${stock > 0 ? `${stock} in stock` : "Out of Stock"}</small>
          </div>
          <div class="card-cart-control">${renderHomeQuantityControl(product)}</div>
        </div>
      </div>
    </article>`;
}

async function loadPopularProducts() {
  try {
    const res = await fetch(`${API_BASE}/products`);
    const data = await res.json();
    if (!data.success) throw new Error(data.message);
    homeProducts = (data.products || [])
      .filter(product => product.is_active === undefined || product.is_active === true || product.is_active === 1)
      .sort((a, b) => Number(b.is_premium || 0) - Number(a.is_premium || 0) || Number(b.stock || 0) - Number(a.stock || 0) || Number(b.id || 0) - Number(a.id || 0))
      .slice(0, 5);
    popularProducts.innerHTML = homeProducts.map(renderHomeProductCard).join("");
    HealthymaCart.updateAllCartUI(popularProducts);
  } catch (err) {
    popularProducts.innerHTML = `<div class="empty-state"><p>Unable to load products.</p></div>`;
    HealthymaCart.showToast("Unable to load products", "error");
  }
}

function productById(productId) {
  return homeProducts.find(product => Number(product.id) === Number(productId));
}

async function handlePopularAction(button) {
  const product = productById(button.closest("[data-product-id]")?.dataset.productId);
  if (!product) return;
  try {
    button.disabled = true;
    if (button.dataset.action === "add") {
      await HealthymaCart.addToCart(product);
      HealthymaCart.showToast(`${product.name} added to cart`, "success");
    }
    if (button.dataset.action === "increase") {
      await HealthymaCart.increaseQuantity(product);
      HealthymaCart.showToast("Quantity updated", "success");
    }
    if (button.dataset.action === "decrease") {
      const before = HealthymaCart.getProductQuantity(product.id);
      await HealthymaCart.decreaseQuantity(product);
      HealthymaCart.showToast(before <= 1 ? "Product removed from cart" : "Quantity updated", "success");
    }
  } catch (err) {
    HealthymaCart.showToast(err.message || "Unable to update cart", "error");
  } finally {
    popularProducts.innerHTML = homeProducts.map(renderHomeProductCard).join("");
    HealthymaCart.updateAllCartUI(popularProducts);
  }
}

if (popularProducts) {
  popularProducts.addEventListener("click", event => {
    const button = event.target.closest("[data-action]");
    if (button) handlePopularAction(button);
  });
}

if (exploreBtn) exploreBtn.addEventListener("click", () => window.location.href = "products.html");
if (goToCartBtn) goToCartBtn.addEventListener("click", () => window.location.href = "cart.html");

async function logout() {
  await fetch(`${API_BASE}/logout`, { method: "POST", credentials: "include" });
  sessionStorage.clear();
  HealthymaCart.clearCart();
  window.location.href = "login.html";
}

if (logoutBtn) logoutBtn.addEventListener("click", logout);
if (logoutLink) logoutLink.addEventListener("click", event => {
  event.preventDefault();
  logout();
});

(async function initHome() {
  const signedIn = await requireAuth();
  if (!signedIn) return;
  await HealthymaCart.hydrateCartFromBackend();
  await loadPopularProducts();
})();
