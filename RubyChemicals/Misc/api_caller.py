import requests

BASE_URL = "http://127.0.0.1:8000"
SESSION = requests.Session()

def get_csrf():
    # Hit any GET endpoint to receive CSRF cookie
    SESSION.get(f"{BASE_URL}/user-api/me-api/")
    return SESSION.cookies.get("csrftoken")

def api_post(url, payload):
    csrf = get_csrf()
    headers = {
        "X-CSRFToken": csrf
    }
    res = SESSION.post(url, json=payload, headers=headers)
    print("\nPOST", url, res.status_code)
    print(res.json())
    return res.json()

def api_get(url):
    res = SESSION.get(url)
    print("\nGET", url, res.status_code)
    print(res.json())
    return res.json()

# -----------------------------
# 1. LOGIN
# -----------------------------

print("\n--- LOGIN ---")
api_post(f"{BASE_URL}/user-api/login-api/", {
    "email": "admin@admin.com",
    "password": "Admin@123"
})

# -----------------------------
# 2. CREATE STOCK GROUPS
# -----------------------------

print("\n--- STOCK GROUPS ---")

raw = api_post(f"{BASE_URL}/operation-api/stock-group-api/", {
    "name": "Raw Material",
    "description": "Liquid and powder raw materials"
})

packing = api_post(f"{BASE_URL}/operation-api/stock-group-api/", {
    "name": "Packing",
    "description": "Buckets and containers"
})

finished = api_post(f"{BASE_URL}/operation-api/stock-group-api/", {
    "name": "Finished Goods",
    "description": "Final products"
})

raw_id = raw["data"]["id"]
packing_id = packing["data"]["id"]
finished_id = finished["data"]["id"]

# -----------------------------
# 3. CREATE STOCK ITEMS
# -----------------------------

print("\n--- STOCK ITEMS ---")

chemical = api_post(f"{BASE_URL}/operation-api/stock-item-api/", {
    "name": "Waterproof Chemical A",
    "group": raw_id,
    "unit": "kg"
})

binder = api_post(f"{BASE_URL}/operation-api/stock-item-api/", {
    "name": "Binder Powder",
    "group": raw_id,
    "unit": "kg"
})

bucket = api_post(f"{BASE_URL}/operation-api/stock-item-api/", {
    "name": "20kg Bucket",
    "group": packing_id,
    "unit": "pcs"
})

rainproof = api_post(f"{BASE_URL}/operation-api/stock-item-api/", {
    "name": "Rainproof",
    "group": finished_id,
    "unit": "kg"
})

chemical_id = chemical["data"]["id"]
binder_id = binder["data"]["id"]
bucket_id = bucket["data"]["id"]
rainproof_id = rainproof["data"]["id"]

# -----------------------------
# 4. STOCK INWARD
# -----------------------------

print("\n--- STOCK INWARD ---")

api_post(f"{BASE_URL}/operation-api/stock-inward-api/", {
    "stock_item_id": chemical_id,
    "quantity": 500,
    "date": "2026-01-15"
})

api_post(f"{BASE_URL}/operation-api/stock-inward-api/", {
    "stock_item_id": binder_id,
    "quantity": 200,
    "date": "2026-01-15"
})

api_post(f"{BASE_URL}/operation-api/stock-inward-api/", {
    "stock_item_id": bucket_id,
    "quantity": 50,
    "date": "2026-01-15"
})

# -----------------------------
# 5. PRODUCTION
# -----------------------------

print("\n--- PRODUCTION ---")

api_post(f"{BASE_URL}/operation-api/production-api/", {
    "batch_code": "RC001",
    "product_stock_item_id": rainproof_id,
    "production_date": "2026-01-15",
    "output_quantity": 300,
    "loss_quantity": 6,
    "consumptions": [
        {"stock_item_id": chemical_id, "quantity": 250},
        {"stock_item_id": binder_id, "quantity": 40},
        {"stock_item_id": bucket_id, "quantity": 15}
    ]
})

# -----------------------------
# 6. DISPATCH
# -----------------------------

print("\n--- DISPATCH ---")

api_post(f"{BASE_URL}/operation-api/dispatch-api/", {
    "stock_item_id": rainproof_id,
    "quantity": 120,
    "customer_name": "ABC Constructions",
    "dispatch_date": "2026-01-15"
})

# -----------------------------
# 7. EXPENSE HEAD
# -----------------------------

print("\n--- EXPENSE HEAD ---")

refresh = api_post(f"{BASE_URL}/operation-api/expense-head-api/", {
    "name": "Refreshments"
})

refresh_id = refresh["data"]["id"]

# -----------------------------
# 8. PETTY CASH
# -----------------------------

print("\n--- PETTY CASH ---")

api_post(f"{BASE_URL}/operation-api/petty-cash-api/", {
    "expense_head_id": refresh_id,
    "amount": 350,
    "expense_date": "2026-01-15",
    "notes": "Tea & snacks for workers"
})

# -----------------------------
# 9. FINAL STOCK CHECK
# -----------------------------

print("\n--- FINAL STOCK ---")
api_get(f"{BASE_URL}/operation-api/stock-item-api/")
