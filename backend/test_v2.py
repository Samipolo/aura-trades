"""Quick V2 end-to-end test"""
import requests
import time
import json

print("AURA TRADES V2 - Full Pipeline Test")
print("=" * 50)

# Health check
r = requests.get("http://localhost:8000/api/health", timeout=10)
h = r.json()
print(f"Health: {h['status']} | Version: {h['version']} | Engines: {h['engines']}")

# Full analysis
print("\nRunning full analysis (this may take 1-3 minutes)...")
start = time.time()
r = requests.get("http://localhost:8000/api/analyze", timeout=600)
data = r.json()
elapsed = time.time() - start

print(f"\nStatus: {r.status_code}")
print(f"Time: {elapsed:.1f}s")
print(f"Success: {data.get('success')}")
print(f"Instruments scanned: {data.get('total_instruments')}")
print(f"Signals generated: {data.get('signals_generated')}")
print(f"Errors: {len(data.get('errors', []))}")

# Correlation
corr = data.get("correlation_data", {})
print(f"\n--- Correlation ---")
print(f"DXY Bias: {corr.get('dxy_bias')}")
print(f"Currency Strength: {corr.get('currency_strength', {}).get('index', {})}")
print(f"Risk Sentiment: {corr.get('risk_sentiment', {}).get('sentiment')}")
print(f"Lead-Lag: {len(corr.get('lead_lag', []))} relationships")
print(f"Cointegration: {len(corr.get('cointegration', []))} pairs")
print(f"Divergence signals: {len(corr.get('signals', []))}")

# Market overview
ov = data.get("market_overview", {})
print(f"\n--- Market Overview ---")
print(f"Bullish: {ov.get('bullish_instruments')} | Bearish: {ov.get('bearish_instruments')} | Neutral: {ov.get('neutral_instruments')}")
print(f"Strongest Currency: {ov.get('strongest_currency')}")
print(f"Weakest Currency: {ov.get('weakest_currency')}")
print(f"Best Pair: {ov.get('best_pair')}")

# Top trades
trades = data.get("ranked_trades", [])
print(f"\n--- Top 5 Trades ---")
for t in trades[:5]:
    print(f"  #{t['rank']} {t['display_name']:12s} {t['direction']:5s} "
          f"conf={t['confidence']:.0f}% grade={t.get('risk_grade','?')} "
          f"R:R=1:{t.get('dynamic_rr', t.get('risk_reward'))} "
          f"win={t.get('win_probability','-')}% "
          f"factors={t.get('num_factors',0)} "
          f"regime={t.get('quant_regime','?')} "
          f"wyckoff={t.get('wyckoff_phase','?')} "
          f"mtf={t.get('mtf_quality','?')}")

if trades:
    print(f"\n--- Top Trade Detail ---")
    t = trades[0]
    print(f"  Entry: {t['entry']} | SL: {t['stop_loss']} | TP: {t['take_profit']}")
    print(f"  Factors:")
    for f in t.get("factors", [])[:8]:
        print(f"    - {f['name']}: {f['score']}")
    if t.get("warnings"):
        print(f"  Warnings: {t['warnings']}")

# Errors
if data.get("errors"):
    print(f"\n--- Errors (first 5) ---")
    for e in data["errors"][:5]:
        print(f"  {e}")

print(f"\n{'=' * 50}")
print("V2 TEST COMPLETE")
