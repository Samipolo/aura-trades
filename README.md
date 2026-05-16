# AURA TRADES - AI Day Trading System

A self-decision based day trading AI that analyzes all CFD trading pairs on the 15-minute timeframe with 1:2 Risk:Reward ratio.

## Features

- **Multi-Factor Analysis**: Combines order flow, technical indicators, correlation analysis, and market structure
- **Real Market Data**: Uses Yahoo Finance for 100% real-time data (free, no API key needed)
- **Ranked Trade Ideas**: All signals are scored and ranked from best to least
- **1:2 Risk:Reward**: Every trade has a strict 1:2 R:R ratio

## Technical Indicators & Tools

| Category | Indicators |
|----------|-----------|
| Trend | EMA 50, EMA 200 |
| Volatility | Bollinger Bands (50, 2.5 StdDev) |
| VWAP | Daily, Weekly, Monthly, Previous Day, Previous Week |
| Volume Profile | Daily, Previous Day, Weekly, Monthly (POC, VAH, VAL) |
| Session | Initial Balance (first hour) |
| Momentum | RSI 14, MACD (12, 26, 9) |
| Volatility | ATR 14, ADX 14 |
| Market Structure | Swing H/L, BOS, CHoCH, Order Blocks, FVGs |
| Correlation | Cross-pair, DXY proxy, Risk Sentiment |

## Instruments Covered

- **Forex**: 20 major/minor pairs (EUR/USD, GBP/USD, USD/JPY, etc.)
- **Indices**: S&P 500, NASDAQ, DAX, FTSE, Nikkei, etc.
- **Commodities**: Gold, Silver, Crude Oil, Natural Gas, Copper, Platinum
- **Crypto**: BTC/USD, ETH/USD

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API server starts at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The web UI starts at `http://localhost:3000`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/analyze` | Full analysis of all instruments with ranked signals |
| `GET /api/analyze/{symbol}` | Single instrument analysis |
| `GET /api/instruments` | List all monitored instruments |
| `GET /api/health` | Health check |

## How It Works

1. **Data Fetch**: Pulls 60 days of 15-minute candle data from Yahoo Finance
2. **Indicator Calculation**: Computes all technical indicators
3. **Market Structure**: Identifies swing points, BOS, CHoCH, order blocks, FVGs
4. **Correlation**: Analyzes cross-pair correlations and risk sentiment
5. **Signal Generation**: Multi-factor confluence scoring
6. **Ranking**: Signals ranked by confidence, confluence, correlation alignment

## Architecture

```
backend/
├── main.py              # FastAPI server
├── config.py            # Instruments & settings
├── data_fetcher.py      # Yahoo Finance data fetcher
├── indicators.py        # All technical indicators
├── market_structure.py  # SMC / Order flow analysis
├── correlation.py       # Inter-market correlation
├── signal_generator.py  # Trade signal & ranking engine
└── requirements.txt     # Python dependencies

frontend/
├── src/
│   ├── App.jsx          # Main React component
│   ├── main.jsx         # Entry point
│   └── index.css        # Tailwind styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Disclaimer

This is an educational tool. Trading CFDs carries significant risk. Past performance does not guarantee future results. Always use proper risk management and never trade with money you cannot afford to lose.
