"""
AURA TRADES - Main FastAPI Application
Self-decision AI day trading system on 15-minute timeframe
"""

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import traceback
from datetime import datetime

from data_fetcher import DataFetcher
from indicators import IndicatorEngine
from market_structure import MarketStructureAnalyzer
from correlation import CorrelationAnalyzer
from signal_generator import SignalGenerator, TradeRanker
from config import ALL_INSTRUMENTS, INSTRUMENT_NAMES, ASSET_CLASSES

app = FastAPI(
    title="AURA TRADES - AI Trading System",
    description="Self-decision day trading AI on 15-minute timeframe with 1:2 R:R",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
data_fetcher = DataFetcher()
indicator_engine = IndicatorEngine()
market_structure_analyzer = MarketStructureAnalyzer()
correlation_analyzer = CorrelationAnalyzer()
signal_generator = SignalGenerator()
trade_ranker = TradeRanker()


class AnalysisResponse(BaseModel):
    success: bool
    timestamp: str
    total_instruments: int
    signals_generated: int
    ranked_trades: List[dict]
    correlation_data: dict
    market_overview: dict
    errors: List[str]


@app.get("/")
async def root():
    return {"message": "AURA TRADES AI Trading System - Active", "version": "1.0.0"}


@app.get("/api/analyze", response_model=None)
async def analyze_all():
    """Main endpoint: Analyze all CFD pairs and return ranked trade signals"""
    errors = []
    all_signals = []

    try:
        # Step 1: Fetch data for all instruments
        print("[AURA] Fetching market data...")
        all_data = {}
        for symbol in ALL_INSTRUMENTS:
            try:
                df = data_fetcher.fetch_15m_data(symbol)
                if not df.empty and len(df) >= 200:
                    all_data[symbol] = df
            except Exception as e:
                errors.append(f"Data fetch error for {symbol}: {str(e)}")

        if not all_data:
            raise HTTPException(status_code=503, detail="No market data available")

        print(f"[AURA] Data loaded for {len(all_data)} instruments")

        # Step 2: Correlation analysis
        print("[AURA] Running correlation analysis...")
        correlation_data = correlation_analyzer.analyze(all_data)

        # Step 3: Analyze each instrument
        print("[AURA] Analyzing instruments...")
        for symbol, df_15m in all_data.items():
            try:
                # Calculate indicators
                indicator_data = indicator_engine.calculate_all(df_15m)
                if not indicator_data:
                    continue

                # Market structure analysis
                structure_data = market_structure_analyzer.analyze(df_15m)
                if not structure_data:
                    continue

                # Get correlation score for this symbol's potential direction
                corr_score = correlation_analyzer.get_correlation_score(
                    symbol,
                    structure_data.get("bias", "neutral"),
                    all_data
                )

                # Generate signal
                signal = signal_generator.generate_signal(
                    symbol, indicator_data, structure_data, corr_score, all_data
                )

                if signal:
                    all_signals.append(signal)

            except Exception as e:
                errors.append(f"Analysis error for {symbol}: {str(e)}")

        # Step 4: Rank all signals
        print(f"[AURA] Ranking {len(all_signals)} trade signals...")
        ranked_signals = trade_ranker.rank_signals(all_signals)

        # Step 5: Market overview
        market_overview = _build_market_overview(all_data, correlation_data)

        print(f"[AURA] Analysis complete. {len(ranked_signals)} trade ideas generated.")

        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "total_instruments": len(all_data),
            "signals_generated": len(ranked_signals),
            "ranked_trades": ranked_signals,
            "correlation_data": {
                "dxy_bias": correlation_data.get("dxy_bias", {}),
                "signals": correlation_data.get("signals", []),
                "cross_asset": correlation_data.get("cross_asset", []),
            },
            "market_overview": market_overview,
            "errors": errors[:10],  # Limit error reporting
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/analyze/{symbol}")
async def analyze_single(symbol: str):
    """Analyze a single instrument"""
    try:
        df = data_fetcher.fetch_15m_data(symbol)
        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        indicator_data = indicator_engine.calculate_all(df)
        structure_data = market_structure_analyzer.analyze(df)

        # Fetch related instruments for correlation
        all_data = {symbol: df}
        for related_symbol in ALL_INSTRUMENTS[:10]:
            if related_symbol != symbol:
                rdf = data_fetcher.fetch_15m_data(related_symbol)
                if not rdf.empty:
                    all_data[related_symbol] = rdf

        corr_score = correlation_analyzer.get_correlation_score(
            symbol, structure_data.get("bias", "neutral"), all_data
        )

        signal = signal_generator.generate_signal(symbol, indicator_data, structure_data, corr_score, all_data)

        return JSONResponse(content={
            "success": True,
            "symbol": symbol,
            "display_name": INSTRUMENT_NAMES.get(symbol, symbol),
            "signal": signal,
            "structure": {
                "bias": structure_data.get("bias"),
                "type": structure_data.get("structure", {}).get("type"),
                "order_blocks": len(structure_data.get("order_blocks", [])),
                "fvgs": len(structure_data.get("fair_value_gaps", [])),
            },
            "indicators": {
                "trend": indicator_data["signals"]["trend"] if indicator_data else None,
                "momentum": indicator_data["signals"]["momentum"] if indicator_data else None,
                "volatility": indicator_data["signals"]["volatility"] if indicator_data else None,
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
    """List all monitored instruments"""
    return {
        "instruments": [
            {"symbol": s, "name": INSTRUMENT_NAMES.get(s, s), "class": _get_asset_class(s)}
            for s in ALL_INSTRUMENTS
        ],
        "total": len(ALL_INSTRUMENTS)
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def _build_market_overview(all_data: dict, correlation_data: dict) -> dict:
    """Build overall market overview"""
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

    return {
        "total_analyzed": len(all_data),
        "bullish_instruments": bullish_count,
        "bearish_instruments": bearish_count,
        "neutral_instruments": neutral_count,
        "dxy_bias": correlation_data.get("dxy_bias", {}).get("bias", "neutral"),
        "risk_sentiment": _get_risk_sentiment(correlation_data),
    }


def _get_risk_sentiment(correlation_data: dict) -> str:
    """Extract risk sentiment from correlation data"""
    cross_asset = correlation_data.get("cross_asset", [])
    for signal in cross_asset:
        if signal.get("type") == "risk_sentiment":
            return signal.get("sentiment", "neutral")
    return "neutral"


def _get_asset_class(symbol: str) -> str:
    """Get asset class for a symbol"""
    for cls, symbols in ASSET_CLASSES.items():
        if symbol in symbols:
            return cls
    return "unknown"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
