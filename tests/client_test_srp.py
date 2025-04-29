import requests
import srp

srp.rfc5054_enable()

API = "http://localhost:8000"

EMAIL = "anothertest1@example.com"
PASSWORD = "SecretPassword123!"

def delete_user():
    # delete user via /users/{email} endpoint
    r = requests.delete(f"{API}/users/{EMAIL}")
    print(f"Deleted {EMAIL} from DB:", r.status_code, r.text)

def register():
    # register user via /register endpoint
    r = requests.post(f"{API}/register?email={EMAIL}&password={PASSWORD}")
    print("Register:", r.status_code, r.text)

def srp_handshake():
    #  ==== SRP handshake (start & verify) ====

    # CLIENT 1. create SRP User & generate A (public client ephemeral)
    usr = srp.User(EMAIL, PASSWORD, hash_alg=srp.SHA256, ng_type=srp.NG_2048)      
    I, A_bytes = usr.start_authentication()
    
    A_hex = A_bytes.hex()
    print("A:", A_hex)

    # ==== START ====

    # CLIENT 2. SERVER SRP START: get salt & B (public server ephemeral)
    payload = {"email": I, "A": A_hex}
    r = requests.post(f"{API}/auth/srp/start", json=payload)
    r.raise_for_status()
    data = r.json()
    salt_hex = data["salt"]
    B_hex = data["B"]
    print(f"Server salt:{data["salt"]}")
    print(f"Server B:{data["B"]}")
    print("Received salt & B from server")

    # CLIENT 3. process server challenge (B) & compute M1 (client proof)
    salt_bytes = bytes.fromhex(salt_hex)
    B_bytes = bytes.fromhex(B_hex)
    M1_bytes = usr.process_challenge(salt_bytes, B_bytes)
    M1_hex = M1_bytes.hex()
    print("Computed client proof (M1)")
    print("M1:", M1_hex)

    # ==== VERIFY ====

    # CLIENT 4. SERVER SRP VERIFY: send M1, get server's proof (M2)
    payload = {"email": I, "M1": M1_hex}
    r2 = requests.post(f"{API}/auth/srp/verify", json=payload)
    print("Status:", r2.status_code)
    print("Response body:", r2.text)
    r2.raise_for_status()
    resp = r2.json()
    M2_hex = resp["M2"]
    print("Server proof M2:", M2_hex)

    M2 = bytes.fromhex(M2_hex)
    # print(f"M2 bytes: {M2}")

    # CLIENT 5. verify server's proof (M2)
    usr.verify_session(M2) # does not return True for some reason (even tho it's supposed to according to the documentation)
    if usr.authenticated():
        print("SRP handshake successful — mutual proof verified")
        print("Client K =", usr.get_session_key().hex())

    else:
        print("SRP handshake failed — server proof mismatch")

if __name__ == "__main__":
    # delete user if exists
    delete_user()
    # register user
    register()
    # perform SRP handshake
    srp_handshake()
