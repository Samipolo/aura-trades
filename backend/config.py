"""
AURA TRADES - Configuration
All CFD trading pairs and system settings
"""

# Forex Pairs (Major, Minor, Exotic)
FOREX_PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
    "NZDUSD=X", "USDCAD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
    "AUDJPY=X", "EURAUD=X", "EURNZD=X", "GBPAUD=X", "GBPNZD=X",
    "AUDNZD=X", "AUDCAD=X", "NZDJPY=X", "CADJPY=X", "CHFJPY=X",
]

# Indices CFDs
INDICES = [
    "^GSPC",    # S&P 500
    "^DJI",     # Dow Jones
    "^IXIC",    # NASDAQ
    "^FTSE",    # FTSE 100
    "^GDAXI",   # DAX 40
    "^FCHI",    # CAC 40
    "^N225",    # Nikkei 225
    "^HSI",     # Hang Seng
    "^STOXX50E", # Euro Stoxx 50
    "^RUT",     # Russell 2000
]

# Commodities CFDs
COMMODITIES = [
    "GC=F",     # Gold
    "SI=F",     # Silver
    "CL=F",     # Crude Oil WTI
    "BZ=F",     # Brent Crude
    "NG=F",     # Natural Gas
    "HG=F",     # Copper
    "PL=F",     # Platinum
]

# Crypto CFDs
CRYPTO = [
    "BTC-USD",  # Bitcoin
    "ETH-USD",  # Ethereum
]

# All instruments combined
ALL_INSTRUMENTS = FOREX_PAIRS + INDICES + COMMODITIES + CRYPTO

# Display names mapping
INSTRUMENT_NAMES = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "NZDUSD=X": "NZD/USD",
    "USDCAD=X": "USD/CAD", "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "AUDJPY=X": "AUD/JPY", "EURAUD=X": "EUR/AUD",
    "EURNZD=X": "EUR/NZD", "GBPAUD=X": "GBP/AUD", "GBPNZD=X": "GBP/NZD",
    "AUDNZD=X": "AUD/NZD", "AUDCAD=X": "AUD/CAD", "NZDJPY=X": "NZD/JPY",
    "CADJPY=X": "CAD/JPY", "CHFJPY=X": "CHF/JPY",
    "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ",
    "^FTSE": "FTSE 100", "^GDAXI": "DAX 40", "^FCHI": "CAC 40",
    "^N225": "Nikkei 225", "^HSI": "Hang Seng", "^STOXX50E": "Euro Stoxx 50",
    "^RUT": "Russell 2000",
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil WTI",
    "BZ=F": "Brent Crude", "NG=F": "Natural Gas", "HG=F": "Copper",
    "PL=F": "Platinum",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
}

# Asset class mapping
ASSET_CLASSES = {
    "forex": FOREX_PAIRS,
    "indices": INDICES,
    "commodities": COMMODITIES,
    "crypto": CRYPTO,
}

# Trading session times (UTC)
SESSIONS = {
    "asian": {"start": "00:00", "end": "09:00"},
    "london": {"start": "07:00", "end": "16:00"},
    "new_york": {"start": "12:00", "end": "21:00"},
}

# Indicator Settings
INDICATOR_CONFIG = {
    "ema_fast": 50,
    "ema_slow": 200,
    "bb_period": 50,
    "bb_std": 2.5,
    "timeframe": "15m",
    "risk_reward_ratio": 2.0,
    "atr_period": 14,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
}

# Data fetch settings
DATA_CONFIG = {
    "lookback_15m": "60d",      # 60 days of 15m data
    "lookback_1h": "730d",      # 2 years of hourly data
    "lookback_1d": "365d",      # 1 year of daily data
}
