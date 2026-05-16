import React, { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, LineStyle, CandlestickSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts'
import {
  ChevronLeft, ChevronRight, ArrowLeft, TrendingUp, TrendingDown,
  Shield, Eye, Zap
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : window.location.port === '3000' ? '/api' : 'http://localhost:8000/api'

// ═══════════════════════════════════════════════════════════════
// CUSTOM RECTANGLE PRIMITIVE — draws trade boxes on the chart
// ═══════════════════════════════════════════════════════════════

class BoxRenderer {
  constructor() { this._data = null }
  setData(d) { this._data = d }
  draw(target) {
    target.useBitmapCoordinateSpace(scope => {
      if (!this._data) return
      const ctx = scope.context
      const { x1, y1, x2, y2, fillColor, borderColor } = this._data
      const hr = scope.horizontalPixelRatio
      const vr = scope.verticalPixelRatio
      const bx1 = Math.round(x1 * hr)
      const by1 = Math.round(y1 * vr)
      const bx2 = Math.round(x2 * hr)
      const by2 = Math.round(y2 * vr)
      ctx.fillStyle = fillColor
      ctx.fillRect(bx1, by1, bx2 - bx1, by2 - by1)
      if (borderColor) {
        ctx.strokeStyle = borderColor
        ctx.lineWidth = 1 * hr
        ctx.strokeRect(bx1, by1, bx2 - bx1, by2 - by1)
      }
    })
  }
}

class BoxPaneView {
  constructor(source) {
    this._source = source
    this._renderer = new BoxRenderer()
  }
  update() {
    const s = this._source
    if (!s._chart || !s._series) { this._renderer.setData(null); return }
    const ts = s._chart.timeScale()
    let x1 = ts.timeToCoordinate(s._p1.time)
    let x2 = ts.timeToCoordinate(s._p2.time)
    const y1 = s._series.priceToCoordinate(s._p1.price)
    const y2 = s._series.priceToCoordinate(s._p2.price)
    if (y1 === null || y2 === null) { this._renderer.setData(null); return }
    if (x1 === null && x2 === null) { this._renderer.setData(null); return }
    if (x1 === null) x1 = 0
    if (x2 === null) x2 = ts.width()
    this._renderer.setData({
      x1: Math.min(x1, x2), y1: Math.min(y1, y2),
      x2: Math.max(x1, x2), y2: Math.max(y1, y2),
      fillColor: s._fillColor,
      borderColor: s._borderColor || null,
    })
  }
  renderer() { return this._renderer }
}

class TradeBox {
  constructor(p1, p2, fillColor, borderColor) {
    this._p1 = p1; this._p2 = p2
    this._fillColor = fillColor; this._borderColor = borderColor || null
    this._chart = null; this._series = null; this._requestUpdate = null
    this._paneView = new BoxPaneView(this)
  }
  attached({ chart, series, requestUpdate }) {
    this._chart = chart; this._series = series; this._requestUpdate = requestUpdate
  }
  detached() { this._chart = null; this._series = null; this._requestUpdate = null }
  paneViews() { return [this._paneView] }
  updateAllViews() { this._paneView.update() }
}

// ═══════════════════════════════════════════════════════════════
// DRAW TRADE SIGNAL ON CHART
// ═══════════════════════════════════════════════════════════════

function drawTradeSignal(chart, series, signal, candles) {
  if (!signal || !candles.length) return

  const lastCandle = candles[candles.length - 1]
  const startTime = lastCandle.time - (2 * 15 * 60)
  const endTime = lastCandle.time + (25 * 15 * 60)

  const entry = signal.entry
  const tp = signal.take_profit
  const sl = signal.stop_loss
  const isLong = signal.direction === 'LONG'

  // TP box (profit zone) — dark blue like TradingView
  const tpBox = new TradeBox(
    { time: startTime, price: entry },
    { time: endTime, price: tp },
    'rgba(33, 150, 243, 0.28)',
    'rgba(33, 150, 243, 0.45)'
  )
  series.attachPrimitive(tpBox)

  // SL box (risk zone) — gray
  const slBox = new TradeBox(
    { time: startTime, price: entry },
    { time: endTime, price: sl },
    'rgba(128, 128, 134, 0.22)',
    'rgba(128, 128, 134, 0.35)'
  )
  series.attachPrimitive(slBox)

  // Entry price line
  series.createPriceLine({
    price: entry,
    color: '#2962FF',
    lineWidth: 1,
    lineStyle: LineStyle.Solid,
    axisLabelVisible: true,
    title: '',
  })

  // TP price line
  series.createPriceLine({
    price: tp,
    color: '#26a69a',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '',
  })

  // SL price line
  series.createPriceLine({
    price: sl,
    color: '#787b86',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '',
  })

  // Entry marker arrow
  createSeriesMarkers(series, [{
    time: lastCandle.time,
    position: isLong ? 'belowBar' : 'aboveBar',
    color: isLong ? '#26a69a' : '#ef5350',
    shape: isLong ? 'arrowUp' : 'arrowDown',
    text: `${signal.direction} @ ${fmtPrice(entry)}`,
  }]);
}

// ═══════════════════════════════════════════════════════════════
// MAIN CHART COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function TradingChart({ signals, selectedSignal, onBack, onSelectSignal }) {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)

  const signal = selectedSignal || signals?.[currentIndex]
  const isLong = signal?.direction === 'LONG'

  // Sync index when selectedSignal changes
  useEffect(() => {
    if (selectedSignal && signals) {
      const idx = signals.findIndex(s => s.symbol === selectedSignal.symbol)
      if (idx >= 0) setCurrentIndex(idx)
    }
  }, [selectedSignal, signals])

  const navigate = (dir) => {
    const next = dir === 'prev'
      ? Math.max(0, currentIndex - 1)
      : Math.min((signals?.length || 1) - 1, currentIndex + 1)
    setCurrentIndex(next)
    if (onSelectSignal && signals?.[next]) onSelectSignal(signals[next])
  }

  // Create chart + load data when signal changes
  useEffect(() => {
    if (!signal || !chartContainerRef.current) return
    setLoading(true)
    setError(null)

    // Destroy old chart
    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }

    const container = chartContainerRef.current
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#0a0e17' },
        textColor: '#787b86',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1a1e2e' },
        horzLines: { color: '#1a1e2e' },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: '#555', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#2a2e39' },
        horzLine: { color: '#555', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#2a2e39' },
      },
      rightPriceScale: {
        borderColor: '#2a2e39',
        scaleMargins: { top: 0.05, bottom: 0.2 },
      },
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 35,
        barSpacing: 6,
      },
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    })
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })

    // Fetch chart data
    fetch(`${API_BASE}/chart-data/${encodeURIComponent(signal.symbol)}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(data => {
        if (!data.candles?.length) { setError('No chart data'); setLoading(false); return }

        candleSeries.setData(data.candles.map(c => ({
          time: c.time, open: c.open, high: c.high, low: c.low, close: c.close
        })))

        volumeSeries.setData(data.candles.map(c => ({
          time: c.time,
          value: c.volume || 0,
          color: c.close >= c.open ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)',
        })))

        drawTradeSignal(chart, candleSeries, signal, data.candles)
        chart.timeScale().scrollToRealTime()
        setLoading(false)
      })
      .catch(err => { setError(err.message); setLoading(false) })

    const onResize = () => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth, height: container.clientHeight })
      }
    }
    window.addEventListener('resize', onResize)

    // Auto-refresh every 15s for real-time MT5 data
    const refreshTimer = setInterval(() => {
      fetch(`${API_BASE}/chart-data/${encodeURIComponent(signal.symbol)}`)
        .then(r => r.json())
        .then(data => {
          if (data.candles?.length) {
            candleSeries.setData(data.candles.map(c => ({
              time: c.time, open: c.open, high: c.high, low: c.low, close: c.close
            })))
            volumeSeries.setData(data.candles.map(c => ({
              time: c.time,
              value: c.volume || 0,
              color: c.close >= c.open ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)',
            })))
          }
        })
        .catch(() => {})
    }, 15000)

    return () => {
      clearInterval(refreshTimer)
      window.removeEventListener('resize', onResize)
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [signal?.symbol])

  if (!signal) return null

  return (
    <div className="fixed inset-0 bg-[#0a0e17] z-50 flex flex-col">
      {/* ─── TOP BAR ─── */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0d1117] border-b border-[#1f2937] shrink-0">
        {/* Left: Back + instrument */}
        <div className="flex items-center gap-3">
          <button onClick={onBack}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-[#1f2937] transition-all">
            <ArrowLeft size={14} /> Dashboard
          </button>
          <div className="h-6 w-px bg-[#2a2e39]" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-bold text-sm">{signal.display_name}</span>
              <span className="text-[10px] text-gray-500 font-mono">{signal.symbol}</span>
            </div>
            <span className="text-[10px] text-gray-600">15 Minute Chart</span>
          </div>
        </div>

        {/* Center: Signal badge */}
        <div className={`flex items-center gap-3 px-4 py-1.5 rounded-lg border text-xs font-semibold ${
          isLong
            ? 'bg-green-900/30 border-green-700/40 text-green-400'
            : 'bg-red-900/30 border-red-700/40 text-red-400'
        }`}>
          {isLong ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span>{signal.direction}</span>
          <span className="text-gray-600">|</span>
          <span className="text-blue-400">{signal.confidence?.toFixed(0)}%</span>
          <span className="text-gray-600">|</span>
          <span className={signal.risk_grade === 'A+' || signal.risk_grade === 'A' ? 'text-green-400' : 'text-yellow-400'}>
            {signal.risk_grade}
          </span>
          <span className="text-gray-600">|</span>
          <span className="text-indigo-400">R:R 1:{signal.dynamic_rr || signal.risk_reward}</span>
          <span className="text-gray-600">|</span>
          <span className="text-purple-400">Win {signal.win_probability?.toFixed(0) || '—'}%</span>
        </div>

        {/* Right: Navigation */}
        <div className="flex items-center gap-2">
          <button onClick={() => navigate('prev')} disabled={currentIndex === 0}
            className="flex items-center gap-1 px-2 py-1.5 rounded text-xs text-gray-400 hover:text-white hover:bg-[#1f2937] disabled:opacity-30 transition-all">
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="text-gray-500 text-xs font-mono">{currentIndex + 1}/{signals?.length || 0}</span>
          <button onClick={() => navigate('next')} disabled={currentIndex >= (signals?.length || 1) - 1}
            className="flex items-center gap-1 px-2 py-1.5 rounded text-xs text-gray-400 hover:text-white hover:bg-[#1f2937] disabled:opacity-30 transition-all">
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* ─── SIGNAL PILLS (horizontal scrollable) ─── */}
      <div className="flex gap-1.5 px-4 py-1.5 bg-[#0a0e17] border-b border-[#1a1e2e] overflow-x-auto shrink-0 scrollbar-hide">
        {signals?.map((s, i) => (
          <button key={s.symbol}
            onClick={() => { setCurrentIndex(i); if (onSelectSignal) onSelectSignal(s) }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-[10px] font-medium whitespace-nowrap transition-all ${
              i === currentIndex
                ? 'bg-indigo-600 text-white'
                : 'bg-[#1a1e2e] text-gray-500 hover:text-gray-300 hover:bg-[#252a3a]'
            }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${s.direction === 'LONG' ? 'bg-green-400' : 'bg-red-400'}`} />
            {s.display_name}
          </button>
        ))}
      </div>

      {/* ─── CHART AREA ─── */}
      <div className="flex-1 relative min-h-0">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0e17]/80">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <span className="text-gray-400 text-sm">Loading chart data...</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0e17]/80">
            <div className="text-red-400 text-sm">Error: {error}</div>
          </div>
        )}

        <div ref={chartContainerRef} className="w-full h-full" />

        {/* ─── FLOATING SIGNAL INFO OVERLAY ─── */}
        {!loading && signal && (
          <div className="absolute top-3 left-3 z-10 bg-[#111827]/90 backdrop-blur-sm border border-[#2a2e39] rounded-lg p-3 text-xs min-w-[180px]">
            <div className="flex items-center gap-2 mb-2">
              {isLong ? <TrendingUp size={12} className="text-green-400" /> : <TrendingDown size={12} className="text-red-400" />}
              <span className={`font-bold ${isLong ? 'text-green-400' : 'text-red-400'}`}>{signal.direction}</span>
              <span className="text-gray-600">•</span>
              <span className="text-gray-400">{signal.display_name}</span>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-500">Entry</span>
                <span className="font-mono text-blue-400">{fmtPrice(signal.entry)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Take Profit</span>
                <span className="font-mono text-green-400">{fmtPrice(signal.take_profit)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Stop Loss</span>
                <span className="font-mono text-red-400">{fmtPrice(signal.stop_loss)}</span>
              </div>
              <div className="h-px bg-[#2a2e39] my-1" />
              <div className="flex justify-between">
                <span className="text-gray-500">Risk:Reward</span>
                <span className="font-mono text-indigo-400">1:{signal.dynamic_rr || signal.risk_reward}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Confidence</span>
                <span className="font-mono text-blue-400">{signal.confidence?.toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Grade</span>
                <span className={`font-mono ${signal.risk_grade === 'A+' || signal.risk_grade === 'A' ? 'text-green-400' : 'text-yellow-400'}`}>
                  {signal.risk_grade}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Win Prob</span>
                <span className="font-mono text-purple-400">{signal.win_probability?.toFixed(0) || '—'}%</span>
              </div>
            </div>
            <div className="mt-2 pt-1.5 border-t border-[#2a2e39]">
              <div className="flex flex-wrap gap-1">
                {signal.factors?.slice(0, 4).map((f, i) => (
                  <span key={i} className="px-1.5 py-0.5 bg-[#1f2937] rounded text-[9px] text-gray-400">
                    {f.name.replace(/_/g, ' ')}
                  </span>
                ))}
                {(signal.factors?.length || 0) > 4 && (
                  <span className="px-1.5 py-0.5 bg-[#1f2937] rounded text-[9px] text-gray-500">
                    +{signal.factors.length - 4}
                  </span>
                )}
              </div>
            </div>
            {/* ─── MT5 ONE-CLICK TRADE BUTTON ─── */}
            <div className="mt-3">
              <button 
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE}/mt5/trade`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        symbol: signal.symbol,
                        direction: signal.direction,
                        lot_size: 1.0,
                        sl: signal.stop_loss || 0,
                        tp: signal.take_profit || 0
                      })
                    });
                    const data = await res.json();
                    if (res.ok && data.success) {
                      alert(`✅ MT5 Trade Placed!\nTicket: ${data.deal_ticket}\nPrice: ${data.price}`);
                    } else {
                      alert(`❌ MT5 Error: ${data.detail || data.error}`);
                    }
                  } catch (e) {
                    alert('❌ Failed to communicate with MT5 backend');
                  }
                }}
                className={`w-full py-2 rounded font-bold text-[11px] uppercase tracking-wider transition-all flex justify-center items-center gap-1 ${
                  isLong 
                    ? 'bg-green-600 hover:bg-green-500 text-white shadow-[0_0_10px_rgba(38,166,154,0.4)]' 
                    : 'bg-red-600 hover:bg-red-500 text-white shadow-[0_0_10px_rgba(239,83,80,0.4)]'
                }`}
              >
                <Zap size={12} />
                TAKE ON MT5 (1 LOT)
              </button>
            </div>
          </div>
        )}

        {/* Watermark */}
        <div className="absolute bottom-3 left-3 z-10 flex items-center gap-1.5 text-[10px] text-gray-700 select-none">
          <Zap size={10} /> AURA TRADES V2
        </div>
      </div>
    </div>
  )
}

function fmtPrice(price) {
  if (!price && price !== 0) return '—'
  if (price > 1000) return price.toFixed(2)
  if (price > 10) return price.toFixed(4)
  return price.toFixed(5)
}
