# KitePulse AI — Institutional Quantitative Trading & Algorithmic Execution Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.3+-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3%20WAL%20Mode-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Zerodha Kite](https://img.shields.io/badge/Broker-Zerodha%20KiteConnect%20v5-FF5722)](https://kite.trade/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, event-driven intraday algorithmic trading and quantitative analytics platform for Indian Equity & Derivatives markets (NSE / NFO). Built on clean architectural principles, **KitePulse AI** pairs real-time market data streaming from Zerodha Kite Connect with multimodal Generative AI reasoning (Google Gemini) and deterministic quantitative strategies, guarded by cryptographic security, two-tier risk management, and a zero-dummy-data integrity pipeline.

---

## Architecture Overview

```
                                  +-------------------------------------------------------------+
                                  |                     CLIENT FRONTEND                         |
                                  |        React 19 + TypeScript + Vite + Lightweight Charts    |
                                  +-------------------------------------------------------------+
                                                 |                                   ^
                           REST API Calls        |                                   |  WebSocket Ticks
                           (Bearer Auth)         v                                   |  (Every 2s)
                                  +-------------------------------------------------------------+
                                  |                      FASTAPI GATEWAY                        |
                                  |         Lifespan Managed Event Loops + CORS + Audit Logs    |
                                  +-------------------------------------------------------------+
                                                 |                                   |
                         +-----------------------+-------------------+               |
                         |                                           |               |
                         v                                           v               v
           +---------------------------+               +---------------------------+
           |     SECURITY VAULT        |               |   UNIFIED TRADING ENGINE  |
           | PBKDF2 + Fernet AES Enc   |               |     Strategy Orchestrator |
           +---------------------------+               +---------------------------+
                         |                                           |
                         | Key Unlocked                              +---------------+---------------+
                         v                                           |                               |
           +---------------------------+                             v                               v
           |  SQLite Trading DB (WAL)  |               +---------------------------+   +---------------------------+
           | Repository DAO Layer      |               |   PaperExecutionEngine    |   |    KiteExecutionEngine    |
           +---------------------------+               |   Virtual Capital Sandbox |   |    Zerodha KiteConnect    |
                                                       +---------------------------+   +---------------------------+
                                                                                                     |
                                                                               30s Token Heartbeat   v
                                                                                       +---------------------------+
                                                                                       |   Zerodha NSE / NFO API   |
                                                                                       +---------------------------+
```

---

## Key System Highlights

- **Extensible Strategy & Factory Pattern (`core/interfaces.py`)**: Abstract base classes decouple execution logic (`BaseOrderExecutor`), quote ingestion (`BaseMarketDataProvider`), strategy generation (`BaseTradeAnalyzer`), and multi-channel alerting (`BaseNotificationDispatcher`).
- **Zerodha Kite 30-Second Token Verification Heartbeat**: Outbound broker requests are validated against a 30-second token verification heartbeat, ensuring expired OAuth sessions or invalid credentials fail fast before orders reach the exchange.
- **Zero Plaintext Secret Storage (Fernet Cryptographic Vault)**: API secrets, access tokens, and webhook URLs are encrypted at rest using Fernet (AES-128 in CBC mode with HMAC authentication) derived via PBKDF2-HMAC-SHA256 (100,000 rounds) from a user master password.
- **Two-Tier Safety Guardrails**:
  - **Lot Size Strict Isolation**: In the initial incubation phase, all trades are hard-capped at exactly 1 lot to prevent capital overexposure.
  - **Human-in-the-Loop Audio & UI Approval**: AI generates a proposal with dynamic stop-loss, targets, and a synthesized voice pitch. No order is dispatched until explicitly approved via voice command ("Approve") or UI click within a 60-second window.
  - **Automated Trailing Risk Management**: Open positions are monitored in real time against underlying live ticks, automatically executing square-off orders when stop-loss or take-profit barriers are breached.
- **Deterministic Indicator Fallback Engine**: If the Gemini LLM is offline or unconfigured, the system falls back to mathematical technical indicators (EMA 9/21/50, RSI 14, VWAP, ATR 14, Bollinger Bands, and Floor Pivot Points), maintaining uninterrupted 24/7 scanning.
- **Zero Dummy Data Guarantee**: When unconfigured, the platform reports configuration requirements rather than fabricating synthetic prices.

---

## Technical Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI + Uvicorn | Async ASGI server, Lifespan background workers, OpenAPI schema |
| **Broker SDK** | KiteConnect Python v5 | Official Zerodha Kite Connect SDK for quotes, historical bars, and orders |
| **AI Strategy** | Google GenAI SDK (`gemini-2.5-flash`) | Structured output analysis for technical trade proposal generation |
| **Data Engine** | Pandas & NumPy | High-performance vector calculations for EMA, RSI, VWAP, and ATR |
| **Persistence** | SQLite 3 (WAL Mode) | ACID transaction logging, immutable order audits, and position state |
| **Cryptography** | `cryptography` (Fernet & PBKDF2) | Zero-plaintext vault key derivation and AES symmetric encryption |
| **Frontend UI** | React 19 + TypeScript + Vite | Component-driven trading terminal with custom hooks and StrictMode |
| **Charting** | TradingView Lightweight Charts v5 | Canvas-accelerated candlestick rendering, EMA overlays, and VWAP bands |
| **Speech & Audio** | Web Speech API & Web Audio API | Hands-free spoken trade pitch synthesis and voice approval recognition |
| **Testing** | Pytest + AnyIO + Starlette TestClient | 17 automated integration & architectural unit tests |

---

## Repository Structure

```
trading/
├── backend/
│   ├── core/                           # Abstract architecture & strategy layer
│   │   ├── __init__.py
│   │   ├── interfaces.py               # Base contracts (BaseOrderExecutor, BaseMarketDataProvider, etc.)
│   │   └── paper_executor.py           # Virtual sandbox simulation engine
│   ├── tests/                          # Automated Pytest test suite (17 tests)
│   │   ├── test_30s_kite_auth.py       # Kite token heartbeat verification
│   │   ├── test_api.py                 # REST API endpoints & error handling
│   │   ├── test_core_architecture.py   # Strategy pattern & abstract interface tests
│   │   ├── test_security_auth.py       # PBKDF2 hashing & Fernet vault encryption
│   │   ├── test_server_logging.py      # 3MB rotating log audits & masking
│   │   └── test_trading.py             # Indicator math, proposal lifecycle, position DB restoration
│   ├── config.py                       # Pydantic Settings & environment variables
│   ├── database.py                     # TradingRepository DAO & SQLite WAL management
│   ├── gemini_analyzer.py              # Google Gemini LLM quantitative strategist
│   ├── kite_executor.py                # Broker abstraction & UnifiedTradingEngine
│   ├── main.py                         # FastAPI gateway with Lifespan context manager
│   ├── market_data.py                  # KiteConnect market quotes & candle enricher
│   ├── notifications.py                # Multi-channel Telegram, Discord, and Slack dispatcher
│   ├── security.py                     # PBKDF2 password derivation & session token tokens
│   ├── server_logger.py                # 3MB rotating file logger with request-response tracing
│   ├── technical_indicators.py         # EMA, RSI, VWAP, ATR, Bollinger Bands formulas
│   └── requirements.txt                # Pinned production Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/                 # Modular React UI components
│   │   │   ├── AuthGatekeeper.tsx      # Master password unlock modal
│   │   │   ├── Header.tsx              # Telemetry banner, mode switch, and connection status
│   │   │   ├── HistoryTracker.tsx      # Unified historical trade logs
│   │   │   ├── PositionsTable.tsx      # Real-time mark-to-market positions
│   │   │   ├── SettingsModal.tsx       # Vault credentials & notification settings
│   │   │   ├── TradeProposalCard.tsx   # 60s countdown proposal approval card
│   │   │   ├── TradingChart.tsx        # TradingView Lightweight Charts canvas
│   │   │   ├── VoiceRadar.tsx          # Speech recognition & audio radar HUD
│   │   │   └── Watchlist.tsx           # NSE index & stock ticker selector
│   │   ├── services/                   # Frontend API, WebSockets, and audio drivers
│   │   │   ├── api.ts                  # Typed REST API client & Bearer token management
│   │   │   ├── notifications.ts        # Browser desktop notification service
│   │   │   ├── sound.ts                # Synthesized audio sound effects
│   │   │   └── speech.ts               # Web Speech recognition & synthesis engine
│   │   ├── types/                      # TypeScript schemas & TSDoc documentation
│   │   │   └── index.ts
│   │   ├── App.tsx                     # Root application container & keyboard listeners
│   │   └── index.css                   # Cyberpunk / institutional dark theme design system
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── ARCHITECTURE.md                     # Detailed system design & concurrency documentation
├── start_all.bat                       # One-click launcher for backend & frontend
└── README.md                           # Platform documentation
```

---

## Quick Start & Server Setup

You can run KitePulse AI either with a **single one-click script** (recommended for Windows) or manually in two terminal tabs.

### Prerequisites
- **Python**: 3.11, 3.12, or 3.13
- **Node.js**: v18.0.0 or higher
- **Zerodha Kite Connect Developer Account** *(Optional: Paper Trading works out of the box with zero credentials!)*

---

### Option A: One-Click Quick Start (Windows)
Double-click [`start_all.bat`](file:///d:/DEVELOPMENT/android/trading/start_all.bat) or run from PowerShell:
```powershell
.\start_all.bat
```
This launcher automatically:
1. Verifies the Python virtual environment and launches the **FastAPI Backend** on `http://127.0.0.1:8000`.
2. Installs frontend dependencies (if missing) and starts the **Vite React UI** on `http://127.0.0.1:5173`.
3. Opens the terminals side-by-side with color-coded status banners.

---

### Option B: Manual Setup & Server Execution

#### 1. Backend Server Setup
```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows PowerShell
# source venv/bin/activate    # On Linux / macOS

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. (Optional) Create .env configuration file
# NOTE: Credentials can also be configured securely directly through the Web UI!
copy .env.example .env        # On Windows
# cp .env.example .env        # On Linux / macOS

# 5. Run the automated integration test suite (21 tests)
pytest tests -v

# 6. Start the FastAPI ASGI backend server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
> The backend will be available at **`http://127.0.0.1:8000`** (Swagger docs at `/docs`).

#### 2. Frontend Terminal Setup
In a second terminal window:
```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node.js dependencies
npm install

# 3. Verify TypeScript build and linting
npm run build
npm run lint

# 4. Start the Vite React development server
npm run dev
```
> The frontend terminal UI will be available at **`http://localhost:5173`**.

---

## How It Can Be Used (User Walkthrough)

KitePulse AI is designed for institutional-grade safety, disciplined risk management, and zero dummy data fabrication. Follow this end-to-end workflow:

### 1. First-Time Vault Initialization
1. Open your browser at **`http://localhost:5173`**.
2. On first boot, the **Cryptographic Gatekeeper** modal prompts you to create a **Master Password** (minimum 6 characters).
3. The system derives a 32-byte AES-128 Fernet key using PBKDF2-HMAC-SHA256 (100,000 rounds). **No plaintext credentials are ever stored on disk.**
4. Your master password creates a 24-hour sliding session token stored in your browser.

### 2. Configuring Broker & AI Credentials
Click the **Settings (Gear Icon)** in the top navigation bar to open the Encrypted Vault:
- **Zerodha Kite Connect**:
  - `API Key` & `API Secret`: Found in your [Kite Developer Console](https://kite.trade/).
  - `Access Token`: Generated daily after OAuth login, or paste your active session request token.
- **Google Gemini AI**:
  - `API Key`: Free from [Google AI Studio](https://aistudio.google.com/).
  - `Model`: Defaults to `gemini-2.5-flash` for low-latency reasoning.
- **Multi-Channel Notifications (Optional)**:
  - Telegram Bot Token & Chat ID
  - Discord Webhook URL
  - Slack Webhook URL
  - Desktop browser audio & visual chimes ("Office Mode" toggle).

> **No Zerodha Account?** You can still test! KitePulse AI includes a **Paper Trading Sandbox** with simulated ₹1,00,000 capital and deterministic mathematical technical indicators.

### 3. Choosing Your Trading Mode
In the top header, use the mode toggle:
- **`PAPER` (Default)**: Executes simulated trades within an in-memory virtual portfolio tracking real or mathematical prices with zero financial risk.
- **`LIVE`**: Dispatches real MIS Intraday orders directly to the National Stock Exchange (NSE) via Zerodha KiteConnect. Guarded by a mandatory 30-second token verification heartbeat.

### 4. Scanning Instruments & AI Reasoning
1. Select an instrument from the left-hand **Watchlist** (e.g., `NIFTY 50`, `BANK NIFTY`, `RELIANCE`, `TCS`, `INFY`).
2. The **TradingView Lightweight Chart** renders historical candles with technical indicators:
   - Exponential Moving Averages (EMA 9, EMA 21, EMA 50)
   - Volume Weighted Average Price (VWAP)
   - Relative Strength Index (RSI 14)
   - Average True Range (ATR 14)
   - Dynamic Pivot Points (Support 1/2, Resistance 1/2)
3. Click **"Scan Symbol"**:
   - KitePulse AI extracts vector indicators and dispatches a structured prompt to Google Gemini.
   - If the LLM is offline, the deterministic **Technical Fallback Engine** computes signals using classic quantitative momentum criteria.

### 5. Human-in-the-Loop Voice & UI Approval
When an opportunity is discovered, a **Trade Proposal Card** appears:
- **Proposed Parameters**: Direction (`BUY` / `SELL`), Entry Price, Stop-Loss, Target 1, Target 2, Risk/Reward ratio, and Confidence score.
- **Spoken Audio Pitch**: KitePulse AI synthesizes a concise, natural voice breakdown explaining the institutional rationale.
- **60-Second Countdown**: The proposal automatically expires in 60 seconds if market conditions shift.
- **Voice Command Radar**: Speak aloud `"Approve"` to authorize execution, or `"Reject"` to discard, or simply click the buttons in the UI.

### 6. Managing Active Positions & Trailing SL
- When approved, orders are logged into the immutable database and appear in the **Positions Table**.
- Real-time mark-to-market (MTM) P&L updates every 2 seconds via authenticated WebSocket stream.
- **Automated Square-Off**: The background engine continuously checks live prices against Stop-Loss and Target levels, auto-exiting when barriers are breached.
- **Manual Square-Off**: Click **"Close Position"** anytime to exit immediately at current market price.

### 7. Customizing Instruments
To add or modify tracked symbols, edit external configuration file [`backend/instruments.json`](file:///d:/DEVELOPMENT/android/trading/backend/instruments.json):
```json
{
  "symbol": "TATAMOTORS",
  "kite_symbol": "NSE:TATAMOTORS",
  "tradingsymbol": "TATAMOTORS",
  "exchange": "NSE",
  "lot_size": 1,
  "type": "EQUITY",
  "enabled": true
}
```
No backend code changes are required when updating instruments.

---

## API Reference

### Authentication & Vault
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/auth/status` | Check if vault is initialized and whether session token is valid |
| `POST` | `/api/auth/setup` | One-time master password setup; derives encryption keys |
| `POST` | `/api/auth/login` | Authenticate master password; unlocks secure vault |
| `POST` | `/api/auth/logout` | Revoke session token and lock encrypted vault |
| `GET` | `/api/auth/verify` | Real-time session check & 30-second Kite token verification |

### Market Data & Quotes
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | System health, trading mode, and broker connection status |
| `GET` | `/api/market/quotes` | Live quotes for all 8 tracked symbols from Kite |
| `GET` | `/api/market/candles` | Historical candlestick data with EMA, RSI, VWAP, and ATR |

### Trading Operations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/trade/scan` | Trigger AI quantitative scan on selected symbol |
| `POST` | `/api/trade/approve` | Approve proposal; routes order to Paper engine or Kite LIVE |
| `POST` | `/api/trade/reject` | Reject pending proposal with optional rationale |
| `GET` | `/api/trade/positions` | Active positions with real-time mark-to-market P&L |
| `POST` | `/api/trade/close-position` | Manually exit active position at current LTP |
| `GET` | `/api/trade/orders` | Immutable audit log of all order executions |
| `GET` | `/api/trade/portfolio` | Capital summary, realized/unrealized P&L, win rate |
| `GET` | `/api/trade/history` | Full historical suggestions joined with position outcomes |

### Real-Time Streaming
| Protocol | Endpoint | Description |
| :--- | :--- | :--- |
| `WebSocket` | `/ws/live?token={token}` | Authenticated tick stream broadcasting quotes and P&L updates every 2s |

---

## Resume Highlights & Key Engineering Accomplishments

*For inclusion in Software Engineering, Quantitative Developer, or Full-Stack Engineer resumes:*

- **Event-Driven Trading Architecture**: Designed and implemented an event-driven algorithmic trading platform integrating Zerodha Kite Connect SDK and Google Gemini Generative AI, processing real-time market ticks across NSE equity and derivative contracts.
- **Strategy & Broker Abstraction**: Engineered an extensible broker layer utilizing the Strategy Pattern (`BaseOrderExecutor`), cleanly isolating paper trading simulation from live market execution with zero regressions across 17 automated Pytest suites.
- **Zero-Plaintext Cryptographic Vault**: Architected a secure configuration vault using PBKDF2-HMAC-SHA256 master key derivation and Fernet AES-128 symmetric encryption, eliminating plaintext API secret exposure on disk with sliding-window session management.
- **Risk Management & Low-Latency Execution**: Implemented a two-tier risk engine enforcing strict 1-lot trading incubation constraints, automated 30-second token verification heartbeats, and real-time trailing stop-loss / target auto-square-off triggers.
- **Quantitative Signal Processing**: Developed an intraday indicator pipeline in NumPy and Pandas computing EMA crossovers, Volume Weighted Average Price (VWAP), RSI, and ATR volatility bands, coupled with deterministic fallbacks to guarantee 99.9% uptime during API rate-limits.
- **High-Performance Terminal UI**: Built an institutional dark-theme trading frontend in React 19 and TypeScript, integrating TradingView Lightweight Charts v5 for 60 FPS candlestick rendering, Web Speech hands-free voice execution, and discrete "Office Mode" alerting.
