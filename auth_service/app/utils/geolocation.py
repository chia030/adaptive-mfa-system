import httpx
import json
from shared_lib.infrastructure.cache import get_auth_redis

redis = get_auth_redis()

def check_cached(ip_address: str):
    cache_key = f"geoloc:{ip_address}"
    print(f">Checking if geolocation for {ip_address} is cached.")
    cached = redis.get(cache_key)
    return cached
    
async def get_geolocation(ip_address: str) -> dict:
    cached = check_cached(ip_address)
    if ip_address in ("127.0.0.1", "localhost", "172.18.0.1"): # internal Docker IP 172.18.0.1
        # ip_address = "89.233.29.110"  # local device fallback IP, it simulates location in Copenhagen to test ipapi.co
        ip_address = ""

        # nonsense
        print("\n\n♥ Local device IP address detected ♥\n")
        print(r"""
         /\_/\  
        ( o.o ) 
         > ^ <
        """)
        print("\n\n")
        return {"country_name": "Unknown", "city": "Unknown", "region": "Unknown"} # not to waste (limited) ipapi calls
    elif cached:
        print(">Geolocation found in cache:", cached)
        geoloc = json.loads(cached) # converts the value string from Redis (formatted in JSON) into a py dictionary
        return geoloc

    try:
        async with httpx.AsyncClient() as client:
            # GET request to the ipapi.co API to fetch geolocation data
            r = await client.get(f"https://ipapi.co/{ip_address}/json/")
            if r.status_code == 200:
                print(f">Geolocation data fetched for IP: {ip_address}")
                response = r.json()
                print(">Response from ipapi.co:", response)
                geoloc = {"country_name": f"{response.get('country_name')}", "city": f"{response.get('city')}", "region": f"{response.get('region')}"}
                cache_key = f"geoloc:{ip_address}"
                print(f">Caching geolocation data for 1 month.")
                redis.setex(cache_key, 60 * 60 * 24 * 30, json.dumps(geoloc)) # exp after 30 days
                return geoloc
            else:
                print(f">Failed to fetch geolocation data for IP: {ip_address}, status code: {response.status_code}")
    except Exception as e:
        print(">Something went wrong...")
        print(e)

    # default values if API call failure or exception
    return {"country_name": "Unknown", "city": "Unknown", "region": "Unknown"}