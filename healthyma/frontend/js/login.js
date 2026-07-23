const phoneInput = document.getElementById("phoneInput");
const sendOtpBtn = document.getElementById("sendOtpBtn");
const errorMsg = document.getElementById("errorMsg");

(async function skipLoginWhenSignedIn() {
  try {
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    const data = await res.json();
    if (data.logged_in) window.location.href = "home.html";
  } catch (err) {}
})();

sendOtpBtn.addEventListener("click", async () => {
  const phone = phoneInput.value.trim();
  errorMsg.textContent = "";

  if (phone.length !== 10 || isNaN(phone)) {
    errorMsg.textContent = "Please enter a valid 10-digit phone number.";
    return;
  }

  sendOtpBtn.disabled = true;
  sendOtpBtn.textContent = "Sending...";

  try {
    const res = await fetch(`${API_BASE}/send-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ phone })
    });
    const data = await res.json();

    if (data.success) {
      // Save phone number for the OTP page to use
      sessionStorage.setItem("healthyma_phone", phone);
      sessionStorage.removeItem("healthyma_demo_otp");
      if (data.demo_otp) {
        sessionStorage.setItem("healthyma_demo_otp", data.demo_otp);
      }
      window.location.href = "otp.html";
    } else {
      errorMsg.textContent = data.message || "Something went wrong.";
      sendOtpBtn.disabled = false;
      sendOtpBtn.textContent = "Send OTP";
    }
  } catch (err) {
    errorMsg.textContent = "Could not reach server. Is the Flask backend running?";
    sendOtpBtn.disabled = false;
    sendOtpBtn.textContent = "Send OTP";
  }
});
