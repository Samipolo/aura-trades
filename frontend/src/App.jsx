import React, { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp, TrendingDown, Activity, BarChart3, RefreshCw,
  Target, Shield, Zap, Clock, AlertTriangle,
  ArrowUpRight, ArrowDownRight, Globe, DollarSign, Layers,
  Brain, Gauge, AlertCircle, Award, Crosshair, Eye, LineChart
} from 'lucide-react'
import axios from 'axios'
import TradingChart from './components/TradingChart'
import MCPPanel from './components/MCPPanel'
import TradeJournal from './components/TradeJournal'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : window.location.port === '3000' ? '/api' : 'http://localhost:8000/api'

function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [selectedTrade, setSelectedTrade] = useState(null)
  const [filter, setFilter] = useState('all')
  const [view, setView] = useState('dashboard')
  const [chartSignal, setChartSignal] = useState(null)

  const openChart = (trade) => {
    setChartSignal(trade)
    setSelectedTrade(trade)
    setView('chart')
  }

  const fetchAnalysis = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`${API_BASE}/analyze`, { timeout: 600000 })
      if (response.data?.success === false) {
        setError(response.data.detail || 'Analysis in progress, retrying...')
        setTimeout(() => fetchAnalysis(), 15000)
        return
      }
      setData(response.data)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch analysis')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAnalysis()
    const interval = setInterval(fetchAnalysis, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchAnalysis])

  const filteredTrades = data?.ranked_trades?.filter(trade => {
    if (filter === 'all') return true
    if (filter === 'long') return trade.direction === 'LONG'
    if (filter === 'short') return trade.direction === 'SHORT'
    if (filter === 'high') return trade.confidence >= 70
    if (filter === 'a_grade') return trade.risk_grade === 'A+' || trade.risk_grade === 'A'
    return true
  }) || []

  if (view === 'journal') {
    return (
      <TradeJournal
        onBack={() => setView('dashboard')}
        signals={data?.ranked_trades || []}
      />
    )
  }

  if (view === 'chart' && data?.ranked_trades?.length) {
    return (
      <TradingChart
        signals={data.ranked_trades}
        selectedSignal={chartSignal}
        onBack={() => setView('dashboard')}
        onSelectSignal={(s) => { setChartSignal(s); setSelectedTrade(s) }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] p-4 md:p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center animate-pulse-glow">
              <Zap size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                AURA TRADES V2
              </h1>
              <p className="text-xs text-gray-400">15-Engine AI System • Bloomberg-Level • Institutional Grade</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdate && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Clock size={12} />
                {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            {data?.ranked_trades?.length > 0 && (
              <button
                onClick={() => openChart(data.ranked_trades[0])}
                className="flex items-center gap-2 px-4 py-2 bg-[#1f2937] hover:bg-[#2a3441] rounded-lg text-sm font-medium text-gray-300 transition-all"
              >
                <LineChart size={14} />
                Charts
              </button>
            )}
            <button
              onClick={() => setView('journal')}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 rounded-lg text-sm font-medium text-white transition-all shadow-lg shadow-amber-600/20"
            >
              <Award size={14} />
              Journal
            </button>
            <button
              onClick={fetchAnalysis}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Analyzing...' : 'Run Full Analysis'}
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
        </div>
      )}

      {/* Market Overview */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
          <OverviewCard icon={<BarChart3 size={14} />} label="Scanned" value={data.total_instruments} color="blue" />
          <OverviewCard icon={<Target size={14} />} label="Signals" value={data.signals_generated} color="indigo" />
          <OverviewCard icon={<TrendingUp size={14} />} label="Bullish" value={data.market_overview?.bullish_instruments || 0} color="green" />
          <OverviewCard icon={<TrendingDown size={14} />} label="Bearish" value={data.market_overview?.bearish_instruments || 0} color="red" />
          <OverviewCard icon={<DollarSign size={14} />} label="USD" value={data.correlation_data?.dxy_bias?.bias?.replace('usd_','')?.replace('_',' ') || '—'} color="yellow" isText />
          <OverviewCard icon={<Globe size={14} />} label="Risk" value={data.market_overview?.risk_sentiment?.replace(/_/g,' ') || '—'} color="purple" isText />
          <OverviewCard icon={<Award size={14} />} label="Strongest" value={data.market_overview?.strongest_currency || '—'} color="green" isText />
          <OverviewCard icon={<AlertCircle size={14} />} label="Weakest" value={data.market_overview?.weakest_currency || '—'} color="red" isText />
        </div>
      )}

      {/* Currency Strength & Correlation Insights */}
      {data?.correlation_data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Currency Strength */}
          {data.correlation_data.currency_strength?.index && (
            <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
              <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                <Gauge size={14} className="text-indigo-400" />
                Currency Strength Index
              </h3>
              <div className="space-y-1.5">
                {Object.entries(data.correlation_data.currency_strength.index).map(([currency, score]) => (
                  <div key={currency} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-8 font-mono">{currency}</span>
                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${score > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, Math.abs(score))}%`, marginLeft: score < 0 ? 'auto' : 0 }}
                      />
                    </div>
                    <span className={`text-xs font-mono w-12 text-right ${score > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {score > 0 ? '+' : ''}{score}
                    </span>
                  </div>
                ))}
              </div>
              {data.correlation_data.currency_strength.best_pair_long && (
                <div className="mt-3 pt-2 border-t border-[#1f2937] text-xs text-gray-500">
                  Best pair: <span className="text-indigo-400 font-medium">{data.correlation_data.currency_strength.best_pair_long}</span> LONG
                </div>
              )}
            </div>
          )}

          {/* Risk Sentiment + Alerts */}
          <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Brain size={14} className="text-purple-400" />
              Inter-Market Intelligence
            </h3>
            {data.correlation_data.risk_sentiment && (
              <div className="mb-3 p-2 bg-[#1f2937] rounded-lg">
                <div className="text-[10px] text-gray-500 uppercase">Risk Sentiment</div>
                <div className={`text-sm font-semibold capitalize ${
                  data.correlation_data.risk_sentiment.sentiment?.includes('on') ? 'text-green-400' :
                  data.correlation_data.risk_sentiment.sentiment?.includes('off') ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {data.correlation_data.risk_sentiment.sentiment?.replace(/_/g, ' ') || 'Neutral'}
                </div>
                <div className="text-[10px] text-gray-500 mt-1">{data.correlation_data.risk_sentiment.implication}</div>
              </div>
            )}
            {data.correlation_data.signals?.length > 0 && (
              <div className="space-y-1">
                <div className="text-[10px] text-gray-500 uppercase mb-1">Divergence Alerts</div>
                {data.correlation_data.signals.slice(0, 3).map((sig, i) => (
                  <div key={i} className="text-xs px-2 py-1 bg-yellow-900/20 border border-yellow-800/30 rounded text-yellow-300">
                    {sig.implication}
                  </div>
                ))}
              </div>
            )}
            {data.correlation_data.lead_lag?.length > 0 && (
              <div className="mt-3 space-y-1">
                <div className="text-[10px] text-gray-500 uppercase mb-1">Lead-Lag Relationships</div>
                {data.correlation_data.lead_lag.slice(0, 3).map((ll, i) => (
                  <div key={i} className="text-xs text-gray-400">
                    {ll.implication}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-xs text-gray-400 mr-2">Filter:</span>
        {['all', 'long', 'short', 'high', 'a_grade'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              filter === f ? 'bg-indigo-600 text-white' : 'bg-[#1f2937] text-gray-400 hover:text-white'
            }`}
          >
            {f === 'high' ? 'High Conf.' : f === 'a_grade' ? 'A+ Grade' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-500">{filteredTrades.length} trades</span>
      </div>

      {/* Trade Signals */}
      {loading && !data ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-3">
            {filteredTrades.length === 0 && !loading ? (
              <div className="text-center py-12 text-gray-500">
                <Target size={48} className="mx-auto mb-3 opacity-30" />
                <p>No trade signals match your criteria</p>
              </div>
            ) : (
              filteredTrades.map((trade, i) => (
                <TradeCard key={`${trade.symbol}-${i}`} trade={trade} onClick={() => setSelectedTrade(trade)} onChart={() => openChart(trade)} isSelected={selectedTrade?.symbol === trade.symbol} />
              ))
            )}
          </div>
          <div className="lg:col-span-1 space-y-3">
            {selectedTrade ? (
              <>
                <TradeDetail trade={selectedTrade} />
                <MCPPanel symbol={selectedTrade.symbol} displayName={selectedTrade.display_name} />
              </>
            ) : (
              <div className="sticky top-6 p-6 bg-[#111827] border border-[#1f2937] rounded-xl text-center">
                <Crosshair size={32} className="mx-auto mb-3 text-gray-600" />
                <p className="text-gray-500 text-sm">Select a trade for deep analysis</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function OverviewCard({ icon, label, value, color, isText }) {
  const colorMap = {
    blue: 'from-blue-500/10 to-blue-600/5 border-blue-800/50',
    indigo: 'from-indigo-500/10 to-indigo-600/5 border-indigo-800/50',
    green: 'from-green-500/10 to-green-600/5 border-green-800/50',
    red: 'from-red-500/10 to-red-600/5 border-red-800/50',
    yellow: 'from-yellow-500/10 to-yellow-600/5 border-yellow-800/50',
    purple: 'from-purple-500/10 to-purple-600/5 border-purple-800/50',
  }
  const textColor = {
    blue: 'text-blue-400', indigo: 'text-indigo-400', green: 'text-green-400',
    red: 'text-red-400', yellow: 'text-yellow-400', purple: 'text-purple-400',
  }
  return (
    <div className={`p-2.5 rounded-xl bg-gradient-to-br ${colorMap[color]} border`}>
      <div className={`flex items-center gap-1 mb-0.5 ${textColor[color]}`}>
        {icon}
        <span className="text-[9px] uppercase tracking-wider text-gray-400">{label}</span>
      </div>
      <div className={`${isText ? 'text-xs capitalize' : 'text-lg'} font-bold ${textColor[color]}`}>{value}</div>
    </div>
  )
}

function TradeCard({ trade, onClick, onChart, isSelected }) {
  const isLong = trade.direction === 'LONG'
  const gradeColors = { 'A+': 'text-green-400 bg-green-900/40', 'A': 'text-green-400 bg-green-900/30', 'B': 'text-blue-400 bg-blue-900/30', 'C': 'text-yellow-400 bg-yellow-900/30', 'D': 'text-orange-400 bg-orange-900/30', 'F': 'text-red-400 bg-red-900/30' }
  const gradeClass = gradeColors[trade.risk_grade] || 'text-gray-400 bg-gray-800'

  return (
    <div onClick={onClick} className={`p-4 rounded-xl border cursor-pointer transition-all animate-slide-up ${isSelected ? 'bg-[#111827] border-indigo-500 shadow-lg shadow-indigo-500/10' : 'bg-[#111827] border-[#1f2937] hover:border-gray-600'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${trade.rank <= 3 ? 'bg-gradient-to-br from-yellow-500 to-orange-500 text-black' : trade.rank <= 10 ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
            #{trade.rank}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">{trade.display_name}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isLong ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                {trade.direction}
              </span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${gradeClass}`}>
                {trade.risk_grade}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-[10px] text-gray-500">{trade.wyckoff_phase?.replace(/_/g,' ')}</span>
              <span className="text-[10px] text-gray-600">•</span>
              <span className="text-[10px] text-gray-500">{trade.mtf_quality?.replace(/_/g,' ')}</span>
              {trade.kill_zone && trade.kill_zone !== 'unknown' && trade.kill_zone !== 'off_hours' && (
                <><span className="text-[10px] text-gray-600">•</span><span className="text-[10px] text-amber-400">{trade.kill_zone?.replace(/_/g,' ')}</span></>
              )}
              {trade.po3_phase && trade.po3_phase !== 'unknown' && (
                <><span className="text-[10px] text-gray-600">•</span><span className="text-[10px] text-cyan-400">PO3: {trade.po3_phase}</span></>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${trade.confidence >= 70 ? 'text-green-400' : trade.confidence >= 50 ? 'text-yellow-400' : 'text-gray-400'}`}>
            {trade.confidence.toFixed(0)}%
          </div>
          <div className="text-[10px] text-gray-500">Win: {trade.win_probability || '—'}%</div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-5 gap-2 text-xs">
        <div className="text-center"><div className="text-gray-500">Entry</div><div className="font-mono text-gray-300">{formatPrice(trade.entry)}</div></div>
        <div className="text-center"><div className="text-gray-500">SL</div><div className="font-mono text-red-400">{formatPrice(trade.stop_loss)}</div></div>
        <div className="text-center"><div className="text-gray-500">TP</div><div className="font-mono text-green-400">{formatPrice(trade.take_profit)}</div></div>
        <div className="text-center"><div className="text-gray-500">R:R</div><div className="font-mono text-indigo-400">1:{trade.dynamic_rr || trade.risk_reward}</div></div>
        <div className="text-center"><div className="text-gray-500">Factors</div><div className="font-mono text-purple-400">{trade.num_factors || trade.factors?.length}</div></div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1">
        {trade.factors?.slice(0, 6).map((f, i) => (
          <span key={i} className="px-2 py-0.5 bg-[#1f2937] rounded text-[10px] text-gray-400">{f.name.replace(/_/g, ' ')}</span>
        ))}
        {(trade.factors?.length || 0) > 6 && <span className="px-2 py-0.5 bg-[#1f2937] rounded text-[10px] text-gray-500">+{trade.factors.length - 6}</span>}
      </div>

      <div className="mt-2 flex items-center justify-between">
        {trade.warnings?.length > 0 ? (
          <div className="flex items-center gap-1 text-[10px] text-orange-400">
            <AlertTriangle size={10} /> {trade.warnings[0]}
          </div>
        ) : <div />}
        <button onClick={async (e) => {
          e.stopPropagation();
          if (!confirm(`Place ${trade.direction} 1.0 lot on ${trade.display_name} via MT5?`)) return;
          try {
            const res = await fetch(`${API_BASE}/mt5/trade`, {
              method: 'POST', headers: {'Content-Type':'application/json'},
              body: JSON.stringify({ symbol: trade.symbol, direction: trade.direction, lot_size: 1.0, sl: trade.stop_loss || 0, tp: trade.take_profit || 0 })
            });
            const d = await res.json();
            if (res.ok && d.success) alert(`✅ MT5 Trade Placed!\nTicket: ${d.deal_ticket}\nPrice: ${d.price}`);
            else alert(`❌ MT5 Error: ${d.detail || d.error}`);
          } catch { alert('❌ Could not reach MT5 backend'); }
        }} className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold transition-all ${trade.direction === 'LONG' ? 'bg-green-700 hover:bg-green-600 text-white' : 'bg-red-700 hover:bg-red-600 text-white'}`}>
          <Zap size={10} /> TAKE ON MT5
        </button>
        <button onClick={(e) => { e.stopPropagation(); onChart?.() }}
          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-gray-400 hover:text-white bg-[#1f2937] hover:bg-indigo-600 transition-all">
          <Eye size={10} /> View Chart
        </button>
      </div>
    </div>
  )
}

function TradeDetail({ trade }) {
  const isLong = trade.direction === 'LONG'
  return (
    <div className="sticky top-6 space-y-3 max-h-[90vh] overflow-y-auto pr-1">
      {/* Header */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-bold text-white">{trade.display_name}</h2>
            <p className="text-[10px] text-gray-500">{trade.symbol} • Hurst: {trade.hurst?.toFixed(3) || '—'}</p>
          </div>
          <div className={`px-3 py-1 rounded-lg text-sm font-bold flex items-center gap-1 ${isLong ? 'bg-green-900/50 text-green-400 border border-green-700/50' : 'bg-red-900/50 text-red-400 border border-red-700/50'}`}>
            {isLong ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {trade.direction}
          </div>
        </div>
        <div className="space-y-1.5">
          <LevelRow label="Current" value={trade.current_price} color="white" />
          <LevelRow label="Entry" value={trade.entry} color="indigo" />
          <LevelRow label="Stop Loss" value={trade.stop_loss} color="red" />
          <LevelRow label="Take Profit" value={trade.take_profit} color="green" />
        </div>
      </div>

      {/* Risk Engine */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <Shield size={12} className="text-indigo-400" /> Risk Engine
        </h3>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div><div className="text-gray-500">Grade</div><div className={`text-lg font-bold ${trade.risk_grade === 'A+' || trade.risk_grade === 'A' ? 'text-green-400' : 'text-yellow-400'}`}>{trade.risk_grade}</div></div>
          <div><div className="text-gray-500">Win %</div><div className="text-lg font-bold text-blue-400">{trade.win_probability || '—'}%</div></div>
          <div><div className="text-gray-500">Quality</div><div className="text-lg font-bold text-purple-400">{trade.trade_quality || '—'}</div></div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs mt-2">
          <div><div className="text-gray-500">R:R</div><div className="font-mono text-indigo-400">1:{trade.dynamic_rr || trade.risk_reward}</div></div>
          <div><div className="text-gray-500">Size %</div><div className="font-mono text-gray-300">{trade.position_size_pct || '1.0'}%</div></div>
          <div><div className="text-gray-500">Kelly</div><div className="font-mono text-gray-300">{trade.kelly_fraction || '—'}</div></div>
        </div>
      </div>

      {/* Multi-Engine Analysis */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <Brain size={12} className="text-purple-400" /> 15-Engine Analysis
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<TrendingUp size={11} />} label="Trend (EMA)" value={trade.trend} />
          <AnalysisRow icon={<Activity size={11} />} label="Momentum" value={trade.momentum} />
          <AnalysisRow icon={<Layers size={11} />} label="Structure" value={trade.market_structure} />
          <AnalysisRow icon={<BarChart3 size={11} />} label="Volatility" value={trade.volatility} />
          <AnalysisRow icon={<Globe size={11} />} label="Correlation" value={`${trade.correlation_score}%`} />
          <AnalysisRow icon={<Gauge size={11} />} label="Quant Regime" value={trade.quant_regime} />
          <AnalysisRow icon={<Target size={11} />} label="Wyckoff" value={trade.wyckoff_phase} />
          <AnalysisRow icon={<Crosshair size={11} />} label="MTF Align" value={trade.mtf_quality} />
        </div>
      </div>

      {/* ICT Concepts */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <Crosshair size={12} className="text-cyan-400" /> ICT / Smart Money
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<Target size={11} />} label="ICT Bias" value={trade.ict_bias} />
          <AnalysisRow icon={<Zap size={11} />} label="ICT Score" value={trade.ict_score ? `${trade.ict_score}%` : '—'} />
          <AnalysisRow icon={<Clock size={11} />} label="Kill Zone" value={trade.kill_zone} />
          <AnalysisRow icon={<Layers size={11} />} label="Power of 3" value={trade.po3_phase} />
        </div>
      </div>

      {/* Auction Market Theory */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <BarChart3 size={12} className="text-amber-400" /> Auction Market Theory
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<Target size={11} />} label="AMT Bias" value={trade.amt_bias} />
          <AnalysisRow icon={<Gauge size={11} />} label="AMT Score" value={trade.amt_score ? `${trade.amt_score}%` : '—'} />
          <AnalysisRow icon={<Activity size={11} />} label="Day Type" value={trade.day_type} />
          <AnalysisRow icon={<Layers size={11} />} label="Value Area" value={trade.value_area} />
        </div>
      </div>

      {/* Session Analysis */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <Clock size={12} className="text-emerald-400" /> Session Analysis
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<Globe size={11} />} label="Active Session" value={trade.current_session} />
          <AnalysisRow icon={<Target size={11} />} label="London IB" value={trade.london_ib_status} />
          <AnalysisRow icon={<Zap size={11} />} label="Asian Breakout" value={trade.asian_breakout} />
          <AnalysisRow icon={<TrendingUp size={11} />} label="Session Bias" value={trade.session_bias} />
        </div>
      </div>

      {/* Institutional & Fundamental */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <DollarSign size={12} className="text-rose-400" /> Institutional & Macro
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<Target size={11} />} label="Smart Money" value={trade.smart_money} />
          <AnalysisRow icon={<Layers size={11} />} label="Inst. Phase" value={trade.inst_phase} />
          <AnalysisRow icon={<Activity size={11} />} label="Fundamental" value={trade.fundamental_bias} />
          <AnalysisRow icon={<AlertCircle size={11} />} label="Event Risk" value={trade.event_risk} />
          <AnalysisRow icon={<Globe size={11} />} label="News" value={trade.news_sentiment} />
          <AnalysisRow icon={<TrendingUp size={11} />} label="Macro Bias" value={trade.macro_bias} />
          <AnalysisRow icon={<Gauge size={11} />} label="Risk Sent." value={trade.risk_sentiment} />
        </div>
      </div>

      {/* Regime */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
          <BarChart3 size={12} className="text-sky-400" /> Market Regime
        </h3>
        <div className="space-y-1.5">
          <AnalysisRow icon={<Activity size={11} />} label="Regime" value={trade.regime} />
          <AnalysisRow icon={<Gauge size={11} />} label="Quality" value={trade.regime_quality} />
          <AnalysisRow icon={<Target size={11} />} label="Strategy" value={trade.optimal_strategy} />
        </div>
      </div>

      {/* Confluence Factors */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <h3 className="text-xs font-semibold text-gray-300 mb-2">
          Confluence ({trade.factors?.length || 0} factors)
        </h3>
        <div className="space-y-1.5">
          {trade.factors?.slice(0, 12).map((f, i) => (
            <div key={i} className="flex items-center justify-between">
              <span className="text-[10px] text-gray-400 capitalize">{f.name.replace(/_/g, ' ')}</span>
              <div className="flex items-center gap-1.5">
                <div className="w-12 h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, f.score * 4)}%` }} />
                </div>
                <span className="text-[10px] text-gray-500 w-5 text-right">{f.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warnings */}
      {trade.warnings?.length > 0 && (
        <div className="p-4 bg-orange-900/20 border border-orange-800/40 rounded-xl">
          <h3 className="text-xs font-semibold text-orange-300 mb-2 flex items-center gap-1.5">
            <AlertTriangle size={12} /> Warnings
          </h3>
          {trade.warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-orange-200 mb-1">• {w}</p>
          ))}
        </div>
      )}

      {/* MT5 ONE-CLICK TRADE */}
      <div className="p-4 bg-[#111827] border border-[#1f2937] rounded-xl">
        <button
          onClick={async () => {
            if (!confirm(`Place ${trade.direction} 1.0 lot on ${trade.display_name} via MT5?\n\nEntry: ${formatPrice(trade.entry)}\nSL: ${formatPrice(trade.stop_loss)}\nTP: ${formatPrice(trade.take_profit)}`)) return;
            try {
              const res = await fetch(`${API_BASE}/mt5/trade`, {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ symbol: trade.symbol, direction: trade.direction, lot_size: 1.0, sl: trade.stop_loss || 0, tp: trade.take_profit || 0 })
              });
              const d = await res.json();
              if (res.ok && d.success) alert(`✅ MT5 Trade Placed!\n\nSymbol: ${d.symbol}\nTicket: ${d.deal_ticket}\nPrice: ${d.price}\nVolume: ${d.volume} lots`);
              else alert(`❌ MT5 Error: ${d.detail || d.error}`);
            } catch { alert('❌ Could not reach MT5 backend'); }
          }}
          className={`w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider transition-all flex justify-center items-center gap-2 ${
            isLong
              ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white shadow-lg shadow-green-600/30'
              : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white shadow-lg shadow-red-600/30'
          }`}
        >
          <Zap size={16} />
          TAKE ON MT5 (1 LOT)
        </button>
        <p className="text-center text-[9px] text-gray-600 mt-2">Places a live trade on MetaTrader 5 with SL/TP</p>
      </div>

      <div className="text-center text-[9px] text-gray-600 pb-4">
        {new Date(trade.timestamp).toLocaleString()}
      </div>
    </div>
  )
}

function LevelRow({ label, value, color }) {
  const colors = { white: 'text-white', indigo: 'text-indigo-400', red: 'text-red-400', green: 'text-green-400', gray: 'text-gray-400' }
  return (
    <div className="flex justify-between items-center py-0.5">
      <span className="text-[10px] text-gray-500">{label}</span>
      <span className={`font-mono text-xs font-medium ${colors[color]}`}>{formatPrice(value)}</span>
    </div>
  )
}

function AnalysisRow({ icon, label, value }) {
  const getColor = (val) => {
    if (!val) return 'text-gray-500'
    const v = String(val).toLowerCase()
    if (v.includes('bullish') || v.includes('uptrend') || v.includes('accumulation') || v.includes('markup') || v.includes('perfect') || v.includes('strong_align')) return 'text-green-400'
    if (v.includes('bearish') || v.includes('downtrend') || v.includes('distribution') || v.includes('markdown')) return 'text-red-400'
    if (v.includes('overbought') || v.includes('high') || v.includes('elevated')) return 'text-yellow-400'
    if (v.includes('oversold') || v.includes('compressed')) return 'text-blue-400'
    return 'text-gray-400'
  }
  return (
    <div className="flex justify-between items-center">
      <span className="text-[10px] text-gray-500 flex items-center gap-1">{icon} {label}</span>
      <span className={`text-[10px] font-medium capitalize ${getColor(value)}`}>{String(value || '—').replace(/_/g, ' ')}</span>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-16 h-16 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
      <h3 className="text-lg font-semibold text-gray-300 mb-1">15-Engine Institutional Analysis</h3>
      <p className="text-sm text-gray-500">Running Bloomberg-level analysis with session, fundamental, macro & institutional flow...</p>
      <div className="mt-4 grid grid-cols-3 gap-x-4 gap-y-1 text-xs text-gray-600">
        <p>✦ Technical Indicators</p>
        <p>✦ Market Structure</p>
        <p>✦ Order Flow Analysis</p>
        <p>✦ Quantitative Models</p>
        <p>✦ Multi-Timeframe (1H/4H)</p>
        <p>✦ Pattern Recognition</p>
        <p>✦ Correlation Engine</p>
        <p>✦ Risk Management</p>
        <p>✦ ICT / Smart Money</p>
        <p>✦ Auction Market Theory</p>
        <p>✦ Session Analysis (IB/ORB)</p>
        <p>✦ Fundamentals & News</p>
        <p>✦ Institutional Flow</p>
        <p>✦ Market Regime</p>
        <p>✦ Macro Intermarket</p>
      </div>
    </div>
  )
}

function formatPrice(price) {
  if (!price && price !== 0) return '—'
  if (price > 1000) return price.toFixed(2)
  if (price > 10) return price.toFixed(4)
  return price.toFixed(5)
}

export default App
