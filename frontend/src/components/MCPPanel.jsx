import React, { useState, useEffect } from 'react'
import { Zap, TrendingUp, TrendingDown, BarChart3, Globe, Newspaper, Brain, Activity, RefreshCw, ChevronDown, ChevronUp, AlertTriangle, Database, CheckCircle, XCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : window.location.port === '3000' ? '/api' : 'http://localhost:8000/api'

const STRATEGIES = ['supertrend','rsi','bollinger','macd','ema_cross','donchian']

export default function MCPPanel({ symbol, displayName }) {
  const [tab, setTab] = useState('combined')
  const [data, setData] = useState({})
  const [loading, setLoading] = useState({})
  const [btStrategy, setBtStrategy] = useState('supertrend')
  const [btPeriod, setBtPeriod] = useState('1y')
  const [available, setAvailable] = useState(true)

  useEffect(() => {
    fetch(`${API}/mcp/status`).then(r=>r.json()).then(d=> setAvailable(d.available)).catch(()=>setAvailable(false))
  }, [])

  const load = async (endpoint, key, extra='') => {
    setLoading(p=>({...p,[key]:true}))
    try {
      const r = await fetch(`${API}/mcp/${endpoint}/${encodeURIComponent(symbol)}${extra}`)
      const d = await r.json()
      setData(p=>({...p,[key]:d}))
    } catch(e) { setData(p=>({...p,[key]:{error:e.message}})) }
    setLoading(p=>({...p,[key]:false}))
  }

  const loadSnapshot = async () => {
    setLoading(p=>({...p,snapshot:true}))
    try {
      const r = await fetch(`${API}/mcp/snapshot`)
      const d = await r.json()
      setData(p=>({...p,snapshot:d}))
    } catch(e) { setData(p=>({...p,snapshot:{error:e.message}})) }
    setLoading(p=>({...p,snapshot:false}))
  }

  const loadNews = async () => {
    setLoading(p=>({...p,news:true}))
    try {
      const clean = symbol.replace('=X','').replace('^','').replace('-USD','').replace('=F','')
      const r = await fetch(`${API}/mcp/news?symbol=${clean}`)
      const d = await r.json()
      setData(p=>({...p,news:d}))
    } catch(e) { setData(p=>({...p,news:{error:e.message}})) }
    setLoading(p=>({...p,news:false}))
  }

  const loadSources = async () => {
    setLoading(p=>({...p,sources:true}))
    try {
      const r = await fetch(`${API}/data-sources`)
      const d = await r.json()
      setData(p=>({...p,sources:d}))
    } catch(e) { setData(p=>({...p,sources:{error:e.message}})) }
    setLoading(p=>({...p,sources:false}))
  }

  const loadConsensus = async () => {
    setLoading(p=>({...p,consensus:true}))
    try {
      const r = await fetch(`${API}/consensus-price/${encodeURIComponent(symbol)}`)
      const d = await r.json()
      setData(p=>({...p,consensus:d}))
    } catch(e) { setData(p=>({...p,consensus:{error:e.message}})) }
    setLoading(p=>({...p,consensus:false}))
  }

  useEffect(() => {
    if (!available) return
    if (tab === 'sources') { loadSources(); return }
    if (!symbol) return
    setData({})
    if (tab === 'combined') load('analysis','combined','?timeframe=15m')
    else if (tab === 'backtest') load('backtest','backtest',`?strategy=${btStrategy}&period=${btPeriod}`)
    else if (tab === 'compare') load('compare','compare',`?period=${btPeriod}`)
    else if (tab === 'sentiment') load('sentiment','sentiment')
    else if (tab === 'snapshot') loadSnapshot()
    else if (tab === 'news') loadNews()
  }, [symbol, tab, available])

  if (!available) return (
    <div className="p-3 bg-red-900/20 border border-red-800/40 rounded-xl text-xs text-red-300 flex items-center gap-2">
      <AlertTriangle size={14}/> TradingView MCP bridge unavailable
    </div>
  )

  const tabs = [
    {id:'combined',icon:<Brain size={12}/>,label:'Analysis'},
    {id:'backtest',icon:<BarChart3 size={12}/>,label:'Backtest'},
    {id:'compare',icon:<Activity size={12}/>,label:'Compare'},
    {id:'sentiment',icon:<Globe size={12}/>,label:'Sentiment'},
    {id:'news',icon:<Newspaper size={12}/>,label:'News'},
    {id:'snapshot',icon:<TrendingUp size={12}/>,label:'Snapshot'},
    {id:'sources',icon:<Database size={12}/>,label:'Sources'},
  ]

  return (
    <div className="bg-[#111827] border border-indigo-800/40 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-indigo-900/40 to-purple-900/30 border-b border-indigo-800/30">
        <Zap size={14} className="text-indigo-400"/>
        <span className="text-xs font-bold text-indigo-300">MCP Intelligence</span>
        <span className="text-[9px] text-gray-500 ml-auto">tradingview-mcp</span>
      </div>

      <div className="flex gap-1 px-2 py-1.5 overflow-x-auto scrollbar-hide border-b border-[#1f2937]">
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-medium whitespace-nowrap transition-all ${
              tab===t.id ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-[#1f2937]'
            }`}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      <div className="p-3 max-h-[400px] overflow-y-auto">
        {tab === 'backtest' && (
          <div className="flex gap-2 mb-3">
            <select value={btStrategy} onChange={e=>{setBtStrategy(e.target.value)}}
              className="bg-[#1f2937] text-gray-300 text-[10px] rounded px-2 py-1 border border-[#2a2e39]">
              {STRATEGIES.map(s=><option key={s} value={s}>{s}</option>)}
            </select>
            <select value={btPeriod} onChange={e=>setBtPeriod(e.target.value)}
              className="bg-[#1f2937] text-gray-300 text-[10px] rounded px-2 py-1 border border-[#2a2e39]">
              {['3mo','6mo','1y','2y'].map(p=><option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={()=>load('backtest','backtest',`?strategy=${btStrategy}&period=${btPeriod}`)}
              className="px-2 py-1 bg-indigo-600 rounded text-[10px] text-white hover:bg-indigo-700">
              <RefreshCw size={10}/>
            </button>
          </div>
        )}
        {tab === 'compare' && (
          <div className="flex gap-2 mb-3">
            <select value={btPeriod} onChange={e=>setBtPeriod(e.target.value)}
              className="bg-[#1f2937] text-gray-300 text-[10px] rounded px-2 py-1 border border-[#2a2e39]">
              {['3mo','6mo','1y','2y'].map(p=><option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={()=>load('compare','compare',`?period=${btPeriod}`)}
              className="px-2 py-1 bg-indigo-600 rounded text-[10px] text-white hover:bg-indigo-700">
              <RefreshCw size={10}/>
            </button>
          </div>
        )}

        {Object.values(loading).some(Boolean) ? (
          <div className="flex items-center justify-center py-8 gap-2">
            <div className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"/>
            <span className="text-xs text-gray-500">Loading MCP data...</span>
          </div>
        ) : (
          <RenderData tab={tab} data={data} displayName={displayName} onLoadConsensus={loadConsensus}/>
        )}
      </div>
    </div>
  )
}

function RenderData({tab, data, displayName, onLoadConsensus}) {
  if (tab==='combined') return <CombinedView d={data.combined}/>
  if (tab==='backtest') return <BacktestView d={data.backtest}/>
  if (tab==='compare') return <CompareView d={data.compare}/>
  if (tab==='sentiment') return <SentimentView d={data.sentiment}/>
  if (tab==='news') return <NewsView d={data.news}/>
  if (tab==='snapshot') return <SnapshotView d={data.snapshot}/>
  if (tab==='sources') return <DataSourcesView d={data.sources} consensus={data.consensus} onLoadConsensus={onLoadConsensus}/>
  return null
}

function CombinedView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const c = d.confluence || {}
  const tech = d.technical || {}
  const ms = tech.market_sentiment || {}
  const tv = tech.extended_indicators?.tv_recommendation || {}
  return (
    <div className="space-y-2">
      <div className={`p-2 rounded-lg border text-center ${
        c.confidence==='HIGH' ? 'bg-green-900/20 border-green-700/40' : 'bg-yellow-900/20 border-yellow-700/40'
      }`}>
        <div className="text-[10px] text-gray-400 uppercase">Confluence</div>
        <div className={`text-sm font-bold ${c.confidence==='HIGH'?'text-green-400':'text-yellow-400'}`}>
          {c.confidence} — {c.tech_signal}
        </div>
        <div className="text-[10px] text-gray-500 mt-1">
          Sentiment: {c.sentiment_label} ({c.sentiment_score})
        </div>
      </div>
      {tv.overall_signal && (
        <Row label="TV Recommendation" value={tv.overall_signal} sub={`MA: ${tv.ma_signal} | Osc: ${tv.oscillators_signal}`}/>
      )}
      {ms.momentum && <Row label="Momentum" value={ms.momentum}/>}
      {ms.buy_sell_signal && <Row label="Signal" value={ms.buy_sell_signal}/>}
      {tech.extended_indicators?.rsi && (
        <Row label="RSI" value={`${tech.extended_indicators.rsi.value} (${tech.extended_indicators.rsi.signal})`}/>
      )}
      {tech.extended_indicators?.macd && (
        <Row label="MACD" value={tech.extended_indicators.macd.crossover}/>
      )}
      {d.news?.count > 0 && (
        <div className="mt-2">
          <div className="text-[9px] text-gray-500 uppercase mb-1">Latest News</div>
          {d.news.latest?.slice(0,2).map((n,i)=>(
            <div key={i} className="text-[10px] text-gray-400 mb-1 truncate">• {n.title || n}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function BacktestView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const m = d.metrics || d
  return (
    <div className="space-y-1.5">
      <div className="text-center mb-2">
        <div className="text-[10px] text-gray-500 uppercase">{d.strategy || 'Strategy'} on {d.symbol}</div>
        <div className={`text-lg font-bold ${(m.total_return_pct||0)>=0?'text-green-400':'text-red-400'}`}>
          {m.total_return_pct?.toFixed(1) || 0}%
        </div>
      </div>
      <Row label="Win Rate" value={`${m.win_rate_pct?.toFixed(1)||0}%`}/>
      <Row label="Sharpe Ratio" value={m.sharpe_ratio?.toFixed(2)||'—'}/>
      <Row label="Max Drawdown" value={`${m.max_drawdown_pct?.toFixed(1)||0}%`}/>
      <Row label="Total Trades" value={m.total_trades||0}/>
      <Row label="Profit Factor" value={m.profit_factor?.toFixed(2)||'—'}/>
      {m.buy_and_hold_return_pct != null && (
        <Row label="Buy & Hold" value={`${m.buy_and_hold_return_pct?.toFixed(1)}%`}/>
      )}
      {m.calmar_ratio != null && <Row label="Calmar Ratio" value={m.calmar_ratio?.toFixed(2)}/>}
    </div>
  )
}

function CompareView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const results = d.ranked_strategies || d.results || d.strategies || []
  if (!Array.isArray(results) || !results.length) return <div className="text-xs text-gray-500">No comparison data</div>
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] text-gray-500 uppercase text-center mb-2">Strategy Leaderboard — {d.symbol}</div>
      {results.map((s,i)=>{
        const m = s.metrics || s
        const ret = m.total_return_pct ?? m.return_pct ?? 0
        return (
          <div key={i} className={`flex items-center gap-2 p-1.5 rounded ${i===0?'bg-yellow-900/20 border border-yellow-700/30':'bg-[#1a1e2e]'}`}>
            <span className={`text-[10px] font-bold w-4 ${i===0?'text-yellow-400':i<3?'text-indigo-400':'text-gray-500'}`}>#{i+1}</span>
            <span className="text-[10px] text-gray-300 flex-1 capitalize">{s.strategy||s.name}</span>
            <span className={`text-[10px] font-mono font-bold ${ret>=0?'text-green-400':'text-red-400'}`}>
              {ret>=0?'+':''}{ret.toFixed(1)}%
            </span>
            <span className="text-[9px] text-gray-500">SR:{(m.sharpe_ratio||0).toFixed(1)}</span>
          </div>
        )
      })}
    </div>
  )
}

function SentimentView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const score = d.sentiment_score || 0
  const label = d.sentiment_label || 'Neutral'
  return (
    <div className="space-y-2">
      <div className={`text-center p-2 rounded-lg ${score>0.1?'bg-green-900/20':'score<-0.1'?'bg-red-900/20':'bg-gray-800'}`}>
        <div className="text-[10px] text-gray-400 uppercase">Reddit Sentiment</div>
        <div className={`text-lg font-bold ${score>0.1?'text-green-400':score<-0.1?'text-red-400':'text-gray-400'}`}>
          {label}
        </div>
        <div className="text-[10px] text-gray-500">Score: {score.toFixed(3)} • {d.posts_analyzed||0} posts</div>
      </div>
      {d.bullish_count != null && <Row label="Bullish Posts" value={d.bullish_count}/>}
      {d.bearish_count != null && <Row label="Bearish Posts" value={d.bearish_count}/>}
    </div>
  )
}

function NewsView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const items = d.items || d.articles || []
  if (!items.length) return <div className="text-xs text-gray-500 text-center py-4">No news available</div>
  return (
    <div className="space-y-2">
      {items.slice(0,8).map((n,i)=>(
        <div key={i} className="p-2 bg-[#1a1e2e] rounded-lg">
          <div className="text-[10px] text-gray-300 leading-snug">{n.title}</div>
          {n.source && <div className="text-[9px] text-gray-600 mt-1">{n.source} • {n.published||''}</div>}
        </div>
      ))}
    </div>
  )
}

function SnapshotView({d}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const sections = Object.entries(d).filter(([k])=>k!=='timestamp'&&k!=='error')
  return (
    <div className="space-y-2">
      {sections.map(([section, assets])=>{
        if (typeof assets !== 'object' || assets === null) return null
        const entries = Array.isArray(assets) ? assets : Object.entries(assets).map(([k,v])=>({symbol:k,...(typeof v==='object'?v:{value:v})}))
        return (
          <div key={section}>
            <div className="text-[9px] text-gray-500 uppercase mb-1">{section.replace(/_/g,' ')}</div>
            {entries.slice(0,6).map((a,i)=>{
              const chg = a.change_pct ?? a.changePercent ?? a.change ?? null
              return (
                <div key={i} className="flex justify-between text-[10px] py-0.5">
                  <span className="text-gray-400">{a.symbol || a.name || '—'}</span>
                  <div className="flex gap-2">
                    <span className="text-gray-300 font-mono">{a.price?.toFixed?.(2)||a.value||'—'}</span>
                    {chg!=null && <span className={`font-mono ${chg>=0?'text-green-400':'text-red-400'}`}>{chg>=0?'+':''}{typeof chg==='number'?chg.toFixed(2):chg}%</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

function Row({label,value,sub}) {
  const getColor = v => {
    if (!v) return 'text-gray-400'
    const s = String(v).toLowerCase()
    if (s.includes('bull')||s.includes('buy')||s.includes('strong buy')) return 'text-green-400'
    if (s.includes('bear')||s.includes('sell')||s.includes('strong sell')) return 'text-red-400'
    return 'text-gray-300'
  }
  return (
    <div>
      <div className="flex justify-between items-center">
        <span className="text-[10px] text-gray-500">{label}</span>
        <span className={`text-[10px] font-medium ${getColor(value)}`}>{String(value??'—')}</span>
      </div>
      {sub && <div className="text-[9px] text-gray-600 text-right">{sub}</div>}
    </div>
  )
}

function DataSourcesView({d, consensus, onLoadConsensus}) {
  if (!d) return <Empty/>
  if (d.error) return <Err msg={d.error}/>
  const sources = d.sources || []
  return (
    <div className="space-y-2">
      <div className="text-center mb-2">
        <div className="text-[10px] text-gray-500 uppercase">Free Data Sources</div>
        <div className="text-xs text-indigo-400 font-bold">{d.total_active || 0} Active</div>
        <div className="text-[8px] text-gray-600 mt-0.5">{d.regulatory_note}</div>
      </div>
      {sources.map((s,i)=>(
        <div key={i} className={`p-2 rounded-lg border ${
          s.configured ? 'bg-[#0d1117] border-green-800/30' : 'bg-[#0d1117] border-gray-800/30 opacity-60'
        }`}>
          <div className="flex items-center gap-1.5 mb-1">
            {s.configured
              ? <CheckCircle size={10} className="text-green-500"/>
              : <XCircle size={10} className="text-gray-600"/>
            }
            <span className="text-[10px] font-bold text-gray-200">{s.name}</span>
            <span className={`text-[8px] px-1.5 py-0.5 rounded-full ml-auto ${
              s.configured ? 'bg-green-900/40 text-green-400' : 'bg-gray-800 text-gray-500'
            }`}>{s.configured ? 'ACTIVE' : 'SETUP NEEDED'}</span>
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed">
            <div>Delay: <span className="text-gray-400">{s.delay}</span></div>
            <div>Rate: <span className="text-gray-400">{s.rate_limit}</span></div>
            {s.notes && <div className="text-[8px] text-gray-600 mt-0.5 italic">{s.notes}</div>}
          </div>
        </div>
      ))}

      {onLoadConsensus && (
        <div className="mt-3 pt-2 border-t border-gray-800">
          <button onClick={onLoadConsensus}
            className="w-full py-1.5 bg-indigo-600/20 border border-indigo-700/40 rounded-lg text-[10px] text-indigo-300 hover:bg-indigo-600/30 transition-colors">
            ⚡ Test Consensus Price
          </button>
          {consensus && !consensus.error && (
            <div className="mt-2 space-y-1">
              <Row label="Price" value={consensus.price}/>
              <Row label="Consensus" value={consensus.consensus_price}/>
              <Row label="Sources" value={consensus.sources_used?.join(', ')}/>
              <Row label="Agreement" value={consensus.sources_agree ? '✅ Sources agree' : '⚠️ Deviation detected'}/>
              {consensus.max_deviation_pct > 0 && <Row label="Max Dev" value={`${consensus.max_deviation_pct}%`}/>}
            </div>
          )}
          {consensus?.error && <div className="text-[9px] text-red-400 mt-1">{consensus.error}</div>}
        </div>
      )}
    </div>
  )
}

function Empty() { return <div className="text-xs text-gray-600 text-center py-6">Click a tab to load data</div> }
function Err({msg}) { return <div className="text-xs text-red-400 py-4 text-center">{msg}</div> }
