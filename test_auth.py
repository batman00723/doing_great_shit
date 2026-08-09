import requests

BASE_URL = "http://127.0.0.1:8000/api_v1/auth"

print("1. Registering Organisation...")
res1 = requests.post(f"{BASE_URL}/register-org", json={
    "organisation_name": "Test Org",
    "admin_name": "Test Admin",
    "email": "admin@test.com",
    "password": "password123"
})
print(res1.status_code, res1.text)

print("\n2. Logging in as Admin...")
res2 = requests.post(f"{BASE_URL}/login", json={
    "email": "admin@test.com",
    "password": "password123"
})
print(res2.status_code, res2.text)

if res2.status_code == 200:
    access_token = res2.json()["access_token"]
    
    print("\n3. Registering Salesperson...")
    res3 = requests.post(f"{BASE_URL}/register-salesperson", json={
        "salesperson_name": "Test Sales",
        "email": "sales@test.com",
        "password": "password123"
    }, headers={
        "Authorization": f"Bearer {access_token}"
    })
    print(res3.status_code, res3.text)
