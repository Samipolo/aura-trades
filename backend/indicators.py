"""
AURA TRADES - Technical Indicators Engine
Computes all required indicators: EMA, BB, VWAPs, Volume Profiles, IB, etc.
"""

import pandas as pd
import numpy as np
from scipy import stats
from config import INDICATOR_CONFIG


class IndicatorEngine:
    """Calculates all technical indicators on 15m data"""

    def __init__(self):
        self.config = INDICATOR_CONFIG

    def calculate_all(self, df_15m: pd.DataFrame, df_daily: pd.DataFrame = None) -> dict:
        """Calculate all indicators and return enriched dataframe + levels"""
        if df_15m.empty or len(df_15m) < 200:
            return None

        result = {
            "df": df_15m.copy(),
            "levels": {},
            "signals": {}
        }

        df = result["df"]

        # EMA 50 & 200
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

        # Bollinger Bands (50 EMA, 2.5 StdDev)
        df["bb_mid"] = df["close"].ewm(span=50, adjust=False).mean()
        bb_std = df["close"].rolling(window=50).std()
        df["bb_upper"] = df["bb_mid"] + (2.5 * bb_std)
        df["bb_lower"] = df["bb_mid"] - (2.5 * bb_std)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

        # RSI
        df["rsi"] = self._calculate_rsi(df["close"], 14)

        # MACD
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ATR (14 period)
        df["atr"] = self._calculate_atr(df, 14)

        # ADX
        df["adx"] = self._calculate_adx(df, 14)

        # VWAPs
        result["levels"]["daily_vwap"] = self._calculate_vwap(df, "daily")
        result["levels"]["weekly_vwap"] = self._calculate_vwap(df, "weekly")
        result["levels"]["monthly_vwap"] = self._calculate_vwap(df, "monthly")
        result["levels"]["prev_day_vwap"] = self._calculate_prev_vwap(df, "daily")
        result["levels"]["prev_week_vwap"] = self._calculate_prev_vwap(df, "weekly")

        # Volume Profile
        result["levels"]["daily_vpoc"] = self._calculate_volume_profile(df, "daily")
        result["levels"]["prev_day_vpoc"] = self._calculate_prev_volume_profile(df, "daily")
        result["levels"]["weekly_vpoc"] = self._calculate_volume_profile(df, "weekly")
        result["levels"]["monthly_vpoc"] = self._calculate_volume_profile(df, "monthly")

        # Session Initial Balance
        result["levels"]["session_ib"] = self._calculate_initial_balance(df)

        # Market regime
        result["signals"]["trend"] = self._determine_trend(df)
        result["signals"]["momentum"] = self._determine_momentum(df)
        result["signals"]["volatility"] = self._determine_volatility(df)

        return result

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()

    def _calculate_adx(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average Directional Index"""
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self._calculate_atr(df, 1) * 1  # single period TR
        atr = tr.rolling(window=period).mean()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.rolling(window=period).mean()
        return adx

    def _calculate_vwap(self, df: pd.DataFrame, period_type: str) -> dict:
        """Calculate anchored VWAP for current period"""
        if df.empty or "volume" not in df.columns:
            return {"value": None, "upper": None, "lower": None}

        df_copy = df.copy()
        df_copy["typical_price"] = (df_copy["high"] + df_copy["low"] + df_copy["close"]) / 3

        # Determine period start
        now = df_copy.index[-1]
        if period_type == "daily":
            start = now.normalize()
        elif period_type == "weekly":
            start = now - pd.Timedelta(days=now.weekday())
            start = start.normalize()
        elif period_type == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = df_copy.index[0]

        mask = df_copy.index >= start
        period_data = df_copy[mask]

        if period_data.empty:
            return {"value": float(df_copy["close"].iloc[-1]), "upper": None, "lower": None}

        # If volume is 0 (forex), use equal weight VWAP (essentially a TWAP)
        if period_data["volume"].sum() == 0:
            period_data = period_data.copy()
            period_data["volume"] = 1

        cumulative_vol = period_data["volume"].cumsum()
        cumulative_tp_vol = (period_data["typical_price"] * period_data["volume"]).cumsum()
        vwap = cumulative_tp_vol / cumulative_vol

        # VWAP bands (1 std dev)
        vwap_val = float(vwap.iloc[-1]) if not vwap.empty else float(df_copy["close"].iloc[-1])
        squared_diff = ((period_data["typical_price"] - vwap) ** 2 * period_data["volume"]).cumsum()
        variance = squared_diff / cumulative_vol
        std_dev = float(np.sqrt(variance.iloc[-1])) if not variance.empty else 0

        return {
            "value": vwap_val,
            "upper": vwap_val + std_dev,
            "lower": vwap_val - std_dev
        }

    def _calculate_prev_vwap(self, df: pd.DataFrame, period_type: str) -> dict:
        """Calculate previous period's VWAP final value"""
        if df.empty or "volume" not in df.columns:
            return {"value": None}

        df_copy = df.copy()
        df_copy["typical_price"] = (df_copy["high"] + df_copy["low"] + df_copy["close"]) / 3

        now = df_copy.index[-1]
        if period_type == "daily":
            current_start = now.normalize()
            prev_start = current_start - pd.Timedelta(days=1)
            prev_end = current_start
        elif period_type == "weekly":
            current_start = now - pd.Timedelta(days=now.weekday())
            current_start = current_start.normalize()
            prev_start = current_start - pd.Timedelta(weeks=1)
            prev_end = current_start
        else:
            return {"value": None}

        mask = (df_copy.index >= prev_start) & (df_copy.index < prev_end)
        period_data = df_copy[mask]

        if period_data.empty or period_data["volume"].sum() == 0:
            return {"value": None}

        total_vol = period_data["volume"].sum()
        vwap_val = float((period_data["typical_price"] * period_data["volume"]).sum() / total_vol)

        return {"value": vwap_val}

    def _calculate_volume_profile(self, df: pd.DataFrame, period_type: str) -> dict:
        """Calculate Volume Profile POC (Point of Control) for current period"""
        if df.empty or "volume" not in df.columns:
            return {"poc": None, "vah": None, "val": None}

        df_copy = df.copy()
        now = df_copy.index[-1]

        if period_type == "daily":
            start = now.normalize()
        elif period_type == "weekly":
            start = now - pd.Timedelta(days=now.weekday())
            start = start.normalize()
        elif period_type == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = df_copy.index[0]

        mask = df_copy.index >= start
        period_data = df_copy[mask]

        if period_data.empty or len(period_data) < 2:
            return {"poc": None, "vah": None, "val": None}

        return self._compute_volume_profile(period_data)

    def _calculate_prev_volume_profile(self, df: pd.DataFrame, period_type: str) -> dict:
        """Calculate previous period's Volume Profile"""
        if df.empty or "volume" not in df.columns:
            return {"poc": None, "vah": None, "val": None}

        df_copy = df.copy()
        now = df_copy.index[-1]

        if period_type == "daily":
            current_start = now.normalize()
            prev_start = current_start - pd.Timedelta(days=1)
            prev_end = current_start
        else:
            return {"poc": None, "vah": None, "val": None}

        mask = (df_copy.index >= prev_start) & (df_copy.index < prev_end)
        period_data = df_copy[mask]

        if period_data.empty or len(period_data) < 2:
            return {"poc": None, "vah": None, "val": None}

        return self._compute_volume_profile(period_data)

    def _compute_volume_profile(self, data: pd.DataFrame) -> dict:
        """Compute volume profile with POC, VAH, VAL"""
        price_range = data["high"].max() - data["low"].min()
        if price_range == 0:
            return {"poc": float(data["close"].iloc[-1]), "vah": None, "val": None}

        num_bins = min(50, max(10, len(data)))
        bins = np.linspace(data["low"].min(), data["high"].max(), num_bins)
        volume_at_price = np.zeros(num_bins - 1)

        for _, row in data.iterrows():
            bar_range = row["high"] - row["low"]
            if bar_range == 0:
                idx = np.searchsorted(bins, row["close"]) - 1
                idx = max(0, min(idx, len(volume_at_price) - 1))
                volume_at_price[idx] += row["volume"]
            else:
                for i in range(len(bins) - 1):
                    overlap_low = max(bins[i], row["low"])
                    overlap_high = min(bins[i + 1], row["high"])
                    if overlap_high > overlap_low:
                        proportion = (overlap_high - overlap_low) / bar_range
                        volume_at_price[i] += row["volume"] * proportion

        # POC - price level with most volume
        poc_idx = np.argmax(volume_at_price)
        poc = float((bins[poc_idx] + bins[poc_idx + 1]) / 2)

        # Value Area (70% of volume)
        total_vol = volume_at_price.sum()
        if total_vol == 0:
            return {"poc": poc, "vah": None, "val": None}

        sorted_indices = np.argsort(volume_at_price)[::-1]
        cumulative_vol = 0
        va_indices = []
        for idx in sorted_indices:
            cumulative_vol += volume_at_price[idx]
            va_indices.append(idx)
            if cumulative_vol >= total_vol * 0.7:
                break

        va_indices.sort()
        val_price = float((bins[va_indices[0]] + bins[va_indices[0] + 1]) / 2)
        vah_price = float((bins[va_indices[-1]] + bins[va_indices[-1] + 1]) / 2)

        return {"poc": poc, "vah": vah_price, "val": val_price}

    def _calculate_initial_balance(self, df: pd.DataFrame) -> dict:
        """Calculate Session Initial Balance (first hour of session)"""
        if df.empty:
            return {"high": None, "low": None, "mid": None}

        # Get today's data
        now = df.index[-1]
        today_start = now.normalize()
        today_data = df[df.index >= today_start]

        if today_data.empty:
            return {"high": None, "low": None, "mid": None}

        # First hour = first 4 candles of 15m
        ib_data = today_data.head(4)
        if ib_data.empty:
            return {"high": None, "low": None, "mid": None}

        ib_high = float(ib_data["high"].max())
        ib_low = float(ib_data["low"].min())
        ib_mid = (ib_high + ib_low) / 2

        return {"high": ib_high, "low": ib_low, "mid": ib_mid}

    def _determine_trend(self, df: pd.DataFrame) -> str:
        """Determine current trend state"""
        if df.empty or len(df) < 200:
            return "neutral"

        current = df.iloc[-1]
        ema50 = current.get("ema_50")
        ema200 = current.get("ema_200")
        close = current["close"]

        if pd.isna(ema50) or pd.isna(ema200):
            return "neutral"

        if close > ema50 > ema200:
            return "strong_bullish"
        elif close > ema50 and ema50 < ema200:
            return "bullish"
        elif close < ema50 < ema200:
            return "strong_bearish"
        elif close < ema50 and ema50 > ema200:
            return "bearish"
        else:
            return "neutral"

    def _determine_momentum(self, df: pd.DataFrame) -> str:
        """Determine momentum state from RSI and MACD"""
        if df.empty:
            return "neutral"

        current = df.iloc[-1]
        rsi = current.get("rsi")
        macd_hist = current.get("macd_hist")

        if pd.isna(rsi) or pd.isna(macd_hist):
            return "neutral"

        if rsi > 60 and macd_hist > 0:
            return "bullish"
        elif rsi < 40 and macd_hist < 0:
            return "bearish"
        elif rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        else:
            return "neutral"

    def _determine_volatility(self, df: pd.DataFrame) -> str:
        """Determine volatility regime"""
        if df.empty or "bb_width" not in df.columns:
            return "normal"

        current_width = df["bb_width"].iloc[-1]
        avg_width = df["bb_width"].rolling(100).mean().iloc[-1]

        if pd.isna(current_width) or pd.isna(avg_width):
            return "normal"

        if current_width > avg_width * 1.5:
            return "high"
        elif current_width < avg_width * 0.5:
            return "low_squeeze"
        else:
            return "normal"
