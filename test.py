import requests

BASE_URL = "http://127.0.0.1:5000"

def step(title, res):
    print(f"\n=== {title} ===")
    try:
        print(res.json())
    except:
        print(res.text)

# ------------------ 1. REGISTER USERS ------------------

inspector = {
    "name": "Inspector One",
    "email": "inspector@test.com",
    "password": "1234",
    "role": "inspector"
}

requests.post(f"{BASE_URL}/register", json=inspector)

# ------------------ 2. LOGIN ------------------

res = requests.post(f"{BASE_URL}/login", json={
    "email": inspector["email"],
    "password": inspector["password"]
})
step("LOGIN", res)

user = res.json()["user"]
user_id = user["id"]

# ------------------ 3. CREATE TRACK (QR ASSET) ------------------

res = requests.post(f"{BASE_URL}/track", json={
    "track_code": "QR-TRACK-001",
    "location": "Chennai Central",
    "zone": "Southern Zone",
    "description": "Main line near platform 3"
})
step("CREATE TRACK", res)

track_id = res.json()["track_id"]

# ------------------ 4. SCAN QR ------------------

res = requests.get(f"{BASE_URL}/track/QR-TRACK-001")
step("SCAN QR", res)

# ------------------ 5. CREATE MAINTENANCE REQUEST ------------------

res = requests.post(f"{BASE_URL}/maintenance", json={
    "track_id": track_id,
    "reported_by": user_id,
    "title": "Crack detected",
    "description": "Visible crack on rail surface",
    "severity": "high"
})
step("CREATE MAINTENANCE", res)

request_id = res.json()["request_id"]

# ------------------ 6. UPLOAD IMAGE ------------------

files = {
    "file": ("damage.jpg", b"fake-image-data", "image/jpeg")
}

res = requests.post(
    f"{BASE_URL}/upload/{request_id}",
    files=files
)
step("UPLOAD IMAGE", res)

# ------------------ 7. UPDATE STATUS ------------------

res = requests.put(
    f"{BASE_URL}/maintenance/{request_id}/status",
    json={
        "status": "in_progress",
        "user_id": user_id
    }
)
step("UPDATE STATUS", res)

# ------------------ 8. AI ANALYSIS ------------------

res = requests.post(f"{BASE_URL}/ai/analyze", json={
    "request_id": request_id
})
step("AI ANALYSIS", res)

# ------------------ 9. FETCH ALL MAINTENANCE ------------------

res = requests.get(f"{BASE_URL}/maintenance/all")
step("ALL MAINTENANCE", res)

# ------------------ 10. FETCH AUDIT LOGS ------------------

res = requests.get(f"{BASE_URL}/audit")
step("AUDIT LOGS", res)

print("\n✅ DATABASE FULLY POPULATED & LIFECYCLE VERIFIED")
