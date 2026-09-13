import React, { useRef, useEffect } from "react";
import { ShieldAlert, AlertTriangle, RefreshCw, Settings, BarChart2 } from "lucide-react";
import type { Candle, TradeProposal } from "../types";

interface TradingChartProps {
    symbol: string;
    candles: Candle[];
    proposal?: TradeProposal | null;
    isLoading?: boolean;
    chartStatus?: string | null;
    errorMessage?: string | null;
    kiteConnected?: boolean;
    onOpenSettings?: () => void;
    onRetry?: () => void;
}

export const TradingChart: React.FC<TradingChartProps> = ({
    symbol,
    candles,
    proposal,
    isLoading = false,
    chartStatus = null,
    errorMessage = null,
    kiteConnected = false,
    onOpenSettings,
    onRetry
}) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || candles.length === 0) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Handle high DPI
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;
        const padding = { top: 30, right: 65, bottom: 30, left: 10 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Clear
        ctx.clearRect(0, 0, width, height);

        // Calculate Price Extents
        let minPrice = Math.min(...candles.map((c) => c.low));
        let maxPrice = Math.max(...candles.map((c) => c.high));

        // Include proposal levels if active
        if (proposal && proposal.symbol === symbol) {
            minPrice = Math.min(minPrice, proposal.stop_loss, proposal.entry_price);
            maxPrice = Math.max(maxPrice, proposal.target_1, proposal.entry_price);
        }

        const priceBuffer = (maxPrice - minPrice) * 0.08 || 1;
        minPrice -= priceBuffer;
        maxPrice += priceBuffer;
        const priceRange = maxPrice - minPrice;

        const getY = (price: number) => padding.top + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
        const candleWidth = Math.max(2, chartWidth / candles.length - 3);

        // Grid lines (Horizontal)
        ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        ctx.lineWidth = 1;
        const numGridLines = 5;
        for (let i = 0; i <= numGridLines; i++) {
            const y = padding.top + (chartHeight / numGridLines) * i;
            const price = maxPrice - (priceRange / numGridLines) * i;

            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();

            // Price label on right axis
            ctx.fillStyle = "#64748b";
            ctx.font = "10px 'JetBrains Mono', monospace";
            ctx.textAlign = "left";
            ctx.fillText(`₹${price.toFixed(1)}`, width - padding.right + 8, y + 3);
        }

        // Draw Volume Bars at bottom
        const maxVolume = Math.max(...candles.map((c) => c.volume), 1);
        const volumeHeightMax = chartHeight * 0.2;

        candles.forEach((candle, idx) => {
            const x = padding.left + idx * (chartWidth / candles.length) + (chartWidth / candles.length - candleWidth) / 2;
            const isBullish = candle.close >= candle.open;
            const vHeight = (candle.volume / maxVolume) * volumeHeightMax;

            ctx.fillStyle = isBullish ? "rgba(0, 230, 153, 0.15)" : "rgba(255, 51, 102, 0.15)";
            ctx.fillRect(x, padding.top + chartHeight - vHeight, candleWidth, vHeight);
        });

        // Draw Candlesticks
        candles.forEach((candle, idx) => {
            const x = padding.left + idx * (chartWidth / candles.length) + (chartWidth / candles.length - candleWidth) / 2;
            const centerX = x + candleWidth / 2;
            const isBullish = candle.close >= candle.open;

            const openY = getY(candle.open);
            const closeY = getY(candle.close);
            const highY = getY(candle.high);
            const lowY = getY(candle.low);

            const color = isBullish ? "#00e699" : "#ff3366";
            ctx.strokeStyle = color;
            ctx.fillStyle = color;

            // Wick
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(centerX, highY);
            ctx.lineTo(centerX, lowY);
            ctx.stroke();

            // Body
            const bodyY = Math.min(openY, closeY);
            const bodyH = Math.max(Math.abs(closeY - openY), 1.5);
            ctx.fillRect(x, bodyY, candleWidth, bodyH);
        });

        // Draw Indicator Lines: EMA 9 (Cyan), EMA 21 (Amber), VWAP (Purple)
        const drawLine = (key: keyof Candle, strokeColor: string, isDashed = false) => {
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 1.5;
            if (isDashed) {
                ctx.setLineDash([4, 4]);
            } else {
                ctx.setLineDash([]);
            }

            ctx.beginPath();
            let started = false;
            candles.forEach((c, idx) => {
                const val = c[key];
                if (typeof val === "number" && !isNaN(val)) {
                    const x = padding.left + idx * (chartWidth / candles.length) + chartWidth / candles.length / 2;
                    const y = getY(val);
                    if (!started) {
                        ctx.moveTo(x, y);
                        started = true;
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
            });
            ctx.stroke();
            ctx.setLineDash([]);
        };

        drawLine("ema_9", "#00f0ff");
        drawLine("ema_21", "#ffb703");
        drawLine("vwap", "#c084fc", true);

        // Draw Proposal Price Overlay Lines (if symbol matches)
        if (proposal && proposal.symbol === symbol) {
            // Entry Line
            ctx.setLineDash([6, 3]);
            ctx.lineWidth = 1.5;

            // Stop Loss (Red)
            const slY = getY(proposal.stop_loss);
            ctx.strokeStyle = "#ff3366";
            ctx.beginPath();
            ctx.moveTo(padding.left, slY);
            ctx.lineTo(width - padding.right, slY);
            ctx.stroke();
            ctx.fillStyle = "#ff3366";
            ctx.font = "10px 'JetBrains Mono', monospace";
            ctx.fillText(`SL: ₹${proposal.stop_loss}`, width - padding.right + 4, slY - 3);

            // Target 1 (Green)
            const tY = getY(proposal.target_1);
            ctx.strokeStyle = "#00e699";
            ctx.beginPath();
            ctx.moveTo(padding.left, tY);
            ctx.lineTo(width - padding.right, tY);
            ctx.stroke();
            ctx.fillStyle = "#00e699";
            ctx.fillText(`TP: ₹${proposal.target_1}`, width - padding.right + 4, tY - 3);

            // Entry Price (Gold)
            const entY = getY(proposal.entry_price);
            ctx.strokeStyle = "#ffb703";
            ctx.beginPath();
            ctx.moveTo(padding.left, entY);
            ctx.lineTo(width - padding.right, entY);
            ctx.stroke();
            ctx.fillStyle = "#ffb703";
            ctx.fillText(`ENTRY: ₹${proposal.entry_price}`, width - padding.right + 4, entY - 3);

            ctx.setLineDash([]);
        }

    }, [candles, proposal, symbol]);

    return (
        <div className="glass-panel" style={{ padding: "18px", marginBottom: "20px" }}>
            {/* Chart Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 700 }}>{symbol} Real-Time Chart</h3>
                    <span style={{ fontSize: "12px", color: "var(--text-dim)" }}>5-Min Intraday Candles</span>
                </div>

                {/* Indicator Legend */}
                <div style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: "11px", fontFamily: "var(--font-mono)" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#00f0ff" }}>
                        <span style={{ width: "8px", height: "2px", backgroundColor: "#00f0ff" }}></span> EMA 9
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#ffb703" }}>
                        <span style={{ width: "8px", height: "2px", backgroundColor: "#ffb703" }}></span> EMA 21
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#c084fc" }}>
                        <span style={{ width: "8px", height: "2px", backgroundColor: "#c084fc", borderBottom: "1px dashed" }}></span> VWAP
                    </span>
                </div>
            </div>

            {/* Canvas */}
            <div style={{ width: "100%", height: "320px", position: "relative", overflow: "hidden", borderRadius: "8px" }}>
                <canvas
                    ref={canvasRef}
                    style={{ width: "100%", height: "100%", display: "block" }}
                />
                {isLoading && (
                    <div
                        style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: "rgba(10, 15, 26, 0.82)",
                            backdropFilter: "blur(6px)",
                            WebkitBackdropFilter: "blur(6px)",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "14px",
                            zIndex: 10,
                            animation: "fadeIn 0.2s ease"
                        }}
                    >
                        <div
                            style={{
                                width: "40px",
                                height: "40px",
                                border: "3px solid rgba(0, 240, 255, 0.15)",
                                borderTop: "3px solid #00f0ff",
                                borderRadius: "50%",
                                animation: "spin 0.75s linear infinite",
                                boxShadow: "0 0 15px rgba(0, 240, 255, 0.3)"
                            }}
                        />
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "5px", textAlign: "center" }}>
                            <span style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.4px" }}>
                                Loading live chart data for {symbol}...
                            </span>
                            <span style={{ fontSize: "11px", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                                Streaming real-time 5-min candles & technical indicators
                            </span>
                        </div>
                    </div>
                )}

                {/* Diagnostic Status Screen when candles are not loaded */}
                {!isLoading && candles.length === 0 && (
                    <div
                        style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: "rgba(10, 15, 26, 0.94)",
                            backdropFilter: "blur(8px)",
                            WebkitBackdropFilter: "blur(8px)",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "24px",
                            textAlign: "center",
                            zIndex: 5
                        }}
                    >
                        {/* Condition A: Kite session is not initialized or not connected */}
                        {(!kiteConnected || chartStatus === "KITE_SESSION_NOT_INITIALIZED") && (
                            <div style={{ maxWidth: "480px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                                <div style={{ background: "rgba(255, 179, 0, 0.15)", padding: "14px", borderRadius: "16px", border: "1px solid rgba(255, 179, 0, 0.3)" }}>
                                    <ShieldAlert size={36} color="#ffb300" />
                                </div>
                                <div>
                                    <h4 style={{ fontSize: "16px", fontWeight: 700, color: "#ffb300", marginBottom: "6px" }}>
                                        Zerodha Kite Session Not Initialized
                                    </h4>
                                    <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5 }}>
                                        Real-time candlestick charts cannot load without an authenticated Zerodha Kite session.
                                    </p>
                                    <p style={{ fontSize: "11.5px", color: "#94a3b8", marginTop: "6px", fontFamily: "var(--font-mono)" }}>
                                        {errorMessage || "Please configure your Kite API credentials and authenticate today's daily session in Settings."}
                                    </p>
                                </div>
                                {onOpenSettings && (
                                    <button
                                        onClick={onOpenSettings}
                                        className="btn btn-primary"
                                        style={{
                                            marginTop: "6px",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "8px",
                                            padding: "8px 18px",
                                            fontSize: "13px",
                                            background: "#ffb300",
                                            color: "#0c111d",
                                            borderColor: "#ffb300"
                                        }}
                                    >
                                        <Settings size={15} />
                                        Open Settings to Authenticate
                                    </button>
                                )}
                            </div>
                        )}

                        {/* Condition B: Kite is connected, but Zerodha Kite returned an error from their side */}
                        {kiteConnected && chartStatus === "KITE_BROKER_ERROR" && (
                            <div style={{ maxWidth: "520px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                                <div style={{ background: "rgba(255, 51, 102, 0.15)", padding: "14px", borderRadius: "16px", border: "1px solid rgba(255, 51, 102, 0.35)" }}>
                                    <AlertTriangle size={36} color="#ff3366" />
                                </div>
                                <div>
                                    <h4 style={{ fontSize: "16px", fontWeight: 700, color: "#ff3366", marginBottom: "6px" }}>
                                        Zerodha Kite Broker Error
                                    </h4>
                                    <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5 }}>
                                        Kite session is active, but Zerodha Kite returned an error while fetching 5-minute candles for <strong>{symbol}</strong>:
                                    </p>
                                    <div
                                        style={{
                                            marginTop: "8px",
                                            background: "rgba(0, 0, 0, 0.45)",
                                            border: "1px solid rgba(255, 51, 102, 0.3)",
                                            padding: "10px 14px",
                                            borderRadius: "8px",
                                            fontSize: "12px",
                                            color: "#fca5a5",
                                            fontFamily: "var(--font-mono)",
                                            wordBreak: "break-word"
                                        }}
                                    >
                                        {errorMessage || "Historical data API call failed or timed out from broker."}
                                    </div>
                                    <p style={{ fontSize: "11px", color: "#94a3b8", marginTop: "8px" }}>
                                        💡 Note: Zerodha requires an active <strong>Kite Connect Historical Data</strong> add-on subscription (₹2,000/mo) on your developer app to stream candlestick charts.
                                    </p>
                                </div>
                                {onRetry && (
                                    <button
                                        onClick={onRetry}
                                        className="btn btn-secondary"
                                        style={{
                                            marginTop: "4px",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "8px",
                                            padding: "8px 16px",
                                            fontSize: "13px"
                                        }}
                                    >
                                        <RefreshCw size={14} />
                                        Retry Fetching Candles
                                    </button>
                                )}
                            </div>
                        )}

                        {/* Condition C: Kite is connected, but no intraday candles returned (market closed, weekend, or holiday) */}
                        {kiteConnected && chartStatus !== "KITE_SESSION_NOT_INITIALIZED" && chartStatus !== "KITE_BROKER_ERROR" && (
                            <div style={{ maxWidth: "460px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                                <div style={{ background: "rgba(0, 240, 255, 0.12)", padding: "14px", borderRadius: "16px", border: "1px solid rgba(0, 240, 255, 0.25)" }}>
                                    <BarChart2 size={36} color="#00f0ff" />
                                </div>
                                <div>
                                    <h4 style={{ fontSize: "16px", fontWeight: 700, color: "#00f0ff", marginBottom: "6px" }}>
                                        No Market Candles Available for {symbol}
                                    </h4>
                                    <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5 }}>
                                        {errorMessage || "No recent 5-minute candlestick data was returned by Zerodha Kite for this instrument. Market may be closed or trading is halted."}
                                    </p>
                                </div>
                                {onRetry && (
                                    <button
                                        onClick={onRetry}
                                        className="btn btn-secondary"
                                        style={{
                                            marginTop: "4px",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "8px",
                                            padding: "8px 16px",
                                            fontSize: "13px"
                                        }}
                                    >
                                        <RefreshCw size={14} />
                                        Refresh Candles
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
