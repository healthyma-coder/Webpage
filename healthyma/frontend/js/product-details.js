const root = document.getElementById("productDetailsRoot");
const params = new URLSearchParams(window.location.search);
const productId = Number(params.get("id") || 0);

function rupee(value) {
  return HealthymaCart.formatCurrency(value);
}

function section(title, value) {
  if (!value) return "";
  return `<section class="detail-section"><h2>${title}</h2><p>${value}</p></section>`;
}

function renderProduct(product, variants, similar) {
  const image = HealthymaCart.safeImage(product);
  const price = Number(product.price || 0);
  const original = Number(product.original_price || 0);
  const discount = HealthymaCart.discount(product);
  const stock = Number(product.stock || 0);
  root.innerHTML = `
    <section class="product-detail-grid">
      <div class="product-detail-media">
        ${discount > 0 && original > price ? `<span class="discount-badge">${discount}% OFF</span>` : ""}
        <img src="${image}" alt="${product.name}" onerror="this.onerror=null;this.src='images/default-product.jpg'">
      </div>
      <div class="product-detail-info" data-product-id="${product.id}">
        <p class="eyebrow">${product.category || "Healthyma"}</p>
        <h1>${product.name}</h1>
        <p class="desc">${product.short_description || product.description || "Pure Healthyma product for daily use."}</p>
        <div class="detail-price"><strong>${rupee(price)}</strong>${original > price ? `<del>${rupee(original)}</del>` : ""}</div>
        <p class="${stock > 0 ? "stock-ok" : "stock-out"}">${stock > 0 ? `${stock} in stock` : "Out of Stock"}</p>
        ${variants.length ? `<label class="field-label">Variant<select id="variantSelect">${variants.map(variant => `<option value="${variant.id}">${variant.name} - ${rupee(variant.price)}</option>`).join("")}</select></label>` : ""}
        <label class="field-label">Quantity<input id="detailQty" type="number" min="1" max="${Math.max(1, stock)}" value="1"></label>
        <div class="detail-actions">
          <button class="btn-primary" id="addDetailBtn" ${stock <= 0 ? "disabled" : ""}>Add to Cart</button>
          <button class="secondary-pill" id="buyNowBtn" ${stock <= 0 ? "disabled" : ""}>Buy Now</button>
        </div>
      </div>
    </section>
    ${section("Description", product.description)}
    ${section("Ingredients", product.ingredients)}
    ${section("Benefits", product.benefits)}
    ${section("Usage", product.usage_instructions)}
    ${section("Storage", product.storage_instructions)}
    <section class="detail-section"><h2>Similar products</h2><div class="similar-grid">${similar.map(item => `<a class="similar-card" href="product-details.html?id=${item.id}"><img src="${HealthymaCart.safeImage(item)}" alt="${item.name}"><strong>${item.name}</strong><span>${rupee(item.price)}</span></a>`).join("") || "<p>No similar products yet.</p>"}</div></section>`;

  document.getElementById("addDetailBtn")?.addEventListener("click", async () => {
    const qty = Math.max(1, Number(document.getElementById("detailQty").value || 1));
    try {
      await HealthymaCart.setProductQuantity(product, HealthymaCart.getProductQuantity(product.id) + qty);
      HealthymaCart.showToast("Added to cart", "success");
    } catch (err) {
      HealthymaCart.showToast(err.message || "Unable to add item", "error");
    }
  });
  document.getElementById("buyNowBtn")?.addEventListener("click", async () => {
    document.getElementById("addDetailBtn").click();
    window.setTimeout(() => { window.location.href = "cart.html"; }, 250);
  });
}

(async function initProductDetails() {
  if (!productId) {
    root.innerHTML = `<div class="empty-state"><p>Product not found.</p><br><button class="primary-pill" onclick="window.location.href='products.html'">Continue Shopping</button></div>`;
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/products/${productId}`, { credentials: "include" });
    const data = await res.json();
    if (!data.success) throw new Error(data.message || "Product not found");
    const payload = data.data || {};
    renderProduct(payload.product, payload.variants || [], payload.similar_products || []);
  } catch (err) {
    root.innerHTML = `<div class="empty-state"><p>${err.message || "Could not load product."}</p><br><button class="primary-pill" onclick="window.location.href='products.html'">Continue Shopping</button></div>`;
  }
})();

document.getElementById("goToCartBtn")?.addEventListener("click", () => window.location.href = "cart.html");
