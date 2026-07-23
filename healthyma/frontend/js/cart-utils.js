(function () {
  const CART_KEY = "healthyma_cart";

  function getCart() {
    try {
      const cart = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
      return Array.isArray(cart) ? cart : [];
    } catch (err) {
      return [];
    }
  }

  function saveCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    window.dispatchEvent(new CustomEvent("healthyma-cart-updated", { detail: cart }));
  }

  function formatCurrency(amount) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(Number(amount || 0));
  }

  function safeImage(product) {
    const name = (product.name || "").toLowerCase();
    const category = product.category || "";
    if (name.includes("moringa")) return "images/moringa-mix-powder.jpeg";
    if (name.includes("curry")) return "images/curry-leaf-mix.jpeg";
    if (name.includes("millet atta")) return "images/millet-atta.jpeg";
    if (name.includes("kambu") || name.includes("ragi")) return "images/kambu-ragi-mix.jpeg";
    if (name.includes("corn")) return "images/corn-flour.jpeg";
    if (category === "Health Mix") return "images/moringa-mix-powder.jpeg";
    if (category === "Millet Flour") return "images/millet-atta.jpeg";
    if (category === "Flour") return "images/corn-flour.jpeg";
    const url = product.image_url || "";
    if (url.startsWith("/images/")) return `.${url}`;
    if (url.startsWith("http")) return url;
    return url || "images/default-product.jpg";
  }

  function packageSize(product) {
    if (product.weight && product.unit) return `${product.weight} ${product.unit}`;
    const match = (product.name || "").match(/\(([^)]+)\)/);
    return match ? match[1] : "Pack";
  }

  function discount(product) {
    const price = Number(product.price || 0);
    const original = Number(product.original_price || 0);
    if (original > price) return Math.round(((original - price) / original) * 100);
    return Math.round(Number(product.discount_percentage || 0));
  }

  function normalizeProduct(product, quantity = 1) {
    return {
      product_id: Number(product.product_id || product.id),
      name: product.name,
      price: Number(product.price || product.unit_price || 0),
      original_price: Number(product.original_price || product.price || 0),
      discount_percentage: discount(product),
      image_url: product.image_url || safeImage(product),
      weight: product.weight || "",
      unit: product.unit || "",
      package_size: product.package_size || packageSize(product),
      category: product.category || "",
      stock: Number(product.stock || 0),
      quantity,
      description: product.description || "",
      is_premium: product.is_premium !== false
    };
  }

  function getProductQuantity(productId) {
    const item = getCart().find(entry => Number(entry.product_id) === Number(productId));
    return item ? Number(item.quantity || 0) : 0;
  }

  function getCartItemCount() {
    return getCart().reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  }

  function getCartSubtotal() {
    return getCart().reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0);
  }

  function setQuantity(product, quantity) {
    const normalized = normalizeProduct(product, quantity);
    const cart = getCart();
    const index = cart.findIndex(item => Number(item.product_id) === normalized.product_id);
    if (quantity <= 0) {
      if (index >= 0) cart.splice(index, 1);
    } else if (index >= 0) {
      cart[index] = { ...cart[index], ...normalized, quantity };
    } else {
      cart.push(normalized);
    }
    saveCart(cart);
  }

  async function syncBackend(productId, quantity) {
    if (!window.API_BASE) return { success: true };
    const res = await fetch(`${API_BASE}/cart/product/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ product_id: productId, quantity })
    });
    const data = await res.json();
    if (res.status === 401) {
      window.location.href = "login.html";
      return data;
    }
    if (!data.success) throw new Error(data.message || "Unable to update cart");
    return data;
  }

  async function setProductQuantity(product, quantity, sync = true) {
    const productId = Number(product.product_id || product.id);
    const stock = Number(product.stock || 0);
    if (stock <= 0) throw new Error("Product is out of stock");
    if (quantity > stock) throw new Error(`Only ${stock} items are available`);
    if (sync) await syncBackend(productId, quantity);
    setQuantity(product, quantity);
  }

  async function addToCart(product) {
    const next = getProductQuantity(product.id || product.product_id) + 1;
    await setProductQuantity(product, next);
  }

  async function increaseQuantity(product) {
    const next = getProductQuantity(product.id || product.product_id) + 1;
    await setProductQuantity(product, next);
  }

  async function decreaseQuantity(product) {
    const next = Math.max(0, getProductQuantity(product.id || product.product_id) - 1);
    await setProductQuantity(product, next);
  }

  function removeFromCart(productId) {
    const cart = getCart().filter(item => Number(item.product_id) !== Number(productId));
    saveCart(cart);
  }

  function clearCart() {
    saveCart([]);
  }

  function updateHeaderCartCount() {
    const total = getCartItemCount();
    document.querySelectorAll(".market-cart").forEach(link => {
      link.classList.add("cart-with-badge");
      let badge = link.querySelector(".cart-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "cart-badge";
        link.appendChild(badge);
      }
      badge.textContent = total;
      badge.hidden = total === 0;
    });
  }

  function updateBottomCartBar() {
    const bar = document.getElementById("floatingBar");
    const count = document.getElementById("cartCount");
    const subtotal = document.getElementById("cartSubtotal");
    if (!bar || !count) return;
    const total = getCartItemCount();
    count.textContent = `${total} item${total === 1 ? "" : "s"}`;
    if (subtotal) subtotal.textContent = formatCurrency(getCartSubtotal());
    bar.classList.toggle("show", total > 0);
  }

  function updateProductControls(root = document) {
    root.querySelectorAll("[data-product-id]").forEach(node => {
      const productId = node.dataset.productId;
      const qty = getProductQuantity(productId);
      const card = node.closest(".product-card");
      if (card) card.classList.toggle("in-cart", qty > 0);
      node.querySelectorAll("[data-qty-value]").forEach(value => { value.textContent = qty; });
      node.querySelectorAll("[data-action='increase']").forEach(button => {
        const stock = Number(button.dataset.stock || 0);
        button.disabled = stock > 0 && qty >= stock;
      });
    });
  }

  function updateAllCartUI(root = document) {
    updateHeaderCartCount();
    updateBottomCartBar();
    updateProductControls(root);
  }

  function showToast(message, type = "success") {
    let host = document.querySelector(".toast-host");
    if (!host) {
      host = document.createElement("div");
      host.className = "toast-host";
      document.body.appendChild(host);
    }
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    host.appendChild(toast);
    window.setTimeout(() => toast.classList.add("hide"), 2300);
    window.setTimeout(() => toast.remove(), 2800);
  }

  async function hydrateCartFromBackend() {
    if (!window.API_BASE) return;
    try {
      const res = await fetch(`${API_BASE}/cart`, { credentials: "include" });
      if (res.status === 401) return;
      const data = await res.json();
      if (data.success) {
        saveCart((data.items || []).map(item => normalizeProduct(item, Number(item.quantity || 0))));
      }
    } catch (err) {
      updateAllCartUI();
    }
  }

  window.addEventListener("storage", event => {
    if (event.key === CART_KEY) updateAllCartUI();
  });
  window.addEventListener("healthyma-cart-updated", () => updateAllCartUI());
  document.addEventListener("DOMContentLoaded", updateAllCartUI);

  window.HealthymaCart = {
    CART_KEY,
    getCart,
    saveCart,
    addToCart,
    increaseQuantity,
    decreaseQuantity,
    removeFromCart,
    clearCart,
    setProductQuantity,
    getProductQuantity,
    getCartItemCount,
    getCartSubtotal,
    formatCurrency,
    safeImage,
    packageSize,
    discount,
    normalizeProduct,
    updateAllCartUI,
    updateHeaderCartCount,
    updateBottomCartBar,
    renderProductCard: null,
    showToast,
    hydrateCartFromBackend,
    updateProductControls
  };
})();
