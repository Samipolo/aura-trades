"""
AURA TRADES — MT5 Bridge
Connects AURA TRADES to MetaTrader 5 for:
  1) Real-time OHLCV chart data (no delay)
  2) One-click trade execution from AI signals
"""

import MetaTrader5 as mt5
import pandas as pd
import time as _time
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# MT5 CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════════
# If MT5_LOGIN is set in .env, we will enforce login to that account.
# Otherwise, we will just use whatever account is currently active in the terminal.
MT5_LOGIN = os.getenv("MT5_LOGIN")
if MT5_LOGIN:
    MT5_LOGIN = int(MT5_LOGIN)
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# Ordered list of terminal paths to try — Deriv SVG uses a generic MT5 install
_MT5_PATHS = [
    os.getenv("MT5_PATH", ""),  # user-specified first
    r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\FTMO MetaTrader 5\terminal64.exe",
    r"C:\Program Files\FundedNext MT5 Terminal\terminal64.exe",
    r"C:\Program Files\FBS MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
]
# Filter out empty/non-existent paths, de-duplicate, keep first valid
MT5_PATH = next((p for p in _MT5_PATHS if p and os.path.exists(p)), None)
print(f"[MT5 Bridge] Using terminal: {MT5_PATH}")

# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL MAPPING: Yahoo Finance (AURA) → MT5
# ═══════════════════════════════════════════════════════════════════════════════
YAHOO_TO_MT5 = {
    # Forex
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "USDJPY=X": "USDJPY",
    "USDCHF=X": "USDCHF",
    "AUDUSD=X": "AUDUSD",
    "NZDUSD=X": "NZDUSD",
    "USDCAD=X": "USDCAD",
    "EURGBP=X": "EURGBP",
    "EURJPY=X": "EURJPY",
    "GBPJPY=X": "GBPJPY",
    "AUDJPY=X": "AUDJPY",
    "EURAUD=X": "EURAUD",
    "EURNZD=X": "EURNZD",
    "GBPAUD=X": "GBPAUD",
    "GBPNZD=X": "GBPNZD",
    "AUDNZD=X": "AUDNZD",
    "AUDCAD=X": "AUDCAD",
    "NZDJPY=X": "NZDJPY",
    "CADJPY=X": "CADJPY",
    "CHFJPY=X": "CHFJPY",
    # Indices — Deriv SVG exact symbol names
    "^GSPC":     "SPX500",    # S&P 500
    "^DJI":      "DJI30",     # Dow Jones 30
    "^IXIC":     "NDX100",    # NASDAQ 100
    "^FTSE":     "FTSE100",   # FTSE 100
    "^GDAXI":    "GER40",     # DAX 40 (Deriv name)
    "^FCHI":     "FRA40",     # CAC 40
    "^N225":     "JP225",     # Nikkei 225
    "^HSI":      "HK50",      # Hang Seng
    "^STOXX50E": "STOXX50",  # Euro Stoxx 50
    "^RUT":      "US2000",    # Russell 2000
    # Commodities — Deriv SVG exact symbol names
    "GC=F":      "XAUUSD",   # Gold
    "SI=F":      "XAGUSD",   # Silver
    "CL=F":      "USOIL",    # WTI Crude Oil (Deriv name)
    "BZ=F":      "UKOIL",    # Brent Crude Oil (Deriv name)
    "NG=F":      "NATGAS",   # Natural Gas
    "HG=F":      "COPPER",   # Copper
    "PL=F":      "PLATINUM", # Platinum
    # Crypto — Deriv SVG exact symbol names
    "BTC-USD":   "BTCUSD",
    "ETH-USD":   "ETHUSD",
}

# Reverse mapping MT5 → Yahoo
MT5_TO_YAHOO = {v: k for k, v in YAHOO_TO_MT5.items()}

# Track which symbols we've already selected in Market Watch
_selected_symbols = set()


def _convert_symbol(yahoo_symbol: str) -> str:
    """Convert a Yahoo Finance symbol to its MT5 equivalent"""
    return YAHOO_TO_MT5.get(yahoo_symbol, yahoo_symbol)


def ensure_initialized() -> bool:
    """Ensure MT5 is connected and logged in. Tries all known terminal paths."""
    # Try initializing with the located path first, then fallback list
    paths_to_try = [MT5_PATH] + [p for p in _MT5_PATHS if p and p != MT5_PATH and os.path.exists(p)]

    initialized = False
    for path in paths_to_try:
        if not path:
            continue
        if mt5.initialize(path=path):
            initialized = True
            break
        else:
            print(f"[MT5 Bridge] Initialize failed for {path}: {mt5.last_error()}")

    if not initialized:
        # Last resort: try without specifying a path (attaches to already-running terminal)
        if mt5.initialize():
            initialized = True
            print("[MT5 Bridge] Connected to already-running MT5 terminal (no path)")
        else:
            print(f"[MT5 Bridge] All initialization attempts failed: {mt5.last_error()}")
            return False

    # If no specific login is required in .env, we assume the user is manually
    # logged into the terminal with their preferred broker account.
    if not MT5_LOGIN:
        return True

    # Check if already logged in to the right account
    acct = mt5.account_info()
    if acct and acct.login == MT5_LOGIN:
        return True

    if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"[MT5 Bridge] Login failed: {mt5.last_error()}")
        return False

    return True


def _select_symbol(mt5_symbol: str) -> bool:
    """Select symbol in Market Watch (only once per session)"""
    if mt5_symbol in _selected_symbols:
        return True
    if mt5.symbol_select(mt5_symbol, True):
        _selected_symbols.add(mt5_symbol)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# CHART DATA — Real-time OHLCV from MT5
# ═══════════════════════════════════════════════════════════════════════════════

def get_chart_data(yahoo_symbol: str, timeframe=None, num_bars: int = 500):
    """
    Fetch real-time OHLCV data from MT5.
    Accepts Yahoo-format symbol (e.g. 'GBPUSD=X') — auto-converts to MT5 format.
    Returns a DataFrame with columns: time, open, high, low, close, tick_volume
    """
    if timeframe is None:
        timeframe = mt5.TIMEFRAME_M15

    if not ensure_initialized():
        return None

    mt5_symbol = _convert_symbol(yahoo_symbol)

    if not _select_symbol(mt5_symbol):
        print(f"[MT5 Bridge] Symbol {mt5_symbol} (from {yahoo_symbol}) not found in MT5")
        return None

    # Brief wait on first select so ticks arrive
    if mt5_symbol not in _selected_symbols:
        _time.sleep(0.5)

    rates = mt5.copy_rates_from_pos(mt5_symbol, timeframe, 0, num_bars)
    if rates is None or len(rates) == 0:
        print(f"[MT5 Bridge] No rate data for {mt5_symbol}")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


def get_current_price(yahoo_symbol: str) -> dict:
    """Get the live bid/ask for a symbol"""
    if not ensure_initialized():
        return None

    mt5_symbol = _convert_symbol(yahoo_symbol)
    _select_symbol(mt5_symbol)

    tick = mt5.symbol_info_tick(mt5_symbol)
    if not tick or tick.bid == 0:
        return None

    return {"bid": tick.bid, "ask": tick.ask, "last": tick.last, "time": tick.time}


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE EXECUTION — Place live orders on MT5
# ═══════════════════════════════════════════════════════════════════════════════

def place_trade(yahoo_symbol: str, direction: str, lot_size: float = 1.0,
                sl: float = 0, tp: float = 0) -> dict:
    """
    Place a trade on MT5.
    Accepts Yahoo-format symbol — auto-converts.
    direction: 'LONG' or 'SHORT'
    """
    if not ensure_initialized():
        return {"success": False, "error": "Could not connect to MT5"}

    mt5_symbol = _convert_symbol(yahoo_symbol)

    if not _select_symbol(mt5_symbol):
        return {"success": False, "error": f"Symbol {mt5_symbol} not available on MT5"}

    # Wait briefly for tick data
    _time.sleep(0.3)
    tick = mt5.symbol_info_tick(mt5_symbol)
    if not tick or tick.bid == 0:
        return {"success": False, "error": f"No price data for {mt5_symbol}"}

    # Check if algo trading is enabled
    term_info = mt5.terminal_info()
    if not term_info.trade_allowed:
        return {"success": False, "error": "Algo trading disabled in MT5. Enable it in Tools > Options > Expert Advisors"}

    is_buy = direction.upper() == "LONG"
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    price = tick.ask if is_buy else tick.bid

    # --- Dynamic Lot Size Calculation ---
    target_risk_usd = 10.0
    symbol_info = mt5.symbol_info(mt5_symbol)
    
    if not symbol_info:
        return {"success": False, "error": f"Could not get symbol info for {mt5_symbol}"}

    if not sl or sl <= 0:
        error_msg = "No valid Stop Loss provided. Cannot calculate risk. Trade aborted to prevent >$12 risk."
        print(f"[MT5 Bridge] ERROR: {error_msg}")
        return {"success": False, "error": error_msg}

    price_diff = abs(price - sl)
    tick_size = symbol_info.trade_tick_size
    
    # Use tick_value_loss if available, else tick_value
    tick_value = getattr(symbol_info, 'trade_tick_value_loss', 0)
    if not tick_value or tick_value <= 0:
        tick_value = getattr(symbol_info, 'trade_tick_value', 0)
        
    if price_diff <= 0 or tick_size <= 0 or tick_value <= 0:
        error_msg = f"Invalid tick metrics for {mt5_symbol}. Diff: {price_diff}, TickSize: {tick_size}, TickValue: {tick_value}"
        print(f"[MT5 Bridge] ERROR: {error_msg}")
        return {"success": False, "error": "Invalid tick size or value. Cannot calculate risk."}

    points = price_diff / tick_size
    raw_lot = target_risk_usd / (points * tick_value)
    
    # Normalize to volume step
    step = symbol_info.volume_step
    lot_size = round(raw_lot / step) * step
    
    # Bound within min/max limits
    lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
    
    # --- Hard Limit Safety Check ---
    estimated_risk = lot_size * points * tick_value
    if estimated_risk > 12.0:
        # Try adjusting lot size down to meet the < $12 limit
        while estimated_risk > 12.0 and lot_size > symbol_info.volume_min:
            lot_size = round((lot_size - step) / step) * step # Avoid floating point drift
            estimated_risk = lot_size * points * tick_value
            
        if estimated_risk > 12.0:
            error_msg = f"Calculated risk (${estimated_risk:.2f} for {lot_size} lot) exceeds $12 limit. Trade aborted."
            print(f"[MT5 Bridge] ERROR: {error_msg}")
            return {"success": False, "error": error_msg}

    # Ensure final lot size is valid
    if lot_size < symbol_info.volume_min:
        return {"success": False, "error": "Calculated lot size is below minimum allowed volume for symbol."}

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": mt5_symbol,
        "volume": float(lot_size),
        "type": order_type,
        "price": price,
        "sl": float(sl) if sl and sl > 0 else 0.0,
        "tp": float(tp) if tp and tp > 0 else 0.0,
        "deviation": 20,
        "magic": 777777,
        "comment": "AURA AI TRADE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    print(f"[MT5 Bridge] Sending order: {mt5_symbol} {direction} {lot_size} lots @ {price} | Est. Risk: ${estimated_risk:.2f}")
    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        error_msg = f"Order failed. Code: {result.retcode}, Reason: {result.comment}"
        print(f"[MT5 Bridge] {error_msg}")
        return {"success": False, "error": error_msg}

    print(f"[MT5 Bridge] ✅ Order filled: ticket={result.deal}, price={result.price}")
    return {
        "success": True,
        "deal_ticket": result.deal,
        "price": result.price,
        "volume": result.volume,
        "symbol": mt5_symbol,
    }


def shutdown():
    mt5.shutdown()
