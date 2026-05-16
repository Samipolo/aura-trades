import time, requests

URL = "https://aura-trades-api.onrender.com/api/analyze"
start = time.time()

for i in range(18):  # poll for up to 3 min
    try:
        r = requests.get(URL, timeout=120)
        elapsed = time.time() - start
        print(f"[{elapsed:.0f}s] Status: {r.status_code} | {r.text[:150]}")
        if r.status_code == 200:
            data = r.json()
            print(f"\n=== SUCCESS in {elapsed:.0f}s ===")
            print(f"Instruments: {data.get('total_instruments')}")
            print(f"Signals: {data.get('signals_generated')}")
            print(f"Errors: {len(data.get('errors', []))}")
            break
    except Exception as e:
        print(f"[{time.time()-start:.0f}s] Error: {e}")
    time.sleep(10)
else:
    print(f"\nFailed after {time.time()-start:.0f}s")
