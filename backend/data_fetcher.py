"""
AURA TRADES - Real Data Fetcher
Fetches 100% real market data from Yahoo Finance (direct API, no yfinance dependency issues)
"""

import requests as _requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time as _time
import pytz
from config import ALL_INSTRUMENTS, DATA_CONFIG, INSTRUMENT_NAMES

_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

_PERIOD_MAP = {
    "60d": 5184000,
    "30d": 2592000,
    "7d": 604800,
    "5d": 432000,
    "1d": 86400,
}

_INTERVAL_SECONDS = {
    "15m": 900,
    "1h": 3600,
    "1d": 86400,
}


def _yahoo_chart(symbol: str, interval: str = "15m", range_str: str = "60d") -> pd.DataFrame:
    """Fetch OHLCV data directly from Yahoo Finance chart API (bypass yfinance bugs)"""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": interval, "range": range_str, "includePrePost": "false"}
    try:
        r = _requests.get(url, params=params, headers=_YAHOO_HEADERS, timeout=30)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return pd.DataFrame()
        result = result[0]
        timestamps = result.get("timestamp")
        if not timestamps:
            return pd.DataFrame()
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        o = quote.get("open", [])
        h = quote.get("high", [])
        l = quote.get("low", [])
        c = quote.get("close", [])
        v = quote.get("volume", [])

        df = pd.DataFrame({
            "open": o, "high": h, "low": l, "close": c, "volume": v
        }, index=pd.to_datetime(timestamps, unit="s", utc=True))
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = df["volume"].fillna(0).astype(int)
        return df
    except Exception as e:
        print(f"[DataFetcher] Yahoo API error for {symbol} ({interval}): {e}")
        return pd.DataFrame()


class DataFetcher:
    """Fetches real market data from Yahoo Finance (direct API, free, no key needed)"""

    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(minutes=5)

    def fetch_15m_data(self, symbol: str, period: str = None) -> pd.DataFrame:
        """Fetch 15-minute candle data"""
        cache_key = f"{symbol}_15m"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            df = _yahoo_chart(symbol, interval="15m", range_str="60d")
            if df.empty:
                return pd.DataFrame()
            self.cache[cache_key] = df
            self.cache_expiry[cache_key] = datetime.now()
            return df
        except Exception as e:
            print(f"Error fetching 15m data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_1h_data(self, symbol: str) -> pd.DataFrame:
        """Fetch 1-hour candle data for higher timeframe context"""
        cache_key = f"{symbol}_1h"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            df = _yahoo_chart(symbol, interval="1h", range_str="60d")
            if df.empty:
                return pd.DataFrame()
            self.cache[cache_key] = df
            self.cache_expiry[cache_key] = datetime.now()
            return df
        except Exception as e:
            print(f"Error fetching 1h data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_daily_data(self, symbol: str) -> pd.DataFrame:
        """Fetch daily candle data for swing context"""
        cache_key = f"{symbol}_1d"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            df = _yahoo_chart(symbol, interval="1d", range_str="1y")
            if df.empty:
                return pd.DataFrame()
            self.cache[cache_key] = df
            self.cache_expiry[cache_key] = datetime.now()
            return df
        except Exception as e:
            print(f"Error fetching daily data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_all_instruments(self) -> dict:
        """Fetch 15m data for all configured instruments"""
        all_data = {}
        for symbol in ALL_INSTRUMENTS:
            df = self.fetch_15m_data(symbol)
            if not df.empty:
                all_data[symbol] = df
        return all_data

    def get_current_price(self, symbol: str) -> float:
        """Get the latest available price"""
        df = self.fetch_15m_data(symbol)
        if not df.empty:
            return float(df["close"].iloc[-1])
        return 0.0

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache or key not in self.cache_expiry:
            return False
        elapsed = datetime.now() - self.cache_expiry[key]
        return elapsed < self.cache_duration
