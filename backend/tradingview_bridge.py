"""
AURA TRADES — TradingView MCP Bridge
Direct Python integration with the tradingview-mcp-server package.
Bypasses MCP protocol overhead by calling service functions directly.
"""

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── TradingView MCP core imports ──────────────────────────────────────────────
from tradingview_mcp.core.services.screener_service import (
    analyze_coin,
    run_multi_timeframe_analysis,
)
from tradingview_mcp.core.services.multi_agent_service import run_multi_agent_analysis
from tradingview_mcp.core.services.sentiment_service import analyze_sentiment
from tradingview_mcp.core.services.news_service import fetch_news_summary
from tradingview_mcp.core.services.yahoo_finance_service import (
    get_price as yahoo_get_price,
    get_market_snapshot as yahoo_market_snapshot,
)
from tradingview_mcp.core.services.backtest_service import (
    run_backtest,
    compare_strategies as compare_all_strategies,
    walk_forward_backtest,
)

# ── Symbol Mapping: AURA Yahoo symbols → TradingView format ─────────────────

# Map Yahoo Finance symbols to TradingView exchange:symbol pairs
_TV_SYMBOL_MAP = {
    # Forex
    "EURUSD=X": ("FX_IDC", "EURUSD"),
    "GBPUSD=X": ("FX_IDC", "GBPUSD"),
    "USDJPY=X": ("FX_IDC", "USDJPY"),
    "USDCHF=X": ("FX_IDC", "USDCHF"),
    "AUDUSD=X": ("FX_IDC", "AUDUSD"),
    "NZDUSD=X": ("FX_IDC", "NZDUSD"),
    "USDCAD=X": ("FX_IDC", "USDCAD"),
    "EURGBP=X": ("FX_IDC", "EURGBP"),
    "EURJPY=X": ("FX_IDC", "EURJPY"),
    "GBPJPY=X": ("FX_IDC", "GBPJPY"),
    "AUDJPY=X": ("FX_IDC", "AUDJPY"),
    "EURAUD=X": ("FX_IDC", "EURAUD"),
    "EURNZD=X": ("FX_IDC", "EURNZD"),
    "GBPAUD=X": ("FX_IDC", "GBPAUD"),
    "GBPNZD=X": ("FX_IDC", "GBPNZD"),
    "AUDNZD=X": ("FX_IDC", "AUDNZD"),
    "AUDCAD=X": ("FX_IDC", "AUDCAD"),
    "NZDJPY=X": ("FX_IDC", "NZDJPY"),
    "CADJPY=X": ("FX_IDC", "CADJPY"),
    "CHFJPY=X": ("FX_IDC", "CHFJPY"),
    # Indices
    "^GSPC": ("SP", "SPX"),
    "^DJI": ("DJ", "DJI"),
    "^IXIC": ("NASDAQ", "IXIC"),
    "^FTSE": ("FTSE", "UKX"),
    "^GDAXI": ("XETR", "DAX"),
    "^FCHI": ("EURONEXT", "PX1"),
    "^N225": ("TVC", "NI225"),
    "^HSI": ("TVC", "HSI"),
    "^STOXX50E": ("TVC", "SX5E"),
    "^RUT": ("TVC", "RUT"),
    # Commodities
    "GC=F": ("TVC", "GOLD"),
    "SI=F": ("TVC", "SILVER"),
    "CL=F": ("TVC", "USOIL"),
    "BZ=F": ("TVC", "UKOIL"),
    "NG=F": ("NYMEX", "NG1!"),
    "HG=F": ("COMEX", "HG1!"),
    "PL=F": ("NYMEX", "PL1!"),
    # Crypto
    "BTC-USD": ("BINANCE", "BTCUSDT"),
    "ETH-USD": ("BINANCE", "ETHUSDT"),
}


def _get_tv_params(yahoo_symbol: str):
    """Convert Yahoo symbol → (exchange, tv_symbol) for TradingView"""
    if yahoo_symbol in _TV_SYMBOL_MAP:
        return _TV_SYMBOL_MAP[yahoo_symbol]
    # Fallback: try to build a sensible default
    if yahoo_symbol.endswith("=X"):
        pair = yahoo_symbol.replace("=X", "")
        return ("FX_IDC", pair)
    if yahoo_symbol.startswith("^"):
        return ("TVC", yahoo_symbol[1:])
    if yahoo_symbol.endswith("-USD"):
        return ("BINANCE", yahoo_symbol.replace("-USD", "USDT"))
    return ("NASDAQ", yahoo_symbol)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — called by main.py endpoints
# ══════════════════════════════════════════════════════════════════════════════


def tv_coin_analysis(yahoo_symbol: str, timeframe: str = "15m") -> dict:
    """Get TradingView technical analysis for a symbol (30+ indicators)."""
    try:
        exchange, tv_sym = _get_tv_params(yahoo_symbol)
        result = analyze_coin(tv_sym, exchange, timeframe)
        if isinstance(result, dict):
            result["_source"] = "tradingview_mcp"
            result["_yahoo_symbol"] = yahoo_symbol
        return result
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e), "_yahoo_symbol": yahoo_symbol}


def tv_multi_agent(yahoo_symbol: str, timeframe: str = "15m") -> dict:
    """Run 3-agent debate (Technical, Sentiment, Risk) for a symbol."""
    try:
        exchange, tv_sym = _get_tv_params(yahoo_symbol)
        full_symbol = f"{exchange}:{tv_sym}"
        return run_multi_agent_analysis(full_symbol, exchange, timeframe)
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_sentiment(symbol_keyword: str, category: str = "all") -> dict:
    """Reddit sentiment analysis for a symbol keyword."""
    try:
        # Strip Yahoo suffixes for reddit search
        clean = symbol_keyword.replace("=X", "").replace("^", "").replace("-USD", "").replace("=F", "")
        return analyze_sentiment(clean, category, 20)
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_news(symbol_keyword: str = None, category: str = "all") -> dict:
    """Live financial news from RSS feeds (Reuters, CoinDesk, etc.)."""
    try:
        clean = None
        if symbol_keyword:
            clean = symbol_keyword.replace("=X", "").replace("^", "").replace("-USD", "").replace("=F", "")
        return fetch_news_summary(clean, category, 10)
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_yahoo_price(yahoo_symbol: str) -> dict:
    """Real-time price from Yahoo Finance via MCP."""
    try:
        return yahoo_get_price(yahoo_symbol)
    except Exception as e:
        return {"error": str(e)}


def tv_market_snapshot() -> dict:
    """Global market snapshot: indices, crypto, FX, ETFs."""
    try:
        return yahoo_market_snapshot()
    except Exception as e:
        return {"error": str(e)}


def tv_backtest(yahoo_symbol: str, strategy: str = "supertrend",
                period: str = "1y", interval: str = "1d",
                include_trade_log: bool = False,
                include_equity_curve: bool = False) -> dict:
    """Backtest a strategy (rsi, bollinger, macd, ema_cross, supertrend, donchian)."""
    try:
        return run_backtest(
            yahoo_symbol, strategy, period,
            initial_capital=10000.0,
            commission_pct=0.1,
            slippage_pct=0.05,
            interval=interval,
            include_trade_log=include_trade_log,
            include_equity_curve=include_equity_curve,
        )
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_compare_strategies(yahoo_symbol: str, period: str = "1y",
                          interval: str = "1d") -> dict:
    """Run all 6 strategies and return ranked leaderboard."""
    try:
        return compare_all_strategies(yahoo_symbol, period, 10000.0, interval=interval)
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_walk_forward(yahoo_symbol: str, strategy: str = "supertrend",
                    period: str = "2y", interval: str = "1d") -> dict:
    """Walk-forward backtest to detect overfitting."""
    try:
        return walk_forward_backtest(
            yahoo_symbol, strategy, period,
            initial_capital=10000.0,
            commission_pct=0.1,
            slippage_pct=0.05,
            n_splits=3,
            train_ratio=0.7,
            interval=interval,
        )
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def tv_combined_analysis(yahoo_symbol: str, timeframe: str = "15m") -> dict:
    """
    POWER TOOL: TradingView technicals + Reddit sentiment + News → confluence decision.
    This is the flagship MCP analysis endpoint.
    """
    try:
        exchange, tv_sym = _get_tv_params(yahoo_symbol)
        clean_keyword = yahoo_symbol.replace("=X", "").replace("^", "").replace("-USD", "").replace("=F", "")

        # Run all 3 in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(analyze_coin, tv_sym, exchange, timeframe): "tech",
                pool.submit(analyze_sentiment, clean_keyword, "all", 15): "sentiment",
                pool.submit(fetch_news_summary, clean_keyword, "all", 5): "news",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = {"error": str(e)}

        tech = results.get("tech", {})
        sentiment = results.get("sentiment", {})
        news = results.get("news", {})

        # Build confluence
        tech_momentum = ""
        if isinstance(tech, dict):
            tech_momentum = tech.get("market_sentiment", {}).get("momentum", "")
        tech_bullish = tech_momentum == "Bullish"
        sent_score = sentiment.get("sentiment_score", 0) if isinstance(sentiment, dict) else 0
        sent_bullish = sent_score > 0.1
        signals_agree = tech_bullish == sent_bullish

        tech_signal = "N/A"
        if isinstance(tech, dict):
            tech_signal = tech.get("market_sentiment", {}).get("buy_sell_signal", "N/A")

        return {
            "symbol": yahoo_symbol,
            "exchange": exchange,
            "tv_symbol": tv_sym,
            "timeframe": timeframe,
            "technical": tech,
            "sentiment": sentiment,
            "news": {
                "count": news.get("count", 0) if isinstance(news, dict) else 0,
                "latest": (news.get("items", []) if isinstance(news, dict) else [])[:3],
            },
            "confluence": {
                "signals_agree": signals_agree,
                "confidence": "HIGH" if signals_agree else "MIXED",
                "tech_signal": tech_signal,
                "sentiment_label": sentiment.get("sentiment_label", "Neutral") if isinstance(sentiment, dict) else "N/A",
                "sentiment_score": round(sent_score, 3),
            },
            "_source": "tradingview_mcp_combined",
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
