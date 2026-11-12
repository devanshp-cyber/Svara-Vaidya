import { useState, useRef, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";

// ─── Semantic Theme Colors & Helpers ─────────────────────────────────────────
const THEME = {
  bg: "#FAF6F0",
  cardBg: "#FFFFFF",
  cardBorder: "#EAE2D6",
  textPrimary: "#1C1917",
  textSecondary: "#57534E",
  textMuted: "#8A817C",
  accentOrange: "#EA580C",
  accentAmber: "#D97706",
  accentYellow: "#F59E0B",
  emerald: "#059669",
  emeraldBg: "#ECFDF5",
  emeraldBorder: "#A7F3D0",
  amber: "#D97706",
  amberBg: "#FFFBEB",
  amberBorder: "#FDE68A",
  crimson: "#DC2626",
  crimsonBg: "#FEF2F2",
  crimsonBorder: "#FECACA",
};

const CANONICAL_WORD_ACCENTS = [
  "Udātta ↗ (High Pitch)",
  "Svarita ⌒ (Falling Pitch)",
  "Udātta ↗ (High Pitch)",
  "Anudātta _ (Low Pitch)",
  "Udātta ↗ (High Pitch)",
  "Svarita ⌒ (Falling Pitch)",
  "Udātta ↗ (High Pitch)",
  "Svarita ⌒ (Falling Pitch)",
];

const getScoreColor = (score) => {
  const s = Math.round(score || 0);
  if (s >= 80) return "#059669"; // Emerald (Mastery)
  if (s >= 60) return "#D97706"; // Amber (Proficient)
  if (s >= 45) return "#EA580C"; // Saffron Orange (Developing)
  return "#DC2626";              // Crimson (Needs Guidance)
};

const gradeEmoji = (score) => {
  if (score >= 85) return "✓";
  if (score >= 70) return "◐";
  if (score >= 45) return "△";
  return "✗";
};

// ─── Score Bar Component (Light Theme) ───────────────────────────────────────
const ScoreBar = ({ label, score, sublabel, height = 7 }) => {
  const numScore = typeof score === "number" ? Math.round(score) : 0;
  const col = getScoreColor(numScore);
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
        <span style={{ fontSize: 13, color: THEME.textPrimary, fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono', monospace" }}>
          {numScore}% <span style={{ fontSize: 11 }}>{gradeEmoji(numScore)}</span>
        </span>
      </div>
      <div style={{ background: "#EAE2D6", borderRadius: 99, height, overflow: "hidden" }}>
        <div
          style={{
            width: `${Math.min(numScore, 100)}%`,
            height: "100%",
            borderRadius: 99,
            background: `linear-gradient(90deg, ${col}CC, ${col})`,
            transition: "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />
      </div>
      {sublabel && <div style={{ fontSize: 11, color: THEME.textMuted, marginTop: 4 }}>{sublabel}</div>}
    </div>
  );
};

const formatGrade = (g) => {
  if (!g) return "";
  if (g.includes("(")) return g;
  const map = {
    Uttama: "Uttama (Excellent)",
    Madhyama: "Madhyama (Intermediate)",
    Ādi: "Ādi (Foundation)",
    Adi: "Ādi (Foundation)",
    Prārambhika: "Prārambhika (Beginner)",
    Prarambhika: "Prārambhika (Beginner)",
  };
  return map[g] || g;
};

const formatAccentWithSymbol = (acc) => {
  if (!acc) return "Sādhāraṇa ⁓ (Neutral)";
  const a = acc.toLowerCase();
  if (a.includes("udatta")) return "Udātta ↗ (High Pitch)";
  if (a.includes("anudatta")) return "Anudātta _ (Low Pitch)";
  if (a.includes("svarita")) return "Svarita ⌒ (Falling Pitch)";
  return "Sādhāraṇa ⁓ (Neutral)";
};

const formatShapeWithSymbol = (shape) => {
  if (!shape) return "Flat →";
  const s = shape.toLowerCase();
  if (s.includes("rising")) return "Rising ↗";
  if (s.includes("falling")) return "Falling ↘";
  if (s.includes("circumflex")) return "Circumflex ⌒";
  if (s.includes("flat")) return "Flat →";
  return shape;
};

// ─── SVG Radial Resonance Gauge (Light Theme) ────────────────────────────────
const RadialGauge = ({ score, size = 180, grade = "" }) => {
  const numScore = Math.round(score || 0);
  const radius = (size - 26) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (Math.min(numScore, 100) / 100) * circumference;
  const color = getScoreColor(numScore);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#EAE2D6"
          strokeWidth="11"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="11"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 1.4s ease" }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -58%)",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 46, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'Cormorant Garamond', Georgia, serif", lineHeight: 1 }}>
          {numScore}<span style={{ fontSize: 22, color, fontWeight: 700 }}>%</span>
        </div>
        <div style={{ fontSize: 11, color: THEME.textMuted, letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 4, fontWeight: 600 }}>
          Resonance
        </div>
      </div>
      {grade && (
        <div style={{ marginTop: 10, textAlign: "center" }}>
          <span style={{
            fontSize: 13,
            fontWeight: 700,
            color,
            background: numScore >= 80 ? THEME.emeraldBg : numScore >= 60 ? THEME.amberBg : numScore >= 45 ? "#FFF7ED" : THEME.crimsonBg,
            border: `1px solid ${numScore >= 80 ? THEME.emeraldBorder : numScore >= 60 ? THEME.amberBorder : numScore >= 45 ? "#FED7AA" : THEME.crimsonBorder}`,
            borderRadius: 99,
            padding: "4px 14px",
            letterSpacing: "0.02em",
          }}>
            {formatGrade(grade)}
          </span>
        </div>
      )}
    </div>
  );
};

// ─── Visual Tempo Meter Component (Druta vs Madhya vs Vilambita) ──────────────
const TempoMeter = ({ ratio = 1.0 }) => {
  const r = typeof ratio === "number" ? ratio : 1.0;
  const isFast = r < 0.85;
  const isIdeal = r >= 0.85 && r <= 1.35;
  const isSlow = r > 1.35;

  // Normalized position on a 0.5x to 1.7x scale (clamp between 6% and 94%)
  const clampedRatio = Math.max(0.5, Math.min(1.7, r));
  const pointerPercent = Math.max(6, Math.min(94, ((clampedRatio - 0.5) / (1.7 - 0.5)) * 100));

  return (
    <div style={{ marginTop: 8 }}>
      {/* 3-segment color track */}
      <div style={{ height: 10, borderRadius: 99, background: "#EAE2D6", display: "flex", overflow: "hidden", position: "relative" }}>
        {/* Fast segment: 0.5x to 0.85x (29.1%) */}
        <div style={{ width: "29.1%", background: "#F59E0B", opacity: isFast ? 1 : 0.4 }} title="Fast / Druta (< 0.85x)" />
        {/* Ideal segment: 0.85x to 1.35x (41.7%) */}
        <div style={{ width: "41.7%", background: "#059669", opacity: isIdeal ? 1 : 0.4 }} title="Ideal / Madhya (0.85x–1.35x)" />
        {/* Slow segment: 1.35x to 1.7x (29.2%) */}
        <div style={{ width: "29.2%", background: "#EA580C", opacity: isSlow ? 1 : 0.4 }} title="Slow / Vilambita (> 1.35x)" />
      </div>

      {/* Pointer */}
      <div style={{ position: "relative", height: 14, marginTop: 2 }}>
        <div
          style={{
            position: "absolute",
            left: `${pointerPercent}%`,
            transform: "translateX(-50%)",
            fontSize: 11,
            lineHeight: 1,
            color: isIdeal ? "#059669" : THEME.accentOrange,
            transition: "left 0.8s ease",
          }}
        >
          ▲
        </div>
      </div>

      {/* 3 Zone Labels */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: THEME.textMuted, marginTop: 2 }}>
        <span style={{ color: isFast ? THEME.amber : THEME.textMuted, fontWeight: isFast ? 700 : 500 }}>
          ⚡ Fast (&lt;0.85x)
        </span>
        <span style={{ color: isIdeal ? THEME.emerald : THEME.textMuted, fontWeight: isIdeal ? 700 : 500 }}>
          ★ Ideal Madhya (0.85–1.35x)
        </span>
        <span style={{ color: isSlow ? THEME.accentOrange : THEME.textMuted, fontWeight: isSlow ? 700 : 500 }}>
          🧘 Vilambita (&gt;1.35x)
        </span>
      </div>
    </div>
  );
};

// ─── Shared Audio Player for Word Slices ─────────────────────────────────────
let globalActiveSliceAudio = null;

const playAudioSpan = (audioUrl, startSec, endSec, onPlayStateChange) => {
  if (!audioUrl) return;
  if (globalActiveSliceAudio) {
    try {
      globalActiveSliceAudio.pause();
      if (globalActiveSliceAudio._cleanup) globalActiveSliceAudio._cleanup();
    } catch {
      /* ignore audio pause errors */
    }
    globalActiveSliceAudio = null;
  }

  const s = Math.max(0, startSec || 0);
  const e = (endSec && endSec > s) ? endSec : (s + 1.2);

  const a = new Audio(audioUrl);
  globalActiveSliceAudio = a;

  let timer = null;
  const cleanup = () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (onPlayStateChange) onPlayStateChange(false);
    if (globalActiveSliceAudio === a) globalActiveSliceAudio = null;
  };
  a._cleanup = cleanup;

  const startPlayback = () => {
    try {
      a.currentTime = s;
      a.play().then(() => {
        if (onPlayStateChange) onPlayStateChange(true);
        timer = setInterval(() => {
          if (a.currentTime >= e || a.ended || a.paused) {
            a.pause();
            cleanup();
          }
        }, 30);
      }).catch(() => cleanup());
    } catch {
      cleanup();
    }
  };

  if (a.readyState >= 1) {
    startPlayback();
  } else {
    a.addEventListener("loadedmetadata", startPlayback, { once: true });
    a.addEventListener("error", cleanup, { once: true });
  }
};

// ─── Phonetic Word Card (Light Theme Studio Card) ─────────────────────────────
const PhoneticWordCard = ({ word, audioURL, refAudioURL, isSelected = false }) => {
  const [playingUser, setPlayingUser] = useState(false);
  const [playingRef, setPlayingRef] = useState(false);

  const statusCfg = {
    acceptable:   { bg: THEME.emeraldBg, border: THEME.emerald, badge: THEME.emerald, label: "✓ Acceptable" },
    review:       { bg: THEME.amberBg,   border: THEME.amber,   badge: THEME.amber,   label: "◐ Needs Review" },
    inconclusive: { bg: "#F5F0E8",       border: "#D6CEBE",     badge: THEME.textMuted, label: "? Inconclusive" }
  };
  const s = statusCfg[word.status] || statusCfg.inconclusive;

  const hasUserAudio = Boolean(
    audioURL &&
    word.user_end_sec &&
    word.user_end_sec > (word.user_start_sec || 0) &&
    (word.user_end_sec - (word.user_start_sec || 0)) >= 0.05
  );

  const userDurSec = hasUserAudio ? (word.user_end_sec - word.user_start_sec).toFixed(2) : null;
  const refDurSec = (word.ref_end_sec && word.ref_start_sec != null) ? (word.ref_end_sec - word.ref_start_sec).toFixed(2) : null;
  const expectedSvara = CANONICAL_WORD_ACCENTS[word.index] || "Vedic Accent";

  const playUserSlice = () => {
    if (!hasUserAudio) return;
    if (playingUser) {
      if (globalActiveSliceAudio) globalActiveSliceAudio.pause();
      setPlayingUser(false);
      return;
    }
    playAudioSpan(audioURL, word.user_start_sec, word.user_end_sec, setPlayingUser);
  };

  const playRefSlice = () => {
    if (!refAudioURL) return;
    if (playingRef) {
      if (globalActiveSliceAudio) globalActiveSliceAudio.pause();
      setPlayingRef(false);
      return;
    }
    playAudioSpan(refAudioURL, word.ref_start_sec, word.ref_end_sec, setPlayingRef);
  };

  return (
    <div
      id={`word-card-${word.index}`}
      className="hover-lift"
      style={{
        background: THEME.cardBg,
        border: `1.5px solid ${isSelected ? THEME.accentOrange : THEME.cardBorder}`,
        borderLeft: `5px solid ${s.badge}`,
        borderRadius: 16,
        padding: "20px 22px",
        boxShadow: isSelected ? "0 10px 28px -2px rgba(234, 88, 12, 0.22)" : "0 4px 18px -2px rgba(120, 80, 40, 0.05)",
        transition: "all 0.22s ease",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
          <span
            style={{
              background: isSelected ? "#FFF7ED" : "#F5F0E8",
              color: isSelected ? THEME.accentOrange : THEME.textSecondary,
              border: `1px solid ${isSelected ? "#FED7AA" : "transparent"}`,
              borderRadius: 6,
              padding: "2px 8px",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            Word {word.index + 1}
          </span>
          <span style={{ fontSize: 24, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'Noto Serif Devanagari', serif" }}>
            {word.devanagari}
          </span>
          <span style={{ fontSize: 14, color: THEME.textSecondary, fontStyle: "italic", fontFamily: "'Cormorant Garamond', Georgia, serif" }}>
            ({word.iast})
          </span>

          {/* Expected Svara Badge */}
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: THEME.accentOrange,
              background: "#FFF7ED",
              border: "1px solid #FED7AA",
              borderRadius: 99,
              padding: "2px 8px",
            }}
          >
            🎵 {expectedSvara}
          </span>

          {/* Status Badge */}
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              fontWeight: 700,
              color: s.badge,
              background: s.bg,
              padding: "3px 10px",
              borderRadius: 99,
              border: `1px solid ${s.border}44`,
            }}
          >
            {s.label}
          </span>
        </div>

        {/* Dual Audio Comparison Bar */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
          {/* User Word Audio Button */}
          <button
            onClick={hasUserAudio ? playUserSlice : undefined}
            disabled={!hasUserAudio}
            title={!hasUserAudio ? "This word was not detected in your recitation" : "Play your pronunciation slice"}
            style={{
              background: !hasUserAudio ? "#F5F0E8" : (playingUser ? THEME.emerald : "#FFFFFF"),
              color: !hasUserAudio ? THEME.textMuted : (playingUser ? "#FFFFFF" : THEME.textPrimary),
              border: `1.5px solid ${!hasUserAudio ? "#EAE2D6" : (playingUser ? THEME.emerald : THEME.cardBorder)}`,
              borderRadius: 10,
              padding: "9px 12px",
              fontSize: 12,
              fontWeight: 700,
              cursor: !hasUserAudio ? "not-allowed" : "pointer",
              opacity: !hasUserAudio ? 0.6 : 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              transition: "all 0.15s ease",
              boxShadow: playingUser ? "0 4px 12px rgba(5, 150, 105, 0.3)" : "0 2px 6px rgba(120, 80, 40, 0.04)",
            }}
          >
            <span>{playingUser ? "■" : (hasUserAudio ? "▶" : "—")}</span>
            <span>{playingUser ? "Playing You..." : (hasUserAudio ? `Play My Word (${userDurSec}s)` : "Not Spoken")}</span>
          </button>

          {/* Reference Word Audio Button */}
          <button
            onClick={playRefSlice}
            style={{
              background: playingRef ? THEME.accentAmber : "#FFF7ED",
              color: playingRef ? "#FFFFFF" : THEME.accentOrange,
              border: `1.5px solid ${playingRef ? THEME.accentAmber : "#FED7AA"}`,
              borderRadius: 10,
              padding: "9px 12px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              transition: "all 0.15s ease",
              boxShadow: playingRef ? "0 4px 12px rgba(217, 119, 6, 0.3)" : "none",
            }}
          >
            <span>{playingRef ? "■" : "🎧"}</span>
            <span>{playingRef ? "Playing Guru..." : `Play Reference Word (${refDurSec || "1.2"}s)`}</span>
          </button>
        </div>

        {/* Word Match Progress Bar */}
        <ScoreBar label="Acoustic Articulation (MFCC Resonance Match)" score={word.word_match_score} />

        {/* Phonetic Contrasts Details Chips */}
        {word.contrasts && word.contrasts.length > 0 && (
          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            {word.contrasts.map((c, idx) => {
              const isAcc = c.status === "acceptable";
              const isRev = c.status === "review";
              const col = isAcc ? THEME.emerald : isRev ? THEME.amber : THEME.textMuted;
              const bg = isAcc ? THEME.emeraldBg : isRev ? THEME.amberBg : "#F5F0E8";
              return (
                <div
                  key={idx}
                  style={{
                    background: bg,
                    border: `1px solid ${col}33`,
                    borderLeft: `4px solid ${col}`,
                    padding: "10px 14px",
                    borderRadius: 10,
                    fontSize: 12,
                    lineHeight: 1.6,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4, flexWrap: "wrap", gap: 4 }}>
                    <span style={{ fontWeight: 700, textTransform: "capitalize", color: THEME.textPrimary }}>
                      {c.contrast_type.replace(/_/g, " ")}: {c.label ? c.label.replace(/_/g, " ") : ""}
                    </span>
                    <span
                      style={{
                        color: col,
                        fontWeight: 700,
                        fontSize: 10,
                        textTransform: "uppercase",
                        background: "#FFFFFF",
                        border: `1px solid ${col}44`,
                        padding: "1px 7px",
                        borderRadius: 99,
                      }}
                    >
                      {c.status}
                    </span>
                  </div>

                  {/* Quantitative Metric Badge */}
                  {c.measured_ratio != null && (
                    <div style={{ fontSize: 11, color: THEME.textSecondary, marginBottom: 4 }}>
                      <span style={{ background: "#FFFFFF", border: "1px solid #EAE2D6", padding: "1px 6px", borderRadius: 4, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'JetBrains Mono', monospace" }}>
                        Measured Ratio: {c.measured_ratio}x
                      </span>
                      {c.target_range && (
                        <span style={{ marginLeft: 6, color: THEME.textMuted }}>
                          (Target: {c.target_range[0]}–{c.target_range[1]}x)
                        </span>
                      )}
                    </div>
                  )}

                  {c.measured_centroid != null && (
                    <div style={{ fontSize: 11, color: THEME.textSecondary, marginBottom: 4 }}>
                      <span style={{ background: "#FFFFFF", border: "1px solid #EAE2D6", padding: "1px 6px", borderRadius: 4, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'JetBrains Mono', monospace" }}>
                        Centroid: {Math.round(c.measured_centroid)} Hz
                      </span>
                    </div>
                  )}

                  <div style={{ color: THEME.textSecondary, marginTop: 2 }}>{c.reason}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: THEME.textMuted, marginTop: 14, borderTop: `1px solid ${THEME.cardBorder}`, paddingTop: 10 }}>
        <span>Timing: {word.user_start_sec?.toFixed(2)}s – {word.user_end_sec?.toFixed(2)}s ({word.duration_sec?.toFixed(2)}s)</span>
        <span>Confidence: {Math.round((word.alignment_confidence || 0) * 100)}%</span>
      </div>
    </div>
  );
};

// ─── Word Svara Card (Accent & Shape 2-Column Item) ──────────────────────────
const SvaraWordCard = ({ item }) => {
  const ok = item.accent_ok && item.shape_ok;
  return (
    <div
      className="hover-lift"
      style={{
        background: THEME.cardBg,
        border: `1.5px solid ${ok ? THEME.emeraldBorder : THEME.crimsonBorder}`,
        borderLeft: `5px solid ${ok ? THEME.emerald : THEME.crimson}`,
        borderRadius: 14,
        padding: "16px 18px",
        boxShadow: "0 2px 10px rgba(120, 80, 40, 0.04)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <span style={{ background: "#F5F0E8", color: THEME.textSecondary, borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 700 }}>
            Word {item.word_num}
          </span>
          <span style={{ fontSize: 20, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'Noto Serif Devanagari', serif" }}>
            '{item.word}'
          </span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              fontWeight: 700,
              color: ok ? THEME.emerald : THEME.crimson,
              background: ok ? THEME.emeraldBg : THEME.crimsonBg,
              border: `1px solid ${ok ? THEME.emeraldBorder : THEME.crimsonBorder}`,
              borderRadius: 99,
              padding: "2px 10px",
            }}
          >
            {ok ? "✓ Accurate Svara" : "✗ Accent Deviation"}
          </span>
        </div>

        {/* Accent Comparison Row */}
        <div style={{ background: "#FAF6F0", borderRadius: 8, padding: "10px 12px", marginBottom: 10, fontSize: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontWeight: 600, color: THEME.textSecondary }}>Pitch Accent:</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: item.accent_ok ? THEME.emerald : THEME.crimson }}>
              {item.accent_ok ? "✓ Matched" : "✗ Deviation"}
            </span>
          </div>
          <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
            <div>
              <span style={{ color: THEME.textMuted, fontSize: 11 }}>Expected: </span>
              <span style={{ color: THEME.emerald, fontWeight: 700 }}>{formatAccentWithSymbol(item.ref_accent)}</span>
            </div>
            <span>→</span>
            <div>
              <span style={{ color: THEME.textMuted, fontSize: 11 }}>Sung: </span>
              <span style={{ color: item.accent_ok ? THEME.emerald : THEME.crimson, fontWeight: 700 }}>{formatAccentWithSymbol(item.user_accent)}</span>
            </div>
          </div>
          {item.accent_fix && (
            <div style={{ marginTop: 6, fontSize: 11, color: THEME.accentOrange, background: "#FFF7ED", border: "1px solid #FED7AA", borderRadius: 6, padding: "4px 8px" }}>
              💡 {item.accent_fix}
            </div>
          )}
        </div>

        {/* Pitch Shape Comparison Row */}
        <div style={{ background: "#FAF6F0", borderRadius: 8, padding: "10px 12px", fontSize: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontWeight: 600, color: THEME.textSecondary }}>Vowel Contour Shape:</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: item.shape_ok ? THEME.emerald : THEME.crimson }}>
              {item.shape_ok ? "✓ Matched" : "✗ Deviation"}
            </span>
          </div>
          <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
            <div>
              <span style={{ color: THEME.textMuted, fontSize: 11 }}>Expected: </span>
              <span style={{ color: THEME.emerald, fontWeight: 700 }}>{formatShapeWithSymbol(item.ref_shape)}</span>
            </div>
            <span>→</span>
            <div>
              <span style={{ color: THEME.textMuted, fontSize: 11 }}>Sung: </span>
              <span style={{ color: item.shape_ok ? THEME.emerald : THEME.crimson, fontWeight: 700 }}>{formatShapeWithSymbol(item.user_shape)}</span>
            </div>
          </div>
          {item.shape_fix && (
            <div style={{ marginTop: 6, fontSize: 11, color: THEME.accentOrange, background: "#FFF7ED", border: "1px solid #FED7AA", borderRadius: 6, padding: "4px 8px" }}>
              💡 {item.shape_fix}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Feedback List (Light Theme) ─────────────────────────────────────────────
const FeedbackList = ({ items, variant = "default" }) => {
  const borderCol = variant === "error" ? THEME.crimson : variant === "success" ? THEME.emerald : THEME.amber;
  const bgCol = variant === "error" ? THEME.crimsonBg : variant === "success" ? THEME.emeraldBg : THEME.amberBg;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((item, i) => (
        <div
          key={i}
          style={{
            background: bgCol,
            borderLeft: `4px solid ${borderCol}`,
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: 13,
            color: THEME.textPrimary,
            lineHeight: 1.6,
          }}
        >
          {item}
        </div>
      ))}
    </div>
  );
};

// ─── PCM WAV Encoder ─────────────────────────────────────────────────────────
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

// ─── QuickTime / MP4 Container Audio (LPCM) Demuxer ──────────────────────────
function extractQuickTimeLPCM(arrayBuffer) {
  try {
    const data = new Uint8Array(arrayBuffer);
    const view = new DataView(arrayBuffer);

    function findBytes(needle, start = 0, end = data.length) {
      const nLen = needle.length;
      const limit = Math.min(end, data.length - nLen);
      for (let i = start; i <= limit; i++) {
        let match = true;
        for (let j = 0; j < nLen; j++) {
          if (data[i + j] !== needle[j]) { match = false; break; }
        }
        if (match) return i;
      }
      return -1;
    }

    const sounSig = [109, 104, 108, 114, 115, 111, 117, 110]; // 'mhlrsoun'
    const trakSoun = findBytes(sounSig);
    if (trakSoun === -1) return null;

    let sampleRate = 44100;
    const mdhdSig = [109, 100, 104, 100]; // 'mdhd'
    const mdhdPos = findBytes(mdhdSig, Math.max(0, trakSoun - 400), trakSoun + 400);
    if (mdhdPos !== -1) {
      sampleRate = view.getUint32(mdhdPos + 20, false);
    }

    const stsdSig = [115, 116, 115, 100]; // 'stsd'
    const stsdIdx = findBytes(stsdSig, trakSoun);
    if (stsdIdx === -1) return null;

    let numChannels = 2;
    let bitsPerSample = 16;
    let isBigEndian = false;

    const lpcmSig = [108, 112, 99, 109]; // 'lpcm'
    const lpcmIdx = findBytes(lpcmSig, stsdIdx, stsdIdx + 300);
    if (lpcmIdx !== -1) {
      const ver = view.getUint16(lpcmIdx + 12, false);
      if (ver === 2) {
        sampleRate = Math.round(view.getFloat64(lpcmIdx + 36, false));
        numChannels = view.getUint32(lpcmIdx + 44, false);
        bitsPerSample = view.getUint32(lpcmIdx + 52, false);
        const flags = view.getUint32(lpcmIdx + 56, false);
        isBigEndian = Boolean(flags & 2);
      } else {
        numChannels = view.getUint16(lpcmIdx + 20, false);
        bitsPerSample = view.getUint16(lpcmIdx + 22, false);
      }
    }

    const stscSig = [115, 116, 115, 99]; // 'stsc'
    const stscIdx = findBytes(stscSig, trakSoun);
    if (stscIdx === -1) return null;
    const stscEntries = view.getUint32(stscIdx + 8, false);
    const stscTable = [];
    for (let i = 0; i < stscEntries; i++) {
      const fc = view.getUint32(stscIdx + 12 + i * 12, false);
      const spc = view.getUint32(stscIdx + 16 + i * 12, false);
      stscTable.push({ firstChunk: fc, samplesPerChunk: spc });
    }

    let chunkOffsets = [];
    const stcoSig = [115, 116, 99, 111]; // 'stco'
    const stcoIdx = findBytes(stcoSig, trakSoun);
    if (stcoIdx !== -1) {
      const entries = view.getUint32(stcoIdx + 8, false);
      for (let i = 0; i < entries; i++) {
        chunkOffsets.push(view.getUint32(stcoIdx + 12 + i * 4, false));
      }
    } else {
      const co64Sig = [99, 111, 54, 52]; // 'co64'
      const co64Idx = findBytes(co64Sig, trakSoun);
      if (co64Idx !== -1) {
        const entries = view.getUint32(co64Idx + 8, false);
        for (let i = 0; i < entries; i++) {
          chunkOffsets.push(Number(view.getBigUint64(co64Idx + 12 + i * 8, false)));
        }
      }
    }
    if (chunkOffsets.length === 0) return null;

    const bytesPerChannel = Math.floor(bitsPerSample / 8);
    const bytesPerFrame = bytesPerChannel * numChannels;
    let totalSamples = 0;
    for (let c = 0; c < chunkOffsets.length; c++) {
      const chunkNum = c + 1;
      let spc = 0;
      for (let s = stscTable.length - 1; s >= 0; s--) {
        if (chunkNum >= stscTable[s].firstChunk) {
          spc = stscTable[s].samplesPerChunk;
          break;
        }
      }
      totalSamples += spc;
    }

    const mono = new Float32Array(totalSamples);
    let writeIdx = 0;
    for (let c = 0; c < chunkOffsets.length; c++) {
      const chunkNum = c + 1;
      let spc = 0;
      for (let s = stscTable.length - 1; s >= 0; s--) {
        if (chunkNum >= stscTable[s].firstChunk) {
          spc = stscTable[s].samplesPerChunk;
          break;
        }
      }
      const offset = chunkOffsets[c];
      for (let i = 0; i < spc; i++) {
        const frameOffset = offset + i * bytesPerFrame;
        let sum = 0;
        for (let ch = 0; ch < numChannels; ch++) {
          const sOffset = frameOffset + ch * bytesPerChannel;
          let val = 0;
          if (bitsPerSample === 16) {
            val = view.getInt16(sOffset, !isBigEndian) / 32768.0;
          } else if (bitsPerSample === 24) {
            let b0 = data[sOffset], b1 = data[sOffset + 1], b2 = data[sOffset + 2];
            let i24 = isBigEndian ? ((b0 << 16) | (b1 << 8) | b2) : ((b2 << 16) | (b1 << 8) | b0);
            if (i24 >= 0x800000) i24 -= 0x1000000;
            val = i24 / 8388608.0;
          } else if (bitsPerSample === 32) {
            val = view.getInt32(sOffset, !isBigEndian) / 2147483648.0;
          }
          sum += val;
        }
        mono[writeIdx++] = sum / numChannels;
      }
    }

    return { sampleRate, monoSamples: mono, duration: totalSamples / sampleRate };
  } catch (err) {
    console.warn("QuickTime LPCM parser notice:", err);
    return null;
  }
}

// ─── Mantra Catalog ──────────────────────────────────────────────────────────
export const MANTRAS = [
  {
    id: "ganesha",
    name: "Shri Ganesha Shloka",
    subtitle: "Vakratuṇḍa Mahākāya",
    icon: "🕉️",
    badge: "ॐ गं गणपतये नमः · Reference Recitation",
    line1: "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ ।",
    line2: "निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा ॥",
    fullDevanagari: "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा",
    iast: "vakratuṇḍa mahākāya sūryakoṭi samaprabha | nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā ||",
    meaning: "O Lord with the curved trunk and immense radiant body, whose brilliance equals ten million suns, please make all my endeavors free from obstacles, always.",
    tradition: "Guru-Paramparā Standard"
  },
  {
    id: "mrityunjaya",
    name: "Maha Mrityunjaya Mantra",
    subtitle: "Tryambakaṃ Yajāmahe",
    icon: "🔱",
    badge: "ॐ नमः शिवाय · Reference Recitation",
    line1: "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् ।",
    line2: "उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात् ॥",
    fullDevanagari: "त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात्",
    iast: "tryambakaṃ yajāmahe sugandhiṃ puṣṭivardhanam | urvārukamiva bandhanān mṛtyormukṣīya māmṛtāt ||",
    meaning: "We worship the Three-Eyed One (Lord Shiva), who is fragrant and who nourishes all beings. As a ripe cucumber is freed from its stem, may we be liberated from death, for the sake of immortality.",
    tradition: "Rigvedic Chhandas Standard"
  },
  {
    id: "gayatri",
    name: "Gayatri Mantra",
    subtitle: "Savitṛ Gāyatrī",
    icon: "☀️",
    badge: "ॐ भूर्भुवः स्वः · Reference Recitation",
    line1: "ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं ।",
    line2: "भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात् ॥",
    fullDevanagari: "ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्",
    iast: "oṃ bhūrbhuvaḥ svaḥ tatsaviturvareṇyaṃ | bhargo devasya dhīmahi dhiyo yo naḥ pracodayāt ||",
    meaning: "We meditate on the supreme radiant splendor of the divine Sun (Savitṛ), the Creator of the universe. May that divine light inspire and illumine our intellect.",
    tradition: "Rigvedic Gāyatrī Chhandas Standard"
  }
];

// ─── Main Application ────────────────────────────────────────────────────────
export default function App() {
  const [currentPage, setCurrentPage] = useState("studio"); // "studio" | "results"
  const [selectedMantra, setSelectedMantra] = useState("ganesha");
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("phonetic");
  const [apiStatus, setApiStatus] = useState("checking");
  const [selectedWordIdx, setSelectedWordIdx] = useState(null);
  const [refPlaying, setRefPlaying] = useState(false);
  const [userFullPlaying, setUserFullPlaying] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const [loadingStage, setLoadingStage] = useState(1);
  const [loadingElapsed, setLoadingElapsed] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const analyserRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const refAudioElementRef = useRef(null);
  const userFullAudioRef = useRef(null);
  const abortControllerRef = useRef(null);
  const canvasRef = useRef(null);

  const cancelAnalysis = () => {
    if (abortControllerRef.current) {
      try { abortControllerRef.current.abort(); } catch { /* ignore */ }
      abortControllerRef.current = null;
    }
    setLoadingStage(1);
    setLoadingElapsed(0);
    setLoading(false);
  };

  const resetToStartPage = () => {
    cancelAnalysis();
    if (userFullAudioRef.current) {
      try { userFullAudioRef.current.pause(); } catch { /* ignore */ }
    }
    if (refAudioElementRef.current) {
      try { refAudioElementRef.current.pause(); } catch { /* ignore */ }
    }
    setUserFullPlaying(false);
    setRefPlaying(false);
    setResult(null);
    setAudioBlob(null);
    setAudioURL(null);
    setError(null);
    setSelectedWordIdx(null);
    setActiveTab("phonetic");
    setCurrentPage("studio");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const currentMantra = MANTRAS.find((m) => m.id === selectedMantra) || MANTRAS[0];
  const refAudioURL = `${API_URL}/reference-audio?mantra_id=${selectedMantra}`;

  // Reset audio when switching mantras
  useEffect(() => {
    if (refAudioElementRef.current) {
      try { refAudioElementRef.current.pause(); } catch { /* ignore */ }
      refAudioElementRef.current = null;
    }
    setRefPlaying(false);
  }, [selectedMantra]);

  // API Health Check
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API_URL}/health`);
        setApiStatus(r.ok ? "ok" : "down");
      } catch {
        setApiStatus("down");
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  // Multi-Stage Loading Timer
  useEffect(() => {
    if (!loading) return;
    const start = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000);
      setLoadingElapsed(elapsed);
      if (elapsed < 6) {
        setLoadingStage(1);
      } else if (elapsed < 14) {
        setLoadingStage(2);
      } else {
        setLoadingStage(3);
      }
    }, 500);
    return () => clearInterval(timer);
  }, [loading]);

  // Recording Timer
  useEffect(() => {
    if (!recording) return;
    const start = Date.now();
    const timer = setInterval(() => {
      setRecordDuration((Date.now() - start) / 1000);
    }, 100);
    return () => clearInterval(timer);
  }, [recording]);

  // HTML5 Canvas Audio Waveform Visualizer
  useEffect(() => {
    let animId;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const render = () => {
      animId = requestAnimationFrame(render);

      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }
      ctx.resetTransform();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      const barCount = 42;
      const barSpacing = 4;
      const totalSpacing = (barCount - 1) * barSpacing;
      const barWidth = Math.max(3, (width - 48 - totalSpacing) / barCount);
      const startX = (width - (barCount * barWidth + totalSpacing)) / 2;

      if (recording && analyserRef.current) {
        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyserRef.current.getByteFrequencyData(dataArray);

        for (let i = 0; i < barCount; i++) {
          const dataIdx = Math.floor((i / barCount) * (bufferLength * 0.72));
          const val = dataArray[dataIdx] || 0;
          const percent = val / 255;
          const barHeight = Math.max(6, percent * (height - 24));
          const x = startX + i * (barWidth + barSpacing);
          const y = (height - barHeight) / 2;

          const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
          grad.addColorStop(0, THEME.accentOrange);
          grad.addColorStop(0.5, THEME.accentAmber);
          grad.addColorStop(1, THEME.accentYellow);

          ctx.fillStyle = grad;
          ctx.beginPath();
          const r = Math.min(barWidth / 2, barHeight / 2);
          if (ctx.roundRect) {
            ctx.roundRect(x, y, barWidth, barHeight, r);
          } else {
            ctx.rect(x, y, barWidth, barHeight);
          }
          ctx.fill();
        }
      } else {
        // Idle gentle waveform visualization
        const time = Date.now() / 800;
        for (let i = 0; i < barCount; i++) {
          const wave = Math.sin(time + (i * 0.28)) * 0.5 + 0.5;
          const barHeight = 8 + wave * 16;
          const x = startX + i * (barWidth + barSpacing);
          const y = (height - barHeight) / 2;

          ctx.fillStyle = "#EAE2D6";
          ctx.beginPath();
          const r = Math.min(barWidth / 2, barHeight / 2);
          if (ctx.roundRect) {
            ctx.roundRect(x, y, barWidth, barHeight, r);
          } else {
            ctx.rect(x, y, barWidth, barHeight);
          }
          ctx.fill();
        }
      }
    };

    render();
    return () => {
      if (animId) cancelAnimationFrame(animId);
    };
  }, [recording]);

  const togglePlayReferenceMantra = () => {
    if (userFullAudioRef.current && userFullPlaying) {
      userFullAudioRef.current.pause();
      setUserFullPlaying(false);
    }

    if (!refAudioElementRef.current || refAudioElementRef.current.src !== new URL(refAudioURL, window.location.href).href) {
      if (refAudioElementRef.current) {
        try { refAudioElementRef.current.pause(); } catch { /* ignore */ }
      }
      const a = new Audio(refAudioURL);
      refAudioElementRef.current = a;
      a.onended = () => setRefPlaying(false);
      a.onpause = () => setRefPlaying(false);
    }
    if (refPlaying) {
      refAudioElementRef.current.pause();
      setRefPlaying(false);
    } else {
      refAudioElementRef.current.play().then(() => setRefPlaying(true)).catch(() => setRefPlaying(false));
    }
  };

  const togglePlayUserFullAudio = () => {
    if (!audioURL) return;

    if (refAudioElementRef.current && refPlaying) {
      refAudioElementRef.current.pause();
      setRefPlaying(false);
    }

    if (!userFullAudioRef.current || userFullAudioRef.current.src !== audioURL) {
      const a = new Audio(audioURL);
      userFullAudioRef.current = a;
      a.onended = () => setUserFullPlaying(false);
      a.onpause = () => setUserFullPlaying(false);
    }
    if (userFullPlaying) {
      userFullAudioRef.current.pause();
      setUserFullPlaying(false);
    } else {
      userFullAudioRef.current.play().then(() => setUserFullPlaying(true)).catch(() => setUserFullPlaying(false));
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        }
      });
      mediaStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);

      // Connect Analyser for real-time canvas visualizer
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      source.connect(analyser);
      analyserRef.current = analyser;

      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      audioChunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioChunksRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setRecordDuration(0);
      setRecording(true);
      setResult(null);
      setError(null);
    } catch {
      setError("Microphone access denied. Please grant microphone permissions in your browser.");
    }
  };

  const stopRecording = () => {
    if (!recording) return;
    setRecording(false);
    setRecordDuration(0);

    try {
      if (processorRef.current) processorRef.current.disconnect();
      if (analyserRef.current) {
        try { analyserRef.current.disconnect(); } catch { /* ignore */ }
        analyserRef.current = null;
      }
      if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      if (audioContextRef.current) {
        const sampleRate = audioContextRef.current.sampleRate;
        audioContextRef.current.close();

        const chunks = audioChunksRef.current;
        let totalLen = 0;
        for (const c of chunks) totalLen += c.length;
        const merged = new Float32Array(totalLen);
        let offset = 0;
        for (const c of chunks) {
          merged.set(c, offset);
          offset += c.length;
        }

        // Peak-normalize recorded audio to 0.92 maximum amplitude
        let maxPeak = 0;
        for (let i = 0; i < merged.length; i++) {
          const abs = Math.abs(merged[i]);
          if (abs > maxPeak) maxPeak = abs;
        }
        if (maxPeak > 0.01) {
          const gain = Math.min(0.92 / maxPeak, 6.0);
          for (let i = 0; i < merged.length; i++) {
            merged[i] = merged[i] * gain;
          }
        }

        const wavBlob = encodeWAV(merged, sampleRate);
        setAudioBlob(wavBlob);
        setAudioURL(URL.createObjectURL(wavBlob));
      }
    } catch (e) {
      setError("Failed to encode audio into WAV format: " + e.message);
    }
  };

  const processAudioFile = async (file) => {
    if (!file) return;
    setError(null);
    setResult(null);

    try {
      const arrayBuffer = await file.arrayBuffer();
      let monoSamples = null;
      let sampleRate = 16000;

      // 1. Try standard Web Audio API decodeAudioData
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
        audioCtx.close();
        sampleRate = decoded.sampleRate;
        if (decoded.numberOfChannels === 1) {
          monoSamples = decoded.getChannelData(0);
        } else {
          const left = decoded.getChannelData(0);
          const right = decoded.getChannelData(1);
          monoSamples = new Float32Array(left.length);
          for (let i = 0; i < left.length; i++) {
            monoSamples[i] = (left[i] + right[i]) / 2.0;
          }
        }
      } catch (decodeErr) {
        console.warn("Standard decodeAudioData failed, checking QuickTime/MP4 container...", decodeErr);
        // 2. Try zero-dependency QuickTime LPCM parser for MOV/MP4 files
        const qt = extractQuickTimeLPCM(arrayBuffer);
        if (qt && qt.monoSamples && qt.monoSamples.length > 0) {
          monoSamples = qt.monoSamples;
          sampleRate = qt.sampleRate;
        } else {
          throw decodeErr;
        }
      }

      if (monoSamples) {
        let maxPeak = 0;
        for (let i = 0; i < monoSamples.length; i++) {
          const abs = Math.abs(monoSamples[i]);
          if (abs > maxPeak) maxPeak = abs;
        }
        if (maxPeak > 0.01 && maxPeak < 0.25) {
          const gain = Math.min(0.92 / maxPeak, 4.0);
          for (let i = 0; i < monoSamples.length; i++) {
            monoSamples[i] = monoSamples[i] * gain;
          }
        }

        const wavBlob = encodeWAV(monoSamples, sampleRate);
        const wavFile = new File([wavBlob], file.name.replace(/\.[^/.]+$/, ".wav"), { type: "audio/wav" });
        setAudioBlob(wavFile);
        setAudioURL(URL.createObjectURL(wavBlob));
      }
    } catch (fallbackErr) {
      console.warn("Client-side audio decode fallback to raw file:", fallbackErr);
      setAudioBlob(file);
      setAudioURL(URL.createObjectURL(file));
    }
  };

  const handleFile = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) processAudioFile(file);
  };

  const analyze = async () => {
    if (!audioBlob) return;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setLoadingStage(1);
    setLoadingElapsed(0);
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", audioBlob, "user_chant.wav");
      form.append("mantra_id", selectedMantra);
      const resp = await fetch(`${API_URL}/analyze?mantra_id=${encodeURIComponent(selectedMantra)}`, {
        method: "POST",
        body: form,
        signal: controller.signal
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Server analysis error" }));
        throw new Error(err.detail || "Analysis failed");
      }
      const data = await resp.json();
      setResult(data);
      setActiveTab("phonetic");
      setCurrentPage("results"); // Automatically transition to Page 2!
    } catch (e) {
      if (e.name === "AbortError") {
        return;
      }
      setError(e.message);
    } finally {
      setLoading(false);
      setLoadingStage(1);
      setLoadingElapsed(0);
      abortControllerRef.current = null;
    }
  };

  const r = result;
  const sc = r?.scores || {};
  const d = r?.dimensions || {};
  const wordDetail = r?.svara_word_detail || [];
  const wordAlign = r?.word_alignment || [];
  const phoneticWords = r?.phonetic_evaluation?.words || [];

  // Compute Priority Items (Ranked by Gap × Weight Impact)
  const priorityItems = (r?.priority && r.priority.length > 0)
    ? r.priority
    : [
        { dimension: "Ucchāraṇa (Pronunciation)", score: Math.round(d.uccharana?.score ?? sc.text_similarity ?? 0), impact: Number(((100 - (d.uccharana?.score ?? sc.text_similarity ?? 0)) * 0.40).toFixed(1)) },
        { dimension: "Svara (Pitch & Accent)", score: Math.round(d.svara?.score ?? sc.pitch_combined ?? 0), impact: Number(((100 - (d.svara?.score ?? sc.pitch_combined ?? 0)) * 0.20).toFixed(1)) },
        { dimension: "Nāda (Voice Quality)", score: Math.round(d.nada?.score ?? sc.mfcc_similarity ?? 0), impact: Number(((100 - (d.nada?.score ?? sc.mfcc_similarity ?? 0)) * 0.25).toFixed(1)) },
        { dimension: "Laya (Rhythm & Tempo)", score: Math.round(d.laya?.score ?? sc.tempo_similarity ?? 0), impact: Number(((100 - (d.laya?.score ?? sc.tempo_similarity ?? 0)) * 0.15).toFixed(1)) },
      ].sort((a, b) => b.impact - a.impact);

  // Compute All Sādhu Praises
  const allPraises = (r?.all_praises && r.all_praises.length > 0)
    ? r.all_praises
    : [
        ...(d.uccharana?.praises || []),
        ...(d.svara?.praises || []),
        ...(d.laya?.praises || []),
        ...(d.nada?.praises || []),
      ];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Noto+Serif+Devanagari:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        * { box-sizing: border-box; }
        body {
          margin: 0;
          background-color: ${THEME.bg};
          background-image: 
            radial-gradient(circle at 15% 10%, rgba(251, 146, 60, 0.12), transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(217, 119, 6, 0.10), transparent 50%),
            radial-gradient(circle at 50% 85%, rgba(245, 158, 11, 0.08), transparent 45%);
          background-attachment: fixed;
          color: ${THEME.textPrimary};
          font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
          -webkit-font-smoothing: antialiased;
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(234, 88, 12, 0.45); }
          50% { box-shadow: 0 0 0 12px rgba(234, 88, 12, 0); }
        }

        @keyframes floatSlow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }

        @keyframes spinSlow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .hover-lift {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .hover-lift:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 28px -4px rgba(120, 80, 40, 0.12) !important;
        }

        button:active {
          transform: scale(0.985);
        }

        @media (max-width: 768px) {
          .top-hero-grid {
            grid-template-columns: 1fr !important;
          }
          .macro-2x2-grid {
            grid-template-columns: 1fr !important;
          }
          .coaching-2col-grid {
            grid-template-columns: 1fr !important;
          }
          .word-strip-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
          nav {
            flex-direction: column !important;
            gap: 12px !important;
            align-items: stretch !important;
            padding: 12px 16px !important;
          }
        }
      `}</style>

      {/* ─── Sticky Top Navigation Bar ────────────────────────────────────────── */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 1000,
          backdropFilter: "blur(14px)",
          background: "rgba(250, 246, 240, 0.90)",
          borderBottom: `1px solid ${THEME.cardBorder}`,
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          boxShadow: "0 4px 20px -5px rgba(120, 80, 40, 0.05)",
        }}
      >
        {/* Left: Brand Identity */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #EA580C 0%, #D97706 100%)",
              color: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              fontWeight: 700,
              boxShadow: "0 3px 10px rgba(234, 88, 12, 0.35)",
            }}
          >
            ॐ
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Cormorant Garamond', Georgia, serif", color: THEME.textPrimary, letterSpacing: "0.02em" }}>
                Svara Vaidya · स्वर वैद्य
              </span>
              <span style={{ fontSize: 10, fontWeight: 700, color: THEME.accentOrange, background: "#FFF7ED", border: "1px solid #FED7AA", padding: "1px 6px", borderRadius: 4 }}>
                v2.0
              </span>
            </div>
            <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 500 }}>
              Vedic Phonetic & Svara Telemetry System
            </div>
          </div>
        </div>

        {/* Center: Multi-Page Switcher Pill Tabs */}
        <div
          style={{
            display: "flex",
            background: "#EFE8DE",
            padding: "4px",
            borderRadius: 99,
            gap: 4,
            border: `1px solid ${THEME.cardBorder}`,
          }}
        >
          <button
            onClick={() => setCurrentPage("studio")}
            style={{
              padding: "7px 18px",
              borderRadius: 99,
              border: "none",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: currentPage === "studio" ? "#FFFFFF" : "transparent",
              color: currentPage === "studio" ? THEME.accentOrange : THEME.textSecondary,
              boxShadow: currentPage === "studio" ? "0 2px 8px rgba(120, 80, 40, 0.10)" : "none",
              transition: "all 0.18s ease",
            }}
          >
            <span>🎙️</span>
            <span>1. Chanting Studio</span>
          </button>

          <button
            onClick={() => {
              if (result) setCurrentPage("results");
            }}
            disabled={!result}
            title={!result ? "Complete recording & evaluation to view analysis" : "View Analysis Dashboard"}
            style={{
              padding: "7px 18px",
              borderRadius: 99,
              border: "none",
              cursor: !result ? "not-allowed" : "pointer",
              fontSize: 12,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: currentPage === "results" ? "#FFFFFF" : "transparent",
              color: currentPage === "results" ? THEME.accentOrange : (!result ? THEME.textMuted : THEME.textSecondary),
              opacity: !result ? 0.6 : 1,
              boxShadow: currentPage === "results" ? "0 2px 8px rgba(120, 80, 40, 0.10)" : "none",
              transition: "all 0.18s ease",
            }}
          >
            <span>📊</span>
            <span>2. Analysis Dashboard</span>
            {result && (
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: THEME.emerald,
                  display: "inline-block",
                  boxShadow: `0 0 6px ${THEME.emerald}`,
                }}
              />
            )}
          </button>
        </div>

        {/* Right: API Status & Reset Action */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {(result || audioURL) && (
            <button
              onClick={resetToStartPage}
              title="Return to start page and reset recording"
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: THEME.textSecondary,
                background: "#FFFFFF",
                border: `1px solid ${THEME.cardBorder}`,
                padding: "5px 12px",
                borderRadius: 99,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                boxShadow: "0 1px 4px rgba(120, 80, 40, 0.05)",
                transition: "all 0.15s ease",
              }}
            >
              <span>↺</span>
              <span>Reset Studio</span>
            </button>
          )}

          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              padding: "4px 10px",
              borderRadius: 99,
              background: apiStatus === "ok" ? THEME.emeraldBg : THEME.crimsonBg,
              color: apiStatus === "ok" ? THEME.emerald : THEME.crimson,
              border: `1px solid ${apiStatus === "ok" ? THEME.emeraldBorder : THEME.crimsonBorder}`,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span style={{ fontSize: 9 }}>●</span>
            <span>{apiStatus === "ok" ? "Server Online" : "Server Offline"}</span>
          </span>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════════════════════════════════
          PAGE 1: DYNAMIC CHANTING STUDIO (currentPage === "studio")
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentPage === "studio" && (
        <main style={{ maxWidth: 960, margin: "0 auto", padding: "32px 20px 80px", animation: "fadeUp 0.3s ease" }}>
          
          {/* Card 1: Hero Reference Shloka Banner Card */}
          <div
            className="hover-lift"
            style={{
              background: THEME.cardBg,
              border: `1px solid ${THEME.cardBorder}`,
              borderRadius: 20,
              padding: "32px 36px",
              marginBottom: 28,
              boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Decorative Top Accent Bar */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 4,
                background: "linear-gradient(90deg, #EA580C 0%, #D97706 50%, #F59E0B 100%)",
              }}
            />

            <div style={{ textAlign: "center" }}>
              {/* Mantra Selector Pill Tabs */}
              <div
                style={{
                  display: "inline-flex",
                  background: "#F1ECE1",
                  padding: 4,
                  borderRadius: 99,
                  gap: 4,
                  marginBottom: 20,
                  boxShadow: "inset 0 1px 3px rgba(0,0,0,0.06)",
                }}
              >
                {MANTRAS.map((m) => {
                  const isSel = m.id === selectedMantra;
                  return (
                    <button
                      key={m.id}
                      onClick={() => {
                        if (selectedMantra !== m.id) {
                          setSelectedMantra(m.id);
                          setResult(null);
                          setError(null);
                        }
                      }}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 20px",
                        borderRadius: 99,
                        border: "none",
                        background: isSel ? "#FFFFFF" : "transparent",
                        color: isSel ? THEME.accentOrange : THEME.textSecondary,
                        fontWeight: isSel ? 700 : 500,
                        fontSize: 13,
                        cursor: "pointer",
                        boxShadow: isSel ? "0 2px 6px rgba(0,0,0,0.08)" : "none",
                        transition: "all 0.18s ease",
                      }}
                    >
                      <span>{m.icon}</span>
                      <span>{m.name}</span>
                    </button>
                  );
                })}
              </div>

              <div
                style={{
                  display: "block",
                  margin: "0 auto 16px",
                }}
              >
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: "#FFF7ED",
                    border: "1px solid #FED7AA",
                    color: THEME.accentOrange,
                    borderRadius: 99,
                    padding: "4px 14px",
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  <span>{currentMantra.badge}</span>
                </div>
              </div>

              {/* Large Glowing Devanagari Verse */}
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: THEME.textPrimary,
                  fontFamily: "'Noto Serif Devanagari', serif",
                  lineHeight: 1.6,
                  letterSpacing: "0.02em",
                  marginBottom: 10,
                }}
              >
                {currentMantra.line1}<br />
                {currentMantra.line2}
              </div>

              {/* IAST Transliteration */}
              <div
                style={{
                  fontSize: 14,
                  color: THEME.textSecondary,
                  fontStyle: "italic",
                  marginBottom: 18,
                  fontFamily: "'Cormorant Garamond', Georgia, serif",
                  letterSpacing: "0.03em",
                }}
              >
                {currentMantra.iast}
              </div>

              {/* Meaning Box */}
              <div
                style={{
                  background: "#FAF6F0",
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 12,
                  padding: "12px 20px",
                  maxWidth: 780,
                  margin: "0 auto 20px",
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: THEME.textSecondary,
                }}
              >
                <span style={{ color: THEME.accentOrange, fontWeight: 700 }}>English Meaning: </span>
                {currentMantra.meaning}
              </div>

              {/* Master Reference Audio Playback Button */}
              <button
                onClick={togglePlayReferenceMantra}
                style={{
                  background: refPlaying ? THEME.accentAmber : "#FFF7ED",
                  color: refPlaying ? "#FFFFFF" : THEME.accentOrange,
                  border: `1px solid ${refPlaying ? THEME.accentAmber : "#FED7AA"}`,
                  borderRadius: 99,
                  padding: "9px 24px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 2px 8px rgba(234, 88, 12, 0.12)",
                  transition: "all 0.18s ease",
                }}
              >
                <span>{refPlaying ? "■" : "▶"}</span>
                <span>{refPlaying ? "Stop Golden Reference" : "Listen to Golden Reference"}</span>
              </button>
            </div>
          </div>

          {/* Card 2: Interactive Recording & Upload Studio Card */}
          <div
            className="hover-lift"
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                processAudioFile(e.dataTransfer.files[0]);
              }
            }}
            style={{
              background: isDragging ? "#FFF7ED" : THEME.cardBg,
              border: isDragging ? `2px dashed ${THEME.accentOrange}` : `1px solid ${THEME.cardBorder}`,
              borderRadius: 20,
              padding: "32px 36px",
              boxShadow: isDragging ? "0 14px 36px -4px rgba(234, 88, 12, 0.18)" : "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
              position: "relative",
              transition: "all 0.2s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                  01 · Interactive Recording Studio
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                  Record Live or Upload Chant
                </div>
              </div>
              <div style={{ fontSize: 12, color: THEME.textMuted }}>
                Lossless 16kHz PCM Pipeline
              </div>
            </div>

            {/* HTML5 Canvas Audio Waveform Visualizer */}
            <div
              style={{
                background: "#FAF6F0",
                border: `1px solid ${recording ? THEME.accentOrange : THEME.cardBorder}`,
                borderRadius: 14,
                padding: "16px",
                height: 120,
                position: "relative",
                marginBottom: 22,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                transition: "border 0.3s ease",
              }}
            >
              <canvas
                ref={canvasRef}
                style={{ width: "100%", height: "100%", display: "block" }}
              />

              {/* Visualizer Status & Live Timer Overlay */}
              <div
                style={{
                  position: "absolute",
                  top: 10,
                  left: 16,
                  right: 16,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  pointerEvents: "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: recording ? THEME.crimson : THEME.textMuted,
                      animation: recording ? "pulseGlow 1.2s infinite" : "none",
                    }}
                  />
                  <span style={{ fontSize: 11, fontWeight: 700, color: recording ? THEME.crimson : THEME.textMuted, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    {recording ? "Recording Live..." : "Microphone Idle"}
                  </span>
                </div>

                {recording && (
                  <div
                    style={{
                      background: "#FFFFFF",
                      border: `1px solid ${THEME.crimsonBorder}`,
                      color: THEME.crimson,
                      borderRadius: 99,
                      padding: "2px 10px",
                      fontSize: 12,
                      fontWeight: 700,
                      fontFamily: "'JetBrains Mono', monospace",
                      boxShadow: "0 2px 6px rgba(220, 38, 38, 0.15)",
                    }}
                  >
                    ⏱ {recordDuration.toFixed(1)}s
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons: Record & Upload */}
            <div style={{ display: "flex", gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
              {!recording ? (
                <button
                  onClick={() => {
                    if (loading) cancelAnalysis();
                    startRecording();
                  }}
                  style={{
                    flex: "1 1 240px",
                    background: "linear-gradient(135deg, #EA580C 0%, #D97706 100%)",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: 12,
                    padding: "14px 24px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                    boxShadow: "0 6px 18px -2px rgba(234, 88, 12, 0.35)",
                    transition: "all 0.15s ease",
                  }}
                >
                  <span style={{ fontSize: 11 }}>●</span>
                  <span>Start Chanting</span>
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  style={{
                    flex: "1 1 240px",
                    background: THEME.crimson,
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: 12,
                    padding: "14px 24px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                    boxShadow: "0 6px 18px -2px rgba(220, 38, 38, 0.40)",
                    animation: "pulseGlow 1.4s infinite",
                  }}
                >
                  <span>■</span>
                  <span>Stop Recording ({recordDuration.toFixed(1)}s)</span>
                </button>
              )}

              <button
                onClick={() => {
                  if (loading) cancelAnalysis();
                  if (fileInputRef.current) fileInputRef.current.value = "";
                  fileInputRef.current.click();
                }}
                style={{
                  flex: "1 1 240px",
                  background: "#FFFFFF",
                  color: THEME.textPrimary,
                  border: `1.5px solid ${THEME.cardBorder}`,
                  borderRadius: 12,
                  padding: "14px 20px",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 2px 6px rgba(120, 80, 40, 0.04)",
                  transition: "all 0.15s ease",
                }}
                title="Upload audio/video chant in WAV, MP3, M4A, OGG, FLAC, MOV, MP4 formats"
              >
                <span>📁</span>
                <span>Upload Audio or Video (WAV, MP3, M4A, MOV, MP4)</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.mpeg,.mpga,.m4a,.aac,.ogg,.flac,.webm,.mov,.mp4,.m4v,.3gp,audio/*,video/*"
                style={{ display: "none" }}
                onChange={handleFile}
              />
            </div>

            <div style={{ color: THEME.textMuted, fontSize: 12, textAlign: "center", marginBottom: 20 }}>
              Automatic client-side PCM decoding guarantees lossless 16-bit WAV transmission without server dependencies.
            </div>

            {/* Recorded Audio Preview & Evaluation Launch Card */}
            {audioURL && (
              <div
                style={{
                  background: "#FAF6F0",
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 14,
                  padding: "18px 20px",
                  marginBottom: 16,
                  animation: "fadeUp 0.25s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 16 }}>🎵</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: THEME.textPrimary }}>
                      Recorded Audio Preview
                    </span>
                    <span style={{ fontSize: 11, background: THEME.emeraldBg, color: THEME.emerald, padding: "2px 8px", borderRadius: 99, fontWeight: 700 }}>
                      Ready
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setAudioBlob(null);
                      setAudioURL(null);
                      setResult(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: THEME.textMuted,
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    ✕ Clear / Re-record
                  </button>
                </div>

                <audio
                  controls
                  src={audioURL}
                  style={{
                    width: "100%",
                    borderRadius: 8,
                    height: 40,
                    marginBottom: 16,
                  }}
                />

                {!loading && (
                  <button
                    onClick={analyze}
                    style={{
                      width: "100%",
                      background: "linear-gradient(135deg, #EA580C 0%, #D97706 100%)",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: 12,
                      padding: "15px",
                      fontSize: 15,
                      fontWeight: 700,
                      letterSpacing: "0.04em",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                      boxShadow: "0 8px 24px -2px rgba(234, 88, 12, 0.45)",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <span>✨</span>
                    <span>{result ? "Re-Evaluate My Recitation →" : "Evaluate My Recitation →"}</span>
                  </button>
                )}
              </div>
            )}

            {/* Dynamic Multi-Stage Loading Overlay */}
            {loading && (
              <div
                style={{
                  background: "#FAF6F0",
                  border: `1.5px solid ${THEME.accentOrange}`,
                  borderRadius: 14,
                  padding: "24px 20px",
                  textAlign: "center",
                  animation: "fadeUp 0.25s ease",
                }}
              >
                <div style={{ display: "inline-block", fontSize: 24, animation: "spinSlow 2s linear infinite", marginBottom: 8 }}>
                  ⏳
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: THEME.textPrimary, marginBottom: 4 }}>
                  Evaluating Vedic Phonetics & Svara ({loadingElapsed}s)
                </div>
                <div style={{ fontSize: 12, color: THEME.textMuted, marginBottom: 18 }}>
                  Running Sanskrit neural phonetics + local word DTW alignment
                </div>

                {/* 3 Progress Milestones */}
                <div style={{ maxWidth: 440, margin: "0 auto 20px", textAlign: "left", display: "flex", flexDirection: "column", gap: 10 }}>
                  {[
                    { step: 1, label: "Zero-phase bandpass & silence trimming", active: loadingStage >= 1, done: loadingStage > 1 },
                    { step: 2, label: "MMS-1B Sanskrit character alignment", active: loadingStage >= 2, done: loadingStage > 2 },
                    { step: 3, label: "DTW Svara & micro-phonetic scoring", active: loadingStage >= 3, done: false },
                  ].map((s) => (
                    <div
                      key={s.step}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        fontSize: 12,
                        color: s.done ? THEME.emerald : s.active ? THEME.accentOrange : THEME.textMuted,
                        fontWeight: s.active ? 700 : 500,
                      }}
                    >
                      <span
                        style={{
                          width: 20,
                          height: 20,
                          borderRadius: "50%",
                          background: s.done ? THEME.emeraldBg : s.active ? "#FFF7ED" : "#EAE2D6",
                          border: `1px solid ${s.done ? THEME.emerald : s.active ? THEME.accentOrange : "#D6CEBE"}`,
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        {s.done ? "✓" : s.step}
                      </span>
                      <span>{s.label}</span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={cancelAnalysis}
                  style={{
                    background: "#FFFFFF",
                    color: THEME.crimson,
                    border: `1px solid ${THEME.crimsonBorder}`,
                    borderRadius: 99,
                    padding: "7px 18px",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    boxShadow: "0 2px 6px rgba(220, 38, 38, 0.10)",
                  }}
                >
                  <span>✕</span>
                  <span>Cancel Evaluation & Return</span>
                </button>
              </div>
            )}

            {/* Error Notification */}
            {error && (
              <div
                style={{
                  background: THEME.crimsonBg,
                  border: `1px solid ${THEME.crimsonBorder}`,
                  borderRadius: 12,
                  padding: "14px 18px",
                  color: THEME.crimson,
                  fontSize: 13,
                  marginTop: 16,
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <span style={{ fontSize: 18 }}>⚠️</span>
                <span>{error}</span>
              </div>
            )}
          </div>
        </main>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          PAGE 2: ANALYSIS DASHBOARD (currentPage === "results")
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentPage === "results" && (
        <main style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 20px 80px", animation: "fadeUp 0.3s ease" }}>
          
          {/* ── 1. Top Action Bar on Results Page ── */}
          <div
            className="top-action-bar"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 20,
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            {/* Left: Return to Studio button */}
            <button
              onClick={() => setCurrentPage("studio")}
              className="hover-lift"
              style={{
                background: "#FFFFFF",
                border: `1.5px solid ${THEME.cardBorder}`,
                color: THEME.accentOrange,
                padding: "9px 20px",
                borderRadius: 99,
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                boxShadow: "0 2px 8px rgba(120, 80, 40, 0.05)",
                transition: "all 0.15s ease",
              }}
            >
              <span>←</span>
              <span>Back to Chanting Studio</span>
            </button>

            {/* Right: Quick audio comparison pills */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              {audioURL && (
                <button
                  onClick={togglePlayUserFullAudio}
                  className="hover-lift"
                  style={{
                    background: userFullPlaying ? THEME.emerald : "#FFFFFF",
                    color: userFullPlaying ? "#FFFFFF" : THEME.textPrimary,
                    border: `1.5px solid ${userFullPlaying ? THEME.emerald : THEME.cardBorder}`,
                    borderRadius: 99,
                    padding: "8px 18px",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    boxShadow: "0 2px 8px rgba(120, 80, 40, 0.05)",
                    transition: "all 0.15s ease",
                  }}
                >
                  <span>{userFullPlaying ? "■" : "▶"}</span>
                  <span>{userFullPlaying ? "Playing My Recording..." : "Play My Full Recording"}</span>
                </button>
              )}

              <button
                onClick={togglePlayReferenceMantra}
                className="hover-lift"
                style={{
                  background: refPlaying ? THEME.accentAmber : "#FFF7ED",
                  color: refPlaying ? "#FFFFFF" : THEME.accentOrange,
                  border: `1.5px solid ${refPlaying ? THEME.accentAmber : "#FED7AA"}`,
                  borderRadius: 99,
                  padding: "8px 18px",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  boxShadow: "0 2px 8px rgba(234, 88, 12, 0.10)",
                  transition: "all 0.15s ease",
                }}
              >
                <span>{refPlaying ? "■" : "▶"}</span>
                <span>{refPlaying ? "Playing Master Shloka..." : "Play Reference Shloka"}</span>
              </button>
            </div>
          </div>

          {/* ── 2. Prominent Mantra Verification Gate Banner ── */}
          {r && (
            <div
              style={{
                background: r.is_valid_mantra ? THEME.emeraldBg : THEME.crimsonBg,
                border: `1px solid ${r.is_valid_mantra ? THEME.emeraldBorder : THEME.crimsonBorder}`,
                borderLeft: `5px solid ${r.is_valid_mantra ? THEME.emerald : THEME.crimson}`,
                borderRadius: 16,
                padding: "20px 24px",
                marginBottom: 24,
                boxShadow: "0 4px 16px rgba(120, 80, 40, 0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 24 }}>{r.is_valid_mantra ? "✓" : "⚠️"}</span>
                  <div>
                    <div
                      style={{
                        fontSize: 15,
                        fontWeight: 700,
                        letterSpacing: "0.04em",
                        color: r.is_valid_mantra ? "#065F46" : THEME.crimson,
                      }}
                    >
                      {r.is_valid_mantra
                        ? `${r.mantra_name || currentMantra.name} Verified · ${r.matched_words_count ?? 8}/${r.word_alignment?.length || 8} Canonical Words Matched`
                        : `Mantra Verification Gate Alert · ${r.matched_words_count || 0}/${r.word_alignment?.length || 8} Words Verified`}
                    </div>
                    <div style={{ fontSize: 13, color: THEME.textPrimary, marginTop: 4, lineHeight: 1.5, maxWidth: 900 }}>
                      {r.gate_message}
                    </div>
                  </div>
                </div>

                {!r.is_valid_mantra && (
                  <button
                    onClick={() => setCurrentPage("studio")}
                    style={{
                      background: THEME.crimson,
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: 99,
                      padding: "8px 18px",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      boxShadow: "0 2px 8px rgba(220, 38, 38, 0.25)",
                    }}
                  >
                    <span>↺</span>
                    <span>Try Recording Again</span>
                  </button>
                )}
              </div>

              {r.user_transcript && (
                <div style={{ marginTop: 10, fontSize: 11, color: THEME.textSecondary, fontStyle: "italic", borderTop: `1px solid ${r.is_valid_mantra ? THEME.emeraldBorder : THEME.crimsonBorder}`, paddingTop: 8 }}>
                  ASR Transcript: "{r.user_transcript}" · Duration Ratio: {r.duration_ratio || 1.0}x
                </div>
              )}
            </div>
          )}

          {/* ── 3. Hero Score & 4-Pillar Vedic Telemetry Grid (2-Column Top Row) ── */}
          {r && (
            <div
              className="top-hero-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(320px, 380px) 1fr",
                gap: 20,
                marginBottom: 24,
                alignItems: "stretch",
              }}
            >
              {/* Left Card — Animated Circular SVG Resonance Gauge */}
              <div
                className="hover-lift"
                style={{
                  background: THEME.cardBg,
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 20,
                  padding: "28px 24px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange, marginBottom: 12 }}>
                  Vedic Resonance Index
                </div>
                <RadialGauge score={r.overall_score || sc.overall || 0} grade={r.overall_grade} />
                
                {/* Phonetic Word Summary Pills */}
                {r.phonetic_evaluation?.summary && (
                  <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap", justifyContent: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: THEME.emerald, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "3px 10px", borderRadius: 99 }}>
                      ✓ {r.phonetic_evaluation.summary.acceptable || 0} Acceptable
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: THEME.amber, background: THEME.amberBg, border: `1px solid ${THEME.amberBorder}`, padding: "3px 10px", borderRadius: 99 }}>
                      ◐ {r.phonetic_evaluation.summary.review || 0} Needs Review
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: THEME.textSecondary, background: "#F5F0E8", border: "1px solid #EAE2D6", padding: "3px 10px", borderRadius: 99, fontFamily: "'JetBrains Mono', monospace" }}>
                      Avg: {r.phonetic_evaluation.summary.average_word_score || 0}%
                    </span>
                  </div>
                )}
              </div>

              {/* Right Card — 4 Macro Vedic Dimensions (2x2 Grid) */}
              <div
                className="hover-lift"
                style={{
                  background: THEME.cardBg,
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 20,
                  padding: "24px 26px",
                  boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                      Macro Telemetry
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                      4 Pillars of Sanskrit Chanting
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: THEME.textMuted }}>
                    Click any pillar to inspect details
                  </div>
                </div>

                {/* 2x2 Grid of Dimension Cards */}
                <div
                  className="macro-2x2-grid"
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 14,
                  }}
                >
                  {[
                    {
                      key: "uccharana",
                      tab: "uccharana",
                      icon: "🔤",
                      title: "Ucchāraṇa",
                      devanagari: "उच्चारण",
                      subtitle: "Pronunciation & Phonemic Fidelity",
                      score: d.uccharana?.score ?? sc.text_similarity ?? 0,
                    },
                    {
                      key: "svara",
                      tab: "svara",
                      icon: "🎵",
                      title: "Svara",
                      devanagari: "स्वर",
                      subtitle: "Pitch Accents (Udātta/Anudātta)",
                      score: d.svara?.score ?? sc.pitch_combined ?? 0,
                    },
                    {
                      key: "laya",
                      tab: "layanada",
                      icon: "🥁",
                      title: "Laya",
                      devanagari: "लय",
                      subtitle: "Tempo, Rhythmic Flow & Mātrā",
                      score: d.laya?.score ?? sc.tempo_similarity ?? 0,
                    },
                    {
                      key: "nada",
                      tab: "layanada",
                      icon: "🔔",
                      title: "Nāda",
                      devanagari: "नाद",
                      subtitle: "Vocal Resonance & Timbre Match",
                      score: d.nada?.score ?? sc.mfcc_similarity ?? 0,
                    },
                  ].map((dim) => {
                    const numScore = Math.round(dim.score);
                    const col = getScoreColor(numScore);
                    return (
                      <div
                        key={dim.key}
                        onClick={() => {
                          setActiveTab(dim.tab);
                          document.getElementById("diagnostic-tabs-section")?.scrollIntoView({ behavior: "smooth" });
                        }}
                        className="hover-lift"
                        style={{
                          background: "#FAF6F0",
                          border: `1.5px solid ${THEME.cardBorder}`,
                          borderRadius: 14,
                          padding: "16px 18px",
                          cursor: "pointer",
                          transition: "all 0.18s ease",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                        }}
                      >
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: THEME.textPrimary }}>
                              {dim.icon} {dim.title} <span style={{ fontSize: 13, color: THEME.textSecondary, fontFamily: "'Noto Serif Devanagari', serif", fontWeight: 600 }}>({dim.devanagari})</span>
                            </span>
                            <span style={{ fontSize: 16, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono', monospace" }}>
                              {numScore}%
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 12 }}>
                            {dim.subtitle}
                          </div>
                        </div>

                        <div>
                          <div style={{ background: "#EAE2D6", borderRadius: 99, height: 6, overflow: "hidden", marginBottom: 6 }}>
                            <div
                              style={{
                                width: `${Math.min(numScore, 100)}%`,
                                height: "100%",
                                borderRadius: 99,
                                background: `linear-gradient(90deg, ${col}CC, ${col})`,
                                transition: "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)",
                              }}
                            />
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 10, color: THEME.textMuted }}>
                            <span>{gradeEmoji(numScore)} {numScore >= 80 ? "Mastery" : numScore >= 60 ? "Proficient" : "Developing"}</span>
                            <span style={{ color: THEME.accentOrange, fontWeight: 700 }}>Inspect Details →</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── 4. Interactive "Expected vs. Heard" 8-Word Alignment Ribbon ── */}
          {wordAlign.length > 0 && (
            <div
              className="hover-lift"
              style={{
                background: THEME.cardBg,
                border: `1px solid ${THEME.cardBorder}`,
                borderRadius: 20,
                padding: "24px 26px",
                marginBottom: 24,
                boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                    Chronological Word Alignment
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                    Interactive {wordAlign.length || 8}-Word Akṣara & Audio Alignment Map
                  </div>
                </div>
                <div style={{ fontSize: 12, color: THEME.textMuted }}>
                  Click any word to hear your audio slice & inspect contrasts
                </div>
              </div>

              {/* Responsive 8-word strip */}
              <div
                className="word-strip-grid"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: 12,
                }}
              >
                {wordAlign.map((w) => {
                  const isGreen = w.status === "green" || w.color === "green";
                  const isWhite = w.status === "white" || w.color === "white";

                  const cardBg = isGreen ? "#ECFDF5" : isWhite ? "#FFFBEB" : "#FEF2F2";
                  const cardBorder = isGreen ? "#6EE7B7" : isWhite ? "#FCD34D" : "#FCA5A5";
                  const cardText = isGreen ? "#065F46" : isWhite ? "#92400E" : "#991B1B";
                  const badgeBg = isGreen ? "#D1FAE5" : isWhite ? "#FEF3C7" : "#FEE2E2";

                  const isSelected = selectedWordIdx === w.index;
                  const scoreVal = Math.round(w.combined_score || w.word_match_score || 0);

                  const handleWordClick = () => {
                    setSelectedWordIdx(w.index);
                    setActiveTab("phonetic");
                    if (audioURL && w.user_start_sec != null) {
                      playAudioSpan(audioURL, w.user_start_sec, w.user_end_sec);
                    }
                    setTimeout(() => {
                      const el = document.getElementById(`word-card-${w.index}`);
                      if (el) {
                        el.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    }, 60);
                  };

                  return (
                    <div
                      key={w.index}
                      onClick={handleWordClick}
                      className="hover-lift"
                      style={{
                        background: isSelected ? "#FFFFFF" : cardBg,
                        border: `1.5px solid ${isSelected ? THEME.accentOrange : cardBorder}`,
                        borderRadius: 14,
                        padding: "14px 12px",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        textAlign: "center",
                        gap: 4,
                        transition: "all 0.18s ease",
                        boxShadow: isSelected ? "0 8px 22px -3px rgba(234, 88, 12, 0.25)" : "0 2px 6px rgba(120, 80, 40, 0.04)",
                        position: "relative",
                      }}
                    >
                      {/* Top: Word # & Score Badge */}
                      <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center", marginBottom: 2 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: THEME.textMuted }}>
                          #{w.index + 1}
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: cardText,
                            background: badgeBg,
                            padding: "1px 6px",
                            borderRadius: 99,
                            fontFamily: "'JetBrains Mono', monospace",
                          }}
                        >
                          {scoreVal}%
                        </span>
                      </div>

                      {/* Word in Devanagari */}
                      <div
                        style={{
                          fontSize: 19,
                          fontWeight: 700,
                          color: THEME.textPrimary,
                          fontFamily: "'Noto Serif Devanagari', serif",
                          lineHeight: 1.3,
                          marginTop: 2,
                        }}
                      >
                        {w.expected_devanagari || w.devanagari}
                      </div>

                      {/* Word IAST */}
                      <div
                        style={{
                          fontSize: 11,
                          color: THEME.textSecondary,
                          fontStyle: "italic",
                          fontFamily: "'Cormorant Garamond', Georgia, serif",
                        }}
                      >
                        {w.expected_iast || w.iast}
                      </div>

                      {/* Heard Token */}
                      <div
                        style={{
                          fontSize: 10,
                          color: THEME.textMuted,
                          maxWidth: 120,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          marginTop: 2,
                        }}
                      >
                        Heard: {w.heard_token ? `"${w.heard_token}"` : (w.user_start_sec == null ? "(not spoken)" : "—")}
                      </div>

                      {/* Mini Play Slice Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleWordClick();
                        }}
                        title={w.user_start_sec != null ? "Play audio slice for this word" : "Word was not detected"}
                        disabled={w.user_start_sec == null}
                        style={{
                          marginTop: 4,
                          background: w.user_start_sec != null ? (isSelected ? THEME.accentOrange : "#FFFFFF") : "#EAE2D6",
                          color: w.user_start_sec != null ? (isSelected ? "#FFFFFF" : cardText) : THEME.textMuted,
                          border: `1px solid ${w.user_start_sec != null ? cardBorder : "#EAE2D6"}`,
                          borderRadius: 99,
                          padding: "2px 10px",
                          fontSize: 10,
                          fontWeight: 700,
                          cursor: w.user_start_sec != null ? "pointer" : "not-allowed",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          boxShadow: "0 1px 4px rgba(120, 80, 40, 0.05)",
                        }}
                      >
                        <span>{w.user_start_sec != null ? "🔊 Play" : "—"}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── 5. Diagnostic Tabs Section ── */}
          <div
            id="diagnostic-tabs-section"
            className="hover-lift"
            style={{
              background: THEME.cardBg,
              border: `1px solid ${THEME.cardBorder}`,
              borderRadius: 20,
              padding: "26px 28px",
              boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
              marginBottom: 24,
            }}
          >
            {/* Sleek Pill Segmented Control Tab Bar */}
            <div
              style={{
                display: "flex",
                background: "#F5EFEB",
                padding: "5px",
                borderRadius: 99,
                gap: 6,
                border: `1px solid ${THEME.cardBorder}`,
                marginBottom: 24,
                flexWrap: "wrap",
                boxShadow: "inset 0 1px 3px rgba(120, 80, 40, 0.05)",
              }}
            >
              {[
                { id: "phonetic", icon: "🔬", label: `${phoneticWords.length || 8}-Word Phonetic Studio`, count: phoneticWords.length || 8 },
                { id: "uccharana", icon: "🔤", label: "Ucchāraṇa (Pronunciation)" },
                { id: "svara", icon: "🎵", label: "Svara (Pitch & Accent)" },
                { id: "layanada", icon: "🥁", label: "Laya & Nāda (Rhythm & Timbre)" },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      flex: "1 1 auto",
                      padding: "9px 18px",
                      borderRadius: 99,
                      border: "none",
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: 700,
                      background: isActive ? "linear-gradient(135deg, #EA580C 0%, #D97706 100%)" : "transparent",
                      color: isActive ? "#FFFFFF" : THEME.textSecondary,
                      boxShadow: isActive ? "0 4px 14px rgba(234, 88, 12, 0.35)" : "none",
                      transition: "all 0.18s ease",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                    }}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                    {tab.count != null && (
                      <span
                        style={{
                          fontSize: 10,
                          background: isActive ? "rgba(255, 255, 255, 0.25)" : "#EAE2D6",
                          color: isActive ? "#FFFFFF" : THEME.textSecondary,
                          borderRadius: 99,
                          padding: "1px 7px",
                        }}
                      >
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* ── Tab 1: 8-Word Phonetic Studio (2-Column Grid) ── */}
            {activeTab === "phonetic" && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                      Local Word-by-Word Diagnostics
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                      {phoneticWords.length || 8}-Word Phonetic Studio (Local DTW & Acoustic Resonance)
                    </div>
                  </div>
                  {r?.phonetic_evaluation?.summary && (
                    <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
                      <span style={{ color: THEME.emerald, fontWeight: 700, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "3px 10px", borderRadius: 99 }}>
                        ✓ {r.phonetic_evaluation.summary.acceptable} Acceptable
                      </span>
                      <span style={{ color: THEME.amber, fontWeight: 700, background: THEME.amberBg, border: `1px solid ${THEME.amberBorder}`, padding: "3px 10px", borderRadius: 99 }}>
                        ◐ {r.phonetic_evaluation.summary.review} Review
                      </span>
                      <span style={{ color: THEME.textSecondary, background: "#F5F0E8", border: "1px solid #EAE2D6", padding: "3px 10px", borderRadius: 99, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>
                        Avg Match: {r.phonetic_evaluation.summary.average_word_score}%
                      </span>
                    </div>
                  )}
                </div>

                {/* Single Vedic Pronunciation Explanation Banner */}
                <div
                  style={{
                    background: "#FAF6F0",
                    border: `1px solid ${THEME.cardBorder}`,
                    borderRadius: 12,
                    padding: "14px 18px",
                    marginBottom: 20,
                    fontSize: 12,
                    lineHeight: 1.6,
                    color: THEME.textSecondary,
                  }}
                >
                  <div style={{ fontWeight: 700, color: THEME.accentOrange, marginBottom: 4 }}>
                    Vedic Phonetic Articulation & Vowel Prosody (Varṇa & Mātrā)
                  </div>
                  <div>
                    Evaluates vocal resonance, consonant articulation (Sthāna & Prayatna), and short vs. long vowel timing (Hrasva & Dīrgha Mātrā) against authentic master chanting. Use the dual audio buttons on each card to compare your voice against the Guru's master recitation.
                  </div>
                </div>

                {/* Responsive 2-column grid */}
                {phoneticWords.length > 0 ? (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
                      gap: 16,
                    }}
                  >
                    {phoneticWords.map((w) => (
                      <PhoneticWordCard
                        key={w.index}
                        word={w}
                        isSelected={selectedWordIdx === w.index}
                        audioURL={audioURL}
                        refAudioURL={refAudioURL}
                      />
                    ))}
                  </div>
                ) : (
                  <div style={{ color: THEME.textMuted, textAlign: "center", padding: "40px 0" }}>
                    Record or upload audio to inspect word-level phonetics.
                  </div>
                )}
              </div>
            )}

            {/* ── Tab 2: Ucchāraṇa (Pronunciation) ── */}
            {activeTab === "uccharana" && (
              <div>
                {!r ? (
                  <div style={{ color: THEME.textMuted, textAlign: "center", padding: "40px 0" }}>
                    Record or upload audio to inspect Ucchāraṇa diagnostics.
                  </div>
                ) : (
                  <>
                    {/* 3 Elevated KPI Stat Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 20 }}>
                      {[
                        { label: "Character Similarity", val: d.uccharana?.char_sim ?? sc.text_similarity ?? 0, desc: "Character-level sequence alignment" },
                        { label: "Word Similarity", val: d.uccharana?.word_sim ?? 0, desc: "Isolated Sanskrit token matching" },
                        { label: "Syllable (Akṣara)", val: d.uccharana?.syl_sim ?? 0, desc: "Syllable boundary congruence" },
                      ].map((kpi) => (
                        <div
                          key={kpi.label}
                          className="hover-lift"
                          style={{
                            background: "#FAF6F0",
                            border: `1.5px solid ${THEME.cardBorder}`,
                            borderRadius: 14,
                            padding: "16px",
                            textAlign: "center",
                          }}
                        >
                          <div style={{ fontSize: 11, color: THEME.textMuted, textTransform: "uppercase", marginBottom: 6, fontWeight: 700 }}>
                            {kpi.label}
                          </div>
                          <div style={{ fontSize: 32, fontWeight: 700, color: getScoreColor(kpi.val), fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.1, marginBottom: 6 }}>
                            {Math.round(kpi.val)}%
                          </div>
                          <div style={{ fontSize: 11, color: THEME.textSecondary }}>
                            {kpi.desc}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Full Reference vs. Heard Comparison Banner */}
                    <div
                      style={{
                        background: "#FAF6F0",
                        border: `1.5px solid ${THEME.cardBorder}`,
                        borderRadius: 14,
                        padding: "18px 20px",
                        marginBottom: 20,
                      }}
                    >
                      <div style={{ fontSize: 11, fontWeight: 700, color: THEME.accentOrange, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>
                        Canonical Reference vs. Recognized ASR Recitation
                      </div>

                      <div style={{ marginBottom: 14, background: "#FFFFFF", border: `1px solid ${THEME.cardBorder}`, borderRadius: 10, padding: "12px 16px" }}>
                        <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 600, marginBottom: 4 }}>
                          CANONICAL SHLOKA:
                        </div>
                        <div style={{ fontSize: 17, fontWeight: 700, color: THEME.textPrimary, fontFamily: "'Noto Serif Devanagari', serif", lineHeight: 1.5 }}>
                          {r.mantra || currentMantra.fullDevanagari}
                        </div>
                        <div style={{ fontSize: 12, color: THEME.textSecondary, fontStyle: "italic", marginTop: 2 }}>
                          {currentMantra.iast}
                        </div>
                      </div>

                      <div style={{ background: "#FFFFFF", border: `1px solid ${THEME.cardBorder}`, borderRadius: 10, padding: "12px 16px" }}>
                        <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 600, marginBottom: 4 }}>
                          HEARD ASR TRANSCRIPTION (MMS-1B):
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: r.is_valid_mantra ? THEME.emerald : THEME.amber, fontFamily: "'Noto Serif Devanagari', serif", lineHeight: 1.5 }}>
                          {r.user_transcript ? r.user_transcript : "(No recognizable Sanskrit words detected)"}
                        </div>
                      </div>
                    </div>

                    {d.uccharana?.issues?.length > 0 && (
                      <div style={{ marginBottom: 18 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: THEME.crimson, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                          Pronunciation Issues Detected
                        </div>
                        <FeedbackList items={d.uccharana.issues} variant="error" />
                      </div>
                    )}

                    {d.uccharana?.fixes?.length > 0 && (
                      <div style={{ marginBottom: 18 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: THEME.amber, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                          How To Improve Pronunciation
                        </div>
                        <FeedbackList items={d.uccharana.fixes} variant="warning" />
                      </div>
                    )}

                    {(!d.uccharana?.issues || d.uccharana.issues.length === 0) && (
                      <div style={{ color: THEME.emerald, fontSize: 13, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "14px 18px", borderRadius: 10, fontWeight: 600 }}>
                        ✓ High ucchāraṇa fidelity — no major phonemic articulation errors detected.
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* ── Tab 3: Svara (Pitch & Accent) ── */}
            {activeTab === "svara" && (
              <div>
                {!r ? (
                  <div style={{ color: THEME.textMuted, textAlign: "center", padding: "40px 0" }}>
                    Record or upload audio to inspect Vedic Svara diagnostics.
                  </div>
                ) : (
                  <>
                    {/* 5-Bar Vedic Pitch Telemetry Card */}
                    <div
                      style={{
                        background: "#FAF6F0",
                        border: `1.5px solid ${THEME.cardBorder}`,
                        borderRadius: 16,
                        padding: "20px 24px",
                        marginBottom: 24,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 700, color: THEME.accentOrange, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                            Vedic Pitch Accent Sub-Score Breakdown
                          </div>
                          <div style={{ fontSize: 16, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                            Pitch Shape, Zone (U/A/S) & Slope Telemetry
                          </div>
                        </div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: THEME.accentOrange, fontFamily: "'JetBrains Mono', monospace" }}>
                          Composite: {Math.round(d.svara?.score ?? sc.pitch_combined ?? 0)}%
                        </div>
                      </div>

                      <ScoreBar label="1. Contour Shape Similarity (DTW Path Alignment)" score={sc.pitch_breakdown?.contour_shape} />
                      <ScoreBar label="2. Pitch Zone Accuracy (Udātta [High] / Anudātta [Low] / Svarita [Falling])" score={sc.pitch_breakdown?.zone_accuracy} />
                      <ScoreBar label="3. Accent Placement (Svara-sthāna timing)" score={sc.pitch_breakdown?.accent_placement} />
                      <ScoreBar label="4. Intra-Syllable Pitch Shape (Rising, Falling, Circumflex)" score={sc.pitch_breakdown?.syllable_shape} />
                      <ScoreBar label="5. Slope / Steepness (Pitch velocity transition)" score={sc.pitch_breakdown?.slope_steepness} />
                    </div>

                    {/* Word-by-Word Svara Diagnostics Title */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: THEME.textPrimary, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        Word-by-Word Svara Diagnostics ({wordDetail.length} Canonical Words)
                      </div>
                      <div style={{ fontSize: 11, color: THEME.textMuted }}>
                        Udātta ↗ (High) · Anudātta _ (Low) · Svarita ⌒ (Falling)
                      </div>
                    </div>

                    {/* 2-Column Grid for Svara Word Cards */}
                    {wordDetail.length > 0 ? (
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
                          gap: 14,
                        }}
                      >
                        {wordDetail.map((item, idx) => <SvaraWordCard key={idx} item={item} />)}
                      </div>
                    ) : (
                      <div style={{ color: THEME.emerald, fontSize: 13, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "16px 20px", borderRadius: 10, fontWeight: 600 }}>
                        ✓ All words carry authentic Vedic svara accents.
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* ── Tab 4: Laya & Nāda (Rhythm, Cadence & Vocal Resonance) ── */}
            {activeTab === "layanada" && (
              <div>
                {!r ? (
                  <div style={{ color: THEME.textMuted, textAlign: "center", padding: "40px 0" }}>
                    Record or upload audio to view Laya & Nāda diagnostics.
                  </div>
                ) : (
                  <>
                    {/* Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                          Temporal & Timbral Telemetry
                        </div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                          Laya (Rhythm & Tempo) & Nāda (Vocal Resonance)
                        </div>
                      </div>
                      <div style={{ fontSize: 12, color: THEME.textMuted }}>
                        Mātrā pace ratios, syllable velocity & harmonic overtone analysis
                      </div>
                    </div>

                    {/* 3 Visual Gauge Cards: Laya, Tempo Meter, Nāda */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                        gap: 16,
                        marginBottom: 24,
                      }}
                    >
                      {/* Card 1: Laya (Rhythm Score) */}
                      <div
                        className="hover-lift"
                        style={{
                          background: "#FAF6F0",
                          border: `1.5px solid ${THEME.cardBorder}`,
                          borderRadius: 16,
                          padding: "20px",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                        }}
                      >
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: THEME.textPrimary }}>
                              🥁 Laya (लय)
                            </span>
                            <span style={{ fontSize: 26, fontWeight: 700, color: getScoreColor(d.laya?.score || 0), fontFamily: "'JetBrains Mono', monospace" }}>
                              {Math.round(d.laya?.score || 0)}%
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 12 }}>
                            Rhythm & Cadence Onset Matching
                          </div>
                        </div>

                        <div>
                          <ScoreBar label="Onset Flow Match" score={d.laya?.score || 0} />
                          <div style={{ fontSize: 11, color: THEME.textSecondary, lineHeight: 1.5, marginTop: 4 }}>
                            Measures rhythmic pulse coherence and syllable duration proportion against the golden reference chanting.
                          </div>
                        </div>
                      </div>

                      {/* Card 2: Chant Tempo / Duration Ratio Meter */}
                      <div
                        className="hover-lift"
                        style={{
                          background: "#FAF6F0",
                          border: `1.5px solid ${THEME.cardBorder}`,
                          borderRadius: 16,
                          padding: "20px",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                        }}
                      >
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: THEME.textPrimary }}>
                              ⏱ Chant Tempo (Mātrā Velocity)
                            </span>
                            <span
                              style={{
                                fontSize: 22,
                                fontWeight: 700,
                                color: Math.abs((d.laya?.duration_ratio || 1) - 1) < 0.25 ? THEME.emerald : THEME.amber,
                                fontFamily: "'JetBrains Mono', monospace",
                              }}
                            >
                              {d.laya?.duration_ratio != null ? `${d.laya.duration_ratio}x` : "1.0x"}
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 12 }}>
                            Duration Ratio vs. Master Chanting (11.0s)
                          </div>
                        </div>

                        <div>
                          <TempoMeter ratio={d.laya?.duration_ratio || 1.0} />
                          <div style={{ fontSize: 11, color: THEME.textSecondary, lineHeight: 1.5, marginTop: 8 }}>
                            {d.laya?.duration_ratio > 1.35
                              ? "🧘 Vilambita Laya: Slow, meditative tempo. Syllables are well-elongated."
                              : d.laya?.duration_ratio < 0.85
                              ? "⚡ Druta Laya: Fast tempo. Take care not to rush vowel closures."
                              : "★ Madhya Laya: Ideal classical recitation pace matching the master reference."}
                          </div>
                        </div>
                      </div>

                      {/* Card 3: Nāda (Vocal Timbre & Resonance) */}
                      <div
                        className="hover-lift"
                        style={{
                          background: "#FAF6F0",
                          border: `1.5px solid ${THEME.cardBorder}`,
                          borderRadius: 16,
                          padding: "20px",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                        }}
                      >
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: THEME.textPrimary }}>
                              🔔 Nāda (नाद)
                            </span>
                            <span style={{ fontSize: 26, fontWeight: 700, color: getScoreColor(d.nada?.score || 0), fontFamily: "'JetBrains Mono', monospace" }}>
                              {Math.round(d.nada?.score || 0)}%
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 12 }}>
                            Vocal Resonance & Timbre (MFCC)
                          </div>
                        </div>

                        <div>
                          <ScoreBar label="Harmonic Spectrum Match" score={d.nada?.score || 0} />
                          <div style={{ fontSize: 11, color: THEME.textSecondary, lineHeight: 1.5, marginTop: 4 }}>
                            Quantifies deep throat resonance, vocal tract openness, and authentic Vedic harmonic overtone balance.
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Detailed Issues & Fixes for Laya & Nāda */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
                      {/* Laya Feedback */}
                      <div style={{ background: "#FAF6F0", border: `1px solid ${THEME.cardBorder}`, borderRadius: 14, padding: "16px 20px" }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: THEME.accentOrange, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                          Laya (Rhythm) Coaching
                        </div>
                        {d.laya?.issues?.length > 0 ? (
                          <FeedbackList items={d.laya.issues} variant="error" />
                        ) : (
                          <div style={{ color: THEME.emerald, fontSize: 12, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "10px 14px", borderRadius: 8, fontWeight: 600 }}>
                            ✓ Steady, balanced rhythmic cadence.
                          </div>
                        )}
                        {d.laya?.fixes?.length > 0 && (
                          <div style={{ marginTop: 10 }}>
                            <FeedbackList items={d.laya.fixes} variant="warning" />
                          </div>
                        )}
                      </div>

                      {/* Nāda Feedback */}
                      <div style={{ background: "#FAF6F0", border: `1px solid ${THEME.cardBorder}`, borderRadius: 14, padding: "16px 20px" }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: THEME.accentOrange, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                          Nāda (Resonance) Coaching
                        </div>
                        {d.nada?.issues?.length > 0 ? (
                          <FeedbackList items={d.nada.issues} variant="error" />
                        ) : (
                          <div style={{ color: THEME.emerald, fontSize: 12, background: THEME.emeraldBg, border: `1px solid ${THEME.emeraldBorder}`, padding: "10px 14px", borderRadius: 8, fontWeight: 600 }}>
                            ✓ Authentic vocal tract openness and natural harmonic richness.
                          </div>
                        )}
                        {d.nada?.fixes?.length > 0 && (
                          <div style={{ marginTop: 10 }}>
                            <FeedbackList items={d.nada.fixes} variant="warning" />
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* ── 6. Bottom Executive Coaching Row (Priority Focus Areas + Sādhu Praises) ── */}
          {r && (
            <div
              className="coaching-2col-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
                gap: 20,
                marginBottom: 24,
              }}
            >
              {/* Left Card: Priority Focus Areas */}
              <div
                className="hover-lift"
                style={{
                  background: THEME.cardBg,
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 20,
                  padding: "24px 26px",
                  boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.accentOrange }}>
                        Optimization Roadmap
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                        🎯 Priority Focus Areas (Ranked by Impact)
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: THEME.textMuted }}>
                      Gap × Weight Impact
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {priorityItems.map((p, idx) => {
                      const col = getScoreColor(p.score);
                      return (
                        <div
                          key={idx}
                          style={{
                            background: "#FAF6F0",
                            border: `1px solid ${THEME.cardBorder}`,
                            borderRadius: 12,
                            padding: "12px 14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span
                                style={{
                                  width: 22,
                                  height: 22,
                                  borderRadius: "50%",
                                  background: idx === 0 ? THEME.accentOrange : "#EAE2D6",
                                  color: idx === 0 ? "#FFFFFF" : THEME.textSecondary,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  fontSize: 11,
                                  fontWeight: 700,
                                }}
                              >
                                #{idx + 1}
                              </span>
                              <span style={{ fontSize: 13, fontWeight: 700, color: THEME.textPrimary }}>
                                {p.dimension}
                              </span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 13, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono', monospace" }}>
                                {Math.round(p.score)}%
                              </span>
                              <span
                                style={{
                                  fontSize: 10,
                                  fontWeight: 700,
                                  color: idx === 0 ? THEME.accentOrange : THEME.textMuted,
                                  background: idx === 0 ? "#FFF7ED" : "#F5F0E8",
                                  border: `1px solid ${idx === 0 ? "#FED7AA" : "#EAE2D6"}`,
                                  padding: "1px 6px",
                                  borderRadius: 4,
                                }}
                              >
                                Impact: {p.impact}
                              </span>
                            </div>
                          </div>

                          {/* Micro score progress bar */}
                          <div style={{ height: 4, background: "#EAE2D6", borderRadius: 99, overflow: "hidden" }}>
                            <div style={{ width: `${Math.min(p.score, 100)}%`, height: "100%", background: col, borderRadius: 99 }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Card: Sādhu Praises */}
              <div
                className="hover-lift"
                style={{
                  background: THEME.cardBg,
                  border: `1px solid ${THEME.cardBorder}`,
                  borderRadius: 20,
                  padding: "24px 26px",
                  boxShadow: "0 10px 30px -5px rgba(120, 80, 40, 0.06)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: THEME.emerald }}>
                        Authentic Strengths
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: THEME.textPrimary, marginTop: 2 }}>
                        ✨ Sādhu! What You Did Well
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: THEME.emerald, fontWeight: 700 }}>
                      Vedic Mastery Praise
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {allPraises.length > 0 ? (
                      allPraises.map((p, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: THEME.emeraldBg,
                            border: `1px solid ${THEME.emeraldBorder}`,
                            borderLeft: `4px solid ${THEME.emerald}`,
                            borderRadius: 12,
                            padding: "12px 14px",
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 8,
                            fontSize: 12,
                            lineHeight: 1.5,
                            color: "#065F46",
                            fontWeight: 600,
                          }}
                        >
                          <span style={{ fontSize: 14, color: THEME.emerald, lineHeight: 1 }}>✓</span>
                          <span>{p}</span>
                        </div>
                      ))
                    ) : (
                      <div
                        style={{
                          background: THEME.emeraldBg,
                          border: `1px solid ${THEME.emeraldBorder}`,
                          borderRadius: 12,
                          padding: "16px",
                          color: "#065F46",
                          fontSize: 13,
                          lineHeight: 1.5,
                        }}
                      >
                        ✓ Complete Ganesha Shloka recited with verified phonemic presence and clear vocal engagement.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── 7. Full-Width Illuminated Sādhanā Scroll Card ── */}
          {r && (
            <div
              className="hover-lift"
              style={{
                background: "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)",
                border: "1.5px solid #F59E0B",
                borderLeft: "6px solid #D97706",
                borderRadius: 20,
                padding: "26px 30px",
                boxShadow: "0 10px 28px -4px rgba(217, 119, 6, 0.16)",
                marginBottom: 32,
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Saffron Watermark */}
              <div
                style={{
                  position: "absolute",
                  right: -10,
                  bottom: -20,
                  fontSize: 130,
                  opacity: 0.08,
                  fontFamily: "'Noto Serif Devanagari', serif",
                  color: "#D97706",
                  pointerEvents: "none",
                  userSelect: "none",
                }}
              >
                ॐ
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <span style={{ fontSize: 28 }}>🪔</span>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#92400E", fontFamily: "'Cormorant Garamond', Georgia, serif", letterSpacing: "0.02em" }}>
                    Daily Sādhanā (दैनिक साधना) · Spiritual Practice Protocol
                  </div>
                  <div style={{ fontSize: 11, color: "#B45309", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    Vedic Oral Tradition Transmission Protocol
                  </div>
                </div>
              </div>

              <div
                style={{
                  fontSize: 14,
                  color: "#78350F",
                  lineHeight: 1.7,
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  background: "rgba(255, 255, 255, 0.65)",
                  border: "1px solid rgba(245, 158, 11, 0.35)",
                  borderRadius: 12,
                  padding: "16px 20px",
                }}
              >
                {r?.sadhana_tip || "Chant the Ganesha Shloka 11 times daily with attention to Pada-pāṭha (word separation) and Svara melody."}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, fontSize: 11, color: "#B45309", fontWeight: 600 }}>
                <span>{currentMantra.badge}</span>
                <span>{currentMantra.tradition}</span>
              </div>
            </div>
          )}

          {/* ── 8. Bottom Action Studio Buttons ── */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 14,
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={() => setCurrentPage("studio")}
              className="hover-lift"
              style={{
                background: "linear-gradient(135deg, #EA580C 0%, #D97706 100%)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: 99,
                padding: "12px 28px",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                boxShadow: "0 4px 14px rgba(234, 88, 12, 0.35)",
              }}
            >
              <span>🎙️</span>
              <span>Chant Again in Studio</span>
            </button>

            <button
              onClick={resetToStartPage}
              className="hover-lift"
              style={{
                background: "#FFFFFF",
                color: THEME.textSecondary,
                border: `1.5px solid ${THEME.cardBorder}`,
                borderRadius: 99,
                padding: "12px 24px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                boxShadow: "0 2px 6px rgba(120, 80, 40, 0.04)",
              }}
            >
              <span>↺</span>
              <span>Reset All & Start Fresh</span>
            </button>
          </div>
        </main>
      )}

      {/* ─── Sacred Footer ─────────────────────────────────────────────────── */}
      <footer
        style={{
          textAlign: "center",
          color: THEME.textMuted,
          fontSize: 13,
          padding: "24px 20px 36px",
          borderTop: `1px solid ${THEME.cardBorder}`,
          background: "rgba(250, 246, 240, 0.70)",
        }}
      >
        ॐ शान्तिः शान्तिः शान्तिः · Swara Vaidya Vedic Phonetic & Svara Telemetry System
      </footer>
    </>
  );
}
