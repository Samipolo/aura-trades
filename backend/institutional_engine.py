"""
AURA TRADES - Institutional Flow Engine
Simulates institutional-grade positioning analysis: COT-style data,
smart money footprint detection, dark pool level estimation, and
institutional order flow reconstruction from price action.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class InstitutionalFlowEngine:
    """
    Reconstructs institutional positioning from price/volume data:
    - COT-style net positioning (derived from price behavior)
    - Smart money vs retail divergence
    - Institutional accumulation/distribution phases
    - Dark pool level estimation (from volume clusters)
    - Large player footprint detection
    - Position commitment analysis
    - Institutional order block identification
    - Liquidity engineering detection
    """

    def __init__(self):
        self.lookback_long = 100
        self.lookback_short = 20

    def analyze(self, df: pd.DataFrame, df_1h: pd.DataFrame = None, df_4h: pd.DataFrame = None) -> dict:
        """Full institutional flow analysis"""
        if df is None or df.empty or len(df) < 50:
            return self._empty_result()

        try:
            result = {}

            # COT-style positioning
            result["cot_positioning"] = self._cot_style_positioning(df)

            # Smart money divergence
            result["smart_money"] = self._smart_money_analysis(df)

            # Accumulation/Distribution
            result["accum_distrib"] = self._accumulation_distribution(df)

            # Dark pool levels
            result["dark_pool_levels"] = self._dark_pool_estimation(df)

            # Institutional footprint
            result["institutional_footprint"] = self._institutional_footprint(df)

            # Position commitment
            result["commitment"] = self._position_commitment(df)

            # Institutional order blocks
            result["inst_order_blocks"] = self._institutional_order_blocks(df)

            # Liquidity engineering
            result["liquidity_engineering"] = self._liquidity_engineering(df)

            # HTF institutional flow
            if df_4h is not None and not df_4h.empty:
                result["htf_flow"] = self._htf_institutional_flow(df_4h)
            else:
                result["htf_flow"] = {"bias": "neutral", "strength": 0}

            # Composite signal
            result["signal"] = self._composite_signal(result)
            result["bias"] = result["signal"].get("bias", "neutral")
            result["inst_score"] = result["signal"].get("score", 0)

            return result

        except Exception as e:
            print(f"[InstitutionalEngine] Error: {e}")
            return self._empty_result()

    def _cot_style_positioning(self, df: pd.DataFrame) -> dict:
        """
        Derive COT-style net positioning from price action.
        Uses momentum, volume, and price structure to estimate
        commercial vs speculative positioning.
        """
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        # Replace zero volume
        volume = np.where(volume == 0, 1, volume)

        n = len(close)
        lookback = min(50, n - 1)

        # Commercial hedger proxy: mean-reversion tendency
        # (Commercials are typically counter-trend)
        returns = np.diff(close) / close[:-1]
        recent_returns = returns[-lookback:]
        cumulative_move = close[-1] / close[-lookback] - 1

        # Speculative proxy: trend-following behavior
        sma_20 = pd.Series(close).rolling(20).mean().values
        sma_50 = pd.Series(close).rolling(50).mean().values

        # Net speculative positioning (derived)
        # Positive = specs are long, negative = specs are short
        spec_position = 0
        if not np.isnan(sma_20[-1]) and not np.isnan(sma_50[-1]):
            spec_position = (sma_20[-1] - sma_50[-1]) / close[-1] * 1000

        # Commercial positioning (inverse of speculators)
        commercial_position = -spec_position * 0.8

        # Volume-weighted positioning
        vol_direction = np.zeros(lookback)
        for i in range(lookback):
            idx = -(lookback - i)
            if close[idx] > close[idx - 1]:
                vol_direction[i] = volume[idx]
            else:
                vol_direction[i] = -volume[idx]

        buying_vol = vol_direction[vol_direction > 0].sum()
        selling_vol = abs(vol_direction[vol_direction < 0].sum())
        total_vol = buying_vol + selling_vol

        if total_vol > 0:
            vol_ratio = buying_vol / total_vol
        else:
            vol_ratio = 0.5

        # Net position score (-100 to +100)
        net_position = (vol_ratio - 0.5) * 200

        # Extreme positioning detection
        if net_position > 70:
            positioning = "extreme_long"
            signal = "bearish"  # Contrarian: extreme long = potential top
        elif net_position > 30:
            positioning = "net_long"
            signal = "bullish"
        elif net_position > -30:
            positioning = "neutral"
            signal = "neutral"
        elif net_position > -70:
            positioning = "net_short"
            signal = "bearish"
        else:
            positioning = "extreme_short"
            signal = "bullish"  # Contrarian: extreme short = potential bottom

        return {
            "net_position": round(net_position, 1),
            "positioning": positioning,
            "spec_position": round(spec_position, 2),
            "commercial_position": round(commercial_position, 2),
            "volume_buy_ratio": round(vol_ratio, 3),
            "extreme": abs(net_position) > 70,
            "signal": signal,
        }

    def _smart_money_analysis(self, df: pd.DataFrame) -> dict:
        """
        Detect smart money vs retail divergence.
        Smart money operates during high-volume institutional hours,
        retail typically trades during off-hours with smaller size.
        """
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
        volume = np.where(volume == 0, 1, volume)

        n = len(close)
        lookback = min(40, n - 1)

        # Smart money indicator: large candles with volume
        body_sizes = abs(df["close"].values - df["open"].values)
        candle_ranges = df["high"].values - df["low"].values

        # Identify "smart money candles" (large body, above-average volume)
        avg_body = np.mean(body_sizes[-lookback:])
        avg_vol = np.mean(volume[-lookback:])

        smart_candles_bull = 0
        smart_candles_bear = 0
        retail_candles_bull = 0
        retail_candles_bear = 0

        for i in range(-lookback, 0):
            is_smart = body_sizes[i] > avg_body * 1.5 and volume[i] > avg_vol * 1.3
            is_bullish = close[i] > df["open"].values[i]

            if is_smart:
                if is_bullish:
                    smart_candles_bull += 1
                else:
                    smart_candles_bear += 1
            else:
                if is_bullish:
                    retail_candles_bull += 1
                else:
                    retail_candles_bear += 1

        # Smart money direction
        total_smart = smart_candles_bull + smart_candles_bear
        if total_smart > 0:
            smart_ratio = smart_candles_bull / total_smart
        else:
            smart_ratio = 0.5

        # Retail direction
        total_retail = retail_candles_bull + retail_candles_bear
        if total_retail > 0:
            retail_ratio = retail_candles_bull / total_retail
        else:
            retail_ratio = 0.5

        # Divergence detection
        divergence = smart_ratio - retail_ratio
        if abs(divergence) > 0.2:
            divergence_detected = True
            # Follow smart money, not retail
            if smart_ratio > 0.6:
                signal = "bullish"
            elif smart_ratio < 0.4:
                signal = "bearish"
            else:
                signal = "neutral"
        else:
            divergence_detected = False
            signal = "neutral"

        # Money flow index (simplified)
        tp = (df["high"].values + df["low"].values + close) / 3
        raw_mf = tp * volume
        pos_mf = np.sum(raw_mf[-lookback:][np.diff(tp[-(lookback+1):]) > 0])
        neg_mf = np.sum(raw_mf[-lookback:][np.diff(tp[-(lookback+1):]) <= 0])
        mfi = 100 - (100 / (1 + pos_mf / max(neg_mf, 1)))

        return {
            "smart_money_ratio": round(smart_ratio, 3),
            "retail_ratio": round(retail_ratio, 3),
            "divergence_detected": divergence_detected,
            "divergence_magnitude": round(divergence, 3),
            "smart_candles_bull": smart_candles_bull,
            "smart_candles_bear": smart_candles_bear,
            "mfi": round(mfi, 1),
            "signal": signal,
        }

    def _accumulation_distribution(self, df: pd.DataFrame) -> dict:
        """Detect institutional accumulation or distribution phases"""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
        volume = np.where(volume == 0, 1, volume)

        n = len(close)
        lookback = min(60, n - 1)

        # Chaikin Money Flow
        clv = np.zeros(n)
        for i in range(n):
            hl_range = high[i] - low[i]
            if hl_range > 0:
                clv[i] = ((close[i] - low[i]) - (high[i] - close[i])) / hl_range
            else:
                clv[i] = 0

        ad_line = np.cumsum(clv * volume)

        # AD line trend
        ad_recent = ad_line[-lookback:]
        ad_slope = np.polyfit(range(len(ad_recent)), ad_recent, 1)[0]

        # Price vs AD divergence
        price_slope = np.polyfit(range(lookback), close[-lookback:], 1)[0]

        # Detect divergence
        price_up = price_slope > 0
        ad_up = ad_slope > 0

        if price_up and not ad_up:
            phase = "distribution"  # Price up but AD down = distribution
            signal = "bearish"
        elif not price_up and ad_up:
            phase = "accumulation"  # Price down but AD up = accumulation
            signal = "bullish"
        elif price_up and ad_up:
            phase = "markup"  # Both up = markup phase
            signal = "bullish"
        else:
            phase = "markdown"  # Both down = markdown phase
            signal = "bearish"

        # Wyckoff-style phase detection
        price_range = close[-lookback:].max() - close[-lookback:].min()
        recent_range = close[-10:].max() - close[-10:].min()
        compression = recent_range / price_range if price_range > 0 else 1

        if compression < 0.3 and phase == "accumulation":
            wyckoff = "spring_imminent"
        elif compression < 0.3 and phase == "distribution":
            wyckoff = "upthrust_imminent"
        else:
            wyckoff = phase

        return {
            "phase": phase,
            "wyckoff_phase": wyckoff,
            "ad_slope": round(ad_slope, 4),
            "price_slope": round(price_slope, 6),
            "divergence": (price_up != ad_up),
            "compression": round(compression, 2),
            "signal": signal,
        }

    def _dark_pool_estimation(self, df: pd.DataFrame) -> dict:
        """
        Estimate dark pool levels from volume clusters.
        High-volume nodes often correspond to institutional execution levels.
        """
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
        volume = np.where(volume == 0, 1, volume)

        n = len(close)
        lookback = min(100, n)

        # Volume profile to find high-volume nodes
        prices = close[-lookback:]
        vols = volume[-lookback:]

        # Create price bins
        price_min = prices.min()
        price_max = prices.max()
        num_bins = 30
        bin_edges = np.linspace(price_min, price_max, num_bins + 1)

        vol_profile = np.zeros(num_bins)
        for i in range(len(prices)):
            bin_idx = min(int((prices[i] - price_min) / (price_max - price_min) * num_bins), num_bins - 1)
            vol_profile[bin_idx] += vols[i]

        # Find top volume nodes (potential dark pool levels)
        sorted_indices = np.argsort(vol_profile)[::-1]
        dark_pool_levels = []

        for idx in sorted_indices[:5]:
            level_price = (bin_edges[idx] + bin_edges[idx + 1]) / 2
            vol_pct = vol_profile[idx] / vol_profile.sum() * 100
            dark_pool_levels.append({
                "price": round(float(level_price), 5),
                "volume_pct": round(float(vol_pct), 1),
                "strength": "strong" if vol_pct > 10 else "moderate",
            })

        # POC (Point of Control) - highest volume level
        poc_idx = sorted_indices[0]
        poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2

        current = close[-1]
        above_poc = current > poc_price

        return {
            "poc": round(float(poc_price), 5),
            "above_poc": above_poc,
            "dark_pool_levels": dark_pool_levels[:3],
            "nearest_level": dark_pool_levels[0] if dark_pool_levels else None,
            "signal": "bullish" if above_poc else "bearish",
        }

    def _institutional_footprint(self, df: pd.DataFrame) -> dict:
        """Detect institutional order execution patterns"""
        close = df["close"].values
        open_p = df["open"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        n = len(close)
        lookback = min(30, n - 1)

        # Institutional patterns:
        # 1. Absorption: Large volume but small price movement
        # 2. Exhaustion: Large move on declining volume
        # 3. Iceberg: Repeated tests of same level

        absorptions = 0
        exhaustions = 0
        avg_vol = np.mean(volume[-lookback:])
        avg_range = np.mean(high[-lookback:] - low[-lookback:])

        for i in range(-lookback, 0):
            candle_range = high[i] - low[i]
            vol_ratio = volume[i] / max(avg_vol, 1)
            range_ratio = candle_range / max(avg_range, 0.00001)

            # Absorption: high volume, small range
            if vol_ratio > 1.5 and range_ratio < 0.5:
                absorptions += 1

            # Exhaustion: large range, declining volume
            if range_ratio > 1.5 and vol_ratio < 0.7:
                exhaustions += 1

        # Iceberg detection: repeated tests of a level
        recent_lows = low[-lookback:]
        recent_highs = high[-lookback:]
        level_tests = self._count_level_tests(recent_lows, recent_highs, close[-1])

        # Footprint interpretation
        if absorptions > 3 and close[-1] > close[-lookback]:
            footprint = "institutional_buying"
            signal = "bullish"
        elif absorptions > 3 and close[-1] < close[-lookback]:
            footprint = "institutional_selling"
            signal = "bearish"
        elif exhaustions > 2 and close[-1] > close[-lookback]:
            footprint = "buying_exhaustion"
            signal = "bearish"
        elif exhaustions > 2 and close[-1] < close[-lookback]:
            footprint = "selling_exhaustion"
            signal = "bullish"
        else:
            footprint = "neutral"
            signal = "neutral"

        return {
            "footprint": footprint,
            "absorptions": absorptions,
            "exhaustions": exhaustions,
            "level_tests": level_tests,
            "signal": signal,
        }

    def _count_level_tests(self, lows: np.ndarray, highs: np.ndarray, current: float) -> int:
        """Count how many times a level near current price was tested"""
        tolerance = (highs.max() - lows.min()) * 0.02
        low_tests = np.sum(np.abs(lows - current) < tolerance)
        high_tests = np.sum(np.abs(highs - current) < tolerance)
        return int(low_tests + high_tests)

    def _position_commitment(self, df: pd.DataFrame) -> dict:
        """Measure how committed institutions are to current direction"""
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        n = len(close)
        lookback = min(30, n - 1)

        # Commitment = consistency of direction + volume backing
        up_days = 0
        down_days = 0
        up_vol = 0
        down_vol = 0

        for i in range(-lookback, 0):
            if close[i] > close[i - 1]:
                up_days += 1
                up_vol += volume[i]
            else:
                down_days += 1
                down_vol += volume[i]

        total_days = up_days + down_days
        direction_consistency = max(up_days, down_days) / max(total_days, 1)

        # Volume commitment
        total_vol = up_vol + down_vol
        vol_commitment = max(up_vol, down_vol) / max(total_vol, 1)

        # Combined commitment score (0-100)
        commitment_score = (direction_consistency * 50 + vol_commitment * 50)

        if up_days > down_days:
            direction = "long"
        elif down_days > up_days:
            direction = "short"
        else:
            direction = "neutral"

        # Conviction level
        if commitment_score > 75:
            conviction = "high"
        elif commitment_score > 55:
            conviction = "moderate"
        else:
            conviction = "low"

        return {
            "direction": direction,
            "commitment_score": round(commitment_score, 1),
            "conviction": conviction,
            "up_days": up_days,
            "down_days": down_days,
            "direction_consistency": round(direction_consistency, 2),
            "volume_commitment": round(vol_commitment, 2),
            "signal": "bullish" if direction == "long" and conviction != "low" else
                     "bearish" if direction == "short" and conviction != "low" else "neutral",
        }

    def _institutional_order_blocks(self, df: pd.DataFrame) -> dict:
        """Identify institutional order blocks with volume confirmation"""
        close = df["close"].values
        open_p = df["open"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        n = len(close)
        lookback = min(50, n - 5)
        avg_vol = np.mean(volume[-lookback:])

        bullish_obs = []
        bearish_obs = []

        for i in range(-lookback, -3):
            # Bullish OB: Down candle followed by strong up move with volume
            if close[i] < open_p[i]:  # Down candle
                # Check if next 3 candles break above
                subsequent_high = max(high[i+1], high[i+2], high[i+3])
                if subsequent_high > high[i] and volume[i+1] > avg_vol * 1.2:
                    bullish_obs.append({
                        "top": float(open_p[i]),
                        "bottom": float(close[i]),
                        "volume_ratio": round(float(volume[i+1] / avg_vol), 2),
                    })

            # Bearish OB: Up candle followed by strong down move with volume
            if close[i] > open_p[i]:  # Up candle
                subsequent_low = min(low[i+1], low[i+2], low[i+3])
                if subsequent_low < low[i] and volume[i+1] > avg_vol * 1.2:
                    bearish_obs.append({
                        "top": float(close[i]),
                        "bottom": float(open_p[i]),
                        "volume_ratio": round(float(volume[i+1] / avg_vol), 2),
                    })

        # Find nearest unmitigated OBs
        current = close[-1]
        nearest_bull_ob = None
        nearest_bear_ob = None

        for ob in reversed(bullish_obs):
            if current > ob["top"]:  # Price above = OB mitigated
                continue
            if current >= ob["bottom"]:  # Price in OB zone
                nearest_bull_ob = ob
                break
            if nearest_bull_ob is None or ob["top"] > nearest_bull_ob["top"]:
                nearest_bull_ob = ob

        for ob in reversed(bearish_obs):
            if current < ob["bottom"]:
                continue
            if current <= ob["top"]:
                nearest_bear_ob = ob
                break
            if nearest_bear_ob is None or ob["bottom"] < nearest_bear_ob["bottom"]:
                nearest_bear_ob = ob

        # Signal based on proximity
        signal = "neutral"
        if nearest_bull_ob and current <= nearest_bull_ob["top"] * 1.001:
            signal = "bullish"
        elif nearest_bear_ob and current >= nearest_bear_ob["bottom"] * 0.999:
            signal = "bearish"

        return {
            "bullish_obs": len(bullish_obs),
            "bearish_obs": len(bearish_obs),
            "nearest_bullish": nearest_bull_ob,
            "nearest_bearish": nearest_bear_ob,
            "signal": signal,
        }

    def _liquidity_engineering(self, df: pd.DataFrame) -> dict:
        """
        Detect liquidity engineering: stop hunts, liquidity sweeps,
        and engineered moves designed to trigger retail stops.
        """
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        n = len(close)
        lookback = min(40, n - 3)

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(2, lookback):
            idx = -(lookback - i)
            if high[idx] > high[idx-1] and high[idx] > high[idx+1] and \
               high[idx] > high[idx-2] and high[idx] > high[idx+2] if abs(idx+2) < n else True:
                swing_highs.append(float(high[idx]))
            if low[idx] < low[idx-1] and low[idx] < low[idx+1] and \
               low[idx] < low[idx-2] and low[idx] < low[idx+2] if abs(idx+2) < n else True:
                swing_lows.append(float(low[idx]))

        current = close[-1]
        recent_high = high[-5:].max()
        recent_low = low[-5:].min()

        # Detect stop hunts (price pierces level then reverses)
        stop_hunt_above = False
        stop_hunt_below = False

        if swing_highs:
            nearest_swing_high = min(swing_highs, key=lambda x: abs(x - current)) if swing_highs else current
            # Check if recent price swept above a swing high then came back
            if recent_high > nearest_swing_high and current < nearest_swing_high:
                stop_hunt_above = True

        if swing_lows:
            nearest_swing_low = max([sl for sl in swing_lows if sl < current], default=current)
            if recent_low < nearest_swing_low and current > nearest_swing_low:
                stop_hunt_below = True

        # Liquidity grab assessment
        if stop_hunt_above:
            signal = "bearish"  # Swept highs = likely reversal down
            engineering = "sell_side_grab"
        elif stop_hunt_below:
            signal = "bullish"  # Swept lows = likely reversal up
            engineering = "buy_side_grab"
        else:
            signal = "neutral"
            engineering = "none"

        return {
            "stop_hunt_above": stop_hunt_above,
            "stop_hunt_below": stop_hunt_below,
            "engineering_type": engineering,
            "swing_highs_found": len(swing_highs),
            "swing_lows_found": len(swing_lows),
            "signal": signal,
        }

    def _htf_institutional_flow(self, df_4h: pd.DataFrame) -> dict:
        """Analyze institutional flow on higher timeframe"""
        if df_4h is None or df_4h.empty or len(df_4h) < 20:
            return {"bias": "neutral", "strength": 0}

        close = df_4h["close"].values
        volume = df_4h["volume"].values if "volume" in df_4h.columns else np.ones(len(df_4h))
        volume = np.where(volume == 0, 1, volume)

        lookback = min(20, len(close) - 1)

        # 4H volume-weighted direction
        weighted_direction = 0
        for i in range(-lookback, 0):
            change = close[i] - close[i-1]
            weight = volume[i] / np.mean(volume[-lookback:])
            weighted_direction += np.sign(change) * weight

        normalized = weighted_direction / lookback

        if normalized > 0.3:
            bias = "bullish"
        elif normalized < -0.3:
            bias = "bearish"
        else:
            bias = "neutral"

        return {
            "bias": bias,
            "strength": round(abs(normalized) * 100, 1),
            "weighted_direction": round(normalized, 3),
        }

    def _composite_signal(self, result: dict) -> dict:
        """Generate composite institutional signal"""
        bullish = 0
        bearish = 0
        factors = []

        # COT positioning (weight: 20)
        cot = result.get("cot_positioning", {})
        if cot.get("signal") == "bullish":
            bullish += 20
            factors.append("cot_bullish")
        elif cot.get("signal") == "bearish":
            bearish += 20
            factors.append("cot_bearish")

        # Smart money (weight: 25)
        sm = result.get("smart_money", {})
        if sm.get("signal") == "bullish":
            bullish += 25
            factors.append("smart_money_buying")
        elif sm.get("signal") == "bearish":
            bearish += 25
            factors.append("smart_money_selling")

        # Accumulation/Distribution (weight: 20)
        ad = result.get("accum_distrib", {})
        if ad.get("signal") == "bullish":
            bullish += 20
            factors.append("accumulation")
        elif ad.get("signal") == "bearish":
            bearish += 20
            factors.append("distribution")

        # Institutional footprint (weight: 15)
        fp = result.get("institutional_footprint", {})
        if fp.get("signal") == "bullish":
            bullish += 15
            factors.append("inst_buying_footprint")
        elif fp.get("signal") == "bearish":
            bearish += 15
            factors.append("inst_selling_footprint")

        # Commitment (weight: 10)
        cm = result.get("commitment", {})
        if cm.get("signal") == "bullish":
            bullish += 10
            factors.append("commitment_long")
        elif cm.get("signal") == "bearish":
            bearish += 10
            factors.append("commitment_short")

        # Liquidity engineering (weight: 15)
        le = result.get("liquidity_engineering", {})
        if le.get("signal") == "bullish":
            bullish += 15
            factors.append("liquidity_grab_bullish")
        elif le.get("signal") == "bearish":
            bearish += 15
            factors.append("liquidity_grab_bearish")

        # HTF flow (weight: 15)
        htf = result.get("htf_flow", {})
        if htf.get("bias") == "bullish":
            bullish += 15
            factors.append("htf_inst_bullish")
        elif htf.get("bias") == "bearish":
            bearish += 15
            factors.append("htf_inst_bearish")

        total = max(bullish + bearish, 1)
        if bullish > bearish * 1.3:
            bias = "bullish"
        elif bearish > bullish * 1.3:
            bias = "bearish"
        else:
            bias = "neutral"

        score = max(bullish, bearish)

        return {
            "bias": bias,
            "score": min(100, score),
            "bullish": bullish,
            "bearish": bearish,
            "factors": factors,
        }

    def _empty_result(self) -> dict:
        return {
            "cot_positioning": {"signal": "neutral", "net_position": 0},
            "smart_money": {"signal": "neutral"},
            "accum_distrib": {"signal": "neutral", "phase": "neutral"},
            "dark_pool_levels": {"signal": "neutral"},
            "institutional_footprint": {"signal": "neutral", "footprint": "neutral"},
            "commitment": {"signal": "neutral", "commitment_score": 50},
            "inst_order_blocks": {"signal": "neutral"},
            "liquidity_engineering": {"signal": "neutral", "engineering_type": "none"},
            "htf_flow": {"bias": "neutral", "strength": 0},
            "signal": {"bias": "neutral", "score": 0, "factors": []},
            "bias": "neutral",
            "inst_score": 0,
        }
