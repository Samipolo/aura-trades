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
from config import ALL_INSTRUMENTS, INSTRUMENT_NAMES, ASSET_CLASSES

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


@app.get("/api/analyze")
async def analyze_all():
    """
    MAIN ENDPOINT: Full multi-engine analysis of all CFD pairs.
    Returns ranked trade signals with institutional-grade analysis.
    """
    errors = []
    all_signals = []

    try:
        # ===== STEP 1: FETCH ALL DATA =====
        print("[AURA V2] Fetching market data for all instruments...")
        all_data = {}
        for symbol in ALL_INSTRUMENTS:
            try:
                df = data_fetcher.fetch_15m_data(symbol)
                if not df.empty and len(df) >= 200:
                    all_data[symbol] = df
            except Exception as e:
                errors.append(f"Fetch: {symbol}: {str(e)[:50]}")

        if not all_data:
            raise HTTPException(status_code=503, detail="No market data available")

        print(f"[AURA V2] Loaded {len(all_data)} instruments")

        # ===== STEP 2: CORRELATION & INTER-MARKET =====
        print("[AURA V2] Running enhanced correlation analysis...")
        correlation_data = correlation_analyzer.analyze(all_data)

        # ===== STEP 3: ANALYZE EACH INSTRUMENT =====
        print("[AURA V2] Running 8-engine analysis on each instrument...")
        for symbol, df_15m in all_data.items():
            try:
                # Engine 1: Technical Indicators
                indicator_data = indicator_engine.calculate_all(df_15m)
                if not indicator_data:
                    continue

                # Engine 2: Market Structure
                structure_data = structure_analyzer.analyze(df_15m)
                if not structure_data:
                    continue

                # Engine 3: Advanced Quantitative
                quant_data = quant_engine.analyze(df_15m)

                # Engine 4: Order Flow
                orderflow_data = orderflow_engine.analyze(df_15m)

                # Engine 5: Multi-Timeframe
                mtf_data = mtf_engine.analyze(df_15m)

                # Engine 6: Pattern Recognition
                pattern_data = pattern_engine.analyze(df_15m)

                # Engine 7: Correlation Score
                corr_score = correlation_analyzer.get_correlation_score(
                    symbol, structure_data.get("bias", "neutral"), all_data
                )

                # Engine 8: Generate Signal (combines all engines)
                signal = signal_generator.generate_signal(
                    symbol, indicator_data, structure_data, corr_score,
                    quant_data, orderflow_data, mtf_data, pattern_data, all_data
                )

                if signal:
                    # Apply Risk Engine evaluation
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

                    all_signals.append(signal)

            except Exception as e:
                errors.append(f"Analysis: {symbol}: {str(e)[:80]}")

        # ===== STEP 4: RANK ALL SIGNALS =====
        print(f"[AURA V2] Ranking {len(all_signals)} signals...")
        ranked_signals = trade_ranker.rank_signals(all_signals)

        # ===== STEP 5: BUILD OVERVIEW =====
        market_overview = _build_market_overview(all_data, correlation_data)

        print(f"[AURA V2] ✓ Analysis complete: {len(ranked_signals)} trade ideas ranked")

        return JSONResponse(content={
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
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/analyze/{symbol}")
async def analyze_single(symbol: str):
    """Deep analysis of a single instrument"""
    try:
        df = data_fetcher.fetch_15m_data(symbol)
        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        # Run all engines
        indicator_data = indicator_engine.calculate_all(df)
        structure_data = structure_analyzer.analyze(df)
        quant_data = quant_engine.analyze(df)
        orderflow_data = orderflow_engine.analyze(df)
        mtf_data = mtf_engine.analyze(df)
        pattern_data = pattern_engine.analyze(df)

        # Correlation context
        all_data = {symbol: df}
        for s in ALL_INSTRUMENTS[:10]:
            if s != symbol:
                rdf = data_fetcher.fetch_15m_data(s)
                if not rdf.empty:
                    all_data[s] = rdf

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

        return JSONResponse(content={
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
        })

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
    return {
        "status": "healthy",
        "version": "2.0.0",
        "engines": 8,
        "timestamp": datetime.now().isoformat()
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
