const productGrid = document.getElementById("productGrid");
const categoryBar = document.getElementById("categoryBar");
const searchInput = document.getElementById("searchInput");
const logoutLink = document.getElementById("logoutLink");
const productCount = document.getElementById("productCount");

let allProducts = [];
const params = new URLSearchParams(window.location.search);
let currentCategory = params.get("category") || "all";

const fallbackProducts = [
  { id: 1, name: "Moringa Mix Powder", category: "Health Mix", price: 180, original_price: 220, weight: "250", unit: "g", stock: 100, image_url: "images/moringa-mix-powder.jpeg", description: "Premium moringa leaf podi made for everyday nutrition.", is_premium: true, is_active: true },
  { id: 2, name: "Curry Leaf Mix", category: "Health Mix", price: 160, original_price: 199, weight: "250", unit: "g", stock: 100, image_url: "images/curry-leaf-mix.jpeg", description: "Traditional karuveppilai podi with natural curry leaves and spices.", is_premium: true, is_active: true },
  { id: 3, name: "Millet Atta", category: "Millet Flour", price: 220, original_price: 260, weight: "1", unit: "kg", stock: 150, image_url: "images/millet-atta.jpeg", description: "Multigrain millet flour with ragi, kambu, thinai, samai and kuthiravali.", is_premium: true, is_active: true },
  { id: 4, name: "Kambu Ragi Mix", category: "Millet Flour", price: 210, original_price: 250, weight: "1", unit: "kg", stock: 150, image_url: "images/kambu-ragi-mix.jpeg", description: "Nutritious kambu, ragi and millet flour mix for daily cooking.", is_premium: true, is_active: true },
  { id: 5, name: "Corn Flour", category: "Flour", price: 120, original_price: 150, weight: "500", unit: "g", stock: 120, image_url: "images/corn-flour.jpeg", description: "Pure corn flour for cooking, baking and everyday kitchen use.", is_premium: true, is_active: true }
];

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

function redirectToLogin() {
  window.location.href = "login.html";
}

function isActive(product) {
  return product.is_active === undefined || product.is_active === true || product.is_active === 1;
}

async function loadProductsFromApi() {
  try {
    const res = await fetch(`${API_BASE}/products`);
    const data = await res.json();
    if (data.success && data.products?.length) return data.products.filter(isActive);
  } catch (err) {
    HealthymaCart.showToast("Unable to load products. Showing demo items.", "warning");
  }
  return fallbackProducts;
}

function productImages(product) {
  return [{ src: HealthymaCart.safeImage(product), label: "Product" }];
}

function renderQuantityControl(product) {
  const qty = HealthymaCart.getProductQuantity(product.id);
  const stock = Number(product.stock || 0);
  if (stock <= 0) {
    return `<button class="product-add-btn disabled" type="button" disabled>Out of Stock</button>`;
  }
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

function renderProductCard(product) {
  const images = productImages(product);
  const discount = HealthymaCart.discount(product);
  const original = Number(product.original_price || 0);
  const price = Number(product.price || 0);
  const stock = Number(product.stock || 0);
  const packageSize = HealthymaCart.packageSize(product);
  const sliderControls = images.length > 1
    ? `<button type="button" class="slider-btn prev" data-dir="-1" aria-label="Previous image">&lsaquo;</button><button type="button" class="slider-btn next" data-dir="1" aria-label="Next image">&rsaquo;</button><div class="slider-dots">${images.map((image, index) => `<button type="button" class="slider-dot ${index === 0 ? "active" : ""}" data-index="${index}" aria-label="Show ${image.label} image"></button>`).join("")}</div>`
    : "";

  return `
    <article class="product-card premium-product-card" data-product-id="${product.id}">
      <div class="premium-badge-row">
        <span class="premium-quality-badge">Premium Quality</span>
        ${discount > 0 && original > price ? `<span class="discount-badge">${discount}% OFF</span>` : ""}
      </div>
      <div class="product-slider" data-index="0" data-images='${JSON.stringify(images)}'>
        <img src="${images[0].src}" alt="${product.name}" onerror="this.onerror=null;this.src='images/default-product.jpg'">
        ${sliderControls}
      </div>
      <div class="info">
        <div class="cat-tag">${product.category || "Healthyma"}</div>
        <h3>${product.name}</h3>
        <p class="desc">${product.description || "Pure Healthyma product for daily use."}</p>
        <a class="details-link" href="product-details.html?id=${product.id}">View details</a>
        <span class="package-size">${packageSize}</span>
        <div class="product-buy-row">
          <div class="price-stack">
            <strong>${HealthymaCart.formatCurrency(price)}</strong>
            ${original > price ? `<del>${HealthymaCart.formatCurrency(original)}</del>` : ""}
            <small class="${stock > 0 ? "stock-ok" : "stock-out"}">${stock > 0 ? `${stock} in stock` : "Out of Stock"}</small>
            <small class="stock-limit-msg" aria-live="polite">${HealthymaCart.getProductQuantity(product.id) >= stock && stock > 0 ? "Maximum stock reached" : ""}</small>
          </div>
          <div class="card-cart-control">${renderQuantityControl(product)}</div>
        </div>
      </div>
    </article>`;
}

HealthymaCart.renderProductCard = renderProductCard;

function renderCategories(products) {
  const cats = ["all", ...new Set(products.map(p => p.category).filter(Boolean))];
  categoryBar.innerHTML = "";
  cats.forEach(cat => {
    const active = cat.toLowerCase() === currentCategory.toLowerCase();
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `category-chip ${active ? "active" : ""}`;
    chip.dataset.category = cat;
    chip.textContent = cat === "all" ? "All" : cat;
    categoryBar.appendChild(chip);
  });
}

function filteredProducts() {
  const q = (searchInput ? searchInput.value : params.get("q") || "").trim().toLowerCase();
  return allProducts.filter(product => {
    const categoryMatches = currentCategory.toLowerCase() === "all" || String(product.category || "").toLowerCase() === currentCategory.toLowerCase();
    const text = `${product.name} ${product.description || ""} ${product.category || ""}`.toLowerCase();
    return categoryMatches && (!q || text.includes(q));
  });
}

function renderProducts() {
  const filtered = filteredProducts();
  if (productCount) productCount.textContent = `${filtered.length} product${filtered.length === 1 ? "" : "s"}`;
  if (!filtered.length) {
    productGrid.innerHTML = `<div class="empty-state"><p>No products found.</p></div>`;
    HealthymaCart.updateAllCartUI(productGrid);
    return;
  }
  productGrid.innerHTML = filtered.map(renderProductCard).join("");
  HealthymaCart.updateAllCartUI(productGrid);
}

function showSlide(slider, nextIndex) {
  const images = JSON.parse(slider.dataset.images || "[]");
  if (!images.length) return;
  const index = (nextIndex + images.length) % images.length;
  slider.dataset.index = String(index);
  const img = slider.querySelector("img");
  img.src = images[index].src;
  slider.querySelectorAll(".slider-dot").forEach((dot, dotIndex) => {
    dot.classList.toggle("active", dotIndex === index);
  });
}

function productById(productId) {
  return allProducts.find(product => Number(product.id) === Number(productId));
}

async function handleProductAction(target) {
  const action = target.dataset.action;
  if (!action) return;
  const card = target.closest("[data-product-id]");
  const product = productById(card?.dataset.productId);
  if (!product) return;

  try {
    target.disabled = true;
    if (action === "add") {
      await HealthymaCart.addToCart(product);
      HealthymaCart.showToast(`${product.name} added to cart`, "success");
    }
    if (action === "increase") {
      await HealthymaCart.increaseQuantity(product);
      HealthymaCart.showToast("Quantity updated", "success");
    }
    if (action === "decrease") {
      const before = HealthymaCart.getProductQuantity(product.id);
      await HealthymaCart.decreaseQuantity(product);
      HealthymaCart.showToast(before <= 1 ? "Product removed from cart" : "Quantity updated", "success");
    }
  } catch (err) {
    HealthymaCart.showToast(err.message || "Unable to update cart", "error");
    if ((err.message || "").toLowerCase().includes("login")) redirectToLogin();
  } finally {
    renderProducts();
  }
}

productGrid.addEventListener("click", event => {
  const sliderButton = event.target.closest(".slider-btn");
  const sliderDot = event.target.closest(".slider-dot");
  const actionButton = event.target.closest("[data-action]");
  if (sliderButton) {
    const slider = sliderButton.closest(".product-slider");
    showSlide(slider, Number(slider.dataset.index || 0) + Number(sliderButton.dataset.dir));
    return;
  }
  if (sliderDot) {
    showSlide(sliderDot.closest(".product-slider"), Number(sliderDot.dataset.index));
    return;
  }
  if (actionButton) handleProductAction(actionButton);
});

categoryBar.addEventListener("click", event => {
  const chip = event.target.closest(".category-chip");
  if (!chip) return;
  currentCategory = chip.dataset.category || "all";
  history.replaceState(null, "", currentCategory.toLowerCase() === "all" ? "products.html" : `products.html?category=${encodeURIComponent(currentCategory)}`);
  renderCategories(allProducts);
  renderProducts();
});

document.getElementById("goToCartBtn").addEventListener("click", () => window.location.href = "cart.html");
if (searchInput) {
  searchInput.addEventListener("input", renderProducts);
  searchInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      renderProducts();
    }
  });
}
document.querySelector(".market-search button")?.addEventListener("click", renderProducts);
document.querySelectorAll(".category-shortcut").forEach(btn => {
  btn.addEventListener("click", () => {
    currentCategory = btn.dataset.category || "all";
    history.replaceState(null, "", `products.html?category=${encodeURIComponent(currentCategory)}`);
    renderCategories(allProducts);
    renderProducts();
    productGrid.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
if (logoutLink) {
  logoutLink.addEventListener("click", async event => {
    event.preventDefault();
    await fetch(`${API_BASE}/logout`, { method: "POST", credentials: "include" });
    sessionStorage.clear();
    HealthymaCart.clearCart();
    window.location.href = "login.html";
  });
}
window.addEventListener("healthyma-cart-updated", () => HealthymaCart.updateProductControls?.(productGrid));

(async function init() {
  const signedIn = await requireAuth();
  if (!signedIn) return;
  if (searchInput && params.get("q")) searchInput.value = params.get("q");
  await HealthymaCart.hydrateCartFromBackend();
  allProducts = await loadProductsFromApi();
  renderCategories(allProducts);
  renderProducts();
})();
