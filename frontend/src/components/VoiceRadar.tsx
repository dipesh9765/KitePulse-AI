import React from "react";
import { Mic, Volume2, MessageSquare, Briefcase, Keyboard, CheckCircle, XCircle } from "lucide-react";

interface VoiceRadarProps {
  isListening: boolean;
  transcript: string;
  isSpeaking: boolean;
  onSimulateCommand: (cmdText: string) => void;
  officeMode: boolean;
}

export const VoiceRadar: React.FC<VoiceRadarProps> = ({
  isListening,
  transcript,
  isSpeaking,
  onSimulateCommand,
  officeMode
}) => {
  if (officeMode) {
    return (
      <div className="glass-panel" style={{
        padding: "12px 20px",
        marginBottom: "20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "14px",
        background: "rgba(16, 22, 34, 0.9)",
        borderColor: "rgba(0, 240, 255, 0.2)"
      }}>
        {/* Office Silent Mode Indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "36px",
            height: "36px",
            borderRadius: "50%",
            background: "rgba(0, 240, 255, 0.12)",
            border: "1px solid var(--border-glow)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}>
            <Briefcase size={18} color="var(--color-cyan)" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--color-cyan)" }}>
                Office Silent Mode Active
              </span>
              <span style={{ fontSize: "10px", background: "rgba(0, 230, 153, 0.15)", color: "var(--color-bull)", padding: "1px 6px", borderRadius: "4px" }}>
                DISCREET
              </span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              Voice is muted. Notifications will pop up as Windows alerts, Telegram, or Discord.
            </div>
          </div>
        </div>

        {/* Quick Keyboard Hotkeys Pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(0, 0, 0, 0.35)",
            padding: "5px 12px",
            borderRadius: "8px",
            border: "1px solid var(--border-color)",
            fontSize: "12px"
          }}>
            <Keyboard size={14} color="var(--text-dim)" />
            <span style={{ color: "var(--text-dim)" }}>Shortcuts:</span>
            <span style={{ color: "var(--color-bull)", fontWeight: 700 }}>[A] / [Enter]</span> Approve
            <span style={{ color: "var(--text-dim)" }}>•</span>
            <span style={{ color: "var(--color-bear)", fontWeight: 700 }}>[R] / [Esc]</span> Reject
            <span style={{ color: "var(--text-dim)" }}>•</span>
            <span style={{ color: "var(--color-cyan)", fontWeight: 700 }}>[S]</span> Scan
          </div>

          <div style={{ display: "flex", gap: "6px" }}>
            <button
              onClick={() => onSimulateCommand("approve")}
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "11px", borderColor: "rgba(0, 230, 153, 0.3)", color: "var(--color-bull)" }}
              title="Quick Approve Trade (Key: A)"
            >
              <CheckCircle size={12} /> Approve
            </button>
            <button
              onClick={() => onSimulateCommand("reject")}
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "11px", borderColor: "rgba(255, 51, 102, 0.3)", color: "var(--color-bear)" }}
              title="Quick Reject Trade (Key: R)"
            >
              <XCircle size={12} /> Reject
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Voice Active Radar View
  return (
    <div className="glass-panel" style={{ padding: "16px 20px", marginBottom: "20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
      {/* Visual radar & status */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div
            className={isListening ? "radar-active" : ""}
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              background: isSpeaking
                ? "linear-gradient(135deg, #a855f7 0%, #6366f1 100%)"
                : isListening
                ? "linear-gradient(135deg, #00f0ff 0%, #0088ff 100%)"
                : "rgba(255, 255, 255, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.3s ease"
            }}
          >
            {isSpeaking ? (
              <Volume2 size={22} color="#ffffff" />
            ) : (
              <Mic size={22} color={isListening ? "#001020" : "var(--text-muted)"} />
            )}
          </div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-main)" }}>
              {isSpeaking ? "AI Co-Pilot is Speaking..." : isListening ? "Verbal Trading Radar Active" : "Voice Listening Standby"}
            </span>
            {isSpeaking && (
              <div className="sound-wave">
                <div className="sound-bar" style={{ backgroundColor: "#a855f7" }} />
                <div className="sound-bar" style={{ backgroundColor: "#a855f7" }} />
                <div className="sound-bar" style={{ backgroundColor: "#a855f7" }} />
                <div className="sound-bar" style={{ backgroundColor: "#a855f7" }} />
                <div className="sound-bar" style={{ backgroundColor: "#a855f7" }} />
              </div>
            )}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
            Speak into your mic: <span style={{ color: "var(--color-bull)", fontWeight: 600 }}>"Approve"</span> to confirm trade, or <span style={{ color: "var(--color-bear)", fontWeight: 600 }}>"Reject"</span> to dismiss.
          </div>
        </div>
      </div>

      {/* Transcript feedback box */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {transcript && (
          <div style={{
            background: "rgba(0, 0, 0, 0.4)",
            border: "1px solid var(--border-glow)",
            borderRadius: "8px",
            padding: "6px 14px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "13px",
            color: "var(--color-cyan)"
          }}>
            <MessageSquare size={14} />
            <span>Heard: <em>"{transcript}"</em></span>
          </div>
        )}

        {/* Quick Voice simulation buttons */}
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            onClick={() => onSimulateCommand("approve")}
            className="btn btn-secondary"
            style={{ padding: "5px 10px", fontSize: "11px", borderColor: "rgba(0, 230, 153, 0.3)", color: "var(--color-bull)" }}
            title="Simulate speaking 'Approve'"
          >
            Voice: "Approve"
          </button>
          <button
            onClick={() => onSimulateCommand("reject")}
            className="btn btn-secondary"
            style={{ padding: "5px 10px", fontSize: "11px", borderColor: "rgba(255, 51, 102, 0.3)", color: "var(--color-bear)" }}
            title="Simulate speaking 'Reject'"
          >
            Voice: "Reject"
          </button>
          <button
            onClick={() => onSimulateCommand("scan nifty")}
            className="btn btn-secondary"
            style={{ padding: "5px 10px", fontSize: "11px", borderColor: "rgba(0, 240, 255, 0.3)", color: "var(--color-cyan)" }}
            title="Simulate speaking 'Scan Nifty'"
          >
            Voice: "Scan"
          </button>
        </div>
      </div>
    </div>
  );
};
