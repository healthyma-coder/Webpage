const phone = sessionStorage.getItem("healthyma_phone");
const showDemoOtp = window.SHOW_DEMO_OTP === true;
if (!showDemoOtp) sessionStorage.removeItem("healthyma_demo_otp");
const demoOtp = showDemoOtp ? sessionStorage.getItem("healthyma_demo_otp") : "";
const demoHint = document.getElementById("demoHint");
if (demoHint) {
  demoHint.style.display = "none";
  demoHint.textContent = "";
}

if (!phone) {
  // No phone in session -> user must login first
  window.location.href = "login.html";
}

document.getElementById("phoneDisplay").textContent = `OTP sent to ${phone}`;

if (demoOtp) {
  demoHint.style.display = "block";
  demoHint.textContent = `Development OTP: ${demoOtp}`;
}

const otpInput = document.getElementById("otpInput");
const verifyBtn = document.getElementById("verifyBtn");
const resendBtn = document.getElementById("resendBtn");
const errorMsg = document.getElementById("errorMsg");

verifyBtn.addEventListener("click", async () => {
  const otp = otpInput.value.trim();
  errorMsg.textContent = "";

  if (!otp) {
    errorMsg.textContent = "Please enter the OTP.";
    return;
  }

  verifyBtn.disabled = true;
  verifyBtn.textContent = "Verifying...";

  try {
    const res = await fetch(`${API_BASE}/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ phone, otp })
    });
    const data = await res.json();

    if (data.success) {
      sessionStorage.removeItem("healthyma_demo_otp");
      window.location.href = "home.html";
    } else {
      errorMsg.textContent = data.message || "Invalid OTP.";
      verifyBtn.disabled = false;
      verifyBtn.textContent = "Verify & Continue";
    }
  } catch (err) {
    errorMsg.textContent = "Could not reach server. Is the Flask backend running?";
    verifyBtn.disabled = false;
    verifyBtn.textContent = "Verify & Continue";
  }
});

resendBtn.addEventListener("click", async () => {
  errorMsg.textContent = "";
  try {
    const res = await fetch(`${API_BASE}/send-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ phone })
    });
    const data = await res.json();
    if (data.success) {
      sessionStorage.removeItem("healthyma_demo_otp");
      if (showDemoOtp && data.demo_otp) {
        sessionStorage.setItem("healthyma_demo_otp", data.demo_otp);
        demoHint.style.display = "block";
        demoHint.textContent = `Development OTP: ${data.demo_otp}`;
      } else {
        demoHint.style.display = "none";
        demoHint.textContent = "";
      }
      errorMsg.style.color = "#2f4f3a";
      errorMsg.textContent = "OTP resent successfully.";
    }
  } catch (err) {
    errorMsg.textContent = "Could not reach server.";
  }
});
