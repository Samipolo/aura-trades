"""
AURA TRADES — Multi-Source Data Aggregator
Exploits the 15-minute delay regulatory rule to aggregate free data from:
  1. Yahoo Finance   — Primary workhorse (real-time FX/Crypto, 15m delayed equities)
  2. Alpha Vantage   — Intraday down to 1-min (25 req/day free → SQLite cache)
  3. Financial Modeling Prep (FMP) — Stocks, forex, crypto + fundamentals
  4. Alpaca Markets  — Institutional-grade US equities (IEX real-time or 15m SIP)

Smart routing: Each asset class is routed to its best free provider.
Consensus pricing: Cross-references prices from multiple sources for reliability.
Caching: SQLite-backed cache respects rate limits (especially Alpha Vantage).
"""

import os
import json
import time
import sqlite3
import traceback
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Any

import requests
import pandas as pd
import numpy as np

# ── API Keys (from environment or .env) ─────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
FMP_KEY = os.getenv("FMP_KEY", "")
ALPACA_KEY_ID = os.getenv("ALPACA_KEY_ID", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET", "")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ── SQLite Cache (for rate-limited APIs) ─────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "source_cache.db")
_db_lock = threading.Lock()


def _init_cache_db():
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            source TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            ttl_seconds INTEGER NOT NULL DEFAULT 900
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS rate_tracker (
            source TEXT PRIMARY KEY,
            calls_today INTEGER DEFAULT 0,
            last_reset TEXT,
            daily_limit INTEGER DEFAULT 25
        )""")
        conn.commit()


_init_cache_db()


def _cache_get(key: str, max_age_s: int = 900) -> Optional[dict]:
    """Retrieve cached data if still fresh."""
    with _db_lock:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                row = conn.execute(
                    "SELECT data, fetched_at FROM api_cache WHERE cache_key=?", (key,)
                ).fetchone()
                if row and (time.time() - row[1]) < max_age_s:
                    return json.loads(row[0])
        except Exception:
            pass
    return None


def _cache_set(key: str, data: dict, source: str, ttl: int = 900):
    """Store data in cache."""
    with _db_lock:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO api_cache (cache_key, data, source, fetched_at, ttl_seconds) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (key, json.dumps(data), source, time.time(), ttl),
                )
                conn.commit()
        except Exception:
            pass


def _check_rate_limit(source: str, daily_limit: int = 25) -> bool:
    """Returns True if we still have API calls left today."""
    today = datetime.now().strftime("%Y-%m-%d")
    with _db_lock:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                row = conn.execute(
                    "SELECT calls_today, last_reset FROM rate_tracker WHERE source=?",
                    (source,),
                ).fetchone()
                if not row or row[1] != today:
                    conn.execute(
                        "INSERT OR REPLACE INTO rate_tracker (source, calls_today, last_reset, daily_limit) "
                        "VALUES (?, 0, ?, ?)",
                        (source, today, daily_limit),
                    )
                    conn.commit()
                    return True
                return row[0] < daily_limit
        except Exception:
            return False


def _increment_rate(source: str):
    today = datetime.now().strftime("%Y-%m-%d")
    with _db_lock:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    "UPDATE rate_tracker SET calls_today = calls_today + 1 WHERE source=? AND last_reset=?",
                    (source, today),
                )
                conn.commit()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: YAHOO FINANCE (already exists — wrapper for consensus)
# ══════════════════════════════════════════════════════════════════════════════

def _yahoo_quote(symbol: str) -> Optional[dict]:
    """Quick quote from Yahoo Finance v8 API."""
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "5d", "includePrePost": "false"}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", 0))
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        return {
            "price": round(price, 5),
            "prev_close": round(prev_close, 5),
            "change_pct": round(change_pct, 3),
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", ""),
            "source": "yahoo_finance",
            "delay": "real-time" if symbol.endswith(("=X", "-USD")) else "≤15min",
        }
    except Exception:
        return None


def _yahoo_intraday(symbol: str, interval: str = "15m", range_str: str = "5d") -> pd.DataFrame:
    """Intraday OHLCV from Yahoo Finance."""
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": interval, "range": range_str, "includePrePost": "false"}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        ts = result.get("timestamp")
        if not ts:
            return pd.DataFrame()
        q = result.get("indicators", {}).get("quote", [{}])[0]
        df = pd.DataFrame({
            "open": q.get("open", []),
            "high": q.get("high", []),
            "low": q.get("low", []),
            "close": q.get("close", []),
            "volume": q.get("volume", []),
        }, index=pd.to_datetime(ts, unit="s", utc=True))
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = df["volume"].fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: ALPHA VANTAGE (25 req/day free — cached aggressively)
# ══════════════════════════════════════════════════════════════════════════════

def _av_quote(symbol: str) -> Optional[dict]:
    """Alpha Vantage global quote (uses 1 API call)."""
    if not ALPHA_VANTAGE_KEY:
        return None
    cache_key = f"av_quote_{symbol}"
    cached = _cache_get(cache_key, max_age_s=900)  # 15 min cache
    if cached:
        return cached

    if not _check_rate_limit("alpha_vantage", 25):
        return None

    try:
        url = "https://www.alphavantage.co/query"
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHA_VANTAGE_KEY}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        _increment_rate("alpha_vantage")
        data = r.json().get("Global Quote", {})
        if not data:
            return None
        price = float(data.get("05. price", 0))
        prev = float(data.get("08. previous close", 0))
        change_pct = float(data.get("10. change percent", "0").replace("%", ""))
        result = {
            "price": round(price, 5),
            "prev_close": round(prev, 5),
            "change_pct": round(change_pct, 3),
            "volume": int(data.get("06. volume", 0)),
            "source": "alpha_vantage",
            "delay": "≤15min",
        }
        _cache_set(cache_key, result, "alpha_vantage", ttl=900)
        return result
    except Exception:
        return None


def _av_intraday(symbol: str, interval: str = "15min") -> pd.DataFrame:
    """Alpha Vantage intraday OHLCV (uses 1 API call, cached for 15 min)."""
    if not ALPHA_VANTAGE_KEY:
        return pd.DataFrame()
    cache_key = f"av_intraday_{symbol}_{interval}"
    cached = _cache_get(cache_key, max_age_s=900)
    if cached:
        try:
            return pd.DataFrame(cached)
        except Exception:
            pass

    if not _check_rate_limit("alpha_vantage", 25):
        return pd.DataFrame()

    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "outputsize": "compact",
            "apikey": ALPHA_VANTAGE_KEY,
        }
        r = requests.get(url, params=params, headers=_HEADERS, timeout=20)
        _increment_rate("alpha_vantage")
        ts_key = f"Time Series ({interval})"
        series = r.json().get(ts_key, {})
        if not series:
            return pd.DataFrame()

        rows = []
        for dt_str, vals in series.items():
            rows.append({
                "open": float(vals["1. open"]),
                "high": float(vals["2. high"]),
                "low": float(vals["3. low"]),
                "close": float(vals["4. close"]),
                "volume": int(vals["5. volume"]),
                "datetime": dt_str,
            })
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df["datetime"], utc=True)
        df = df.drop(columns=["datetime"]).sort_index()
        _cache_set(cache_key, df.reset_index().to_dict(orient="list"), "alpha_vantage", ttl=900)
        return df
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3: FINANCIAL MODELING PREP (FMP)
# ══════════════════════════════════════════════════════════════════════════════

def _fmp_quote(symbol: str) -> Optional[dict]:
    """FMP real-time / 15-min delayed quote."""
    if not FMP_KEY:
        return None
    cache_key = f"fmp_quote_{symbol}"
    cached = _cache_get(cache_key, max_age_s=300)
    if cached:
        return cached

    try:
        url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
        r = requests.get(url, params={"apikey": FMP_KEY}, headers=_HEADERS, timeout=15)
        data = r.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        q = data[0]
        result = {
            "price": round(float(q.get("price", 0)), 5),
            "prev_close": round(float(q.get("previousClose", 0)), 5),
            "change_pct": round(float(q.get("changesPercentage", 0)), 3),
            "volume": int(q.get("volume", 0)),
            "market_cap": q.get("marketCap"),
            "pe": q.get("pe"),
            "eps": q.get("eps"),
            "day_high": q.get("dayHigh"),
            "day_low": q.get("dayLow"),
            "year_high": q.get("yearHigh"),
            "year_low": q.get("yearLow"),
            "source": "fmp",
            "delay": "≤15min",
        }
        _cache_set(cache_key, result, "fmp", ttl=300)
        return result
    except Exception:
        return None


def _fmp_fundamentals(symbol: str) -> Optional[dict]:
    """FMP fundamental data — earnings, balance sheet, ratios."""
    if not FMP_KEY:
        return None
    cache_key = f"fmp_fundamentals_{symbol}"
    cached = _cache_get(cache_key, max_age_s=86400)  # cache 24h — fundamentals don't change fast
    if cached:
        return cached

    try:
        base = "https://financialmodelingprep.com/api/v3"
        # Key ratios
        r = requests.get(f"{base}/ratios-ttm/{symbol}", params={"apikey": FMP_KEY}, timeout=15)
        ratios = r.json()[0] if r.json() else {}
        # Profile
        r2 = requests.get(f"{base}/profile/{symbol}", params={"apikey": FMP_KEY}, timeout=15)
        profile = r2.json()[0] if r2.json() else {}

        result = {
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "market_cap": profile.get("mktCap"),
            "beta": profile.get("beta"),
            "dividend_yield": ratios.get("dividendYielTTM"),
            "pe_ratio": ratios.get("peRatioTTM"),
            "peg_ratio": ratios.get("pegRatioTTM"),
            "roe": ratios.get("returnOnEquityTTM"),
            "roa": ratios.get("returnOnAssetsTTM"),
            "debt_equity": ratios.get("debtEquityRatioTTM"),
            "current_ratio": ratios.get("currentRatioTTM"),
            "source": "fmp",
        }
        _cache_set(cache_key, result, "fmp", ttl=86400)
        return result
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4: ALPACA MARKETS (Paper Trading — US Equities)
# ══════════════════════════════════════════════════════════════════════════════

def _alpaca_quote(symbol: str) -> Optional[dict]:
    """Alpaca latest quote for US equities."""
    if not ALPACA_KEY_ID or not ALPACA_SECRET:
        return None
    # Alpaca only handles US stocks/ETFs — skip forex/crypto/futures
    if any(c in symbol for c in ["=X", "=F", "-USD", "^"]):
        return None

    cache_key = f"alpaca_quote_{symbol}"
    cached = _cache_get(cache_key, max_age_s=60)
    if cached:
        return cached

    try:
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
        headers = {
            "APCA-API-KEY-ID": ALPACA_KEY_ID,
            "APCA-API-SECRET-KEY": ALPACA_SECRET,
        }
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("quote", {})
        mid = (float(data.get("ap", 0)) + float(data.get("bp", 0))) / 2
        if mid <= 0:
            return None
        result = {
            "price": round(mid, 4),
            "bid": float(data.get("bp", 0)),
            "ask": float(data.get("ap", 0)),
            "bid_size": data.get("bs", 0),
            "ask_size": data.get("as", 0),
            "source": "alpaca",
            "delay": "IEX real-time",
        }
        _cache_set(cache_key, result, "alpaca", ttl=60)
        return result
    except Exception:
        return None


def _alpaca_bars(symbol: str, timeframe: str = "15Min", limit: int = 200) -> pd.DataFrame:
    """Alpaca historical bars for US equities."""
    if not ALPACA_KEY_ID or not ALPACA_SECRET:
        return pd.DataFrame()
    if any(c in symbol for c in ["=X", "=F", "-USD", "^"]):
        return pd.DataFrame()

    try:
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
        headers = {
            "APCA-API-KEY-ID": ALPACA_KEY_ID,
            "APCA-API-SECRET-KEY": ALPACA_SECRET,
        }
        params = {"timeframe": timeframe, "limit": limit, "feed": "iex"}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()
        bars = r.json().get("bars", [])
        if not bars:
            return pd.DataFrame()
        df = pd.DataFrame(bars)
        df.index = pd.to_datetime(df["t"], utc=True)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        return df[["open", "high", "low", "close", "volume"]]
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# SMART ROUTER — Routes to best source per asset class
# ══════════════════════════════════════════════════════════════════════════════

def _classify_symbol(symbol: str) -> str:
    """Classify a Yahoo-format symbol into an asset class."""
    if symbol.endswith("=X"):
        return "forex"
    if symbol.startswith("^"):
        return "index"
    if symbol.endswith("-USD"):
        return "crypto"
    if symbol.endswith("=F"):
        return "commodity"
    return "equity"


# Source priority per asset class
# Forex/Crypto: Yahoo is real-time and free → primary
# Equities: Yahoo + Alpaca (IEX) + Alpha Vantage + FMP for consensus
# Indices: Yahoo + FMP
# Commodities: Yahoo primary
_SOURCE_PRIORITY = {
    "forex":     ["yahoo"],
    "crypto":    ["yahoo"],
    "equity":    ["yahoo", "alpaca", "fmp", "alpha_vantage"],
    "index":     ["yahoo", "fmp"],
    "commodity": ["yahoo", "fmp"],
}


def get_consensus_price(symbol: str) -> dict:
    """
    Fetch price from multiple sources and return consensus.
    Cross-references for reliability. Returns the best available price
    with metadata about which sources agreed.
    """
    asset_class = _classify_symbol(symbol)
    sources = _SOURCE_PRIORITY.get(asset_class, ["yahoo"])

    quotes = {}
    fetchers = {
        "yahoo": lambda: _yahoo_quote(symbol),
        "alpha_vantage": lambda: _av_quote(symbol.replace("=X", "").replace("^", "").replace("-USD", "")),
        "fmp": lambda: _fmp_quote(symbol.replace("=X", "").replace("^", "")),
        "alpaca": lambda: _alpaca_quote(symbol),
    }

    # Fetch from all applicable sources in parallel
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for src in sources:
            if src in fetchers:
                futures[pool.submit(fetchers[src])] = src
        for future in as_completed(futures):
            src = futures[future]
            try:
                result = future.result()
                if result and result.get("price", 0) > 0:
                    quotes[src] = result
            except Exception:
                pass

    if not quotes:
        return {"error": f"No price data for {symbol}", "sources_tried": sources}

    # Build consensus
    prices = {src: q["price"] for src, q in quotes.items()}
    avg_price = sum(prices.values()) / len(prices)
    primary = list(quotes.values())[0]  # first available

    # Check if sources agree (within 0.5% of each other)
    max_dev = 0
    if len(prices) > 1:
        max_dev = max(abs(p - avg_price) / avg_price * 100 for p in prices.values())

    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "price": primary["price"],
        "consensus_price": round(avg_price, 5),
        "price_by_source": prices,
        "sources_used": list(quotes.keys()),
        "sources_agree": max_dev < 0.5,
        "max_deviation_pct": round(max_dev, 3),
        "change_pct": primary.get("change_pct", 0),
        "delay": primary.get("delay", "unknown"),
        "primary_source": list(quotes.keys())[0],
        "timestamp": datetime.now().isoformat(),
        # Include any extra data (fundamentals from FMP, bid/ask from Alpaca)
        "extra": {
            src: {k: v for k, v in q.items() if k not in ("price", "source", "delay")}
            for src, q in quotes.items()
        },
    }


def get_multi_source_bars(symbol: str, interval: str = "15m", lookback: str = "5d") -> dict:
    """
    Fetch OHLCV bars from the best available source.
    Falls back through sources if primary fails.
    """
    asset_class = _classify_symbol(symbol)

    # Try Yahoo first (works for everything)
    df = _yahoo_intraday(symbol, interval, lookback)
    source_used = "yahoo_finance"

    # For equities, try Alpaca as fallback
    if df.empty and asset_class == "equity":
        tf_map = {"15m": "15Min", "1h": "1Hour", "1d": "1Day", "5m": "5Min"}
        alpaca_tf = tf_map.get(interval, "15Min")
        df = _alpaca_bars(symbol, alpaca_tf)
        source_used = "alpaca"

    # Alpha Vantage as last resort for equities
    if df.empty and asset_class == "equity":
        av_map = {"15m": "15min", "5m": "5min", "1h": "60min"}
        av_interval = av_map.get(interval, "15min")
        df = _av_intraday(symbol, av_interval)
        source_used = "alpha_vantage"

    if df.empty:
        return {"symbol": symbol, "bars": [], "source": "none", "error": "No data from any source"}

    return {
        "symbol": symbol,
        "source": source_used,
        "bars_count": len(df),
        "interval": interval,
        "first": df.index[0].isoformat() if len(df) > 0 else None,
        "last": df.index[-1].isoformat() if len(df) > 0 else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# DATA SOURCES STATUS — for the dashboard
# ══════════════════════════════════════════════════════════════════════════════

def get_sources_status() -> dict:
    """Return status of all data sources (configured, rate limits, etc.)."""
    today = datetime.now().strftime("%Y-%m-%d")
    av_calls = 0
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            row = conn.execute(
                "SELECT calls_today FROM rate_tracker WHERE source='alpha_vantage' AND last_reset=?",
                (today,),
            ).fetchone()
            if row:
                av_calls = row[0]
    except Exception:
        pass

    return {
        "sources": [
            {
                "name": "Yahoo Finance",
                "id": "yahoo",
                "status": "active",
                "configured": True,
                "rate_limit": "unlimited",
                "delay": "Real-time (FX/Crypto) · ≤15min (Equities/Indices)",
                "covers": ["forex", "crypto", "indices", "commodities", "equities"],
                "notes": "Primary data source — no API key needed",
            },
            {
                "name": "Alpha Vantage",
                "id": "alpha_vantage",
                "status": "active" if ALPHA_VANTAGE_KEY else "unconfigured",
                "configured": bool(ALPHA_VANTAGE_KEY),
                "rate_limit": f"{av_calls}/25 calls used today",
                "calls_remaining": 25 - av_calls,
                "delay": "≤15min (equities) · Real-time varies",
                "covers": ["equities", "forex", "crypto"],
                "notes": "25 free requests/day — cached aggressively in SQLite",
            },
            {
                "name": "Financial Modeling Prep",
                "id": "fmp",
                "status": "active" if FMP_KEY else "unconfigured",
                "configured": bool(FMP_KEY),
                "rate_limit": "250 req/day (free tier)",
                "delay": "≤15min delayed",
                "covers": ["equities", "forex", "crypto", "fundamentals"],
                "notes": "Fundamentals (P/E, EPS, balance sheets) + price data",
            },
            {
                "name": "Alpaca Markets",
                "id": "alpaca",
                "status": "active" if ALPACA_KEY_ID else "unconfigured",
                "configured": bool(ALPACA_KEY_ID),
                "rate_limit": "200 req/min",
                "delay": "IEX real-time (free) or 15min SIP",
                "covers": ["us_equities"],
                "notes": "Paper trading account — institutional-grade WebSocket + REST",
            },
            {
                "name": "TradingView MCP",
                "id": "tradingview_mcp",
                "status": "active",
                "configured": True,
                "rate_limit": "unlimited",
                "delay": "Real-time (FX/Crypto) · 15min (equities on free tier)",
                "covers": ["technicals", "sentiment", "news", "backtesting"],
                "notes": "30+ indicators, sentiment, news, backtesting via MCP bridge",
            },
        ],
        "timestamp": datetime.now().isoformat(),
        "total_active": sum(1 for s in [True, bool(ALPHA_VANTAGE_KEY), bool(FMP_KEY), bool(ALPACA_KEY_ID), True] if s),
        "regulatory_note": "Data delayed ≤15 minutes is reclassified as freely distributable per exchange regulations.",
    }
