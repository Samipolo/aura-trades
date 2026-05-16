"""
AURA TRADES — Trade Journal Engine (Tradezella-Style)
Persistent SQLite journal with auto-outcome monitoring via Yahoo Finance.
+1 point for TP hit, -1 point for SL hit.
"""

import sqlite3
import json
import os
import threading
import time as _time
from datetime import datetime, timezone
from typing import Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "aura_journal.db")
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(_DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            display_name TEXT,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            current_price REAL,
            status TEXT DEFAULT 'OPEN',
            outcome TEXT DEFAULT NULL,
            points INTEGER DEFAULT 0,
            pnl_pips REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            risk_grade TEXT DEFAULT '',
            risk_reward REAL DEFAULT 0,
            win_probability REAL DEFAULT 0,
            factors TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            screenshot_url TEXT DEFAULT '',
            opened_at TEXT NOT NULL,
            closed_at TEXT DEFAULT NULL,
            session TEXT DEFAULT '',
            timeframe TEXT DEFAULT '15m',
            asset_class TEXT DEFAULT '',
            ict_bias TEXT DEFAULT '',
            wyckoff_phase TEXT DEFAULT '',
            extra_json TEXT DEFAULT '{}'
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS journal_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        c.commit()


_init_db()


# ══════════════════════════════════════════════════════════════════════════════
# CRUD Operations
# ══════════════════════════════════════════════════════════════════════════════

def open_trade(signal: dict, notes: str = "") -> int:
    """Record a new trade from a signal dict. Returns trade ID."""
    now = datetime.now(timezone.utc).isoformat()
    factors = json.dumps(signal.get("factors", []), default=str)
    tags_list = []
    if signal.get("risk_grade") in ("A+", "A"):
        tags_list.append("high-grade")
    if signal.get("confidence", 0) >= 70:
        tags_list.append("high-confidence")
    if signal.get("kill_zone") and signal["kill_zone"] not in ("unknown", "off_hours"):
        tags_list.append(f"kz-{signal['kill_zone']}")

    with _lock:
        with _conn() as c:
            cur = c.execute("""
            INSERT INTO trades (
                symbol, display_name, direction, entry_price, stop_loss, take_profit,
                current_price, confidence, risk_grade, risk_reward, win_probability,
                factors, notes, tags, opened_at, session, timeframe, asset_class,
                ict_bias, wyckoff_phase, status, extra_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                signal.get("symbol", ""),
                signal.get("display_name", ""),
                signal.get("direction", "LONG"),
                signal.get("entry", 0),
                signal.get("stop_loss", 0),
                signal.get("take_profit", 0),
                signal.get("current_price", 0),
                signal.get("confidence", 0),
                signal.get("risk_grade", ""),
                signal.get("dynamic_rr") or signal.get("risk_reward", 0),
                signal.get("win_probability", 0),
                factors,
                notes,
                json.dumps(tags_list),
                now,
                signal.get("kill_zone", ""),
                "15m",
                _classify(signal.get("symbol", "")),
                signal.get("ict_bias", ""),
                signal.get("wyckoff_phase", ""),
                "OPEN",
                json.dumps({
                    "amt_bias": signal.get("amt_bias"),
                    "po3_phase": signal.get("po3_phase"),
                    "confluence_score": signal.get("confluence_score"),
                    "num_factors": signal.get("num_factors"),
                }, default=str),
            ))
            c.commit()
            return cur.lastrowid


def close_trade(trade_id: int, outcome: str, close_price: float = 0,
                notes: str = "") -> dict:
    """Close a trade manually. outcome = 'WIN' or 'LOSS'."""
    now = datetime.now(timezone.utc).isoformat()
    points = 1 if outcome == "WIN" else -1
    with _lock:
        with _conn() as c:
            row = c.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
            if not row:
                return {"error": "Trade not found"}
            entry = row["entry_price"]
            direction = row["direction"]
            if close_price <= 0:
                close_price = row["take_profit"] if outcome == "WIN" else row["stop_loss"]
            if direction == "LONG":
                pnl = close_price - entry
            else:
                pnl = entry - close_price
            c.execute("""
            UPDATE trades SET status='CLOSED', outcome=?, points=?, pnl_pips=?,
                current_price=?, closed_at=?, notes=CASE WHEN ?='' THEN notes ELSE ? END
            WHERE id=?
            """, (outcome, points, round(pnl, 5), close_price, now,
                  notes, notes, trade_id))
            c.commit()
    return get_trade(trade_id)


def update_notes(trade_id: int, notes: str, tags: list = None) -> dict:
    with _lock:
        with _conn() as c:
            if tags is not None:
                c.execute("UPDATE trades SET notes=?, tags=? WHERE id=?",
                          (notes, json.dumps(tags), trade_id))
            else:
                c.execute("UPDATE trades SET notes=? WHERE id=?", (notes, trade_id))
            c.commit()
    return get_trade(trade_id)


def delete_trade(trade_id: int):
    with _lock:
        with _conn() as c:
            c.execute("DELETE FROM trades WHERE id=?", (trade_id,))
            c.commit()
    return {"deleted": trade_id}


def get_trade(trade_id: int) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return _row_to_dict(row) if row else {"error": "Not found"}


def get_all_trades(status: str = None, limit: int = 200) -> list:
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM trades WHERE status=? ORDER BY opened_at DESC LIMIT ?",
                (status, limit)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?",
                (limit,)).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_open_trades() -> list:
    return get_all_trades(status="OPEN")


def get_journal_stats() -> dict:
    """Tradezella-style dashboard stats."""
    with _conn() as c:
        all_rows = c.execute(
            "SELECT * FROM trades WHERE status='CLOSED' ORDER BY closed_at ASC"
        ).fetchall()

    if not all_rows:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "total_points": 0, "equity_curve": [], "current_streak": 0,
            "best_streak": 0, "worst_streak": 0, "profit_factor": 0,
            "avg_winner_pips": 0, "avg_loser_pips": 0,
            "by_session": {}, "by_asset_class": {}, "by_direction": {},
            "daily_pnl": {}, "open_count": 0,
        }

    wins = [r for r in all_rows if r["outcome"] == "WIN"]
    losses = [r for r in all_rows if r["outcome"] == "LOSS"]
    total = len(all_rows)

    # Equity curve (+1/-1 cumulative)
    cumulative = 0
    equity_curve = []
    for r in all_rows:
        cumulative += r["points"]
        equity_curve.append({
            "time": r["closed_at"],
            "value": cumulative,
            "symbol": r["display_name"] or r["symbol"],
            "outcome": r["outcome"],
        })

    # Streaks
    streak = 0
    best_streak = 0
    worst_streak = 0
    current_streak = 0
    for r in all_rows:
        if r["outcome"] == "WIN":
            streak = max(1, streak + 1) if streak >= 0 else 1
        else:
            streak = min(-1, streak - 1) if streak <= 0 else -1
        best_streak = max(best_streak, streak)
        worst_streak = min(worst_streak, streak)
    current_streak = streak

    # Avg pips
    avg_w = sum(r["pnl_pips"] for r in wins) / len(wins) if wins else 0
    avg_l = sum(abs(r["pnl_pips"]) for r in losses) / len(losses) if losses else 0
    pf = (sum(r["pnl_pips"] for r in wins) / sum(abs(r["pnl_pips"]) for r in losses)) if losses and sum(abs(r["pnl_pips"]) for r in losses) > 0 else 0

    # By session / asset / direction
    by_session = _group_stats(all_rows, "session")
    by_asset = _group_stats(all_rows, "asset_class")
    by_dir = _group_stats(all_rows, "direction")

    # Daily P&L
    daily = {}
    for r in all_rows:
        day = (r["closed_at"] or "")[:10]
        if day:
            daily.setdefault(day, {"wins": 0, "losses": 0, "points": 0})
            daily[day]["points"] += r["points"]
            if r["outcome"] == "WIN":
                daily[day]["wins"] += 1
            else:
                daily[day]["losses"] += 1

    open_count = len(get_open_trades())

    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1) if total else 0,
        "total_points": cumulative,
        "equity_curve": equity_curve,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "worst_streak": worst_streak,
        "profit_factor": round(pf, 2),
        "avg_winner_pips": round(avg_w, 5),
        "avg_loser_pips": round(avg_l, 5),
        "by_session": by_session,
        "by_asset_class": by_asset,
        "by_direction": by_dir,
        "daily_pnl": daily,
        "open_count": open_count,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUTO OUTCOME MONITOR — checks open trades against live price
# ══════════════════════════════════════════════════════════════════════════════

_monitor_running = False


def start_monitor(fetch_price_fn):
    """Start background thread that checks open trades every 30s."""
    global _monitor_running
    if _monitor_running:
        return
    _monitor_running = True

    def _loop():
        while _monitor_running:
            try:
                _check_open_trades(fetch_price_fn)
            except Exception as e:
                print(f"[Journal Monitor] Error: {e}")
            _time.sleep(30)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("[Journal] Auto-outcome monitor started (30s interval)")


def _check_open_trades(fetch_price_fn):
    """Check if any open trade has hit TP or SL."""
    open_trades = get_open_trades()
    for trade in open_trades:
        try:
            price = fetch_price_fn(trade["symbol"])
            if price <= 0:
                continue

            # Update current price
            with _lock:
                with _conn() as c:
                    c.execute("UPDATE trades SET current_price=? WHERE id=?",
                              (price, trade["id"]))
                    c.commit()

            entry = trade["entry_price"]
            tp = trade["take_profit"]
            sl = trade["stop_loss"]
            direction = trade["direction"]

            if direction == "LONG":
                if price >= tp:
                    close_trade(trade["id"], "WIN", price)
                    print(f"[Journal] TP HIT: {trade['display_name']} LONG @ {price:.5f}")
                elif price <= sl:
                    close_trade(trade["id"], "LOSS", price)
                    print(f"[Journal] SL HIT: {trade['display_name']} LONG @ {price:.5f}")
            else:
                if price <= tp:
                    close_trade(trade["id"], "WIN", price)
                    print(f"[Journal] TP HIT: {trade['display_name']} SHORT @ {price:.5f}")
                elif price >= sl:
                    close_trade(trade["id"], "LOSS", price)
                    print(f"[Journal] SL HIT: {trade['display_name']} SHORT @ {price:.5f}")
        except Exception as e:
            print(f"[Journal] Monitor err {trade['symbol']}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("factors", "tags"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    if "extra_json" in d and isinstance(d["extra_json"], str):
        try:
            d["extra_data"] = json.loads(d["extra_json"])
        except Exception:
            d["extra_data"] = {}
        del d["extra_json"]
    return d


def _classify(symbol: str) -> str:
    if symbol.endswith("=X"):
        return "forex"
    if symbol.startswith("^"):
        return "indices"
    if symbol.endswith("=F"):
        return "commodities"
    if "-USD" in symbol:
        return "crypto"
    return "other"


def _group_stats(rows, key: str) -> dict:
    groups = {}
    for r in rows:
        g = r[key] or "unknown"
        groups.setdefault(g, {"total": 0, "wins": 0, "losses": 0})
        groups[g]["total"] += 1
        if r["outcome"] == "WIN":
            groups[g]["wins"] += 1
        else:
            groups[g]["losses"] += 1
    for g in groups:
        t = groups[g]["total"]
        groups[g]["win_rate"] = round(groups[g]["wins"] / t * 100, 1) if t else 0
    return groups
