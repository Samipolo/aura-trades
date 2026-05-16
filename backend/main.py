"""
AURA TRADES V2 - Main FastAPI Application (5x Enhanced)
Self-decision AI day trading system with:
- Advanced Quantitative Models (Hurst, Kalman, Monte Carlo, Z-score)
- Deep Order Flow Analysis (Delta, Wyckoff, Stop Hunts, Absorption)
- Multi-Timeframe Alignment (15M/1H/4H/Daily)
- Pattern Recognition (Candles, Divergences, Chart Patterns)
- Advanced Risk Management (Kelly, Dynamic Sizing)
- Enhanced Correlation (Currency Strength, Cointegration, Lead-Lag)
"""

import traceback
import asyncio
import json
import threading
import time as _time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from datetime import datetime

from data_fetcher import DataFetcher
from indicators import IndicatorEngine
from market_structure import MarketStructureAnalyzer
from correlation_v2 import CorrelationAnalyzerV2
from advanced_quant import AdvancedQuantEngine
from orderflow_engine import OrderFlowEngine
from multi_timeframe import MultiTimeframeEngine
from pattern_recognition import PatternRecognitionEngine
from risk_engine import RiskEngine
from signal_generator_v2 import SignalGeneratorV2, TradeRankerV2
from ict_engine import ICTEngine
from auction_market import AuctionMarketEngine
from session_engine import SessionAnalysisEngine
from fundamental_engine import FundamentalEngine
from institutional_engine import InstitutionalFlowEngine
from regime_engine import RegimeDetectionEngine
from macro_engine import MacroIntermarketEngine
from config import ALL_INSTRUMENTS, INSTRUMENT_NAMES, ASSET_CLASSES

# TradingView MCP Bridge — direct Python integration (no MCP overhead)
try:
    import tradingview_bridge as tv_bridge
    TV_MCP_AVAILABLE = True
    print("[AURA V2] TradingView MCP bridge loaded OK")
except ImportError as _tv_err:
    TV_MCP_AVAILABLE = False
    print(f"[AURA V2] TradingView MCP bridge unavailable: {_tv_err}")

# Trade Journal Engine
try:
    import trade_journal as journal
    JOURNAL_AVAILABLE = True
    print("[AURA V2] Trade Journal engine loaded OK")
except Exception as _j_err:
    JOURNAL_AVAILABLE = False
    journal = None
    print(f"[AURA V2] Trade Journal unavailable: {_j_err}")

# Multi-Source Data Aggregator — Yahoo + Alpha Vantage + FMP + Alpaca
try:
    import multi_source_fetcher as msf
    MULTI_SOURCE_AVAILABLE = True
    print("[AURA V2] Multi-source data aggregator loaded OK")
except ImportError as _ms_err:
    MULTI_SOURCE_AVAILABLE = False
    print(f"[AURA V2] Multi-source aggregator unavailable: {_ms_err}")

# MT5 Bridge
try:
    import mt5_bridge
    MT5_AVAILABLE = True
    print("[AURA V2] MT5 Bridge loaded OK")
except Exception as _mt5_err:
    MT5_AVAILABLE = False
    print(f"[AURA V2] MT5 Bridge unavailable: {_mt5_err}")

app = FastAPI(
    title="AURA TRADES V2 - AI Trading System",
    description="5x Enhanced self-decision day trading AI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize all engines
data_fetcher = DataFetcher()
indicator_engine = IndicatorEngine()
structure_analyzer = MarketStructureAnalyzer()
correlation_analyzer = CorrelationAnalyzerV2()
quant_engine = AdvancedQuantEngine()
orderflow_engine = OrderFlowEngine()
mtf_engine = MultiTimeframeEngine()
pattern_engine = PatternRecognitionEngine()
risk_engine = RiskEngine()
signal_generator = SignalGeneratorV2()
trade_ranker = TradeRankerV2()
ict_engine = ICTEngine()
amt_engine = AuctionMarketEngine()
session_engine = SessionAnalysisEngine()
fundamental_engine = FundamentalEngine()
institutional_engine = InstitutionalFlowEngine()
regime_engine = RegimeDetectionEngine()
macro_engine = MacroIntermarketEngine()

# Start journal auto-monitor (checks TP/SL on open trades every 30s)
if JOURNAL_AVAILABLE and journal:
    def _journal_price_fn(symbol):
        return data_fetcher.get_current_price(symbol)
    journal.start_monitor(_journal_price_fn)


@app.get("/")
async def root():
    return {
        "message": "AURA TRADES V2 - AI Trading System (5x Enhanced)",
        "version": "2.0.0",
        "engines": [
            "Technical Indicators", "Market Structure", "Order Flow",
            "Quantitative Models", "Multi-Timeframe", "Pattern Recognition",
            "Correlation Analysis", "Risk Management"
        ]
    }


def _fetch_one(symbol):
    """Fetch 15m + 1h + 4h data for a single instrument (runs in thread pool)"""
    try:
        df_15m = data_fetcher.fetch_15m_data(symbol)
        if df_15m.empty or len(df_15m) < 200:
            return symbol, None, None, None, None

        df_1h = data_fetcher.fetch_1h_data(symbol)
        df_4h = None
        # Build 4h from 1h if available
        if not df_1h.empty and len(df_1h) >= 50:
            try:
                df_4h = df_1h.resample('4h').agg({
                    'open': 'first', 'high': 'max', 'low': 'min',
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            except Exception:
                df_4h = None

        return symbol, df_15m, df_1h, df_4h, None
    except Exception as e:
        return symbol, None, None, None, f"Fetch: {symbol}: {str(e)[:50]}"


def _run_full_analysis():
    """Synchronous heavy analysis – called via asyncio.to_thread"""
    errors = []
    all_signals = []

    # ===== STEP 1: PARALLEL DATA FETCH (15m + 1H + 4H) =====
    print("[AURA V2] Fetching market data (15m + 1H + 4H parallel)...")
    all_data = {}  # 15m data
    all_1h = {}    # 1h data
    all_4h = {}    # 4h data
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one, sym): sym for sym in ALL_INSTRUMENTS}
        for future in as_completed(futures):
            sym, df_15m, df_1h, df_4h, err = future.result()
            if err:
                errors.append(err)
            elif df_15m is not None:
                all_data[sym] = df_15m
                if df_1h is not None and not df_1h.empty:
                    all_1h[sym] = df_1h
                if df_4h is not None and not df_4h.empty:
                    all_4h[sym] = df_4h

    if not all_data:
        return {"success": False, "detail": "No market data available"}

    print(f"[AURA V2] Loaded {len(all_data)} instruments (+ {len(all_1h)} 1H, {len(all_4h)} 4H)")

    # ===== STEP 2: CORRELATION & INTER-MARKET =====
    print("[AURA V2] Running enhanced correlation analysis...")
    correlation_data = correlation_analyzer.analyze(all_data)

    # ===== STEP 3: MACRO INTERMARKET (run once for all) =====
    print("[AURA V2] Running macro intermarket analysis...")
    macro_context = macro_engine.analyze("DX-Y.NYB", all_data)

    # ===== STEP 4: ANALYZE EACH INSTRUMENT (15 engines + HTF) =====
    print("[AURA V2] Running 15-engine institutional analysis...")
    for symbol, df_15m in all_data.items():
        try:
            indicator_data = indicator_engine.calculate_all(df_15m)
            if not indicator_data:
                continue

            structure_data = structure_analyzer.analyze(df_15m)
            if not structure_data:
                continue

            df_1h = all_1h.get(symbol)
            df_4h = all_4h.get(symbol)

            quant_data = quant_engine.analyze(df_15m)
            orderflow_data = orderflow_engine.analyze(df_15m)
            mtf_data = mtf_engine.analyze(df_15m)
            pattern_data = pattern_engine.analyze(df_15m)
            ict_data = ict_engine.analyze(df_15m, df_1h, df_4h)
            amt_data = amt_engine.analyze(df_15m, df_1h, df_4h)

            # NEW: Session, Fundamental, Institutional, Regime
            session_data = session_engine.analyze(df_15m)
            fundamental_data = fundamental_engine.analyze(symbol, df_15m)
            institutional_data = institutional_engine.analyze(df_15m, df_1h, df_4h)
            regime_data = regime_engine.analyze(df_15m, df_1h)

            # Per-symbol macro score
            symbol_macro = macro_engine.analyze(symbol, all_data)

            corr_score = correlation_analyzer.get_correlation_score(
                symbol, structure_data.get("bias", "neutral"), all_data
            )

            signal = signal_generator.generate_signal(
                symbol, indicator_data, structure_data, corr_score,
                quant_data, orderflow_data, mtf_data, pattern_data, all_data,
                ict_data=ict_data, amt_data=amt_data,
                session_data=session_data, fundamental_data=fundamental_data,
                institutional_data=institutional_data, regime_data=regime_data,
                macro_data=symbol_macro
            )

            if signal:
                risk_eval = risk_engine.evaluate_trade(
                    signal, quant_data, orderflow_data, mtf_data, pattern_data
                )
                signal["win_probability"] = risk_eval.get("win_probability", 50)
                signal["trade_quality"] = risk_eval.get("trade_quality", 50)
                signal["risk_grade"] = risk_eval.get("risk_grade", "C")
                signal["position_size_pct"] = risk_eval.get("position_size_pct", 1.0)
                signal["kelly_fraction"] = risk_eval.get("kelly_fraction", 0)
                signal["dynamic_rr"] = risk_eval.get("dynamic_rr", 2.0)
                signal["should_trade"] = risk_eval.get("should_trade", False)
                signal["warnings"] = risk_eval.get("warnings", [])
                signal["session_score"] = risk_eval.get("session_score", 50)
                signal["confluence_score"] = risk_eval.get("confluence_score", 0)

                # ICT & AMT summary
                signal["ict_bias"] = ict_data.get("bias", "neutral")
                signal["ict_score"] = ict_data.get("ict_score", 0)
                signal["kill_zone"] = ict_data.get("kill_zone", {}).get("session", "unknown")
                signal["po3_phase"] = ict_data.get("power_of_3", {}).get("phase", "unknown")
                signal["amt_bias"] = amt_data.get("bias", "neutral")
                signal["amt_score"] = amt_data.get("amt_score", 0)
                signal["day_type"] = amt_data.get("day_type", {}).get("type", "unknown")
                signal["value_area"] = amt_data.get("price_position", {}).get("zone", "unknown")

                # Session summary
                signal["london_ib_status"] = session_data.get("london_ib", {}).get("status", "unknown")
                signal["asian_breakout"] = session_data.get("asian_range", {}).get("breakout", "none")
                signal["session_bias"] = session_data.get("bias", "neutral")
                signal["current_session"] = session_data.get("current_session", {}).get("primary", "unknown")

                # Fundamental summary
                signal["fundamental_bias"] = fundamental_data.get("bias", "neutral")
                signal["fundamental_score"] = fundamental_data.get("score", 50)
                signal["event_risk"] = fundamental_data.get("event_risk", {}).get("risk_level", "low")
                signal["news_sentiment"] = fundamental_data.get("news_sentiment", {}).get("news_bias", "neutral")

                # Institutional summary
                signal["inst_bias"] = institutional_data.get("bias", "neutral")
                signal["inst_score"] = institutional_data.get("inst_score", 0)
                signal["smart_money"] = institutional_data.get("smart_money", {}).get("signal", "neutral")
                signal["inst_phase"] = institutional_data.get("accum_distrib", {}).get("phase", "neutral")

                # Regime summary
                signal["regime"] = regime_data.get("current_regime", {}).get("primary", "unknown")
                signal["regime_quality"] = regime_data.get("current_regime", {}).get("quality", "fair")
                signal["regime_tradeable"] = regime_data.get("tradeable", {}).get("tradeable", True)
                signal["optimal_strategy"] = regime_data.get("optimal_strategy", {}).get("strategy", "unknown")

                # Macro summary
                signal["macro_bias"] = symbol_macro.get("bias", "neutral")
                signal["risk_sentiment"] = symbol_macro.get("risk_sentiment", {}).get("sentiment", "neutral")

                # Apply regime confidence multiplier
                conf_mult = regime_data.get("tradeable", {}).get("confidence_multiplier", 1.0)
                signal["confidence"] = min(98, signal.get("confidence", 50) * conf_mult)

                # Apply event risk warning
                if fundamental_data.get("event_risk", {}).get("should_reduce_size"):
                    signal["warnings"] = signal.get("warnings", []) + ["High-impact event pending - reduce size"]
                    signal["position_size_pct"] = signal.get("position_size_pct", 1.0) * 0.5

                all_signals.append(signal)

        except Exception as e:
            errors.append(f"Analysis: {symbol}: {str(e)[:80]}")

    # ===== STEP 4: RANK =====
    print(f"[AURA V2] Ranking {len(all_signals)} signals...")
    ranked_signals = trade_ranker.rank_signals(all_signals)

    # ===== STEP 5: BUILD OVERVIEW =====
    market_overview = _build_market_overview(all_data, correlation_data)

    print(f"[AURA V2] Analysis complete: {len(ranked_signals)} trade ideas ranked")

    return {
        "success": True,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "total_instruments": len(all_data),
        "signals_generated": len(ranked_signals),
        "ranked_trades": ranked_signals,
        "correlation_data": {
            "dxy_bias": correlation_data.get("dxy_bias", {}),
            "signals": correlation_data.get("signals", [])[:10],
            "currency_strength": correlation_data.get("currency_strength", {}),
            "risk_sentiment": correlation_data.get("risk_sentiment", {}),
            "lead_lag": correlation_data.get("lead_lag", [])[:5],
            "cointegration": correlation_data.get("cointegration", []),
            "smart_money_flow": correlation_data.get("smart_money_flow", {}),
        },
        "market_overview": market_overview,
        "errors": errors[:10],
    }


# ── Analysis lock + cache: prevent stacking requests ──
_analysis_lock = threading.Lock()
_analysis_cache = {"result": None, "timestamp": 0}
_CACHE_TTL = 120  # seconds – serve cached result for 2 min


@app.get("/api/analyze")
async def analyze_all():
    """
    MAIN ENDPOINT: Full multi-engine analysis of all CFD pairs.
    Only one analysis runs at a time; others get cached / busy.
    """
    # Serve cached result if still fresh
    age = _time.time() - _analysis_cache["timestamp"]
    if _analysis_cache["result"] and age < _CACHE_TTL:
        return JSONResponse(content=_analysis_cache["result"])

    # If another analysis is already running, return cached or busy
    if not _analysis_lock.acquire(blocking=False):
        if _analysis_cache["result"]:
            return JSONResponse(content=_analysis_cache["result"])
        return JSONResponse(
            status_code=202,
            content={"success": False, "detail": "Analysis already in progress, please wait..."},
        )

    try:
        result = await asyncio.to_thread(_run_full_analysis)
        if not result.get("success"):
            raise HTTPException(status_code=503, detail=result.get("detail", "Analysis failed"))
        _analysis_cache["result"] = result
        _analysis_cache["timestamp"] = _time.time()
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        _analysis_lock.release()


def _run_single_analysis(symbol):
    """Synchronous single-instrument analysis"""
    df = data_fetcher.fetch_15m_data(symbol)
    if df.empty or len(df) < 200:
        return None, f"Insufficient data for {symbol}"

    indicator_data = indicator_engine.calculate_all(df)
    structure_data = structure_analyzer.analyze(df)
    quant_data = quant_engine.analyze(df)
    orderflow_data = orderflow_engine.analyze(df)
    mtf_data = mtf_engine.analyze(df)
    pattern_data = pattern_engine.analyze(df)

    all_data = {symbol: df}
    corr_score = correlation_analyzer.get_correlation_score(
        symbol, structure_data.get("bias", "neutral"), all_data
    )

    signal = signal_generator.generate_signal(
        symbol, indicator_data, structure_data, corr_score,
        quant_data, orderflow_data, mtf_data, pattern_data, all_data
    )

    if signal:
        risk_eval = risk_engine.evaluate_trade(signal, quant_data, orderflow_data, mtf_data, pattern_data)
        signal.update({
            "win_probability": risk_eval.get("win_probability", 50),
            "trade_quality": risk_eval.get("trade_quality", 50),
            "risk_grade": risk_eval.get("risk_grade", "C"),
            "warnings": risk_eval.get("warnings", []),
        })

    return {
        "success": True,
        "symbol": symbol,
        "display_name": INSTRUMENT_NAMES.get(symbol, symbol),
        "signal": signal,
        "quant": {
            "hurst": quant_data.get("hurst_exponent"),
            "kalman": quant_data.get("kalman"),
            "regime": quant_data.get("regime"),
            "z_score": quant_data.get("z_score"),
            "monte_carlo": quant_data.get("monte_carlo"),
            "volatility": quant_data.get("volatility_regime"),
            "momentum_quality": quant_data.get("momentum_quality"),
            "mean_reversion": quant_data.get("mean_reversion"),
        },
        "orderflow": {
            "delta": orderflow_data.get("delta"),
            "wyckoff": orderflow_data.get("wyckoff"),
            "stop_hunts": orderflow_data.get("stop_hunts"),
            "absorption": orderflow_data.get("absorption"),
            "institutional": orderflow_data.get("institutional_prints"),
            "trapped_traders": orderflow_data.get("trapped_traders"),
            "effort_result": orderflow_data.get("effort_result"),
        },
        "mtf": mtf_data,
        "patterns": pattern_data,
        "structure": {
            "bias": structure_data.get("bias"),
            "type": structure_data.get("structure", {}).get("type"),
            "order_blocks": len(structure_data.get("order_blocks", [])),
            "fvgs": len(structure_data.get("fair_value_gaps", [])),
        },
        "correlation_score": corr_score,
    }, None


@app.get("/api/analyze/{symbol}")
async def analyze_single(symbol: str):
    """Deep analysis of a single instrument"""
    try:
        result, err = await asyncio.to_thread(_run_single_analysis, symbol)
        if err:
            raise HTTPException(status_code=404, detail=err)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/instruments")
async def list_instruments():
    return {
        "instruments": [
            {"symbol": s, "name": INSTRUMENT_NAMES.get(s, s), "class": _get_asset_class(s)}
            for s in ALL_INSTRUMENTS
        ],
        "total": len(ALL_INSTRUMENTS)
    }


@app.get("/api/health")
async def health_check():
    data_sources = []
    if MULTI_SOURCE_AVAILABLE:
        try:
            st = msf.get_sources_status()
            data_sources = [s["name"] for s in st.get("sources", []) if s.get("configured")]
        except Exception:
            data_sources = ["Yahoo Finance"]
    else:
        data_sources = ["Yahoo Finance"]

    return {
        "status": "healthy",
        "version": "2.0.0",
        "engines": 10,
        "data_sources": data_sources,
        "data_sources_count": len(data_sources),
        "multi_source": MULTI_SOURCE_AVAILABLE,
        "tradingview_mcp": TV_MCP_AVAILABLE,
        "mt5_bridge": MT5_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }


_chart_cache = {}
_chart_cache_ts = {}
_CHART_CACHE_TTL = 15  # 15 seconds — near-real-time for MT5 live data


def _fetch_chart_data(symbol: str):
    """Fetch FRESH 15m OHLCV. Tries MT5 first for live data, falls back to Yahoo Finance."""
    now = _time.time()
    cached = _chart_cache.get(symbol)
    if cached and (now - _chart_cache_ts.get(symbol, 0)) < _CHART_CACHE_TTL:
        # Only serve cache if it was from MT5 (live). Don't cache Yahoo data for long.
        if cached.get("source") == "mt5_live":
            return cached

    candles = []
    source = "unknown"
    
    # ── Try MT5 first (live real-time data) ──────────────────────────────────
    if MT5_AVAILABLE:
        try:
            mt5_df = mt5_bridge.get_chart_data(symbol)
            if mt5_df is not None and not mt5_df.empty:
                source = "mt5_live"
                for _, row in mt5_df.iterrows():
                    candles.append({
                        "time": int(row["time"].timestamp()),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": int(row["tick_volume"])
                    })
                print(f"[CHART] ✅ MT5 live data for {symbol}: {len(candles)} candles")
            else:
                # Convert Yahoo symbol to expected MT5 name for the log
                mt5_sym = mt5_bridge._convert_symbol(symbol)
                print(f"[CHART] ⚠️  MT5 returned no data for {symbol} (MT5 symbol: '{mt5_sym}'). "
                      f"Check that symbol exists in Deriv Market Watch.")
        except Exception as e:
            print(f"[CHART] ❌ MT5 fetch error for {symbol}: {e}")

    # ── Fallback to Yahoo Finance if MT5 failed ───────────────────────────────
    if not candles:
        from data_fetcher import _yahoo_chart
        import numpy as np
        print(f"[CHART] ⚠️  Falling back to Yahoo Finance for {symbol} (data may be delayed 15min)")
        try:
            df = _yahoo_chart(symbol, interval="15m", range_str="60d")
            if df.empty:
                return {"error": f"No data for {symbol}", "candles": []}

            source = "yahoo_finance"
            for ts, row in df.iterrows():
                t = int(ts.timestamp()) if hasattr(ts, 'timestamp') else int(pd.Timestamp(ts).timestamp())
                o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
                v = int(row.get("volume", 0)) if "volume" in row.index else 0

                if np.isnan(o) or np.isnan(h) or np.isnan(l) or np.isnan(c):
                    continue
                if h < l:
                    h, l = l, h

                dp = 5 if abs(c) <= 10 else (4 if abs(c) <= 1000 else 2)
                candles.append({
                    "time": t, "open": round(o, dp), "high": round(h, dp),
                    "low": round(l, dp), "close": round(c, dp), "volume": v,
                })
        except Exception as e:
            print(f"[CHART] Yahoo error fetching {symbol}: {e}")

    if not candles:
        if symbol in _chart_cache:
            return _chart_cache[symbol]
        return {"error": f"Failed to fetch data for {symbol}", "candles": []}

    # Deduplicate and sort
    seen = set()
    unique = []
    for c in candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            unique.append(c)
    unique.sort(key=lambda x: x["time"])

    result = {
        "symbol": symbol,
        "display_name": INSTRUMENT_NAMES.get(symbol, symbol),
        "candles": unique,
        "count": len(unique),
        "last_update": datetime.now().isoformat(),
        "source": source,
    }

    # Only cache MT5 live data with full TTL; don't cache Yahoo fallback
    if source == "mt5_live":
        _chart_cache[symbol] = result
        _chart_cache_ts[symbol] = now

    return result



@app.get("/api/chart-data/{symbol:path}")
async def get_chart_data(symbol: str):
    """Return 15m OHLCV data formatted for lightweight-charts"""
    try:
        result = await asyncio.to_thread(_fetch_chart_data, symbol)
        if "error" in result and not result.get("candles"):
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_market_overview(all_data: dict, correlation_data: dict) -> dict:
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for symbol, df in all_data.items():
        if len(df) < 20:
            continue
        pct = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df["close"].iloc[-20]
        if pct > 0.001:
            bullish_count += 1
        elif pct < -0.001:
            bearish_count += 1
        else:
            neutral_count += 1

    # Currency strength summary
    cs = correlation_data.get("currency_strength", {})
    strongest = cs.get("strongest", "N/A")
    weakest = cs.get("weakest", "N/A")

    # Risk sentiment
    risk = correlation_data.get("risk_sentiment", {})

    return {
        "total_analyzed": len(all_data),
        "bullish_instruments": bullish_count,
        "bearish_instruments": bearish_count,
        "neutral_instruments": neutral_count,
        "dxy_bias": correlation_data.get("dxy_bias", {}).get("bias", "neutral"),
        "risk_sentiment": risk.get("sentiment", "neutral"),
        "strongest_currency": strongest,
        "weakest_currency": weakest,
        "best_pair": cs.get("best_pair_long"),
    }


def _get_asset_class(symbol: str) -> str:
    for cls, symbols in ASSET_CLASSES.items():
        if symbol in symbols:
            return cls
    return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# TRADINGVIEW MCP ENDPOINTS — powered by tradingview-mcp-server package
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/mcp/status")
async def mcp_status():
    """Check if TradingView MCP integration is available"""
    return {"available": TV_MCP_AVAILABLE}


@app.get("/api/mcp/analysis/{symbol:path}")
async def mcp_combined_analysis(symbol: str, timeframe: str = "15m"):
    """TradingView technicals + Reddit sentiment + News → confluence decision"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_combined_analysis, symbol, timeframe)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/technicals/{symbol:path}")
async def mcp_technicals(symbol: str, timeframe: str = "15m"):
    """30+ TradingView indicators for a symbol"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_coin_analysis, symbol, timeframe)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/multi-agent/{symbol:path}")
async def mcp_multi_agent(symbol: str, timeframe: str = "15m"):
    """3-agent debate: Technical Analyst vs Sentiment Analyst vs Risk Manager"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_multi_agent, symbol, timeframe)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/sentiment/{symbol:path}")
async def mcp_sentiment(symbol: str):
    """Reddit sentiment analysis"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_sentiment, symbol)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/news")
async def mcp_news(symbol: str = None, category: str = "all"):
    """Live financial news headlines"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_news, symbol, category)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/snapshot")
async def mcp_market_snapshot():
    """Global market snapshot: S&P500, NASDAQ, VIX, BTC, EUR/USD, etc."""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_market_snapshot)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/price/{symbol:path}")
async def mcp_yahoo_price(symbol: str):
    """Real-time Yahoo Finance price quote"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(tv_bridge.tv_yahoo_price, symbol)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/backtest/{symbol:path}")
async def mcp_backtest(symbol: str, strategy: str = "supertrend",
                       period: str = "1y", interval: str = "1d",
                       trade_log: bool = False, equity_curve: bool = False):
    """Backtest a strategy: rsi, bollinger, macd, ema_cross, supertrend, donchian"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(
            tv_bridge.tv_backtest, symbol, strategy, period, interval,
            trade_log, equity_curve
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/compare/{symbol:path}")
async def mcp_compare_strategies(symbol: str, period: str = "1y", interval: str = "1d"):
    """Run all 6 strategies on a symbol and rank by performance"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(
            tv_bridge.tv_compare_strategies, symbol, period, interval
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/walkforward/{symbol:path}")
async def mcp_walk_forward(symbol: str, strategy: str = "supertrend",
                            period: str = "2y", interval: str = "1d"):
    """Walk-forward backtest to detect overfitting"""
    if not TV_MCP_AVAILABLE:
        raise HTTPException(status_code=503, detail="TradingView MCP bridge not available")
    try:
        result = await asyncio.to_thread(
            tv_bridge.tv_walk_forward, symbol, strategy, period, interval
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# MT5 TRADING ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
from pydantic import BaseModel

class MT5TradeRequest(BaseModel):
    symbol: str
    direction: str
    lot_size: float = 1.0
    sl: float = 0.0
    tp: float = 0.0

@app.post("/api/mt5/trade")
async def execute_mt5_trade(req: MT5TradeRequest):
    """Place a live trade directly on the MT5 terminal"""
    if not MT5_AVAILABLE:
        raise HTTPException(status_code=503, detail="MT5 Bridge is not loaded")
    
    try:
        result = await asyncio.to_thread(
            mt5_bridge.place_trade,
            req.symbol, req.direction, req.lot_size, req.sl, req.tp
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Trade failed"))
            
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════════════════════════════
# TRADE JOURNAL ENDPOINTS — Tradezella-style trade tracking
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/journal/open")
async def journal_open_trade(signal: dict):
    """Open a new trade from a signal. Send the full signal object."""
    try:
        trade_id = await asyncio.to_thread(journal.open_trade, signal, signal.get("notes", ""))
        return JSONResponse(content={"success": True, "trade_id": trade_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/journal/close/{trade_id}")
async def journal_close_trade(trade_id: int, outcome: str = "WIN",
                               close_price: float = 0, notes: str = ""):
    """Manually close a trade. outcome = WIN or LOSS"""
    try:
        result = await asyncio.to_thread(
            journal.close_trade, trade_id, outcome.upper(), close_price, notes)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journal/trades")
async def journal_list_trades(status: str = None, limit: int = 200):
    """List all trades, optionally filtered by OPEN/CLOSED"""
    try:
        trades = await asyncio.to_thread(journal.get_all_trades, status, limit)
        return JSONResponse(content={"trades": trades, "count": len(trades)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journal/trade/{trade_id}")
async def journal_get_trade(trade_id: int):
    try:
        trade = await asyncio.to_thread(journal.get_trade, trade_id)
        return JSONResponse(content=trade)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journal/stats")
async def journal_stats():
    """Tradezella-style dashboard stats + equity curve"""
    try:
        stats = await asyncio.to_thread(journal.get_journal_stats)
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/journal/trade/{trade_id}")
async def journal_delete_trade(trade_id: int):
    try:
        result = await asyncio.to_thread(journal.delete_trade, trade_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/journal/notes/{trade_id}")
async def journal_update_notes(trade_id: int, notes: str = "",
                                tags: str = None):
    try:
        tag_list = json.loads(tags) if tags else None
        result = await asyncio.to_thread(
            journal.update_notes, trade_id, notes, tag_list)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-SOURCE DATA ENDPOINTS — Yahoo + Alpha Vantage + FMP + Alpaca
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/data-sources")
async def data_sources_status():
    """Status of all free data sources (configured, rate limits, coverage)"""
    if not MULTI_SOURCE_AVAILABLE:
        return JSONResponse(content={"error": "Multi-source module not loaded"})
    try:
        status = await asyncio.to_thread(msf.get_sources_status)
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/consensus-price/{symbol:path}")
async def consensus_price(symbol: str):
    """Get price from multiple sources with consensus validation"""
    if not MULTI_SOURCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-source module not loaded")
    try:
        result = await asyncio.to_thread(msf.get_consensus_price, symbol)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fundamentals/{symbol:path}")
async def get_fundamentals(symbol: str):
    """Get fundamental data (P/E, EPS, ROE, etc.) from FMP"""
    if not MULTI_SOURCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-source module not loaded")
    try:
        result = await asyncio.to_thread(msf._fmp_fundamentals, symbol)
        if not result:
            return JSONResponse(content={"error": f"No fundamental data for {symbol}. Ensure FMP_KEY is set in .env"})
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
