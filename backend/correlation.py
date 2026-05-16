"""
AURA TRADES - Correlation Analysis Engine
Analyzes inter-market correlations, divergences, and confirmations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from config import FOREX_PAIRS, INDICES, COMMODITIES, ASSET_CLASSES


class CorrelationAnalyzer:
    """Analyzes correlations between instruments for trade confirmation"""

    # Known correlation relationships
    KNOWN_CORRELATIONS = {
        # Positive correlations
        ("EURUSD=X", "GBPUSD=X"): "positive",
        ("EURUSD=X", "AUDUSD=X"): "positive",
        ("GBPUSD=X", "AUDUSD=X"): "positive",
        ("AUDUSD=X", "NZDUSD=X"): "positive",
        ("GC=F", "SI=F"): "positive",
        ("^GSPC", "^DJI"): "positive",
        ("^GSPC", "^IXIC"): "positive",
        ("CL=F", "USDCAD=X"): "negative",
        # Negative correlations
        ("EURUSD=X", "USDJPY=X"): "negative",
        ("EURUSD=X", "USDCHF=X"): "negative",
        ("GC=F", "USDJPY=X"): "negative",
        ("^GSPC", "GC=F"): "negative",
    }

    # Dollar index proxy components
    DXY_COMPONENTS = {
        "EURUSD=X": -0.576,
        "USDJPY=X": 0.136,
        "GBPUSD=X": -0.119,
        "USDCAD=X": 0.091,
        "USDCHF=X": 0.036,
    }

    def __init__(self):
        self.correlation_matrix = None

    def analyze(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Perform full correlation analysis"""
        if len(all_data) < 2:
            return {"matrix": {}, "signals": [], "dxy_bias": "neutral"}

        # Build returns dataframe
        returns_df = self._build_returns_df(all_data)
        if returns_df.empty:
            return {"matrix": {}, "signals": [], "dxy_bias": "neutral"}

        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        self.correlation_matrix = corr_matrix

        # Find divergences and confirmations
        signals = self._find_correlation_signals(all_data, corr_matrix)

        # Calculate DXY proxy bias
        dxy_bias = self._calculate_dxy_bias(all_data)

        # Cross-asset signals
        cross_asset = self._cross_asset_analysis(all_data)

        return {
            "matrix": corr_matrix.to_dict() if not corr_matrix.empty else {},
            "signals": signals,
            "dxy_bias": dxy_bias,
            "cross_asset": cross_asset,
        }

    def get_correlation_score(self, symbol: str, direction: str, all_data: Dict[str, pd.DataFrame]) -> float:
        """Get a correlation confirmation score for a trade signal (0-100)"""
        if not all_data or symbol not in all_data:
            return 50.0

        score = 50.0
        confirmations = 0
        contradictions = 0

        for pair, rel_type in self.KNOWN_CORRELATIONS.items():
            if symbol in pair:
                other = pair[0] if pair[1] == symbol else pair[1]
                if other not in all_data:
                    continue

                other_direction = self._get_recent_direction(all_data[other])
                if other_direction == "neutral":
                    continue

                if rel_type == "positive":
                    if direction == other_direction:
                        confirmations += 1
                    else:
                        contradictions += 1
                elif rel_type == "negative":
                    if direction != other_direction:
                        confirmations += 1
                    else:
                        contradictions += 1

        total = confirmations + contradictions
        if total > 0:
            score = (confirmations / total) * 100

        return score

    def _build_returns_df(self, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build a dataframe of returns for correlation calculation"""
        closes = {}
        for symbol, df in all_data.items():
            if not df.empty and "close" in df.columns:
                closes[symbol] = df["close"].pct_change().dropna()

        if not closes:
            return pd.DataFrame()

        # Align all series by index
        returns_df = pd.DataFrame(closes)
        returns_df = returns_df.dropna(how="all")
        return returns_df

    def _find_correlation_signals(self, all_data: Dict[str, pd.DataFrame], corr_matrix: pd.DataFrame) -> List[dict]:
        """Find trading signals based on correlation divergences"""
        signals = []

        for (sym1, sym2), expected_rel in self.KNOWN_CORRELATIONS.items():
            if sym1 not in all_data or sym2 not in all_data:
                continue

            dir1 = self._get_recent_direction(all_data[sym1])
            dir2 = self._get_recent_direction(all_data[sym2])

            if dir1 == "neutral" or dir2 == "neutral":
                continue

            # Check for divergence from expected correlation
            if expected_rel == "positive" and dir1 != dir2:
                signals.append({
                    "type": "divergence",
                    "pair1": sym1,
                    "pair2": sym2,
                    "expected": "positive",
                    "actual": f"{sym1}={dir1}, {sym2}={dir2}",
                    "strength": "moderate",
                    "implication": f"{sym1} or {sym2} likely to reverse"
                })
            elif expected_rel == "negative" and dir1 == dir2:
                signals.append({
                    "type": "divergence",
                    "pair1": sym1,
                    "pair2": sym2,
                    "expected": "negative",
                    "actual": f"{sym1}={dir1}, {sym2}={dir2}",
                    "strength": "moderate",
                    "implication": f"Unusual alignment - potential reversal"
                })

        return signals

    def _calculate_dxy_bias(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Calculate USD strength from proxy components"""
        usd_score = 0
        components_used = 0

        for symbol, weight in self.DXY_COMPONENTS.items():
            if symbol not in all_data:
                continue

            df = all_data[symbol]
            if df.empty or len(df) < 20:
                continue

            # Calculate recent returns (last 20 candles ~5 hours on 15m)
            recent_return = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df["close"].iloc[-20]

            # Positive weight means USD strengthens when pair rises
            usd_contribution = recent_return * weight * 100
            usd_score += usd_contribution
            components_used += 1

        if components_used == 0:
            return {"bias": "neutral", "score": 0}

        if usd_score > 0.1:
            bias = "usd_bullish"
        elif usd_score < -0.1:
            bias = "usd_bearish"
        else:
            bias = "neutral"

        return {"bias": bias, "score": round(usd_score, 4)}

    def _cross_asset_analysis(self, all_data: Dict[str, pd.DataFrame]) -> List[dict]:
        """Analyze cross-asset relationships"""
        signals = []

        # Risk-on vs Risk-off
        risk_on_assets = ["^GSPC", "^IXIC", "AUDUSD=X", "NZDUSD=X"]
        risk_off_assets = ["GC=F", "USDJPY=X", "USDCHF=X"]

        risk_on_score = 0
        risk_off_score = 0

        for symbol in risk_on_assets:
            if symbol in all_data:
                direction = self._get_recent_direction(all_data[symbol])
                if direction == "bullish":
                    risk_on_score += 1
                elif direction == "bearish":
                    risk_on_score -= 1

        for symbol in risk_off_assets:
            if symbol in all_data:
                direction = self._get_recent_direction(all_data[symbol])
                if direction == "bullish":
                    risk_off_score += 1
                elif direction == "bearish":
                    risk_off_score -= 1

        if risk_on_score > 2:
            signals.append({
                "type": "risk_sentiment",
                "sentiment": "risk_on",
                "strength": risk_on_score,
                "implication": "Favor long AUD, NZD, indices. Short JPY, CHF, Gold"
            })
        elif risk_off_score > 2:
            signals.append({
                "type": "risk_sentiment",
                "sentiment": "risk_off",
                "strength": risk_off_score,
                "implication": "Favor long JPY, CHF, Gold. Short AUD, NZD, indices"
            })

        return signals

    def _get_recent_direction(self, df: pd.DataFrame) -> str:
        """Get the recent directional move of an instrument"""
        if df.empty or len(df) < 10:
            return "neutral"

        # Use last 10 candles
        recent_close = df["close"].iloc[-1]
        past_close = df["close"].iloc[-10]

        if past_close == 0:
            return "neutral"

        pct_change = (recent_close - past_close) / past_close

        if pct_change > 0.001:
            return "bullish"
        elif pct_change < -0.001:
            return "bearish"
        return "neutral"
