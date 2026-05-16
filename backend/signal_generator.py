"""
AURA TRADES - Trade Signal Generator
Generates trade signals with 1:2 Risk:Reward using confluence of all analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config import INDICATOR_CONFIG, INSTRUMENT_NAMES


class SignalGenerator:
    """Generates ranked trade signals based on multi-factor confluence"""

    def __init__(self):
        self.risk_reward = INDICATOR_CONFIG["risk_reward_ratio"]

    def generate_signal(self, symbol: str, indicator_data: dict, structure_data: dict,
                        correlation_score: float, all_data: Dict[str, pd.DataFrame] = None) -> Optional[dict]:
        """Generate a trade signal for a single instrument"""
        if not indicator_data or not structure_data:
            return None

        df = indicator_data.get("df")
        levels = indicator_data.get("levels", {})
        signals = indicator_data.get("signals", {})

        if df is None or df.empty or len(df) < 200:
            return None

        current = df.iloc[-1]
        current_price = float(current["close"])
        atr = float(current.get("atr", 0))

        if atr == 0 or pd.isna(atr):
            return None

        # Collect all confluence factors
        bullish_factors = []
        bearish_factors = []

        # 1. Trend Analysis (EMA 50/200)
        trend = signals.get("trend", "neutral")
        if trend in ["strong_bullish", "bullish"]:
            bullish_factors.append(("trend", 20 if trend == "strong_bullish" else 15))
        elif trend in ["strong_bearish", "bearish"]:
            bearish_factors.append(("trend", 20 if trend == "strong_bearish" else 15))

        # 2. Market Structure
        bias = structure_data.get("bias", "neutral")
        if bias == "bullish":
            bullish_factors.append(("market_structure", 20))
        elif bias == "bearish":
            bearish_factors.append(("market_structure", 20))

        # 3. BOS / CHoCH
        structure = structure_data.get("structure", {})
        bos = structure.get("bos")
        choch = structure.get("choch")
        if choch:
            if choch["direction"] == "bullish":
                bullish_factors.append(("choch", 15))
            else:
                bearish_factors.append(("choch", 15))
        elif bos:
            if bos["direction"] == "bullish":
                bullish_factors.append(("bos", 10))
            else:
                bearish_factors.append(("bos", 10))

        # 4. VWAP Analysis
        vwap_score = self._analyze_vwap(current_price, levels)
        if vwap_score > 0:
            bullish_factors.append(("vwap_confluence", vwap_score))
        elif vwap_score < 0:
            bearish_factors.append(("vwap_confluence", abs(vwap_score)))

        # 5. Volume Profile (POC proximity)
        vpoc_score = self._analyze_volume_profile(current_price, levels, atr)
        if vpoc_score > 0:
            bullish_factors.append(("volume_profile", vpoc_score))
        elif vpoc_score < 0:
            bearish_factors.append(("volume_profile", abs(vpoc_score)))

        # 6. Bollinger Bands
        bb_score = self._analyze_bollinger(current, df)
        if bb_score > 0:
            bullish_factors.append(("bollinger_bands", bb_score))
        elif bb_score < 0:
            bearish_factors.append(("bollinger_bands", abs(bb_score)))

        # 7. Momentum (RSI + MACD)
        momentum = signals.get("momentum", "neutral")
        if momentum == "bullish":
            bullish_factors.append(("momentum", 10))
        elif momentum == "bearish":
            bearish_factors.append(("momentum", 10))
        elif momentum == "oversold":
            bullish_factors.append(("oversold_bounce", 12))
        elif momentum == "overbought":
            bearish_factors.append(("overbought_reversal", 12))

        # 8. Order Blocks
        ob_score = self._analyze_order_blocks(current_price, structure_data.get("order_blocks", []), atr)
        if ob_score > 0:
            bullish_factors.append(("order_block", ob_score))
        elif ob_score < 0:
            bearish_factors.append(("order_block", abs(ob_score)))

        # 9. Fair Value Gaps
        fvg_score = self._analyze_fvgs(current_price, structure_data.get("fair_value_gaps", []), atr)
        if fvg_score > 0:
            bullish_factors.append(("fair_value_gap", fvg_score))
        elif fvg_score < 0:
            bearish_factors.append(("fair_value_gap", abs(fvg_score)))

        # 10. Initial Balance
        ib_score = self._analyze_initial_balance(current_price, levels.get("session_ib", {}), atr)
        if ib_score > 0:
            bullish_factors.append(("initial_balance", ib_score))
        elif ib_score < 0:
            bearish_factors.append(("initial_balance", abs(ib_score)))

        # 11. Correlation
        if correlation_score > 65:
            bullish_factors.append(("correlation", int((correlation_score - 50) * 0.3)))
            bearish_factors.append(("correlation", int((correlation_score - 50) * 0.3)))
        elif correlation_score < 35:
            pass  # Contradicting correlations reduce confidence

        # 12. Volatility
        volatility = signals.get("volatility", "normal")
        if volatility == "low_squeeze":
            # BB squeeze - big move incoming
            bullish_factors.append(("bb_squeeze", 5))
            bearish_factors.append(("bb_squeeze", 5))

        # Calculate total scores
        bull_score = sum(s for _, s in bullish_factors)
        bear_score = sum(s for _, s in bearish_factors)

        # Minimum threshold for a trade
        min_score = 40

        if bull_score < min_score and bear_score < min_score:
            return None

        # Determine direction
        if bull_score > bear_score and bull_score >= min_score:
            direction = "LONG"
            score = bull_score
            factors = bullish_factors
        elif bear_score > bull_score and bear_score >= min_score:
            direction = "SHORT"
            score = bear_score
            factors = bearish_factors
        else:
            return None

        # Calculate entry, SL, TP with 1:2 R:R
        entry, sl, tp = self._calculate_levels(current_price, direction, atr, levels, structure_data)

        # Confidence score (0-100)
        confidence = min(100, score)

        # Adjust confidence based on correlation
        confidence = confidence * (correlation_score / 100) if correlation_score < 50 else confidence

        return {
            "symbol": symbol,
            "display_name": INSTRUMENT_NAMES.get(symbol, symbol),
            "direction": direction,
            "entry": round(entry, 5),
            "stop_loss": round(sl, 5),
            "take_profit": round(tp, 5),
            "risk_reward": self.risk_reward,
            "confidence": round(confidence, 1),
            "score": score,
            "factors": [{"name": name, "score": s} for name, s in factors],
            "trend": trend,
            "momentum": momentum,
            "volatility": volatility,
            "market_structure": bias,
            "correlation_score": round(correlation_score, 1),
            "current_price": current_price,
            "atr": round(atr, 5),
            "timestamp": str(df.index[-1]),
        }

    def _analyze_vwap(self, price: float, levels: dict) -> int:
        """Score VWAP position"""
        score = 0
        daily_vwap = levels.get("daily_vwap", {}).get("value")
        weekly_vwap = levels.get("weekly_vwap", {}).get("value")
        monthly_vwap = levels.get("monthly_vwap", {}).get("value")
        prev_day_vwap = levels.get("prev_day_vwap", {}).get("value")
        prev_week_vwap = levels.get("prev_week_vwap", {}).get("value")

        # Price above/below VWAPs = trend confirmation
        if daily_vwap and daily_vwap > 0:
            if price > daily_vwap:
                score += 3
            else:
                score -= 3

        if weekly_vwap and weekly_vwap > 0:
            if price > weekly_vwap:
                score += 4
            else:
                score -= 4

        if monthly_vwap and monthly_vwap > 0:
            if price > monthly_vwap:
                score += 5
            else:
                score -= 5

        if prev_day_vwap and prev_day_vwap > 0:
            if price > prev_day_vwap:
                score += 2
            else:
                score -= 2

        if prev_week_vwap and prev_week_vwap > 0:
            if price > prev_week_vwap:
                score += 3
            else:
                score -= 3

        return score

    def _analyze_volume_profile(self, price: float, levels: dict, atr: float) -> int:
        """Score based on volume profile levels"""
        score = 0

        daily_vpoc = levels.get("daily_vpoc", {}).get("poc")
        daily_vah = levels.get("daily_vpoc", {}).get("vah")
        daily_val = levels.get("daily_vpoc", {}).get("val")

        if daily_vpoc and atr > 0:
            distance_to_poc = abs(price - daily_vpoc) / atr

            # Near POC = strong reference
            if distance_to_poc < 0.5:
                # At POC, look for rejection direction
                if price > daily_vpoc:
                    score += 5
                else:
                    score -= 5
            elif price > daily_vpoc:
                score += 3
            else:
                score -= 3

        # Value Area analysis
        if daily_vah and daily_val:
            if price > daily_vah:
                score += 4  # Above value = bullish
            elif price < daily_val:
                score -= 4  # Below value = bearish

        return score

    def _analyze_bollinger(self, current: pd.Series, df: pd.DataFrame) -> int:
        """Analyze Bollinger Band position"""
        score = 0
        bb_upper = current.get("bb_upper")
        bb_lower = current.get("bb_lower")
        bb_mid = current.get("bb_mid")
        close = current["close"]

        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return 0

        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0

        # Position within bands (0=lower, 1=upper)
        position = (close - bb_lower) / bb_range

        if position > 0.9:
            score -= 8  # Near upper = potential reversal down
        elif position < 0.1:
            score += 8  # Near lower = potential reversal up
        elif position > 0.5:
            score += 3  # Upper half = mild bullish
        else:
            score -= 3  # Lower half = mild bearish

        # BB squeeze detection
        bb_width = current.get("bb_width", 0)
        if not pd.isna(bb_width):
            avg_width = df["bb_width"].rolling(50).mean().iloc[-1]
            if not pd.isna(avg_width) and bb_width < avg_width * 0.5:
                # Squeeze - amplify whatever direction we're leaning
                score = int(score * 1.5)

        return score

    def _analyze_order_blocks(self, price: float, order_blocks: List[dict], atr: float) -> int:
        """Score based on proximity to order blocks"""
        score = 0
        for ob in order_blocks:
            distance = abs(price - (ob["high"] + ob["low"]) / 2) / atr if atr > 0 else float('inf')
            if distance < 1.5:  # Within 1.5 ATR
                if ob["type"] == "bullish" and price >= ob["low"] and price <= ob["high"]:
                    score += 10  # At bullish OB
                elif ob["type"] == "bearish" and price >= ob["low"] and price <= ob["high"]:
                    score -= 10  # At bearish OB
                elif ob["type"] == "bullish" and price > ob["high"]:
                    score += 5
                elif ob["type"] == "bearish" and price < ob["low"]:
                    score -= 5
        return score

    def _analyze_fvgs(self, price: float, fvgs: List[dict], atr: float) -> int:
        """Score based on Fair Value Gap proximity"""
        score = 0
        for fvg in fvgs:
            if fvg["type"] == "bullish" and price >= fvg["low"] and price <= fvg["high"]:
                score += 8  # Price filling bullish FVG = support
            elif fvg["type"] == "bearish" and price >= fvg["low"] and price <= fvg["high"]:
                score -= 8  # Price filling bearish FVG = resistance
        return score

    def _analyze_initial_balance(self, price: float, ib: dict, atr: float) -> int:
        """Score based on Initial Balance breakout"""
        score = 0
        ib_high = ib.get("high")
        ib_low = ib.get("low")

        if ib_high is None or ib_low is None:
            return 0

        if price > ib_high:
            score += 7  # IB breakout bullish
        elif price < ib_low:
            score -= 7  # IB breakout bearish
        else:
            # Inside IB - look for range trade
            ib_mid = (ib_high + ib_low) / 2
            if price > ib_mid:
                score += 2
            else:
                score -= 2

        return score

    def _calculate_levels(self, price: float, direction: str, atr: float,
                          levels: dict, structure_data: dict) -> tuple:
        """Calculate entry, stop loss, and take profit with 1:2 R:R"""
        # Use ATR-based stop loss (1.5x ATR)
        sl_distance = atr * 1.5

        # Look for structural levels for SL placement
        structure = structure_data.get("structure", {})
        last_high = structure.get("last_swing_high")
        last_low = structure.get("last_swing_low")

        if direction == "LONG":
            entry = price
            # Place SL below swing low or ATR-based, whichever is tighter
            if last_low and (price - last_low) < sl_distance * 2 and (price - last_low) > 0:
                sl = last_low - (atr * 0.2)  # Just below swing low
            else:
                sl = price - sl_distance

            risk = entry - sl
            tp = entry + (risk * self.risk_reward)  # 1:2 R:R

        else:  # SHORT
            entry = price
            if last_high and (last_high - price) < sl_distance * 2 and (last_high - price) > 0:
                sl = last_high + (atr * 0.2)  # Just above swing high
            else:
                sl = price + sl_distance

            risk = sl - entry
            tp = entry - (risk * self.risk_reward)  # 1:2 R:R

        return entry, sl, tp


class TradeRanker:
    """Ranks trade signals by quality"""

    def rank_signals(self, signals: List[dict]) -> List[dict]:
        """Rank signals from best to worst based on multi-factor scoring"""
        if not signals:
            return []

        for signal in signals:
            signal["rank_score"] = self._calculate_rank_score(signal)

        # Sort by rank score descending
        ranked = sorted(signals, key=lambda x: x["rank_score"], reverse=True)

        # Assign rank numbers
        for i, signal in enumerate(ranked):
            signal["rank"] = i + 1

        return ranked

    def _calculate_rank_score(self, signal: dict) -> float:
        """Calculate composite ranking score"""
        score = 0.0

        # Base confidence (40% weight)
        score += signal.get("confidence", 0) * 0.4

        # Number of confluent factors (20% weight)
        num_factors = len(signal.get("factors", []))
        score += min(num_factors * 3, 20)

        # Correlation alignment (15% weight)
        corr_score = signal.get("correlation_score", 50)
        score += (corr_score / 100) * 15

        # Market structure clarity (15% weight)
        structure = signal.get("market_structure", "neutral")
        if structure in ["bullish", "bearish"]:
            score += 15
        elif structure == "neutral":
            score += 5

        # Volatility favorability (10% weight)
        vol = signal.get("volatility", "normal")
        if vol == "normal":
            score += 10
        elif vol == "low_squeeze":
            score += 8
        elif vol == "high":
            score += 4  # High vol = higher risk

        return score
