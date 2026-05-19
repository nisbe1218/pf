import requests

# Login pour obtenir un token
login_resp = requests.post("http://localhost:8000/api/auth/login/", 
                           json={"email": "admin@hopital.com", 
                                 "password": "MotDePasseSecurise123"})

if login_resp.status_code != 200:
    print(f"Login échoué: {login_resp.status_code} - {login_resp.text}")
    exit()

token = login_resp.json()["access"]
print(f"Token obtenu: {token[:50]}...")

# Lister les utilisateurs
resp = requests.get("http://localhost:8000/api/auth/utilisateurs/", 
                    headers={"Authorization": f"Bearer {token}"})

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    users = resp.json()
    print(f"Total: {len(users)} utilisateurs")
    for u in users:
        print(f"{u.get('id')} - {u.get('email')} - {u.get('role', {}).get('nom', 'sans rôle')}")
else:
    print("Erreur:", resp.text)
