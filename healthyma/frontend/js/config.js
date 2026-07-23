const IS_LOCAL = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";

const API_BASE = IS_LOCAL 
  ? "http://127.0.0.1:5000/api" 
  : "https://healthyma-webpage.onrender.com/api";

window.SHOW_DEMO_OTP = IS_LOCAL;