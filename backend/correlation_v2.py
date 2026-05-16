"""
AURA TRADES - V2 Correlation & Inter-Market Analysis
Advanced institutional-grade correlation:
- Rolling correlation with regime detection
- Lead-lag relationship detection
- Cointegration analysis (Engle-Granger)
- Currency Strength Index
- Sector rotation signals
- Risk sentiment composite
- Smart Money Flow Index proxy
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple
from config import FOREX_PAIRS, INDICES, COMMODITIES, ASSET_CLASSES


class CorrelationAnalyzerV2:
    """Enhanced inter-market correlation analysis"""

    KNOWN_CORRELATIONS = {
        ("EURUSD=X", "GBPUSD=X"): "positive",
        ("EURUSD=X", "AUDUSD=X"): "positive",
        ("GBPUSD=X", "AUDUSD=X"): "positive",
        ("AUDUSD=X", "NZDUSD=X"): "positive",
        ("GC=F", "SI=F"): "positive",
        ("^GSPC", "^DJI"): "positive",
        ("^GSPC", "^IXIC"): "positive",
        ("CL=F", "USDCAD=X"): "negative",
        ("EURUSD=X", "USDJPY=X"): "negative",
        ("EURUSD=X", "USDCHF=X"): "negative",
        ("GC=F", "USDJPY=X"): "negative",
        ("^GSPC", "GC=F"): "negative",
    }

    DXY_COMPONENTS = {
        "EURUSD=X": -0.576,
        "USDJPY=X": 0.136,
        "GBPUSD=X": -0.119,
        "USDCAD=X": 0.091,
        "USDCHF=X": 0.036,
    }

    # Currency pairs for strength calculation
    CURRENCY_PAIRS = {
        "USD": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X"],
        "EUR": ["EURUSD=X", "EURGBP=X", "EURJPY=X", "EURAUD=X", "EURNZD=X"],
        "GBP": ["GBPUSD=X", "EURGBP=X", "GBPJPY=X", "GBPAUD=X", "GBPNZD=X"],
        "JPY": ["USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "NZDJPY=X", "CADJPY=X", "CHFJPY=X"],
        "AUD": ["AUDUSD=X", "EURAUD=X", "GBPAUD=X", "AUDJPY=X", "AUDNZD=X", "AUDCAD=X"],
        "NZD": ["NZDUSD=X", "EURNZD=X", "GBPNZD=X", "NZDJPY=X", "AUDNZD=X"],
        "CAD": ["USDCAD=X", "AUDCAD=X", "CADJPY=X"],
        "CHF": ["USDCHF=X", "CHFJPY=X"],
    }

    def __init__(self):
        self.correlation_matrix = None

    def analyze(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Full enhanced correlation analysis"""
        if len(all_data) < 2:
            return {"matrix": {}, "signals": [], "dxy_bias": "neutral"}

        returns_df = self._build_returns_df(all_data)

        # Standard correlation
        corr_matrix = returns_df.corr() if not returns_df.empty else pd.DataFrame()
        self.correlation_matrix = corr_matrix

        # Rolling correlation regime
        rolling_corr = self._rolling_correlation_regime(all_data)

        # Lead-lag detection
        lead_lag = self._lead_lag_detection(all_data)

        # Cointegration
        cointegration = self._cointegration_analysis(all_data)

        # Currency Strength Index
        currency_strength = self._currency_strength_index(all_data)

        # DXY bias
        dxy_bias = self._calculate_dxy_bias(all_data)

        # Risk sentiment composite
        risk_sentiment = self._risk_sentiment_composite(all_data)

        # Smart Money Flow
        smart_money = self._smart_money_flow(all_data)

        # Cross-pair signals
        signals = self._find_correlation_signals(all_data, corr_matrix)

        return {
            "matrix": corr_matrix.to_dict() if not corr_matrix.empty else {},
            "signals": signals,
            "dxy_bias": dxy_bias,
            "rolling_correlations": rolling_corr,
            "lead_lag": lead_lag,
            "cointegration": cointegration,
            "currency_strength": currency_strength,
            "risk_sentiment": risk_sentiment,
            "smart_money_flow": smart_money,
        }

    def get_correlation_score(self, symbol: str, direction: str, all_data: Dict[str, pd.DataFrame]) -> float:
        """Enhanced correlation confirmation score (0-100)"""
        if not all_data or symbol not in all_data:
            return 50.0

        score = 50.0
        confirmations = 0
        contradictions = 0

        for pair, rel_type in self.KNOWN_CORRELATIONS.items():
            if symbol in pair:
                other = pair[0] if pair[1] == symbol else pair[1]
                if other not in all_data:
                    continue

                other_direction = self._get_recent_direction(all_data[other])
                if other_direction == "neutral":
                    continue

                if rel_type == "positive":
                    if direction.lower() == other_direction:
                        confirmations += 1
                    else:
                        contradictions += 1
                elif rel_type == "negative":
                    if direction.lower() != other_direction:
                        confirmations += 1
                    else:
                        contradictions += 1

        total = confirmations + contradictions
        if total > 0:
            score = (confirmations / total) * 100

        return score

    def _build_returns_df(self, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        closes = {}
        for symbol, df in all_data.items():
            if not df.empty and "close" in df.columns and len(df) > 10:
                closes[symbol] = df["close"].pct_change().dropna()
        if not closes:
            return pd.DataFrame()
        return pd.DataFrame(closes).dropna(how="all")

    def _rolling_correlation_regime(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Detect when correlations break down or strengthen"""
        results = {}

        key_pairs = [("EURUSD=X", "GBPUSD=X"), ("GC=F", "^GSPC"), ("EURUSD=X", "USDCHF=X")]

        for sym1, sym2 in key_pairs:
            if sym1 not in all_data or sym2 not in all_data:
                continue

            df1 = all_data[sym1]["close"].pct_change().dropna()
            df2 = all_data[sym2]["close"].pct_change().dropna()

            # Align
            aligned = pd.concat([df1, df2], axis=1).dropna()
            if len(aligned) < 50:
                continue

            # Rolling 20-period correlation
            rolling_corr = aligned.iloc[:, 0].rolling(20).corr(aligned.iloc[:, 1])
            if rolling_corr.empty:
                continue

            current_corr = float(rolling_corr.iloc[-1]) if not pd.isna(rolling_corr.iloc[-1]) else 0
            avg_corr = float(rolling_corr.mean()) if not rolling_corr.isna().all() else 0

            # Regime change detection
            if abs(current_corr - avg_corr) > 0.3:
                regime = "breakdown" if abs(current_corr) < abs(avg_corr) else "strengthening"
            else:
                regime = "normal"

            pair_key = f"{sym1}_{sym2}"
            results[pair_key] = {
                "current": round(current_corr, 4),
                "average": round(avg_corr, 4),
                "regime": regime
            }

        return results

    def _lead_lag_detection(self, all_data: Dict[str, pd.DataFrame]) -> List[dict]:
        """Detect which instruments lead others"""
        leads = []
        key_pairs = [
            ("^GSPC", "^FTSE"), ("^GSPC", "^GDAXI"),
            ("GC=F", "SI=F"), ("CL=F", "USDCAD=X"),
            ("^GSPC", "AUDJPY=X"),
        ]

        for sym1, sym2 in key_pairs:
            if sym1 not in all_data or sym2 not in all_data:
                continue

            df1 = all_data[sym1]["close"].pct_change().dropna()
            df2 = all_data[sym2]["close"].pct_change().dropna()

            aligned = pd.concat([df1, df2], axis=1).dropna()
            if len(aligned) < 30:
                continue

            s1 = aligned.iloc[:, 0].values
            s2 = aligned.iloc[:, 1].values

            # Cross-correlation at different lags
            best_lag = 0
            best_corr = 0
            for lag in range(-5, 6):
                if lag == 0:
                    corr = np.corrcoef(s1, s2)[0, 1]
                elif lag > 0:
                    corr = np.corrcoef(s1[:-lag], s2[lag:])[0, 1]
                else:
                    corr = np.corrcoef(s1[-lag:], s2[:lag])[0, 1]

                if not np.isnan(corr) and abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag

            if abs(best_lag) >= 1 and abs(best_corr) > 0.3:
                leader = sym1 if best_lag > 0 else sym2
                follower = sym2 if best_lag > 0 else sym1
                leads.append({
                    "leader": leader,
                    "follower": follower,
                    "lag_bars": abs(best_lag),
                    "correlation": round(float(best_corr), 4),
                    "implication": f"{leader} leads {follower} by {abs(best_lag)} bars"
                })

        return leads

    def _cointegration_analysis(self, all_data: Dict[str, pd.DataFrame]) -> List[dict]:
        """Engle-Granger cointegration test for mean-reverting pairs"""
        results = []
        test_pairs = [
            ("EURUSD=X", "GBPUSD=X"), ("AUDUSD=X", "NZDUSD=X"),
            ("GC=F", "SI=F"), ("^GSPC", "^DJI"),
        ]

        for sym1, sym2 in test_pairs:
            if sym1 not in all_data or sym2 not in all_data:
                continue

            s1 = all_data[sym1]["close"].values
            s2 = all_data[sym2]["close"].values

            min_len = min(len(s1), len(s2))
            if min_len < 100:
                continue

            s1 = s1[-min_len:]
            s2 = s2[-min_len:]

            # OLS regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(s1, s2)

            # Residuals
            residuals = s2 - (slope * s1 + intercept)

            # ADF-like test: check if residuals are stationary
            # Simplified: check if residuals revert to mean
            resid_diff = np.diff(residuals)
            resid_lag = residuals[:-1]

            if len(resid_lag) > 10 and np.std(resid_lag) > 0:
                adf_slope, _, r, p, _ = stats.linregress(resid_lag, resid_diff)

                # Negative slope = mean reverting
                if adf_slope < -0.01 and p < 0.1:
                    # Current spread z-score
                    spread = residuals[-1]
                    spread_mean = np.mean(residuals)
                    spread_std = np.std(residuals)
                    z_score = (spread - spread_mean) / spread_std if spread_std > 0 else 0

                    results.append({
                        "pair": f"{sym1}/{sym2}",
                        "cointegrated": True,
                        "z_score": round(float(z_score), 3),
                        "half_life": round(float(-np.log(2) / adf_slope), 1),
                        "signal": "short_spread" if z_score > 1.5 else "long_spread" if z_score < -1.5 else "neutral"
                    })

        return results

    def _currency_strength_index(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Calculate relative strength of each currency"""
        strength = {}

        for currency, pairs in self.CURRENCY_PAIRS.items():
            scores = []
            for pair in pairs:
                if pair not in all_data or len(all_data[pair]) < 20:
                    continue

                df = all_data[pair]
                ret = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df["close"].iloc[-20]

                # Determine if currency is base or quote
                pair_clean = pair.replace("=X", "")
                if pair_clean.startswith(currency):
                    scores.append(float(ret))  # Base currency: positive return = strength
                else:
                    scores.append(-float(ret))  # Quote currency: negative return = strength

            if scores:
                avg_score = np.mean(scores) * 1000  # Scale
                strength[currency] = round(float(avg_score), 2)

        # Normalize to -100 to +100 range
        if strength:
            max_abs = max(abs(v) for v in strength.values()) or 1
            strength = {k: round(v / max_abs * 100, 1) for k, v in strength.items()}

        # Sort by strength
        sorted_strength = dict(sorted(strength.items(), key=lambda x: x[1], reverse=True))

        # Determine strongest and weakest
        currencies = list(sorted_strength.keys())
        values = list(sorted_strength.values())

        return {
            "index": sorted_strength,
            "strongest": currencies[0] if currencies else None,
            "weakest": currencies[-1] if currencies else None,
            "best_pair_long": f"{currencies[0]}/{currencies[-1]}" if len(currencies) >= 2 else None,
            "best_pair_short": f"{currencies[-1]}/{currencies[0]}" if len(currencies) >= 2 else None,
        }

    def _calculate_dxy_bias(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Calculate USD strength from proxy components"""
        usd_score = 0
        components_used = 0

        for symbol, weight in self.DXY_COMPONENTS.items():
            if symbol not in all_data:
                continue
            df = all_data[symbol]
            if df.empty or len(df) < 20:
                continue

            recent_return = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df["close"].iloc[-20]
            usd_contribution = recent_return * weight * 100
            usd_score += usd_contribution
            components_used += 1

        if components_used == 0:
            return {"bias": "neutral", "score": 0}

        if usd_score > 0.1:
            bias = "usd_bullish"
        elif usd_score < -0.1:
            bias = "usd_bearish"
        else:
            bias = "neutral"

        return {"bias": bias, "score": round(usd_score, 4)}

    def _risk_sentiment_composite(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """Composite risk sentiment from multiple asset classes"""
        risk_on_assets = ["^GSPC", "^IXIC", "AUDUSD=X", "NZDUSD=X", "^GDAXI"]
        risk_off_assets = ["GC=F", "USDJPY=X", "USDCHF=X"]
        
        risk_on_score = 0
        risk_off_score = 0
        total_checked = 0

        for symbol in risk_on_assets:
            if symbol in all_data and len(all_data[symbol]) >= 20:
                direction = self._get_recent_direction(all_data[symbol])
                total_checked += 1
                if direction == "bullish":
                    risk_on_score += 1
                elif direction == "bearish":
                    risk_off_score += 1

        for symbol in risk_off_assets:
            if symbol in all_data and len(all_data[symbol]) >= 20:
                direction = self._get_recent_direction(all_data[symbol])
                total_checked += 1
                if direction == "bullish":
                    risk_off_score += 1
                elif direction == "bearish":
                    risk_on_score += 1

        if total_checked == 0:
            return {"sentiment": "neutral", "score": 0, "confidence": 0}

        net_score = risk_on_score - risk_off_score
        confidence = (abs(net_score) / total_checked) * 100

        if net_score >= 3:
            sentiment = "strong_risk_on"
        elif net_score >= 1:
            sentiment = "risk_on"
        elif net_score <= -3:
            sentiment = "strong_risk_off"
        elif net_score <= -1:
            sentiment = "risk_off"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": net_score,
            "confidence": round(confidence, 1),
            "implication": self._risk_implication(sentiment)
        }

    def _risk_implication(self, sentiment: str) -> str:
        implications = {
            "strong_risk_on": "Strong risk appetite: Long AUD, NZD, equities. Short JPY, CHF, Gold",
            "risk_on": "Moderate risk appetite: Favor risk assets over havens",
            "strong_risk_off": "Strong risk aversion: Long Gold, JPY, CHF. Short equities, AUD, NZD",
            "risk_off": "Moderate risk aversion: Favor safe havens",
            "neutral": "Mixed signals - no clear risk bias"
        }
        return implications.get(sentiment, "")

    def _smart_money_flow(self, all_data: Dict[str, pd.DataFrame]) -> dict:
        """
        Proxy for Smart Money Flow using first/last hour price action.
        Smart money trades early session, dumb money follows late.
        """
        # Compare early candles vs late candles direction
        results = {}
        for symbol in ["^GSPC", "EURUSD=X", "GC=F"]:
            if symbol not in all_data:
                continue
            df = all_data[symbol]
            if len(df) < 96:  # Need at least 1 day of 15m bars
                continue

            # Last day's data (up to 96 bars = 24 hours)
            last_day = df.tail(96)

            # First quarter (first 6 hours) vs Last quarter direction
            first_q = last_day.head(24)
            last_q = last_day.tail(24)

            early_move = first_q["close"].iloc[-1] - first_q["open"].iloc[0]
            late_move = last_q["close"].iloc[-1] - last_q["open"].iloc[0]

            if early_move > 0 and late_move < 0:
                flow = "smart_money_bullish_dumb_bearish"
            elif early_move < 0 and late_move > 0:
                flow = "smart_money_bearish_dumb_bullish"
            elif early_move > 0 and late_move > 0:
                flow = "aligned_bullish"
            elif early_move < 0 and late_move < 0:
                flow = "aligned_bearish"
            else:
                flow = "neutral"

            results[symbol] = flow

        return results

    def _find_correlation_signals(self, all_data: Dict[str, pd.DataFrame], corr_matrix: pd.DataFrame) -> List[dict]:
        """Find trading signals from correlation analysis"""
        signals = []

        for (sym1, sym2), expected_rel in self.KNOWN_CORRELATIONS.items():
            if sym1 not in all_data or sym2 not in all_data:
                continue

            dir1 = self._get_recent_direction(all_data[sym1])
            dir2 = self._get_recent_direction(all_data[sym2])

            if dir1 == "neutral" or dir2 == "neutral":
                continue

            if expected_rel == "positive" and dir1 != dir2:
                signals.append({
                    "type": "divergence",
                    "pair1": sym1, "pair2": sym2,
                    "expected": "positive",
                    "actual": f"{sym1}={dir1}, {sym2}={dir2}",
                    "implication": f"Correlation divergence: {sym1} or {sym2} likely to reverse"
                })
            elif expected_rel == "negative" and dir1 == dir2:
                signals.append({
                    "type": "divergence",
                    "pair1": sym1, "pair2": sym2,
                    "expected": "negative",
                    "actual": f"{sym1}={dir1}, {sym2}={dir2}",
                    "implication": f"Unusual alignment - potential reversal"
                })

        return signals

    def _get_recent_direction(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < 10:
            return "neutral"
        pct = (df["close"].iloc[-1] - df["close"].iloc[-10]) / df["close"].iloc[-10]
        if pct > 0.001:
            return "bullish"
        elif pct < -0.001:
            return "bearish"
        return "neutral"
