"""
AURA TRADES - Macro Intermarket Engine
Cross-asset analysis: Bond yields, VIX, DXY, commodities, equities.
Provides institutional-grade intermarket context for trade decisions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from data_fetcher import _yahoo_chart


class MacroIntermarketEngine:
    """
    Bloomberg-level intermarket analysis:
    - DXY (Dollar Index) flow analysis
    - Bond yield curve (2Y, 10Y, 30Y)
    - Yield curve inversion detection
    - VIX regime (fear/greed)
    - Gold/Oil as risk indicators
    - Equity index correlation
    - Risk-on / Risk-off classification
    - Cross-asset momentum
    - Macro regime scoring
    """

    # Macro instruments to track
    MACRO_SYMBOLS = {
        "dxy": "DX-Y.NYB",        # Dollar Index
        "vix": "^VIX",             # Volatility Index
        "gold": "GC=F",           # Gold futures
        "oil": "CL=F",            # Crude Oil
        "sp500": "^GSPC",         # S&P 500
        "us10y": "^TNX",          # 10Y Treasury Yield
        "us2y": "^IRX",           # 13-week T-Bill (proxy for short rates)
        "nasdaq": "^IXIC",        # Nasdaq
        "dax": "^GDAXI",          # DAX
        "nikkei": "^N225",        # Nikkei
    }

    # Currency sensitivity to macro factors
    CURRENCY_SENSITIVITY = {
        "USD": {"dxy": 1.0, "us10y": 0.7, "vix": 0.3, "gold": -0.5, "sp500": -0.2},
        "EUR": {"dxy": -0.9, "dax": 0.3, "gold": 0.2, "vix": -0.2},
        "GBP": {"dxy": -0.7, "us10y": -0.3, "gold": 0.2, "vix": -0.3},
        "JPY": {"dxy": -0.3, "vix": 0.7, "us10y": -0.6, "gold": 0.4, "sp500": -0.5},
        "CHF": {"dxy": -0.4, "vix": 0.5, "gold": 0.6, "sp500": -0.3},
        "AUD": {"dxy": -0.6, "gold": 0.5, "oil": 0.3, "sp500": 0.5, "vix": -0.5},
        "NZD": {"dxy": -0.5, "sp500": 0.4, "vix": -0.4},
        "CAD": {"dxy": -0.5, "oil": 0.7, "sp500": 0.3, "vix": -0.3},
    }

    def __init__(self):
        self._macro_cache = {}
        self._macro_ts = 0
        self._cache_ttl = 300  # 5 min cache

    def analyze(self, symbol: str, all_data: dict = None) -> dict:
        """Full macro intermarket analysis"""
        try:
            # Extract currencies
            base_ccy, quote_ccy = self._extract_currencies(symbol)

            result = {}

            # Fetch macro data
            macro_data = self._get_macro_data(all_data)

            # DXY analysis
            result["dxy"] = self._dxy_analysis(macro_data)

            # VIX regime
            result["vix"] = self._vix_regime(macro_data)

            # Bond yield analysis
            result["yields"] = self._yield_analysis(macro_data)

            # Gold as safe haven indicator
            result["gold"] = self._gold_analysis(macro_data)

            # Oil / Energy
            result["oil"] = self._oil_analysis(macro_data)

            # Equity market context
            result["equities"] = self._equity_analysis(macro_data)

            # Risk-on/Risk-off classification
            result["risk_sentiment"] = self._risk_sentiment(result)

            # Cross-asset momentum
            result["cross_momentum"] = self._cross_asset_momentum(macro_data)

            # Currency-specific macro score
            result["currency_macro"] = self._currency_macro_score(result, base_ccy, quote_ccy)

            # Composite
            result["bias"] = result["currency_macro"].get("bias", "neutral")
            result["macro_score"] = result["currency_macro"].get("score", 50)

            return result

        except Exception as e:
            print(f"[MacroEngine] Error for {symbol}: {e}")
            return self._empty_result()

    def _get_macro_data(self, all_data: dict = None) -> dict:
        """Get macro instrument data (from cache or all_data)"""
        import time
        now = time.time()

        if now - self._macro_ts < self._cache_ttl and self._macro_cache:
            return self._macro_cache

        macro = {}

        # Try to get from all_data first
        if all_data:
            for name, symbol in self.MACRO_SYMBOLS.items():
                if symbol in all_data:
                    macro[name] = all_data[symbol]

        # Fetch missing ones
        for name, symbol in self.MACRO_SYMBOLS.items():
            if name not in macro:
                try:
                    df = _yahoo_chart(symbol, interval="1d", range_str="30d")
                    if not df.empty:
                        macro[name] = df
                except Exception:
                    pass

        self._macro_cache = macro
        self._macro_ts = now
        return macro

    def _dxy_analysis(self, macro_data: dict) -> dict:
        """Dollar Index analysis"""
        dxy_df = macro_data.get("dxy")
        if dxy_df is None or dxy_df.empty or len(dxy_df) < 5:
            return {"trend": "neutral", "strength": 0, "signal": "neutral"}

        close = dxy_df["close"].values
        current = close[-1]

        # DXY trend
        sma_10 = np.mean(close[-10:]) if len(close) >= 10 else current
        sma_20 = np.mean(close[-20:]) if len(close) >= 20 else current

        # Momentum
        roc_5 = (current / close[-5] - 1) * 100 if len(close) >= 5 else 0

        if current > sma_10 > sma_20:
            trend = "bullish"  # USD strengthening
        elif current < sma_10 < sma_20:
            trend = "bearish"  # USD weakening
        else:
            trend = "neutral"

        # Strength score (0-100)
        if len(close) >= 20:
            price_range = close[-20:].max() - close[-20:].min()
            if price_range > 0:
                position = (current - close[-20:].min()) / price_range * 100
            else:
                position = 50
        else:
            position = 50

        return {
            "trend": trend,
            "current": round(float(current), 2),
            "sma_10": round(float(sma_10), 2),
            "roc_5": round(roc_5, 2),
            "strength": round(position, 1),
            "signal": trend,
        }

    def _vix_regime(self, macro_data: dict) -> dict:
        """VIX fear/greed analysis"""
        vix_df = macro_data.get("vix")
        if vix_df is None or vix_df.empty:
            return {"level": "unknown", "regime": "normal", "signal": "neutral"}

        close = vix_df["close"].values
        current = float(close[-1])

        # VIX levels
        if current > 30:
            regime = "extreme_fear"
            signal = "risk_off"
        elif current > 20:
            regime = "elevated_fear"
            signal = "cautious"
        elif current > 15:
            regime = "normal"
            signal = "neutral"
        elif current > 12:
            regime = "complacency"
            signal = "risk_on"
        else:
            regime = "extreme_greed"
            signal = "risk_on"

        # VIX trend (rising VIX = increasing fear)
        if len(close) >= 5:
            vix_5d_change = (current / close[-5] - 1) * 100
        else:
            vix_5d_change = 0

        # VIX spike detection
        spike = vix_5d_change > 20

        return {
            "level": round(current, 1),
            "regime": regime,
            "change_5d_pct": round(vix_5d_change, 1),
            "spike": spike,
            "signal": signal,
        }

    def _yield_analysis(self, macro_data: dict) -> dict:
        """Bond yield analysis"""
        us10y_df = macro_data.get("us10y")
        us2y_df = macro_data.get("us2y")

        result = {"curve": "normal", "signal": "neutral"}

        if us10y_df is not None and not us10y_df.empty:
            y10 = float(us10y_df["close"].iloc[-1])
            result["us10y"] = round(y10, 3)

            # Yield trend
            if len(us10y_df) >= 10:
                y10_prev = float(us10y_df["close"].iloc[-10])
                result["us10y_trend"] = "rising" if y10 > y10_prev else "falling"
            else:
                result["us10y_trend"] = "neutral"

            # Rising yields = USD bullish (usually)
            if result["us10y_trend"] == "rising":
                result["signal"] = "usd_bullish"
            elif result["us10y_trend"] == "falling":
                result["signal"] = "usd_bearish"

        if us2y_df is not None and not us2y_df.empty and us10y_df is not None and not us10y_df.empty:
            y2 = float(us2y_df["close"].iloc[-1])
            y10 = float(us10y_df["close"].iloc[-1])
            spread = y10 - y2
            result["yield_spread"] = round(spread, 3)
            result["curve"] = "inverted" if spread < 0 else "flat" if spread < 0.5 else "normal"

        return result

    def _gold_analysis(self, macro_data: dict) -> dict:
        """Gold as safe-haven indicator"""
        gold_df = macro_data.get("gold")
        if gold_df is None or gold_df.empty:
            return {"trend": "neutral", "signal": "neutral"}

        close = gold_df["close"].values
        current = float(close[-1])

        # Gold trend
        sma_10 = np.mean(close[-10:]) if len(close) >= 10 else current
        roc_5 = (current / close[-5] - 1) * 100 if len(close) >= 5 else 0

        if current > sma_10 and roc_5 > 0.5:
            trend = "rising"
            signal = "risk_off"  # Gold rising = fear
        elif current < sma_10 and roc_5 < -0.5:
            trend = "falling"
            signal = "risk_on"  # Gold falling = confidence
        else:
            trend = "neutral"
            signal = "neutral"

        return {
            "current": round(current, 2),
            "trend": trend,
            "roc_5": round(roc_5, 2),
            "signal": signal,
        }

    def _oil_analysis(self, macro_data: dict) -> dict:
        """Oil / Energy analysis (impacts CAD, NOK, and inflation)"""
        oil_df = macro_data.get("oil")
        if oil_df is None or oil_df.empty:
            return {"trend": "neutral", "signal": "neutral"}

        close = oil_df["close"].values
        current = float(close[-1])

        sma_10 = np.mean(close[-10:]) if len(close) >= 10 else current
        roc_5 = (current / close[-5] - 1) * 100 if len(close) >= 5 else 0

        if current > sma_10 and roc_5 > 1:
            trend = "rising"
            signal = "cad_bullish"
        elif current < sma_10 and roc_5 < -1:
            trend = "falling"
            signal = "cad_bearish"
        else:
            trend = "neutral"
            signal = "neutral"

        return {
            "current": round(current, 2),
            "trend": trend,
            "roc_5": round(roc_5, 2),
            "signal": signal,
        }

    def _equity_analysis(self, macro_data: dict) -> dict:
        """Equity market analysis"""
        sp500_df = macro_data.get("sp500")
        if sp500_df is None or sp500_df.empty:
            return {"trend": "neutral", "signal": "neutral", "risk_appetite": "neutral"}

        close = sp500_df["close"].values
        current = float(close[-1])

        sma_10 = np.mean(close[-10:]) if len(close) >= 10 else current
        sma_20 = np.mean(close[-20:]) if len(close) >= 20 else current
        roc_5 = (current / close[-5] - 1) * 100 if len(close) >= 5 else 0

        if current > sma_10 > sma_20:
            trend = "bullish"
            risk_appetite = "risk_on"
        elif current < sma_10 < sma_20:
            trend = "bearish"
            risk_appetite = "risk_off"
        else:
            trend = "mixed"
            risk_appetite = "neutral"

        return {
            "current": round(current, 2),
            "trend": trend,
            "roc_5": round(roc_5, 2),
            "risk_appetite": risk_appetite,
            "signal": risk_appetite,
        }

    def _risk_sentiment(self, result: dict) -> dict:
        """Determine overall risk sentiment from all macro data"""
        risk_on_score = 0
        risk_off_score = 0

        # VIX
        vix = result.get("vix", {})
        if vix.get("signal") == "risk_on":
            risk_on_score += 30
        elif vix.get("signal") == "risk_off":
            risk_off_score += 30
        elif vix.get("signal") == "cautious":
            risk_off_score += 15

        # Gold
        gold = result.get("gold", {})
        if gold.get("signal") == "risk_off":
            risk_off_score += 20
        elif gold.get("signal") == "risk_on":
            risk_on_score += 20

        # Equities
        eq = result.get("equities", {})
        if eq.get("risk_appetite") == "risk_on":
            risk_on_score += 25
        elif eq.get("risk_appetite") == "risk_off":
            risk_off_score += 25

        # Yields
        yields = result.get("yields", {})
        if yields.get("curve") == "inverted":
            risk_off_score += 15
        elif yields.get("signal") == "usd_bullish":
            risk_on_score += 10

        # Oil (rising oil = inflation risk)
        oil = result.get("oil", {})
        if oil.get("trend") == "rising":
            risk_off_score += 10

        total = risk_on_score + risk_off_score
        if total == 0:
            return {"sentiment": "neutral", "score": 50, "signal": "neutral"}

        if risk_on_score > risk_off_score * 1.5:
            sentiment = "strong_risk_on"
            signal = "risk_on"
        elif risk_on_score > risk_off_score:
            sentiment = "mild_risk_on"
            signal = "risk_on"
        elif risk_off_score > risk_on_score * 1.5:
            sentiment = "strong_risk_off"
            signal = "risk_off"
        elif risk_off_score > risk_on_score:
            sentiment = "mild_risk_off"
            signal = "risk_off"
        else:
            sentiment = "neutral"
            signal = "neutral"

        score = (risk_on_score / total) * 100

        return {
            "sentiment": sentiment,
            "risk_on_score": risk_on_score,
            "risk_off_score": risk_off_score,
            "score": round(score, 1),
            "signal": signal,
        }

    def _cross_asset_momentum(self, macro_data: dict) -> dict:
        """Cross-asset momentum analysis"""
        momentum = {}

        for name, df in macro_data.items():
            if df is None or df.empty or len(df) < 5:
                continue
            close = df["close"].values
            roc = (close[-1] / close[-5] - 1) * 100
            momentum[name] = round(roc, 2)

        # Identify strongest / weakest
        if momentum:
            strongest = max(momentum, key=momentum.get)
            weakest = min(momentum, key=momentum.get)
        else:
            strongest = "unknown"
            weakest = "unknown"

        return {
            "momentum": momentum,
            "strongest_asset": strongest,
            "weakest_asset": weakest,
        }

    def _currency_macro_score(self, result: dict, base: str, quote: str) -> dict:
        """Calculate currency-specific macro score"""
        base_score = 0
        quote_score = 0

        # DXY impact
        dxy = result.get("dxy", {})
        dxy_trend = dxy.get("trend", "neutral")

        base_sens = self.CURRENCY_SENSITIVITY.get(base, {})
        quote_sens = self.CURRENCY_SENSITIVITY.get(quote, {})

        # DXY
        if dxy_trend == "bullish":
            base_score += base_sens.get("dxy", 0) * 20
            quote_score += quote_sens.get("dxy", 0) * 20
        elif dxy_trend == "bearish":
            base_score -= base_sens.get("dxy", 0) * 20
            quote_score -= quote_sens.get("dxy", 0) * 20

        # Risk sentiment
        risk = result.get("risk_sentiment", {})
        risk_signal = risk.get("signal", "neutral")
        if risk_signal == "risk_on":
            # Risk-on favors AUD, NZD, CAD; hurts JPY, CHF
            base_score += base_sens.get("sp500", 0) * 15
            quote_score += quote_sens.get("sp500", 0) * 15
        elif risk_signal == "risk_off":
            base_score -= base_sens.get("sp500", 0) * 15
            quote_score -= quote_sens.get("sp500", 0) * 15
            # Safe havens benefit
            base_score += base_sens.get("vix", 0) * 15
            quote_score += quote_sens.get("vix", 0) * 15

        # Gold
        gold = result.get("gold", {})
        if gold.get("trend") == "rising":
            base_score += base_sens.get("gold", 0) * 10
            quote_score += quote_sens.get("gold", 0) * 10
        elif gold.get("trend") == "falling":
            base_score -= base_sens.get("gold", 0) * 10
            quote_score -= quote_sens.get("gold", 0) * 10

        # Oil (mainly CAD)
        oil = result.get("oil", {})
        if oil.get("trend") == "rising":
            base_score += base_sens.get("oil", 0) * 10
            quote_score += quote_sens.get("oil", 0) * 10
        elif oil.get("trend") == "falling":
            base_score -= base_sens.get("oil", 0) * 10
            quote_score -= quote_sens.get("oil", 0) * 10

        # Net score (positive = bullish for pair)
        net = base_score - quote_score
        normalized = max(0, min(100, net + 50))

        if net > 15:
            bias = "bullish"
        elif net < -15:
            bias = "bearish"
        else:
            bias = "neutral"

        return {
            "bias": bias,
            "score": round(normalized, 1),
            "base_score": round(base_score, 1),
            "quote_score": round(quote_score, 1),
            "net": round(net, 1),
        }

    def _extract_currencies(self, symbol: str) -> tuple:
        """Extract base/quote currencies"""
        clean = symbol.replace("=X", "").replace("/", "")
        if len(clean) == 6 and clean.isalpha():
            return clean[:3].upper(), clean[3:].upper()
        currency_map = {
            "^GSPC": ("USD", "USD"), "^DJI": ("USD", "USD"), "^IXIC": ("USD", "USD"),
            "^FTSE": ("GBP", "GBP"), "^GDAXI": ("EUR", "EUR"),
            "GC=F": ("XAU", "USD"), "SI=F": ("XAG", "USD"),
            "CL=F": ("OIL", "USD"), "BTC-USD": ("BTC", "USD"), "ETH-USD": ("ETH", "USD"),
        }
        return currency_map.get(symbol, ("USD", "USD"))

    def _empty_result(self) -> dict:
        return {
            "dxy": {"trend": "neutral", "signal": "neutral"},
            "vix": {"regime": "normal", "signal": "neutral"},
            "yields": {"curve": "normal", "signal": "neutral"},
            "gold": {"trend": "neutral", "signal": "neutral"},
            "oil": {"trend": "neutral", "signal": "neutral"},
            "equities": {"trend": "neutral", "signal": "neutral"},
            "risk_sentiment": {"sentiment": "neutral", "signal": "neutral", "score": 50},
            "cross_momentum": {},
            "currency_macro": {"bias": "neutral", "score": 50},
            "bias": "neutral",
            "macro_score": 50,
        }
