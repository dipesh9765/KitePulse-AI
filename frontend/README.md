# KitePulse AI — Frontend Quantitative Terminal

A modern, high-frequency algorithmic trading terminal built with **React 19**, **TypeScript**, and **Vite**, featuring hardware-accelerated financial charting, real-time WebSocket tick streaming, Web Speech hands-free voice execution, and discrete audio cues.

---

## Architectural Highlights

- **React 19 & TypeScript Strict Mode**: Strong typing across all market domain schemas (`Quote`, `Candle`, `TradeProposal`, `Position`, `OrderRecord`, `PortfolioSummary`).
- **TradingView Lightweight Charts v5**: Canvas-accelerated, 60 FPS candlestick charts supporting multi-timeframe OHLCV bars, overlaid with 9/21/50 EMA ribbons, volume histograms, and VWAP bands.
- **WebSocket Streaming (`useRef` + Reconnect Policy)**: Subscribes to `/ws/live` tick stream, synchronizing live price updates, floating unrealized P&L, and portfolio summaries mark-to-market.
- **Hands-Free Voice Execution**: Integrates browser Web Speech API for voice-driven radar scanning, pitch reading, and verbal trade confirmations (`"Approve"`, `"Reject"`, `"Scan"`).
- **Zero-Plaintext Security Barrier**: Integrates with backend PBKDF2/Fernet encrypted vault via `AuthGatekeeper` and Bearer session tokens.
- **Discrete "Office Mode"**: Mutes loud audio synthesis in favor of gentle, subtle Web Audio synthesizer chimes for privacy.

---

## Component Architecture

```
frontend/src/
├── components/
│   ├── AuthGatekeeper.tsx       # Master password login & initial vault setup modal
│   ├── Header.tsx               # System telemetry, active mode switch (PAPER / LIVE), and P&L pill
│   ├── HistoryTracker.tsx       # Unified historical trade suggestion and linked position table
│   ├── PositionsTable.tsx       # Real-time mark-to-market positions with manual square-off
│   ├── SettingsModal.tsx        # Vault credentials manager, Kite OAuth login, and webhook testing
│   ├── TradeProposalCard.tsx    # 60s countdown proposal approval card with risk-reward metrics
│   ├── TradingChart.tsx         # TradingView Lightweight Charts canvas with EMA & VWAP overlays
│   ├── VoiceRadar.tsx           # Visual speech synthesis and audio radar HUD
│   └── Watchlist.tsx            # NSE index and high-liquidity stock selector
├── services/
│   ├── api.ts                   # REST API client with Bearer token authentication
│   ├── notifications.ts         # Browser desktop notification service
│   ├── sound.ts                 # Web Audio API procedural sound synthesizer
│   └── speech.ts                # Web Speech recognition and speech synthesis service
├── types/
│   └── index.ts                 # Comprehensive TSDoc schemas and domain interfaces
├── App.tsx                      # Root application layout, WebSocket listener, keyboard shortcuts
└── index.css                    # Cyberpunk / institutional dark theme design system
```

---

## Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `A` or `Enter` | **Approve Proposal** | Confirms pending proposal and routes order |
| `R` or `Escape` | **Reject Proposal** | Declines pending proposal |
| `S` | **Scan Symbol** | Triggers AI quantitative scan on selected symbol |

---

## Available Scripts

```bash
# Start local development server (Vite HMR)
npm run dev

# Run TypeScript check and production build
npm run build

# Run Oxlint high-performance linter
npm run lint

# Preview production build locally
npm run preview
```
