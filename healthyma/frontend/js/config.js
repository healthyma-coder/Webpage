// Match the browser host so Flask session cookies work for admin/customer login.
const API_HOST = window.location.hostname || "127.0.0.1";
const API_BASE = `http://${API_HOST}:5000/api`;
window.SHOW_DEMO_OTP = true;
