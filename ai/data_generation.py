import csv
import random
import uuid
import datetime
from collections import defaultdict
from faker import Faker
from faker.providers import internet, user_agent, geo

fake = Faker()
fake.add_provider(internet)
fake.add_provider(user_agent)
fake.add_provider(geo)

# possible values for user agents
USER_AGENTS = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)…Chrome/114.0.5735.199",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)…Firefox/114.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)…Safari/16.5",
    "Mozilla/5.0 (X11; Linux x86_64)…Chrome/114.0.5735.199",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64)…Firefox/113.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)…Edg/114.0.1823.43",
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)…Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7)…Chrome/114.0.5735.199 Mobile",
    "Mozilla/5.0 (Linux; Android 13; SM‑G991B)…SamsungBrowser/20.0",
    "Mozilla/5.0 (Linux; U; Android 12; en‑US; Pixel 6)…Firefox/113.0",
    # Tablets
    "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X)…Safari/16.5",
    "Mozilla/5.0 (Linux; Android 12; SM‑T860)…Chrome/114.0.5735.199"
]

# possible values for geolocation
GEOLOC = [
    {"country":"USA","region":"California","city":"San Francisco"},
    {"country":"USA","region":"New York","city":"New York"},
    {"country":"UK", "region":"England","city":"London"},
    {"country":"DE", "region":"Bavaria","city":"Munich"},
    {"country":"IN", "region":"Maharashtra","city":"Mumbai"},
    {"country":"CN", "region":"Beijing","city":"Beijing"},
    {"country":"AU", "region":"New South Wales","city":"Sydney"},
    {"country":"BR", "region":"São Paulo","city":"São Paulo"},
    {"country":"ZA", "region":"Gauteng","city":"Johannesburg"},
    {"country":"JP", "region":"Tokyo Prefecture","city":"Tokyo"}
]

# possible public ips
IPS = [
    "178.33.227.196",  # FR
    "24.48.0.1",       # CA
    "89.233.29.110",   # DK
    "134.201.250.155", # US
    "91.198.174.192",  # NL
    "88.198.50.103",   # DE
    "133.242.0.3",     # JP
    "139.99.9.14",     # SG
    "170.244.102.6",   # BR
    "103.86.96.100",   # IN
    "51.15.0.0",       # FR
    "5.39.0.0",        # NL
    "13.224.0.0",      # US
    "52.32.0.0",       # CA
    "203.113.0.0"      # AU
]

def random_user_agent():
    return fake.user_agent()

def random_ip():
    return fake.ipv4_public()

def random_geo():
    return {
        "country": fake.country(),
        "region": fake.state(),
        "city": fake.city()
    }

# the neural network is not going to learn anything beyond this. having these rules will make it work with them only.
# TODO: turn this into a percentage from zero to one: the NN does not like big variations in numbers (normalize)
def rule_based_risk_score(login_result, ip_new, time_risk, device_new, geoloc_new):
    # starts from zero and accumulates points based on anomalies
    score = 0
    if ip_new: score += 30
    if time_risk: score += 20
    if device_new: score += 25
    if geoloc_new: score += 15
    return min(score, 100)

def generate_synthetic_login():
    # generate base data
    email = fake.email()
    timestamp = fake.date_time_between(start_date="-30d", end_date="now")
    ip_address = random.choice(IPS) if random.random()<0.7 else random_ip()
    user_agent = random.choice(USER_AGENTS) if random.random()<0.7 else random_user_agent()
    device_fingerprint = str(uuid.uuid4())
    login_result = random.choices([True, False], weights=[75,25])[0] # 75% success rate
    
    # simulate new ip/device/geoloc or not
    ip_new = random.choice([True, False])
    time_risk = timestamp.hour < 5 or timestamp.hour > 23 # risky time (e.g., 12am-5am or 11pm-12am)
    device_new = random.choice([True, False])
    geoloc = random.choice(GEOLOC) if random.random()<0.7 else random_geo()
    geoloc_new = random.choice([True, False])

    # generate risk score using rules (weak label)
    risk_score = rule_based_risk_score(login_result, ip_new, time_risk, device_new, geoloc_new)

    # TODO: make the score "wrong" sometimes

    return {
        "email": email,
        "timestamp": timestamp.isoformat(),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device_fingerprint": device_fingerprint,
        "login_result": login_result,
        "risk_score": risk_score,
        "country": geoloc["country"],
        "region": geoloc["region"],
        "city": geoloc["city"]
    }

def generate_synthetic_dataset(n, fraud_rate=0.05):
    """
    n: number of samples
    fraud_rate: probability that any given record is user‑reported fraud
    """
    streaks = defaultdict(int)
    # data = [generate_synthetic_login() for _ in range(n)]
    data = []

    for _ in range(n):
        rec = generate_synthetic_login()

        # update fail_streak counter for this user
        if not rec["login_result"]:
            streaks[rec["email"]] += 1
        else:
            streaks[rec["email"]] = 0
        rec["fail_streak"] = streaks[rec["email"]]

        # simulate user-reported fraud with given probability
        rec["fraud"] = random.random() < fraud_rate

        data.append(rec)
    return data

def save_dataset_to_csv(data, filename="synthetic_logins.csv"):
    if not data:
        return
    # use keys of 1st dictionary as CSV headers
    keys = data[0].keys()
    # "w" opens CSV file in write mode
    with open(filename, "w", newline="", encoding="utf-8") as output_file:
        # convert dictionaries into CSV rows
        dict_writer = csv.DictWriter(output_file, keys)
        # write header row
        dict_writer.writeheader()
        # write all data rows
        dict_writer.writerows(data)

if __name__ == "__main__":
    n_samples = 20000 # no. of synthetic logins
    dataset = generate_synthetic_dataset(n_samples, fraud_rate=0.05)
    save_dataset_to_csv(dataset)
    print(f"\n\nGenerated {n_samples} synthetic login attempts and saved to 'synthetic_logins.csv'\n\n")
