"""
AURA TRADES - Advanced Risk Management Engine
Institutional-grade position sizing and risk control:
- Kelly Criterion position sizing
- Dynamic R:R based on structure
- Signal freshness decay
- Drawdown-aware confidence adjustment
- Session timing filters
- Volatility-adjusted sizing
- Win probability estimation
- Maximum confluence requirement
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from typing import Dict, Optional
from config import SESSIONS


class RiskEngine:
    """Advanced risk management and position sizing"""

    def __init__(self):
        self.base_risk_pct = 1.0  # 1% base risk per trade
        self.max_risk_pct = 2.0   # Maximum 2% risk
        self.min_confidence = 55   # Minimum confidence to trade

    def evaluate_trade(self, signal: dict, quant_data: dict, orderflow_data: dict,
                       mtf_data: dict, pattern_data: dict) -> dict:
        """
        Comprehensive trade evaluation with risk-adjusted scoring.
        Returns enhanced signal with risk metrics.
        """
        if not signal:
            return {}

        # 1. Kelly Criterion sizing
        kelly = self._kelly_criterion(signal, quant_data)

        # 2. Session timing quality
        session_score = self._session_timing_score(signal)

        # 3. Signal freshness
        freshness = self._signal_freshness(signal)

        # 4. Volatility adjustment
        vol_adjustment = self._volatility_adjustment(quant_data)

        # 5. Multi-factor confluence count
        confluence = self._confluence_score(signal, quant_data, orderflow_data, mtf_data, pattern_data)

        # 6. Win probability estimation
        win_prob = self._estimate_win_probability(signal, quant_data, orderflow_data, mtf_data)

        # 7. Risk grade
        risk_grade = self._calculate_risk_grade(confluence, win_prob, session_score, vol_adjustment)

        # 8. Optimal position size
        position_size = self._optimal_position_size(kelly, vol_adjustment, risk_grade)

        # 9. Dynamic R:R adjustment
        dynamic_rr = self._dynamic_risk_reward(signal, quant_data, mtf_data)

        # 10. Trade quality score (0-100)
        trade_quality = self._trade_quality_score(
            confluence, win_prob, session_score, freshness,
            vol_adjustment, risk_grade, mtf_data
        )

        return {
            "kelly_fraction": kelly,
            "session_score": session_score,
            "freshness": freshness,
            "vol_adjustment": vol_adjustment,
            "confluence_score": confluence,
            "win_probability": win_prob,
            "risk_grade": risk_grade,
            "position_size_pct": position_size,
            "dynamic_rr": dynamic_rr,
            "trade_quality": trade_quality,
            "should_trade": trade_quality >= 60 and win_prob >= 50,
            "warnings": self._generate_warnings(signal, quant_data, orderflow_data, session_score)
        }

    def _kelly_criterion(self, signal: dict, quant_data: dict) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        where p=win prob, b=reward/risk ratio, q=loss prob
        We use half-Kelly for safety
        """
        # Estimate win probability from confidence
        confidence = signal.get("confidence", 50)
        p = confidence / 100  # Win probability
        q = 1 - p
        b = signal.get("risk_reward", 2.0)  # Reward/Risk

        if b <= 0:
            return 0.0

        kelly = (p * b - q) / b
        half_kelly = max(0, kelly * 0.5)  # Half-Kelly for safety

        return round(min(half_kelly, 0.05), 4)  # Cap at 5%

    def _session_timing_score(self, signal: dict) -> float:
        """
        Score based on trading session.
        Best: London/NY overlap, Good: London/NY open, Poor: Asian quiet hours
        """
        try:
            now = datetime.now(pytz.UTC)
            hour = now.hour

            # London/NY overlap (12:00-16:00 UTC) = best liquidity
            if 12 <= hour <= 16:
                return 100.0
            # London session (07:00-16:00 UTC)
            elif 7 <= hour <= 16:
                return 85.0
            # NY session (12:00-21:00 UTC)
            elif 12 <= hour <= 21:
                return 80.0
            # Asian session (00:00-09:00 UTC) - lower liquidity
            elif 0 <= hour <= 9:
                return 50.0
            else:
                return 40.0
        except:
            return 70.0

    def _signal_freshness(self, signal: dict) -> float:
        """
        Signals decay over time. Fresh signals > stale signals.
        Returns 0-100 (100 = just generated, 0 = very stale)
        """
        try:
            signal_time = pd.Timestamp(signal.get("timestamp", ""))
            now = pd.Timestamp.now(tz="UTC")
            if signal_time.tz is None:
                signal_time = signal_time.tz_localize("UTC")

            age_minutes = (now - signal_time).total_seconds() / 60

            # Decay curve: 100% at 0 min, 50% at 60 min, 20% at 180 min
            freshness = 100 * np.exp(-age_minutes / 120)
            return round(max(0, min(100, float(freshness))), 1)
        except:
            return 80.0

    def _volatility_adjustment(self, quant_data: dict) -> float:
        """
        Adjust position size based on volatility regime.
        High vol = reduce size, Low vol = normal or increase
        """
        vol_regime = quant_data.get("volatility_regime", {})
        regime = vol_regime.get("regime", "normal")
        percentile = vol_regime.get("percentile", 50)

        adjustments = {
            "extreme_high": 0.4,   # Reduce to 40%
            "elevated": 0.7,       # Reduce to 70%
            "normal": 1.0,         # Full size
            "low": 1.1,            # Slightly above
            "compressed": 0.9,     # Slightly below (squeeze about to break)
        }

        return adjustments.get(regime, 1.0)

    def _confluence_score(self, signal: dict, quant_data: dict,
                          orderflow_data: dict, mtf_data: dict, pattern_data: dict) -> float:
        """
        Count unique confluent factors across all engines.
        More confluence = higher probability trade.
        """
        confluence_count = 0
        direction = signal.get("direction", "")
        is_long = direction == "LONG"

        # From base signal factors
        confluence_count += len(signal.get("factors", []))

        # From quant engine
        if quant_data:
            hurst = quant_data.get("hurst_exponent", {})
            if hurst.get("regime") == "trending":
                confluence_count += 1

            kalman = quant_data.get("kalman", {})
            if (is_long and kalman.get("prediction") == "bullish") or \
               (not is_long and kalman.get("prediction") == "bearish"):
                confluence_count += 1

            regime = quant_data.get("regime", {})
            if (is_long and "uptrend" in regime.get("regime", "")) or \
               (not is_long and "downtrend" in regime.get("regime", "")):
                confluence_count += 1

            momentum_q = quant_data.get("momentum_quality", {})
            if momentum_q.get("type") == "institutional_flow":
                confluence_count += 2

        # From order flow
        if orderflow_data:
            delta = orderflow_data.get("delta", {})
            if (is_long and "buyers" in delta.get("momentum", "")) or \
               (not is_long and "sellers" in delta.get("momentum", "")):
                confluence_count += 1

            wyckoff = orderflow_data.get("wyckoff", {})
            if (is_long and wyckoff.get("signal") == "bullish") or \
               (not is_long and wyckoff.get("signal") == "bearish"):
                confluence_count += 2

            trapped = orderflow_data.get("trapped_traders", {})
            if (is_long and trapped.get("signal") == "bullish") or \
               (not is_long and trapped.get("signal") == "bearish"):
                confluence_count += 1

        # From MTF
        if mtf_data:
            alignment = mtf_data.get("alignment", {})
            if alignment.get("all_aligned"):
                confluence_count += 3
            elif alignment.get("quality") == "strong_alignment":
                confluence_count += 2

            pd_zones = mtf_data.get("premium_discount", {})
            if (is_long and pd_zones.get("signal") == "long") or \
               (not is_long and pd_zones.get("signal") == "short"):
                confluence_count += 2

        # From patterns
        if pattern_data:
            divergences = pattern_data.get("divergences", {})
            if (is_long and "bullish" in divergences.get("overall", "")) or \
               (not is_long and "bearish" in divergences.get("overall", "")):
                confluence_count += 2

        # Normalize to 0-100
        return min(100, confluence_count * 5)

    def _estimate_win_probability(self, signal: dict, quant_data: dict,
                                   orderflow_data: dict, mtf_data: dict) -> float:
        """
        Estimate win probability using multiple factors
        """
        base_prob = signal.get("confidence", 50)

        # Adjustments
        adjustments = 0

        # Monte Carlo probability
        if quant_data:
            mc = quant_data.get("monte_carlo", {})
            mc_edge = mc.get("risk_adjusted_edge", 0)
            adjustments += mc_edge * 0.2  # 20% weight

        # MTF alignment
        if mtf_data:
            mtf_score = mtf_data.get("mtf_score", 0)
            adjustments += (mtf_score - 50) * 0.15  # 15% weight

        # Order flow
        if orderflow_data:
            delta = orderflow_data.get("delta", {})
            delta_score = delta.get("score", 0)
            adjustments += (delta_score - 50) * 0.1  # 10% weight

        final_prob = base_prob + adjustments
        return round(max(20, min(95, final_prob)), 1)

    def _calculate_risk_grade(self, confluence: float, win_prob: float,
                              session_score: float, vol_adjustment: float) -> str:
        """
        Calculate overall risk grade: A+, A, B, C, D, F
        """
        composite = (
            confluence * 0.3 +
            win_prob * 0.3 +
            session_score * 0.2 +
            vol_adjustment * 100 * 0.2
        )

        if composite >= 85:
            return "A+"
        elif composite >= 75:
            return "A"
        elif composite >= 65:
            return "B"
        elif composite >= 55:
            return "C"
        elif composite >= 45:
            return "D"
        else:
            return "F"

    def _optimal_position_size(self, kelly: float, vol_adjustment: float, risk_grade: str) -> float:
        """Calculate optimal position size as % of account"""
        grade_multipliers = {"A+": 1.0, "A": 0.85, "B": 0.7, "C": 0.5, "D": 0.3, "F": 0}
        multiplier = grade_multipliers.get(risk_grade, 0.5)

        # Base = 1% risk, adjusted by Kelly, volatility, and grade
        position = self.base_risk_pct * kelly * 20 * vol_adjustment * multiplier
        return round(max(0.25, min(self.max_risk_pct, position)), 2)

    def _dynamic_risk_reward(self, signal: dict, quant_data: dict, mtf_data: dict) -> float:
        """
        Dynamically adjust R:R based on context.
        Strong setups may warrant 1:3+, weak setups stick to 1:2
        """
        base_rr = 2.0

        # Strong trend regime = extend target
        if quant_data:
            hurst = quant_data.get("hurst_exponent", {})
            if hurst.get("value", 0.5) > 0.65:
                base_rr += 0.5

            efficiency = quant_data.get("price_efficiency", {})
            if efficiency.get("ratio", 0) > 0.5:
                base_rr += 0.3

        # Perfect MTF alignment = extend target
        if mtf_data:
            alignment = mtf_data.get("alignment", {})
            if alignment.get("all_aligned"):
                base_rr += 0.5
            elif alignment.get("quality") == "strong_alignment":
                base_rr += 0.3

        return round(min(4.0, base_rr), 1)

    def _trade_quality_score(self, confluence: float, win_prob: float,
                             session_score: float, freshness: float,
                             vol_adjustment: float, risk_grade: str, mtf_data: dict) -> float:
        """
        Master trade quality score (0-100)
        This is the ultimate decision metric.
        """
        grade_scores = {"A+": 100, "A": 85, "B": 70, "C": 55, "D": 40, "F": 20}

        score = (
            confluence * 0.25 +
            win_prob * 0.25 +
            session_score * 0.15 +
            freshness * 0.10 +
            grade_scores.get(risk_grade, 50) * 0.15 +
            (mtf_data.get("mtf_score", 50) if mtf_data else 50) * 0.10
        )

        return round(max(0, min(100, score)), 1)

    def _generate_warnings(self, signal: dict, quant_data: dict,
                           orderflow_data: dict, session_score: float) -> List:
        """Generate risk warnings for the trade"""
        warnings = []

        # Low session liquidity
        if session_score < 50:
            warnings.append("Low liquidity session - wider spreads expected")

        # Extreme volatility
        if quant_data:
            vol = quant_data.get("volatility_regime", {})
            if vol.get("regime") == "extreme_high":
                warnings.append("EXTREME volatility - reduce position size significantly")

            # Mean reversion conflict
            mr = quant_data.get("mean_reversion", {})
            direction = signal.get("direction", "")
            if direction == "LONG" and mr.get("signal") == "short_to_mean":
                warnings.append("Mean reversion model suggests downside - conflicting")
            elif direction == "SHORT" and mr.get("signal") == "long_to_mean":
                warnings.append("Mean reversion model suggests upside - conflicting")

        # Exhaustion warning
        if orderflow_data:
            exhaustion = orderflow_data.get("exhaustion", {})
            if exhaustion.get("exhaustion"):
                warnings.append(f"Momentum exhaustion detected: {exhaustion.get('type')}")

        return warnings


# Import List type hint
from typing import List
