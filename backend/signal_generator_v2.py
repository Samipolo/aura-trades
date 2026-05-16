"""
AURA TRADES - V2 Signal Generator (5x Enhanced)
Ensemble scoring system combining:
- Technical indicators
- Market structure
- Order flow
- Quantitative models
- Multi-timeframe alignment
- Pattern recognition
- Correlation analysis
- Risk management

Produces institutional-grade trade signals with dynamic R:R
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config import INDICATOR_CONFIG, INSTRUMENT_NAMES


class SignalGeneratorV2:
    """Enhanced signal generator with full multi-engine confluence"""

    def __init__(self):
        self.risk_reward = INDICATOR_CONFIG["risk_reward_ratio"]

    def generate_signal(self, symbol: str, indicator_data: dict, structure_data: dict,
                        correlation_score: float, quant_data: dict, orderflow_data: dict,
                        mtf_data: dict, pattern_data: dict,
                        all_data: Dict[str, pd.DataFrame] = None,
                        ict_data: dict = None, amt_data: dict = None,
                        session_data: dict = None, fundamental_data: dict = None,
                        institutional_data: dict = None, regime_data: dict = None,
                        macro_data: dict = None) -> Optional[dict]:
        """Generate enhanced trade signal with full multi-engine analysis"""
        if not indicator_data or not structure_data:
            return None

        df = indicator_data.get("df")
        levels = indicator_data.get("levels", {})
        signals = indicator_data.get("signals", {})

        if df is None or df.empty or len(df) < 200:
            return None

        current = df.iloc[-1]
        current_price = float(current["close"])
        atr = float(current.get("atr", 0))

        if atr == 0 or pd.isna(atr):
            return None

        # ===== COLLECT ALL CONFLUENCE FACTORS =====
        bullish_factors = []
        bearish_factors = []

        # --- TIER 1: TREND & STRUCTURE (High weight) ---
        # 1. EMA Trend (TOP PRIORITY ANALYSIS)
        trend = signals.get("trend", "neutral")
        if trend in ["strong_bullish", "bullish"]:
            bullish_factors.append(("ema_trend", 40 if "strong" in trend else 25))
        elif trend in ["strong_bearish", "bearish"]:
            bearish_factors.append(("ema_trend", 40 if "strong" in trend else 25))

        # 2. Market Structure (BOS/CHoCH)
        bias = structure_data.get("bias", "neutral")
        structure = structure_data.get("structure", {})
        bos = structure.get("bos")
        choch = structure.get("choch")

        if bias == "bullish":
            bullish_factors.append(("market_structure", 18))
        elif bias == "bearish":
            bearish_factors.append(("market_structure", 18))

        if choch:
            score = 20
            if choch["direction"] == "bullish":
                bullish_factors.append(("choch", score))
            else:
                bearish_factors.append(("choch", score))
        elif bos:
            score = 12
            if bos["direction"] == "bullish":
                bullish_factors.append(("bos", score))
            else:
                bearish_factors.append(("bos", score))

        # 3. Multi-Timeframe Alignment (CRITICAL)
        if mtf_data:
            alignment = mtf_data.get("alignment", {})
            mtf_direction = alignment.get("recommended_direction", "neutral")
            mtf_score = alignment.get("score", 0)
            mtf_quality = alignment.get("quality", "conflicting")

            if mtf_quality == "perfect_alignment":
                weight = 30
            elif mtf_quality == "strong_alignment":
                weight = 22
            elif mtf_quality == "moderate_alignment":
                weight = 14
            else:
                weight = 0

            if mtf_direction == "bullish" and weight > 0:
                bullish_factors.append(("mtf_alignment", weight))
            elif mtf_direction == "bearish" and weight > 0:
                bearish_factors.append(("mtf_alignment", weight))

            # Premium/Discount zone
            pd_zones = mtf_data.get("premium_discount", {})
            if pd_zones.get("in_ote_long"):
                bullish_factors.append(("ote_discount_zone", 15))
            elif pd_zones.get("in_ote_short"):
                bearish_factors.append(("ote_premium_zone", 15))
            elif pd_zones.get("signal") == "long":
                bullish_factors.append(("discount_zone", 8))
            elif pd_zones.get("signal") == "short":
                bearish_factors.append(("premium_zone", 8))

        # --- TIER 2: ORDER FLOW (High weight) ---
        if orderflow_data:
            # Delta Analysis
            delta = orderflow_data.get("delta", {})
            delta_momentum = delta.get("momentum", "balanced")
            if "strong_buyers" in delta_momentum:
                bullish_factors.append(("delta_buyers", 15))
            elif "moderate_buyers" in delta_momentum:
                bullish_factors.append(("delta_buyers", 8))
            elif "strong_sellers" in delta_momentum:
                bearish_factors.append(("delta_sellers", 15))
            elif "moderate_sellers" in delta_momentum:
                bearish_factors.append(("delta_sellers", 8))

            # Delta divergence
            if delta.get("divergence") == "bullish_divergence":
                bullish_factors.append(("delta_divergence", 12))
            elif delta.get("divergence") == "bearish_divergence":
                bearish_factors.append(("delta_divergence", 12))

            # Wyckoff Phase
            wyckoff = orderflow_data.get("wyckoff", {})
            wyckoff_signal = wyckoff.get("signal", "neutral")
            wyckoff_conf = wyckoff.get("confidence", 0)
            if wyckoff_signal == "bullish" and wyckoff_conf > 50:
                bullish_factors.append(("wyckoff_phase", min(20, wyckoff_conf // 5)))
            elif wyckoff_signal == "bearish" and wyckoff_conf > 50:
                bearish_factors.append(("wyckoff_phase", min(20, wyckoff_conf // 5)))

            # Stop Hunt
            stop_hunts = orderflow_data.get("stop_hunts", {})
            if stop_hunts.get("detected"):
                event = stop_hunts.get("recent_event", {})
                if event.get("type") == "buy_side_sweep":
                    bullish_factors.append(("stop_hunt_reversal", 18))
                elif event.get("type") == "sell_side_sweep":
                    bearish_factors.append(("stop_hunt_reversal", 18))

            # Trapped Traders
            trapped = orderflow_data.get("trapped_traders", {})
            if trapped.get("signal") == "bullish":
                bullish_factors.append(("trapped_shorts", 12))
            elif trapped.get("signal") == "bearish":
                bearish_factors.append(("trapped_longs", 12))

            # Absorption
            absorption = orderflow_data.get("absorption", {})
            if absorption.get("recent_signal") == "bullish":
                bullish_factors.append(("absorption", 10))
            elif absorption.get("recent_signal") == "bearish":
                bearish_factors.append(("absorption", 10))

            # Institutional Prints
            inst = orderflow_data.get("institutional_prints", {})
            if inst.get("bias") == "institutional_buying":
                bullish_factors.append(("institutional_flow", 14))
            elif inst.get("bias") == "institutional_selling":
                bearish_factors.append(("institutional_flow", 14))

            # Supply/Demand
            sd = orderflow_data.get("supply_demand", {})
            if sd.get("at_demand"):
                bullish_factors.append(("demand_zone", 12))
            elif sd.get("at_supply"):
                bearish_factors.append(("supply_zone", 12))

        # --- TIER 3: QUANTITATIVE MODELS ---
        if quant_data:
            # Kalman prediction
            kalman = quant_data.get("kalman", {})
            if kalman.get("prediction") == "bullish" and kalman.get("confidence", 0) > 30:
                bullish_factors.append(("kalman_prediction", min(12, kalman["confidence"] // 5)))
            elif kalman.get("prediction") == "bearish" and kalman.get("confidence", 0) > 30:
                bearish_factors.append(("kalman_prediction", min(12, kalman["confidence"] // 5)))

            # Hurst regime
            hurst = quant_data.get("hurst_exponent", {})
            if hurst.get("regime") == "trending":
                # Amplify trend signals
                if trend in ["strong_bullish", "bullish"]:
                    bullish_factors.append(("hurst_trending", 8))
                elif trend in ["strong_bearish", "bearish"]:
                    bearish_factors.append(("hurst_trending", 8))
            elif hurst.get("regime") == "mean_reverting":
                # Amplify reversal signals
                mr = quant_data.get("mean_reversion", {})
                if mr.get("signal") == "long_to_mean":
                    bullish_factors.append(("mean_reversion", 10))
                elif mr.get("signal") == "short_to_mean":
                    bearish_factors.append(("mean_reversion", 10))

            # Z-Score extremes
            z = quant_data.get("z_score", {})
            if z.get("signal") == "extremely_oversold":
                bullish_factors.append(("z_score_extreme", 14))
            elif z.get("signal") == "oversold":
                bullish_factors.append(("z_score_oversold", 8))
            elif z.get("signal") == "extremely_overbought":
                bearish_factors.append(("z_score_extreme", 14))
            elif z.get("signal") == "overbought":
                bearish_factors.append(("z_score_overbought", 8))

            # Momentum quality
            mom_q = quant_data.get("momentum_quality", {})
            if mom_q.get("type") == "institutional_flow":
                if trend in ["strong_bullish", "bullish"]:
                    bullish_factors.append(("momentum_quality", 10))
                elif trend in ["strong_bearish", "bearish"]:
                    bearish_factors.append(("momentum_quality", 10))

            # Price efficiency
            pe = quant_data.get("price_efficiency", {})
            if pe.get("signal") == "strong_trend":
                if trend in ["strong_bullish", "bullish"]:
                    bullish_factors.append(("price_efficiency", 8))
                elif trend in ["strong_bearish", "bearish"]:
                    bearish_factors.append(("price_efficiency", 8))

            # Microstructure
            micro = quant_data.get("microstructure", {})
            if micro.get("rejection_signal") == "buyers_rejecting_lows":
                bullish_factors.append(("microstructure_rejection", 8))
            elif micro.get("rejection_signal") == "sellers_rejecting_highs":
                bearish_factors.append(("microstructure_rejection", 8))

            if micro.get("exhaustion_detected"):
                # Exhaustion counters current direction
                if trend in ["strong_bullish", "bullish"]:
                    bearish_factors.append(("exhaustion_signal", 10))
                elif trend in ["strong_bearish", "bearish"]:
                    bullish_factors.append(("exhaustion_signal", 10))

        # --- TIER 4: PATTERNS ---
        if pattern_data:
            # Candlestick patterns
            candle_patterns = pattern_data.get("candlestick_patterns", [])
            for p in candle_patterns[-3:]:  # Last 3 patterns
                if p.get("significance") in ["high", "very_high"]:
                    weight = 12 if p["significance"] == "very_high" else 8
                    if p["direction"] == "bullish":
                        bullish_factors.append((f"candle_{p['name']}", weight))
                    elif p["direction"] == "bearish":
                        bearish_factors.append((f"candle_{p['name']}", weight))

            # Divergences
            divs = pattern_data.get("divergences", {})
            if "strong_bullish" in divs.get("overall", ""):
                bullish_factors.append(("strong_divergence", 16))
            elif "bullish" in divs.get("overall", ""):
                bullish_factors.append(("divergence", 10))
            elif "strong_bearish" in divs.get("overall", ""):
                bearish_factors.append(("strong_divergence", 16))
            elif "bearish" in divs.get("overall", ""):
                bearish_factors.append(("divergence", 10))

            # Chart patterns
            chart = pattern_data.get("chart_patterns", {})
            for cp in chart.get("patterns", []):
                if cp.get("significance") in ["high", "very_high"]:
                    weight = 18 if cp["significance"] == "very_high" else 12
                    if cp["direction"] == "bullish":
                        bullish_factors.append((f"chart_{cp['name']}", weight))
                    elif cp["direction"] == "bearish":
                        bearish_factors.append((f"chart_{cp['name']}", weight))

            # Institutional patterns
            inst_patterns = pattern_data.get("institutional_patterns", {})
            for ip in inst_patterns.get("patterns", []):
                if ip["direction"] == "bullish":
                    bullish_factors.append(("institutional_pattern", 15))
                elif ip["direction"] == "bearish":
                    bearish_factors.append(("institutional_pattern", 15))

        # --- TIER 5: INDICATORS & LEVELS ---
        # VWAP (TOP PRIORITY ANALYSIS)
        vwap_score = self._analyze_vwap(current_price, levels)
        if vwap_score > 0:
            bullish_factors.append(("vwap_confluence", vwap_score))
        elif vwap_score < 0:
            bearish_factors.append(("vwap_confluence", abs(vwap_score)))

        # Volume Profile (TOP PRIORITY ANALYSIS)
        vpoc_score = self._analyze_volume_profile(current_price, levels, atr)
        if vpoc_score > 0:
            bullish_factors.append(("volume_profile", vpoc_score))
        elif vpoc_score < 0:
            bearish_factors.append(("volume_profile", abs(vpoc_score)))

        # Bollinger Bands (50 EMA, 2.5 SD)
        bb_score = self._analyze_bollinger(current, df)
        if bb_score > 0:
            bullish_factors.append(("bollinger_bands", bb_score))
        elif bb_score < 0:
            bearish_factors.append(("bollinger_bands", abs(bb_score)))

        # Momentum
        momentum = signals.get("momentum", "neutral")
        if momentum == "bullish":
            bullish_factors.append(("rsi_macd_momentum", 10))
        elif momentum == "bearish":
            bearish_factors.append(("rsi_macd_momentum", 10))
        elif momentum == "oversold":
            bullish_factors.append(("oversold_bounce", 8))
        elif momentum == "overbought":
            bearish_factors.append(("overbought_reversal", 8))

        # Order Blocks
        ob_score = self._analyze_order_blocks(current_price, structure_data.get("order_blocks", []), atr)
        if ob_score > 0:
            bullish_factors.append(("order_block", ob_score))
        elif ob_score < 0:
            bearish_factors.append(("order_block", abs(ob_score)))

        # Fair Value Gaps
        fvg_score = self._analyze_fvgs(current_price, structure_data.get("fair_value_gaps", []), atr)
        if fvg_score > 0:
            bullish_factors.append(("fair_value_gap", fvg_score))
        elif fvg_score < 0:
            bearish_factors.append(("fair_value_gap", abs(fvg_score)))

        # Initial Balance (High weight)
        ib_score = self._analyze_initial_balance(current_price, levels.get("session_ib", {}), atr)
        if ib_score > 0:
            bullish_factors.append(("initial_balance", ib_score))
        elif ib_score < 0:
            bearish_factors.append(("initial_balance", abs(ib_score)))

        # --- TIER 6: ICT CONCEPTS ---
        if ict_data:
            ict_bias = ict_data.get("bias", "neutral")
            ict_score_val = ict_data.get("ict_score", 0)

            # MSS / CHoCH (highest ICT weight)
            mss = ict_data.get("mss", {})
            if mss.get("detected"):
                w = 22
                if mss["direction"] == "bullish":
                    bullish_factors.append(("ict_mss", w))
                else:
                    bearish_factors.append(("ict_mss", w))

            choch = ict_data.get("choch", {})
            if choch.get("detected"):
                w = 25
                if choch["direction"] == "bullish":
                    bullish_factors.append(("ict_choch", w))
                else:
                    bearish_factors.append(("ict_choch", w))

            # Displacement
            disp = ict_data.get("displacement", {})
            if disp.get("detected"):
                w = 15
                if disp["direction"] == "bullish":
                    bullish_factors.append(("ict_displacement", w))
                else:
                    bearish_factors.append(("ict_displacement", w))

            # Liquidity sweeps
            liq = ict_data.get("liquidity_sweeps", {})
            if liq.get("sell_side_swept"):
                bullish_factors.append(("liquidity_sweep_buy", 20))
            if liq.get("buy_side_swept"):
                bearish_factors.append(("liquidity_sweep_sell", 20))

            # OTE zone
            ote = ict_data.get("ote", {})
            if ote.get("ote_long"):
                bullish_factors.append(("ict_ote_long", 16))
            if ote.get("ote_short"):
                bearish_factors.append(("ict_ote_short", 16))

            # Kill zone amplifier
            kz = ict_data.get("kill_zone", {})
            if kz.get("in_kill_zone") and kz.get("quality") == "high":
                bullish_factors = [(n, int(s * 1.1)) for n, s in bullish_factors]
                bearish_factors = [(n, int(s * 1.1)) for n, s in bearish_factors]

            # Power of 3
            po3 = ict_data.get("power_of_3", {})
            if po3.get("signal") == "bullish":
                bullish_factors.append(("ict_po3", 14))
            elif po3.get("signal") == "bearish":
                bearish_factors.append(("ict_po3", 14))

            # Judas swing
            judas = ict_data.get("judas_swing", {})
            if judas.get("detected"):
                w = 18
                if judas["direction"] == "bullish":
                    bullish_factors.append(("ict_judas_swing", w))
                else:
                    bearish_factors.append(("ict_judas_swing", w))

            # Breaker blocks
            for bb in ict_data.get("breaker_blocks", [])[:2]:
                if bb.get("active"):
                    w = 12
                    if bb["type"] == "bullish":
                        bullish_factors.append(("ict_breaker_block", w))
                    else:
                        bearish_factors.append(("ict_breaker_block", w))

            # HTF ICT confluence
            for tf_key, htf in ict_data.get("htf_ict", {}).items():
                htf_b = htf.get("bias", "neutral")
                w = 15 if tf_key == "4h" else 10
                if htf_b == "bullish":
                    bullish_factors.append((f"ict_htf_{tf_key}", w))
                elif htf_b == "bearish":
                    bearish_factors.append((f"ict_htf_{tf_key}", w))

        # --- TIER 7: AUCTION MARKET THEORY ---
        if amt_data:
            # Value Area positioning
            pos = amt_data.get("price_position", {})
            zone = pos.get("zone", "unknown")
            if zone == "below_value":
                bullish_factors.append(("amt_below_value", 14))
            elif zone == "above_value":
                bearish_factors.append(("amt_above_value", 14))

            # Balance / Imbalance (PBD Logic)
            bal = amt_data.get("balance_state", {})
            bal_signal = bal.get("signal", "neutral")
            
            tpo = amt_data.get("tpo", {})
            dist = tpo.get("distribution", "unknown")
            
            if dist == "P_shape" or bal_signal == "bullish":
                bullish_factors.append(("amt_pbd_bullish", 25))
            elif dist == "b_shape" or bal_signal == "bearish":
                bearish_factors.append(("amt_pbd_bearish", 25))
            elif dist == "D_shape":
                # Balanced market, slight weight to current bias
                if trend in ["strong_bullish", "bullish"]:
                    bullish_factors.append(("amt_pbd_balanced_bull", 10))
                elif trend in ["strong_bearish", "bearish"]:
                    bearish_factors.append(("amt_pbd_balanced_bear", 10))

            # IB breakout
            ib = amt_data.get("initial_balance", {})
            if ib.get("above_ib"):
                bullish_factors.append(("amt_ib_breakout_up", 12))
            elif ib.get("below_ib"):
                bearish_factors.append(("amt_ib_breakout_down", 12))

            # Day type
            dt = amt_data.get("day_type", {}).get("type", "unknown")
            if dt == "trend":
                if bal_signal == "bullish":
                    bullish_factors.append(("amt_trend_day", 10))
                elif bal_signal == "bearish":
                    bearish_factors.append(("amt_trend_day", 10))

            # Excess at extremes
            excess = amt_data.get("excess", {})
            if excess.get("high_excess"):
                bearish_factors.append(("amt_excess_highs", 10))
            if excess.get("low_excess"):
                bullish_factors.append(("amt_excess_lows", 10))

            # Rotation factor
            rot = amt_data.get("rotation_factor", {})
            rot_interp = rot.get("interpretation", "neutral")
            if "bullish" in rot_interp:
                w = 10 if "strong" in rot_interp else 6
                bullish_factors.append(("amt_rotation", w))
            elif "bearish" in rot_interp:
                w = 10 if "strong" in rot_interp else 6
                bearish_factors.append(("amt_rotation", w))

            # HTF profile confluence
            for tf_key, prof in amt_data.get("htf_profile", {}).items():
                if prof.get("poc"):
                    w = 8 if tf_key == "4h" else 5
                    if current_price > prof["poc"]:
                        bullish_factors.append((f"amt_{tf_key}_poc", w))
                    else:
                        bearish_factors.append((f"amt_{tf_key}_poc", w))

        # --- TIER 8: ENHANCED QUANT ---
        if quant_data:
            # Fractal dimension
            fd = quant_data.get("fractal_dimension", {})
            fd_sig = fd.get("signal", "neutral")
            if fd_sig in ["strong_trend", "trending"]:
                w = 10 if fd_sig == "strong_trend" else 6
                if trend in ["strong_bullish", "bullish"]:
                    bullish_factors.append(("fractal_trending", w))
                elif trend in ["strong_bearish", "bearish"]:
                    bearish_factors.append(("fractal_trending", w))

            # Information ratio
            ir = quant_data.get("information_ratio", {})
            ir_sig = ir.get("signal", "neutral")
            if "bullish" in ir_sig:
                w = 12 if "strong" in ir_sig else 8
                bullish_factors.append(("info_ratio_bull", w))
            elif "bearish" in ir_sig:
                w = 12 if "strong" in ir_sig else 8
                bearish_factors.append(("info_ratio_bear", w))

            # VWAP deviation
            vd = quant_data.get("vwap_deviation", {})
            vd_sig = vd.get("signal", "neutral")
            if "extremely_below" in vd_sig:
                bullish_factors.append(("vwap_extreme_low", 12))
            elif "below" in vd_sig:
                bullish_factors.append(("vwap_below", 6))
            elif "extremely_above" in vd_sig:
                bearish_factors.append(("vwap_extreme_high", 12))
            elif "above" in vd_sig:
                bearish_factors.append(("vwap_above", 6))

            # Spectral cycle
            spec = quant_data.get("spectral", {})
            if spec.get("has_clear_cycle"):
                spec_sig = spec.get("signal", "neutral")
                if spec_sig == "cycle_bottom":
                    bullish_factors.append(("cycle_bottom", 10))
                elif spec_sig == "cycle_top":
                    bearish_factors.append(("cycle_top", 10))

        # --- TIER 9: SESSION ANALYSIS ---
        if session_data:
            # London IB
            lib = session_data.get("london_ib", {})
            if lib.get("valid"):
                if lib.get("signal") == "bullish":
                    bullish_factors.append(("london_ib_bull", 18))
                elif lib.get("signal") == "bearish":
                    bearish_factors.append(("london_ib_bear", 18))
                if lib.get("predicted_day_type") == "trend":
                    # Amplify on predicted trend days
                    bullish_factors = [(n, int(s * 1.05)) for n, s in bullish_factors]
                    bearish_factors = [(n, int(s * 1.05)) for n, s in bearish_factors]

            # Asian Range Breakout
            ar = session_data.get("asian_range", {})
            if ar.get("valid"):
                if ar.get("signal") == "bullish":
                    bullish_factors.append(("asian_breakout_bull", 16))
                elif ar.get("signal") == "bearish":
                    bearish_factors.append(("asian_breakout_bear", 16))

            # NY Open
            ny = session_data.get("ny_open", {})
            if ny.get("valid"):
                if ny.get("signal") == "bullish":
                    bullish_factors.append(("ny_drive_bull", 12))
                elif ny.get("signal") == "bearish":
                    bearish_factors.append(("ny_drive_bear", 12))

            # Session VWAP
            svwap = session_data.get("session_vwap", {})
            if svwap.get("valid"):
                if svwap.get("signal") == "bullish":
                    bullish_factors.append(("session_vwap_low", 10))
                elif svwap.get("signal") == "bearish":
                    bearish_factors.append(("session_vwap_high", 10))

            # ORB
            orb = session_data.get("orb", {})
            if orb.get("valid"):
                if orb.get("signal") == "bullish":
                    bullish_factors.append(("orb_bull", 10))
                elif orb.get("signal") == "bearish":
                    bearish_factors.append(("orb_bear", 10))

            # Kill zone amplifier
            kz = session_data.get("kill_zone", {})
            if kz.get("tradeable"):
                bullish_factors = [(n, int(s * 1.08)) for n, s in bullish_factors]
                bearish_factors = [(n, int(s * 1.08)) for n, s in bearish_factors]

        # --- TIER 10: FUNDAMENTALS & NEWS ---
        if fundamental_data:
            fs = fundamental_data.get("fundamental_score", {})
            if fs.get("bias") == "bullish":
                w = 20 if fs.get("bullish_score", 0) > 50 else 12
                bullish_factors.append(("fundamental_bull", w))
            elif fs.get("bias") == "bearish":
                w = 20 if fs.get("bearish_score", 0) > 50 else 12
                bearish_factors.append(("fundamental_bear", w))

            # Rate differential
            rd = fundamental_data.get("rate_differential", {})
            if "bullish" in rd.get("signal", ""):
                bullish_factors.append(("rate_diff_bull", 10))
            elif "bearish" in rd.get("signal", ""):
                bearish_factors.append(("rate_diff_bear", 10))

            # News sentiment
            ns = fundamental_data.get("news_sentiment", {})
            if ns.get("signal") == "bullish":
                bullish_factors.append(("news_bull", 8))
            elif ns.get("signal") == "bearish":
                bearish_factors.append(("news_bear", 8))

        # --- TIER 11: INSTITUTIONAL FLOW ---
        if institutional_data:
            # Smart money
            sm = institutional_data.get("smart_money", {})
            if sm.get("signal") == "bullish":
                bullish_factors.append(("smart_money_buy", 22))
            elif sm.get("signal") == "bearish":
                bearish_factors.append(("smart_money_sell", 22))

            # Accumulation/Distribution
            ad = institutional_data.get("accum_distrib", {})
            if ad.get("signal") == "bullish":
                bullish_factors.append(("accumulation", 16))
            elif ad.get("signal") == "bearish":
                bearish_factors.append(("distribution", 16))

            # Institutional footprint
            fp = institutional_data.get("institutional_footprint", {})
            if fp.get("signal") == "bullish":
                bullish_factors.append(("inst_footprint_buy", 14))
            elif fp.get("signal") == "bearish":
                bearish_factors.append(("inst_footprint_sell", 14))

            # Liquidity engineering
            le = institutional_data.get("liquidity_engineering", {})
            if le.get("signal") == "bullish":
                bullish_factors.append(("liq_grab_bull", 18))
            elif le.get("signal") == "bearish":
                bearish_factors.append(("liq_grab_bear", 18))

            # Position commitment
            cm = institutional_data.get("commitment", {})
            if cm.get("signal") == "bullish":
                bullish_factors.append(("commitment_long", 10))
            elif cm.get("signal") == "bearish":
                bearish_factors.append(("commitment_short", 10))

        # --- TIER 12: REGIME ---
        if regime_data:
            # Regime quality multiplier
            quality = regime_data.get("current_regime", {}).get("quality", "fair")
            if quality == "very_poor":
                bullish_factors = [(n, int(s * 0.6)) for n, s in bullish_factors]
                bearish_factors = [(n, int(s * 0.6)) for n, s in bearish_factors]
            elif quality == "poor":
                bullish_factors = [(n, int(s * 0.8)) for n, s in bullish_factors]
                bearish_factors = [(n, int(s * 0.8)) for n, s in bearish_factors]
            elif quality == "excellent":
                bullish_factors = [(n, int(s * 1.1)) for n, s in bullish_factors]
                bearish_factors = [(n, int(s * 1.1)) for n, s in bearish_factors]

            # Trend regime confirmation
            tr = regime_data.get("trend_regime", {})
            if tr.get("regime") == "strong_trend":
                if tr.get("direction") == "bullish":
                    bullish_factors.append(("regime_strong_trend_bull", 12))
                elif tr.get("direction") == "bearish":
                    bearish_factors.append(("regime_strong_trend_bear", 12))

        # --- TIER 13: MACRO INTERMARKET ---
        if macro_data:
            cm = macro_data.get("currency_macro", {})
            if cm.get("bias") == "bullish":
                w = 15 if cm.get("net", 0) > 20 else 8
                bullish_factors.append(("macro_bull", w))
            elif cm.get("bias") == "bearish":
                w = 15 if cm.get("net", 0) < -20 else 8
                bearish_factors.append(("macro_bear", w))

            # Risk sentiment
            rs = macro_data.get("risk_sentiment", {})
            rs_sig = rs.get("signal", "neutral")
            if rs_sig == "risk_on":
                # Risk-on = favor AUD, NZD, CAD, equities
                if symbol and any(c in symbol.upper() for c in ["AUD", "NZD", "CAD"]):
                    bullish_factors.append(("risk_on_commodity", 10))
                elif symbol and "JPY" in symbol.upper() and "=X" in symbol:
                    bearish_factors.append(("risk_on_vs_jpy", 8))
            elif rs_sig == "risk_off":
                if symbol and any(c in symbol.upper() for c in ["JPY", "CHF"]):
                    bullish_factors.append(("risk_off_safe_haven", 10))
                elif symbol and any(c in symbol.upper() for c in ["AUD", "NZD"]):
                    bearish_factors.append(("risk_off_commodity", 8))

        # Correlation
        if correlation_score > 65:
            pass
        elif correlation_score < 35:
            bullish_factors = [(n, int(s * 0.8)) for n, s in bullish_factors]
            bearish_factors = [(n, int(s * 0.8)) for n, s in bearish_factors]

        # ===== CALCULATE FINAL SCORES =====
        bull_score = sum(s for _, s in bullish_factors)
        bear_score = sum(s for _, s in bearish_factors)

        # Higher threshold for V2 (more factors available)
        min_score = 60

        if bull_score < min_score and bear_score < min_score:
            return None

        # Direction determination
        if bull_score > bear_score and bull_score >= min_score:
            direction = "LONG"
            score = bull_score
            factors = bullish_factors
        elif bear_score > bull_score and bear_score >= min_score:
            direction = "SHORT"
            score = bear_score
            factors = bearish_factors
        else:
            return None

        # Filter: don't trade against strong MTF alignment
        if mtf_data:
            mtf_dir = mtf_data.get("alignment", {}).get("recommended_direction", "neutral")
            if mtf_dir == "bullish" and direction == "SHORT":
                score = int(score * 0.6)  # Penalize counter-trend
            elif mtf_dir == "bearish" and direction == "LONG":
                score = int(score * 0.6)

        # Calculate entry, SL, TP
        entry, sl, tp = self._calculate_levels(current_price, direction, atr, levels, structure_data, mtf_data)

        # Confidence score (0-100)
        max_possible_score = 800  # Theoretical max with 15 engines firing
        confidence = min(98, (score / max_possible_score) * 100 + 20)

        # Adjust by correlation
        if correlation_score < 40:
            confidence *= 0.85

        return {
            "symbol": symbol,
            "display_name": INSTRUMENT_NAMES.get(symbol, symbol),
            "direction": direction,
            "entry": round(entry, 5),
            "stop_loss": round(sl, 5),
            "take_profit": round(tp, 5),
            "risk_reward": self.risk_reward,
            "confidence": round(confidence, 1),
            "score": score,
            "factors": [{"name": name, "score": s} for name, s in sorted(factors, key=lambda x: x[1], reverse=True)],
            "trend": trend,
            "momentum": momentum,
            "volatility": signals.get("volatility", "normal"),
            "market_structure": bias,
            "correlation_score": round(correlation_score, 1),
            "current_price": current_price,
            "atr": round(atr, 5),
            "timestamp": str(df.index[-1]),
            # V2 enhanced fields
            "num_factors": len(factors),
            "quant_regime": quant_data.get("regime", {}).get("regime", "unknown") if quant_data else "unknown",
            "hurst": quant_data.get("hurst_exponent", {}).get("value", 0.5) if quant_data else 0.5,
            "wyckoff_phase": orderflow_data.get("wyckoff", {}).get("phase", "unknown") if orderflow_data else "unknown",
            "mtf_quality": mtf_data.get("alignment", {}).get("quality", "unknown") if mtf_data else "unknown",
            "win_probability": 0,  # Set by risk engine
            "trade_quality": 0,    # Set by risk engine
            "risk_grade": "—",     # Set by risk engine
        }

    def _analyze_vwap(self, price: float, levels: dict) -> int:
        score = 0
        # Increased VWAP weights (TOP PRIORITY)
        for key, weight in [("daily_vwap", 15), ("weekly_vwap", 20), ("monthly_vwap", 25),
                            ("prev_day_vwap", 10), ("prev_week_vwap", 15)]:
            vwap = levels.get(key, {}).get("value")
            if vwap and vwap > 0:
                score += weight if price > vwap else -weight
        return score

    def _analyze_volume_profile(self, price: float, levels: dict, atr: float) -> int:
        score = 0
        # Increased Volume Profile weights (TOP PRIORITY)
        daily_vpoc = levels.get("daily_vpoc", {}).get("poc")
        daily_vah = levels.get("daily_vpoc", {}).get("vah")
        daily_val = levels.get("daily_vpoc", {}).get("val")

        if daily_vpoc and atr > 0:
            distance = abs(price - daily_vpoc) / atr
            if distance < 0.5:
                score += 20 if price > daily_vpoc else -20
            elif price > daily_vpoc:
                score += 15
            else:
                score -= 15

        if daily_vah and daily_val:
            if price > daily_vah:
                score += 18
            elif price < daily_val:
                score -= 18
        return score

    def _analyze_bollinger(self, current: pd.Series, df: pd.DataFrame) -> int:
        bb_upper = current.get("bb_upper")
        bb_lower = current.get("bb_lower")
        close = current["close"]

        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return 0

        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0

        # Bollinger Bands weights increased
        position = (close - bb_lower) / bb_range
        if position > 0.9:
            return -20
        elif position < 0.1:
            return 20
        elif position > 0.5:
            return 10
        else:
            return -10

    def _analyze_order_blocks(self, price: float, order_blocks: list, atr: float) -> int:
        score = 0
        for ob in order_blocks:
            distance = abs(price - (ob["high"] + ob["low"]) / 2) / atr if atr > 0 else float('inf')
            if distance < 1.5:
                if ob["type"] == "bullish" and price >= ob["low"] and price <= ob["high"]:
                    score += 10
                elif ob["type"] == "bearish" and price >= ob["low"] and price <= ob["high"]:
                    score -= 10
        return score

    def _analyze_fvgs(self, price: float, fvgs: list, atr: float) -> int:
        score = 0
        for fvg in fvgs:
            if fvg["type"] == "bullish" and price >= fvg["low"] and price <= fvg["high"]:
                score += 8
            elif fvg["type"] == "bearish" and price >= fvg["low"] and price <= fvg["high"]:
                score -= 8
        return score

    def _analyze_initial_balance(self, price: float, ib: dict, atr: float) -> int:
        ib_high = ib.get("high")
        ib_low = ib.get("low")
        if ib_high is None or ib_low is None:
            return 0
        # Increased IB weight
        if price > ib_high:
            return 25
        elif price < ib_low:
            return -25
        return 0

    def _calculate_levels(self, price: float, direction: str, atr: float,
                          levels: dict, structure_data: dict, mtf_data: dict) -> tuple:
        """Calculate entry, SL, TP with structure-based levels"""
        sl_distance = atr * 1.5

        structure = structure_data.get("structure", {})
        last_high = structure.get("last_swing_high")
        last_low = structure.get("last_swing_low")

        if direction == "LONG":
            entry = price
            if last_low and 0 < (price - last_low) < sl_distance * 2:
                sl = last_low - (atr * 0.2)
            else:
                sl = price - sl_distance
            risk = entry - sl
            tp = entry + (risk * self.risk_reward)
        else:
            entry = price
            if last_high and 0 < (last_high - price) < sl_distance * 2:
                sl = last_high + (atr * 0.2)
            else:
                sl = price + sl_distance
            risk = sl - entry
            tp = entry - (risk * self.risk_reward)

        return entry, sl, tp


class TradeRankerV2:
    """Enhanced ranking system with risk-adjusted scoring"""

    def rank_signals(self, signals: List[dict]) -> List[dict]:
        """Rank signals using comprehensive multi-factor scoring"""
        if not signals:
            return []

        for signal in signals:
            signal["rank_score"] = self._calculate_rank_score(signal)

        ranked = sorted(signals, key=lambda x: x["rank_score"], reverse=True)

        for i, signal in enumerate(ranked):
            signal["rank"] = i + 1

        return ranked

    def _calculate_rank_score(self, signal: dict) -> float:
        """Enhanced composite ranking score"""
        score = 0.0

        # Trade quality (35% weight) - from risk engine
        score += signal.get("trade_quality", signal.get("confidence", 50)) * 0.35

        # Number of factors (20% weight) - more confluence = better
        num_factors = signal.get("num_factors", len(signal.get("factors", [])))
        score += min(num_factors * 2.5, 20)

        # Correlation alignment (10% weight)
        corr = signal.get("correlation_score", 50)
        score += (corr / 100) * 10

        # MTF quality (15% weight)
        mtf_quality = signal.get("mtf_quality", "unknown")
        mtf_scores = {"perfect_alignment": 15, "strong_alignment": 12,
                      "moderate_alignment": 8, "conflicting": 2, "unknown": 5}
        score += mtf_scores.get(mtf_quality, 5)

        # Win probability (10% weight)
        win_prob = signal.get("win_probability", 50)
        score += (win_prob / 100) * 10

        # Risk grade (10% weight)
        grade = signal.get("risk_grade", "C")
        grade_scores = {"A+": 10, "A": 8, "B": 6, "C": 4, "D": 2, "F": 0, "—": 5}
        score += grade_scores.get(grade, 4)

        return score
