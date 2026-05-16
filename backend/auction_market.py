"""
AURA TRADES - Auction Market Theory (AMT) Engine
==================================================
Implements Market Profile / Auction Market Theory concepts:
- Volume Profile (POC, Value Area High/Low)
- TPO (Time Price Opportunity) analysis
- Initial Balance (IB) range
- Balance vs Imbalance detection
- Excess / Initiative activity
- Single prints / poor highs & lows
- Day type classification (Normal, Trend, Double Distribution, etc.)
- Composite profile (multi-day)
- Acceptance / Rejection zones
- Rotation Factor
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter


class AuctionMarketEngine:
    """Auction Market Theory analysis based on Market Profile concepts"""

    def analyze(self, df_15m: pd.DataFrame, df_1h: pd.DataFrame = None,
                df_4h: pd.DataFrame = None) -> dict:
        if df_15m.empty or len(df_15m) < 50:
            return {"amt_score": 0, "day_type": "unknown"}

        current_price = float(df_15m["close"].iloc[-1])

        # Volume profile
        vol_profile = self._build_volume_profile(df_15m, bins=50)
        poc = vol_profile["poc"]
        vah = vol_profile["vah"]
        val = vol_profile["val"]

        # TPO analysis
        tpo = self._build_tpo_profile(df_15m)

        # Initial Balance
        ib = self._calculate_initial_balance(df_15m)

        # Balance / Imbalance
        balance = self._detect_balance_imbalance(df_15m, vol_profile)

        # Day type classification
        day_type = self._classify_day_type(df_15m, ib, vol_profile, balance)

        # Excess detection (long wicks at extremes)
        excess = self._detect_excess(df_15m)

        # Single prints (gaps in TPO = initiative)
        singles = self._detect_single_prints(tpo)

        # Poor highs/lows (no excess = likely to be revisited)
        poor = self._detect_poor_extremes(df_15m)

        # Rotation factor
        rotation = self._calculate_rotation_factor(df_15m)

        # Composite profile (multi-day)
        composite = self._build_composite_profile(df_15m, days=5)

        # HTF volume profile
        htf_profile = {}
        if df_1h is not None and len(df_1h) >= 30:
            htf_profile["1h"] = self._build_volume_profile(df_1h, bins=30)
        if df_4h is not None and len(df_4h) >= 15:
            htf_profile["4h"] = self._build_volume_profile(df_4h, bins=20)

        # Price position relative to value area
        position = self._price_position(current_price, poc, vah, val)

        # AMT composite signal
        bias, amt_score, factors = self._calculate_amt_signal(
            current_price, vol_profile, tpo, ib, balance, day_type,
            excess, singles, poor, rotation, composite, position, htf_profile
        )

        return {
            "bias": bias,
            "amt_score": amt_score,
            "factors": factors,
            "volume_profile": {
                "poc": round(poc, 5),
                "vah": round(vah, 5),
                "val": round(val, 5),
                "value_area_width": round(vah - val, 5),
            },
            "tpo": {
                "poc_tpo": tpo.get("poc_price"),
                "max_tpo_count": tpo.get("max_count", 0),
                "distribution": tpo.get("distribution", "unknown"),
            },
            "initial_balance": ib,
            "balance_state": balance,
            "day_type": day_type,
            "excess": excess,
            "single_prints": singles,
            "poor_extremes": poor,
            "rotation_factor": rotation,
            "composite_poc": composite.get("poc"),
            "price_position": position,
            "htf_profile": {k: {"poc": round(v["poc"], 5), "vah": round(v["vah"], 5),
                                "val": round(v["val"], 5)} for k, v in htf_profile.items()},
        }

    # ───────────────────── VOLUME PROFILE ───────────────────

    def _build_volume_profile(self, df, bins=50):
        closes = df["close"].values
        volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        # If volume is all zeros (forex), use time as proxy
        if np.sum(volumes) == 0:
            volumes = np.ones(len(df))

        price_min = float(np.min(df["low"].values))
        price_max = float(np.max(df["high"].values))

        if price_max == price_min:
            return {"poc": price_min, "vah": price_max, "val": price_min,
                    "profile": [], "total_volume": 0}

        # Build price bins
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        bin_volumes = np.zeros(bins)

        for i in range(len(df)):
            h = float(df["high"].iloc[i])
            l = float(df["low"].iloc[i])
            v = float(volumes[i])
            for j in range(bins):
                bin_low = bin_edges[j]
                bin_high = bin_edges[j + 1]
                if l <= bin_high and h >= bin_low:
                    overlap = min(h, bin_high) - max(l, bin_low)
                    rng = h - l if h - l > 0 else 1
                    bin_volumes[j] += v * (overlap / rng)

        # POC = price level with most volume
        poc_idx = np.argmax(bin_volumes)
        poc = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2)

        # Value Area = 70% of total volume around POC
        total_vol = np.sum(bin_volumes)
        target_vol = total_vol * 0.70

        va_vol = bin_volumes[poc_idx]
        va_low_idx = poc_idx
        va_high_idx = poc_idx

        while va_vol < target_vol:
            expand_up = bin_volumes[va_high_idx + 1] if va_high_idx + 1 < bins else 0
            expand_down = bin_volumes[va_low_idx - 1] if va_low_idx - 1 >= 0 else 0

            if expand_up >= expand_down:
                va_high_idx = min(va_high_idx + 1, bins - 1)
                va_vol += expand_up
            else:
                va_low_idx = max(va_low_idx - 1, 0)
                va_vol += expand_down

            if va_low_idx == 0 and va_high_idx == bins - 1:
                break

        vah = float(bin_edges[va_high_idx + 1]) if va_high_idx + 1 <= bins else price_max
        val = float(bin_edges[va_low_idx])

        profile = []
        for j in range(bins):
            if bin_volumes[j] > 0:
                profile.append({
                    "price": round(float((bin_edges[j] + bin_edges[j + 1]) / 2), 5),
                    "volume": round(float(bin_volumes[j]), 2)
                })

        return {
            "poc": poc, "vah": vah, "val": val,
            "profile": profile,
            "total_volume": float(total_vol),
            "high_volume_nodes": self._find_hvn_lvn(bin_volumes, bin_edges, "high"),
            "low_volume_nodes": self._find_hvn_lvn(bin_volumes, bin_edges, "low"),
        }

    def _find_hvn_lvn(self, bin_volumes, bin_edges, mode="high"):
        """Find High Volume Nodes or Low Volume Nodes"""
        avg = np.mean(bin_volumes)
        nodes = []
        for j in range(len(bin_volumes)):
            price = float((bin_edges[j] + bin_edges[j + 1]) / 2)
            if mode == "high" and bin_volumes[j] > avg * 1.5:
                nodes.append(round(price, 5))
            elif mode == "low" and 0 < bin_volumes[j] < avg * 0.5:
                nodes.append(round(price, 5))
        return nodes[:5]

    # ───────────────────── TPO PROFILE ──────────────────────

    def _build_tpo_profile(self, df, bins=30):
        if len(df) < 10:
            return {"distribution": "unknown"}

        price_min = float(np.min(df["low"].values))
        price_max = float(np.max(df["high"].values))
        if price_max == price_min:
            return {"poc_price": price_min, "max_count": 1, "distribution": "single"}

        bin_edges = np.linspace(price_min, price_max, bins + 1)
        tpo_counts = np.zeros(bins, dtype=int)

        for i in range(len(df)):
            h = float(df["high"].iloc[i])
            l = float(df["low"].iloc[i])
            for j in range(bins):
                if l <= bin_edges[j + 1] and h >= bin_edges[j]:
                    tpo_counts[j] += 1

        poc_idx = np.argmax(tpo_counts)
        poc_price = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2)

        # Distribution shape (PBD logic)
        upper_half = np.sum(tpo_counts[bins // 2:])
        lower_half = np.sum(tpo_counts[:bins // 2])
        total = upper_half + lower_half

        if total == 0:
            dist = "unknown"
        elif upper_half > total * 0.60:
            dist = "P_shape"  # Short covering / bullish continuation
        elif lower_half > total * 0.60:
            dist = "b_shape"  # Long liquidation / bearish continuation
        elif 0.40 <= upper_half / total <= 0.60:
            dist = "D_shape"  # Balanced fair value
        elif poc_idx > bins * 0.6:
            dist = "P_shape"
        elif poc_idx < bins * 0.4:
            dist = "b_shape"
        else:
            dist = "D_shape"

        return {
            "poc_price": round(poc_price, 5),
            "max_count": int(np.max(tpo_counts)),
            "distribution": dist,
        }

    # ───────────────────── INITIAL BALANCE ──────────────────

    def _calculate_initial_balance(self, df):
        """IB = first hour of trading session range"""
        if len(df) < 4:
            return {"high": None, "low": None}

        try:
            last_date = df.index[-1].date() if hasattr(df.index[-1], 'date') else None
            if last_date is None:
                # Use first 4 candles as proxy
                ib_data = df.tail(min(len(df), 16)).head(4)
            else:
                today_data = df[df.index.date == last_date]
                ib_data = today_data.head(4)  # First 4 x 15m = 1 hour
                if len(ib_data) < 4:
                    ib_data = df.tail(min(len(df), 16)).head(4)
        except Exception:
            ib_data = df.tail(min(len(df), 16)).head(4)

        if ib_data.empty:
            return {"high": None, "low": None}

        ib_high = float(ib_data["high"].max())
        ib_low = float(ib_data["low"].min())
        current = float(df["close"].iloc[-1])
        ib_range = ib_high - ib_low

        return {
            "high": round(ib_high, 5),
            "low": round(ib_low, 5),
            "range": round(ib_range, 5),
            "above_ib": current > ib_high,
            "below_ib": current < ib_low,
            "inside_ib": ib_low <= current <= ib_high,
            "ib_extension": round(float(max(0, current - ib_high, ib_low - current) / ib_range), 2) if ib_range > 0 else 0,
        }

    # ───────────────────── BALANCE / IMBALANCE ──────────────

    def _detect_balance_imbalance(self, df, vol_profile):
        """Detect if market is in balance (range) or imbalance (trending)"""
        if len(df) < 20:
            return {"state": "unknown"}

        closes = df["close"].values
        recent = closes[-20:]
        vah = vol_profile["vah"]
        val = vol_profile["val"]
        poc = vol_profile["poc"]
        va_width = vah - val

        if va_width == 0:
            return {"state": "unknown"}

        # Price within value area = balance
        pct_inside = sum(1 for c in recent if val <= c <= vah) / len(recent)

        # Trend strength via linear regression slope
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0] if len(recent) > 2 else 0
        normalized_slope = slope / va_width if va_width > 0 else 0

        if pct_inside > 0.7 and abs(normalized_slope) < 0.02:
            state = "balance"
            signal = "range_bound"
        elif pct_inside < 0.3:
            state = "imbalance"
            signal = "bullish" if recent[-1] > vah else "bearish"
        elif abs(normalized_slope) > 0.05:
            state = "imbalance"
            signal = "bullish" if normalized_slope > 0 else "bearish"
        else:
            state = "transitioning"
            signal = "neutral"

        return {
            "state": state,
            "signal": signal,
            "pct_in_value": round(pct_inside, 2),
            "trend_slope": round(float(normalized_slope), 4),
        }

    # ───────────────────── DAY TYPE CLASSIFICATION ──────────

    def _classify_day_type(self, df, ib, vol_profile, balance):
        """
        Market Profile day types:
        - Normal: balanced, 70% inside IB
        - Normal Variation: extends one side of IB
        - Trend Day: directional, closes at extreme
        - Double Distribution: two POCs
        - Neutral: inside IB, no extension
        """
        if not ib.get("high") or not ib.get("low"):
            return {"type": "unknown", "description": "Insufficient IB data"}

        ib_high = ib["high"]
        ib_low = ib["low"]
        ib_range = ib.get("range", 0)
        current = float(df["close"].iloc[-1])

        day_high = float(df.tail(96)["high"].max())  # Last 24h
        day_low = float(df.tail(96)["low"].min())
        day_range = day_high - day_low

        if ib_range == 0:
            return {"type": "unknown"}

        ib_ratio = day_range / ib_range if ib_range > 0 else 1

        above_ib = current > ib_high
        below_ib = current < ib_low

        if ib_ratio < 1.3 and not above_ib and not below_ib:
            dtype = "neutral"
            desc = "Tight range, no IB extension — avoid"
        elif ib_ratio < 1.8 and (above_ib or below_ib):
            dtype = "normal_variation"
            desc = f"IB extended {'above' if above_ib else 'below'} — moderate trend"
        elif ib_ratio >= 2.5 and balance.get("state") == "imbalance":
            dtype = "trend"
            desc = "Strong directional move — trade with trend"
        elif ib_ratio >= 1.8:
            dtype = "normal"
            desc = "Standard day with extensions"
        else:
            dtype = "developing"
            desc = "Day type still forming"

        return {
            "type": dtype,
            "description": desc,
            "ib_ratio": round(ib_ratio, 2),
            "day_range": round(day_range, 5),
        }

    # ───────────────────── EXCESS ───────────────────────────

    def _detect_excess(self, df):
        """Excess = rejection at highs/lows via long wicks"""
        if len(df) < 10:
            return {"high_excess": False, "low_excess": False}

        recent = df.tail(10)
        highs = recent["high"].values
        lows = recent["low"].values
        closes = recent["close"].values
        opens = recent["open"].values

        # Check for upper excess (long upper wicks at highs)
        day_high = float(np.max(highs))
        upper_wicks = []
        for i in range(len(recent)):
            body_top = max(closes[i], opens[i])
            wick = highs[i] - body_top
            body = abs(closes[i] - opens[i])
            if body > 0 and wick > body * 1.5 and highs[i] > day_high * 0.999:
                upper_wicks.append(float(wick))

        # Lower excess
        day_low = float(np.min(lows))
        lower_wicks = []
        for i in range(len(recent)):
            body_bottom = min(closes[i], opens[i])
            wick = body_bottom - lows[i]
            body = abs(closes[i] - opens[i])
            if body > 0 and wick > body * 1.5 and lows[i] < day_low * 1.001:
                lower_wicks.append(float(wick))

        return {
            "high_excess": len(upper_wicks) > 0,
            "low_excess": len(lower_wicks) > 0,
            "upper_rejection_count": len(upper_wicks),
            "lower_rejection_count": len(lower_wicks),
            "signal": "bearish" if upper_wicks else ("bullish" if lower_wicks else "neutral")
        }

    # ───────────────────── SINGLE PRINTS ────────────────────

    def _detect_single_prints(self, tpo):
        """Single prints = gaps in TPO profile = initiative/aggressive activity"""
        dist = tpo.get("distribution", "unknown")
        # PBD Logic for directional conviction
        if dist == "P_shape":
            return {"detected": True, "type": "buying_initiative",
                    "signal": "bullish", "note": "P-shape (Short covering / Bullish initiative)"}
        elif dist == "b_shape":
            return {"detected": True, "type": "selling_initiative",
                    "signal": "bearish", "note": "b-shape (Long liquidation / Bearish initiative)"}
        elif dist == "D_shape":
            return {"detected": False, "signal": "neutral", "note": "D-shape (Balanced market)"}
        return {"detected": False, "signal": "neutral"}

    # ───────────────────── POOR HIGHS/LOWS ──────────────────

    def _detect_poor_extremes(self, df):
        """Poor highs/lows = no rejection = likely to be revisited"""
        if len(df) < 10:
            return {"poor_high": False, "poor_low": False}

        recent = df.tail(10)
        highs = recent["high"].values
        closes = recent["close"].values
        opens = recent["open"].values
        lows = recent["low"].values

        # Poor high: closes near the high with small wicks
        day_high_idx = np.argmax(highs)
        upper_wick = float(highs[day_high_idx] - max(closes[day_high_idx], opens[day_high_idx]))
        body = abs(closes[day_high_idx] - opens[day_high_idx])
        poor_high = body > 0 and upper_wick < body * 0.3

        # Poor low: closes near the low
        day_low_idx = np.argmin(lows)
        lower_wick = float(min(closes[day_low_idx], opens[day_low_idx]) - lows[day_low_idx])
        body_low = abs(closes[day_low_idx] - opens[day_low_idx])
        poor_low = body_low > 0 and lower_wick < body_low * 0.3

        return {
            "poor_high": poor_high,
            "poor_low": poor_low,
            "signal": "bearish" if poor_high else ("bullish" if poor_low else "neutral"),
            "note": "Poor high likely revisited" if poor_high else ("Poor low likely revisited" if poor_low else "")
        }

    # ───────────────────── ROTATION FACTOR ──────────────────

    def _calculate_rotation_factor(self, df):
        """Rotation factor measures how many half-hours rotate up/down"""
        if len(df) < 10:
            return {"value": 0, "interpretation": "neutral"}

        recent = df.tail(20)
        closes = recent["close"].values

        up_rotations = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
        down_rotations = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i - 1])

        rf = up_rotations - down_rotations

        if rf >= 5:
            interp = "strong_bullish"
        elif rf >= 2:
            interp = "bullish"
        elif rf <= -5:
            interp = "strong_bearish"
        elif rf <= -2:
            interp = "bearish"
        else:
            interp = "neutral"

        return {"value": rf, "interpretation": interp,
                "up": up_rotations, "down": down_rotations}

    # ───────────────────── COMPOSITE PROFILE ────────────────

    def _build_composite_profile(self, df, days=5):
        """Multi-day composite volume profile for higher conviction POC"""
        bars = min(len(df), days * 96)  # 96 bars per day on 15m
        recent = df.tail(bars)
        if len(recent) < 50:
            return {}
        return self._build_volume_profile(recent, bins=40)

    # ───────────────────── PRICE POSITION ───────────────────

    def _price_position(self, price, poc, vah, val):
        if vah == val:
            return {"zone": "unknown"}

        if price > vah:
            zone = "above_value"
            action = "responsive_sellers_expected"  # Short opportunities
        elif price < val:
            zone = "below_value"
            action = "responsive_buyers_expected"  # Long opportunities
        elif abs(price - poc) / (vah - val) < 0.1:
            zone = "at_poc"
            action = "balance_point"
        elif price > poc:
            zone = "upper_value"
            action = "slight_bullish"
        else:
            zone = "lower_value"
            action = "slight_bearish"

        return {
            "zone": zone,
            "action": action,
            "distance_to_poc": round(abs(price - poc), 5),
            "distance_to_vah": round(abs(price - vah), 5),
            "distance_to_val": round(abs(price - val), 5),
        }

    # ───────────────────── AMT COMPOSITE SIGNAL ─────────────

    def _calculate_amt_signal(self, price, vol_profile, tpo, ib, balance,
                              day_type, excess, singles, poor, rotation,
                              composite, position, htf_profile):
        bull_score = 0
        bear_score = 0
        factors = []

        # Position in value area
        zone = position.get("zone", "unknown")
        if zone == "below_value":
            bull_score += 15
            factors.append(("below_value_area", 15))
        elif zone == "above_value":
            bear_score += 15
            factors.append(("above_value_area", 15))

        # POC reference
        poc = vol_profile["poc"]
        if price > poc:
            bull_score += 8
            factors.append(("above_poc", 8))
        else:
            bear_score += 8
            factors.append(("below_poc", 8))

        # Balance / Imbalance
        bal_signal = balance.get("signal", "neutral")
        if bal_signal == "bullish":
            bull_score += 18
            factors.append(("imbalance_bullish", 18))
        elif bal_signal == "bearish":
            bear_score += 18
            factors.append(("imbalance_bearish", 18))

        # IB breakout
        if ib.get("above_ib"):
            bull_score += 14
            factors.append(("ib_breakout_up", 14))
        elif ib.get("below_ib"):
            bear_score += 14
            factors.append(("ib_breakout_down", 14))

        # Day type
        dt = day_type.get("type", "unknown")
        if dt == "trend":
            w = 12
            if balance.get("signal") == "bullish":
                bull_score += w
                factors.append(("trend_day_bullish", w))
            elif balance.get("signal") == "bearish":
                bear_score += w
                factors.append(("trend_day_bearish", w))

        # Excess
        if excess.get("high_excess"):
            bear_score += 12
            factors.append(("excess_at_highs", 12))
        if excess.get("low_excess"):
            bull_score += 12
            factors.append(("excess_at_lows", 12))

        # Single prints / TPO initiative
        if singles.get("signal") == "bullish":
            bull_score += 10
            factors.append(("buying_initiative", 10))
        elif singles.get("signal") == "bearish":
            bear_score += 10
            factors.append(("selling_initiative", 10))

        # Poor extremes
        if poor.get("signal") == "bullish":
            bull_score += 8
            factors.append(("poor_low_revisit", 8))
        elif poor.get("signal") == "bearish":
            bear_score += 8
            factors.append(("poor_high_revisit", 8))

        # Rotation factor
        rf = rotation.get("interpretation", "neutral")
        if "bullish" in rf:
            w = 10 if "strong" in rf else 6
            bull_score += w
            factors.append(("rotation_bullish", w))
        elif "bearish" in rf:
            w = 10 if "strong" in rf else 6
            bear_score += w
            factors.append(("rotation_bearish", w))

        # Composite POC reference (higher conviction)
        comp_poc = composite.get("poc")
        if comp_poc:
            if price > comp_poc:
                bull_score += 6
                factors.append(("above_composite_poc", 6))
            else:
                bear_score += 6
                factors.append(("below_composite_poc", 6))

        # HTF profile confluence
        for tf_key, prof in htf_profile.items():
            htf_poc = prof.get("poc", 0)
            if htf_poc:
                w = 10 if tf_key == "4h" else 7
                if price > htf_poc:
                    bull_score += w
                    factors.append((f"above_{tf_key}_poc", w))
                else:
                    bear_score += w
                    factors.append((f"below_{tf_key}_poc", w))

        total = bull_score + bear_score
        if total == 0:
            return "neutral", 0, factors

        if bull_score > bear_score:
            bias = "bullish"
            amt_score = round((bull_score / max(total, 1)) * 100, 1)
        elif bear_score > bull_score:
            bias = "bearish"
            amt_score = round((bear_score / max(total, 1)) * 100, 1)
        else:
            bias = "neutral"
            amt_score = 50

        return bias, amt_score, factors
