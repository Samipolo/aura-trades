"""
AURA TRADES - ICT (Inner Circle Trader) Concepts Engine
=========================================================
Implements institutional Smart Money Concepts:
- Order Blocks (OB) with mitigation tracking
- Breaker Blocks
- Fair Value Gaps (FVG) with inversion detection
- Market Structure Shift (MSS) & Change of Character (CHoCH)
- Liquidity Sweeps (buy-side / sell-side)
- Optimal Trade Entry (OTE) — Fibonacci 0.618-0.786
- Kill Zones (London, NY, Asian sessions)
- Power of 3 (Accumulation, Manipulation, Distribution)
- Judas Swing detection
- Displacement candles
- Institutional reference points (weekly/daily open, midnight open)
"""

import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import List, Dict, Optional, Tuple


class ICTEngine:
    """Full ICT / Smart Money Concepts analysis engine"""

    def analyze(self, df_15m: pd.DataFrame, df_1h: pd.DataFrame = None,
                df_4h: pd.DataFrame = None) -> dict:
        if df_15m.empty or len(df_15m) < 100:
            return {"ict_score": 0, "bias": "neutral"}

        closes = df_15m["close"].values
        highs = df_15m["high"].values
        lows = df_15m["low"].values
        opens = df_15m["open"].values
        current_price = float(closes[-1])

        # Core ICT concepts
        swing_h, swing_l = self._find_swing_points(df_15m)
        mss = self._detect_mss(swing_h, swing_l, closes)
        choch = self._detect_choch(swing_h, swing_l, closes)
        displacement = self._detect_displacement(df_15m)
        order_blocks = self._find_order_blocks_ict(df_15m, swing_h, swing_l)
        breaker_blocks = self._find_breaker_blocks(df_15m, order_blocks)
        fvgs = self._find_fvg_ict(df_15m)
        fvg_inversions = self._detect_fvg_inversions(fvgs, current_price)
        liquidity = self._detect_liquidity_sweeps(df_15m, swing_h, swing_l)
        ote = self._calculate_ote(swing_h, swing_l, current_price)
        kill_zone = self._get_kill_zone(df_15m)
        po3 = self._detect_power_of_3(df_15m)
        judas = self._detect_judas_swing(df_15m)
        ref_points = self._institutional_ref_points(df_15m)

        # HTF analysis if provided
        htf_ict = {}
        if df_1h is not None and len(df_1h) >= 50:
            htf_ict["1h"] = self._htf_ict_analysis(df_1h, "1H")
        if df_4h is not None and len(df_4h) >= 20:
            htf_ict["4h"] = self._htf_ict_analysis(df_4h, "4H")

        # Composite ICT bias
        bias, ict_score, factors = self._calculate_ict_bias(
            mss, choch, displacement, order_blocks, breaker_blocks,
            fvgs, fvg_inversions, liquidity, ote, kill_zone, po3, judas,
            current_price, htf_ict
        )

        return {
            "bias": bias,
            "ict_score": ict_score,
            "factors": factors,
            "mss": mss,
            "choch": choch,
            "displacement": displacement,
            "order_blocks": order_blocks[:5],
            "breaker_blocks": breaker_blocks[:3],
            "fvgs": fvgs[:5],
            "fvg_inversions": fvg_inversions,
            "liquidity_sweeps": liquidity,
            "ote": ote,
            "kill_zone": kill_zone,
            "power_of_3": po3,
            "judas_swing": judas,
            "ref_points": ref_points,
            "htf_ict": htf_ict,
        }

    # ───────────────────── SWING POINTS ─────────────────────

    def _find_swing_points(self, df, lookback=5):
        highs, lows = df["high"].values, df["low"].values
        sh, sl = [], []
        for i in range(lookback, len(df) - lookback):
            if all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, lookback + 1)):
                sh.append({"idx": i, "price": float(highs[i])})
            if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, lookback + 1)):
                sl.append({"idx": i, "price": float(lows[i])})
        return sh, sl

    # ───────────────────── MSS (Market Structure Shift) ─────

    def _detect_mss(self, swing_h, swing_l, closes):
        if len(swing_h) < 2 or len(swing_l) < 2:
            return {"detected": False}
        last_sh = swing_h[-1]["price"]
        prev_sh = swing_h[-2]["price"]
        last_sl = swing_l[-1]["price"]
        prev_sl = swing_l[-2]["price"]
        current = float(closes[-1])

        # Bullish MSS: price breaks above a lower high (shift from bearish to bullish)
        if prev_sh > last_sh and current > last_sh:
            return {"detected": True, "direction": "bullish", "broken_level": last_sh,
                    "type": "break_of_lower_high"}
        # Bearish MSS: price breaks below a higher low
        if prev_sl < last_sl and current < last_sl:
            return {"detected": True, "direction": "bearish", "broken_level": last_sl,
                    "type": "break_of_higher_low"}
        return {"detected": False}

    # ───────────────────── CHoCH (Change of Character) ──────

    def _detect_choch(self, swing_h, swing_l, closes):
        if len(swing_h) < 3 or len(swing_l) < 3:
            return {"detected": False}

        current = float(closes[-1])
        # Bullish CHoCH: series of lower lows then price breaks above last swing high
        lows_descending = swing_l[-3]["price"] > swing_l[-2]["price"] > swing_l[-1]["price"]
        if lows_descending and current > swing_h[-1]["price"]:
            return {"detected": True, "direction": "bullish",
                    "type": "break_above_swing_high_after_downtrend",
                    "level": swing_h[-1]["price"]}

        # Bearish CHoCH: series of higher highs then price breaks below last swing low
        highs_ascending = swing_h[-3]["price"] < swing_h[-2]["price"] < swing_h[-1]["price"]
        if highs_ascending and current < swing_l[-1]["price"]:
            return {"detected": True, "direction": "bearish",
                    "type": "break_below_swing_low_after_uptrend",
                    "level": swing_l[-1]["price"]}
        return {"detected": False}

    # ───────────────────── DISPLACEMENT CANDLES ─────────────

    def _detect_displacement(self, df):
        if len(df) < 20:
            return {"detected": False}
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values

        bodies = np.abs(closes - opens)
        avg_body = np.mean(bodies[-50:]) if len(bodies) >= 50 else np.mean(bodies)
        recent = []

        for i in range(-5, 0):
            body = abs(closes[i] - opens[i])
            rng = highs[i] - lows[i]
            if avg_body > 0 and body > avg_body * 2.5 and rng > 0 and body / rng > 0.7:
                direction = "bullish" if closes[i] > opens[i] else "bearish"
                recent.append({"idx": len(df) + i, "direction": direction,
                               "strength": round(float(body / avg_body), 1)})

        if recent:
            return {"detected": True, "candles": recent,
                    "direction": recent[-1]["direction"],
                    "count": len(recent)}
        return {"detected": False}

    # ───────────────────── ORDER BLOCKS (ICT) ───────────────

    def _find_order_blocks_ict(self, df, swing_h, swing_l):
        obs = []
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        n = len(df)

        # Bullish OB: last bearish candle before a bullish impulse move
        for i in range(2, min(n - 1, 100)):
            idx = n - 1 - i
            if idx < 1:
                break
            # Bearish candle followed by bullish displacement
            if closes[idx] < opens[idx]:  # bearish candle
                # Next candle(s) move up aggressively
                if idx + 1 < n and closes[idx + 1] > opens[idx + 1]:
                    up_move = closes[idx + 1] - opens[idx + 1]
                    avg_body = np.mean(np.abs(closes[max(0, idx - 20):idx] - opens[max(0, idx - 20):idx]))
                    if avg_body > 0 and up_move > avg_body * 1.8:
                        obs.append({
                            "type": "bullish", "idx": idx,
                            "high": float(opens[idx]), "low": float(lows[idx]),
                            "mitigated": float(lows[idx]) > float(min(lows[idx + 1:])) if idx + 1 < n else False
                        })

            # Bearish OB: last bullish candle before bearish impulse
            if closes[idx] > opens[idx]:  # bullish candle
                if idx + 1 < n and closes[idx + 1] < opens[idx + 1]:
                    down_move = opens[idx + 1] - closes[idx + 1]
                    avg_body = np.mean(np.abs(closes[max(0, idx - 20):idx] - opens[max(0, idx - 20):idx]))
                    if avg_body > 0 and down_move > avg_body * 1.8:
                        obs.append({
                            "type": "bearish", "idx": idx,
                            "high": float(highs[idx]), "low": float(opens[idx]),
                            "mitigated": float(highs[idx]) < float(max(highs[idx + 1:])) if idx + 1 < n else False
                        })

        return sorted(obs, key=lambda x: x["idx"], reverse=True)[:8]

    # ───────────────────── BREAKER BLOCKS ───────────────────

    def _find_breaker_blocks(self, df, order_blocks):
        """An OB that fails becomes a breaker block (support becomes resistance & vice versa)"""
        breakers = []
        current = float(df["close"].iloc[-1])
        for ob in order_blocks:
            if ob.get("mitigated"):
                # Flipped OB = breaker
                breakers.append({
                    "type": "bearish" if ob["type"] == "bullish" else "bullish",
                    "high": ob["high"], "low": ob["low"],
                    "origin": f"failed_{ob['type']}_ob",
                    "active": ob["low"] <= current <= ob["high"]
                })
        return breakers

    # ───────────────────── FAIR VALUE GAPS (ICT) ────────────

    def _find_fvg_ict(self, df):
        fvgs = []
        n = len(df)
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        current = float(closes[-1])

        for i in range(2, min(n, 80)):
            idx = n - 1 - i
            if idx < 1:
                break
            # Bullish FVG: candle[i-1] high < candle[i+1] low (gap up)
            if lows[idx + 1] > highs[idx - 1]:
                gap_size = float(lows[idx + 1] - highs[idx - 1])
                fvgs.append({
                    "type": "bullish", "idx": idx,
                    "high": float(lows[idx + 1]),
                    "low": float(highs[idx - 1]),
                    "size": gap_size,
                    "filled": current <= float(highs[idx - 1])
                })
            # Bearish FVG: candle[i-1] low > candle[i+1] high (gap down)
            if highs[idx + 1] < lows[idx - 1]:
                gap_size = float(lows[idx - 1] - highs[idx + 1])
                fvgs.append({
                    "type": "bearish", "idx": idx,
                    "high": float(lows[idx - 1]),
                    "low": float(highs[idx + 1]),
                    "size": gap_size,
                    "filled": current >= float(lows[idx - 1])
                })

        return sorted(fvgs, key=lambda x: x["idx"], reverse=True)[:10]

    # ───────────────────── FVG INVERSIONS ───────────────────

    def _detect_fvg_inversions(self, fvgs, current_price):
        """A filled FVG that now acts as opposite level (support↔resistance)"""
        inversions = []
        for fvg in fvgs:
            if fvg.get("filled"):
                new_type = "bearish" if fvg["type"] == "bullish" else "bullish"
                in_zone = fvg["low"] <= current_price <= fvg["high"]
                inversions.append({
                    "original_type": fvg["type"],
                    "inverted_type": new_type,
                    "high": fvg["high"], "low": fvg["low"],
                    "price_in_zone": in_zone
                })
        return inversions[:3]

    # ───────────────────── LIQUIDITY SWEEPS ─────────────────

    def _detect_liquidity_sweeps(self, df, swing_h, swing_l):
        if len(df) < 20:
            return {"buy_side": False, "sell_side": False}

        current = float(df["close"].iloc[-1])
        recent_high = float(df["high"].iloc[-1])
        recent_low = float(df["low"].iloc[-1])

        buy_side_swept = False
        sell_side_swept = False
        sweep_details = {}

        # Buy-side liquidity: stops above swing highs
        for sh in swing_h[-5:]:
            # Price wicked above the high but closed below = sweep
            if recent_high > sh["price"] and current < sh["price"]:
                buy_side_swept = True
                sweep_details["buy_side_level"] = sh["price"]
                break

        # Sell-side liquidity: stops below swing lows
        for sl in swing_l[-5:]:
            if recent_low < sl["price"] and current > sl["price"]:
                sell_side_swept = True
                sweep_details["sell_side_level"] = sl["price"]
                break

        # Equal highs/lows = resting liquidity
        equal_highs = self._find_equal_levels([s["price"] for s in swing_h[-8:]], threshold=0.0003)
        equal_lows = self._find_equal_levels([s["price"] for s in swing_l[-8:]], threshold=0.0003)

        return {
            "buy_side_swept": buy_side_swept,
            "sell_side_swept": sell_side_swept,
            **sweep_details,
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "signal": "bullish" if sell_side_swept else ("bearish" if buy_side_swept else "neutral")
        }

    def _find_equal_levels(self, prices, threshold=0.0003):
        clusters = []
        for i in range(len(prices)):
            for j in range(i + 1, len(prices)):
                if prices[i] > 0 and abs(prices[i] - prices[j]) / prices[i] < threshold:
                    clusters.append(round((prices[i] + prices[j]) / 2, 5))
        return list(set(clusters))[:3]

    # ───────────────────── OPTIMAL TRADE ENTRY (OTE) ────────

    def _calculate_ote(self, swing_h, swing_l, current_price):
        if len(swing_h) < 1 or len(swing_l) < 1:
            return {"in_ote": False}

        # Find the most recent swing range
        last_h = swing_h[-1]["price"]
        last_l = swing_l[-1]["price"]

        # Make sure we have a valid range
        if last_h <= last_l:
            return {"in_ote": False}

        rng = last_h - last_l
        fib_618 = last_h - rng * 0.618
        fib_786 = last_h - rng * 0.786
        fib_705 = last_h - rng * 0.705  # sweet spot

        # Check if price is in OTE zone
        in_ote_long = fib_786 <= current_price <= fib_618
        in_ote_short = (last_l + rng * 0.618) <= current_price <= (last_l + rng * 0.786)

        return {
            "in_ote": in_ote_long or in_ote_short,
            "ote_long": in_ote_long,
            "ote_short": in_ote_short,
            "fib_618": round(fib_618, 5),
            "fib_705": round(fib_705, 5),
            "fib_786": round(fib_786, 5),
            "swing_high": last_h,
            "swing_low": last_l,
        }

    # ───────────────────── KILL ZONES ───────────────────────

    def _get_kill_zone(self, df):
        try:
            last_ts = df.index[-1]
            if hasattr(last_ts, 'hour'):
                h = last_ts.hour
            else:
                h = pd.Timestamp(last_ts).hour
        except Exception:
            return {"session": "unknown", "in_kill_zone": False}

        # UTC-based kill zones
        if 2 <= h <= 5:
            return {"session": "asian", "in_kill_zone": True, "quality": "moderate",
                    "note": "Asian session — lower volatility, range formation"}
        elif 7 <= h <= 10:
            return {"session": "london_open", "in_kill_zone": True, "quality": "high",
                    "note": "London open kill zone — highest manipulation probability"}
        elif 12 <= h <= 15:
            return {"session": "ny_open", "in_kill_zone": True, "quality": "high",
                    "note": "New York open kill zone — maximum liquidity"}
        elif 15 <= h <= 17:
            return {"session": "ny_pm", "in_kill_zone": True, "quality": "moderate",
                    "note": "NY afternoon — continuation or reversal"}
        else:
            return {"session": "off_hours", "in_kill_zone": False, "quality": "low",
                    "note": "Outside kill zones — avoid new entries"}

    # ───────────────────── POWER OF 3 ──────────────────────

    def _detect_power_of_3(self, df):
        """
        ICT Power of 3: Accumulation → Manipulation → Distribution
        Detect which phase the market is currently in for the session.
        """
        if len(df) < 20:
            return {"phase": "unknown"}

        try:
            last_ts = df.index[-1]
            h = last_ts.hour if hasattr(last_ts, 'hour') else pd.Timestamp(last_ts).hour
        except Exception:
            return {"phase": "unknown"}

        # Session data (last ~16 candles = 4 hours on 15m)
        session_data = df.tail(16)
        if len(session_data) < 8:
            return {"phase": "unknown"}

        opens = session_data["open"].values
        closes = session_data["close"].values
        highs = session_data["high"].values
        lows = session_data["low"].values

        session_open = float(opens[0])
        session_high = float(np.max(highs))
        session_low = float(np.min(lows))
        current = float(closes[-1])
        session_range = session_high - session_low

        if session_range == 0:
            return {"phase": "unknown"}

        # Volatility in first vs second half
        first_half = session_data.iloc[:len(session_data) // 2]
        second_half = session_data.iloc[len(session_data) // 2:]

        first_range = float(first_half["high"].max() - first_half["low"].min())
        second_range = float(second_half["high"].max() - second_half["low"].min())

        # Accumulation: tight range, low volatility
        if first_range < session_range * 0.4 and second_range < session_range * 0.4:
            phase = "accumulation"
            signal = "wait"
        # Manipulation: false move (e.g., sweep of Asian high/low)
        elif first_range > session_range * 0.5 and second_range > first_range * 0.8:
            phase = "manipulation"
            # Direction of manipulation = opposite of real move
            if current < session_open:
                signal = "bullish"  # Manipulated sellers, expect reversal up
            else:
                signal = "bearish"
        # Distribution: trending move after manipulation
        elif second_range > first_range * 1.5:
            phase = "distribution"
            signal = "bullish" if current > session_open else "bearish"
        else:
            phase = "developing"
            signal = "neutral"

        return {
            "phase": phase,
            "signal": signal,
            "session_open": round(session_open, 5),
            "session_range": round(session_range, 5),
        }

    # ───────────────────── JUDAS SWING ─────────────────────

    def _detect_judas_swing(self, df):
        """
        Judas Swing: false breakout at session open designed to trap traders.
        Price moves one direction to grab liquidity, then reverses.
        """
        if len(df) < 12:
            return {"detected": False}

        # Look at last 12 candles (3 hours on 15m)
        recent = df.tail(12)
        opens = recent["open"].values
        closes = recent["close"].values
        highs = recent["high"].values
        lows = recent["low"].values

        session_open = float(opens[0])
        current = float(closes[-1])

        # Early high then reversal down = bearish Judas
        early_high = float(np.max(highs[:4]))
        late_close = float(closes[-1])
        if early_high > session_open and late_close < session_open:
            move_up = early_high - session_open
            move_down = session_open - late_close
            if move_down > move_up * 0.8:
                return {"detected": True, "direction": "bearish",
                        "type": "false_high_reversal",
                        "false_level": round(early_high, 5)}

        # Early low then reversal up = bullish Judas
        early_low = float(np.min(lows[:4]))
        if early_low < session_open and late_close > session_open:
            move_down = session_open - early_low
            move_up = late_close - session_open
            if move_up > move_down * 0.8:
                return {"detected": True, "direction": "bullish",
                        "type": "false_low_reversal",
                        "false_level": round(early_low, 5)}

        return {"detected": False}

    # ───────────────────── INSTITUTIONAL REFERENCE POINTS ───

    def _institutional_ref_points(self, df):
        """Weekly open, daily open, midnight open — key institutional levels"""
        try:
            closes = df["close"]
            opens = df["open"]
            current = float(closes.iloc[-1])

            # Daily open (approximate: find first candle of today)
            today = df.index[-1].date() if hasattr(df.index[-1], 'date') else None
            daily_open = None
            weekly_open = None

            if today:
                today_data = df[df.index.date == today]
                if not today_data.empty:
                    daily_open = float(today_data["open"].iloc[0])

                # Weekly open
                monday = today
                while hasattr(monday, 'weekday') and monday.weekday() != 0:
                    monday = monday - pd.Timedelta(days=1)
                week_data = df[df.index.date >= monday]
                if not week_data.empty:
                    weekly_open = float(week_data["open"].iloc[0])

            result = {}
            if daily_open:
                result["daily_open"] = round(daily_open, 5)
                result["above_daily_open"] = current > daily_open
            if weekly_open:
                result["weekly_open"] = round(weekly_open, 5)
                result["above_weekly_open"] = current > weekly_open

            return result
        except Exception:
            return {}

    # ───────────────────── HTF ICT ANALYSIS ─────────────────

    def _htf_ict_analysis(self, df, tf_name):
        """Simplified ICT analysis for higher timeframes"""
        sh, sl = self._find_swing_points(df, lookback=3)
        current = float(df["close"].iloc[-1])

        # HTF bias from structure
        bias = "neutral"
        if len(sh) >= 2 and len(sl) >= 2:
            hh = sh[-1]["price"] > sh[-2]["price"]
            hl = sl[-1]["price"] > sl[-2]["price"]
            lh = sh[-1]["price"] < sh[-2]["price"]
            ll = sl[-1]["price"] < sl[-2]["price"]
            if hh and hl:
                bias = "bullish"
            elif lh and ll:
                bias = "bearish"

        # HTF FVGs
        fvgs = self._find_fvg_ict(df)
        unfilled_bull = [f for f in fvgs if f["type"] == "bullish" and not f.get("filled")]
        unfilled_bear = [f for f in fvgs if f["type"] == "bearish" and not f.get("filled")]

        # HTF OBs
        obs = self._find_order_blocks_ict(df, sh, sl)
        active_bull_ob = [o for o in obs if o["type"] == "bullish" and not o.get("mitigated")]
        active_bear_ob = [o for o in obs if o["type"] == "bearish" and not o.get("mitigated")]

        return {
            "timeframe": tf_name,
            "bias": bias,
            "unfilled_bull_fvg": len(unfilled_bull),
            "unfilled_bear_fvg": len(unfilled_bear),
            "active_bull_ob": len(active_bull_ob),
            "active_bear_ob": len(active_bear_ob),
            "swing_highs": len(sh),
            "swing_lows": len(sl),
        }

    # ───────────────────── ICT COMPOSITE SCORING ────────────

    def _calculate_ict_bias(self, mss, choch, displacement, obs, breakers,
                            fvgs, inversions, liquidity, ote, kill_zone,
                            po3, judas, current_price, htf_ict):
        bull_score = 0
        bear_score = 0
        factors = []

        # MSS (very high weight)
        if mss.get("detected"):
            w = 20
            if mss["direction"] == "bullish":
                bull_score += w
                factors.append(("mss_bullish", w))
            else:
                bear_score += w
                factors.append(("mss_bearish", w))

        # CHoCH (highest weight — trend change)
        if choch.get("detected"):
            w = 25
            if choch["direction"] == "bullish":
                bull_score += w
                factors.append(("choch_bullish", w))
            else:
                bear_score += w
                factors.append(("choch_bearish", w))

        # Displacement
        if displacement.get("detected"):
            w = 15
            if displacement["direction"] == "bullish":
                bull_score += w
                factors.append(("displacement_bullish", w))
            else:
                bear_score += w
                factors.append(("displacement_bearish", w))

        # Active (unmitigated) Order Blocks at price
        for ob in obs[:5]:
            if not ob.get("mitigated") and ob["low"] <= current_price <= ob["high"]:
                w = 18
                if ob["type"] == "bullish":
                    bull_score += w
                    factors.append(("at_bullish_ob", w))
                else:
                    bear_score += w
                    factors.append(("at_bearish_ob", w))

        # Breaker Blocks
        for bb in breakers[:3]:
            if bb.get("active"):
                w = 12
                if bb["type"] == "bullish":
                    bull_score += w
                    factors.append(("breaker_block_bull", w))
                else:
                    bear_score += w
                    factors.append(("breaker_block_bear", w))

        # FVGs at price
        for fvg in fvgs[:5]:
            if not fvg.get("filled") and fvg["low"] <= current_price <= fvg["high"]:
                w = 14
                if fvg["type"] == "bullish":
                    bull_score += w
                    factors.append(("in_bullish_fvg", w))
                else:
                    bear_score += w
                    factors.append(("in_bearish_fvg", w))

        # FVG Inversions
        for inv in inversions:
            if inv.get("price_in_zone"):
                w = 10
                if inv["inverted_type"] == "bullish":
                    bull_score += w
                    factors.append(("fvg_inversion_bull", w))
                else:
                    bear_score += w
                    factors.append(("fvg_inversion_bear", w))

        # Liquidity sweep
        if liquidity.get("sell_side_swept"):
            bull_score += 20
            factors.append(("sell_side_liquidity_swept", 20))
        if liquidity.get("buy_side_swept"):
            bear_score += 20
            factors.append(("buy_side_liquidity_swept", 20))

        # OTE
        if ote.get("ote_long"):
            bull_score += 16
            factors.append(("in_ote_long", 16))
        if ote.get("ote_short"):
            bear_score += 16
            factors.append(("in_ote_short", 16))

        # Kill zone bonus
        if kill_zone.get("in_kill_zone") and kill_zone.get("quality") == "high":
            bull_score = int(bull_score * 1.15)
            bear_score = int(bear_score * 1.15)
            factors.append(("kill_zone_active", 5))

        # Power of 3
        if po3.get("signal") == "bullish":
            bull_score += 12
            factors.append(("po3_bullish", 12))
        elif po3.get("signal") == "bearish":
            bear_score += 12
            factors.append(("po3_bearish", 12))

        # Judas Swing
        if judas.get("detected"):
            w = 18
            if judas["direction"] == "bullish":
                bull_score += w
                factors.append(("judas_swing_bullish", w))
            else:
                bear_score += w
                factors.append(("judas_swing_bearish", w))

        # HTF confluence bonus
        for tf_key, htf in htf_ict.items():
            htf_bias = htf.get("bias", "neutral")
            if htf_bias == "bullish":
                w = 15 if tf_key == "4h" else 10
                bull_score += w
                factors.append((f"htf_{tf_key}_bullish", w))
            elif htf_bias == "bearish":
                w = 15 if tf_key == "4h" else 10
                bear_score += w
                factors.append((f"htf_{tf_key}_bearish", w))

        total = bull_score + bear_score
        if total == 0:
            return "neutral", 0, factors

        if bull_score > bear_score:
            bias = "bullish"
            ict_score = round((bull_score / max(bull_score + bear_score, 1)) * 100, 1)
        elif bear_score > bull_score:
            bias = "bearish"
            ict_score = round((bear_score / max(bull_score + bear_score, 1)) * 100, 1)
        else:
            bias = "neutral"
            ict_score = 50

        return bias, ict_score, factors
