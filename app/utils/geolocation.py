import httpx

async def get_geolocation(ip_address: str) -> dict:
    if ip_address in ("127.0.0.1", "localhost"):
        # ip_address = "89.233.29.110"  # local device fallback IP, it simulates location in Copenhagen to test ipapi.co
        ip_address = ""

        # silly nonsense
        print("\n\n♥ Local device IP address detected ♥\n")
        print(r"""
         /\_/\  
        ( o.o ) 
         > ^ <
        """)
        print("\n\n")
        return {"country": "Unknown", "city": "Unknown", "region": "Unknown"} # not to waste (limited) ipapi calls

    try:
        async with httpx.AsyncClient() as client:
            # GET request to the ipapi.co API to fetch geolocation data
            response = await client.get(f"https://ipapi.co/{ip_address}/json/")
            if response.status_code == 200:
                print(f"\nGeolocation data fetched for IP: {ip_address}\n")
                return response.json()
            else:
                print(f"\nFailed to fetch geolocation data for IP: {ip_address}, status code: {response.status_code}\n")
                """
                From ipapi.co:
                The returned HTTP header X-Rl contains the number of requests remaining in the current rate limit window. X-Ttl contains the seconds until the limit is reset.
                Your implementation should always check the value of the X-Rl header, and if its is 0 you must not send any more requests for the duration of X-Ttl in seconds.
                """
                #TODO: print and check (at least) limit counter to avoid getting blocked, otherwise find alternatives
                #TODO: switch to another geolocation API, this one sucks!
                #TODO: maybe cache location data instead of calling the api for a previously used IP address
    except Exception:
        pass

    # default values if API call failure or exception
    return {"country": "Unknown", "city": "Unknown", "region": "Unknown"}
