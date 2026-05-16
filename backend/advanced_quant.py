"""
AURA TRADES - Advanced Quantitative Engine
Statistical & Mathematical models for institutional-grade analysis:
- Hurst Exponent (trending vs mean-reverting regime)
- Z-Score mean reversion
- Kalman Filter price prediction
- Monte Carlo probability estimation
- Realized volatility regime
- Entropy-based market randomness
- Autocorrelation decay analysis
- Statistical distribution analysis (skew, kurtosis)
- Regime detection (Hidden Markov proxy)
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import argrelextrema
from typing import Dict, Tuple, Optional


class AdvancedQuantEngine:
    """Institutional-grade quantitative analysis"""

    def analyze(self, df: pd.DataFrame) -> dict:
        """Run full quantitative analysis suite"""
        if df.empty or len(df) < 200:
            return {}

        closes = df["close"].values.astype(float)
        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        volumes = df["volume"].values.astype(float)

        return {
            "hurst_exponent": self._hurst_exponent(closes),
            "z_score": self._z_score_analysis(closes),
            "kalman": self._kalman_filter(closes),
            "monte_carlo": self._monte_carlo_probability(closes),
            "volatility_regime": self._volatility_regime(closes),
            "entropy": self._market_entropy(closes),
            "autocorrelation": self._autocorrelation_analysis(closes),
            "distribution": self._distribution_analysis(closes),
            "regime": self._regime_detection(closes),
            "mean_reversion": self._mean_reversion_signal(closes),
            "momentum_quality": self._momentum_quality(closes),
            "price_efficiency": self._price_efficiency_ratio(closes),
            "microstructure": self._microstructure_analysis(df),
            "fractal_dimension": self._fractal_dimension(closes),
            "spectral": self._spectral_analysis(closes),
            "vwap_deviation": self._vwap_deviation_bands(df),
            "information_ratio": self._information_ratio(closes),
            "regime_persistence": self._regime_persistence(closes),
        }

    def _hurst_exponent(self, prices: np.ndarray) -> dict:
        """
        Hurst Exponent: H > 0.5 = trending, H < 0.5 = mean-reverting, H = 0.5 = random
        Uses R/S (Rescaled Range) analysis
        """
        n = len(prices)
        if n < 100:
            return {"value": 0.5, "regime": "random", "confidence": 0}

        returns = np.diff(np.log(prices))
        max_k = min(int(n / 4), 200)
        lags = range(10, max_k)
        rs_values = []
        lag_values = []

        for lag in lags:
            subseries = [returns[i:i + lag] for i in range(0, len(returns) - lag, lag)]
            rs_list = []
            for s in subseries:
                if len(s) < 2:
                    continue
                mean_s = np.mean(s)
                deviations = np.cumsum(s - mean_s)
                r = np.max(deviations) - np.min(deviations)
                std_s = np.std(s, ddof=1)
                if std_s > 0:
                    rs_list.append(r / std_s)

            if rs_list:
                rs_values.append(np.mean(rs_list))
                lag_values.append(lag)

        if len(rs_values) < 5:
            return {"value": 0.5, "regime": "random", "confidence": 0}

        log_lags = np.log(lag_values)
        log_rs = np.log(rs_values)
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_lags, log_rs)

        hurst = float(slope)
        confidence = float(r_value ** 2) * 100

        if hurst > 0.6:
            regime = "trending"
        elif hurst < 0.4:
            regime = "mean_reverting"
        else:
            regime = "random"

        return {
            "value": round(hurst, 4),
            "regime": regime,
            "confidence": round(confidence, 1),
            "implication": self._hurst_implication(hurst)
        }

    def _hurst_implication(self, h: float) -> str:
        if h > 0.7:
            return "Strong trend persistence - momentum strategies favored"
        elif h > 0.6:
            return "Moderate trending - trend following viable"
        elif h < 0.3:
            return "Strong mean reversion - fade extremes"
        elif h < 0.4:
            return "Mean reverting - range trading favored"
        return "Random walk - reduce position size"

    def _z_score_analysis(self, prices: np.ndarray) -> dict:
        """
        Z-Score from multiple lookbacks for mean reversion signals
        """
        results = {}
        for period in [20, 50, 100]:
            if len(prices) < period:
                continue
            window = prices[-period:]
            mean = np.mean(window)
            std = np.std(window)
            if std > 0:
                z = (prices[-1] - mean) / std
                results[f"z_{period}"] = round(float(z), 3)

        # Composite Z-score
        z_values = list(results.values())
        if z_values:
            composite = np.mean(z_values)
            results["composite"] = round(float(composite), 3)

            if composite > 2.0:
                results["signal"] = "extremely_overbought"
                results["strength"] = min(100, int(abs(composite) * 30))
            elif composite > 1.5:
                results["signal"] = "overbought"
                results["strength"] = min(80, int(abs(composite) * 25))
            elif composite < -2.0:
                results["signal"] = "extremely_oversold"
                results["strength"] = min(100, int(abs(composite) * 30))
            elif composite < -1.5:
                results["signal"] = "oversold"
                results["strength"] = min(80, int(abs(composite) * 25))
            else:
                results["signal"] = "neutral"
                results["strength"] = 0

        return results

    def _kalman_filter(self, prices: np.ndarray) -> dict:
        """
        Kalman Filter for adaptive price estimation and trend detection
        Predicts next likely price move direction
        """
        n = len(prices)
        if n < 50:
            return {"prediction": "neutral", "confidence": 0}

        # State: [price, velocity]
        x = np.array([prices[0], 0.0])  # Initial state
        P = np.array([[1.0, 0.0], [0.0, 1.0]])  # Initial covariance
        F = np.array([[1.0, 1.0], [0.0, 1.0]])  # State transition
        H = np.array([[1.0, 0.0]])  # Observation matrix
        R = np.array([[np.var(np.diff(prices[-50:]))]])  # Measurement noise
        Q = np.array([[0.01, 0.0], [0.0, 0.001]])  # Process noise

        filtered_prices = []
        velocities = []

        for i in range(n):
            # Predict
            x_pred = F @ x
            P_pred = F @ P @ F.T + Q

            # Update
            z = np.array([prices[i]])
            y = z - H @ x_pred
            S = H @ P_pred @ H.T + R
            K = P_pred @ H.T @ np.linalg.inv(S)
            x = x_pred + K @ y
            P = (np.eye(2) - K @ H) @ P_pred

            filtered_prices.append(float(x[0]))
            velocities.append(float(x[1]))

        current_velocity = velocities[-1]
        avg_velocity = np.mean(velocities[-20:])
        velocity_acceleration = current_velocity - np.mean(velocities[-5:])

        # Predicted next price
        predicted_price = filtered_prices[-1] + current_velocity
        prediction_diff = (predicted_price - prices[-1]) / prices[-1]

        if prediction_diff > 0.0002:
            prediction = "bullish"
        elif prediction_diff < -0.0002:
            prediction = "bearish"
        else:
            prediction = "neutral"

        confidence = min(100, int(abs(prediction_diff) * 50000))

        return {
            "prediction": prediction,
            "predicted_price": round(float(predicted_price), 5),
            "velocity": round(current_velocity, 6),
            "acceleration": round(velocity_acceleration, 6),
            "confidence": confidence,
            "filtered_vs_raw": round(float(filtered_prices[-1] - prices[-1]), 6)
        }

    def _monte_carlo_probability(self, prices: np.ndarray, simulations: int = 5000) -> dict:
        """
        Monte Carlo simulation to estimate probability of hitting TP vs SL
        Using geometric Brownian motion with real volatility
        """
        if len(prices) < 50:
            return {"tp_probability": 50, "sl_probability": 50}

        returns = np.diff(np.log(prices[-100:]))
        mu = np.mean(returns)
        sigma = np.std(returns)
        current_price = prices[-1]

        # Simulate next 4 candles (1 hour on 15m)
        steps = 8  # 2 hours forward
        tp_hits = 0
        sl_hits = 0

        # Use 1.5 ATR for SL, 3 ATR for TP (1:2)
        atr_proxy = sigma * current_price * np.sqrt(14)
        sl_distance = atr_proxy * 1.5
        tp_distance = atr_proxy * 3.0

        for _ in range(simulations):
            path = current_price
            hit_tp = False
            hit_sl = False

            for _ in range(steps):
                path *= np.exp(mu + sigma * np.random.randn())
                if path >= current_price + tp_distance:
                    hit_tp = True
                    break
                elif path <= current_price - sl_distance:
                    hit_sl = True
                    break

            if hit_tp:
                tp_hits += 1
            elif hit_sl:
                sl_hits += 1

        tp_prob = (tp_hits / simulations) * 100
        sl_prob = (sl_hits / simulations) * 100
        neutral_prob = 100 - tp_prob - sl_prob

        return {
            "tp_probability": round(tp_prob, 1),
            "sl_probability": round(sl_prob, 1),
            "neutral_probability": round(neutral_prob, 1),
            "expected_move": round(float(mu * steps * current_price), 5),
            "risk_adjusted_edge": round(tp_prob - sl_prob, 1)
        }

    def _volatility_regime(self, prices: np.ndarray) -> dict:
        """
        Detect volatility regime using realized vol vs historical
        Parkinson estimator for intraday vol
        """
        if len(prices) < 100:
            return {"regime": "normal", "percentile": 50}

        returns = np.diff(np.log(prices))

        # Current realized vol (20-period)
        current_vol = np.std(returns[-20:]) * np.sqrt(252 * 26)  # Annualized (26 bars/day for 15m)
        # Historical vol (100-period)
        hist_vol = np.std(returns[-100:]) * np.sqrt(252 * 26)
        # Long-term vol
        long_vol = np.std(returns) * np.sqrt(252 * 26)

        # Volatility ratio
        vol_ratio = current_vol / hist_vol if hist_vol > 0 else 1.0

        # Vol percentile
        rolling_vols = []
        for i in range(20, len(returns), 5):
            rv = np.std(returns[max(0, i - 20):i])
            rolling_vols.append(rv)

        if rolling_vols:
            percentile = float(stats.percentileofscore(rolling_vols, np.std(returns[-20:])))
        else:
            percentile = 50.0

        if vol_ratio > 1.8:
            regime = "extreme_high"
        elif vol_ratio > 1.3:
            regime = "elevated"
        elif vol_ratio < 0.5:
            regime = "compressed"
        elif vol_ratio < 0.7:
            regime = "low"
        else:
            regime = "normal"

        return {
            "regime": regime,
            "current_vol": round(float(current_vol), 4),
            "historical_vol": round(float(hist_vol), 4),
            "vol_ratio": round(float(vol_ratio), 3),
            "percentile": round(percentile, 1),
            "expanding": bool(current_vol > hist_vol),
            "implication": self._vol_implication(regime)
        }

    def _vol_implication(self, regime: str) -> str:
        implications = {
            "extreme_high": "Extreme volatility - reduce size, widen stops",
            "elevated": "Above average vol - normal stops, expect fast moves",
            "normal": "Normal conditions - standard parameters",
            "low": "Low vol - tighten stops, expect breakout soon",
            "compressed": "Vol squeeze imminent - prepare for expansion"
        }
        return implications.get(regime, "")

    def _market_entropy(self, prices: np.ndarray) -> dict:
        """
        Shannon Entropy of price distribution - measures market randomness
        Low entropy = predictable/trending, High entropy = random/choppy
        """
        if len(prices) < 50:
            return {"entropy": 0, "predictability": "unknown"}

        returns = np.diff(prices) / prices[:-1]
        recent = returns[-50:]

        # Discretize returns into bins
        n_bins = 20
        hist, _ = np.histogram(recent, bins=n_bins, density=True)
        hist = hist[hist > 0]  # Remove zero bins
        hist = hist / hist.sum()  # Normalize

        entropy = -np.sum(hist * np.log2(hist))
        max_entropy = np.log2(n_bins)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        if normalized_entropy < 0.5:
            predictability = "high"
        elif normalized_entropy < 0.7:
            predictability = "moderate"
        elif normalized_entropy < 0.85:
            predictability = "low"
        else:
            predictability = "very_low"

        return {
            "entropy": round(float(normalized_entropy), 4),
            "predictability": predictability,
            "score": round((1 - normalized_entropy) * 100, 1)
        }

    def _autocorrelation_analysis(self, prices: np.ndarray) -> dict:
        """
        Autocorrelation analysis - detects if recent moves predict next moves
        """
        if len(prices) < 100:
            return {"trending_score": 0}

        returns = np.diff(np.log(prices[-100:]))

        # Calculate autocorrelation at different lags
        autocorrs = {}
        for lag in [1, 2, 3, 5, 10]:
            if len(returns) > lag:
                corr = np.corrcoef(returns[:-lag], returns[lag:])[0, 1]
                autocorrs[f"lag_{lag}"] = round(float(corr), 4) if not np.isnan(corr) else 0

        # Positive autocorrelation = trending, negative = mean-reverting
        lag1 = autocorrs.get("lag_1", 0)
        if lag1 > 0.1:
            signal = "momentum_continuation"
        elif lag1 < -0.1:
            signal = "mean_reversion"
        else:
            signal = "no_edge"

        return {
            "autocorrelations": autocorrs,
            "signal": signal,
            "trending_score": round(float(lag1) * 100, 1)
        }

    def _distribution_analysis(self, prices: np.ndarray) -> dict:
        """
        Statistical distribution: skewness, kurtosis, normality test
        """
        if len(prices) < 50:
            return {}

        returns = np.diff(np.log(prices[-200:]))

        skewness = float(stats.skew(returns))
        kurtosis = float(stats.kurtosis(returns))

        # Jarque-Bera normality test
        jb_stat, jb_pvalue = stats.jarque_bera(returns)

        # Fat tails detection
        fat_tails = kurtosis > 3

        # Skew implication
        if skewness > 0.5:
            skew_signal = "positive_skew_bullish_tail_risk"
        elif skewness < -0.5:
            skew_signal = "negative_skew_bearish_tail_risk"
        else:
            skew_signal = "symmetric"

        return {
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "fat_tails": fat_tails,
            "normal_distribution": bool(jb_pvalue > 0.05),
            "skew_signal": skew_signal
        }

    def _regime_detection(self, prices: np.ndarray) -> dict:
        """
        Simple regime detection using price position relative to moving averages
        and volatility clustering (HMM proxy)
        """
        if len(prices) < 200:
            return {"regime": "unknown", "confidence": 0}

        # Fast/Slow MA regime
        ma_20 = np.mean(prices[-20:])
        ma_50 = np.mean(prices[-50:])
        ma_100 = np.mean(prices[-100:])
        ma_200 = np.mean(prices[-200:])
        current = prices[-1]

        # Score alignment
        alignment_score = 0
        if current > ma_20:
            alignment_score += 1
        if current > ma_50:
            alignment_score += 1
        if current > ma_100:
            alignment_score += 1
        if current > ma_200:
            alignment_score += 1
        if ma_20 > ma_50:
            alignment_score += 1
        if ma_50 > ma_100:
            alignment_score += 1
        if ma_100 > ma_200:
            alignment_score += 1

        # Volatility regime
        returns = np.diff(np.log(prices))
        recent_vol = np.std(returns[-20:])
        hist_vol = np.std(returns[-100:])
        vol_expanding = recent_vol > hist_vol

        if alignment_score >= 6:
            regime = "strong_uptrend"
        elif alignment_score >= 5:
            regime = "uptrend"
        elif alignment_score <= 1:
            regime = "strong_downtrend"
        elif alignment_score <= 2:
            regime = "downtrend"
        else:
            regime = "transition" if vol_expanding else "consolidation"

        return {
            "regime": regime,
            "alignment_score": alignment_score,
            "max_score": 7,
            "vol_expanding": vol_expanding,
            "confidence": round(abs(alignment_score - 3.5) / 3.5 * 100, 1)
        }

    def _mean_reversion_signal(self, prices: np.ndarray) -> dict:
        """
        Ornstein-Uhlenbeck mean reversion model
        """
        if len(prices) < 100:
            return {"signal": "neutral", "half_life": 0}

        log_prices = np.log(prices[-100:])
        # Estimate OU parameters
        y = np.diff(log_prices)
        x = log_prices[:-1]

        # Linear regression: y = a + b*x
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        if slope >= 0:
            return {"signal": "no_mean_reversion", "half_life": float('inf'), "strength": 0}

        # Half-life of mean reversion
        half_life = -np.log(2) / slope

        # Mean level
        mean_level = -intercept / slope
        current_deviation = log_prices[-1] - mean_level

        if half_life < 5:  # Less than 5 bars
            speed = "fast"
        elif half_life < 20:
            speed = "moderate"
        else:
            speed = "slow"

        if current_deviation > 0.01:
            signal = "short_to_mean"
        elif current_deviation < -0.01:
            signal = "long_to_mean"
        else:
            signal = "at_mean"

        return {
            "signal": signal,
            "half_life": round(float(half_life), 1),
            "speed": speed,
            "deviation": round(float(current_deviation), 5),
            "mean_price": round(float(np.exp(mean_level)), 5),
            "strength": round(min(100, abs(current_deviation) * 5000), 1)
        }

    def _momentum_quality(self, prices: np.ndarray) -> dict:
        """
        Measure quality of momentum - smooth vs choppy moves
        """
        if len(prices) < 50:
            return {"quality": 0, "type": "unknown"}

        returns = np.diff(prices[-50:]) / prices[-50:-1]

        # Consistency: % of returns in same direction as overall move
        overall_direction = 1 if prices[-1] > prices[-50] else -1
        consistent_bars = np.sum(np.sign(returns) == overall_direction)
        consistency = consistent_bars / len(returns) * 100

        # Smoothness: inverse of path volatility vs end-to-end move
        total_move = abs(prices[-1] - prices[-50])
        path_length = np.sum(np.abs(np.diff(prices[-50:])))
        efficiency = (total_move / path_length * 100) if path_length > 0 else 0

        quality = (consistency + efficiency) / 2

        if quality > 70:
            momentum_type = "institutional_flow"
        elif quality > 50:
            momentum_type = "healthy_trend"
        elif quality > 30:
            momentum_type = "choppy_momentum"
        else:
            momentum_type = "noise"

        return {
            "quality": round(float(quality), 1),
            "consistency": round(float(consistency), 1),
            "efficiency": round(float(efficiency), 1),
            "type": momentum_type
        }

    def _price_efficiency_ratio(self, prices: np.ndarray) -> dict:
        """
        Kaufman's Efficiency Ratio - measures trend strength
        ER = Direction / Volatility
        """
        if len(prices) < 30:
            return {"ratio": 0, "signal": "neutral"}

        period = 20
        direction = abs(prices[-1] - prices[-period - 1])
        volatility = np.sum(np.abs(np.diff(prices[-period - 1:])))

        er = direction / volatility if volatility > 0 else 0

        if er > 0.6:
            signal = "strong_trend"
        elif er > 0.3:
            signal = "moderate_trend"
        else:
            signal = "ranging"

        return {
            "ratio": round(float(er), 4),
            "signal": signal,
            "score": round(float(er) * 100, 1)
        }

    def _microstructure_analysis(self, df: pd.DataFrame) -> dict:
        """
        Market microstructure from candle data:
        - Wick-to-body ratios (rejection analysis)
        - Consecutive candle patterns
        - Momentum exhaustion detection
        """
        if len(df) < 20:
            return {}

        recent = df.tail(20)
        bodies = abs(recent["close"] - recent["open"])
        upper_wicks = recent["high"] - recent[["close", "open"]].max(axis=1)
        lower_wicks = recent[["close", "open"]].min(axis=1) - recent["low"]
        ranges = recent["high"] - recent["low"]

        # Average wick ratios
        avg_upper_wick_ratio = float((upper_wicks / ranges).replace([np.inf, -np.inf], 0).mean())
        avg_lower_wick_ratio = float((lower_wicks / ranges).replace([np.inf, -np.inf], 0).mean())
        avg_body_ratio = float((bodies / ranges).replace([np.inf, -np.inf], 0).mean())

        # Rejection signals
        last_5 = df.tail(5)
        recent_upper_rejection = float((last_5["high"] - last_5[["close", "open"]].max(axis=1)).mean())
        recent_lower_rejection = float((last_5[["close", "open"]].min(axis=1) - last_5["low"]).mean())

        if recent_upper_rejection > recent_lower_rejection * 1.5:
            rejection_signal = "sellers_rejecting_highs"
        elif recent_lower_rejection > recent_upper_rejection * 1.5:
            rejection_signal = "buyers_rejecting_lows"
        else:
            rejection_signal = "balanced"

        # Exhaustion detection (decreasing bodies with increasing wicks)
        last_bodies = bodies.tail(5).values
        last_ranges = ranges.tail(5).values
        body_decreasing = all(last_bodies[i] >= last_bodies[i + 1] for i in range(len(last_bodies) - 1))
        exhaustion = body_decreasing and avg_body_ratio < 0.4

        return {
            "avg_body_ratio": round(avg_body_ratio, 3),
            "avg_upper_wick": round(avg_upper_wick_ratio, 3),
            "avg_lower_wick": round(avg_lower_wick_ratio, 3),
            "rejection_signal": rejection_signal,
            "exhaustion_detected": exhaustion,
            "market_conviction": "strong" if avg_body_ratio > 0.6 else "weak" if avg_body_ratio < 0.3 else "moderate"
        }

    # ─── FRACTAL DIMENSION (market roughness) ───
    def _fractal_dimension(self, prices, window=50):
        """
        Fractal Dimension via Higuchi method.
        FD ~1.0 = trending, FD ~1.5 = random/choppy, FD ~2.0 = very noisy
        """
        if len(prices) < window + 10:
            return {"value": 1.5, "signal": "neutral"}

        recent = prices[-window:]
        k_max = min(10, window // 4)
        lk = []
        ln_k = []

        for k in range(1, k_max + 1):
            lengths = []
            for m in range(1, k + 1):
                idx = np.arange(m - 1, len(recent), k)
                if len(idx) < 2:
                    continue
                seg = recent[idx]
                length = np.sum(np.abs(np.diff(seg))) * (len(recent) - 1) / (k * len(idx))
                lengths.append(length)
            if lengths:
                avg_l = np.mean(lengths)
                if avg_l > 0:
                    lk.append(np.log(avg_l))
                    ln_k.append(np.log(1.0 / k))

        if len(lk) < 3:
            return {"value": 1.5, "signal": "neutral"}

        fd = float(np.polyfit(ln_k, lk, 1)[0])
        fd = max(1.0, min(2.0, fd))

        if fd < 1.25:
            signal = "strong_trend"
        elif fd < 1.4:
            signal = "trending"
        elif fd > 1.65:
            signal = "very_choppy"
        elif fd > 1.55:
            signal = "choppy"
        else:
            signal = "neutral"

        return {"value": round(fd, 3), "signal": signal}

    # ─── SPECTRAL ANALYSIS (dominant cycle) ───
    def _spectral_analysis(self, prices, max_period=100):
        """
        FFT-based spectral analysis to find dominant market cycle.
        Helps identify periodicity in price action.
        """
        if len(prices) < max_period * 2:
            return {"dominant_period": 0, "signal": "neutral"}

        try:
            detrended = prices - np.convolve(prices, np.ones(20) / 20, mode='same')
            n = len(detrended)
            fft_vals = np.fft.rfft(detrended[-max_period * 2:])
            power = np.abs(fft_vals) ** 2
            freqs = np.fft.rfftfreq(len(detrended[-max_period * 2:]))

            # Ignore DC component and very low frequencies
            power[0] = 0
            if len(power) > 3:
                power[1:3] = 0

            if len(power) < 5:
                return {"dominant_period": 0, "signal": "neutral"}

            peak_idx = np.argmax(power)
            if freqs[peak_idx] > 0:
                dominant_period = int(1.0 / freqs[peak_idx])
            else:
                dominant_period = 0

            # Spectral concentration (is there a clear cycle?)
            total_power = np.sum(power)
            if total_power > 0:
                concentration = float(power[peak_idx] / total_power)
            else:
                concentration = 0

            # Position in cycle (approximate)
            if dominant_period > 0:
                cycle_pos = len(prices) % dominant_period
                pct_through = cycle_pos / dominant_period
            else:
                pct_through = 0.5

            signal = "neutral"
            if concentration > 0.3 and dominant_period > 5:
                if pct_through < 0.25:
                    signal = "cycle_bottom"
                elif pct_through > 0.75:
                    signal = "cycle_top"
                elif pct_through < 0.5:
                    signal = "cycle_rising"
                else:
                    signal = "cycle_falling"

            return {
                "dominant_period": dominant_period,
                "concentration": round(concentration, 3),
                "cycle_position": round(pct_through, 2),
                "signal": signal,
                "has_clear_cycle": concentration > 0.2
            }
        except Exception:
            return {"dominant_period": 0, "signal": "neutral"}

    # ─── VWAP DEVIATION BANDS ───
    def _vwap_deviation_bands(self, df):
        """Calculate price deviation from session VWAP in standard deviation units"""
        if len(df) < 20:
            return {"deviation": 0, "signal": "neutral"}

        try:
            closes = df["close"].values.astype(float)
            highs = df["high"].values.astype(float)
            lows = df["low"].values.astype(float)
            volumes = df["volume"].values.astype(float)
            if np.sum(volumes) == 0:
                volumes = np.ones(len(df))

            typical = (highs + lows + closes) / 3
            cum_vol = np.cumsum(volumes[-96:])  # Last day
            cum_tp_vol = np.cumsum((typical * volumes)[-96:])

            if cum_vol[-1] == 0:
                return {"deviation": 0, "signal": "neutral"}

            vwap = cum_tp_vol / cum_vol
            current_vwap = float(vwap[-1])
            current_price = float(closes[-1])

            # Standard deviation of price from VWAP
            diffs = (typical[-96:] - vwap) ** 2
            cum_diffs = np.cumsum(diffs * volumes[-96:])
            std = np.sqrt(cum_diffs[-1] / cum_vol[-1]) if cum_vol[-1] > 0 else 1

            deviation = (current_price - current_vwap) / std if std > 0 else 0

            if deviation > 2.0:
                signal = "extremely_above_vwap"
            elif deviation > 1.0:
                signal = "above_vwap"
            elif deviation < -2.0:
                signal = "extremely_below_vwap"
            elif deviation < -1.0:
                signal = "below_vwap"
            else:
                signal = "near_vwap"

            return {
                "deviation": round(float(deviation), 2),
                "vwap": round(current_vwap, 5),
                "std": round(float(std), 5),
                "signal": signal
            }
        except Exception:
            return {"deviation": 0, "signal": "neutral"}

    # ─── INFORMATION RATIO (risk-adjusted trend) ───
    def _information_ratio(self, prices, window=50):
        """
        Information Ratio = excess return / tracking error.
        High IR = strong risk-adjusted trend. Low IR = noise.
        """
        if len(prices) < window + 10:
            return {"value": 0, "signal": "neutral"}

        returns = np.diff(np.log(prices[-window:]))
        if len(returns) < 10:
            return {"value": 0, "signal": "neutral"}

        mean_ret = np.mean(returns)
        std_ret = np.std(returns)

        if std_ret == 0:
            return {"value": 0, "signal": "neutral"}

        ir = float(mean_ret / std_ret) * np.sqrt(252 * 4)  # Annualized for 15m

        if ir > 2.0:
            signal = "strong_bullish_trend"
        elif ir > 1.0:
            signal = "bullish_trend"
        elif ir < -2.0:
            signal = "strong_bearish_trend"
        elif ir < -1.0:
            signal = "bearish_trend"
        else:
            signal = "no_clear_trend"

        return {"value": round(ir, 2), "signal": signal}

    # ─── REGIME PERSISTENCE ───
    def _regime_persistence(self, prices, window=100):
        """
        Measures how persistent the current regime is.
        Long-running regimes more likely to continue (momentum) or mean-revert (exhaustion).
        """
        if len(prices) < window:
            return {"streak": 0, "signal": "neutral"}

        returns = np.diff(prices[-window:])
        # Count current streak of same-direction moves
        streak = 0
        last_dir = 1 if returns[-1] > 0 else -1
        for r in reversed(returns):
            if (r > 0 and last_dir > 0) or (r < 0 and last_dir < 0):
                streak += 1
            else:
                break

        direction = "bullish" if last_dir > 0 else "bearish"

        # Calculate regime change frequency
        sign_changes = np.sum(np.abs(np.diff(np.sign(returns))) > 0)
        churn = float(sign_changes / len(returns))

        if streak > 10:
            signal = f"extended_{direction}"
        elif streak > 5:
            signal = f"persistent_{direction}"
        elif churn > 0.6:
            signal = "high_churn"
        else:
            signal = "normal"

        return {
            "streak": streak,
            "direction": direction,
            "churn": round(churn, 3),
            "signal": signal
        }
