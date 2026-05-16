"""
AURA TRADES - Market Regime Detection Engine
Statistical regime classification using Hidden Markov Model concepts,
volatility clustering, fractal analysis, and entropy measures.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class RegimeDetectionEngine:
    """
    Institutional-grade market regime classification:
    - Hidden Markov Model (simplified) regime states
    - Volatility regime (low/normal/high/extreme)
    - Trend regime (trending/ranging/transitioning)
    - Momentum regime (accelerating/decelerating/reversal)
    - Liquidity regime (liquid/illiquid/drying up)
    - Market efficiency (efficient/inefficient)
    - Fractal regime (persistent/anti-persistent/random)
    - Entropy-based disorder measure
    """

    # Regime state definitions
    REGIMES = {
        0: "low_vol_range",      # Quiet, ranging market
        1: "low_vol_trend",      # Smooth trend with low volatility
        2: "high_vol_trend",     # Strong directional move
        3: "high_vol_range",     # Choppy, volatile, no direction
        4: "transition",         # Regime change in progress
    }

    def __init__(self):
        pass

    def analyze(self, df: pd.DataFrame, df_1h: pd.DataFrame = None) -> dict:
        """Full regime analysis"""
        if df is None or df.empty or len(df) < 50:
            return self._empty_result()

        try:
            result = {}

            # Volatility regime
            result["volatility_regime"] = self._volatility_regime(df)

            # Trend regime
            result["trend_regime"] = self._trend_regime(df)

            # HMM-style regime detection
            result["hmm_regime"] = self._hmm_regime(df)

            # Momentum regime
            result["momentum_regime"] = self._momentum_regime(df)

            # Liquidity regime
            result["liquidity_regime"] = self._liquidity_regime(df)

            # Market efficiency
            result["efficiency"] = self._market_efficiency(df)

            # Fractal regime (Hurst exponent)
            result["fractal_regime"] = self._fractal_regime(df)

            # Shannon entropy
            result["entropy"] = self._entropy_analysis(df)

            # Volatility term structure
            result["vol_term_structure"] = self._volatility_term_structure(df)

            # Regime transition probability
            result["transition_prob"] = self._regime_transition(df)

            # HTF regime context
            if df_1h is not None and not df_1h.empty and len(df_1h) > 30:
                result["htf_regime"] = self._htf_regime(df_1h)
            else:
                result["htf_regime"] = {"regime": "unknown", "vol_state": "unknown"}

            # Composite
            result["current_regime"] = self._classify_composite_regime(result)
            result["tradeable"] = self._is_tradeable(result)
            result["optimal_strategy"] = self._optimal_strategy(result)

            return result

        except Exception as e:
            print(f"[RegimeEngine] Error: {e}")
            return self._empty_result()

    def _volatility_regime(self, df: pd.DataFrame) -> dict:
        """Classify volatility regime using multiple measures"""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        n = len(close)

        # ATR-based volatility
        tr = np.maximum(high[1:] - low[1:],
                       np.maximum(abs(high[1:] - close[:-1]),
                                 abs(low[1:] - close[:-1])))
        atr_14 = pd.Series(tr).rolling(14).mean().iloc[-1]
        atr_50 = pd.Series(tr).rolling(min(50, len(tr))).mean().iloc[-1]

        # Realized volatility (annualized)
        returns = np.diff(np.log(close))
        rv_20 = np.std(returns[-20:]) * np.sqrt(252 * 24 * 4)  # 15m bars
        rv_60 = np.std(returns[-min(60, len(returns)):]) * np.sqrt(252 * 24 * 4)

        # Volatility ratio (short-term vs long-term)
        vol_ratio = rv_20 / rv_60 if rv_60 > 0 else 1.0

        # Parkinson volatility (range-based)
        log_hl = np.log(high[-20:] / low[-20:])
        parkinson = np.sqrt(np.sum(log_hl**2) / (4 * 20 * np.log(2)))

        # ATR ratio for regime classification
        atr_ratio = float(atr_14 / atr_50) if atr_50 > 0 else 1.0

        # Classify
        if atr_ratio > 2.0 or vol_ratio > 2.0:
            state = "extreme"
            percentile = 95
        elif atr_ratio > 1.3 or vol_ratio > 1.3:
            state = "high"
            percentile = 75
        elif atr_ratio > 0.8:
            state = "normal"
            percentile = 50
        else:
            state = "low"
            percentile = 25

        # Volatility expansion/compression
        if vol_ratio > 1.5:
            phase = "expanding"
        elif vol_ratio < 0.7:
            phase = "compressing"
        else:
            phase = "stable"

        return {
            "state": state,
            "atr_ratio": round(atr_ratio, 2),
            "vol_ratio": round(vol_ratio, 2),
            "realized_vol_20": round(rv_20, 4),
            "realized_vol_60": round(rv_60, 4),
            "parkinson_vol": round(parkinson, 4),
            "percentile": percentile,
            "phase": phase,
        }

    def _trend_regime(self, df: pd.DataFrame) -> dict:
        """Classify trend regime using ADX, R-squared, and slope analysis"""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        n = len(close)

        # ADX calculation
        adx = self._calculate_adx(high, low, close, 14)

        # Linear regression R-squared (20 periods)
        lookback = min(20, n - 1)
        x = np.arange(lookback)
        y = close[-lookback:]
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Efficiency ratio (Kaufman)
        direction = abs(close[-1] - close[-lookback])
        volatility = np.sum(np.abs(np.diff(close[-lookback:])))
        efficiency_ratio = direction / volatility if volatility > 0 else 0

        # Classify trend
        if adx > 40 and r_squared > 0.7:
            regime = "strong_trend"
        elif adx > 25 and r_squared > 0.4:
            regime = "moderate_trend"
        elif adx < 20 and r_squared < 0.3:
            regime = "range_bound"
        elif adx > 20 and r_squared < 0.3:
            regime = "choppy"
        else:
            regime = "transitioning"

        # Trend direction
        if slope > 0 and close[-1] > close[-lookback]:
            direction_str = "bullish"
        elif slope < 0 and close[-1] < close[-lookback]:
            direction_str = "bearish"
        else:
            direction_str = "neutral"

        return {
            "regime": regime,
            "direction": direction_str,
            "adx": round(adx, 1),
            "r_squared": round(r_squared, 3),
            "efficiency_ratio": round(efficiency_ratio, 3),
            "slope": round(slope, 8),
            "trending": regime in ["strong_trend", "moderate_trend"],
        }

    def _hmm_regime(self, df: pd.DataFrame) -> dict:
        """Simplified Hidden Markov Model regime detection"""
        close = df["close"].values
        n = len(close)

        # Calculate features for regime classification
        returns = np.diff(np.log(close))
        lookback = min(60, len(returns))

        # Rolling statistics
        roll_mean = pd.Series(returns).rolling(10).mean().values[-lookback:]
        roll_std = pd.Series(returns).rolling(10).std().values[-lookback:]

        # Remove NaN
        valid = ~(np.isnan(roll_mean) | np.isnan(roll_std))
        roll_mean = roll_mean[valid]
        roll_std = roll_std[valid]

        if len(roll_mean) < 10:
            return {"regime": "unknown", "state_id": -1, "confidence": 0}

        # Simple regime classification based on mean/std quadrants
        current_mean = roll_mean[-1]
        current_std = roll_std[-1]
        median_std = np.median(roll_std)

        if current_std < median_std:
            if abs(current_mean) > np.std(roll_mean):
                state_id = 1  # Low vol trend
            else:
                state_id = 0  # Low vol range
        else:
            if abs(current_mean) > np.std(roll_mean):
                state_id = 2  # High vol trend
            else:
                state_id = 3  # High vol range

        # Check for transition (recent regime change)
        prev_std = roll_std[-5] if len(roll_std) > 5 else current_std
        if abs(current_std - prev_std) / max(prev_std, 0.0001) > 0.5:
            state_id = 4  # Transition

        regime_name = self.REGIMES.get(state_id, "unknown")

        # Confidence based on how clearly defined the regime is
        std_z = abs(current_std - median_std) / max(np.std(roll_std), 0.0001)
        confidence = min(100, int(std_z * 30 + 40))

        return {
            "regime": regime_name,
            "state_id": state_id,
            "confidence": confidence,
            "mean_return": round(float(current_mean), 6),
            "current_vol": round(float(current_std), 6),
        }

    def _momentum_regime(self, df: pd.DataFrame) -> dict:
        """Classify momentum regime"""
        close = df["close"].values
        n = len(close)

        # Rate of change at multiple scales
        roc_5 = (close[-1] / close[-5] - 1) * 100 if n > 5 else 0
        roc_10 = (close[-1] / close[-10] - 1) * 100 if n > 10 else 0
        roc_20 = (close[-1] / close[-20] - 1) * 100 if n > 20 else 0

        # Acceleration (change in momentum)
        if n > 10:
            momentum_now = close[-1] - close[-5]
            momentum_prev = close[-5] - close[-10]
            acceleration = momentum_now - momentum_prev
        else:
            acceleration = 0

        # RSI for momentum context
        returns = np.diff(close)
        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        rs = avg_gain / max(avg_loss, 0.0001)
        rsi = 100 - (100 / (1 + rs))

        # Classify
        if acceleration > 0 and roc_5 > 0 and roc_10 > 0:
            regime = "accelerating_bullish"
        elif acceleration > 0 and roc_5 < 0 and roc_10 < 0:
            regime = "accelerating_bearish"
        elif acceleration < 0 and roc_5 > 0:
            regime = "decelerating_bullish"
        elif acceleration < 0 and roc_5 < 0:
            regime = "decelerating_bearish"
        elif abs(roc_5) < 0.1 and abs(roc_10) < 0.2:
            regime = "flat"
        else:
            regime = "mixed"

        # Divergence: momentum vs price
        price_higher = close[-1] > close[-20] if n > 20 else False
        momentum_lower = roc_5 < roc_10
        divergence = price_higher and momentum_lower

        return {
            "regime": regime,
            "roc_5": round(roc_5, 3),
            "roc_10": round(roc_10, 3),
            "roc_20": round(roc_20, 3),
            "acceleration": round(float(acceleration), 6),
            "rsi": round(rsi, 1),
            "divergence": divergence,
        }

    def _liquidity_regime(self, df: pd.DataFrame) -> dict:
        """Assess market liquidity conditions"""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        n = len(close)
        lookback = min(30, n - 1)

        # Spread proxy (high-low range / close)
        spreads = (high[-lookback:] - low[-lookback:]) / close[-lookback:]
        avg_spread = np.mean(spreads)
        current_spread = spreads[-1]

        # Volume trend
        vol_recent = np.mean(volume[-10:])
        vol_avg = np.mean(volume[-lookback:])
        vol_ratio = vol_recent / max(vol_avg, 1)

        # Slippage estimation (based on spread widening)
        spread_ratio = current_spread / max(avg_spread, 0.00001)

        # Classify liquidity
        if vol_ratio > 1.3 and spread_ratio < 1.2:
            state = "very_liquid"
        elif vol_ratio > 0.8 and spread_ratio < 1.5:
            state = "liquid"
        elif vol_ratio < 0.5 or spread_ratio > 2.0:
            state = "illiquid"
        elif vol_ratio < 0.3:
            state = "drying_up"
        else:
            state = "normal"

        return {
            "state": state,
            "volume_ratio": round(vol_ratio, 2),
            "spread_ratio": round(spread_ratio, 2),
            "avg_spread_pct": round(avg_spread * 100, 4),
            "tradeable": state in ["very_liquid", "liquid", "normal"],
        }

    def _market_efficiency(self, df: pd.DataFrame) -> dict:
        """Measure market efficiency (how random are returns)"""
        close = df["close"].values
        n = len(close)

        returns = np.diff(np.log(close))
        lookback = min(50, len(returns))
        recent_returns = returns[-lookback:]

        # Variance ratio test (simplified)
        # VR(q) = Var(q-period returns) / (q * Var(1-period returns))
        var_1 = np.var(recent_returns)
        q = 5
        q_returns = np.array([np.sum(recent_returns[i:i+q]) for i in range(0, len(recent_returns)-q, q)])
        var_q = np.var(q_returns) if len(q_returns) > 1 else var_1

        variance_ratio = var_q / (q * var_1) if var_1 > 0 else 1.0

        # Perfect efficiency = VR of 1.0
        # VR > 1 = momentum (positive serial correlation)
        # VR < 1 = mean reversion (negative serial correlation)
        if variance_ratio > 1.3:
            efficiency = "momentum_dominant"
            strategy_hint = "trend_following"
        elif variance_ratio > 0.9:
            efficiency = "efficient"
            strategy_hint = "no_edge"
        elif variance_ratio > 0.7:
            efficiency = "mild_mean_reversion"
            strategy_hint = "mean_reversion"
        else:
            efficiency = "strong_mean_reversion"
            strategy_hint = "mean_reversion"

        # Serial correlation
        auto_corr = np.corrcoef(recent_returns[:-1], recent_returns[1:])[0, 1] if len(recent_returns) > 2 else 0

        return {
            "variance_ratio": round(variance_ratio, 3),
            "efficiency": efficiency,
            "strategy_hint": strategy_hint,
            "auto_correlation": round(float(auto_corr), 3) if not np.isnan(auto_corr) else 0,
        }

    def _fractal_regime(self, df: pd.DataFrame) -> dict:
        """Fractal analysis using Hurst exponent"""
        close = df["close"].values
        n = len(close)

        if n < 50:
            return {"hurst": 0.5, "regime": "random", "persistence": "none"}

        # R/S analysis for Hurst exponent
        series = np.log(close[-100:]) if n >= 100 else np.log(close)
        returns = np.diff(series)

        hurst = self._calculate_hurst(returns)

        if hurst > 0.65:
            regime = "persistent"
            persistence = "strong"
        elif hurst > 0.55:
            regime = "mildly_persistent"
            persistence = "moderate"
        elif hurst > 0.45:
            regime = "random_walk"
            persistence = "none"
        elif hurst > 0.35:
            regime = "mildly_anti_persistent"
            persistence = "mean_reverting"
        else:
            regime = "anti_persistent"
            persistence = "strong_mean_reverting"

        return {
            "hurst": round(hurst, 3),
            "regime": regime,
            "persistence": persistence,
        }

    def _calculate_hurst(self, returns: np.ndarray) -> float:
        """Calculate Hurst exponent via R/S analysis"""
        n = len(returns)
        if n < 20:
            return 0.5

        max_k = min(int(n / 4), 50)
        rs_list = []
        n_list = []

        for k in range(10, max_k, 5):
            rs_vals = []
            for start in range(0, n - k, k):
                chunk = returns[start:start + k]
                mean_val = np.mean(chunk)
                deviate = np.cumsum(chunk - mean_val)
                r = np.max(deviate) - np.min(deviate)
                s = np.std(chunk)
                if s > 0:
                    rs_vals.append(r / s)
            if rs_vals:
                rs_list.append(np.mean(rs_vals))
                n_list.append(k)

        if len(rs_list) < 2:
            return 0.5

        log_rs = np.log(rs_list)
        log_n = np.log(n_list)

        try:
            hurst = np.polyfit(log_n, log_rs, 1)[0]
            return max(0, min(1, hurst))
        except Exception:
            return 0.5

    def _entropy_analysis(self, df: pd.DataFrame) -> dict:
        """Shannon entropy to measure market disorder"""
        close = df["close"].values
        returns = np.diff(close) / close[:-1]
        lookback = min(50, len(returns))
        recent = returns[-lookback:]

        # Discretize returns into bins
        num_bins = 10
        hist, _ = np.histogram(recent, bins=num_bins)
        probs = hist / hist.sum()
        probs = probs[probs > 0]

        # Shannon entropy
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(num_bins)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        if normalized_entropy > 0.85:
            disorder = "high"
            predictability = "low"
        elif normalized_entropy > 0.6:
            disorder = "moderate"
            predictability = "moderate"
        else:
            disorder = "low"
            predictability = "high"

        return {
            "entropy": round(entropy, 3),
            "normalized": round(normalized_entropy, 3),
            "disorder": disorder,
            "predictability": predictability,
        }

    def _volatility_term_structure(self, df: pd.DataFrame) -> dict:
        """Volatility term structure (short vs long-term vol)"""
        close = df["close"].values
        returns = np.diff(np.log(close))

        if len(returns) < 50:
            return {"structure": "flat", "ratio": 1.0}

        vol_5 = np.std(returns[-5:]) * np.sqrt(252 * 24 * 4)
        vol_10 = np.std(returns[-10:]) * np.sqrt(252 * 24 * 4)
        vol_20 = np.std(returns[-20:]) * np.sqrt(252 * 24 * 4)
        vol_50 = np.std(returns[-50:]) * np.sqrt(252 * 24 * 4)

        # Contango = short-term vol < long-term vol (normal)
        # Backwardation = short-term vol > long-term vol (stressed)
        ratio = vol_5 / vol_50 if vol_50 > 0 else 1.0

        if ratio > 1.5:
            structure = "steep_backwardation"  # Stress, vol spike
        elif ratio > 1.1:
            structure = "mild_backwardation"
        elif ratio > 0.9:
            structure = "flat"
        elif ratio > 0.7:
            structure = "contango"  # Normal, calm
        else:
            structure = "steep_contango"

        return {
            "structure": structure,
            "ratio": round(ratio, 2),
            "vol_5": round(vol_5, 4),
            "vol_20": round(vol_20, 4),
            "vol_50": round(vol_50, 4),
        }

    def _regime_transition(self, df: pd.DataFrame) -> dict:
        """Estimate probability of regime change"""
        close = df["close"].values
        n = len(close)

        # Look for signs of regime transition
        returns = np.diff(np.log(close))

        # Rolling volatility change
        if len(returns) < 30:
            return {"transition_probability": 0.2, "signal": "stable"}

        vol_10 = np.std(returns[-10:])
        vol_20 = np.std(returns[-20:])
        vol_30 = np.std(returns[-30:])

        # Volatility acceleration
        vol_change_rate = (vol_10 - vol_20) / max(vol_20, 0.0001)

        # Kurtosis spike (fat tails indicate regime stress)
        from scipy import stats as scipy_stats
        try:
            kurtosis = scipy_stats.kurtosis(returns[-20:])
        except Exception:
            kurtosis = 0

        # Transition probability
        prob = 0.2  # Base probability
        if abs(vol_change_rate) > 0.5:
            prob += 0.3
        if abs(kurtosis) > 3:
            prob += 0.2
        # Mean reversion of vol (extreme vol tends to revert)
        if vol_10 > vol_30 * 2:
            prob += 0.2

        prob = min(prob, 0.95)

        if prob > 0.6:
            signal = "transition_likely"
        elif prob > 0.4:
            signal = "possible_transition"
        else:
            signal = "stable"

        return {
            "transition_probability": round(prob, 2),
            "vol_change_rate": round(vol_change_rate, 3),
            "kurtosis": round(float(kurtosis), 2),
            "signal": signal,
        }

    def _htf_regime(self, df_1h: pd.DataFrame) -> dict:
        """Higher timeframe regime for context"""
        close = df_1h["close"].values
        high = df_1h["high"].values
        low = df_1h["low"].values

        adx = self._calculate_adx(high, low, close, 14)

        returns = np.diff(np.log(close))
        vol = np.std(returns[-20:]) if len(returns) >= 20 else 0

        if adx > 30:
            regime = "trending"
        elif adx < 20:
            regime = "ranging"
        else:
            regime = "transitioning"

        return {
            "regime": regime,
            "adx": round(adx, 1),
            "vol_state": "high" if vol > np.std(returns) * 1.5 else "normal" if vol > np.std(returns) * 0.5 else "low",
        }

    def _calculate_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """Calculate ADX"""
        n = len(close)
        if n < period + 2:
            return 25.0

        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        tr = np.zeros(n)

        for i in range(1, n):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))

        # Smoothed
        atr = pd.Series(tr).rolling(period).mean().values
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean().values / np.maximum(atr, 0.0001)
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean().values / np.maximum(atr, 0.0001)

        dx = 100 * np.abs(plus_di - minus_di) / np.maximum(plus_di + minus_di, 0.0001)
        adx = pd.Series(dx).rolling(period).mean().iloc[-1]

        return float(adx) if not np.isnan(adx) else 25.0

    def _classify_composite_regime(self, result: dict) -> dict:
        """Composite regime classification"""
        vol = result.get("volatility_regime", {})
        trend = result.get("trend_regime", {})
        hmm = result.get("hmm_regime", {})
        mom = result.get("momentum_regime", {})

        vol_state = vol.get("state", "normal")
        trend_regime = trend.get("regime", "transitioning")
        is_trending = trend.get("trending", False)

        # Primary regime
        if is_trending and vol_state in ["low", "normal"]:
            primary = "smooth_trend"
            quality = "excellent"
        elif is_trending and vol_state == "high":
            primary = "volatile_trend"
            quality = "good"
        elif not is_trending and vol_state in ["low", "normal"]:
            primary = "quiet_range"
            quality = "poor"
        elif not is_trending and vol_state in ["high", "extreme"]:
            primary = "choppy"
            quality = "very_poor"
        else:
            primary = "transitioning"
            quality = "fair"

        return {
            "primary": primary,
            "quality": quality,
            "vol_state": vol_state,
            "trend_state": trend_regime,
            "hmm_state": hmm.get("regime", "unknown"),
        }

    def _is_tradeable(self, result: dict) -> dict:
        """Determine if current regime is tradeable"""
        regime = result.get("current_regime", {})
        liquidity = result.get("liquidity_regime", {})
        entropy = result.get("entropy", {})

        quality = regime.get("quality", "fair")
        liq_tradeable = liquidity.get("tradeable", True)
        predictability = entropy.get("predictability", "moderate")

        tradeable = quality in ["excellent", "good", "fair"] and liq_tradeable
        confidence_multiplier = 1.0

        if quality == "excellent":
            confidence_multiplier = 1.2
        elif quality == "good":
            confidence_multiplier = 1.0
        elif quality == "fair":
            confidence_multiplier = 0.8
        else:
            confidence_multiplier = 0.5

        if predictability == "high":
            confidence_multiplier *= 1.1
        elif predictability == "low":
            confidence_multiplier *= 0.8

        return {
            "tradeable": tradeable,
            "confidence_multiplier": round(confidence_multiplier, 2),
            "reason": f"Regime: {quality}, Liquidity: {'OK' if liq_tradeable else 'Poor'}",
        }

    def _optimal_strategy(self, result: dict) -> dict:
        """Recommend optimal strategy for current regime"""
        regime = result.get("current_regime", {}).get("primary", "unknown")
        efficiency = result.get("efficiency", {}).get("strategy_hint", "no_edge")
        fractal = result.get("fractal_regime", {}).get("persistence", "none")

        if regime == "smooth_trend":
            strategy = "trend_following"
            sl_type = "trailing"
        elif regime == "volatile_trend":
            strategy = "momentum_breakout"
            sl_type = "wide_fixed"
        elif regime == "quiet_range":
            strategy = "mean_reversion"
            sl_type = "tight_fixed"
        elif regime == "choppy":
            strategy = "avoid"
            sl_type = "none"
        else:
            strategy = efficiency
            sl_type = "atr_based"

        return {
            "strategy": strategy,
            "stop_loss_type": sl_type,
            "position_sizing": "full" if regime in ["smooth_trend"] else "reduced",
        }

    def _empty_result(self) -> dict:
        return {
            "volatility_regime": {"state": "unknown", "phase": "unknown"},
            "trend_regime": {"regime": "unknown", "trending": False},
            "hmm_regime": {"regime": "unknown", "state_id": -1},
            "momentum_regime": {"regime": "unknown"},
            "liquidity_regime": {"state": "unknown", "tradeable": True},
            "efficiency": {"efficiency": "unknown", "strategy_hint": "no_edge"},
            "fractal_regime": {"hurst": 0.5, "regime": "random_walk"},
            "entropy": {"disorder": "moderate", "predictability": "moderate"},
            "vol_term_structure": {"structure": "flat"},
            "transition_prob": {"transition_probability": 0.2, "signal": "stable"},
            "htf_regime": {"regime": "unknown"},
            "current_regime": {"primary": "unknown", "quality": "fair"},
            "tradeable": {"tradeable": True, "confidence_multiplier": 1.0},
            "optimal_strategy": {"strategy": "unknown", "stop_loss_type": "atr_based"},
        }
