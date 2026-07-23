# Healthyma Ecommerce

Healthyma is a mobile-friendly ecommerce website for natural and village-sourced products. It uses Flask, SQLite for local development fallback, optional MySQL, and plain HTML/CSS/JavaScript.

## Required Software

- Python 3.10+
- VS Code
- Git
- MySQL Server, optional for local development
- Modern browser

## Backend Setup

Windows PowerShell:

```powershell
cd C:\Users\elava\Desktop\healthyma_customer_website\healthyma\backend
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Expected backend:

```text
http://127.0.0.1:5000
```

## Frontend Setup

Open a second terminal:

```powershell
cd C:\Users\elava\Desktop\healthyma_customer_website\healthyma\frontend
python -m http.server 5500
```

Expected frontend:

```text
http://127.0.0.1:5500/login.html
http://127.0.0.1:5500/admin.html
http://127.0.0.1:5500/admin-dashboard.html
```

## Database Setup

### Option 1: SQLite development fallback

Set `DB_ENGINE=sqlite` in `backend/.env`. No MySQL setup is needed. The app creates the SQLite database and missing tables safely on startup.

### Option 2: MySQL

1. Start MySQL.
2. Create the `healthyma` database.
3. Run `backend/schema.sql` if this is a fresh database.
4. Set `DB_ENGINE=mysql` and configure `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `backend/.env`.
5. Start Flask with `python app.py`.
6. Check `http://127.0.0.1:5000/health`.

## Admin Control

Open:

```text
http://127.0.0.1:5500/admin.html
```

After a successful admin login, the browser redirects to:

```text
http://127.0.0.1:5500/admin-dashboard.html
```

Local demo login:

```text
Username: admin
Password: healthyma123
```

For production, change these environment variables in `backend/.env` before starting Flask:

```env
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=use-a-long-private-password
SECRET_KEY=replace-with-a-long-random-secret
FRONTEND_URL=https://your-frontend-domain.example
FLASK_ENV=production
```

The admin password is checked only by Flask and is not exposed in frontend JavaScript.

## Twilio SMS OTP Setup

To send OTPs by SMS, create a Twilio SMS sender and add the credentials to `backend/.env`:

```env
SMS_PROVIDER=twilio
SMS_COUNTRY_CODE=91
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SECRET=your_api_key_secret
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
TWILIO_MESSAGING_SERVICE_SID=
```

You can use `TWILIO_AUTH_TOKEN` instead of `TWILIO_API_KEY_SID` and `TWILIO_API_KEY_SECRET`, but keep all Twilio secrets only in `backend/.env`. If you use a Twilio Messaging Service, set `TWILIO_MESSAGING_SERVICE_SID` and leave `TWILIO_FROM_NUMBER` blank.

After editing `.env`, restart the backend and call `POST /api/send-otp`. For Indian mobile numbers, enter the 10-digit number; the backend sends SMS to `+91` plus that number.

## Main Local Flow

1. Open `login.html`.
2. Enter a 10-digit mobile number.
3. In development, the backend returns a demo OTP and the OTP page displays it.
4. Browse the five Healthyma products, open product details, add items to cart, save an address, apply `HEALTHY10` when the cart reaches the minimum order value, and place a COD order.
5. Open `admin.html`, login, confirm the order appears, update order status, and edit product stock or price.

Delivery addresses saved from `location.html` are stored in the backend database through `/api/addresses`. The browser keeps a small local cache only to show the selected location quickly in the header.

## Product Images

Place product images in:

```text
frontend/images/
```

Use web paths like `/images/moringa-mix-powder.jpeg` in Admin Control. Product changes made in Admin Control appear on the customer products page after refresh.

## Razorpay

Online payment stays disabled until real Razorpay credentials are configured. Add these backend-only values in `backend/.env`:

```env
ONLINE_PAYMENT_ENABLED=true
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

Never put `RAZORPAY_KEY_SECRET` in frontend files.

## Useful Endpoints

- `GET /health`
- `POST /api/send-otp`
- `POST /api/verify-otp`
- `GET /api/auth/session`
- `POST /api/auth/logout`
- `GET /api/categories`
- `GET /api/products`
- `GET /api/products/<id>`
- `POST /api/admin/login`
- `GET /api/admin/me`
- `POST /api/admin/logout`
- `GET /api/admin/dashboard`
- `GET /api/admin/products`
- `POST /api/admin/products`
- `PUT /api/admin/products/<id>`
- `GET /api/admin/orders`
- `PATCH /api/admin/orders/<id>/status`
- `GET /api/admin/customers`
- `PATCH /api/admin/customers/<id>/block`
- `GET /api/cart`
- `POST /api/cart/items`
- `PATCH /api/cart/items/<id>`
- `DELETE /api/cart/items/<id>`
- `DELETE /api/cart`
- `GET /api/addresses`
- `POST /api/addresses`
- `PATCH /api/addresses/<id>`
- `POST /api/addresses/<id>/default`
- `POST /api/coupons/validate`
- `POST /api/orders/cod`
- `GET /api/orders`
- `GET /api/orders/<order_number>`

## Test Commands

```powershell
cd backend
python -m py_compile app.py config.py
python -m pytest
cd ..
node --check frontend\js\admin.js
node --check frontend\js\products.js
node --check frontend\js\cart-utils.js
```

## Production Notes

Use environment variables for all secrets. Do not use SQLite as permanent production storage. Recommended start command for a WSGI host:

```text
gunicorn app:app
```

Razorpay test routes are present, but real checkout requires valid Razorpay credentials and production webhook testing.
