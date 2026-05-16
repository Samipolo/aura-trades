"""
AURA TRADES - Multi-Timeframe Alignment Engine
Analyzes structure alignment across 15M, 1H, 4H, and Daily timeframes.
True institutional edge comes from multi-TF confluence.

Key concept: Trade in the direction of the higher timeframe,
enter on the lower timeframe at premium/discount zones.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class MultiTimeframeEngine:
    """Multi-timeframe structure and trend alignment analysis"""

    def analyze(self, df_15m: pd.DataFrame) -> dict:
        """
        Analyze multiple timeframes by resampling 15m data.
        Returns alignment score and detailed breakdown.
        """
        if df_15m.empty or len(df_15m) < 500:
            return {"alignment": "insufficient_data", "score": 0}

        # Resample to higher timeframes
        df_1h = self._resample(df_15m, "1h")
        df_4h = self._resample(df_15m, "4h")

        # Analyze each timeframe
        tf_15m = self._analyze_timeframe(df_15m, "15M")
        tf_1h = self._analyze_timeframe(df_1h, "1H")
        tf_4h = self._analyze_timeframe(df_4h, "4H")

        # Calculate alignment
        alignment = self._calculate_alignment(tf_15m, tf_1h, tf_4h)

        # Premium/Discount zones from 4H
        pd_zones = self._premium_discount_zones(df_4h, df_15m)

        # Higher timeframe key levels
        htf_levels = self._htf_key_levels(df_1h, df_4h)

        return {
            "timeframes": {
                "15m": tf_15m,
                "1h": tf_1h,
                "4h": tf_4h
            },
            "alignment": alignment,
            "premium_discount": pd_zones,
            "htf_levels": htf_levels,
            "trade_direction": alignment["recommended_direction"],
            "mtf_score": alignment["score"]
        }

    def _resample(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample 15m data to higher timeframe"""
        try:
            resampled = df.resample(timeframe).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()
            return resampled
        except Exception:
            return pd.DataFrame()

    def _analyze_timeframe(self, df: pd.DataFrame, name: str) -> dict:
        """Analyze a single timeframe's trend and structure"""
        if df.empty or len(df) < 20:
            return {"name": name, "trend": "unknown", "strength": 0}

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        # EMA analysis
        ema_20 = self._ema(closes, 20)
        ema_50 = self._ema(closes, min(50, len(closes) - 1))

        current = closes[-1]
        trend_score = 0

        # Price vs EMAs
        if current > ema_20:
            trend_score += 1
        else:
            trend_score -= 1
        if current > ema_50:
            trend_score += 1
        else:
            trend_score -= 1
        if ema_20 > ema_50:
            trend_score += 1
        else:
            trend_score -= 1

        # Swing structure (last 20 bars)
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]

        # Higher highs / lower lows
        mid = len(recent_highs) // 2
        first_half_high = np.max(recent_highs[:mid])
        second_half_high = np.max(recent_highs[mid:])
        first_half_low = np.min(recent_lows[:mid])
        second_half_low = np.min(recent_lows[mid:])

        if second_half_high > first_half_high:
            trend_score += 1  # Higher highs
        else:
            trend_score -= 1
        if second_half_low > first_half_low:
            trend_score += 1  # Higher lows
        else:
            trend_score -= 1

        # Determine trend
        if trend_score >= 4:
            trend = "strong_bullish"
        elif trend_score >= 2:
            trend = "bullish"
        elif trend_score <= -4:
            trend = "strong_bearish"
        elif trend_score <= -2:
            trend = "bearish"
        else:
            trend = "neutral"

        # Candle position in range
        recent_range_high = np.max(highs[-20:])
        recent_range_low = np.min(lows[-20:])
        range_size = recent_range_high - recent_range_low
        position_in_range = (current - recent_range_low) / range_size if range_size > 0 else 0.5

        return {
            "name": name,
            "trend": trend,
            "trend_score": trend_score,
            "strength": abs(trend_score),
            "ema_20": round(float(ema_20), 5),
            "ema_50": round(float(ema_50), 5),
            "position_in_range": round(float(position_in_range), 3),
            "range_high": round(float(recent_range_high), 5),
            "range_low": round(float(recent_range_low), 5)
        }

    def _calculate_alignment(self, tf_15m: dict, tf_1h: dict, tf_4h: dict) -> dict:
        """
        Calculate multi-timeframe alignment score.
        Best trades have ALL timeframes aligned.
        """
        timeframes = [tf_15m, tf_1h, tf_4h]
        weights = [1, 3, 5]  # Higher TF = more weight

        bullish_score = 0
        bearish_score = 0
        total_weight = sum(weights)

        for tf, weight in zip(timeframes, weights):
            trend = tf.get("trend", "neutral")
            if "bullish" in trend:
                bullish_score += weight * (2 if "strong" in trend else 1)
            elif "bearish" in trend:
                bearish_score += weight * (2 if "strong" in trend else 1)

        max_possible = total_weight * 2  # All strong in one direction

        if bullish_score > bearish_score:
            direction = "bullish"
            score = (bullish_score / max_possible) * 100
        elif bearish_score > bullish_score:
            direction = "bearish"
            score = (bearish_score / max_possible) * 100
        else:
            direction = "neutral"
            score = 0

        # Alignment quality
        trends = [tf.get("trend", "neutral") for tf in timeframes]
        all_bullish = all("bullish" in t for t in trends)
        all_bearish = all("bearish" in t for t in trends)

        if all_bullish or all_bearish:
            quality = "perfect_alignment"
        elif sum("bullish" in t for t in trends) >= 3 or sum("bearish" in t for t in trends) >= 3:
            quality = "strong_alignment"
        elif sum("bullish" in t for t in trends) >= 2 or sum("bearish" in t for t in trends) >= 2:
            quality = "moderate_alignment"
        else:
            quality = "conflicting"

        return {
            "recommended_direction": direction,
            "score": round(score, 1),
            "quality": quality,
            "bullish_score": round(bullish_score, 1),
            "bearish_score": round(bearish_score, 1),
            "all_aligned": all_bullish or all_bearish
        }

    def _premium_discount_zones(self, df_htf: pd.DataFrame, df_15m: pd.DataFrame) -> dict:
        """
        Identify premium and discount zones from higher timeframe range.
        Premium zone (>61.8% of range) = look for shorts
        Discount zone (<38.2% of range) = look for longs
        Equilibrium (around 50%) = avoid
        """
        if df_htf.empty or len(df_htf) < 5:
            return {"zone": "unknown", "fib_level": 0.5}

        # Use recent 4H range
        recent_high = float(df_htf["high"].tail(20).max())
        recent_low = float(df_htf["low"].tail(20).min())
        current_price = float(df_15m["close"].iloc[-1])

        range_size = recent_high - recent_low
        if range_size == 0:
            return {"zone": "unknown", "fib_level": 0.5}

        position = (current_price - recent_low) / range_size

        # Fibonacci levels
        fib_levels = {
            "0.0": recent_low,
            "0.236": recent_low + range_size * 0.236,
            "0.382": recent_low + range_size * 0.382,
            "0.5": recent_low + range_size * 0.5,
            "0.618": recent_low + range_size * 0.618,
            "0.786": recent_low + range_size * 0.786,
            "1.0": recent_high,
        }

        # OTE (Optimal Trade Entry) zone = 0.618-0.786 retracement
        if position > 0.786:
            zone = "extreme_premium"
            signal = "short"
        elif position > 0.618:
            zone = "premium"
            signal = "short"
        elif position > 0.5:
            zone = "slight_premium"
            signal = "neutral"
        elif position > 0.382:
            zone = "slight_discount"
            signal = "neutral"
        elif position > 0.236:
            zone = "discount"
            signal = "long"
        else:
            zone = "extreme_discount"
            signal = "long"

        # OTE zone for entries
        in_ote_long = 0.618 <= (1 - position) <= 0.786  # Discount OTE
        in_ote_short = 0.618 <= position <= 0.786  # Premium OTE

        return {
            "zone": zone,
            "signal": signal,
            "position": round(position, 4),
            "fib_levels": {k: round(v, 5) for k, v in fib_levels.items()},
            "in_ote_long": in_ote_long,
            "in_ote_short": in_ote_short,
            "range_high": recent_high,
            "range_low": recent_low
        }

    def _htf_key_levels(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> dict:
        """Extract key levels from higher timeframes"""
        levels = {"support": [], "resistance": []}

        for df, tf_name in [(df_1h, "1H"), (df_4h, "4H")]:
            if df.empty or len(df) < 10:
                continue

            # Find swing highs/lows on HTF
            for i in range(2, min(len(df) - 2, 30)):
                if df["high"].iloc[i] >= df["high"].iloc[i-1] and df["high"].iloc[i] >= df["high"].iloc[i+1]:
                    if df["high"].iloc[i] >= df["high"].iloc[i-2] and df["high"].iloc[i] >= df["high"].iloc[i+2]:
                        levels["resistance"].append({
                            "price": round(float(df["high"].iloc[i]), 5),
                            "timeframe": tf_name,
                            "type": "swing_high"
                        })

                if df["low"].iloc[i] <= df["low"].iloc[i-1] and df["low"].iloc[i] <= df["low"].iloc[i+1]:
                    if df["low"].iloc[i] <= df["low"].iloc[i-2] and df["low"].iloc[i] <= df["low"].iloc[i+2]:
                        levels["support"].append({
                            "price": round(float(df["low"].iloc[i]), 5),
                            "timeframe": tf_name,
                            "type": "swing_low"
                        })

        # Keep only recent significant levels
        levels["resistance"] = sorted(levels["resistance"], key=lambda x: x["price"], reverse=True)[:5]
        levels["support"] = sorted(levels["support"], key=lambda x: x["price"])[:5]

        return levels

    def _ema(self, data: np.ndarray, period: int) -> float:
        """Calculate EMA and return last value"""
        if len(data) < period:
            return float(data[-1])
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price - ema) * multiplier + ema
        return float(ema)
