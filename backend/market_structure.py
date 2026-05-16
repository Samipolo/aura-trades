"""
AURA TRADES - Market Structure & Order Flow Analysis
Identifies swing highs/lows, BOS, CHoCH, liquidity zones, and order blocks
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple


class MarketStructureAnalyzer:
    """Analyzes market structure: swing points, BOS, CHoCH, order blocks"""

    def __init__(self, swing_lookback: int = 5):
        self.swing_lookback = swing_lookback

    def analyze(self, df: pd.DataFrame) -> dict:
        """Full market structure analysis"""
        if df.empty or len(df) < 50:
            return {}

        swing_highs, swing_lows = self._find_swing_points(df)
        structure = self._determine_structure(swing_highs, swing_lows, df)
        order_blocks = self._find_order_blocks(df, swing_highs, swing_lows)
        liquidity_zones = self._find_liquidity_zones(df, swing_highs, swing_lows)
        fvgs = self._find_fair_value_gaps(df)

        return {
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "structure": structure,
            "order_blocks": order_blocks,
            "liquidity_zones": liquidity_zones,
            "fair_value_gaps": fvgs,
            "bias": self._determine_bias(structure, df)
        }

    def _find_swing_points(self, df: pd.DataFrame) -> Tuple[List[dict], List[dict]]:
        """Identify swing highs and swing lows"""
        swing_highs = []
        swing_lows = []
        lookback = self.swing_lookback

        for i in range(lookback, len(df) - lookback):
            # Swing High
            if df["high"].iloc[i] == df["high"].iloc[i - lookback:i + lookback + 1].max():
                swing_highs.append({
                    "index": i,
                    "price": float(df["high"].iloc[i]),
                    "time": str(df.index[i])
                })

            # Swing Low
            if df["low"].iloc[i] == df["low"].iloc[i - lookback:i + lookback + 1].min():
                swing_lows.append({
                    "index": i,
                    "price": float(df["low"].iloc[i]),
                    "time": str(df.index[i])
                })

        return swing_highs, swing_lows

    def _determine_structure(self, swing_highs: List[dict], swing_lows: List[dict], df: pd.DataFrame) -> dict:
        """Determine market structure - BOS, CHoCH, HH/HL/LH/LL"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"type": "undefined", "events": []}

        events = []
        current_price = float(df["close"].iloc[-1])

        # Check for Higher Highs / Lower Lows pattern
        recent_highs = swing_highs[-4:]
        recent_lows = swing_lows[-4:]

        hh_count = 0
        ll_count = 0

        for i in range(1, len(recent_highs)):
            if recent_highs[i]["price"] > recent_highs[i - 1]["price"]:
                hh_count += 1
                events.append({"type": "HH", "price": recent_highs[i]["price"], "time": recent_highs[i]["time"]})
            else:
                events.append({"type": "LH", "price": recent_highs[i]["price"], "time": recent_highs[i]["time"]})

        for i in range(1, len(recent_lows)):
            if recent_lows[i]["price"] > recent_lows[i - 1]["price"]:
                events.append({"type": "HL", "price": recent_lows[i]["price"], "time": recent_lows[i]["time"]})
            else:
                ll_count += 1
                events.append({"type": "LL", "price": recent_lows[i]["price"], "time": recent_lows[i]["time"]})

        # BOS (Break of Structure)
        last_high = swing_highs[-1]["price"] if swing_highs else None
        last_low = swing_lows[-1]["price"] if swing_lows else None
        prev_high = swing_highs[-2]["price"] if len(swing_highs) >= 2 else None
        prev_low = swing_lows[-2]["price"] if len(swing_lows) >= 2 else None

        bos = None
        choch = None

        if prev_high and current_price > prev_high:
            bos = {"direction": "bullish", "level": prev_high}
        elif prev_low and current_price < prev_low:
            bos = {"direction": "bearish", "level": prev_low}

        # CHoCH (Change of Character)
        if hh_count >= 2 and last_low and current_price < last_low:
            choch = {"direction": "bearish", "level": last_low}
        elif ll_count >= 2 and last_high and current_price > last_high:
            choch = {"direction": "bullish", "level": last_high}

        # Determine overall structure type
        if hh_count >= 2:
            structure_type = "bullish"
        elif ll_count >= 2:
            structure_type = "bearish"
        else:
            structure_type = "ranging"

        return {
            "type": structure_type,
            "events": events,
            "bos": bos,
            "choch": choch,
            "last_swing_high": last_high,
            "last_swing_low": last_low
        }

    def _find_order_blocks(self, df: pd.DataFrame, swing_highs: List[dict], swing_lows: List[dict]) -> List[dict]:
        """Find bullish and bearish order blocks"""
        order_blocks = []

        # Bullish OB: last bearish candle before strong bullish move
        for i in range(3, len(df) - 1):
            # Strong bullish move (>1.5x ATR)
            if len(df) > 14:
                atr = (df["high"] - df["low"]).rolling(14).mean().iloc[i]
                if pd.isna(atr) or atr == 0:
                    continue

                move = df["close"].iloc[i] - df["open"].iloc[i]
                if move > atr * 1.5:
                    # Find last bearish candle before
                    for j in range(i - 1, max(i - 5, 0), -1):
                        if df["close"].iloc[j] < df["open"].iloc[j]:
                            order_blocks.append({
                                "type": "bullish",
                                "high": float(df["high"].iloc[j]),
                                "low": float(df["low"].iloc[j]),
                                "index": j,
                                "time": str(df.index[j]),
                                "mitigated": float(df["low"].iloc[i:].min()) <= float(df["low"].iloc[j])
                            })
                            break

                # Strong bearish move
                if move < -atr * 1.5:
                    for j in range(i - 1, max(i - 5, 0), -1):
                        if df["close"].iloc[j] > df["open"].iloc[j]:
                            order_blocks.append({
                                "type": "bearish",
                                "high": float(df["high"].iloc[j]),
                                "low": float(df["low"].iloc[j]),
                                "index": j,
                                "time": str(df.index[j]),
                                "mitigated": float(df["high"].iloc[i:].max()) >= float(df["high"].iloc[j])
                            })
                            break

        # Return only unmitigated recent order blocks
        unmitigated = [ob for ob in order_blocks if not ob["mitigated"]]
        return unmitigated[-10:]  # Last 10 unmitigated OBs

    def _find_liquidity_zones(self, df: pd.DataFrame, swing_highs: List[dict], swing_lows: List[dict]) -> List[dict]:
        """Find areas of liquidity (equal highs/lows, stop clusters)"""
        liquidity = []

        # Equal highs (buy-side liquidity)
        for i in range(len(swing_highs)):
            for j in range(i + 1, len(swing_highs)):
                diff = abs(swing_highs[i]["price"] - swing_highs[j]["price"])
                avg = (swing_highs[i]["price"] + swing_highs[j]["price"]) / 2
                if avg > 0 and diff / avg < 0.001:  # Within 0.1%
                    liquidity.append({
                        "type": "buy_side",
                        "price": avg,
                        "strength": 2,
                        "description": "Equal Highs - Buy Side Liquidity"
                    })

        # Equal lows (sell-side liquidity)
        for i in range(len(swing_lows)):
            for j in range(i + 1, len(swing_lows)):
                diff = abs(swing_lows[i]["price"] - swing_lows[j]["price"])
                avg = (swing_lows[i]["price"] + swing_lows[j]["price"]) / 2
                if avg > 0 and diff / avg < 0.001:
                    liquidity.append({
                        "type": "sell_side",
                        "price": avg,
                        "strength": 2,
                        "description": "Equal Lows - Sell Side Liquidity"
                    })

        return liquidity[-10:]

    def _find_fair_value_gaps(self, df: pd.DataFrame) -> List[dict]:
        """Find Fair Value Gaps (imbalances)"""
        fvgs = []

        for i in range(2, len(df)):
            # Bullish FVG: candle[i] low > candle[i-2] high
            if df["low"].iloc[i] > df["high"].iloc[i - 2]:
                fvgs.append({
                    "type": "bullish",
                    "high": float(df["low"].iloc[i]),
                    "low": float(df["high"].iloc[i - 2]),
                    "index": i - 1,
                    "time": str(df.index[i - 1]),
                    "filled": float(df["low"].iloc[i:].min()) <= float(df["high"].iloc[i - 2])
                })

            # Bearish FVG: candle[i] high < candle[i-2] low
            if df["high"].iloc[i] < df["low"].iloc[i - 2]:
                fvgs.append({
                    "type": "bearish",
                    "high": float(df["low"].iloc[i - 2]),
                    "low": float(df["high"].iloc[i]),
                    "index": i - 1,
                    "time": str(df.index[i - 1]),
                    "filled": float(df["high"].iloc[i:].max()) >= float(df["low"].iloc[i - 2])
                })

        # Return unfilled recent FVGs
        unfilled = [fvg for fvg in fvgs if not fvg["filled"]]
        return unfilled[-10:]

    def _determine_bias(self, structure: dict, df: pd.DataFrame) -> str:
        """Determine overall directional bias"""
        if not structure or structure.get("type") == "undefined":
            return "neutral"

        struct_type = structure.get("type", "ranging")
        choch = structure.get("choch")

        if choch:
            return choch["direction"]

        return struct_type if struct_type in ["bullish", "bearish"] else "neutral"
