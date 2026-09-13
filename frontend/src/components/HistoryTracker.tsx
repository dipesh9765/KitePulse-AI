import React, { useState } from "react";
import { ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight, LogOut } from "lucide-react";
import type { HistoryItem } from "../types";

interface HistoryTrackerProps {
    history: HistoryItem[];
    onClosePosition: (positionId: string) => void;
    onRefreshHistory: () => void;
}

export const HistoryTracker: React.FC<HistoryTrackerProps> = ({
    history,
    onClosePosition
}) => {
    const [filter, setFilter] = useState<"ALL" | "APPROVED" | "OPEN" | "CLOSED" | "REJECTED">("ALL");
    const [expandedId, setExpandedId] = useState<string | null>(null);

    const filteredHistory = history.filter((item) => {
        if (filter === "ALL") return true;
        if (filter === "OPEN") return item.overall_status === "OPEN";
        if (filter === "CLOSED") return item.overall_status === "CLOSED";
        if (filter === "APPROVED") return item.overall_status === "OPEN" || item.overall_status === "CLOSED" || item.overall_status === "APPROVED";
        if (filter === "REJECTED") return item.overall_status === "REJECTED";
        return true;
    });

    const toggleExpand = (proposalId: string) => {
        setExpandedId(expandedId === proposalId ? null : proposalId);
    };

    return (
        <div className="glass-panel" style={{ padding: "18px" }}>
            {/* Header & Filter Tabs */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                <div>
                    <h3 style={{ fontSize: "16px", fontWeight: 700 }}>Signals & Order History Tracker</h3>
                    <div style={{ fontSize: "11px", color: "var(--text-dim)" }}>
                        Persisted in SQLite Database • Track real-time progress, SL, targets, and exit anytime
                    </div>
                </div>

                {/* Filters */}
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {(["ALL", "OPEN", "CLOSED", "REJECTED"] as const).map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            style={{
                                background: filter === f ? "rgba(0, 240, 255, 0.15)" : "rgba(255, 255, 255, 0.04)",
                                color: filter === f ? "var(--color-cyan)" : "var(--text-muted)",
                                border: `1px solid ${filter === f ? "var(--border-glow)" : "var(--border-color)"}`,
                                borderRadius: "6px",
                                padding: "4px 10px",
                                fontSize: "11px",
                                fontWeight: 600,
                                cursor: "pointer"
                            }}
                        >
                            {f === "ALL" ? `All (${history.length})` : f}
                        </button>
                    ))}
                </div>
            </div>

            {/* History Items List */}
            {filteredHistory.length === 0 ? (
                <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--text-muted)", fontSize: "13px" }}>
                    No records match this filter. Trigger a scan above to generate signals.
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {filteredHistory.map((item) => {
                        const isExpanded = expandedId === item.proposal_id;
                        const isBull = item.direction === "BULLISH";
                        const isOpen = item.overall_status === "OPEN";
                        const isClosed = item.overall_status === "CLOSED";
                        const isRejected = item.overall_status === "REJECTED";

                        const pnl = isOpen ? (item.unrealized_pnl || 0) : (item.realized_pnl || 0);
                        const isProfit = pnl >= 0;

                        // Compute Progress towards Target or SL
                        const cur = item.current_ltp || item.buy_price || item.entry_price;
                        const entry = item.buy_price || item.entry_price;
                        const sl = item.stop_loss;
                        const tp = item.target_1;

                        const totalRange = Math.abs(tp - sl) || 1;
                        const progressPct = Math.min(100, Math.max(0, ((cur - sl) / totalRange) * 100));

                        return (
                            <div
                                key={item.proposal_id}
                                style={{
                                    borderRadius: "10px",
                                    background: isExpanded ? "rgba(255, 255, 255, 0.05)" : "rgba(255, 255, 255, 0.02)",
                                    border: `1px solid ${isOpen ? "rgba(0, 230, 153, 0.3)" : isExpanded ? "var(--border-glow)" : "var(--border-color)"}`,
                                    overflow: "hidden",
                                    transition: "all 0.2s ease"
                                }}
                            >
                                {/* Summary Row (Clickable) */}
                                <div
                                    onClick={() => toggleExpand(item.proposal_id)}
                                    style={{
                                        padding: "12px 16px",
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        cursor: "pointer",
                                        userSelect: "none"
                                    }}
                                >
                                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                                        {/* Direction Badge */}
                                        <span
                                            style={{
                                                padding: "3px 8px",
                                                borderRadius: "5px",
                                                fontSize: "11px",
                                                fontWeight: 700,
                                                background: isBull ? "rgba(0, 230, 153, 0.15)" : "rgba(255, 51, 102, 0.15)",
                                                color: isBull ? "var(--color-bull)" : "var(--color-bear)",
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "4px"
                                            }}
                                        >
                                            {isBull ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                            {item.signal_type.replace("_", " ")}
                                        </span>

                                        <div>
                                            <div style={{ fontWeight: 700, fontSize: "14px" }}>{item.instrument}</div>
                                            <div style={{ fontSize: "11px", color: "var(--text-dim)" }}>
                                                {item.suggested_at} • Entry: ₹{item.entry_price}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Status & Realized Net Gain */}
                                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                                        {isOpen && (
                                            <div style={{ textAlign: "right" }}>
                                                <div style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 700, color: item.mode === "PAPER" ? "var(--color-cyan)" : "var(--color-bull)", background: item.mode === "PAPER" ? "rgba(0, 242, 254, 0.15)" : "rgba(0, 230, 153, 0.15)", padding: "2px 8px", borderRadius: "12px" }}>
                                                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: item.mode === "PAPER" ? "var(--color-cyan)" : "var(--color-bull)" }} className="radar-active" />
                                                    {item.mode === "PAPER" ? "SANDBOX OPEN" : "LIVE OPEN"}
                                                </div>
                                                <div className="font-mono" style={{ fontSize: "13px", fontWeight: 700, color: isProfit ? "var(--color-bull)" : "var(--color-bear)", marginTop: "2px" }}>
                                                    {isProfit ? "+" : ""}₹{pnl.toFixed(2)} ({isProfit ? "+" : ""}{item.pnl_pct || 0}%)
                                                </div>
                                            </div>
                                        )}

                                        {isClosed && (
                                            <div style={{ textAlign: "right" }}>
                                                <div style={{ fontSize: "11px", color: "var(--text-dim)", textTransform: "uppercase" }}>
                                                    Net Gain
                                                </div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700, color: isProfit ? "var(--color-bull)" : "var(--color-bear)" }}>
                                                    {isProfit ? "+" : ""}₹{pnl.toFixed(2)}
                                                </div>
                                            </div>
                                        )}

                                        {isRejected && (
                                            <span style={{ fontSize: "11px", color: "var(--text-dim)", background: "rgba(255, 255, 255, 0.05)", padding: "3px 8px", borderRadius: "6px" }}>
                                                REJECTED
                                            </span>
                                        )}

                                        {item.overall_status === "PENDING" && (
                                            <span style={{ fontSize: "11px", color: "var(--color-amber)", background: "rgba(255, 183, 3, 0.12)", padding: "3px 8px", borderRadius: "6px" }}>
                                                PENDING
                                            </span>
                                        )}

                                        {isExpanded ? <ChevronUp size={16} color="var(--text-dim)" /> : <ChevronDown size={16} color="var(--text-dim)" />}
                                    </div>
                                </div>

                                {/* Expanded Real-Time Tracker */}
                                {isExpanded && (
                                    <div style={{ padding: "16px", borderTop: "1px solid var(--border-color)", background: "rgba(0, 0, 0, 0.25)" }}>
                                        {/* Visual Target & Stop-Loss Tracker Bar */}
                                        <div style={{ marginBottom: "16px" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "6px", fontFamily: "var(--font-mono)" }}>
                                                <span style={{ color: "var(--color-bear)", fontWeight: 600 }}>🛑 SL: ₹{item.stop_loss}</span>
                                                <span style={{ color: "var(--color-cyan)", fontWeight: 700 }}>
                                                    Current LTP: ₹{cur.toFixed(2)}
                                                </span>
                                                <span style={{ color: "var(--color-bull)", fontWeight: 600 }}>🎯 Target 1: ₹{item.target_1}</span>
                                            </div>

                                            {/* Progress bar */}
                                            <div style={{ width: "100%", height: "8px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", overflow: "hidden", position: "relative" }}>
                                                <div
                                                    style={{
                                                        width: `${progressPct}%`,
                                                        height: "100%",
                                                        background: isProfit
                                                            ? "linear-gradient(90deg, #ffb703 0%, #00e699 100%)"
                                                            : "linear-gradient(90deg, #ff3366 0%, #ffb703 100%)",
                                                        transition: "width 0.3s ease"
                                                    }}
                                                />
                                            </div>
                                        </div>

                                        {/* Metrics Grid */}
                                        <div style={{
                                            display: "grid",
                                            gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
                                            gap: "10px",
                                            marginBottom: "14px"
                                        }}>
                                            <div className="glass-panel" style={{ padding: "8px 12px", borderRadius: "8px" }}>
                                                <div style={{ fontSize: "10px", color: "var(--text-dim)" }}>BUY / ENTRY</div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700 }}>₹{entry.toFixed(2)}</div>
                                            </div>
                                            <div className="glass-panel" style={{ padding: "8px 12px", borderRadius: "8px" }}>
                                                <div style={{ fontSize: "10px", color: "var(--text-dim)" }}>CURRENT LTP</div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-cyan)" }}>₹{cur.toFixed(2)}</div>
                                            </div>
                                            <div className="glass-panel" style={{ padding: "8px 12px", borderRadius: "8px" }}>
                                                <div style={{ fontSize: "10px", color: "var(--color-bear)" }}>STOP LOSS</div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-bear)" }}>₹{item.stop_loss}</div>
                                            </div>
                                            <div className="glass-panel" style={{ padding: "8px 12px", borderRadius: "8px" }}>
                                                <div style={{ fontSize: "10px", color: "var(--color-bull)" }}>TARGET 1</div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-bull)" }}>₹{item.target_1}</div>
                                            </div>
                                            <div className="glass-panel" style={{ padding: "8px 12px", borderRadius: "8px" }}>
                                                <div style={{ fontSize: "10px", color: isProfit ? "var(--color-bull)" : "var(--color-bear)" }}>
                                                    {isOpen ? "UNREALIZED P&L" : "NET GAIN"}
                                                </div>
                                                <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700, color: isProfit ? "var(--color-bull)" : "var(--color-bear)" }}>
                                                    {isProfit ? "+" : ""}₹{pnl.toFixed(2)}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Metadata & Technical Rationale */}
                                        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                                            {item.close_reason && (
                                                <div style={{ marginBottom: "4px", color: "var(--text-main)" }}>
                                                    <strong>Exit Reason:</strong> <span style={{ color: item.close_reason.includes("TARGET") ? "var(--color-bull)" : "var(--color-amber)" }}>{item.close_reason.replace("_", " ")}</span> ({item.closed_at})
                                                </div>
                                            )}
                                            <div><strong>AI Rationale:</strong> {item.technical_rationale || "EMA alignment and VWAP confirmation."}</div>
                                        </div>

                                        {/* Immediate Exit Button for Open Trades */}
                                        {isOpen && item.position_id && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onClosePosition(item.position_id!);
                                                }}
                                                className="btn btn-bear"
                                                style={{ width: "100%", padding: "10px", fontSize: "13px" }}
                                            >
                                                <LogOut size={16} />
                                                <span>Exit Position Immediately (Sell @ ₹{cur.toFixed(2)})</span>
                                            </button>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
