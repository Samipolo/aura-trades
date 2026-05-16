import requests
import time

# Test EUR/USD
print("=== Testing AUDCAD=X ===")
r = requests.get("http://localhost:8000/api/chart-data/AUDCAD=X", timeout=60)
d = r.json()
print(f"Status: {r.status_code}")
print(f"Symbol: {d.get('display_name')}")
print(f"Source: {d.get('source')}")
print(f"Candles: {d.get('count', 0)}")
if d.get("candles"):
    print(f"First: {d['candles'][0]}")
    print(f"Last:  {d['candles'][-1]}")
    # Check if last candle is recent
    last_ts = d['candles'][-1]['time']
    age_hours = (time.time() - last_ts) / 3600
    print(f"Last candle age: {age_hours:.1f} hours ago")
else:
    print(f"Error: {d.get('error')}")
