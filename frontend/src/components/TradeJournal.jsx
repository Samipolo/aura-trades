import React, { useState, useEffect, useRef, useCallback } from 'react'
import { createChart, ColorType, LineStyle, LineSeries, AreaSeries } from 'lightweight-charts'
import {
  BookOpen, TrendingUp, TrendingDown, Trophy, Target, XCircle,
  Zap, Clock, BarChart3, Flame, ArrowUpRight, ArrowDownRight,
  RefreshCw, Trash2, Edit3, CheckCircle, X, ArrowLeft, Calendar,
  Activity, Award, Shield, AlertTriangle, Plus
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : window.location.port === '3000' ? '/api' : 'http://localhost:8000/api'

export default function TradeJournal({ onBack, signals }) {
  const [stats, setStats] = useState(null)
  const [trades, setTrades] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [taking, setTaking] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [sRes, tRes] = await Promise.all([
        fetch(`${API}/journal/stats`), fetch(`${API}/journal/trades`)
      ])
      const s = await sRes.json()
      const t = await tRes.json()
      setStats(s)
      setTrades(t.trades || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const takeTrade = async (signal) => {
    setTaking(signal.symbol)
    try {
      await fetch(`${API}/journal/open`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signal)
      })
      await refresh()
    } catch (e) { console.error(e) }
    setTaking(null)
  }

  const closeTrade = async (id, outcome) => {
    try {
      await fetch(`${API}/journal/close/${id}?outcome=${outcome}`, { method: 'POST' })
      await refresh()
    } catch (e) { console.error(e) }
  }

  const deleteTrade = async (id) => {
    try {
      await fetch(`${API}/journal/trade/${id}`, { method: 'DELETE' })
      await refresh()
    } catch (e) { console.error(e) }
  }

  const filtered = trades.filter(t => {
    if (filter === 'all') return true
    if (filter === 'open') return t.status === 'OPEN'
    if (filter === 'wins') return t.outcome === 'WIN'
    if (filter === 'losses') return t.outcome === 'LOSS'
    return true
  })

  return (
    <div className="min-h-screen bg-[#0a0e1a] p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={onBack}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-[#1f2937] transition-all">
            <ArrowLeft size={14} /> Dashboard
          </button>
          <div className="h-6 w-px bg-[#2a2e39]" />
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-600 rounded-lg flex items-center justify-center">
              <BookOpen size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
                Trade Journal
              </h1>
              <p className="text-[10px] text-gray-500">Tradezella-Style Performance Tracker</p>
            </div>
          </div>
        </div>
        <button onClick={refresh} disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#1f2937] hover:bg-[#2a3441] rounded-lg text-xs text-gray-300">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
          <StatCard icon={<BarChart3 size={13}/>} label="Total" value={stats.total_trades} color="blue"/>
          <StatCard icon={<Trophy size={13}/>} label="Wins" value={stats.wins} color="green"/>
          <StatCard icon={<XCircle size={13}/>} label="Losses" value={stats.losses} color="red"/>
          <StatCard icon={<Target size={13}/>} label="Win Rate" value={`${stats.win_rate}%`} color="indigo"/>
          <StatCard icon={<Zap size={13}/>} label="Points" value={stats.total_points} color={stats.total_points>=0?'green':'red'}/>
          <StatCard icon={<Flame size={13}/>} label="Streak" value={stats.current_streak} color={stats.current_streak>=0?'green':'red'}/>
          <StatCard icon={<Award size={13}/>} label="Best Run" value={`+${stats.best_streak}`} color="green"/>
          <StatCard icon={<Activity size={13}/>} label="P. Factor" value={stats.profit_factor} color="purple"/>
        </div>
      )}

      {/* Equity Curve */}
      {stats?.equity_curve?.length > 0 && (
        <div className="mb-6 bg-[#111827] border border-[#1f2937] rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp size={14} className="text-amber-400" />
            Performance Curve (+1 TP / -1 SL)
          </h3>
          <EquityChart data={stats.equity_curve} />
        </div>
      )}

      {/* Two columns: Active Signals + Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Take Trade Panel */}
        <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <Plus size={14} className="text-green-400" /> Take Trade from Signals
          </h3>
          <div className="space-y-1.5 max-h-[250px] overflow-y-auto pr-1">
            {signals?.slice(0, 10).map((s, i) => {
              const alreadyOpen = trades.some(t => t.symbol === s.symbol && t.status === 'OPEN')
              return (
                <div key={i} className="flex items-center gap-2 p-2 bg-[#1a1e2e] rounded-lg">
                  <span className={`w-1.5 h-1.5 rounded-full ${s.direction === 'LONG' ? 'bg-green-400' : 'bg-red-400'}`} />
                  <span className="text-[10px] text-gray-300 flex-1">{s.display_name}</span>
                  <span className={`text-[9px] ${s.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>{s.direction}</span>
                  <span className="text-[9px] text-gray-500">{s.confidence?.toFixed(0)}%</span>
                  {alreadyOpen ? (
                    <span className="text-[9px] text-yellow-400 px-2">OPEN</span>
                  ) : (
                    <button onClick={() => takeTrade(s)} disabled={taking === s.symbol}
                      className="px-2 py-0.5 bg-green-600 hover:bg-green-700 rounded text-[9px] text-white font-medium disabled:opacity-50">
                      {taking === s.symbol ? '...' : 'TAKE'}
                    </button>
                  )}
                </div>
              )
            })}
            {(!signals || signals.length === 0) && (
              <p className="text-[10px] text-gray-600 text-center py-4">Run analysis first to see signals</p>
            )}
          </div>
        </div>

        {/* Breakdown by Direction */}
        {stats?.by_direction && Object.keys(stats.by_direction).length > 0 && (
          <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Shield size={14} className="text-indigo-400" /> By Direction
            </h3>
            {Object.entries(stats.by_direction).map(([dir, s]) => (
              <div key={dir} className="flex items-center justify-between py-1.5 border-b border-[#1f2937] last:border-0">
                <span className={`text-xs font-medium ${dir === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>{dir}</span>
                <div className="flex gap-3 text-[10px]">
                  <span className="text-gray-400">{s.total} trades</span>
                  <span className="text-green-400">{s.wins}W</span>
                  <span className="text-red-400">{s.losses}L</span>
                  <span className="text-indigo-400">{s.win_rate}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Breakdown by Asset */}
        {stats?.by_asset_class && Object.keys(stats.by_asset_class).length > 0 && (
          <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <BarChart3 size={14} className="text-purple-400" /> By Asset Class
            </h3>
            {Object.entries(stats.by_asset_class).map(([cls, s]) => (
              <div key={cls} className="flex items-center justify-between py-1.5 border-b border-[#1f2937] last:border-0">
                <span className="text-xs text-gray-300 capitalize">{cls}</span>
                <div className="flex gap-3 text-[10px]">
                  <span className="text-gray-400">{s.total}</span>
                  <span className="text-green-400">{s.wins}W</span>
                  <span className="text-red-400">{s.losses}L</span>
                  <span className="text-indigo-400">{s.win_rate}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Trade List Filter */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-xs text-gray-400 mr-2">Filter:</span>
        {['all', 'open', 'wins', 'losses'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              filter === f ? 'bg-amber-600 text-white' : 'bg-[#1f2937] text-gray-400 hover:text-white'
            }`}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-500">{filtered.length} trades</span>
      </div>

      {/* Trade Cards */}
      <div className="space-y-3">
        {filtered.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500">
            <BookOpen size={48} className="mx-auto mb-3 opacity-30" />
            <p>No trades yet. Click "TAKE" on a signal to start tracking!</p>
          </div>
        )}
        {filtered.map(trade => (
          <TradeCard key={trade.id} trade={trade}
            onClose={closeTrade} onDelete={deleteTrade} />
        ))}
      </div>

      {/* Open Trade Count Badge */}
      {stats?.open_count > 0 && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2 bg-amber-600 rounded-full text-sm font-bold text-white shadow-lg shadow-amber-600/30 animate-pulse">
          {stats.open_count} Open Trade{stats.open_count > 1 ? 's' : ''} — Monitoring TP/SL
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* EQUITY CHART — lightweight-charts area series                             */
/* ═══════════════════════════════════════════════════════════════════════════ */

function EquityChart({ data }) {
  const ref = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!ref.current || !data?.length) return
    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 220,
      layout: { background: { type: ColorType.Solid, color: '#111827' }, textColor: '#787b86', fontSize: 11 },
      grid: { vertLines: { color: '#1a1e2e' }, horzLines: { color: '#1a1e2e' } },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39', timeVisible: true },
      crosshair: {
        vertLine: { color: '#555', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#2a2e39' },
        horzLine: { color: '#555', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#2a2e39' },
      },
    })
    chartRef.current = chart

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#f59e0b',
      topColor: 'rgba(245,158,11,0.3)',
      bottomColor: 'rgba(245,158,11,0.02)',
      lineWidth: 2,
    })

    // Build time-indexed data
    const points = data.map((d, i) => {
      let t
      if (d.time) {
        const dt = new Date(d.time)
        t = Math.floor(dt.getTime() / 1000)
      } else {
        t = Math.floor(Date.now() / 1000) - (data.length - i) * 3600
      }
      return { time: t, value: d.value }
    })

    // Deduplicate times
    const seen = new Set()
    const unique = []
    for (const p of points) {
      if (!seen.has(p.time)) { seen.add(p.time); unique.push(p) }
      else { unique.push({ ...p, time: p.time + unique.length }) }
    }
    unique.sort((a, b) => a.time - b.time)

    series.setData(unique)

    // Zero line
    series.createPriceLine({
      price: 0, color: '#787b86', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
    })

    chart.timeScale().fitContent()

    const onResize = () => {
      if (chartRef.current && ref.current)
        chartRef.current.applyOptions({ width: ref.current.clientWidth })
    }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [data])

  return <div ref={ref} className="w-full" />
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* TRADE CARD — Tradezella-style                                             */
/* ═══════════════════════════════════════════════════════════════════════════ */

function TradeCard({ trade, onClose, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = trade.direction === 'LONG'
  const isOpen = trade.status === 'OPEN'
  const isWin = trade.outcome === 'WIN'

  const statusColor = isOpen
    ? 'border-amber-600/40 bg-amber-900/10'
    : isWin ? 'border-green-700/40 bg-green-900/10' : 'border-red-700/40 bg-red-900/10'

  const gradeColors = { 'A+': 'text-green-400', 'A': 'text-green-400', 'B': 'text-blue-400', 'C': 'text-yellow-400' }

  return (
    <div className={`rounded-xl border ${statusColor} transition-all`}>
      {/* Main Row */}
      <div className="flex items-center gap-3 p-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {/* Status Icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          isOpen ? 'bg-amber-600/20' : isWin ? 'bg-green-600/20' : 'bg-red-600/20'
        }`}>
          {isOpen ? <Clock size={16} className="text-amber-400" />
            : isWin ? <CheckCircle size={16} className="text-green-400" />
            : <XCircle size={16} className="text-red-400" />}
        </div>

        {/* Symbol + Direction */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-white">{trade.display_name || trade.symbol}</span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
              isLong ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
            }`}>{trade.direction}</span>
            {trade.risk_grade && (
              <span className={`text-[9px] font-bold ${gradeColors[trade.risk_grade] || 'text-gray-500'}`}>
                {trade.risk_grade}
              </span>
            )}
            {isOpen && <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-900/40 text-amber-400 animate-pulse">LIVE</span>}
          </div>
          <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
            <span>{new Date(trade.opened_at).toLocaleDateString()}</span>
            <span>{new Date(trade.opened_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</span>
            {trade.session && trade.session !== 'unknown' && trade.session !== 'off_hours' && (
              <span className="text-amber-400">{trade.session}</span>
            )}
          </div>
        </div>

        {/* Outcome / Points */}
        <div className="text-right">
          {isOpen ? (
            <div className="text-xs text-amber-400 font-medium">Monitoring...</div>
          ) : (
            <div className={`text-lg font-bold ${isWin ? 'text-green-400' : 'text-red-400'}`}>
              {isWin ? '+1' : '-1'}
            </div>
          )}
          <div className="text-[10px] text-gray-500">
            {trade.confidence?.toFixed(0)}% conf
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-[#1f2937]">
          <div className="grid grid-cols-4 gap-3 mt-3 text-xs text-center">
            <div><div className="text-gray-500">Entry</div><div className="font-mono text-blue-400">{fmtPrice(trade.entry_price)}</div></div>
            <div><div className="text-gray-500">SL</div><div className="font-mono text-red-400">{fmtPrice(trade.stop_loss)}</div></div>
            <div><div className="text-gray-500">TP</div><div className="font-mono text-green-400">{fmtPrice(trade.take_profit)}</div></div>
            <div><div className="text-gray-500">R:R</div><div className="font-mono text-indigo-400">1:{trade.risk_reward?.toFixed?.(1) || '—'}</div></div>
          </div>

          {isOpen && trade.current_price > 0 && (
            <div className="mt-2 p-2 bg-[#1a1e2e] rounded-lg text-center">
              <div className="text-[10px] text-gray-500">Current Price</div>
              <div className="text-sm font-mono text-white">{fmtPrice(trade.current_price)}</div>
            </div>
          )}

          <div className="grid grid-cols-3 gap-2 mt-2 text-[10px]">
            <div><span className="text-gray-500">Win Prob: </span><span className="text-gray-300">{trade.win_probability?.toFixed(0)}%</span></div>
            <div><span className="text-gray-500">ICT: </span><span className="text-gray-300 capitalize">{trade.ict_bias || '—'}</span></div>
            <div><span className="text-gray-500">Wyckoff: </span><span className="text-gray-300 capitalize">{(trade.wyckoff_phase || '—').replace(/_/g,' ')}</span></div>
          </div>

          {/* Tags */}
          {trade.tags?.length > 0 && (
            <div className="flex gap-1 mt-2 flex-wrap">
              {trade.tags.map((t, i) => (
                <span key={i} className="px-2 py-0.5 bg-[#1f2937] rounded text-[9px] text-gray-400">{t}</span>
              ))}
            </div>
          )}

          {/* Notes */}
          {trade.notes && (
            <div className="mt-2 p-2 bg-[#1a1e2e] rounded text-[10px] text-gray-400 italic">
              {trade.notes}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 mt-3">
            {isOpen && (
              <>
                <button onClick={() => onClose(trade.id, 'WIN')}
                  className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-[10px] text-white font-medium">
                  <CheckCircle size={11} /> Close WIN
                </button>
                <button onClick={() => onClose(trade.id, 'LOSS')}
                  className="flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded-lg text-[10px] text-white font-medium">
                  <XCircle size={11} /> Close LOSS
                </button>
              </>
            )}
            <button onClick={() => onDelete(trade.id)}
              className="flex items-center gap-1 px-2 py-1.5 bg-[#1f2937] hover:bg-red-900/30 rounded-lg text-[10px] text-gray-400 hover:text-red-400 ml-auto">
              <Trash2 size={11} /> Delete
            </button>
          </div>

          {trade.closed_at && (
            <div className="text-[9px] text-gray-600 mt-2 text-right">
              Closed: {new Date(trade.closed_at).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* STAT CARD                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

function StatCard({ icon, label, value, color }) {
  const colorMap = {
    blue: 'from-blue-500/10 to-blue-600/5 border-blue-800/50',
    indigo: 'from-indigo-500/10 to-indigo-600/5 border-indigo-800/50',
    green: 'from-green-500/10 to-green-600/5 border-green-800/50',
    red: 'from-red-500/10 to-red-600/5 border-red-800/50',
    purple: 'from-purple-500/10 to-purple-600/5 border-purple-800/50',
    amber: 'from-amber-500/10 to-amber-600/5 border-amber-800/50',
  }
  const textColor = {
    blue: 'text-blue-400', indigo: 'text-indigo-400', green: 'text-green-400',
    red: 'text-red-400', purple: 'text-purple-400', amber: 'text-amber-400',
  }
  return (
    <div className={`p-2.5 rounded-xl bg-gradient-to-br ${colorMap[color] || colorMap.blue} border`}>
      <div className={`flex items-center gap-1 mb-0.5 ${textColor[color] || textColor.blue}`}>
        {icon}
        <span className="text-[9px] uppercase tracking-wider text-gray-400">{label}</span>
      </div>
      <div className={`text-lg font-bold ${textColor[color] || textColor.blue}`}>{value}</div>
    </div>
  )
}

function fmtPrice(p) {
  if (!p && p !== 0) return '—'
  if (p > 1000) return p.toFixed(2)
  if (p > 10) return p.toFixed(4)
  return p.toFixed(5)
}
