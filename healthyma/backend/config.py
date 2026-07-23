# =========================================================
# Healthyma Backend Configuration
# Edit the DB_CONFIG values to match your local MySQL setup
# =========================================================
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
IS_PRODUCTION = FLASK_ENV == "production"

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
DB_CONFIG = {
    "host": os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost")),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", os.getenv("MYSQL_USER", "root")),
    "password": os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", "")),
    "database": os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "healthyma")),
}

# Flask secret key (used for session/cookies). Change this to any random string.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret-key")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        f"{FRONTEND_URL},http://localhost:5500,http://127.0.0.1:5500,null",
    ).split(",")
    if origin.strip()
]

# Admin dashboard login. Keep real production values in backend/.env only.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "healthyma123")

# ---------------------------------------------------------
# WhatsApp / Instagram business contact used at checkout.
# Replace with your real business number / instagram username.
# ---------------------------------------------------------
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "919999999999")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "healthyma_official")

# ---------------------------------------------------------
# OTP settings
# ---------------------------------------------------------
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "4"))
OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
OTP_EXPIRY_MINUTES = max(1, OTP_EXPIRY_SECONDS // 60)
OTP_RESEND_SECONDS = int(os.getenv("OTP_RESEND_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
SHOW_DEMO_OTP = os.getenv("SHOW_DEMO_OTP", "false" if IS_PRODUCTION else "true").lower() == "true"

# ---------------------------------------------------------
# SMS settings
# ---------------------------------------------------------
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console").lower()
SMS_COUNTRY_CODE = os.getenv("SMS_COUNTRY_CODE", "91")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID", "")
TWILIO_API_KEY_SECRET = os.getenv("TWILIO_API_KEY_SECRET", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "")

# ---------------------------------------------------------
# Checkout settings
# ---------------------------------------------------------
MINIMUM_ORDER_VALUE = os.getenv("MINIMUM_ORDER_VALUE", "199")
DELIVERY_FEE = os.getenv("DELIVERY_FEE", "40")
FREE_DELIVERY_MINIMUM = os.getenv("FREE_DELIVERY_MINIMUM", "499")
COD_ENABLED = os.getenv("COD_ENABLED", "true").lower() == "true"
COD_FEE = os.getenv("COD_FEE", "0")
ONLINE_PAYMENT_ENABLED = os.getenv("ONLINE_PAYMENT_ENABLED", "false").lower() == "true"
TAX_ENABLED = os.getenv("TAX_ENABLED", "false").lower() == "true"
TAX_PERCENTAGE = os.getenv("TAX_PERCENTAGE", "0")
SERVICEABLE_PINCODES = [
    pin.strip()
    for pin in os.getenv("SERVICEABLE_PINCODES", "").split(",")
    if pin.strip()
]

# Razorpay Test Mode keys. Keep KEY_SECRET only on the backend.
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
