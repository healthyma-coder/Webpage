(function updateHeaderLocation() {
  const locationLink = document.querySelector(".market-location");
  if (!locationLink) return;

  const addresses = JSON.parse(localStorage.getItem("healthyma_delivery_addresses") || "[]");
  const activeId = localStorage.getItem("healthyma_active_address_id");
  const active = addresses.find(address => address.id === activeId)
    || JSON.parse(localStorage.getItem("healthyma_delivery_address") || "null");
  if (!active) return;

  const title = locationLink.querySelector("strong");
  const detail = locationLink.querySelector("span");
  if (title) title.textContent = active.label || active.area || active.city || "Delivery location";
  if (detail) detail.textContent = [active.addressLine, active.city, active.pincode].filter(Boolean).join(", ");
})();
