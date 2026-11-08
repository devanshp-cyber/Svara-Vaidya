import { useState, useRef, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:10000";

// ─── Color Helpers & Badges ──────────────────────────────────────────────────
const gradeColor = (score) => {
  if (score >= 70) return "#10b981"; // Emerald green
  if (score >= 45) return "#f59e0b"; // Saffron amber
  return "#ef4444"; // Coral red
};

const gradeEmoji = (score) => {
  if (score >= 85) return "✓";
  if (score >= 70) return "◐";
  if (score >= 45) return "△";
  return "✗";
};

// ─── Score Bar Component ─────────────────────────────────────────────────────
const ScoreBar = ({ label, score, sublabel, height = 6 }) => {
  const numScore = typeof score === "number" ? Math.round(score) : 0;
  const col = gradeColor(numScore);
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
        <span style={{ fontSize: 13, color: "#c9d1d9", fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: col, fontFamily: "monospace" }}>
          {numScore}% <span style={{ fontSize: 11 }}>{gradeEmoji(numScore)}</span>
        </span>
      </div>
      <div style={{ background: "#21262d", borderRadius: 4, height, overflow: "hidden" }}>
        <div
          style={{
            width: `${Math.min(numScore, 100)}%`,
            height: "100%",
            borderRadius: 4,
            background: `linear-gradient(90deg, ${col}99, ${col})`,
            transition: "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />
      </div>
      {sublabel && <div style={{ fontSize: 11, color: "#8b949e", marginTop: 3 }}>{sublabel}</div>}
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

// ─── SVG Radial Gauge ────────────────────────────────────────────────────────
const RadialGauge = ({ score, size = 170, grade = "" }) => {
  const numScore = Math.round(score || 0);
  const radius = (size - 24) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (Math.min(numScore, 100) / 100) * circumference;
  const color = gradeColor(numScore);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#21262d"
          strokeWidth="10"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
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
        <div style={{ fontSize: 44, fontWeight: 300, color: "#f0f6fc", fontFamily: "'Cormorant Garamond', Georgia, serif", lineHeight: 1 }}>
          {numScore}<span style={{ fontSize: 20, color }}>%</span>
        </div>
        <div style={{ fontSize: 11, color: "#8b949e", letterSpacing: "0.08em", textTransform: "uppercase", marginTop: 4 }}>
          Resonance
        </div>
      </div>
      {grade && (
        <div style={{ marginTop: 8, textAlign: "center" }}>
          <span style={{
            fontSize: 13,
            fontWeight: 700,
            color,
            background: `${color}18`,
            border: `1px solid ${color}44`,
            borderRadius: 4,
            padding: "3px 10px",
            letterSpacing: "0.03em",
          }}>
            {formatGrade(grade)}
          </span>
        </div>
      )}
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
    } catch (_) {}
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
    } catch (_) {
      cleanup();
    }
  };

  if (a.readyState >= 1) {
    startPlayback();
  } else {
    a.addEventListener('loadedmetadata', startPlayback, { once: true });
    a.addEventListener('error', cleanup, { once: true });
  }
};

// ─── Interactive Word Pill ───────────────────────────────────────────────────
const WordPill = ({ word, isSelected, onClick, audioURL }) => {
  const colors = {
    green: { bg: "#0d2818", border: "#10b981", text: "#10b981", badge: "#10b981" },
    white: { bg: "#1f1a0d", border: "#f59e0b", text: "#f59e0b", badge: "#f59e0b" },
    red:   { bg: "#251214", border: "#ef4444", text: "#ef4444", badge: "#ef4444" },
  };
  const c = colors[word.status] || colors.red;

  const playSlice = (e) => {
    e.stopPropagation();
    if (!audioURL || word.user_start_sec == null) return;
    playAudioSpan(audioURL, word.user_start_sec, word.user_end_sec);
  };

  return (
    <div
      onClick={onClick}
      style={{
        background: isSelected ? `${c.border}22` : c.bg,
        border: `1.5px solid ${isSelected ? "#f0f6fc" : c.border}`,
        borderRadius: 8,
        padding: "10px 14px",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 3,
        minWidth: 108,
        flex: "1 1 110px",
        transition: "all 0.2s ease",
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 17, fontWeight: 700, color: "#f0f6fc", fontFamily: "'Cormorant Garamond', Georgia, serif" }}>
          {word.expected_devanagari}
        </span>
        <button
          onClick={playSlice}
          title="Play word from your recording"
          style={{
            background: "transparent",
            border: "none",
            color: c.text,
            cursor: "pointer",
            fontSize: 12,
            padding: "0 2px",
          }}
        >
          ▶
        </button>
      </div>
      <span style={{ fontSize: 11, color: "#8b949e", fontStyle: "italic" }}>
        {word.expected_iast}
      </span>
      {word.heard_token && (
        <span style={{ fontSize: 10, color: "#6e7681", maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          Heard: {word.heard_token}
        </span>
      )}
      <span
        style={{
          marginTop: 2,
          fontSize: 10,
          fontWeight: 700,
          color: c.text,
          background: `${c.border}22`,
          padding: "1px 6px",
          borderRadius: 3,
        }}
      >
        {Math.round(word.combined_score || 0)}%
      </span>
    </div>
  );
};

// ─── Phonetic Word Card ──────────────────────────────────────────────────────
const PhoneticWordCard = ({ word, audioURL, refAudioURL }) => {
  const [playingUser, setPlayingUser] = useState(false);
  const [playingRef, setPlayingRef] = useState(false);

  const statusCfg = {
    acceptable: { bg: "#0d2818", border: "#10b981", badge: "#10b981", label: "Acceptable", symbol: "✓" },
    review:     { bg: "#1f1a0d", border: "#f59e0b", badge: "#f59e0b", label: "Needs Review", symbol: "◐" },
    inconclusive: { bg: "#161b22", border: "#30363d", badge: "#6e7681", label: "Inconclusive", symbol: "?" }
  };
  const s = statusCfg[word.status] || statusCfg.inconclusive;

  const hasUserAudio = Boolean(
    audioURL &&
    word.user_end_sec &&
    word.user_end_sec > (word.user_start_sec || 0) &&
    (word.user_end_sec - (word.user_start_sec || 0)) >= 0.05
  );

  const playUserSlice = () => {
    if (!hasUserAudio || playingUser) return;
    playAudioSpan(audioURL, word.user_start_sec, word.user_end_sec, setPlayingUser);
  };

  const playRefSlice = () => {
    if (!refAudioURL || playingRef) return;
    playAudioSpan(refAudioURL, word.ref_start_sec, word.ref_end_sec, setPlayingRef);
  };

  return (
    <div
      style={{
        background: "#161b22",
        border: `1px solid ${s.border}55`,
        borderLeft: `4px solid ${s.badge}`,
        borderRadius: 8,
        padding: "18px 20px",
        marginBottom: 16,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <span
          style={{
            background: "#21262d",
            color: "#8b949e",
            borderRadius: 3,
            padding: "2px 8px",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          Word {word.index + 1}
        </span>
        <span style={{ fontSize: 24, fontWeight: 700, color: "#f0f6fc", fontFamily: "'Cormorant Garamond', Georgia, serif" }}>
          {word.devanagari}
        </span>
        <span style={{ fontSize: 14, color: "#8b949e", fontStyle: "italic" }}>
          ({word.iast})
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 12,
            fontWeight: 700,
            color: s.badge,
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: `${s.badge}18`,
            padding: "3px 9px",
            borderRadius: 4,
            border: `1px solid ${s.badge}44`
          }}
        >
          <span>{s.symbol}</span>
          <span>{s.label}</span>
        </span>
      </div>

      {/* Audio Playback Buttons */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        <button
          onClick={hasUserAudio ? playUserSlice : undefined}
          disabled={!hasUserAudio}
          title={!hasUserAudio ? "This word was not detected in your recitation" : "Play your pronunciation slice"}
          style={{
            background: !hasUserAudio ? "#161b22" : (playingUser ? "#238636" : "#21262d"),
            color: !hasUserAudio ? "#6e7681" : "#f0f6fc",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 12,
            fontWeight: 600,
            cursor: !hasUserAudio ? "not-allowed" : "pointer",
            opacity: !hasUserAudio ? 0.5 : 1,
            display: "flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          <span>{playingUser ? "■" : (hasUserAudio ? "▶" : "—")}</span>
          <span>{playingUser ? "Playing You..." : (hasUserAudio ? "Play My Word" : "No Audio")}</span>
        </button>
        <button
          onClick={playRefSlice}
          style={{
            background: playingRef ? "#b45309" : "#1c2333",
            color: "#f59e0b",
            border: "1px solid #f59e0b55",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          <span>{playingRef ? "■" : "▶"}</span>
          <span>{playingRef ? "Playing Ref..." : "Play Reference"}</span>
        </button>
      </div>

      {/* Word Match Progress Bar */}
      <ScoreBar label="Pronunciation Accuracy" score={word.word_match_score} />

      {/* Phonetic Contrasts Details */}
      {word.contrasts && word.contrasts.length > 0 && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
          {word.contrasts.map((c, idx) => {
            const isAcc = c.status === "acceptable";
            const isRev = c.status === "review";
            const col = isAcc ? "#10b981" : isRev ? "#f59e0b" : "#8b949e";
            return (
              <div
                key={idx}
                style={{
                  background: "#0d1117",
                  border: `1px solid ${col}33`,
                  borderLeft: `3px solid ${col}`,
                  padding: "10px 14px",
                  borderRadius: 4,
                  fontSize: 12,
                  lineHeight: 1.6,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontWeight: 600, textTransform: "capitalize", color: "#f0f6fc" }}>
                    {c.contrast_type.replace(/_/g, " ")}: {c.label ? c.label.replace(/_/g, " ") : ""}
                  </span>
                  <span style={{ color: col, fontWeight: 700, fontSize: 11, textTransform: "uppercase" }}>
                    {c.status}
                  </span>
                </div>
                {c.measured_ratio != null && (
                  <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>
                    Measured Ratio: <span style={{ color: "#f0f6fc", fontWeight: 700 }}>{c.measured_ratio}x</span>
                    {c.target_range && ` (Target: ${c.target_range[0]} - ${c.target_range[1]}x)`}
                  </div>
                )}
                <div style={{ color: "#c9d1d9" }}>{c.reason}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer Info */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#6e7681", marginTop: 12, borderTop: "1px solid #21262d", paddingTop: 8 }}>
        <span>Timing: {word.user_start_sec?.toFixed(2)}s – {word.user_end_sec?.toFixed(2)}s ({word.duration_sec?.toFixed(2)}s)</span>
        <span>Confidence: {Math.round((word.alignment_confidence || 0) * 100)}%</span>
      </div>
    </div>
  );
};

// ─── Word Svara Card (Accent & Shape) ────────────────────────────────────────
const formatAccent = (acc) => {
  if (!acc) return "Neutral";
  const m = {
    udatta: "Udātta (High Pitch Accent)",
    anudatta: "Anudātta (Low Pitch Accent)",
    svarita: "Svarita (Falling Pitch Accent)",
    neutral: "Sādhāraṇa (Neutral)",
  };
  return m[acc.toLowerCase()] || acc;
};

const SvaraWordCard = ({ item }) => {
  const ok = item.accent_ok && item.shape_ok;
  return (
    <div
      style={{
        background: "#161b22",
        border: `1px solid ${ok ? "#10b98133" : "#ef444433"}`,
        borderLeft: `3px solid ${ok ? "#10b981" : "#ef4444"}`,
        borderRadius: 6,
        padding: "12px 16px",
        marginBottom: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: ok ? 0 : 8 }}>
        <span style={{ background: "#21262d", color: "#8b949e", borderRadius: 3, padding: "1px 6px", fontSize: 10, fontWeight: 700 }}>
          Word {item.word_num}
        </span>
        <span style={{ fontSize: 18, fontWeight: 700, color: "#f0f6fc", fontFamily: "'Cormorant Garamond', Georgia, serif" }}>
          '{item.word}'
        </span>
        <span style={{ marginLeft: "auto", fontSize: 13, color: ok ? "#10b981" : "#ef4444" }}>
          {ok ? "✓ Accurate" : "✗ Accent deviation"}
        </span>
      </div>
      {!item.accent_ok && (
        <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 6 }}>
          <span style={{ color: "#ef4444", fontWeight: 600 }}>Accent: </span>
          Expected <span style={{ color: "#10b981", fontWeight: 600 }}>{formatAccent(item.ref_accent)}</span> · Sung{" "}
          <span style={{ color: "#ef4444", fontWeight: 600 }}>{formatAccent(item.user_accent)}</span>
          {item.accent_fix && <div style={{ color: "#c9d1d9", marginTop: 3 }}>{item.accent_fix}</div>}
        </div>
      )}
      {!item.shape_ok && (
        <div style={{ fontSize: 12, color: "#8b949e" }}>
          <span style={{ color: "#ef4444", fontWeight: 600 }}>Pitch Shape: </span>
          Expected <span style={{ color: "#10b981", fontWeight: 600 }}>{item.ref_shape}</span> · Sung{" "}
          <span style={{ color: "#ef4444", fontWeight: 600 }}>{item.user_shape}</span>
          {item.shape_fix && <div style={{ color: "#c9d1d9", marginTop: 3 }}>{item.shape_fix}</div>}
        </div>
      )}
    </div>
  );
};

// ─── Feedback List ────────────────────────────────────────────────────────────
const FeedbackList = ({ items, variant = "default" }) => {
  const borderCol = variant === "error" ? "#ef4444" : variant === "success" ? "#10b981" : "#f59e0b";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((item, i) => (
        <div
          key={i}
          style={{
            background: "#0d1117",
            borderLeft: `3px solid ${borderCol}`,
            padding: "10px 14px",
            borderRadius: 4,
            fontSize: 13,
            color: "#c9d1d9",
            lineHeight: 1.6,
          }}
        >
          {item}
        </div>
      ))}
    </div>
  );
};

// ─── Tab Button ───────────────────────────────────────────────────────────────
const Tab = ({ label, active, onClick, count }) => (
  <button
    onClick={onClick}
    style={{
      padding: "8px 16px",
      borderRadius: 6,
      border: active ? "1px solid #f59e0b" : "1px solid #30363d",
      cursor: "pointer",
      fontSize: 12,
      fontWeight: 600,
      background: active ? "#f59e0b18" : "#161b22",
      color: active ? "#f59e0b" : "#8b949e",
      transition: "all 0.15s ease",
      letterSpacing: "0.04em",
      display: "flex",
      alignItems: "center",
      gap: 6,
    }}
  >
    <span>{label}</span>
    {count != null && (
      <span style={{ fontSize: 10, background: active ? "#f59e0b" : "#21262d", color: active ? "#0d1117" : "#8b949e", borderRadius: 10, padding: "1px 6px" }}>
        {count}
      </span>
    )}
  </button>
);

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

// ─── Main Application ────────────────────────────────────────────────────────
export default function App() {
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

  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const refAudioElementRef = useRef(null);
  const abortControllerRef = useRef(null);

  const cancelAnalysis = () => {
    if (abortControllerRef.current) {
      try { abortControllerRef.current.abort(); } catch (_) {}
      abortControllerRef.current = null;
    }
    setLoading(false);
  };

  const resetToStartPage = () => {
    cancelAnalysis();
    setResult(null);
    setAudioBlob(null);
    setAudioURL(null);
    setError(null);
    setSelectedWordIdx(null);
    setActiveTab("phonetic");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const refAudioURL = `${API_URL}/reference-audio`;

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

  const togglePlayReferenceMantra = () => {
    if (!refAudioElementRef.current) {
      const a = new Audio(refAudioURL);
      refAudioElementRef.current = a;
      a.onended = () => setRefPlaying(false);
    }
    if (refPlaying) {
      refAudioElementRef.current.pause();
      setRefPlaying(false);
    } else {
      refAudioElementRef.current.play().then(() => setRefPlaying(true)).catch(() => setRefPlaying(false));
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
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      audioChunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioChunksRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setRecording(true);
      setResult(null);
      setError(null);
    } catch {
      setError("Microphone access denied. Please grant microphone permissions in browser.");
    }
  };

  const stopRecording = () => {
    if (!recording) return;
    setRecording(false);

    try {
      if (processorRef.current) processorRef.current.disconnect();
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

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setError(null);
    setResult(null);

    try {
      // Decode ANY audio format (WAV, MP3, MPEG, M4A, OGG, FLAC, WEBM) via Web Audio API
      const arrayBuffer = await file.arrayBuffer();
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const decoded = await audioCtx.decodeAudioData(arrayBuffer);
      audioCtx.close();

      // Convert channels to mono
      let monoSamples;
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

      // Check peak for uploaded files - only normalize if quiet (peak < 0.25)
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

      // Encode into clean 16-bit PCM WAV blob
      const wavBlob = encodeWAV(monoSamples, decoded.sampleRate);
      const wavFile = new File([wavBlob], file.name.replace(/\.[^/.]+$/, ".wav"), { type: "audio/wav" });
      setAudioBlob(wavFile);
      setAudioURL(URL.createObjectURL(wavBlob));
    } catch (decodeErr) {
      console.warn("Client-side audio decode failed, falling back to raw file:", decodeErr);
      setAudioBlob(file);
      setAudioURL(URL.createObjectURL(file));
    }
  };

  const analyze = async () => {
    if (!audioBlob) return;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", audioBlob, "user_chant.wav");
      const resp = await fetch(`${API_URL}/analyze`, {
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
    } catch (e) {
      if (e.name === "AbortError") {
        // User cancelled analysis
        return;
      }
      setError(e.message);
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const r = result;
  const sc = r?.scores || {};
  const d = r?.dimensions || {};
  const wordDetail = r?.svara_word_detail || [];
  const wordAlign = r?.word_alignment || [];
  const phoneticWords = r?.phonetic_evaluation?.words || [];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        body { margin: 0; background: #0d1117; color: #f0f6fc; font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }
        button:hover { opacity: 0.92; }
      `}</style>

      {/* ─── Top Bar ──────────────────────────────────────────────────────── */}
      <div
        style={{
          borderBottom: "1px solid #30363d",
          background: "#161b22",
          padding: "10px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 16, color: "#f59e0b", fontWeight: 700 }}>ॐ</span>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#f0f6fc" }}>
            Svara Vaidya · स्वर वैद्य
          </span>
          <span style={{ fontSize: 11, color: "#8b949e", background: "#21262d", padding: "1px 7px", borderRadius: 3 }}>
            Ganesha Shloka Edition
          </span>
          {(result || audioURL) && (
            <button
              onClick={resetToStartPage}
              title="Return to start page and reset recording"
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: "#c9d1d9",
                background: "#21262d",
                border: "1px solid #30363d",
                padding: "2px 10px",
                borderRadius: 4,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                marginLeft: 4,
              }}
            >
              <span>↺</span>
              <span>Reset to Start Page</span>
            </button>
          )}
        </div>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 4,
            background: apiStatus === "ok" ? "#10b98118" : "#ef444418",
            color: apiStatus === "ok" ? "#10b981" : "#ef4444",
            border: `1px solid ${apiStatus === "ok" ? "#10b98144" : "#ef444444"}`,
          }}
        >
           {apiStatus === "ok" ? "● Connected to API" : "● API Offline"} 
        </span>
      </div>

      {/* ─── Mantra Hero Banner ────────────────────────────────────────────── */}
      <div
        style={{
          background: "linear-gradient(180deg, #161b22 0%, #0d1117 100%)",
          borderBottom: "1px solid #30363d",
          padding: "28px 24px 24px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 11, color: "#f59e0b", letterSpacing: "0.15em", textTransform: "uppercase", fontWeight: 700, marginBottom: 8 }}>
          Ganesha Shloka (Vakratuṇḍa Mahākāya)
        </div>
        <div
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: "#f0f6fc",
            fontFamily: "'Cormorant Garamond', Georgia, serif",
            letterSpacing: "0.02em",
            marginBottom: 6,
          }}
        >
          वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ निर्विघ्नं कुरुमेदेव सर्वकार्येषु सर्वदा
        </div>
        <div style={{ fontSize: 13, color: "#8b949e", fontStyle: "italic", marginBottom: 10 }}>
          vakratuṇḍa mahākāya sūryakoṭi samaprabha nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā
        </div>
        <div
          style={{
            fontSize: 13,
            color: "#c9d1d9",
            maxWidth: 720,
            margin: "0 auto 16px",
            lineHeight: 1.6,
            background: "#161b2299",
            border: "1px solid #30363d88",
            borderRadius: 6,
            padding: "8px 16px",
          }}
        >
          <span style={{ color: "#f59e0b", fontWeight: 600 }}>English Meaning: </span>
          "O Lord with the curved trunk and immense body, whose brilliance equals ten million suns, please make all my endeavors free from obstacles, always."
        </div>
        <button
          onClick={togglePlayReferenceMantra}
          style={{
            background: refPlaying ? "#b45309" : "#21262d",
            color: "#f59e0b",
            border: "1px solid #f59e0b66",
            borderRadius: 6,
            padding: "7px 18px",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span>{refPlaying ? "■" : "▶"}</span>
          <span>{refPlaying ? "Stop Reference Audio" : "Play Master Reference Mantra"}</span>
        </button>
      </div>

      {/* ─── Main 2-Column Dashboard Container ────────────────────────────── */}
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "24px 20px 60px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(340px, 420px) 1fr",
            gap: 24,
            alignItems: "start",
          }}
        >
          {/* ══════════════ LEFT COLUMN (Controls & Macro Telemetry) ══════════════ */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Record / Upload Card */}
            <div
              style={{
                background: "#161b22",
                border: "1px solid #30363d",
                borderRadius: 8,
                padding: "20px",
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#8b949e", marginBottom: 16 }}>
                01 · Recording Studio
              </div>

              <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                {!recording ? (
                  <button
                    onClick={() => {
                      if (loading) cancelAnalysis();
                      startRecording();
                    }}
                    style={{
                      flex: 1,
                      background: "#ef4444",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      padding: "12px 16px",
                      fontSize: 13,
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 10 }}>●</span>
                    <span>Record Chant</span>
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    style={{
                      flex: 1,
                      background: "#0d1117",
                      color: "#ef4444",
                      border: "2px solid #ef4444",
                      borderRadius: 6,
                      padding: "12px 16px",
                      fontSize: 13,
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                    }}
                  >
                    <span>■</span>
                    <span>Stop Recording</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    if (loading) cancelAnalysis();
                    fileInputRef.current.click();
                  }}
                  style={{
                    flex: 1,
                    background: "#21262d",
                    color: "#f0f6fc",
                    border: "1px solid #30363d",
                    borderRadius: 6,
                    padding: "12px 16px",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                  title="Upload audio in WAV, MP3, MPEG, M4A, OGG, FLAC, WEBM formats"
                >
                  Upload Audio (WAV, MP3, MPEG, M4A, OGG, FLAC)
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".wav,.mp3,.mpeg,.mpga,.m4a,.aac,.ogg,.flac,.webm,audio/*"
                  style={{ display: "none" }}
                  onChange={handleFile}
                />
              </div>

              <div style={{ color: "#8b949e", fontSize: 11, textAlign: "center", marginBottom: 14 }}>
                Upload Audio (WAV, MP3, MPEG, M4A, OGG, FLAC) or Record Live
              </div>

              {recording && (
                <div style={{ color: "#ef4444", fontSize: 12, textAlign: "center", marginBottom: 12, fontWeight: 600 }}>
                  ● Recording in progress... chant the Ganesha Shloka clearly
                </div>
              )}

              {audioURL && (
                <audio
                  controls
                  src={audioURL}
                  style={{
                    width: "100%",
                    borderRadius: 6,
                    marginBottom: 14,
                    height: 38,
                    filter: "invert(0.9) hue-rotate(180deg)",
                  }}
                />
              )}

              {audioBlob && !loading && !recording && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <button
                    onClick={analyze}
                    style={{
                      width: "100%",
                      background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
                      color: "#0d1117",
                      border: "none",
                      borderRadius: 6,
                      padding: "13px",
                      fontSize: 14,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      cursor: "pointer",
                    }}
                  >
                    {result ? "Re-Analyse Chant" : "Analyse Chant"}
                  </button>

                  {result && (
                    <button
                      onClick={resetToStartPage}
                      style={{
                        width: "100%",
                        background: "#21262d",
                        color: "#f0f6fc",
                        border: "1px solid #30363d",
                        borderRadius: 6,
                        padding: "11px",
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 8,
                      }}
                    >
                      <span>↺</span>
                      <span>Start New Recording / Return to Start Page</span>
                    </button>
                  )}
                </div>
              )}

              {loading && (
                <div style={{ textAlign: "center", padding: "16px", background: "#0d1117", borderRadius: 6, border: "1px solid #30363d" }}>
                  <div style={{ color: "#f59e0b", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                    Analysing your chant...
                  </div>
                  <div style={{ color: "#8b949e", fontSize: 11, marginBottom: 12 }}>
                    MMS phonetics + pitch contour + local word DTW (~15-25s)
                  </div>
                  <button
                    onClick={cancelAnalysis}
                    style={{
                      background: "#21262d",
                      color: "#f87171",
                      border: "1px solid #ef444466",
                      borderRadius: 6,
                      padding: "7px 16px",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <span>✕</span>
                    <span>Cancel Analysis & Return</span>
                  </button>
                </div>
              )}

              {error && (
                <div style={{ background: "#251214", border: "1px solid #ef444455", borderRadius: 6, padding: "12px", color: "#fca5a5", fontSize: 12, marginTop: 12 }}>
                  {error}
                </div>
              )}
            </div>

            {/* Stage-1 Mantra Verification Gate Banner */}
            {r && (
              <div
                style={{
                  background: r.is_valid_mantra ? "#0d2818" : "#251214",
                  border: `1px solid ${r.is_valid_mantra ? "#10b981" : "#ef4444"}`,
                  borderRadius: 8,
                  padding: "16px 18px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 18 }}>{r.is_valid_mantra ? "✓" : "⚠️"}</span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: r.is_valid_mantra ? "#10b981" : "#ef4444",
                    }}
                  >
                    {r.is_valid_mantra ? "Mantra Verification Passed" : "Verification Gate Alert"}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#c9d1d9", lineHeight: 1.5 }}>
                  {r.gate_message}
                </div>
                {r.user_transcript && (
                  <div style={{ marginTop: 8, fontSize: 11, color: "#8b949e", fontStyle: "italic", borderTop: "1px solid #30363d", paddingTop: 6 }}>
                    ASR Transcript: "{r.user_transcript}"
                  </div>
                )}
              </div>
            )}

            {/* Resonance Radial Gauge Card */}
            {r && (
              <div
                style={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 8,
                  padding: "24px 20px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <RadialGauge score={r.overall_score} grade={r.overall_grade} />
              </div>
            )}

            {/* 4 Macro Dimension Scores */}
            {r && (
              <div
                style={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 8,
                  padding: "20px",
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#8b949e", marginBottom: 16 }}>
                  Macro Dimension Telemetry
                </div>
                <ScoreBar label="Ucchāraṇa (Pronunciation)" score={d.uccharana?.score ?? sc.text_similarity} />
                <ScoreBar label="Svara (Pitch & Vedic Accent)" score={d.svara?.score ?? sc.pitch_combined} />
                <ScoreBar label="Laya (Rhythm & Tempo)" score={d.laya?.score ?? sc.tempo_similarity} />
                <ScoreBar label="Nāda (Voice Quality)" score={d.nada?.score ?? sc.mfcc_similarity} />
              </div>
            )}
          </div>

          {/* ══════════════ RIGHT COLUMN (Diagnostics & Tabs) ══════════════ */}
          <div>
            {/* Interactive Word Alignment Pills (Displayed right at top of analysis) */}
            {wordAlign.length > 0 && (
              <div
                style={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 8,
                  padding: "16px 20px",
                  marginBottom: 20,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#8b949e" }}>
                    Word-by-Word Alignment & Acoustic Status
                  </span>
                  <span style={{ fontSize: 11, color: "#6e7681" }}>
                    Click any word to isolate & play audio
                  </span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {wordAlign.map((w) => (
                    <WordPill
                      key={w.index}
                      word={w}
                      isSelected={selectedWordIdx === w.index}
                      onClick={() => {
                        setSelectedWordIdx(w.index);
                        setActiveTab("phonetic");
                      }}
                      audioURL={audioURL}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Diagnostic Tabs Card */}
            <div
              style={{
                background: "#161b22",
                border: "1px solid #30363d",
                borderRadius: 8,
                padding: "20px 24px",
              }}
            >
              {/* Tab Header Buttons */}
              <div style={{ display: "flex", gap: 8, marginBottom: 22, flexWrap: "wrap", borderBottom: "1px solid #21262d", paddingBottom: 14 }}>
                <Tab
                  label="8-Word Phonetic Studio"
                  active={activeTab === "phonetic"}
                  onClick={() => setActiveTab("phonetic")}
                  count={phoneticWords.length || 8}
                />
                <Tab
                  label="Ucchāraṇa (Pronunciation)"
                  active={activeTab === "uccharana"}
                  onClick={() => setActiveTab("uccharana")}
                />
                <Tab
                  label="Svara (Pitch & Accent)"
                  active={activeTab === "svara"}
                  onClick={() => setActiveTab("svara")}
                />
                <Tab
                  label="Laya & Nāda (Rhythm & Timbre)"
                  active={activeTab === "layanada"}
                  onClick={() => setActiveTab("layanada")}
                />
              </div>

              {/* ── Tab 1: 8-Word Phonetic Studio ── */}
              {activeTab === "phonetic" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#f0f6fc" }}>
                      Local DTW Alignment & Phonetic Contrasts
                    </div>
                    {r?.phonetic_evaluation?.summary && (
                      <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
                        <span style={{ color: "#10b981", fontWeight: 700 }}>
                          {r.phonetic_evaluation.summary.acceptable} Acceptable
                        </span>
                        <span style={{ color: "#f59e0b", fontWeight: 700 }}>
                          {r.phonetic_evaluation.summary.review} Review
                        </span>
                        <span style={{ color: "#6e7681" }}>
                          Avg Match: {r.phonetic_evaluation.summary.average_word_score}%
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Single Vedic Pronunciation Explanation Banner */}
                  <div
                    style={{
                      background: "#0d1117",
                      border: "1px solid #30363d",
                      borderRadius: 6,
                      padding: "12px 16px",
                      marginBottom: 18,
                      fontSize: 12,
                      lineHeight: 1.5,
                      color: "#c9d1d9",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#f59e0b", marginBottom: 3 }}>
                      Vedic Phonetic Articulation & Vowel Prosody (Varṇa & Mātrā)
                    </div>
                    <div>
                      Evaluates vocal resonance, consonant articulation (Sthāna & Prayatna), and short vs. long vowel timing (Hrasva & Dīrgha Mātrā) against the authentic master chanting.
                    </div>
                  </div>

                  {phoneticWords.length > 0 ? (
                    phoneticWords.map((w) => (
                      <PhoneticWordCard
                        key={w.index}
                        word={w}
                        audioURL={audioURL}
                        refAudioURL={refAudioURL}
                      />
                    ))
                  ) : (
                    <div style={{ color: "#8b949e", textAlign: "center", padding: "30px 0" }}>
                      Record or upload audio and click "Analyse Chant" to inspect word-level phonetics.
                    </div>
                  )}
                </div>
              )}

              {/* ── Tab 2: Ucchāraṇa ── */}
              {activeTab === "uccharana" && (
                <div>
                  {!r ? (
                    <div style={{ color: "#8b949e", textAlign: "center", padding: "40px 0" }}>
                      Record or upload audio and click "Analyse Chant" to inspect Ucchāraṇa (pronunciation) diagnostics.
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
                        {[
                          ["Character Sim", d.uccharana?.char_sim ?? sc.text_similarity],
                          ["Word Match", d.uccharana?.word_sim ?? 0],
                          ["Syllable (Akṣara)", d.uccharana?.syl_sim ?? 0],
                        ].map(([label, val]) => (
                          <div
                            key={label}
                            style={{
                              background: "#0d1117",
                              border: "1px solid #30363d",
                              borderRadius: 6,
                              padding: "14px",
                              textAlign: "center",
                            }}
                          >
                            <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 }}>
                              {label}
                            </div>
                            <div style={{ fontSize: 26, fontWeight: 700, color: gradeColor(val || 0), fontFamily: "monospace" }}>
                              {Math.round(val || 0)}%
                            </div>
                          </div>
                        ))}
                      </div>

                      {d.uccharana?.issues?.length > 0 && (
                        <div style={{ marginBottom: 18 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "#ef4444", textTransform: "uppercase", marginBottom: 8 }}>
                            Pronunciation Issues
                          </div>
                          <FeedbackList items={d.uccharana.issues} variant="error" />
                        </div>
                      )}

                      {d.uccharana?.fixes?.length > 0 && (
                        <div style={{ marginBottom: 18 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", marginBottom: 8 }}>
                            How To Improve
                          </div>
                          <FeedbackList items={d.uccharana.fixes} variant="warning" />
                        </div>
                      )}

                      {(!d.uccharana?.issues || d.uccharana.issues.length === 0) && (
                        <div style={{ color: "#10b981", fontSize: 13, background: "#0d2818", border: "1px solid #10b98144", padding: "14px", borderRadius: 6 }}>
                          ✓ High ucchāraṇa fidelity — no major phonemic errors detected.
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* ── Tab 3: Svara ── */}
              {activeTab === "svara" && (
                <div>
                  {!r ? (
                    <div style={{ color: "#8b949e", textAlign: "center", padding: "40px 0" }}>
                      Record or upload audio and click "Analyse Chant" to inspect Vedic Svara (pitch & accent) diagnostics.
                    </div>
                  ) : (
                    <>
                      <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "16px", marginBottom: 20 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: 12 }}>
                          Pitch Sub-Score Breakdown
                        </div>
                        <ScoreBar label="Contour Shape Similarity" score={sc.pitch_breakdown?.contour_shape} />
                        <ScoreBar label="Pitch Zone Accuracy (Udātta [High] / Anudātta [Low] / Svarita [Falling])" score={sc.pitch_breakdown?.zone_accuracy} />
                        <ScoreBar label="Accent Placement" score={sc.pitch_breakdown?.accent_placement} />
                        <ScoreBar label="Syllable Pitch Shape" score={sc.pitch_breakdown?.syllable_shape} />
                        <ScoreBar label="Slope / Steepness" score={sc.pitch_breakdown?.slope_steepness} />
                      </div>

                      <div style={{ fontSize: 12, fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: 10 }}>
                        Word-by-Word Svara Diagnostics ({wordDetail.length} words)
                      </div>

                      {wordDetail.length > 0 ? (
                        wordDetail.map((item, idx) => <SvaraWordCard key={idx} item={item} />)
                      ) : (
                        <div style={{ color: "#10b981", fontSize: 13, background: "#0d2818", border: "1px solid #10b98144", padding: "14px", borderRadius: 6 }}>
                          ✓ All words carry authentic Vedic svara accents.
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* ── Tab 4: Laya & Nāda ── */}
              {activeTab === "layanada" && (
                <div>
                  {!r ? (
                    <div style={{ color: "#8b949e", textAlign: "center", padding: "40px 0" }}>
                      Record or upload audio and click "Analyse Chant" to view Laya & Nāda diagnostics.
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "16px", textAlign: "center" }}>
                          <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 }}>
                            Laya (Rhythm & Flow)
                          </div>
                          <div style={{ fontSize: 32, fontWeight: 700, color: gradeColor(d.laya?.score || 0), fontFamily: "monospace" }}>
                            {Math.round(d.laya?.score || 0)}%
                          </div>
                        </div>

                        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "16px", textAlign: "center" }}>
                          <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 }}>
                            Duration Pace Ratio
                          </div>
                          <div style={{ fontSize: 32, fontWeight: 700, color: Math.abs((d.laya?.duration_ratio || 1) - 1) < 0.2 ? "#10b981" : "#f59e0b", fontFamily: "monospace" }}>
                            {d.laya?.duration_ratio != null ? `${d.laya.duration_ratio}x` : "1.0x"}
                          </div>
                          <div style={{ fontSize: 11, color: "#8b949e", marginTop: 2 }}>
                            {d.laya?.duration_ratio > 1.2 ? "Slow tempo" : d.laya?.duration_ratio < 0.8 ? "Brisk tempo" : "Natural tempo"}
                          </div>
                        </div>
                      </div>

                      <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "16px", marginBottom: 20, textAlign: "center" }}>
                        <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 }}>
                          Nāda (Vocal Timbre & Harmonic Richness)
                        </div>
                        <div style={{ fontSize: 36, fontWeight: 700, color: gradeColor(d.nada?.score || 0), fontFamily: "monospace" }}>
                          {Math.round(d.nada?.score || 0)}%
                        </div>
                      </div>

                      {r?.all_praises && r.all_praises.length > 0 && (
                        <div style={{ marginBottom: 18 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "#10b981", textTransform: "uppercase", marginBottom: 8 }}>
                            Sādhu! (What you chanted well)
                          </div>
                          <FeedbackList items={r.all_praises} variant="success" />
                        </div>
                      )}

                      {r?.sadhana_tip && (
                        <div style={{ background: "#1c1a14", border: "1px solid #f59e0b55", borderLeft: "4px solid #f59e0b", borderRadius: 6, padding: "14px 18px", marginTop: 18 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", marginBottom: 4 }}>
                            🪔 Daily Sādhana (Spiritual Practice) Recommendation
                          </div>
                          <div style={{ fontSize: 13, color: "#f0f6fc", lineHeight: 1.6 }}>
                            {r.sadhana_tip}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ─── Footer ───────────────────────────────────────────────────────── */}
        <div style={{ textAlign: "center", color: "#6e7681", fontSize: 13, marginTop: 40, borderTop: "1px solid #21262d", paddingTop: 20 }}>
          ॐ शान्तिः शान्तिः शान्तिः · Swara Vaidya Sanskrit Chanting Evaluation System
        </div>
      </div>
    </>
  );
}
