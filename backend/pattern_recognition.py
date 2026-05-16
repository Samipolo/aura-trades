"""
AURA TRADES - Pattern Recognition Engine
Advanced candlestick and chart pattern detection:
- Japanese candlestick patterns (engulfing, pin bars, doji, morning/evening star)
- RSI/MACD divergences (regular & hidden)
- Chart patterns (double top/bottom, head & shoulders)
- Momentum divergences
- Liquidity pool patterns
- Institutional candle patterns
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class PatternRecognitionEngine:
    """Detects candlestick patterns, divergences, and chart formations"""

    def analyze(self, df: pd.DataFrame) -> dict:
        """Run full pattern recognition suite"""
        if df.empty or len(df) < 50:
            return {}

        return {
            "candlestick_patterns": self._candlestick_patterns(df),
            "divergences": self._divergence_detection(df),
            "chart_patterns": self._chart_patterns(df),
            "key_reversals": self._key_reversal_patterns(df),
            "continuation_patterns": self._continuation_patterns(df),
            "institutional_patterns": self._institutional_patterns(df),
        }

    def _candlestick_patterns(self, df: pd.DataFrame) -> List[dict]:
        """Detect major candlestick patterns on recent bars"""
        patterns = []
        n = len(df)

        if n < 5:
            return patterns

        # Analyze last 10 bars for patterns
        for i in range(max(3, n - 10), n):
            curr = df.iloc[i]
            prev = df.iloc[i - 1]
            prev2 = df.iloc[i - 2] if i >= 2 else None

            body = abs(curr["close"] - curr["open"])
            upper_wick = curr["high"] - max(curr["close"], curr["open"])
            lower_wick = min(curr["close"], curr["open"]) - curr["low"]
            total_range = curr["high"] - curr["low"]
            is_bullish = curr["close"] > curr["open"]

            prev_body = abs(prev["close"] - prev["open"])
            prev_is_bullish = prev["close"] > prev["open"]

            if total_range == 0:
                continue

            # Pin Bar / Hammer (bullish)
            if lower_wick > body * 2.5 and upper_wick < body * 0.5 and lower_wick > total_range * 0.6:
                patterns.append({
                    "name": "hammer" if not prev_is_bullish else "hanging_man",
                    "direction": "bullish" if not prev_is_bullish else "bearish",
                    "index": i,
                    "time": str(df.index[i]),
                    "strength": round(float(lower_wick / body), 1),
                    "significance": "high"
                })

            # Shooting Star (bearish)
            if upper_wick > body * 2.5 and lower_wick < body * 0.5 and upper_wick > total_range * 0.6:
                patterns.append({
                    "name": "shooting_star" if prev_is_bullish else "inverted_hammer",
                    "direction": "bearish" if prev_is_bullish else "bullish",
                    "index": i,
                    "time": str(df.index[i]),
                    "strength": round(float(upper_wick / body), 1),
                    "significance": "high"
                })

            # Bullish Engulfing
            if (is_bullish and not prev_is_bullish and
                    curr["open"] <= prev["close"] and curr["close"] >= prev["open"] and
                    body > prev_body * 1.3):
                patterns.append({
                    "name": "bullish_engulfing",
                    "direction": "bullish",
                    "index": i,
                    "time": str(df.index[i]),
                    "strength": round(float(body / prev_body), 1),
                    "significance": "high"
                })

            # Bearish Engulfing
            if (not is_bullish and prev_is_bullish and
                    curr["open"] >= prev["close"] and curr["close"] <= prev["open"] and
                    body > prev_body * 1.3):
                patterns.append({
                    "name": "bearish_engulfing",
                    "direction": "bearish",
                    "index": i,
                    "time": str(df.index[i]),
                    "strength": round(float(body / prev_body), 1),
                    "significance": "high"
                })

            # Doji (indecision)
            if body < total_range * 0.1 and total_range > 0:
                doji_type = "dragonfly" if lower_wick > upper_wick * 2 else \
                            "gravestone" if upper_wick > lower_wick * 2 else "standard"
                patterns.append({
                    "name": f"doji_{doji_type}",
                    "direction": "bullish" if doji_type == "dragonfly" else "bearish" if doji_type == "gravestone" else "neutral",
                    "index": i,
                    "time": str(df.index[i]),
                    "strength": 1.0,
                    "significance": "moderate"
                })

            # Morning Star (3-candle bullish reversal)
            if prev2 is not None:
                prev2_body = abs(prev2["close"] - prev2["open"])
                prev2_is_bullish = prev2["close"] > prev2["open"]

                if (not prev2_is_bullish and prev2_body > total_range * 0.5 and
                        prev_body < prev2_body * 0.3 and
                        is_bullish and body > prev2_body * 0.5):
                    patterns.append({
                        "name": "morning_star",
                        "direction": "bullish",
                        "index": i,
                        "time": str(df.index[i]),
                        "strength": 2.0,
                        "significance": "very_high"
                    })

                # Evening Star (3-candle bearish reversal)
                if (prev2_is_bullish and prev2_body > total_range * 0.5 and
                        prev_body < prev2_body * 0.3 and
                        not is_bullish and body > prev2_body * 0.5):
                    patterns.append({
                        "name": "evening_star",
                        "direction": "bearish",
                        "index": i,
                        "time": str(df.index[i]),
                        "strength": 2.0,
                        "significance": "very_high"
                    })

        return patterns[-10:]  # Last 10 patterns

    def _divergence_detection(self, df: pd.DataFrame) -> dict:
        """
        Detect RSI and MACD divergences:
        - Regular bullish: price lower low, RSI higher low
        - Regular bearish: price higher high, RSI lower high
        - Hidden bullish: price higher low, RSI lower low
        - Hidden bearish: price lower high, RSI higher high
        """
        if len(df) < 50:
            return {"divergences": []}

        # Calculate RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Calculate MACD
        ema_12 = df["close"].ewm(span=12).mean()
        ema_26 = df["close"].ewm(span=26).mean()
        macd = ema_12 - ema_26

        divergences = []

        # Look for divergences in last 50 bars
        prices = df["close"].values[-50:]
        rsi_vals = rsi.values[-50:]
        macd_vals = macd.values[-50:]

        # Find local extremes
        for lookback in [10, 20, 30]:
            if len(prices) <= lookback:
                continue

            recent_price = prices[-1]
            past_price = prices[-lookback]
            recent_rsi = rsi_vals[-1] if not np.isnan(rsi_vals[-1]) else 50
            past_rsi = rsi_vals[-lookback] if not np.isnan(rsi_vals[-lookback]) else 50
            recent_macd = macd_vals[-1] if not np.isnan(macd_vals[-1]) else 0
            past_macd = macd_vals[-lookback] if not np.isnan(macd_vals[-lookback]) else 0

            # Regular Bullish Divergence (RSI)
            if recent_price < past_price and recent_rsi > past_rsi and recent_rsi < 40:
                divergences.append({
                    "type": "regular_bullish",
                    "indicator": "RSI",
                    "lookback": lookback,
                    "strength": round(abs(recent_rsi - past_rsi), 1),
                    "signal": "bullish"
                })

            # Regular Bearish Divergence (RSI)
            if recent_price > past_price and recent_rsi < past_rsi and recent_rsi > 60:
                divergences.append({
                    "type": "regular_bearish",
                    "indicator": "RSI",
                    "lookback": lookback,
                    "strength": round(abs(recent_rsi - past_rsi), 1),
                    "signal": "bearish"
                })

            # Hidden Bullish (RSI)
            if recent_price > past_price and recent_rsi < past_rsi and recent_rsi < 50:
                divergences.append({
                    "type": "hidden_bullish",
                    "indicator": "RSI",
                    "lookback": lookback,
                    "strength": round(abs(recent_rsi - past_rsi), 1),
                    "signal": "bullish"
                })

            # Hidden Bearish (RSI)
            if recent_price < past_price and recent_rsi > past_rsi and recent_rsi > 50:
                divergences.append({
                    "type": "hidden_bearish",
                    "indicator": "RSI",
                    "lookback": lookback,
                    "strength": round(abs(recent_rsi - past_rsi), 1),
                    "signal": "bearish"
                })

            # MACD Divergences
            if recent_price < past_price and recent_macd > past_macd:
                divergences.append({
                    "type": "regular_bullish",
                    "indicator": "MACD",
                    "lookback": lookback,
                    "strength": round(abs(recent_macd - past_macd) * 10000, 1),
                    "signal": "bullish"
                })

            if recent_price > past_price and recent_macd < past_macd:
                divergences.append({
                    "type": "regular_bearish",
                    "indicator": "MACD",
                    "lookback": lookback,
                    "strength": round(abs(recent_macd - past_macd) * 10000, 1),
                    "signal": "bearish"
                })

        # Summarize
        bullish_divs = [d for d in divergences if d["signal"] == "bullish"]
        bearish_divs = [d for d in divergences if d["signal"] == "bearish"]

        if len(bullish_divs) >= 2:
            overall = "strong_bullish_divergence"
        elif len(bullish_divs) == 1:
            overall = "bullish_divergence"
        elif len(bearish_divs) >= 2:
            overall = "strong_bearish_divergence"
        elif len(bearish_divs) == 1:
            overall = "bearish_divergence"
        else:
            overall = "no_divergence"

        return {
            "overall": overall,
            "divergences": divergences[:5],
            "bullish_count": len(bullish_divs),
            "bearish_count": len(bearish_divs)
        }

    def _chart_patterns(self, df: pd.DataFrame) -> dict:
        """Detect chart patterns: double top/bottom, H&S"""
        if len(df) < 60:
            return {"pattern": None}

        highs = df["high"].values[-60:]
        lows = df["low"].values[-60:]
        closes = df["close"].values[-60:]

        patterns = []

        # Find peaks and troughs
        from scipy.signal import argrelextrema
        peaks = argrelextrema(highs, np.greater, order=5)[0]
        troughs = argrelextrema(lows, np.less, order=5)[0]

        # Double Top
        if len(peaks) >= 2:
            last_two_peaks = peaks[-2:]
            peak_prices = highs[last_two_peaks]
            if len(peak_prices) == 2:
                diff = abs(peak_prices[0] - peak_prices[1]) / peak_prices[0]
                if diff < 0.003:  # Within 0.3% = double top
                    neckline = np.min(lows[last_two_peaks[0]:last_two_peaks[1]])
                    if closes[-1] < neckline:
                        patterns.append({
                            "name": "double_top_confirmed",
                            "direction": "bearish",
                            "neckline": round(float(neckline), 5),
                            "target": round(float(neckline - (peak_prices[0] - neckline)), 5),
                            "significance": "high"
                        })
                    else:
                        patterns.append({
                            "name": "double_top_forming",
                            "direction": "bearish",
                            "neckline": round(float(neckline), 5),
                            "significance": "moderate"
                        })

        # Double Bottom
        if len(troughs) >= 2:
            last_two_troughs = troughs[-2:]
            trough_prices = lows[last_two_troughs]
            if len(trough_prices) == 2:
                diff = abs(trough_prices[0] - trough_prices[1]) / trough_prices[0]
                if diff < 0.003:
                    neckline = np.max(highs[last_two_troughs[0]:last_two_troughs[1]])
                    if closes[-1] > neckline:
                        patterns.append({
                            "name": "double_bottom_confirmed",
                            "direction": "bullish",
                            "neckline": round(float(neckline), 5),
                            "target": round(float(neckline + (neckline - trough_prices[0])), 5),
                            "significance": "high"
                        })
                    else:
                        patterns.append({
                            "name": "double_bottom_forming",
                            "direction": "bullish",
                            "neckline": round(float(neckline), 5),
                            "significance": "moderate"
                        })

        # Head and Shoulders
        if len(peaks) >= 3:
            last_three = peaks[-3:]
            p1, p2, p3 = highs[last_three[0]], highs[last_three[1]], highs[last_three[2]]
            if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.005:
                neckline = min(lows[last_three[0]:last_three[2]].min(), lows[-1])
                patterns.append({
                    "name": "head_and_shoulders",
                    "direction": "bearish",
                    "neckline": round(float(neckline), 5),
                    "head": round(float(p2), 5),
                    "significance": "very_high"
                })

        # Inverse Head and Shoulders
        if len(troughs) >= 3:
            last_three = troughs[-3:]
            t1, t2, t3 = lows[last_three[0]], lows[last_three[1]], lows[last_three[2]]
            if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.005:
                neckline = max(highs[last_three[0]:last_three[2]].max(), highs[-1])
                patterns.append({
                    "name": "inverse_head_and_shoulders",
                    "direction": "bullish",
                    "neckline": round(float(neckline), 5),
                    "head": round(float(t2), 5),
                    "significance": "very_high"
                })

        return {"patterns": patterns}

    def _key_reversal_patterns(self, df: pd.DataFrame) -> List[dict]:
        """Detect key reversal bars and patterns"""
        if len(df) < 10:
            return []

        reversals = []
        recent = df.tail(10)
        avg_range = (df["high"] - df["low"]).tail(50).mean()

        for i in range(1, len(recent)):
            curr = recent.iloc[i]
            prev = recent.iloc[i - 1]
            curr_range = curr["high"] - curr["low"]

            # Key Reversal Bar (bullish): new low then close above prev close
            if curr["low"] < prev["low"] and curr["close"] > prev["close"] and curr_range > avg_range * 1.5:
                reversals.append({
                    "type": "bullish_key_reversal",
                    "time": str(recent.index[i]),
                    "strength": round(float(curr_range / avg_range), 2)
                })

            # Key Reversal Bar (bearish): new high then close below prev close
            if curr["high"] > prev["high"] and curr["close"] < prev["close"] and curr_range > avg_range * 1.5:
                reversals.append({
                    "type": "bearish_key_reversal",
                    "time": str(recent.index[i]),
                    "strength": round(float(curr_range / avg_range), 2)
                })

        return reversals

    def _continuation_patterns(self, df: pd.DataFrame) -> dict:
        """Detect continuation patterns (flags, pennants)"""
        if len(df) < 30:
            return {"pattern": None}

        recent = df.tail(30)
        closes = recent["close"].values
        highs = recent["high"].values
        lows = recent["low"].values

        # Flag detection: strong impulse followed by tight consolidation
        first_10 = closes[:10]
        last_10 = closes[-10:]

        impulse = abs(first_10[-1] - first_10[0])
        consolidation_range = np.max(last_10) - np.min(last_10)
        avg_range = (df["high"] - df["low"]).tail(50).mean()

        if impulse > avg_range * 5 and consolidation_range < impulse * 0.38:
            direction = "bullish" if first_10[-1] > first_10[0] else "bearish"
            return {
                "pattern": f"{direction}_flag",
                "direction": direction,
                "impulse_size": round(float(impulse), 5),
                "consolidation_size": round(float(consolidation_range), 5),
                "target": round(float(closes[-1] + impulse if direction == "bullish" else closes[-1] - impulse), 5),
                "significance": "high"
            }

        return {"pattern": None}

    def _institutional_patterns(self, df: pd.DataFrame) -> dict:
        """
        Detect institutional entry patterns:
        - Spring (Wyckoff) - false break below support then strong reversal
        - Upthrust - false break above resistance then strong reversal
        - Three drives pattern
        """
        if len(df) < 30:
            return {"patterns": []}

        patterns = []
        recent = df.tail(30)
        closes = recent["close"].values
        highs = recent["high"].values
        lows = recent["low"].values

        # Spring: price dips below recent support then immediately reclaims
        support = np.min(lows[:20])
        for i in range(20, len(recent)):
            if lows[i] < support and closes[i] > support:
                patterns.append({
                    "name": "spring",
                    "direction": "bullish",
                    "level": round(float(support), 5),
                    "time": str(recent.index[i]),
                    "significance": "very_high"
                })

        # Upthrust: price spikes above resistance then immediately fails
        resistance = np.max(highs[:20])
        for i in range(20, len(recent)):
            if highs[i] > resistance and closes[i] < resistance:
                patterns.append({
                    "name": "upthrust",
                    "direction": "bearish",
                    "level": round(float(resistance), 5),
                    "time": str(recent.index[i]),
                    "significance": "very_high"
                })

        return {"patterns": patterns[-5:]}
