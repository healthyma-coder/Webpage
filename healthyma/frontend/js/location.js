const detectLocationBtn = document.getElementById("detectLocationBtn");
const openMapBtn = document.getElementById("openMapBtn");
const newAddressBtn = document.getElementById("newAddressBtn");
const addressForm = document.getElementById("addressForm");
const locationMessage = document.getElementById("locationMessage");
const mapBox = document.getElementById("mapBox");
const savedAddresses = document.getElementById("savedAddresses");

const ADDRESS_BOOK_KEY = "healthyma_delivery_addresses";
const ACTIVE_ADDRESS_KEY = "healthyma_active_address_id";
const LEGACY_ADDRESS_KEY = "healthyma_delivery_address";

let addressBook = [];

const fields = {
  id: document.getElementById("addressId"),
  label: document.getElementById("addressLabel"),
  fullName: document.getElementById("fullName"),
  phone: document.getElementById("addressPhone"),
  addressLine: document.getElementById("addressLine"),
  area: document.getElementById("landmark"),
  city: document.getElementById("city"),
  pincode: document.getElementById("pincode"),
  deliveryNote: document.getElementById("deliveryNote"),
  latitude: document.getElementById("latitude"),
  longitude: document.getElementById("longitude")
};

function localAddressId() {
  return `addr_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function getLocalAddressBook() {
  try {
    const addresses = JSON.parse(localStorage.getItem(ADDRESS_BOOK_KEY) || "[]");
    return Array.isArray(addresses) ? addresses : [];
  } catch {
    return [];
  }
}

function getLocalActiveAddressId() {
  return localStorage.getItem(ACTIVE_ADDRESS_KEY);
}

function cacheAddresses(addresses) {
  const localAddresses = (addresses || []).map(addressFromApi);
  addressBook = localAddresses;
  localStorage.setItem(ADDRESS_BOOK_KEY, JSON.stringify(localAddresses));
  const active = localAddresses.find(address => address.isDefault) || localAddresses[0] || null;
  if (active) {
    localStorage.setItem(ACTIVE_ADDRESS_KEY, String(active.id));
    localStorage.setItem(LEGACY_ADDRESS_KEY, JSON.stringify(active));
  } else {
    localStorage.removeItem(ACTIVE_ADDRESS_KEY);
    localStorage.removeItem(LEGACY_ADDRESS_KEY);
  }
}

function activeAddress() {
  const activeId = getLocalActiveAddressId();
  return addressBook.find(address => String(address.id) === String(activeId))
    || addressBook.find(address => address.isDefault)
    || addressBook[0]
    || null;
}

function addressFromApi(address) {
  const lineParts = [address.house, address.street].filter(Boolean);
  const addressLine = [...new Set(lineParts)].join(", ");
  return {
    id: address.id,
    label: address.label || address.area || "Home",
    fullName: address.full_name || "",
    phone: address.mobile || "",
    addressLine,
    area: address.area || address.landmark || "",
    city: address.city || "",
    pincode: address.pincode || "",
    deliveryNote: address.delivery_instructions || "",
    latitude: address.latitude || "",
    longitude: address.longitude || "",
    isDefault: Boolean(address.is_default)
  };
}

function apiPayloadFromForm() {
  return {
    label: fields.label.value.trim() || "Home",
    full_name: fields.fullName.value.trim(),
    mobile: fields.phone.value.trim(),
    address_line: fields.addressLine.value.trim(),
    house: fields.addressLine.value.trim(),
    street: fields.addressLine.value.trim(),
    area: fields.area.value.trim(),
    landmark: fields.area.value.trim(),
    city: fields.city.value.trim(),
    state: "Tamil Nadu",
    pincode: fields.pincode.value.trim(),
    delivery_instructions: fields.deliveryNote.value.trim(),
    latitude: fields.latitude.value.trim(),
    longitude: fields.longitude.value.trim(),
    is_default: true
  };
}

function localApiPayload(saved) {
  if (!saved) return null;
  return {
    label: saved.label || saved.area || "Home",
    full_name: saved.fullName || saved.full_name || "Healthyma Customer",
    mobile: saved.phone || saved.mobile || "",
    address_line: saved.addressLine || saved.address_line || saved.house || saved.street || "",
    house: saved.addressLine || saved.house || saved.street || "",
    street: saved.addressLine || saved.street || saved.house || "",
    area: saved.area || saved.landmark || "",
    landmark: saved.area || saved.landmark || "",
    city: saved.city || "",
    state: saved.state || "Tamil Nadu",
    pincode: saved.pincode || "",
    delivery_instructions: saved.deliveryNote || saved.delivery_instructions || "",
    latitude: saved.latitude || "",
    longitude: saved.longitude || "",
    is_default: true
  };
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const data = await res.json();
  if (res.status === 401) {
    window.location.href = "login.html";
    return data;
  }
  if (!data.success) {
    const errors = data.errors ? ` ${Object.values(data.errors).join(" ")}` : "";
    throw new Error(`${data.message || "Request failed"}${errors}`);
  }
  return data;
}

async function requireAuth() {
  const data = await api("/me");
  if (!data.logged_in) {
    window.location.href = "login.html";
    return false;
  }
  if (!fields.phone.value && data.phone) fields.phone.value = data.phone;
  return true;
}

function setMessage(message, isError = false) {
  locationMessage.textContent = message;
  locationMessage.classList.toggle("error", isError);
}

function setBusy(isBusy) {
  addressForm.querySelector("button[type='submit']").disabled = isBusy;
  detectLocationBtn.disabled = isBusy;
}

function setMapLocation(latitude, longitude) {
  fields.latitude.value = latitude;
  fields.longitude.value = longitude;
  const mapUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
  openMapBtn.href = mapUrl;
  mapBox.innerHTML = `<strong>Map location selected</strong><span>Latitude: ${latitude}<br>Longitude: ${longitude}</span><a href="${mapUrl}" target="_blank" rel="noopener">View on Google Maps</a>`;
}

function resetMapBox() {
  openMapBtn.href = "https://www.google.com/maps";
  mapBox.innerHTML = `<strong>Map location not selected</strong><span>Click "Use Current Location" to get latitude and longitude.</span>`;
}

function clearForm() {
  addressForm.reset();
  Object.values(fields).forEach(field => { field.value = ""; });
  resetMapBox();
  setMessage("");
  fields.label.focus();
}

function fillForm(address) {
  fields.id.value = address.id || "";
  fields.label.value = address.label || "";
  fields.fullName.value = address.fullName || "";
  fields.phone.value = address.phone || "";
  fields.addressLine.value = address.addressLine || "";
  fields.area.value = address.area || "";
  fields.city.value = address.city || "";
  fields.pincode.value = address.pincode || "";
  fields.deliveryNote.value = address.deliveryNote || "";
  fields.latitude.value = address.latitude || "";
  fields.longitude.value = address.longitude || "";
  if (address.latitude && address.longitude) setMapLocation(address.latitude, address.longitude);
  else resetMapBox();
}

function addressSummary(address) {
  return [address.addressLine, address.area, address.city, address.pincode].filter(Boolean).join(", ");
}

function renderSavedAddresses() {
  const activeId = getLocalActiveAddressId();
  if (!addressBook.length) {
    savedAddresses.innerHTML = `<div class="empty-address-book">No saved addresses yet.</div>`;
    return;
  }

  savedAddresses.innerHTML = addressBook.map(address => `
    <div class="saved-address ${String(address.id) === String(activeId) || address.isDefault ? "active" : ""}">
      <div>
        <strong>${address.label || "Address"}</strong>
        <span>${addressSummary(address) || "Address details not complete"}</span>
        ${String(address.id) === String(activeId) || address.isDefault ? `<em>Selected for delivery</em>` : ""}
      </div>
      <div class="saved-address-actions">
        <button type="button" data-action="use" data-id="${address.id}">Use</button>
        <button type="button" data-action="edit" data-id="${address.id}">Edit</button>
        <button type="button" data-action="delete" data-id="${address.id}">Delete</button>
      </div>
    </div>
  `).join("");
}

async function migrateLocalAddressesIfNeeded(apiAddresses) {
  if (apiAddresses.length) return apiAddresses;
  const candidates = [...getLocalAddressBook()];
  try {
    const legacy = JSON.parse(localStorage.getItem(LEGACY_ADDRESS_KEY) || "null");
    if (legacy) candidates.push(legacy);
  } catch {
    // Ignore old malformed local data.
  }
  const unique = candidates.filter((address, index, list) =>
    address && (address.phone || address.mobile) && address.pincode
      && list.findIndex(item => JSON.stringify(item) === JSON.stringify(address)) === index
  );
  for (const saved of unique) {
    await api("/addresses", {
      method: "POST",
      body: JSON.stringify(localApiPayload(saved))
    });
  }
  if (!unique.length) return apiAddresses;
  const refreshed = await api("/addresses");
  return refreshed.addresses || [];
}

async function loadAddresses() {
  const data = await api("/addresses");
  const addresses = await migrateLocalAddressesIfNeeded(data.addresses || []);
  cacheAddresses(addresses);
  renderSavedAddresses();
  const selected = activeAddress();
  if (selected) fillForm(selected);
  else clearForm();
}

async function checkPincode() {
  const pincode = fields.pincode.value.trim();
  if (pincode.length !== 6) return true;
  const res = await fetch(`${API_BASE}/delivery/check?pincode=${encodeURIComponent(pincode)}`, { credentials: "include" });
  const data = await res.json();
  if (!data.serviceable) throw new Error(data.message || "Delivery is not available for this pincode");
  return true;
}

function validateForm() {
  if (!fields.fullName.value.trim()) throw new Error("Full name is required.");
  if (!/^\d{10}$/.test(fields.phone.value.trim())) throw new Error("Please enter a valid 10-digit phone number.");
  if (!fields.addressLine.value.trim()) throw new Error("House / Flat / Street is required.");
  if (!fields.area.value.trim()) throw new Error("Area / Landmark is required.");
  if (!fields.city.value.trim()) throw new Error("City is required.");
  if (!/^\d{6}$/.test(fields.pincode.value.trim())) throw new Error("Please enter a valid 6-digit pincode.");
}

newAddressBtn.addEventListener("click", () => {
  clearForm();
  fields.id.value = "";
  setMessage("Fill the form and save this as a new delivery address.");
  addressForm.scrollIntoView({ behavior: "smooth", block: "start" });
});

detectLocationBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setMessage("Location is not supported in this browser. Please open the map and fill address manually.", true);
    return;
  }

  detectLocationBtn.disabled = true;
  detectLocationBtn.textContent = "Finding location...";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const latitude = position.coords.latitude.toFixed(6);
      const longitude = position.coords.longitude.toFixed(6);
      setMapLocation(latitude, longitude);
      setMessage("Location captured. Please fill or confirm your delivery address.");
      detectLocationBtn.disabled = false;
      detectLocationBtn.textContent = "Use Current Location";
    },
    () => {
      setMessage("Could not get location permission. Please open map and fill address manually.", true);
      detectLocationBtn.disabled = false;
      detectLocationBtn.textContent = "Use Current Location";
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

savedAddresses.addEventListener("click", async event => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = button.dataset.id;
  const action = button.dataset.action;
  const address = addressBook.find(item => String(item.id) === String(id));
  if (!address) return;

  try {
    if (action === "use") {
      await api(`/addresses/${id}/default`, { method: "POST" });
      localStorage.setItem(ACTIVE_ADDRESS_KEY, String(id));
      localStorage.setItem(LEGACY_ADDRESS_KEY, JSON.stringify(address));
      await loadAddresses();
      setMessage(`${address.label || "Address"} selected for delivery.`);
    }

    if (action === "edit") {
      fillForm(address);
      setMessage(`Editing ${address.label || "saved address"}. Save to update it.`);
    }

    if (action === "delete") {
      if (!confirm("Delete this saved address?")) return;
      await api(`/addresses/${id}`, { method: "DELETE" });
      await loadAddresses();
      setMessage("Address deleted.");
    }
  } catch (err) {
    setMessage(err.message || "Could not update address.", true);
  }
});

addressForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    setBusy(true);
    validateForm();
    await checkPincode();
    const id = fields.id.value;
    const payload = apiPayloadFromForm();
    const data = await api(id ? `/addresses/${id}` : "/addresses", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload)
    });
    if (!id && data.address_id) fields.id.value = data.address_id;
    await loadAddresses();
    setMessage(`${payload.label} saved to your account. Redirecting to shop...`);
    setTimeout(() => {
      window.location.href = "products.html";
    }, 700);
  } catch (err) {
    setMessage(err.message || "Could not save address.", true);
  } finally {
    setBusy(false);
  }
});

(async function initLocation() {
  try {
    renderSavedAddresses();
    const signedIn = await requireAuth();
    if (!signedIn) return;
    await loadAddresses();
  } catch (err) {
    setMessage(err.message || "Could not load saved addresses.", true);
    addressBook = getLocalAddressBook();
    renderSavedAddresses();
  }
})();
