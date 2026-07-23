from pathlib import Path

import app as healthyma_app


def client_with_temp_db(tmp_path):
    healthyma_app.DEV_DB_PATH = Path(tmp_path) / "healthyma_test.sqlite3"
    healthyma_app._sqlite_ready = False
    healthyma_app.config.SHOW_DEMO_OTP = True
    healthyma_app.app.config.update(TESTING=True)
    return healthyma_app.app.test_client()


def login(client, phone="9876543210"):
    otp_response = client.post("/api/send-otp", json={"phone": phone})
    assert otp_response.status_code == 200
    otp = otp_response.get_json()["demo_otp"]
    verify_response = client.post("/api/verify-otp", json={"phone": phone, "otp": otp})
    assert verify_response.status_code == 200


def test_health_and_products(tmp_path):
    client = client_with_temp_db(tmp_path)
    assert client.get("/health").status_code == 200

    products = client.get("/api/products?search=moringa&per_page=2").get_json()
    assert products["success"] is True
    assert products["data"]["total"] >= 1

    detail = client.get("/api/products/1").get_json()
    assert detail["success"] is True
    assert detail["data"]["product"]["id"] == 1


def test_login_cart_coupon_and_cod_order(tmp_path):
    client = client_with_temp_db(tmp_path)
    login(client)

    cart = client.post("/api/cart/items", json={"product_id": 1, "quantity": 2})
    assert cart.status_code == 200

    coupon = client.post("/api/coupons/validate", json={"code": "HEALTHY10"})
    assert coupon.status_code == 200

    address = client.post("/api/addresses", json={
        "full_name": "Test Customer",
        "mobile": "9876543210",
        "house": "12",
        "street": "Market Street",
        "area": "Town",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600001",
        "is_default": True,
    })
    assert address.status_code == 200

    order = client.post("/api/orders/cod", json={
        "address_id": address.get_json()["address_id"],
        "coupon_code": "HEALTHY10",
        "agree": True,
    })
    assert order.status_code == 200
    assert order.get_json()["order_number"].startswith("HM")
