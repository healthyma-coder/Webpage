# =========================================================
# Healthyma Backend (Flask + MySQL)
# =========================================================
import random
import sqlite3
import string
import base64
import json
import hmac
import hashlib
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from pathlib import Path

import mysql.connector
from mysql.connector import Error as MySQLError
from flask import Flask, request, jsonify, session
from flask_cors import CORS

import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=config.IS_PRODUCTION,
    SESSION_COOKIE_SAMESITE="None" if config.IS_PRODUCTION else "Lax",
)

# Allow configured frontend origins to call this API and send session cookies.
CORS(app, origins=config.FRONTEND_ORIGINS, supports_credentials=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("healthyma")

DEV_DB_PATH = Path(__file__).with_name("healthyma_dev.sqlite3")
_sqlite_ready = False
_sqlite_lock = threading.Lock()


SAMPLE_PRODUCTS = [
    ("Moringa Mix Powder", "Health Mix", 180.00, 220.00, 18.18, "250", "g", "/images/moringa-mix-powder.jpeg", "Premium moringa leaf podi made for everyday nutrition.", 100, 1, 1),
    ("Curry Leaf Mix", "Health Mix", 160.00, 199.00, 19.60, "250", "g", "/images/curry-leaf-mix.jpeg", "Traditional karuveppilai podi with natural curry leaves and spices.", 100, 1, 1),
    ("Millet Atta", "Millet Flour", 220.00, 260.00, 15.38, "1", "kg", "/images/millet-atta.jpeg", "Multigrain millet flour with ragi, kambu, thinai, samai and kuthiravali.", 150, 1, 1),
    ("Kambu Ragi Mix", "Millet Flour", 210.00, 250.00, 16.00, "1", "kg", "/images/kambu-ragi-mix.jpeg", "Nutritious kambu, ragi and millet flour mix for daily cooking.", 150, 1, 1),
    ("Corn Flour", "Flour", 120.00, 150.00, 20.00, "500", "g", "/images/corn-flour.jpeg", "Pure corn flour for cooking, baking and everyday kitchen use.", 120, 1, 1),
]


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def category_image(name):
    images = {
        "Health Mix": "/images/moringa-mix-powder.jpeg",
        "Millet Flour": "/images/millet-atta.jpeg",
        "Flour": "/images/corn-flour.jpeg",
    }
    return images.get(name, "/images/default-product.jpg")


class SQLiteCursor:
    def __init__(self, cursor, dictionary=False):
        self.cursor = cursor
        self.dictionary = dictionary

    def execute(self, query, params=()):
        self.cursor.execute(query.replace("%s", "?"), params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row) if self.dictionary else tuple(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows] if self.dictionary else [tuple(row) for row in rows]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        self.cursor.close()


class SQLiteConnection:
    def __init__(self, connection):
        self.connection = connection

    def cursor(self, dictionary=False):
        return SQLiteCursor(self.connection.cursor(), dictionary=dictionary)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def init_sqlite():
    global _sqlite_ready
    if _sqlite_ready:
        return
    with _sqlite_lock:
        if _sqlite_ready:
            return
        _init_sqlite_unlocked()


def _init_sqlite_unlocked():
    global _sqlite_ready

    db = sqlite3.connect(DEV_DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            otp TEXT,
            otp_expiry DATETIME,
            otp_attempts INTEGER DEFAULT 0,
            otp_last_sent_at DATETIME,
            is_verified INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            image_url TEXT,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            slug TEXT,
            short_description TEXT,
            price REAL NOT NULL,
            original_price REAL,
            discount_percentage REAL DEFAULT 0,
            weight TEXT,
            unit TEXT,
            sku TEXT,
            image_url TEXT DEFAULT '/images/default-product.jpg',
            description TEXT,
            ingredients TEXT,
            benefits TEXT,
            usage_instructions TEXT,
            storage_instructions TEXT,
            stock INTEGER DEFAULT 100,
            low_stock_limit INTEGER DEFAULT 10,
            is_premium INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            is_best_seller INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            sku TEXT,
            unit TEXT,
            price REAL NOT NULL,
            original_price REAL,
            stock INTEGER DEFAULT 0,
            image_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            variant_id INTEGER,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id, variant_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            label TEXT DEFAULT 'Home',
            full_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            alternate_mobile TEXT,
            house TEXT NOT NULL,
            street TEXT NOT NULL,
            area TEXT NOT NULL,
            landmark TEXT,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode TEXT NOT NULL,
            delivery_instructions TEXT,
            latitude TEXT,
            longitude TEXT,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            address_id INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            product_discount REAL DEFAULT 0,
            coupon_discount REAL DEFAULT 0,
            delivery_fee REAL DEFAULT 0,
            cod_fee REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            grand_total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'PENDING',
            order_status TEXT DEFAULT 'PLACED',
            customer_note TEXT,
            cancellation_reason TEXT,
            idempotency_key TEXT,
            razorpay_order_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP,
            paid_at TIMESTAMP,
            delivered_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (address_id) REFERENCES addresses(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            variant_id INTEGER,
            product_name TEXT NOT NULL,
            variant_name TEXT,
            sku TEXT,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            line_total REAL NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (variant_id) REFERENCES product_variants(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_order_id TEXT,
            provider_payment_id TEXT,
            provider_signature TEXT,
            status TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            failure_code TEXT,
            failure_reason TEXT,
            raw_payload TEXT,
            paid_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            note TEXT,
            changed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            minimum_order REAL DEFAULT 0,
            maximum_discount REAL,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            usage_limit INTEGER,
            used_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'SUPER_ADMIN',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payment_webhook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            event_id TEXT UNIQUE,
            event_type TEXT,
            raw_payload TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    table_columns = {
        table: {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        for table in ["users", "products", "cart", "addresses", "orders", "order_items", "payments"]
    }
    migrations = {
        "users": {
            "name": "ALTER TABLE users ADD COLUMN name TEXT",
            "email": "ALTER TABLE users ADD COLUMN email TEXT",
            "otp_attempts": "ALTER TABLE users ADD COLUMN otp_attempts INTEGER DEFAULT 0",
            "otp_last_sent_at": "ALTER TABLE users ADD COLUMN otp_last_sent_at DATETIME",
            "is_blocked": "ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0",
            "updated_at": "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP",
        },
        "products": {
            "category_id": "ALTER TABLE products ADD COLUMN category_id INTEGER",
            "slug": "ALTER TABLE products ADD COLUMN slug TEXT",
            "short_description": "ALTER TABLE products ADD COLUMN short_description TEXT",
            "sku": "ALTER TABLE products ADD COLUMN sku TEXT",
            "ingredients": "ALTER TABLE products ADD COLUMN ingredients TEXT",
            "benefits": "ALTER TABLE products ADD COLUMN benefits TEXT",
            "usage_instructions": "ALTER TABLE products ADD COLUMN usage_instructions TEXT",
            "storage_instructions": "ALTER TABLE products ADD COLUMN storage_instructions TEXT",
            "low_stock_limit": "ALTER TABLE products ADD COLUMN low_stock_limit INTEGER DEFAULT 10",
            "is_featured": "ALTER TABLE products ADD COLUMN is_featured INTEGER DEFAULT 0",
            "is_best_seller": "ALTER TABLE products ADD COLUMN is_best_seller INTEGER DEFAULT 0",
            "updated_at": "ALTER TABLE products ADD COLUMN updated_at TIMESTAMP",
        },
        "cart": {
            "variant_id": "ALTER TABLE cart ADD COLUMN variant_id INTEGER",
            "updated_at": "ALTER TABLE cart ADD COLUMN updated_at TIMESTAMP",
        },
        "addresses": {
            "label": "ALTER TABLE addresses ADD COLUMN label TEXT DEFAULT 'Home'",
        },
        "orders": {
            "customer_note": "ALTER TABLE orders ADD COLUMN customer_note TEXT",
            "cancellation_reason": "ALTER TABLE orders ADD COLUMN cancellation_reason TEXT",
            "confirmed_at": "ALTER TABLE orders ADD COLUMN confirmed_at TIMESTAMP",
            "paid_at": "ALTER TABLE orders ADD COLUMN paid_at TIMESTAMP",
            "delivered_at": "ALTER TABLE orders ADD COLUMN delivered_at TIMESTAMP",
        },
        "order_items": {
            "variant_id": "ALTER TABLE order_items ADD COLUMN variant_id INTEGER",
            "variant_name": "ALTER TABLE order_items ADD COLUMN variant_name TEXT",
            "sku": "ALTER TABLE order_items ADD COLUMN sku TEXT",
            "image_url": "ALTER TABLE order_items ADD COLUMN image_url TEXT",
            "created_at": "ALTER TABLE order_items ADD COLUMN created_at TIMESTAMP",
        },
        "payments": {
            "provider_signature": "ALTER TABLE payments ADD COLUMN provider_signature TEXT",
            "currency": "ALTER TABLE payments ADD COLUMN currency TEXT DEFAULT 'INR'",
            "failure_code": "ALTER TABLE payments ADD COLUMN failure_code TEXT",
            "failure_reason": "ALTER TABLE payments ADD COLUMN failure_reason TEXT",
            "paid_at": "ALTER TABLE payments ADD COLUMN paid_at TIMESTAMP",
        },
    }
    for table, table_migrations in migrations.items():
        for column, sql in table_migrations.items():
            if column not in table_columns[table]:
                try:
                    db.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
    count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    existing_columns = {row[1] for row in db.execute("PRAGMA table_info(products)").fetchall()}
    product_migrations = {
        "original_price": "ALTER TABLE products ADD COLUMN original_price REAL",
        "discount_percentage": "ALTER TABLE products ADD COLUMN discount_percentage REAL DEFAULT 0",
        "weight": "ALTER TABLE products ADD COLUMN weight TEXT",
        "unit": "ALTER TABLE products ADD COLUMN unit TEXT",
            "is_premium": "ALTER TABLE products ADD COLUMN is_premium INTEGER DEFAULT 1",
            "low_stock_limit": "ALTER TABLE products ADD COLUMN low_stock_limit INTEGER DEFAULT 10",
            "is_best_seller": "ALTER TABLE products ADD COLUMN is_best_seller INTEGER DEFAULT 0",
            "is_active": "ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1",
        }
    for column, sql in product_migrations.items():
        if column not in existing_columns:
            db.execute(sql)
    category_names = ["Health Mix", "Millet Flour", "Flour"]
    db.execute(
        "UPDATE categories SET is_active=0 WHERE name NOT IN ({})".format(",".join(["?"] * len(category_names))),
        category_names,
    )
    for index, name in enumerate(category_names, start=1):
        db.execute(
            "INSERT OR IGNORE INTO categories (name, slug, image_url, sort_order) VALUES (?, ?, ?, ?)",
            (name, slugify(name), category_image(name), index),
        )
        db.execute(
            "UPDATE categories SET image_url=?, sort_order=?, is_active=1 WHERE name=?",
            (category_image(name), index, name),
        )
    db.execute("""
        INSERT OR IGNORE INTO coupons (
            code, discount_type, discount_value, minimum_order, maximum_discount, is_active
        ) VALUES ('HEALTHY10', 'PERCENTAGE', 10, 299, 100, 1)
    """)
    if count == 0:
        db.executemany(
            """
            INSERT INTO products (
                name, category, price, original_price, discount_percentage, weight, unit,
                image_url, description, stock, is_premium, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_PRODUCTS,
        )
    else:
        old_sample_names = [
            "Cold Pressed Groundnut Oil (1L)",
            "Cold Pressed Sesame Oil (1L)",
            "Raw Forest Honey (500g)",
            "Little Millet (1kg)",
            "Foxtail Millet (1kg)",
        ]
        for old_name, product in zip(old_sample_names, SAMPLE_PRODUCTS):
            name, category, price, original_price, discount, weight, unit, image_url, description, stock, is_premium, is_active = product
            db.execute(
                """
                UPDATE products
                SET name=?, category=?, price=?, original_price=?, discount_percentage=?,
                    weight=?, unit=?, image_url=?, description=?, stock=?, is_premium=?, is_active=?
                WHERE name=?
                """,
                (name, category, price, original_price, discount, weight, unit, image_url, description, stock, is_premium, is_active, old_name),
            )
        db.execute(
            "UPDATE products SET is_active=0 WHERE name IN ('A2 Cow Ghee (500ml)', 'Palm Jaggery (1kg)')"
        )
        for name, _category, price, original_price, discount, weight, unit, image_url, _description, _stock, is_premium, is_active in SAMPLE_PRODUCTS:
            db.execute(
                """
                INSERT INTO products (
                    name, category, price, original_price, discount_percentage, weight, unit,
                    image_url, description, stock, is_premium, is_active
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM products WHERE name=?)
                """,
                (name, _category, price, original_price, discount, weight, unit, image_url, _description, _stock, is_premium, is_active, name),
            )
            db.execute(
                """
                UPDATE products
                SET category=?,
                    price=?,
                    original_price=?,
                    discount_percentage=?,
                    weight=?,
                    unit=?,
                    image_url=?,
                    description=?,
                    stock=?,
                    is_premium=?,
                    is_active=?
                WHERE name=?
                """,
                (_category, price, original_price, discount, weight, unit, image_url, _description, _stock, is_premium, is_active, name),
            )
    db.commit()
    db.close()
    _sqlite_ready = True


def get_sqlite_db():
    init_sqlite()
    connection = sqlite3.connect(DEV_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return SQLiteConnection(connection)


def get_db():
    """Open a database connection for each request.

    MySQL is used when configured correctly. During local development, an
    automatic SQLite fallback keeps the frontend usable even before MySQL
    credentials/schema are ready.
    """
    if config.DB_ENGINE == "sqlite":
        return get_sqlite_db()
    try:
        return mysql.connector.connect(**config.DB_CONFIG)
    except MySQLError as exc:
        logger.warning("MySQL unavailable, using SQLite dev DB: %s", exc.__class__.__name__)
        return get_sqlite_db()


def generate_otp():
    return "".join(random.choices(string.digits, k=config.OTP_LENGTH))


def format_sms_phone(phone):
    country_code = re.sub(r"\D", "", config.SMS_COUNTRY_CODE or "91")
    return f"+{country_code}{phone}"


def send_twilio_sms(to_phone, message):
    account_sid = config.TWILIO_ACCOUNT_SID.strip()
    api_key_sid = config.TWILIO_API_KEY_SID.strip()
    api_key_secret = config.TWILIO_API_KEY_SECRET.strip()
    auth_token = config.TWILIO_AUTH_TOKEN.strip()
    from_number = config.TWILIO_FROM_NUMBER.strip()
    messaging_service_sid = config.TWILIO_MESSAGING_SERVICE_SID.strip()

    username = api_key_sid or account_sid
    password = api_key_secret or auth_token
    if not account_sid or not username or not password:
        raise RuntimeError("Twilio credentials are missing")
    if not from_number and not messaging_service_sid:
        raise RuntimeError("Set TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID")

    form = {
        "To": to_phone,
        "Body": message,
    }
    if messaging_service_sid:
        form["MessagingServiceSid"] = messaging_service_sid
    else:
        form["From"] = from_number

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    body = urllib.parse.urlencode(form).encode()
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    request_obj = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Twilio SMS failed: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Twilio SMS failed: {exc.reason}") from exc


def send_otp_sms(phone, otp):
    message = f"Your Healthyma OTP is {otp}. It expires in {config.OTP_EXPIRY_MINUTES} minutes."
    provider = config.SMS_PROVIDER
    if provider == "twilio":
        return send_twilio_sms(format_sms_phone(phone), message)
    if provider == "console":
        logger.info("Console OTP for %s is %s", phone, otp)
        return None
    raise RuntimeError(f"Unsupported SMS_PROVIDER: {provider}")


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def ok(message="Operation completed successfully.", data=None, status=200, **extra):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    body.update(extra)
    return jsonify(body), status


def api_error(message, status=400, error_code="BAD_REQUEST", **extra):
    body = {"success": False, "message": message, "error_code": error_code}
    body.update(extra)
    return jsonify(body), status


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not require_login():
            return api_error("Please login first", 401, "AUTH_REQUIRED")
        return func(*args, **kwargs)
    return wrapper


@app.errorhandler(404)
def not_found(_error):
    return api_error("The requested resource was not found.", 404, "NOT_FOUND")


@app.errorhandler(500)
def internal_error(error):
    logger.exception("Unexpected application error: %s", error)
    return api_error("Something went wrong. Please try again.", 500, "SERVER_ERROR")


# =========================================================
# 1) SEND OTP  ->  POST /api/send-otp   { "phone": "9876543210" }
# =========================================================
@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json(force=True)
    phone = validate_mobile(data.get("phone"))

    if not phone:
        return jsonify({"success": False, "message": "Enter a valid phone number"}), 400

    otp = generate_otp()
    now = datetime.now()
    expiry = now + timedelta(seconds=config.OTP_EXPIRY_SECONDS)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, otp_last_sent_at FROM users WHERE phone=%s", (phone,))
    existing = cursor.fetchone()

    if existing:
        last_sent = parse_datetime(existing.get("otp_last_sent_at"))
        if last_sent and (now - last_sent).total_seconds() < config.OTP_RESEND_SECONDS:
            cursor.close(); db.close()
            return jsonify({"success": False, "message": "Please wait before requesting another OTP"}), 429

    try:
        send_otp_sms(phone, otp)
    except RuntimeError as exc:
        logger.exception("Failed to send OTP SMS to %s", phone)
        cursor.close(); db.close()
        return jsonify({
            "success": False,
            "message": "Could not send OTP SMS. Please check SMS settings.",
            "detail": str(exc) if not config.IS_PRODUCTION else None,
        }), 503

    if existing:
        cursor.execute(
            "UPDATE users SET otp=%s, otp_expiry=%s, otp_attempts=0, otp_last_sent_at=%s, is_verified=0, updated_at=%s WHERE phone=%s",
            (otp, expiry, now, now, phone),
        )
    else:
        cursor.execute(
            "INSERT INTO users (phone, otp, otp_expiry, otp_attempts, otp_last_sent_at, is_verified) VALUES (%s,%s,%s,0,%s,0)",
            (phone, otp, expiry, now),
        )
    db.commit()
    cursor.close()
    db.close()

    response = {
        "success": True,
        "message": "OTP sent successfully"
    }
    if not config.IS_PRODUCTION and config.SHOW_DEMO_OTP:
        response["demo_otp"] = otp
        response["message"] = "Development OTP sent successfully"
    return jsonify(response)


# =========================================================
# 2) VERIFY OTP  ->  POST /api/verify-otp  { "phone": "...", "otp": "1234" }
# =========================================================
@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json(force=True)
    phone = validate_mobile(data.get("phone"))
    otp = (data.get("otp") or "").strip()
    if not phone or not otp:
        return jsonify({"success": False, "message": "Enter phone and OTP"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE phone=%s", (phone,))
    user = cursor.fetchone()

    if not user:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Phone number not found"}), 404

    if int(user.get("otp_attempts") or 0) >= config.OTP_MAX_ATTEMPTS:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Too many incorrect attempts. Please resend OTP."}), 429

    if user["otp"] != otp:
        cursor.execute("UPDATE users SET otp_attempts=COALESCE(otp_attempts, 0)+1, updated_at=%s WHERE phone=%s", (datetime.now(), phone))
        db.commit()
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400

    if datetime.now() > parse_datetime(user["otp_expiry"]):
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "OTP expired, please resend"}), 400

    cursor.execute("UPDATE users SET is_verified=1, otp=NULL, otp_expiry=NULL, otp_attempts=0, updated_at=%s WHERE phone=%s", (datetime.now(), phone))
    db.commit()
    cursor.close()
    db.close()

    # Log the user in via session cookie
    session.clear()
    session["user_id"] = user["id"]
    session["phone"] = phone

    return jsonify({"success": True, "message": "Login successful"})


def require_login():
    return "user_id" in session


def require_admin():
    return bool(session.get("admin_logged_in"))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not require_admin():
            return jsonify({"success": False, "message": "Admin login required"}), 401
        return func(*args, **kwargs)
    return wrapper


def money(value):
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_json(value):
    return f"{money(value):.2f}"


def config_money(name, default="0"):
    return money(getattr(config, name, default))


def config_bool(name, default=False):
    return bool(getattr(config, name, default))


def get_setting(name, default=None):
    return getattr(config, name, default)


def validate_mobile(value, required=True):
    digits = re.sub(r"\D", "", value or "")
    if not digits and not required:
        return ""
    if len(digits) != 10:
        return None
    return digits


def validate_pincode(value):
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) == 6 else None


def serviceability_for_pincode(pincode):
    valid = validate_pincode(pincode)
    if not valid:
        return {"serviceable": False, "message": "Enter a valid 6 digit pincode"}

    allowed = getattr(config, "SERVICEABLE_PINCODES", [])
    serviceable = not allowed or valid in allowed
    return {
        "serviceable": serviceable,
        "pincode": valid,
        "message": "Delivery available" if serviceable else "Delivery is not available for this pincode yet"
    }


def generate_order_number():
    return f"HM{datetime.now():%Y%m%d%H%M%S}{uuid.uuid4().hex[:5].upper()}"


def cart_items_from_db(cursor, user_id):
    cursor.execute("""
        SELECT c.product_id, c.quantity
        FROM cart c
        WHERE c.user_id=%s
    """, (user_id,))
    return cursor.fetchall()


def calculate_cart_totals(cursor, requested_items, coupon_code="", payment_method=""):
    if not requested_items:
        raise ValueError("Your cart is empty")

    normalized = []
    product_ids = []
    for raw in requested_items:
        product_id = int(raw.get("product_id") or 0)
        quantity = int(raw.get("quantity") or 0)
        if product_id <= 0 or quantity <= 0:
            raise ValueError("Invalid cart quantity")
        product_ids.append(product_id)
        normalized.append({"product_id": product_id, "quantity": quantity})

    placeholders = ",".join(["%s"] * len(product_ids))
    cursor.execute(f"""
        SELECT id, name, category, price, original_price, discount_percentage,
               weight, unit, image_url, stock, is_premium, is_active
        FROM products
        WHERE id IN ({placeholders}) AND COALESCE(is_active, 1)=1
    """, tuple(product_ids))
    products = {int(row["id"]): row for row in cursor.fetchall()}

    items = []
    subtotal = money("0")
    for item in normalized:
        product = products.get(item["product_id"])
        if not product:
            raise ValueError("A product in your cart is no longer available")

        stock = int(product.get("stock") or 0)
        quantity = item["quantity"]
        if quantity > stock:
            raise ValueError(f"Only {stock} left for {product['name']}")

        unit_price = money(product["price"])
        line_total = unit_price * quantity
        subtotal += line_total
        items.append({
            "product_id": int(product["id"]),
            "name": product["name"],
            "category": product.get("category"),
            "image_url": product.get("image_url"),
            "original_price": money_json(product.get("original_price") or unit_price),
            "discount_percentage": float(product.get("discount_percentage") or 0),
            "weight": product.get("weight"),
            "unit": product.get("unit"),
            "is_premium": bool(product.get("is_premium", True)),
            "stock": stock,
            "quantity": quantity,
            "unit_price": money_json(unit_price),
            "line_total": money_json(line_total),
        })

    product_discount = money("0")
    coupon_discount = money("0")
    coupon = None
    if coupon_code:
        cursor.execute("""
            SELECT * FROM coupons
            WHERE UPPER(code)=UPPER(%s) AND COALESCE(is_active, 1)=1
        """, (coupon_code.strip(),))
        coupon = cursor.fetchone()
        if not coupon:
            raise ValueError("Coupon is not valid")
        today = datetime.now()
        start_date = parse_datetime(coupon.get("start_date"))
        end_date = parse_datetime(coupon.get("end_date"))
        if start_date and today < start_date:
            raise ValueError("Coupon is not active yet")
        if end_date and today > end_date:
            raise ValueError("Coupon has expired")
        if coupon.get("usage_limit") is not None and int(coupon.get("used_count") or 0) >= int(coupon.get("usage_limit")):
            raise ValueError("Coupon usage limit reached")
        minimum_order = money(coupon.get("minimum_order") or 0)
        if subtotal < minimum_order:
            raise ValueError(f"Minimum order for this coupon is Rs.{minimum_order:.2f}")
        if coupon.get("discount_type") == "PERCENTAGE":
            coupon_discount = (subtotal * money(coupon.get("discount_value")) / Decimal("100")).quantize(Decimal("0.01"))
        else:
            coupon_discount = money(coupon.get("discount_value"))
        maximum_discount = coupon.get("maximum_discount")
        if maximum_discount is not None:
            coupon_discount = min(coupon_discount, money(maximum_discount))
        coupon_discount = min(coupon_discount, subtotal)
    delivery_fee = config_money("DELIVERY_FEE", "0")
    free_delivery_minimum = config_money("FREE_DELIVERY_MINIMUM", "0")
    if free_delivery_minimum and subtotal >= free_delivery_minimum:
        delivery_fee = money("0")

    cod_fee = config_money("COD_FEE", "0") if payment_method == "COD" and config_bool("COD_ENABLED", True) else money("0")
    tax_amount = money("0")
    if config_bool("TAX_ENABLED", False):
        tax_amount = ((subtotal - product_discount - coupon_discount) * config_money("TAX_PERCENTAGE", "0") / Decimal("100")).quantize(Decimal("0.01"))

    grand_total = subtotal - product_discount - coupon_discount + delivery_fee + cod_fee + tax_amount
    return {
        "items": items,
        "totals": {
            "subtotal": money_json(subtotal),
            "product_discount": money_json(product_discount),
            "coupon_discount": money_json(coupon_discount),
            "delivery_fee": money_json(delivery_fee),
            "cod_fee": money_json(cod_fee),
            "tax_amount": money_json(tax_amount),
            "grand_total": money_json(grand_total),
            "currency": "INR",
        },
        "payment_options": {
            "cod_enabled": config_bool("COD_ENABLED", True),
            "online_payment_enabled": config_bool("ONLINE_PAYMENT_ENABLED", False),
            "razorpay_key_id": get_setting("RAZORPAY_KEY_ID", ""),
        },
        "coupon": {"code": coupon["code"], "discount": money_json(coupon_discount)} if coupon else None,
    }


def address_payload(data):
    full_name = (data.get("full_name") or data.get("fullName") or "").strip()
    mobile = validate_mobile(data.get("mobile") or data.get("phone"))
    alternate_mobile = validate_mobile(data.get("alternate_mobile") or data.get("alternateMobile"), required=False)
    pincode = validate_pincode(data.get("pincode"))
    combined_address = (data.get("address_line") or data.get("addressLine") or data.get("house") or data.get("street") or "").strip()
    required = {
        "house": (data.get("house") or data.get("house_flat") or combined_address).strip(),
        "street": (data.get("street") or combined_address).strip(),
        "area": (data.get("area") or "").strip(),
        "city": (data.get("city") or "").strip(),
        "state": (data.get("state") or "Tamil Nadu").strip(),
    }

    errors = {}
    if not full_name:
        errors["full_name"] = "Full name is required"
    if not mobile:
        errors["mobile"] = "Mobile number must contain 10 digits"
    if alternate_mobile is None:
        errors["alternate_mobile"] = "Alternate mobile number must contain 10 digits"
    if not pincode:
        errors["pincode"] = "Pincode must contain 6 digits"
    for field, value in required.items():
        if not value:
            errors[field] = f"{field.replace('_', ' ').title()} is required"

    service = serviceability_for_pincode(pincode or "")
    if pincode and not service["serviceable"]:
        errors["pincode"] = service["message"]

    if errors:
        return None, errors

    return {
        "label": (data.get("label") or data.get("address_label") or data.get("addressLabel") or required["area"] or "Home").strip(),
        "full_name": full_name,
        "mobile": mobile,
        "alternate_mobile": alternate_mobile,
        "house": required["house"],
        "street": required["street"],
        "area": required["area"],
        "landmark": (data.get("landmark") or "").strip(),
        "city": required["city"],
        "state": required["state"],
        "pincode": pincode,
        "delivery_instructions": (data.get("delivery_instructions") or data.get("deliveryNote") or "").strip(),
        "latitude": str(data.get("latitude") or "").strip(),
        "longitude": str(data.get("longitude") or "").strip(),
        "is_default": 1 if data.get("is_default") or data.get("isDefault") else 0,
    }, {}


# =========================================================
# 3) GET PRODUCTS  ->  GET /api/products?category=Oils (category optional)
# =========================================================
@app.route("/api/products", methods=["GET"])
def get_products():
    category = (request.args.get("category") or "").strip()
    search = (request.args.get("search") or request.args.get("q") or "").strip()
    sort = (request.args.get("sort") or "newest").strip()
    featured = (request.args.get("featured") or "").lower()
    in_stock = (request.args.get("in_stock") or "").lower()
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, max(1, int(request.args.get("per_page", 12))))
        min_price = request.args.get("min_price")
        max_price = request.args.get("max_price")
        min_price_value = money(min_price) if min_price not in (None, "") else None
        max_price_value = money(max_price) if max_price not in (None, "") else None
    except Exception:
        return jsonify({"success": False, "message": "Invalid product filter"}), 422

    where = ["COALESCE(is_active, 1)=1"]
    params = []
    if category and category.lower() != "all":
        where.append("(LOWER(category)=LOWER(%s) OR LOWER(COALESCE(slug, ''))=LOWER(%s))")
        params.extend([category, category])
    if search:
        where.append("(LOWER(name) LIKE LOWER(%s) OR LOWER(COALESCE(description, '')) LIKE LOWER(%s) OR LOWER(category) LIKE LOWER(%s))")
        term = f"%{search}%"
        params.extend([term, term, term])
    if min_price_value is not None:
        where.append("price >= %s")
        params.append(str(min_price_value))
    if max_price_value is not None:
        where.append("price <= %s")
        params.append(str(max_price_value))
    if featured in ("1", "true", "yes"):
        where.append("COALESCE(is_featured, is_premium, 0)=1")
    if in_stock in ("1", "true", "yes"):
        where.append("stock > 0")

    order_by = {
        "price_low": "price ASC, id DESC",
        "price_high": "price DESC, id DESC",
        "newest": "id DESC",
        "name": "name ASC",
        "popular": "COALESCE(is_featured, is_premium, 0) DESC, stock DESC, id DESC",
    }.get(sort)
    if not order_by:
        return jsonify({"success": False, "message": "Invalid sort option"}), 422

    where_sql = " AND ".join(where)
    offset = (page - 1) * per_page

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(f"SELECT COUNT(*) AS total FROM products WHERE {where_sql}", tuple(params))
    total = int(cursor.fetchone()["total"])
    cursor.execute(f"""
        SELECT * FROM products
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """, tuple(params + [per_page, offset]))
    products = cursor.fetchall()
    cursor.close()
    db.close()

    data = {
        "items": products,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
    }
    return jsonify({"success": True, "message": "Products loaded", "data": data, "products": products})


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product_detail(product_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s AND COALESCE(is_active, 1)=1", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Product not found"}), 404
    cursor.execute("SELECT * FROM product_variants WHERE product_id=%s AND COALESCE(is_active, 1)=1 ORDER BY id", (product_id,))
    variants = cursor.fetchall()
    cursor.execute("""
        SELECT * FROM products
        WHERE id<>%s AND category=%s AND COALESCE(is_active, 1)=1
        ORDER BY COALESCE(is_featured, is_premium, 0) DESC, id DESC LIMIT 4
    """, (product_id, product.get("category")))
    similar = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Product loaded", "data": {"product": product, "variants": variants, "similar_products": similar}, "product": product})


@app.route("/api/categories", methods=["GET"])
def get_categories():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, c.name, c.slug, c.image_url, c.sort_order
        FROM categories c
        WHERE COALESCE(c.is_active, 1)=1
        UNION
        SELECT NULL AS id, p.category AS name, LOWER(REPLACE(p.category, ' ', '-')) AS slug,
               NULL AS image_url, 999 AS sort_order
        FROM products p
        WHERE COALESCE(p.is_active, 1)=1
        ORDER BY sort_order, name
    """)
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    seen = set()
    categories = []
    for row in rows:
        key = row["name"]
        if key in seen:
            continue
        seen.add(key)
        categories.append(row)
    return jsonify({
        "success": True,
        "message": "Categories loaded",
        "data": categories,
        "categories": [row["name"] for row in categories],
    })


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(force=True) if request.data else {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not hmac.compare_digest(username, config.ADMIN_USERNAME) or not hmac.compare_digest(password, config.ADMIN_PASSWORD):
        return jsonify({"success": False, "message": "Invalid admin username or password"}), 401
    session["admin_logged_in"] = True
    session["admin_username"] = username
    return jsonify({"success": True, "message": "Admin login successful", "admin": {"username": username}})


@app.route("/api/admin/me", methods=["GET"])
def admin_me():
    return jsonify({
        "success": True,
        "logged_in": require_admin(),
        "admin": {"username": session.get("admin_username")} if require_admin() else None,
    })


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return jsonify({"success": True, "message": "Admin logged out"})


@app.route("/api/admin/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            COUNT(*) AS total_products,
            SUM(CASE WHEN COALESCE(is_active, 1)=1 THEN 1 ELSE 0 END) AS active_products,
            SUM(CASE WHEN COALESCE(stock, 0) <= COALESCE(low_stock_limit, 10) AND COALESCE(stock, 0) > 0 THEN 1 ELSE 0 END) AS low_stock_products,
            SUM(CASE WHEN COALESCE(stock, 0) <= 0 THEN 1 ELSE 0 END) AS out_of_stock_products
        FROM products
    """)
    products = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) AS total_customers FROM users")
    customers = cursor.fetchone()
    cursor.execute("""
        SELECT
            COUNT(*) AS total_orders,
            SUM(CASE WHEN DATE(created_at)=DATE(%s) THEN 1 ELSE 0 END) AS today_orders,
            COALESCE(SUM(grand_total), 0) AS total_sales,
            COALESCE(SUM(CASE WHEN DATE(created_at)=DATE(%s) THEN grand_total ELSE 0 END), 0) AS today_sales,
            SUM(CASE WHEN order_status IN ('PLACED','CONFIRMED','PACKING','OUT_FOR_DELIVERY','PENDING_PAYMENT') THEN 1 ELSE 0 END) AS pending_orders,
            SUM(CASE WHEN order_status='DELIVERED' THEN 1 ELSE 0 END) AS delivered_orders
        FROM orders
    """, (today, today))
    orders = cursor.fetchone()
    cursor.close()
    db.close()
    stats = {**products, **customers, **orders}
    for key, value in list(stats.items()):
        stats[key] = float(value) if isinstance(value, Decimal) else (value or 0)
    return jsonify({"success": True, "stats": stats})


def admin_product_payload(data):
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "Healthyma").strip()
    price = money(data.get("price"))
    original_price = data.get("compare_price", data.get("original_price"))
    original_price = money(original_price) if original_price not in (None, "") else None
    if price < 0 or (original_price is not None and original_price < 0):
        raise ValueError("Prices cannot be negative")
    stock = int(data.get("stock") or 0)
    low_stock_limit = int(data.get("low_stock_limit") or 10)
    if stock < 0 or low_stock_limit < 0:
        raise ValueError("Stock values cannot be negative")
    discount = 0
    if original_price and original_price > price:
        discount = float(((original_price - price) / original_price * Decimal("100")).quantize(Decimal("0.01")))
    if not name:
        raise ValueError("Product name is required")
    return {
        "name": name,
        "slug": (data.get("slug") or slugify(name)).strip(),
        "category": category,
        "description": (data.get("description") or "").strip(),
        "price": money_json(price),
        "original_price": money_json(original_price) if original_price is not None else None,
        "discount_percentage": discount,
        "weight": (data.get("weight") or "").strip(),
        "unit": (data.get("unit") or "").strip(),
        "image_url": (data.get("image_url") or "/images/default-product.jpg").strip(),
        "stock": stock,
        "low_stock_limit": low_stock_limit,
        "is_featured": 1 if data.get("is_featured") else 0,
        "is_best_seller": 1 if data.get("is_best_seller") else 0,
        "is_active": 1 if data.get("is_active", True) else 0,
        "is_premium": 1,
    }


@app.route("/api/admin/products", methods=["GET"])
@admin_required
def admin_products():
    search = (request.args.get("search") or "").strip()
    category = (request.args.get("category") or "").strip()
    where = ["1=1"]
    params = []
    if search:
        where.append("(LOWER(name) LIKE LOWER(%s) OR LOWER(COALESCE(description, '')) LIKE LOWER(%s))")
        params.extend([f"%{search}%", f"%{search}%"])
    if category and category.lower() != "all":
        where.append("LOWER(category)=LOWER(%s)")
        params.append(category)
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT *, original_price AS compare_price, NULL AS offer_price
        FROM products
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
    """, tuple(params))
    products = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "products": products})


@app.route("/api/admin/products", methods=["POST"])
@admin_required
def admin_product_create():
    try:
        payload = admin_product_payload(request.get_json(force=True) if request.data else {})
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO products (
            name, slug, category, description, price, original_price, discount_percentage,
            weight, unit, image_url, stock, low_stock_limit, is_featured,
            is_best_seller, is_active, is_premium, created_at, updated_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        payload["name"], payload["slug"], payload["category"], payload["description"],
        payload["price"], payload["original_price"], payload["discount_percentage"],
        payload["weight"], payload["unit"], payload["image_url"], payload["stock"],
        payload["low_stock_limit"], payload["is_featured"], payload["is_best_seller"],
        payload["is_active"], payload["is_premium"], datetime.now(), datetime.now()
    ))
    product_id = cursor.lastrowid
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Product added", "product_id": product_id})


@app.route("/api/admin/products/<int:product_id>", methods=["PUT", "PATCH"])
@admin_required
def admin_product_update(product_id):
    try:
        payload = admin_product_payload(request.get_json(force=True) if request.data else {})
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE products SET name=%s, slug=%s, category=%s, description=%s, price=%s,
            original_price=%s, discount_percentage=%s, weight=%s, unit=%s, image_url=%s,
            stock=%s, low_stock_limit=%s, is_featured=%s, is_best_seller=%s,
            is_active=%s, is_premium=%s, updated_at=%s
        WHERE id=%s
    """, (
        payload["name"], payload["slug"], payload["category"], payload["description"],
        payload["price"], payload["original_price"], payload["discount_percentage"],
        payload["weight"], payload["unit"], payload["image_url"], payload["stock"],
        payload["low_stock_limit"], payload["is_featured"], payload["is_best_seller"],
        payload["is_active"], payload["is_premium"], datetime.now(), product_id
    ))
    changed = cursor.rowcount
    db.commit()
    cursor.close()
    db.close()
    if not changed:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True, "message": "Product updated"})


@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def admin_orders():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    where = ["1=1"]
    params = []
    if q:
        where.append("(LOWER(o.order_number) LIKE LOWER(%s) OR u.phone LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    if status and status.lower() != "all":
        where.append("o.order_status=%s")
        params.append(status)
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT o.*, u.phone AS customer_phone, a.full_name, a.mobile, a.house, a.street,
               a.area, a.landmark, a.city, a.state, a.pincode
        FROM orders o
        JOIN users u ON o.user_id=u.id
        LEFT JOIN addresses a ON o.address_id=a.id
        WHERE {' AND '.join(where)}
        ORDER BY o.id DESC
    """, tuple(params))
    orders = cursor.fetchall()
    for order in orders:
        cursor.execute("SELECT product_name, quantity, unit_price, line_total FROM order_items WHERE order_id=%s", (order["id"],))
        order["items"] = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "orders": orders})


@app.route("/api/admin/orders/<int:order_id>/status", methods=["PATCH"])
@admin_required
def admin_order_status(order_id):
    allowed = {"CONFIRMED", "PACKING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"}
    data = request.get_json(force=True) if request.data else {}
    new_status = (data.get("order_status") or "").strip().upper()
    if new_status not in allowed:
        return jsonify({"success": False, "message": "Invalid order status"}), 400
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, order_status FROM orders WHERE id=%s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"success": False, "message": "Order not found"}), 404
        old_status = order["order_status"]
        if new_status == "CANCELLED" and old_status != "CANCELLED":
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id=%s", (order_id,))
            for item in cursor.fetchall():
                cursor.execute("UPDATE products SET stock=stock+%s WHERE id=%s", (item["quantity"], item["product_id"]))
        delivered_at = datetime.now() if new_status == "DELIVERED" else None
        cursor.execute("UPDATE orders SET order_status=%s, delivered_at=COALESCE(delivered_at,%s), updated_at=%s WHERE id=%s",
                       (new_status, delivered_at, datetime.now(), order_id))
        cursor.execute("""
            INSERT INTO order_status_history (order_id, old_status, new_status, note, changed_by)
            VALUES (%s,%s,%s,%s,%s)
        """, (order_id, old_status, new_status, data.get("note") or "Updated from admin", session.get("admin_username", "admin")))
        db.commit()
    except Exception:
        if hasattr(db, "rollback"):
            db.rollback()
        raise
    finally:
        cursor.close()
        db.close()
    return jsonify({"success": True, "message": "Order status updated"})


@app.route("/api/admin/customers", methods=["GET"])
@admin_required
def admin_customers():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.phone, u.is_verified, COALESCE(u.is_blocked, 0) AS is_blocked, u.created_at,
               COUNT(o.id) AS total_orders,
               COALESCE(SUM(o.grand_total), 0) AS total_purchase_value,
               MAX(o.created_at) AS most_recent_order_date
        FROM users u
        LEFT JOIN orders o ON o.user_id=u.id
        GROUP BY u.id, u.phone, u.is_verified, u.is_blocked, u.created_at
        ORDER BY u.id DESC
    """)
    customers = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "customers": customers})


@app.route("/api/admin/customers/<int:user_id>/block", methods=["PATCH"])
@admin_required
def admin_customer_block(user_id):
    data = request.get_json(force=True) if request.data else {}
    is_blocked = 1 if data.get("is_blocked", True) else 0
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_blocked=%s, updated_at=%s WHERE id=%s", (is_blocked, datetime.now(), user_id))
    changed = cursor.rowcount
    db.commit()
    cursor.close()
    db.close()
    if not changed:
        return jsonify({"success": False, "message": "Customer not found"}), 404
    return jsonify({"success": True, "message": "Customer updated"})


# =========================================================
# 4) CART  -> add / view / remove
# =========================================================
@app.route("/api/cart/add", methods=["POST"])
@app.route("/api/cart/items", methods=["POST"])
def cart_add():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    data = request.get_json(force=True)
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))
    if quantity <= 0:
        return jsonify({"success": False, "message": "Quantity must be at least 1"}), 400
    user_id = session["user_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, stock FROM products WHERE id=%s AND COALESCE(is_active, 1)=1", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Product not found"}), 404

    cursor.execute(
        "SELECT * FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id)
    )
    existing = cursor.fetchone()
    new_quantity = quantity + int(existing["quantity"] if existing else 0)
    if new_quantity > int(product["stock"] or 0):
        cursor.close(); db.close()
        return jsonify({"success": False, "message": f"Only {product['stock']} left in stock"}), 400

    if existing:
        cursor.execute(
            "UPDATE cart SET quantity=%s WHERE id=%s",
            (new_quantity, existing["id"]),
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)",
            (user_id, product_id, quantity),
        )
    db.commit()
    cursor.close()
    db.close()

    return jsonify({"success": True, "message": "Added to cart"})


@app.route("/api/cart/update", methods=["POST"])
def cart_update():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    data = request.get_json(force=True)
    cart_id = data.get("cart_id")
    quantity = int(data.get("quantity") or 0)
    user_id = session["user_id"]
    if quantity < 0:
        return jsonify({"success": False, "message": "Invalid quantity"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, c.product_id, p.stock
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.id=%s AND c.user_id=%s
    """, (cart_id, user_id))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Cart item not found"}), 404
    if quantity == 0:
        cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
    elif quantity > int(row["stock"] or 0):
        cursor.close(); db.close()
        return jsonify({"success": False, "message": f"Only {row['stock']} left in stock"}), 400
    else:
        cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s AND user_id=%s", (quantity, cart_id, user_id))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Cart updated"})


@app.route("/api/cart/items/<int:cart_item_id>", methods=["PATCH"])
def cart_item_patch(cart_item_id):
    payload = request.get_json(force=True) if request.data else {}
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    quantity = int(payload.get("quantity") or 0)
    user_id = session["user_id"]
    if quantity <= 0:
        return jsonify({"success": False, "message": "Quantity must be at least 1"}), 400
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, p.stock
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.id=%s AND c.user_id=%s AND COALESCE(p.is_active, 1)=1
    """, (cart_item_id, user_id))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Cart item not found"}), 404
    if quantity > int(row["stock"] or 0):
        cursor.close(); db.close()
        return jsonify({"success": False, "message": f"Only {row['stock']} left in stock"}), 400
    cursor.execute("UPDATE cart SET quantity=%s, updated_at=%s WHERE id=%s AND user_id=%s", (quantity, datetime.now(), cart_item_id, user_id))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Cart updated"})


@app.route("/api/cart/items/<int:cart_item_id>", methods=["DELETE"])
def cart_item_delete(cart_item_id):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_item_id, session["user_id"]))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Removed from cart"})


@app.route("/api/cart/product/update", methods=["POST"])
def cart_product_update():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    data = request.get_json(force=True)
    product_id = data.get("product_id")
    quantity = int(data.get("quantity") or 0)
    user_id = session["user_id"]
    if quantity < 0:
        return jsonify({"success": False, "message": "Invalid quantity"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, stock FROM products WHERE id=%s AND COALESCE(is_active, 1)=1", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Product not found"}), 404
    if quantity > int(product["stock"] or 0):
        cursor.close(); db.close()
        return jsonify({"success": False, "message": f"Only {product['stock']} left in stock"}), 400

    cursor.execute("SELECT id FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
    row = cursor.fetchone()
    if quantity == 0:
        cursor.execute("DELETE FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
    elif row:
        cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s", (quantity, row["id"]))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)", (user_id, product_id, quantity))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Cart updated"})


@app.route("/api/cart", methods=["GET"])
def cart_view():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id AS cart_id, c.quantity, p.id AS product_id, p.name,
               p.price, p.original_price, p.discount_percentage, p.weight, p.unit,
               p.image_url, p.category, p.stock, p.is_premium
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s AND COALESCE(p.is_active, 1)=1
    """, (user_id,))
    items = cursor.fetchall()
    cursor.close()
    db.close()

    total = sum(float(i["price"]) * i["quantity"] for i in items)
    return jsonify({"success": True, "items": items, "total": round(total, 2)})


@app.route("/api/cart/validate", methods=["POST"])
def cart_validate():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    data = request.get_json(force=True) if request.data else {}
    requested = data.get("items")
    payment_method = (data.get("payment_method") or "").upper()
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if requested is None:
        requested = cart_items_from_db(cursor, session["user_id"])
    try:
        result = calculate_cart_totals(cursor, requested, data.get("coupon_code") or "", payment_method)
    except (ValueError, TypeError) as exc:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": str(exc)}), 400
    cursor.close()
    db.close()
    return jsonify({"success": True, **result})


@app.route("/api/cart/remove", methods=["POST"])
def cart_remove():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    data = request.get_json(force=True)
    cart_id = data.get("cart_id")
    user_id = session["user_id"]

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
    db.commit()
    cursor.close()
    db.close()

    return jsonify({"success": True, "message": "Removed from cart"})


@app.route("/api/cart", methods=["DELETE"])
def cart_clear():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id=%s", (session["user_id"],))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Cart cleared"})


@app.route("/api/delivery/check", methods=["GET"])
def delivery_check():
    return jsonify({"success": True, **serviceability_for_pincode(request.args.get("pincode", ""))})


@app.route("/api/coupons/validate", methods=["POST"])
def coupon_validate():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    data = request.get_json(force=True) if request.data else {}
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        result = calculate_cart_totals(cursor, cart_items_from_db(cursor, session["user_id"]), data.get("code") or data.get("coupon_code") or "")
    except ValueError as exc:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": str(exc)}), 400
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Coupon applied", "data": result.get("coupon"), "totals": result["totals"]})


@app.route("/api/addresses", methods=["GET"])
def addresses_list():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM addresses WHERE user_id=%s ORDER BY is_default DESC, id DESC", (session["user_id"],))
    addresses = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "addresses": addresses})


@app.route("/api/addresses", methods=["POST"])
def addresses_create():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    payload, errors = address_payload(request.get_json(force=True))
    if errors:
        return jsonify({"success": False, "message": "Please correct the address details", "errors": errors}), 400

    db = get_db()
    cursor = db.cursor()
    if payload["is_default"]:
        cursor.execute("UPDATE addresses SET is_default=0 WHERE user_id=%s", (session["user_id"],))
    cursor.execute("""
        INSERT INTO addresses (
            user_id, label, full_name, mobile, alternate_mobile, house, street, area, landmark,
            city, state, pincode, delivery_instructions, latitude, longitude, is_default
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        session["user_id"], payload["label"], payload["full_name"], payload["mobile"], payload["alternate_mobile"],
        payload["house"], payload["street"], payload["area"], payload["landmark"],
        payload["city"], payload["state"], payload["pincode"], payload["delivery_instructions"],
        payload["latitude"], payload["longitude"], payload["is_default"]
    ))
    address_id = cursor.lastrowid
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Address saved", "address_id": address_id})


@app.route("/api/addresses/<int:address_id>", methods=["GET"])
def addresses_get(address_id):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM addresses WHERE id=%s AND user_id=%s", (address_id, session["user_id"]))
    address = cursor.fetchone()
    cursor.close()
    db.close()
    if not address:
        return jsonify({"success": False, "message": "Address not found"}), 404
    return jsonify({"success": True, "message": "Address loaded", "address": address, "data": address})


@app.route("/api/addresses/<int:address_id>", methods=["PUT"])
@app.route("/api/addresses/<int:address_id>", methods=["PATCH"])
def addresses_update(address_id):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    payload, errors = address_payload(request.get_json(force=True))
    if errors:
        return jsonify({"success": False, "message": "Please correct the address details", "errors": errors}), 400

    db = get_db()
    cursor = db.cursor()
    if payload["is_default"]:
        cursor.execute("UPDATE addresses SET is_default=0 WHERE user_id=%s", (session["user_id"],))
    cursor.execute("""
        UPDATE addresses SET label=%s, full_name=%s, mobile=%s, alternate_mobile=%s, house=%s,
            street=%s, area=%s, landmark=%s, city=%s, state=%s, pincode=%s,
            delivery_instructions=%s, latitude=%s, longitude=%s, is_default=%s,
            updated_at=%s
        WHERE id=%s AND user_id=%s
    """, (
        payload["label"], payload["full_name"], payload["mobile"], payload["alternate_mobile"],
        payload["house"], payload["street"], payload["area"], payload["landmark"],
        payload["city"], payload["state"], payload["pincode"], payload["delivery_instructions"],
        payload["latitude"], payload["longitude"], payload["is_default"], datetime.now(),
        address_id, session["user_id"]
    ))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Address updated"})


@app.route("/api/addresses/<int:address_id>/default", methods=["POST"])
def addresses_default(address_id):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE addresses SET is_default=0 WHERE user_id=%s", (session["user_id"],))
    cursor.execute("UPDATE addresses SET is_default=1, updated_at=%s WHERE id=%s AND user_id=%s", (datetime.now(), address_id, session["user_id"]))
    changed = cursor.cursor.rowcount if isinstance(cursor, SQLiteCursor) else cursor.rowcount
    db.commit()
    cursor.close()
    db.close()
    if not changed:
        return jsonify({"success": False, "message": "Address not found"}), 404
    return jsonify({"success": True, "message": "Default address updated"})


@app.route("/api/addresses/<int:address_id>", methods=["DELETE"])
def addresses_delete(address_id):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM addresses WHERE id=%s AND user_id=%s", (address_id, session["user_id"]))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Address deleted"})


def create_order(payment_method, payment_status, order_status, address_id, idempotency_key=None, razorpay_order_id=None, coupon_code="", customer_note=""):
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COALESCE(is_blocked, 0) AS is_blocked FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        if user and int(user.get("is_blocked") or 0):
            raise ValueError("This customer account is blocked from placing orders")
        if idempotency_key:
            cursor.execute("""
                SELECT order_number FROM orders
                WHERE user_id=%s AND idempotency_key=%s
            """, (user_id, idempotency_key))
            existing = cursor.fetchone()
            if existing:
                return {"existing": True, "order_number": existing["order_number"]}

        cursor.execute("SELECT id FROM addresses WHERE id=%s AND user_id=%s", (address_id, user_id))
        if not cursor.fetchone():
            raise ValueError("Select a valid delivery address")

        items = cart_items_from_db(cursor, user_id)
        result = calculate_cart_totals(cursor, items, coupon_code, payment_method)
        totals = result["totals"]
        minimum_order = config_money("MINIMUM_ORDER_VALUE", "0")
        if money(totals["subtotal"]) < minimum_order:
            raise ValueError(f"Minimum order value is Rs.{minimum_order:.2f}")
        order_number = generate_order_number()
        cursor.execute("""
            INSERT INTO orders (
                order_number, user_id, address_id, subtotal, product_discount, coupon_discount,
                delivery_fee, cod_fee, tax_amount, grand_total, payment_method, payment_status,
                order_status, customer_note, idempotency_key, razorpay_order_id, confirmed_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            order_number, user_id, address_id, totals["subtotal"], totals["product_discount"],
            totals["coupon_discount"], totals["delivery_fee"], totals["cod_fee"], totals["tax_amount"],
            totals["grand_total"], payment_method, payment_status, order_status, customer_note, idempotency_key,
            razorpay_order_id, datetime.now() if order_status == "CONFIRMED" else None
        ))
        order_id = cursor.lastrowid
        for item in result["items"]:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, line_total, image_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                order_id, item["product_id"], item["name"], item["unit_price"],
                item["quantity"], item["line_total"], item.get("image_url")
            ))
            cursor.execute("UPDATE products SET stock=stock-%s WHERE id=%s AND stock >= %s",
                           (item["quantity"], item["product_id"], item["quantity"]))

        cursor.execute("""
            INSERT INTO payments (order_id, provider, provider_order_id, status, amount)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            order_id,
            "cod" if payment_method == "COD" else "razorpay",
            razorpay_order_id,
            "PENDING" if payment_status != "PAID" else "PAID",
            totals["grand_total"]
        ))
        cursor.execute("""
            INSERT INTO order_status_history (order_id, old_status, new_status, note, changed_by)
            VALUES (%s,%s,%s,%s,%s)
        """, (order_id, None, order_status, "Order created", "customer"))
        cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
        db.commit()
        return {"existing": False, "order_id": order_id, "order_number": order_number, "totals": totals, "items": result["items"]}
    except Exception:
        if hasattr(db, "rollback"):
            db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


@app.route("/api/orders/cod", methods=["POST"])
def orders_cod():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    if not config_bool("COD_ENABLED", True):
        return jsonify({"success": False, "message": "Cash on Delivery is not available"}), 400

    data = request.get_json(force=True)
    if not data.get("agree"):
        return jsonify({"success": False, "message": "Please accept the order confirmation"}), 400
    try:
        order = create_order(
            "COD",
            "COD_PENDING",
            "CONFIRMED",
            int(data.get("address_id") or 0),
            data.get("idempotency_key"),
            coupon_code=data.get("coupon_code") or "",
            customer_note=(data.get("customer_note") or "").strip(),
        )
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    return jsonify({"success": True, "message": "Order placed successfully", **order})


@app.route("/api/orders", methods=["GET"])
def orders_list():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT order_number, grand_total, payment_method, payment_status, order_status, created_at
        FROM orders WHERE user_id=%s ORDER BY id DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "orders": orders})


@app.route("/api/orders/<order_number>", methods=["GET"])
def order_detail(order_number):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE order_number=%s AND user_id=%s", (order_number, session["user_id"]))
    order = cursor.fetchone()
    if not order:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Order not found"}), 404
    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order["id"],))
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"success": True, "order": order, "items": items})


@app.route("/api/orders/<order_number>/payment-status", methods=["GET"])
def order_payment_status(order_number):
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT order_number, payment_method, payment_status, order_status, grand_total
        FROM orders WHERE order_number=%s AND user_id=%s
    """, (order_number, session["user_id"]))
    order = cursor.fetchone()
    cursor.close()
    db.close()
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    return jsonify({"success": True, "order": order})


@app.route("/api/payments/razorpay/create-order", methods=["POST"])
def razorpay_create_order():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    if not config_bool("ONLINE_PAYMENT_ENABLED", False):
        return jsonify({"success": False, "message": "Online payment is not configured yet"}), 503

    key_id = get_setting("RAZORPAY_KEY_ID", "")
    key_secret = get_setting("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        return jsonify({"success": False, "message": "Razorpay keys are missing on backend"}), 503

    try:
        import razorpay
    except ImportError:
        return jsonify({"success": False, "message": "Install backend dependency: pip install razorpay"}), 503

    data = request.get_json(force=True)
    address_id = int(data.get("address_id") or 0)
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM addresses WHERE id=%s AND user_id=%s", (address_id, session["user_id"]))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Select a valid delivery address"}), 400
        items = cart_items_from_db(cursor, session["user_id"])
        result = calculate_cart_totals(cursor, items, "", "ONLINE")
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    finally:
        cursor.close()
        db.close()

    receipt = generate_order_number()
    amount_paise = int(money(result["totals"]["grand_total"]) * 100)
    client = razorpay.Client(auth=(key_id, key_secret))
    rz_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
        "notes": {"healthyma_user_id": str(session["user_id"])}
    })

    try:
        order = create_order("ONLINE", "PENDING", "PENDING_PAYMENT", address_id, data.get("idempotency_key"), rz_order["id"])
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    return jsonify({
        "success": True,
        "key_id": key_id,
        "razorpay_order_id": rz_order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "order_number": order["order_number"],
        "totals": order.get("totals", result["totals"]),
    })


@app.route("/api/payments/razorpay/verify", methods=["POST"])
def razorpay_verify():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    secret = get_setting("RAZORPAY_KEY_SECRET", "")
    if not secret:
        return jsonify({"success": False, "message": "Razorpay key secret missing on backend"}), 503

    data = request.get_json(force=True)
    order_id = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature = data.get("razorpay_signature", "")
    expected = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return jsonify({"success": False, "message": "Payment verification failed"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, order_number FROM orders WHERE razorpay_order_id=%s AND user_id=%s", (order_id, session["user_id"]))
    order = cursor.fetchone()
    if not order:
        cursor.close(); db.close()
        return jsonify({"success": False, "message": "Order not found"}), 404

    cursor.execute("UPDATE orders SET payment_status='PAID', order_status='PLACED', updated_at=%s WHERE id=%s", (datetime.now(), order["id"]))
    cursor.execute("""
        UPDATE payments SET provider_payment_id=%s, status='PAID', raw_payload=%s, updated_at=%s
        WHERE order_id=%s AND provider='razorpay'
    """, (payment_id, json.dumps(data), datetime.now(), order["id"]))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Payment verified", "order_number": order["order_number"]})


@app.route("/api/webhooks/razorpay", methods=["POST"])
def razorpay_webhook():
    payload = request.get_data() or b"{}"
    webhook_secret = get_setting("RAZORPAY_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Razorpay-Signature", "")
    if webhook_secret:
        expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return jsonify({"success": False, "message": "Invalid webhook signature"}), 400

    body = request.get_json(silent=True) or {}
    event_id = body.get("event_id") or body.get("id") or hashlib.sha256(payload).hexdigest()
    event_type = body.get("event")
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO payment_webhook_events (provider, event_id, event_type, raw_payload, processed)
            VALUES (%s,%s,%s,%s,1)
        """, ("razorpay", event_id, event_type, payload.decode("utf-8", "ignore")))
        db.commit()
    except Exception:
        if hasattr(db, "rollback"):
            db.rollback()
    finally:
        cursor.close()
        db.close()
    return jsonify({"success": True})


# =========================================================
# 5) CHECKOUT -> builds a WhatsApp / Instagram deep link with order summary
# =========================================================
@app.route("/api/checkout-link", methods=["GET"])
def checkout_link():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401

    user_id = session["user_id"]
    phone = session.get("phone", "")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.name, p.price, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()
    cursor.close()
    db.close()

    if not items:
        return jsonify({"success": False, "message": "Your cart is empty"}), 400

    lines = [f"Hi Healthyma, I'd like to order:"]
    total = 0
    for i in items:
        subtotal = float(i["price"]) * i["quantity"]
        total += subtotal
        lines.append(f"- {i['name']} x{i['quantity']} = Rs.{subtotal:.2f}")
    lines.append(f"Total: Rs.{total:.2f}")
    lines.append(f"My phone number: {phone}")
    message = "\n".join(lines)

    import urllib.parse
    encoded_message = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/{config.WHATSAPP_NUMBER}?text={encoded_message}"
    instagram_url = f"https://ig.me/m/{config.INSTAGRAM_USERNAME}"

    return jsonify({
        "success": True,
        "whatsapp_url": whatsapp_url,
        "instagram_url": instagram_url,
        "order_summary": message
    })


@app.route("/api/me", methods=["GET"])
@app.route("/api/auth/session", methods=["GET"])
def me():
    return jsonify({"success": True, "logged_in": require_login(), "phone": session.get("phone"), "user_id": session.get("user_id")})


@app.route("/api/profile", methods=["GET"])
def profile_get():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, phone, name, email, is_verified, created_at FROM users WHERE id=%s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Profile loaded", "data": user, "profile": user})


@app.route("/api/profile", methods=["PATCH"])
def profile_update():
    if not require_login():
        return jsonify({"success": False, "message": "Please login first"}), 401
    data = request.get_json(force=True) if request.data else {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"success": False, "message": "Enter a valid email"}), 422
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET name=%s, email=%s, updated_at=%s WHERE id=%s", (name, email, datetime.now(), session["user_id"]))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True, "message": "Profile updated"})


@app.route("/api/logout", methods=["POST"])
@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/health", methods=["GET"])
def health():
    database = "ok"
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db.close()
    except Exception:
        logger.exception("Health database check failed")
        database = "error"
    return jsonify({"status": "ok" if database == "ok" else "degraded", "database": database}), (200 if database == "ok" else 503)


if __name__ == "__main__":
    app.run(debug=not config.IS_PRODUCTION, port=5000)
