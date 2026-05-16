"""
AURA TRADES - Advanced Order Flow Engine
Deep order flow analysis from price action:
- Delta Analysis (buyer/seller aggression from candles)
- Absorption Detection (large volume with no movement)
- Stop Hunt / Liquidity Sweep Detection
- Wyckoff Phase Analysis (Accumulation/Distribution/Markup/Markdown)
- Institutional Footprint (large candle analysis)
- Exhaustion Volume Detection
- Effort vs Result Analysis
- Supply/Demand Zone Scoring
- Trapped Trader Detection
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class OrderFlowEngine:
    """Advanced order flow analysis from candle data"""

    def analyze(self, df: pd.DataFrame) -> dict:
        """Full order flow analysis"""
        if df.empty or len(df) < 100:
            return {}

        return {
            "delta": self._delta_analysis(df),
            "absorption": self._absorption_detection(df),
            "stop_hunts": self._stop_hunt_detection(df),
            "wyckoff": self._wyckoff_phase(df),
            "institutional_prints": self._institutional_footprint(df),
            "exhaustion": self._exhaustion_detection(df),
            "effort_result": self._effort_vs_result(df),
            "supply_demand": self._supply_demand_zones(df),
            "trapped_traders": self._trapped_trader_detection(df),
            "aggression": self._aggression_analysis(df),
            "composite_score": 0  # Calculated at end
        }

    def _delta_analysis(self, df: pd.DataFrame) -> dict:
        """
        Estimate buying/selling pressure from candle structure
        Delta = (Close - Low) - (High - Close) normalized by range
        Cumulative delta shows underlying order flow direction
        """
        recent = df.tail(50).copy()
        ranges = recent["high"] - recent["low"]
        ranges = ranges.replace(0, np.nan)

        # Bar delta: positive = buyers aggressive, negative = sellers
        buying_pressure = (recent["close"] - recent["low"]) / ranges
        selling_pressure = (recent["high"] - recent["close"]) / ranges
        bar_delta = buying_pressure - selling_pressure

        # Cumulative delta
        cumulative_delta = bar_delta.cumsum()

        # Delta divergence: price making new high but delta not
        price_trend = recent["close"].iloc[-1] > recent["close"].iloc[-20]
        delta_trend = cumulative_delta.iloc[-1] > cumulative_delta.iloc[-20]

        divergence = None
        if price_trend and not delta_trend:
            divergence = "bearish_divergence"
        elif not price_trend and delta_trend:
            divergence = "bullish_divergence"

        # Current delta momentum
        recent_delta = float(bar_delta.tail(5).mean())
        if recent_delta > 0.3:
            momentum = "strong_buyers"
        elif recent_delta > 0.1:
            momentum = "moderate_buyers"
        elif recent_delta < -0.3:
            momentum = "strong_sellers"
        elif recent_delta < -0.1:
            momentum = "moderate_sellers"
        else:
            momentum = "balanced"

        return {
            "current_delta": round(float(bar_delta.iloc[-1]), 3),
            "cumulative_delta": round(float(cumulative_delta.iloc[-1]), 3),
            "momentum": momentum,
            "divergence": divergence,
            "delta_5bar": round(recent_delta, 3),
            "score": round(abs(recent_delta) * 100, 1)
        }

    def _absorption_detection(self, df: pd.DataFrame) -> dict:
        """
        Detect absorption: high volume but price doesn't move much
        Indicates large orders absorbing opposing flow
        """
        recent = df.tail(30).copy()
        volumes = recent["volume"]
        ranges = recent["high"] - recent["low"]
        bodies = abs(recent["close"] - recent["open"])

        if volumes.sum() == 0:
            # For forex with no volume, use range as proxy
            volumes = ranges

        avg_vol = volumes.mean()
        avg_range = ranges.mean()

        absorptions = []
        for i in range(len(recent)):
            vol = volumes.iloc[i]
            rng = ranges.iloc[i]
            body = bodies.iloc[i]

            # High volume + small range = absorption
            if avg_vol > 0 and avg_range > 0:
                vol_ratio = vol / avg_vol
                range_ratio = rng / avg_range if avg_range > 0 else 1

                if vol_ratio > 1.5 and range_ratio < 0.5:
                    absorptions.append({
                        "index": i,
                        "type": "bullish" if recent["close"].iloc[i] > recent["open"].iloc[i] else "bearish",
                        "strength": round(float(vol_ratio / range_ratio), 2)
                    })

        # Recent absorption signal
        recent_absorption = None
        if absorptions and absorptions[-1]["index"] >= len(recent) - 5:
            recent_absorption = absorptions[-1]["type"]

        return {
            "count": len(absorptions),
            "recent_signal": recent_absorption,
            "absorptions": absorptions[-3:],
            "implication": f"{'Bullish' if recent_absorption == 'bullish' else 'Bearish' if recent_absorption == 'bearish' else 'No'} absorption detected"
        }

    def _stop_hunt_detection(self, df: pd.DataFrame) -> dict:
        """
        Detect stop hunts / liquidity sweeps:
        - Price spikes beyond a level then quickly reverses
        - Long wick beyond swing point with close back inside range
        """
        if len(df) < 50:
            return {"detected": False, "events": []}

        recent = df.tail(50)
        events = []

        # Find swing points in recent data
        for i in range(5, len(recent) - 1):
            # Check for upside stop hunt (spike high, close low)
            high = recent["high"].iloc[i]
            close = recent["close"].iloc[i]
            open_p = recent["open"].iloc[i]
            prev_high = recent["high"].iloc[i-5:i].max()

            upper_wick = high - max(close, open_p)
            body = abs(close - open_p)
            total_range = recent["high"].iloc[i] - recent["low"].iloc[i]

            if total_range > 0:
                # Upside stop hunt: high exceeds previous highs, long upper wick, close below
                if high > prev_high and upper_wick > body * 1.5 and close < open_p:
                    events.append({
                        "type": "sell_side_sweep",
                        "price": float(high),
                        "index": i,
                        "time": str(recent.index[i]),
                        "implication": "Sellers swept stops above - bearish"
                    })

                # Downside stop hunt
                low = recent["low"].iloc[i]
                prev_low = recent["low"].iloc[i-5:i].min()
                lower_wick = min(close, open_p) - low

                if low < prev_low and lower_wick > body * 1.5 and close > open_p:
                    events.append({
                        "type": "buy_side_sweep",
                        "price": float(low),
                        "index": i,
                        "time": str(recent.index[i]),
                        "implication": "Buyers swept stops below - bullish"
                    })

        # Check if recent (last 3 bars) had a stop hunt
        recent_hunt = None
        for event in events:
            if event["index"] >= len(recent) - 3:
                recent_hunt = event

        return {
            "detected": recent_hunt is not None,
            "recent_event": recent_hunt,
            "total_events": len(events),
            "events": events[-5:]
        }

    def _wyckoff_phase(self, df: pd.DataFrame) -> dict:
        """
        Wyckoff Market Cycle Phase Detection:
        - Accumulation (smart money buying)
        - Markup (trending up)
        - Distribution (smart money selling)
        - Markdown (trending down)
        """
        if len(df) < 100:
            return {"phase": "unknown", "confidence": 0}

        recent = df.tail(100)
        prices = recent["close"].values
        volumes = recent["volume"].values if recent["volume"].sum() > 0 else np.ones(len(recent))

        # Calculate key metrics
        price_range = prices.max() - prices.min()
        price_position = (prices[-1] - prices.min()) / price_range if price_range > 0 else 0.5

        # Trend: first half vs second half
        first_half_avg = np.mean(prices[:50])
        second_half_avg = np.mean(prices[50:])
        trend = (second_half_avg - first_half_avg) / first_half_avg

        # Volume pattern
        first_half_vol = np.mean(volumes[:50])
        second_half_vol = np.mean(volumes[50:])
        vol_trend = second_half_vol / first_half_vol if first_half_vol > 0 else 1

        # Range contraction/expansion
        first_half_range = np.std(prices[:50])
        second_half_range = np.std(prices[50:])
        range_trend = second_half_range / first_half_range if first_half_range > 0 else 1

        # Determine phase
        if trend < -0.005 and range_trend < 0.8 and price_position < 0.3:
            phase = "accumulation"
            confidence = min(100, int((0.3 - price_position) * 200 + (1 - range_trend) * 50))
            signal = "bullish"
        elif trend > 0.005 and range_trend > 1.0 and price_position > 0.6:
            phase = "markup"
            confidence = min(100, int(price_position * 80 + trend * 2000))
            signal = "bullish"
        elif trend > 0.002 and range_trend < 0.8 and price_position > 0.7:
            phase = "distribution"
            confidence = min(100, int((price_position - 0.5) * 150 + (1 - range_trend) * 50))
            signal = "bearish"
        elif trend < -0.002 and range_trend > 1.0 and price_position < 0.4:
            phase = "markdown"
            confidence = min(100, int((1 - price_position) * 80 + abs(trend) * 2000))
            signal = "bearish"
        else:
            phase = "transition"
            confidence = 30
            signal = "neutral"

        return {
            "phase": phase,
            "signal": signal,
            "confidence": confidence,
            "price_position": round(float(price_position), 3),
            "trend_strength": round(float(trend) * 100, 3),
            "vol_trend": round(float(vol_trend), 3),
            "implication": self._wyckoff_implication(phase)
        }

    def _wyckoff_implication(self, phase: str) -> str:
        implications = {
            "accumulation": "Smart money accumulating - expect markup phase soon",
            "markup": "Institutional buying driving price up - ride the trend",
            "distribution": "Smart money distributing to retail - expect markdown",
            "markdown": "Institutional selling driving price down - ride the downtrend",
            "transition": "Transitioning between phases - wait for clarity"
        }
        return implications.get(phase, "")

    def _institutional_footprint(self, df: pd.DataFrame) -> dict:
        """
        Detect institutional order flow from large candles and volume spikes
        """
        if len(df) < 30:
            return {"prints": [], "bias": "neutral"}

        recent = df.tail(30)
        ranges = recent["high"] - recent["low"]
        avg_range = ranges.mean()
        bodies = abs(recent["close"] - recent["open"])

        prints = []
        for i in range(len(recent)):
            rng = ranges.iloc[i]
            body = bodies.iloc[i]

            # Large range bar with >70% body = institutional candle
            if rng > avg_range * 2.0 and body > rng * 0.7:
                direction = "bullish" if recent["close"].iloc[i] > recent["open"].iloc[i] else "bearish"
                prints.append({
                    "index": i,
                    "direction": direction,
                    "size_multiple": round(float(rng / avg_range), 2),
                    "time": str(recent.index[i])
                })

        # Determine institutional bias from recent prints
        bullish_prints = sum(1 for p in prints if p["direction"] == "bullish")
        bearish_prints = sum(1 for p in prints if p["direction"] == "bearish")

        if bullish_prints > bearish_prints:
            bias = "institutional_buying"
        elif bearish_prints > bullish_prints:
            bias = "institutional_selling"
        else:
            bias = "neutral"

        return {
            "prints": prints[-5:],
            "bullish_count": bullish_prints,
            "bearish_count": bearish_prints,
            "bias": bias
        }

    def _exhaustion_detection(self, df: pd.DataFrame) -> dict:
        """
        Detect momentum exhaustion: large volume/range but diminishing follow-through
        """
        if len(df) < 20:
            return {"exhaustion": False, "type": None}

        last_10 = df.tail(10)
        ranges = (last_10["high"] - last_10["low"]).values
        closes = last_10["close"].values

        # Decreasing ranges after a large bar
        if len(ranges) >= 5:
            # Check for climactic bar followed by diminishing ranges
            max_range_idx = np.argmax(ranges[:7])
            if max_range_idx < 5:
                subsequent_ranges = ranges[max_range_idx + 1:]
                if len(subsequent_ranges) >= 3:
                    diminishing = all(subsequent_ranges[i] >= subsequent_ranges[i + 1]
                                     for i in range(min(3, len(subsequent_ranges) - 1)))

                    if diminishing:
                        climactic_direction = "bullish" if closes[max_range_idx] > last_10["open"].iloc[max_range_idx] else "bearish"
                        return {
                            "exhaustion": True,
                            "type": f"{climactic_direction}_exhaustion",
                            "implication": f"{'Bullish' if climactic_direction == 'bullish' else 'Bearish'} momentum exhausting - reversal likely",
                            "bars_since_climax": int(len(ranges) - max_range_idx - 1)
                        }

        return {"exhaustion": False, "type": None, "implication": "No exhaustion detected"}

    def _effort_vs_result(self, df: pd.DataFrame) -> dict:
        """
        Wyckoff Effort vs Result: Compare volume (effort) to price movement (result)
        High effort + low result = absorption/reversal coming
        """
        if len(df) < 20:
            return {"signal": "neutral"}

        recent = df.tail(20)
        volumes = recent["volume"].values
        ranges = (recent["high"] - recent["low"]).values

        if volumes.sum() == 0:
            volumes = ranges  # Use range as volume proxy

        avg_vol = np.mean(volumes)
        avg_range = np.mean(ranges)

        # Last 5 bars effort vs result
        last_5_vol = np.mean(volumes[-5:])
        last_5_range = np.mean(ranges[-5:])

        effort_ratio = last_5_vol / avg_vol if avg_vol > 0 else 1
        result_ratio = last_5_range / avg_range if avg_range > 0 else 1

        if effort_ratio > 1.3 and result_ratio < 0.7:
            signal = "high_effort_low_result"
            implication = "Absorption detected - reversal likely"
        elif effort_ratio < 0.7 and result_ratio > 1.3:
            signal = "low_effort_high_result"
            implication = "Easy movement - path of least resistance"
        elif effort_ratio > 1.0 and result_ratio > 1.0:
            signal = "effort_confirming"
            implication = "Volume confirming the move - continuation"
        else:
            signal = "neutral"
            implication = "Normal effort/result relationship"

        return {
            "signal": signal,
            "effort_ratio": round(float(effort_ratio), 3),
            "result_ratio": round(float(result_ratio), 3),
            "implication": implication
        }

    def _supply_demand_zones(self, df: pd.DataFrame) -> dict:
        """
        Identify institutional supply/demand zones from price action
        Strong moves away from consolidation = institutional zones
        """
        if len(df) < 50:
            return {"demand_zones": [], "supply_zones": []}

        demand_zones = []
        supply_zones = []

        ranges = (df["high"] - df["low"]).values
        avg_range = np.mean(ranges[-50:])

        for i in range(5, len(df) - 3):
            # Demand zone: consolidation then strong bullish expansion
            if i < len(df) - 1:
                expansion = df["close"].iloc[i + 1] - df["open"].iloc[i + 1]
                consolidation_range = np.std(df["close"].iloc[max(0, i - 5):i])

                if expansion > avg_range * 2 and consolidation_range < avg_range * 0.5:
                    demand_zones.append({
                        "high": float(df["high"].iloc[i]),
                        "low": float(df["low"].iloc[i]),
                        "strength": round(float(expansion / avg_range), 2),
                        "index": i
                    })

                # Supply zone: consolidation then strong bearish expansion
                if expansion < -avg_range * 2 and consolidation_range < avg_range * 0.5:
                    supply_zones.append({
                        "high": float(df["high"].iloc[i]),
                        "low": float(df["low"].iloc[i]),
                        "strength": round(float(abs(expansion) / avg_range), 2),
                        "index": i
                    })

        # Keep only unmitigated zones (price hasn't returned)
        current_price = float(df["close"].iloc[-1])
        active_demand = [z for z in demand_zones if current_price > z["low"]][-5:]
        active_supply = [z for z in supply_zones if current_price < z["high"]][-5:]

        # Score proximity to zones
        nearest_demand = None
        nearest_supply = None
        for z in reversed(active_demand):
            if current_price - z["high"] < avg_range * 3:
                nearest_demand = z
                break
        for z in reversed(active_supply):
            if z["low"] - current_price < avg_range * 3:
                nearest_supply = z
                break

        return {
            "demand_zones": active_demand,
            "supply_zones": active_supply,
            "nearest_demand": nearest_demand,
            "nearest_supply": nearest_supply,
            "at_demand": nearest_demand is not None and current_price <= nearest_demand["high"],
            "at_supply": nearest_supply is not None and current_price >= nearest_supply["low"]
        }

    def _trapped_trader_detection(self, df: pd.DataFrame) -> dict:
        """
        Detect trapped traders (false breakouts that trap participants)
        """
        if len(df) < 30:
            return {"trapped": None, "strength": 0}

        recent = df.tail(30)

        # Find recent swing highs/lows
        highs = recent["high"].values
        lows = recent["low"].values
        closes = recent["close"].values

        trapped_longs = 0
        trapped_shorts = 0

        # Check last 10 bars for trap patterns
        for i in range(20, len(recent)):
            prev_high = np.max(highs[i - 10:i])
            prev_low = np.min(lows[i - 10:i])

            # Bull trap: breaks above then closes below
            if highs[i] > prev_high and closes[i] < prev_high:
                trapped_longs += 1

            # Bear trap: breaks below then closes above
            if lows[i] < prev_low and closes[i] > prev_low:
                trapped_shorts += 1

        if trapped_longs > trapped_shorts:
            return {
                "trapped": "longs_trapped",
                "strength": trapped_longs,
                "implication": "Longs trapped above - expect selling pressure",
                "signal": "bearish"
            }
        elif trapped_shorts > trapped_longs:
            return {
                "trapped": "shorts_trapped",
                "strength": trapped_shorts,
                "implication": "Shorts trapped below - expect buying pressure",
                "signal": "bullish"
            }

        return {"trapped": None, "strength": 0, "signal": "neutral"}

    def _aggression_analysis(self, df: pd.DataFrame) -> dict:
        """
        Measure buyer vs seller aggression from candle characteristics
        """
        if len(df) < 20:
            return {"aggressor": "neutral", "score": 0}

        last_20 = df.tail(20)
        bullish_bars = last_20[last_20["close"] > last_20["open"]]
        bearish_bars = last_20[last_20["close"] < last_20["open"]]

        # Buyer aggression: large bullish bodies, closing near highs
        if len(bullish_bars) > 0:
            bull_body_pct = ((bullish_bars["close"] - bullish_bars["open"]) /
                            (bullish_bars["high"] - bullish_bars["low"]).replace(0, np.nan)).mean()
        else:
            bull_body_pct = 0

        # Seller aggression: large bearish bodies, closing near lows
        if len(bearish_bars) > 0:
            bear_body_pct = ((bearish_bars["open"] - bearish_bars["close"]) /
                            (bearish_bars["high"] - bearish_bars["low"]).replace(0, np.nan)).mean()
        else:
            bear_body_pct = 0

        bull_score = float(bull_body_pct) * len(bullish_bars) if not pd.isna(bull_body_pct) else 0
        bear_score = float(bear_body_pct) * len(bearish_bars) if not pd.isna(bear_body_pct) else 0

        if bull_score > bear_score * 1.3:
            aggressor = "buyers_dominant"
        elif bear_score > bull_score * 1.3:
            aggressor = "sellers_dominant"
        else:
            aggressor = "contested"

        return {
            "aggressor": aggressor,
            "buyer_score": round(bull_score, 2),
            "seller_score": round(bear_score, 2),
            "ratio": round(bull_score / bear_score if bear_score > 0 else 2.0, 3)
        }
