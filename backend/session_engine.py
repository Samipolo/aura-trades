"""
AURA TRADES - Session Analysis Engine
Institutional-grade session mechanics: London IB, Asian Range, NY Open, Session VWAP
Implements professional session-based trading strategies used by institutional desks.
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz


class SessionAnalysisEngine:
    """
    Analyzes market sessions with institutional precision:
    - London Session Initial Balance (first 60 min)
    - Asian Session Range (consolidation/breakout)
    - NY Open Drive / Reversal
    - Session VWAP with standard deviation bands
    - Opening Range Breakout (ORB)
    - Session volume profile
    - Session gap analysis
    - Pre-market positioning
    """

    # Session times in UTC
    SESSIONS = {
        "asian": {"start": time(0, 0), "end": time(8, 0)},
        "london": {"start": time(7, 0), "end": time(16, 0)},
        "new_york": {"start": time(12, 0), "end": time(21, 0)},
        "london_ib": {"start": time(7, 0), "end": time(8, 0)},  # First 60min
        "ny_ib": {"start": time(12, 0), "end": time(13, 0)},  # First 60min
    }

    # Kill zone times (highest probability)
    KILL_ZONES = {
        "london_open": {"start": time(7, 0), "end": time(9, 0)},
        "ny_open": {"start": time(12, 0), "end": time(14, 0)},
        "london_close": {"start": time(15, 0), "end": time(16, 30)},
        "asian_late": {"start": time(5, 0), "end": time(7, 0)},
    }

    def __init__(self):
        self.utc = pytz.utc

    def analyze(self, df: pd.DataFrame) -> dict:
        """Full session analysis on 15m data"""
        if df is None or df.empty or len(df) < 50:
            return self._empty_result()

        try:
            result = {}

            # Ensure UTC index
            if df.index.tz is None:
                df = df.copy()
                df.index = df.index.tz_localize("UTC")

            # Current session identification
            result["current_session"] = self._identify_current_session(df)

            # London Initial Balance
            result["london_ib"] = self._london_initial_balance(df)

            # Asian Session Range
            result["asian_range"] = self._asian_session_range(df)

            # NY Open analysis
            result["ny_open"] = self._ny_open_analysis(df)

            # Session VWAP
            result["session_vwap"] = self._session_vwap(df)

            # Opening Range Breakout
            result["orb"] = self._opening_range_breakout(df)

            # Session gap analysis
            result["session_gap"] = self._session_gap_analysis(df)

            # Multi-session context
            result["session_context"] = self._multi_session_context(df)

            # Session volume profile
            result["session_volume"] = self._session_volume_analysis(df)

            # Kill zone analysis
            result["kill_zone"] = self._kill_zone_analysis(df)

            # Session statistics (historical)
            result["session_stats"] = self._session_statistics(df)

            # Composite session signal
            result["signal"] = self._composite_signal(result)
            result["bias"] = result["signal"].get("bias", "neutral")
            result["session_score"] = result["signal"].get("score", 0)

            return result

        except Exception as e:
            print(f"[SessionEngine] Error: {e}")
            return self._empty_result()

    def _identify_current_session(self, df: pd.DataFrame) -> dict:
        """Identify which session is currently active"""
        now = df.index[-1]
        current_time = now.time()

        active_sessions = []
        for name, times in self.SESSIONS.items():
            if self._time_in_range(current_time, times["start"], times["end"]):
                active_sessions.append(name)

        active_kz = None
        for name, times in self.KILL_ZONES.items():
            if self._time_in_range(current_time, times["start"], times["end"]):
                active_kz = name
                break

        # Determine primary session
        primary = "off_hours"
        if "london" in active_sessions:
            primary = "london"
        elif "new_york" in active_sessions:
            primary = "new_york"
        elif "asian" in active_sessions:
            primary = "asian"

        # Session overlap (highest liquidity)
        overlap = "london" in active_sessions and "new_york" in active_sessions

        return {
            "primary": primary,
            "active_sessions": active_sessions,
            "kill_zone": active_kz,
            "overlap": overlap,
            "time_utc": str(current_time)[:5],
        }

    def _london_initial_balance(self, df: pd.DataFrame) -> dict:
        """
        London Session Initial Balance (first 60 minutes: 07:00-08:00 UTC)
        The IB defines the range for the day and provides key reference levels.
        Professional traders use IB extensions (1.5x, 2x, 3x) as targets.
        """
        # Get today's London IB candles
        today = df.index[-1].date()
        ib_start = pd.Timestamp(f"{today} 07:00:00", tz="UTC")
        ib_end = pd.Timestamp(f"{today} 08:00:00", tz="UTC")

        ib_candles = df[(df.index >= ib_start) & (df.index < ib_end)]

        # If today's IB not yet complete, use yesterday's
        if len(ib_candles) < 2:
            yesterday = today - timedelta(days=1)
            ib_start = pd.Timestamp(f"{yesterday} 07:00:00", tz="UTC")
            ib_end = pd.Timestamp(f"{yesterday} 08:00:00", tz="UTC")
            ib_candles = df[(df.index >= ib_start) & (df.index < ib_end)]

        if ib_candles.empty:
            return {"valid": False}

        ib_high = float(ib_candles["high"].max())
        ib_low = float(ib_candles["low"].min())
        ib_range = ib_high - ib_low
        ib_mid = (ib_high + ib_low) / 2

        # Current price position relative to IB
        current = float(df["close"].iloc[-1])

        # IB Extensions
        extensions = {
            "1.5x_up": ib_high + (ib_range * 0.5),
            "2x_up": ib_high + ib_range,
            "3x_up": ib_high + (ib_range * 2),
            "1.5x_down": ib_low - (ib_range * 0.5),
            "2x_down": ib_low - ib_range,
            "3x_down": ib_low - (ib_range * 2),
        }

        # Determine IB status
        if current > ib_high:
            status = "above_ib"
            extension_reached = 0
            if current >= extensions["3x_up"]:
                extension_reached = 3
            elif current >= extensions["2x_up"]:
                extension_reached = 2
            elif current >= extensions["1.5x_up"]:
                extension_reached = 1.5
        elif current < ib_low:
            status = "below_ib"
            extension_reached = 0
            if current <= extensions["3x_down"]:
                extension_reached = 3
            elif current <= extensions["2x_down"]:
                extension_reached = 2
            elif current <= extensions["1.5x_down"]:
                extension_reached = 1.5
        else:
            status = "inside_ib"
            extension_reached = 0

        # IB width relative to ATR (narrow IB = likely breakout day)
        atr_14 = self._calculate_atr(df, 14)
        ib_atr_ratio = ib_range / atr_14 if atr_14 > 0 else 1.0

        # Day type prediction from IB width
        if ib_atr_ratio < 0.4:
            predicted_day = "trend"  # Narrow IB = trend day likely
        elif ib_atr_ratio < 0.7:
            predicted_day = "normal"
        else:
            predicted_day = "range"  # Wide IB = range day likely

        # Breakout confirmation
        breakout_confirmed = False
        if status != "inside_ib":
            # Check if we closed above/below IB for at least 2 candles
            post_ib = df[df.index >= ib_end]
            if len(post_ib) >= 2:
                if status == "above_ib":
                    breakout_confirmed = all(post_ib["close"].iloc[-2:] > ib_high)
                else:
                    breakout_confirmed = all(post_ib["close"].iloc[-2:] < ib_low)

        return {
            "valid": True,
            "ib_high": round(ib_high, 5),
            "ib_low": round(ib_low, 5),
            "ib_mid": round(ib_mid, 5),
            "ib_range": round(ib_range, 5),
            "ib_range_pips": round(ib_range * 10000, 1),
            "status": status,
            "extensions": {k: round(v, 5) for k, v in extensions.items()},
            "extension_reached": extension_reached,
            "ib_atr_ratio": round(ib_atr_ratio, 2),
            "predicted_day_type": predicted_day,
            "breakout_confirmed": breakout_confirmed,
            "signal": "bullish" if status == "above_ib" and breakout_confirmed else
                      "bearish" if status == "below_ib" and breakout_confirmed else "neutral",
        }

    def _asian_session_range(self, df: pd.DataFrame) -> dict:
        """
        Asian Session Range Analysis (00:00-08:00 UTC)
        The Asian range serves as a liquidity pool that London often sweeps.
        Key strategy: Asian range breakout/failure trade.
        """
        today = df.index[-1].date()
        asia_start = pd.Timestamp(f"{today} 00:00:00", tz="UTC")
        asia_end = pd.Timestamp(f"{today} 08:00:00", tz="UTC")

        asia_candles = df[(df.index >= asia_start) & (df.index < asia_end)]

        # Use yesterday if today's Asian session not available
        if len(asia_candles) < 4:
            yesterday = today - timedelta(days=1)
            asia_start = pd.Timestamp(f"{yesterday} 00:00:00", tz="UTC")
            asia_end = pd.Timestamp(f"{yesterday} 08:00:00", tz="UTC")
            asia_candles = df[(df.index >= asia_start) & (df.index < asia_end)]

        if asia_candles.empty:
            return {"valid": False}

        asia_high = float(asia_candles["high"].max())
        asia_low = float(asia_candles["low"].min())
        asia_range = asia_high - asia_low
        asia_mid = (asia_high + asia_low) / 2
        asia_close = float(asia_candles["close"].iloc[-1])

        current = float(df["close"].iloc[-1])

        # Breakout analysis
        if current > asia_high:
            breakout = "bullish"
            breakout_distance = current - asia_high
        elif current < asia_low:
            breakout = "bearish"
            breakout_distance = asia_low - current
        else:
            breakout = "none"
            breakout_distance = 0

        # Sweep detection (price pierced then returned)
        post_asia = df[df.index >= asia_end]
        high_swept = False
        low_swept = False
        if not post_asia.empty:
            high_swept = float(post_asia["high"].max()) > asia_high and current < asia_high
            low_swept = float(post_asia["low"].min()) < asia_low and current > asia_low

        # Asian range width classification
        atr_14 = self._calculate_atr(df, 14)
        range_classification = "tight" if asia_range < atr_14 * 0.5 else \
                              "normal" if asia_range < atr_14 else "wide"

        # Volume analysis during Asian session
        if "volume" in asia_candles.columns:
            asia_vol = float(asia_candles["volume"].sum())
        else:
            asia_vol = 0

        # Directional bias from Asian close position
        close_position = (asia_close - asia_low) / asia_range if asia_range > 0 else 0.5
        if close_position > 0.7:
            asian_bias = "bullish"
        elif close_position < 0.3:
            asian_bias = "bearish"
        else:
            asian_bias = "neutral"

        # Signal: Asian range breakout strategy
        signal = "neutral"
        if breakout == "bullish" and range_classification in ["tight", "normal"]:
            signal = "bullish"
        elif breakout == "bearish" and range_classification in ["tight", "normal"]:
            signal = "bearish"
        elif high_swept:
            signal = "bearish"  # Sweep of highs = smart money selling
        elif low_swept:
            signal = "bullish"  # Sweep of lows = smart money buying

        return {
            "valid": True,
            "asia_high": round(asia_high, 5),
            "asia_low": round(asia_low, 5),
            "asia_mid": round(asia_mid, 5),
            "asia_range": round(asia_range, 5),
            "asia_range_pips": round(asia_range * 10000, 1),
            "range_classification": range_classification,
            "breakout": breakout,
            "breakout_distance_pips": round(breakout_distance * 10000, 1),
            "high_swept": high_swept,
            "low_swept": low_swept,
            "asian_bias": asian_bias,
            "close_position": round(close_position, 2),
            "signal": signal,
        }

    def _ny_open_analysis(self, df: pd.DataFrame) -> dict:
        """
        New York Open Analysis (12:00-14:00 UTC / 8:00-10:00 ET)
        Analyzes the NY open drive vs reversal pattern.
        """
        today = df.index[-1].date()
        ny_start = pd.Timestamp(f"{today} 12:00:00", tz="UTC")
        ny_end = pd.Timestamp(f"{today} 14:00:00", tz="UTC")

        ny_candles = df[(df.index >= ny_start) & (df.index <= ny_end)]

        if len(ny_candles) < 2:
            yesterday = today - timedelta(days=1)
            ny_start = pd.Timestamp(f"{yesterday} 12:00:00", tz="UTC")
            ny_end = pd.Timestamp(f"{yesterday} 14:00:00", tz="UTC")
            ny_candles = df[(df.index >= ny_start) & (df.index <= ny_end)]

        if ny_candles.empty:
            return {"valid": False}

        ny_open = float(ny_candles["open"].iloc[0])
        ny_high = float(ny_candles["high"].max())
        ny_low = float(ny_candles["low"].min())
        current = float(df["close"].iloc[-1])

        # NY open drive direction
        first_move_up = ny_high - ny_open
        first_move_down = ny_open - ny_low

        if first_move_up > first_move_down * 1.5:
            initial_drive = "bullish"
        elif first_move_down > first_move_up * 1.5:
            initial_drive = "bearish"
        else:
            initial_drive = "neutral"

        # Check if drive continued or reversed
        if initial_drive == "bullish":
            drive_held = current > ny_open
        elif initial_drive == "bearish":
            drive_held = current < ny_open
        else:
            drive_held = True

        # NY IB (first hour)
        ny_ib_end = pd.Timestamp(f"{ny_start.date()} 13:00:00", tz="UTC")
        ny_ib = df[(df.index >= ny_start) & (df.index < ny_ib_end)]

        ny_ib_data = {}
        if not ny_ib.empty:
            ny_ib_high = float(ny_ib["high"].max())
            ny_ib_low = float(ny_ib["low"].min())
            ny_ib_data = {
                "high": round(ny_ib_high, 5),
                "low": round(ny_ib_low, 5),
                "range": round(ny_ib_high - ny_ib_low, 5),
                "above": current > ny_ib_high,
                "below": current < ny_ib_low,
            }

        return {
            "valid": True,
            "ny_open_price": round(ny_open, 5),
            "initial_drive": initial_drive,
            "drive_held": drive_held,
            "reversal": not drive_held and initial_drive != "neutral",
            "ny_ib": ny_ib_data,
            "signal": initial_drive if drive_held else
                     ("bearish" if initial_drive == "bullish" else
                      "bullish" if initial_drive == "bearish" else "neutral"),
        }

    def _session_vwap(self, df: pd.DataFrame) -> dict:
        """Session-anchored VWAP with standard deviation bands"""
        today = df.index[-1].date()
        current_time = df.index[-1].time()

        # Determine session start for VWAP anchor
        if self._time_in_range(current_time, time(7, 0), time(16, 0)):
            session_start = pd.Timestamp(f"{today} 07:00:00", tz="UTC")
            session_name = "london"
        elif self._time_in_range(current_time, time(12, 0), time(21, 0)):
            session_start = pd.Timestamp(f"{today} 12:00:00", tz="UTC")
            session_name = "new_york"
        else:
            session_start = pd.Timestamp(f"{today} 00:00:00", tz="UTC")
            session_name = "asian"

        session_df = df[df.index >= session_start].copy()
        if len(session_df) < 3:
            return {"valid": False}

        # Calculate VWAP
        tp = (session_df["high"] + session_df["low"] + session_df["close"]) / 3
        vol = session_df["volume"].replace(0, 1)  # Avoid div by zero
        cum_tp_vol = (tp * vol).cumsum()
        cum_vol = vol.cumsum()
        vwap = cum_tp_vol / cum_vol

        # Standard deviation bands
        squared_diff = ((tp - vwap) ** 2 * vol).cumsum() / cum_vol
        std = np.sqrt(squared_diff)

        current_vwap = float(vwap.iloc[-1])
        current_std = float(std.iloc[-1]) if not np.isnan(float(std.iloc[-1])) else 0
        current_price = float(df["close"].iloc[-1])

        # Position relative to VWAP
        if current_std > 0:
            z_score = (current_price - current_vwap) / current_std
        else:
            z_score = 0

        if z_score > 2:
            position = "extreme_above"
        elif z_score > 1:
            position = "above_1std"
        elif z_score > 0:
            position = "above_vwap"
        elif z_score > -1:
            position = "below_vwap"
        elif z_score > -2:
            position = "below_1std"
        else:
            position = "extreme_below"

        return {
            "valid": True,
            "session": session_name,
            "vwap": round(current_vwap, 5),
            "upper_1std": round(current_vwap + current_std, 5),
            "upper_2std": round(current_vwap + 2 * current_std, 5),
            "lower_1std": round(current_vwap - current_std, 5),
            "lower_2std": round(current_vwap - 2 * current_std, 5),
            "z_score": round(z_score, 2),
            "position": position,
            "signal": "bearish" if z_score > 2 else "bullish" if z_score < -2 else "neutral",
        }

    def _opening_range_breakout(self, df: pd.DataFrame) -> dict:
        """Opening Range Breakout - first 30 min of each session"""
        today = df.index[-1].date()
        current = float(df["close"].iloc[-1])

        # Use London ORB (07:00-07:30 UTC)
        orb_start = pd.Timestamp(f"{today} 07:00:00", tz="UTC")
        orb_end = pd.Timestamp(f"{today} 07:30:00", tz="UTC")

        orb_candles = df[(df.index >= orb_start) & (df.index < orb_end)]
        if len(orb_candles) < 1:
            yesterday = today - timedelta(days=1)
            orb_start = pd.Timestamp(f"{yesterday} 07:00:00", tz="UTC")
            orb_end = pd.Timestamp(f"{yesterday} 07:30:00", tz="UTC")
            orb_candles = df[(df.index >= orb_start) & (df.index < orb_end)]

        if orb_candles.empty:
            return {"valid": False}

        orb_high = float(orb_candles["high"].max())
        orb_low = float(orb_candles["low"].min())
        orb_range = orb_high - orb_low

        if current > orb_high:
            breakout = "bullish"
        elif current < orb_low:
            breakout = "bearish"
        else:
            breakout = "inside"

        return {
            "valid": True,
            "orb_high": round(orb_high, 5),
            "orb_low": round(orb_low, 5),
            "orb_range": round(orb_range, 5),
            "breakout": breakout,
            "signal": breakout if breakout != "inside" else "neutral",
        }

    def _session_gap_analysis(self, df: pd.DataFrame) -> dict:
        """Analyze gaps between sessions (unfilled gaps are targets)"""
        today = df.index[-1].date()
        yesterday = today - timedelta(days=1)

        # Previous session close vs current session open
        prev_close_time = pd.Timestamp(f"{yesterday} 21:00:00", tz="UTC")
        curr_open_time = pd.Timestamp(f"{today} 00:00:00", tz="UTC")

        prev_candles = df[df.index <= prev_close_time]
        curr_candles = df[df.index >= curr_open_time]

        if prev_candles.empty or curr_candles.empty:
            return {"valid": False, "gap": 0, "gap_filled": True}

        prev_close = float(prev_candles["close"].iloc[-1])
        curr_open = float(curr_candles["open"].iloc[0])
        current = float(df["close"].iloc[-1])

        gap = curr_open - prev_close
        gap_pips = gap * 10000

        # Check if gap filled
        if gap > 0:
            gap_filled = float(curr_candles["low"].min()) <= prev_close
        elif gap < 0:
            gap_filled = float(curr_candles["high"].max()) >= prev_close
        else:
            gap_filled = True

        return {
            "valid": True,
            "gap": round(gap, 5),
            "gap_pips": round(gap_pips, 1),
            "gap_direction": "up" if gap > 0 else "down" if gap < 0 else "none",
            "gap_filled": gap_filled,
            "fill_target": round(prev_close, 5) if not gap_filled else None,
            "signal": "bearish" if gap > 0 and not gap_filled else
                     "bullish" if gap < 0 and not gap_filled else "neutral",
        }

    def _multi_session_context(self, df: pd.DataFrame) -> dict:
        """Analyze price action across multiple sessions for context"""
        today = df.index[-1].date()

        sessions_data = []
        for i in range(5):  # Last 5 trading days
            day = today - timedelta(days=i)
            day_candles = df[(df.index.date == day)]
            if day_candles.empty:
                continue

            sessions_data.append({
                "date": str(day),
                "high": float(day_candles["high"].max()),
                "low": float(day_candles["low"].min()),
                "open": float(day_candles["open"].iloc[0]),
                "close": float(day_candles["close"].iloc[-1]),
                "range": float(day_candles["high"].max() - day_candles["low"].min()),
            })

        if not sessions_data:
            return {"valid": False}

        # Trend across sessions
        closes = [s["close"] for s in sessions_data]
        if len(closes) >= 3:
            rising = all(closes[i] <= closes[i-1] for i in range(1, min(4, len(closes))))  # Most recent first
            falling = all(closes[i] >= closes[i-1] for i in range(1, min(4, len(closes))))
            session_trend = "bullish" if rising else "bearish" if falling else "mixed"
        else:
            session_trend = "insufficient"

        # Average range
        ranges = [s["range"] for s in sessions_data]
        avg_range = np.mean(ranges) if ranges else 0

        # Today's range vs average
        today_range = sessions_data[0]["range"] if sessions_data else 0
        range_ratio = today_range / avg_range if avg_range > 0 else 1.0

        return {
            "valid": True,
            "session_trend": session_trend,
            "avg_daily_range": round(avg_range, 5),
            "today_range": round(today_range, 5),
            "range_ratio": round(range_ratio, 2),
            "range_expansion": range_ratio > 1.3,
            "range_contraction": range_ratio < 0.7,
        }

    def _session_volume_analysis(self, df: pd.DataFrame) -> dict:
        """Volume analysis by session"""
        today = df.index[-1].date()
        vol_data = {}

        for session_name, times in self.SESSIONS.items():
            if session_name in ["london_ib", "ny_ib"]:
                continue
            start = pd.Timestamp(f"{today} {times['start']}", tz="UTC")
            end = pd.Timestamp(f"{today} {times['end']}", tz="UTC")
            session_df = df[(df.index >= start) & (df.index < end)]

            if not session_df.empty and "volume" in session_df.columns:
                vol = float(session_df["volume"].sum())
                avg_vol_per_candle = vol / len(session_df) if len(session_df) > 0 else 0
                vol_data[session_name] = {
                    "total_volume": int(vol),
                    "avg_per_candle": round(avg_vol_per_candle, 0),
                    "candles": len(session_df),
                }

        # Determine highest volume session
        max_vol_session = max(vol_data.items(), key=lambda x: x[1]["total_volume"])[0] if vol_data else "unknown"

        return {
            "sessions": vol_data,
            "highest_volume_session": max_vol_session,
        }

    def _kill_zone_analysis(self, df: pd.DataFrame) -> dict:
        """Detailed kill zone analysis"""
        now = df.index[-1]
        current_time = now.time()

        in_kill_zone = False
        active_kz = "none"
        quality = "low"

        for kz_name, times in self.KILL_ZONES.items():
            if self._time_in_range(current_time, times["start"], times["end"]):
                in_kill_zone = True
                active_kz = kz_name
                break

        if in_kill_zone:
            # Kill zone quality based on time within zone
            if active_kz == "london_open":
                quality = "high"
            elif active_kz == "ny_open":
                quality = "high"
            elif active_kz == "london_close":
                quality = "medium"
            else:
                quality = "medium"

        return {
            "in_kill_zone": in_kill_zone,
            "active": active_kz,
            "quality": quality,
            "tradeable": in_kill_zone and quality in ["high", "medium"],
        }

    def _session_statistics(self, df: pd.DataFrame) -> dict:
        """Historical session statistics for probability assessment"""
        if len(df) < 200:
            return {"valid": False}

        # Calculate session-specific stats over last 20 trading days
        london_bullish = 0
        london_total = 0
        asian_breakout_bullish = 0
        asian_breakout_total = 0

        dates = df.index.date
        unique_dates = sorted(set(dates))[-20:]

        for day in unique_dates:
            day_df = df[df.index.date == day]
            if day_df.empty:
                continue

            # London session direction
            london_start = pd.Timestamp(f"{day} 07:00:00", tz="UTC")
            london_end = pd.Timestamp(f"{day} 16:00:00", tz="UTC")
            london_df = day_df[(day_df.index >= london_start) & (day_df.index <= london_end)]
            if len(london_df) >= 4:
                london_total += 1
                if float(london_df["close"].iloc[-1]) > float(london_df["open"].iloc[0]):
                    london_bullish += 1

            # Asian breakout direction
            asia_end = pd.Timestamp(f"{day} 08:00:00", tz="UTC")
            asia_df = day_df[day_df.index < asia_end]
            post_asia = day_df[day_df.index >= asia_end]
            if len(asia_df) >= 2 and len(post_asia) >= 2:
                asia_h = float(asia_df["high"].max())
                asia_l = float(asia_df["low"].min())
                post_h = float(post_asia["high"].max())
                post_l = float(post_asia["low"].min())
                if post_h > asia_h:
                    asian_breakout_total += 1
                    asian_breakout_bullish += 1
                elif post_l < asia_l:
                    asian_breakout_total += 1

        london_bull_pct = (london_bullish / london_total * 100) if london_total > 0 else 50
        asian_bull_pct = (asian_breakout_bullish / asian_breakout_total * 100) if asian_breakout_total > 0 else 50

        return {
            "valid": True,
            "london_bullish_pct": round(london_bull_pct, 1),
            "london_sessions_analyzed": london_total,
            "asian_breakout_bullish_pct": round(asian_bull_pct, 1),
            "asian_breakouts_analyzed": asian_breakout_total,
        }

    def _composite_signal(self, result: dict) -> dict:
        """Generate composite session signal from all session data"""
        bullish_score = 0
        bearish_score = 0
        factors = []

        # London IB
        ib = result.get("london_ib", {})
        if ib.get("valid"):
            if ib["signal"] == "bullish":
                bullish_score += 25
                factors.append("london_ib_breakout_up")
            elif ib["signal"] == "bearish":
                bearish_score += 25
                factors.append("london_ib_breakout_down")
            if ib.get("predicted_day_type") == "trend":
                # Amplify directional conviction on trend days
                bullish_score = int(bullish_score * 1.2)
                bearish_score = int(bearish_score * 1.2)

        # Asian Range
        ar = result.get("asian_range", {})
        if ar.get("valid"):
            if ar["signal"] == "bullish":
                bullish_score += 20
                factors.append("asian_range_bullish")
            elif ar["signal"] == "bearish":
                bearish_score += 20
                factors.append("asian_range_bearish")

        # NY Open
        ny = result.get("ny_open", {})
        if ny.get("valid"):
            if ny["signal"] == "bullish":
                bullish_score += 15
                factors.append("ny_drive_bullish")
            elif ny["signal"] == "bearish":
                bearish_score += 15
                factors.append("ny_drive_bearish")

        # Session VWAP
        vwap = result.get("session_vwap", {})
        if vwap.get("valid"):
            if vwap["signal"] == "bullish":
                bullish_score += 15
                factors.append("vwap_extreme_low")
            elif vwap["signal"] == "bearish":
                bearish_score += 15
                factors.append("vwap_extreme_high")

        # ORB
        orb = result.get("orb", {})
        if orb.get("valid"):
            if orb["signal"] == "bullish":
                bullish_score += 12
                factors.append("orb_breakout_up")
            elif orb["signal"] == "bearish":
                bearish_score += 12
                factors.append("orb_breakout_down")

        # Gap
        gap = result.get("session_gap", {})
        if gap.get("valid"):
            if gap["signal"] == "bullish":
                bullish_score += 10
                factors.append("unfilled_gap_bullish")
            elif gap["signal"] == "bearish":
                bearish_score += 10
                factors.append("unfilled_gap_bearish")

        # Kill zone amplifier
        kz = result.get("kill_zone", {})
        if kz.get("tradeable"):
            bullish_score = int(bullish_score * 1.15)
            bearish_score = int(bearish_score * 1.15)

        total = bullish_score + bearish_score
        if total == 0:
            return {"bias": "neutral", "score": 0, "factors": []}

        if bullish_score > bearish_score * 1.3:
            bias = "bullish"
            score = bullish_score
        elif bearish_score > bullish_score * 1.3:
            bias = "bearish"
            score = bearish_score
        else:
            bias = "neutral"
            score = max(bullish_score, bearish_score) // 2

        return {
            "bias": bias,
            "score": min(100, score),
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "factors": factors,
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        if len(df) < period + 1:
            return float(df["high"].iloc[-1] - df["low"].iloc[-1])
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        tr = np.maximum(high[1:] - low[1:],
                       np.maximum(abs(high[1:] - close[:-1]),
                                 abs(low[1:] - close[:-1])))
        atr = pd.Series(tr).rolling(period).mean().iloc[-1]
        return float(atr) if not np.isnan(atr) else float(high[-1] - low[-1])

    def _time_in_range(self, t: time, start: time, end: time) -> bool:
        """Check if time is within range (handles midnight crossing)"""
        if start <= end:
            return start <= t <= end
        return t >= start or t <= end

    def _empty_result(self) -> dict:
        return {
            "current_session": {"primary": "unknown", "active_sessions": [], "kill_zone": None, "overlap": False},
            "london_ib": {"valid": False},
            "asian_range": {"valid": False},
            "ny_open": {"valid": False},
            "session_vwap": {"valid": False},
            "orb": {"valid": False},
            "session_gap": {"valid": False},
            "session_context": {"valid": False},
            "session_volume": {},
            "kill_zone": {"in_kill_zone": False, "active": "none", "quality": "low", "tradeable": False},
            "session_stats": {"valid": False},
            "signal": {"bias": "neutral", "score": 0, "factors": []},
            "bias": "neutral",
            "session_score": 0,
        }
