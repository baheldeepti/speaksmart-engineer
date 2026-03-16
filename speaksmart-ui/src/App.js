import React, { useState, useEffect, useRef, useCallback } from "react";
import { Room, RoomEvent, Track, createLocalAudioTrack } from "livekit-client";
import "./App.css";

const LIVEKIT_URL = process.env.REACT_APP_LIVEKIT_URL || "";
const LIVEKIT_TOKEN = process.env.REACT_APP_LIVEKIT_TOKEN || "";

const SCENARIOS = [
  { key: "A", name: "Engineer → Engineers", icon: "👨‍💻", hint: "Technical depth matters", color: "#8b5cf6" },
  { key: "B", name: "Engineer → Executives", icon: "🏢", hint: "Focus on business impact", color: "#6366f1" },
  { key: "C", name: "Data → Business", icon: "📊", hint: "Make data actionable", color: "#22d3ee" },
  { key: "D", name: "Tech → Client", icon: "🤝", hint: "Benefits over features", color: "#34d399" },
  { key: "E", name: "Roadmap Pitch", icon: "🗺️", hint: "Connect to customer value", color: "#fbbf24" },
];

const MAYA_TIPS = [
  "Tip: Start with the outcome, not the process.",
  "Tip: Replace 'I think' with 'I recommend' — instant confidence boost.",
  "Tip: One clear message beats five scattered ones.",
  "Tip: If you can't explain it in 30 seconds, simplify it.",
  "Tip: End with a clear ask — never trail off.",
];

/* ─── Score Circle (extracted outside to prevent re-renders) ─── */
function ScoreCircle({ score, label, delay = 0 }) {
  const val = score || 0;
  const color = val >= 8 ? "var(--green)" : val >= 5 ? "var(--cyan)" : "var(--orange)";
  return (
    <div className="score-circle" style={{ animationDelay: `${delay}ms` }}>
      <div className="score-ring">
        <svg viewBox="0 0 36 36">
          <path
            className="ring-bg"
            d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            className="ring-fill"
            strokeDasharray={`${val * 10}, 100`}
            style={{ stroke: color, animationDelay: `${delay + 200}ms` }}
            d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>
        <span className="score-num" style={{ color }}>{val || "–"}</span>
      </div>
      <div className="score-label">{label}</div>
    </div>
  );
}

export default function App() {
  const [phase, setPhase] = useState("idle");
  const [connected, setConnected] = useState(false);
  const [agentReady, setAgentReady] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectionTime, setConnectionTime] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [error, setError] = useState("");
  const [mayaTip, setMayaTip] = useState("");

  const [selectedScenario, setSelectedScenario] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [partialText, setPartialText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [sessionCount, setSessionCount] = useState(0);

  const roomRef = useRef(null);
  const trackRef = useRef(null);
  const audioElRef = useRef(null);
  const timerRef = useRef(null);
  const connectTimerRef = useRef(null);

  useEffect(() => {
    setMayaTip(MAYA_TIPS[Math.floor(Math.random() * MAYA_TIPS.length)]);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (connectTimerRef.current) clearInterval(connectTimerRef.current);
      disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const formatTime = (s) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  /* ─── Connect to LiveKit room ─── */
  const connect = useCallback(async () => {
    if (!LIVEKIT_TOKEN) {
      setError("Token not configured — add REACT_APP_LIVEKIT_TOKEN to .env");
      return;
    }
    setConnecting(true);
    setError("");
    setConnectionTime(0);
    connectTimerRef.current = setInterval(
      () => setConnectionTime((t) => t + 1),
      1000
    );

    try {
      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      room.on(RoomEvent.Connected, () => {
        console.log("✅ Room connected");
        setConnected(true);
        setConnecting(false);
        setPhase("selecting");
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log("❌ Disconnected");
        setConnected(false);
        setAgentReady(false);
        setPhase("idle");
        clearAllTimers();
      });

      room.on(RoomEvent.ParticipantConnected, (p) => {
        console.log("👤 Participant:", p.identity);
        if (p.identity.includes("agent")) {
          setAgentReady(true);
          clearConnectTimer();
        }
      });

      room.on(RoomEvent.ParticipantDisconnected, (p) => {
        if (p.identity.includes("agent")) setAgentReady(false);
      });

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.style.display = "none";
          document.body.appendChild(el);
          audioElRef.current = el;
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach();
          if (audioElRef.current) {
            audioElRef.current.remove();
            audioElRef.current = null;
          }
        }
      });

      /* ─── FIX: handle DataReceived properly ─── */
      room.on(RoomEvent.DataReceived, (payload, participant, kind) => {
        try {
          const raw =
            payload instanceof Uint8Array
              ? payload
              : new Uint8Array(payload);
          const data = JSON.parse(new TextDecoder().decode(raw));
          console.log("📨", data.type, data);

          switch (data.type) {
            case "agent_ready":
              setAgentReady(true);
              clearConnectTimer();
              break;
            case "partial":
              setPartialText(data.text || "");
              break;
            case "transcript":
              setTranscript(data.text || "");
              setPartialText("");
              break;
            case "analyzing":
              setPhase("analyzing");
              break;
            case "results":
              setTranscript(data.transcript || "");
              setAnalysis(data.analysis);
              setPhase("results");
              setSessionCount((c) => c + 1);
              break;
            case "error":
              setError(data.message);
              setPhase("selecting");
              break;
            default:
              break;
          }
        } catch (e) {
          console.error("DataReceived parse error:", e);
        }
      });

      await room.connect(LIVEKIT_URL, LIVEKIT_TOKEN);

      // Check if agent is already in the room
      room.remoteParticipants.forEach((p) => {
        if (p.identity.includes("agent")) {
          setAgentReady(true);
          clearConnectTimer();
        }
      });
    } catch (e) {
      console.error("Connection error:", e);
      setError(e.message || "Connection failed — check LIVEKIT_URL and token");
      setConnecting(false);
      clearConnectTimer();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const clearConnectTimer = () => {
    if (connectTimerRef.current) {
      clearInterval(connectTimerRef.current);
      connectTimerRef.current = null;
    }
  };

  const clearAllTimers = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (connectTimerRef.current) clearInterval(connectTimerRef.current);
    timerRef.current = null;
    connectTimerRef.current = null;
  };

  /* ─── Disconnect ─── */
  const disconnect = useCallback(async () => {
    clearAllTimers();
    if (trackRef.current) {
      trackRef.current.stop();
      trackRef.current = null;
    }
    if (audioElRef.current) {
      audioElRef.current.remove();
      audioElRef.current = null;
    }
    if (roomRef.current) {
      try {
        await roomRef.current.disconnect();
      } catch (e) {
        console.warn("Disconnect error:", e);
      }
      roomRef.current = null;
    }
    setConnected(false);
    setAgentReady(false);
    setPhase("idle");
    setAnalysis(null);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ─── Start Recording ─── */
  const startRecording = async (scenario) => {
    if (!agentReady || !roomRef.current) {
      setError("Coach Maya isn't ready yet — hang tight!");
      return;
    }

    setSelectedScenario(scenario);
    setError("");
    setTranscript("");
    setPartialText("");
    setAnalysis(null);

    // Send scenario to agent
    const msg = JSON.stringify({ type: "scenario", scenario: scenario.key });
    await roomRef.current.localParticipant.publishData(
      new TextEncoder().encode(msg),
      { reliable: true }
    );
    console.log("📤 Sent scenario:", scenario.key);

    // Start microphone
    try {
      const audioTrack = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 48000,
      });
      trackRef.current = audioTrack;
      await roomRef.current.localParticipant.publishTrack(audioTrack);
      console.log("🎤 Mic track published");

      setPhase("recording");
      setRecordingTime(0);
      timerRef.current = setInterval(
        () => setRecordingTime((t) => t + 1),
        1000
      );
    } catch (e) {
      console.error("Mic error:", e);
      setError(
        "Microphone access denied — please allow mic access and try again."
      );
    }
  };

  /* ─── Stop Recording ───
   * FIX: Send stop signal FIRST, wait for the agent to process remaining audio,
   * then unpublish the track. The 1.5s delay ensures the agent's pipe_audio
   * loop sees the stop_event before the track stream dies.
   */
  const stopRecording = async () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // 1. Send stop signal to agent
    if (roomRef.current) {
      const msg = JSON.stringify({ type: "stop" });
      await roomRef.current.localParticipant.publishData(
        new TextEncoder().encode(msg),
        { reliable: true }
      );
      console.log("📤 Sent stop signal");
    }

    // 2. CRITICAL: Wait for agent to process the stop and flush audio
    //    The agent has a 1.0s grace period after stop_event, so we wait 1.5s
    setPhase("analyzing");
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // 3. NOW unpublish and stop the mic track
    if (trackRef.current && roomRef.current) {
      try {
        await roomRef.current.localParticipant.unpublishTrack(trackRef.current);
      } catch (e) {
        console.warn("Unpublish warning:", e);
      }
      trackRef.current.stop();
      trackRef.current = null;
    }
  };

  /* ─── Try Again ─── */
  const tryAgain = () => {
    setSelectedScenario(null);
    setTranscript("");
    setPartialText("");
    setAnalysis(null);
    setRecordingTime(0);
    setMayaTip(MAYA_TIPS[Math.floor(Math.random() * MAYA_TIPS.length)]);
    setPhase("selecting");
  };

  /* ─── Render ─── */
  return (
    <div className="app">
      <header className="header">
        <button
          className="back-btn"
          onClick={disconnect}
          disabled={phase === "idle"}
        >
          ← Exit
        </button>
        <h1>
          <span className="logo-icon">🎙</span> SpeakSmart
        </h1>
        <span className="status">
          {agentReady ? "🟢" : connected ? "🟡" : ""}
        </span>
      </header>

      <main className="main">
        {error && (
          <div className="error">
            <span>{error}</span>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {/* ═══════ IDLE ═══════ */}
        {phase === "idle" && (
          <div className="screen center">
            <div className="maya-avatar">
              <div className="maya-glow" />
              <span className="maya-emoji">🧠</span>
            </div>
            <h2>Meet Coach Maya</h2>
            <p className="maya-intro">
              Your AI communication coach powered by Amazon Nova.
              <br />
              Practice explaining ideas. Get specific, actionable feedback.
            </p>
            <div className="maya-tip-box">
              <span className="tip-icon">💡</span>
              <span>{mayaTip}</span>
            </div>
            <button className="cta" onClick={connect} disabled={connecting}>
              {connecting ? (
                <>
                  <span className="btn-spinner" /> Connecting...
                </>
              ) : (
                "Start Practice Session"
              )}
            </button>
            {sessionCount > 0 && (
              <p className="session-count">
                Sessions completed: {sessionCount}
              </p>
            )}
          </div>
        )}

        {/* ═══════ SELECTING ═══════ */}
        {phase === "selecting" && (
          <div className="screen">
            <div className="selecting-header">
              <h2>Who's your audience?</h2>
              <p className="subtitle">
                Maya adapts her coaching to your audience
              </p>
            </div>

            <div className="scenario-list">
              {SCENARIOS.map((s, i) => (
                <button
                  key={s.key}
                  className="scenario-card"
                  style={{
                    animationDelay: `${i * 60}ms`,
                    "--accent": s.color,
                  }}
                  onClick={() => startRecording(s)}
                  disabled={!agentReady}
                >
                  <span className="scenario-icon">{s.icon}</span>
                  <div>
                    <div className="scenario-name">{s.name}</div>
                    <div className="scenario-hint">{s.hint}</div>
                  </div>
                  <span className="scenario-arrow">→</span>
                </button>
              ))}
            </div>

            {!agentReady && (
              <div className="connection-box">
                <div className="spinner" />
                <div>
                  <div>Connecting to Coach Maya...</div>
                  <div className="connect-time">{connectionTime}s</div>
                </div>
              </div>
            )}

            {!agentReady && connectionTime > 8 && (
              <div className="help-section">
                <button
                  className="help-btn"
                  onClick={() => setShowHelp(!showHelp)}
                >
                  ⚠️ Taking too long? Troubleshoot
                </button>
                {showHelp && (
                  <div className="help-content">
                    <p>
                      <b>1.</b> Is the agent running?
                    </p>
                    <code>
                      cd ~/Projects/speaksmart-engineer/speaksmart-env && python
                      main.py dev
                    </code>
                    <p>
                      <b>2.</b> Look for "✅ Connected" in terminal
                    </p>
                    <p>
                      <b>3.</b> Token expired? Regenerate:
                    </p>
                    <code>
                      lk token create --api-key YOUR_KEY --api-secret
                      YOUR_SECRET --join --room speaksmart --identity user
                      --valid-for 1h
                    </code>
                  </div>
                )}
              </div>
            )}

            {agentReady && (
              <div className="ready-badge">
                <span className="ready-pulse" />
                ✅ Coach Maya is ready — pick your audience!
              </div>
            )}
          </div>
        )}

        {/* ═══════ RECORDING ═══════ */}
        {phase === "recording" && (
          <div className="screen center">
            <div className="rec-badge">{selectedScenario?.name}</div>

            <div className="rec-orb">
              <div className="pulse" />
              <div className="pulse d" />
              <div className="wave-box">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="bar" />
                ))}
              </div>
            </div>

            <div className="rec-status">
              <span className="rec-dot" />
              <span>RECORDING</span>
              <span className="timer">{formatTime(recordingTime)}</span>
            </div>

            <div className="maya-listening">
              🧠 Maya is listening...
            </div>

            {partialText && (
              <div className="live-text">
                <span className="live-indicator">LIVE</span>
                {partialText}
              </div>
            )}

            <button className="stop-btn" onClick={stopRecording}>
              ■ Stop & Get Feedback
            </button>

            {recordingTime > 3 && recordingTime < 8 && (
              <p className="rec-hint fade-in">
                Speak naturally — Maya analyzes content, not performance anxiety
              </p>
            )}
          </div>
        )}

        {/* ═══════ ANALYZING ═══════ */}
        {phase === "analyzing" && (
          <div className="screen center">
            <div className="analyzing">
              <div className="spin" />
              <div className="spin s2" />
              <span>🧠</span>
            </div>
            <h2>Maya is analyzing...</h2>
            <p>Checking clarity, structure, impact & confidence</p>
            <div className="analysis-steps">
              <div className="step active">📝 Reading transcript</div>
              <div className="step">🔍 Analyzing structure</div>
              <div className="step">💡 Generating feedback</div>
            </div>
          </div>
        )}

        {/* ═══════ RESULTS ═══════ */}
        {phase === "results" && analysis && (
          <div className="screen results">
            {/* Maya's Headline */}
            {analysis.maya_headline && (
              <div className="maya-headline-box">
                <span className="maya-says">🧠 Maya says:</span>
                <p className="maya-headline">"{analysis.maya_headline}"</p>
              </div>
            )}

            {/* Transcript */}
            <div className="section transcript-box">
              <h3>🎤 What You Said</h3>
              <p>{transcript || "No transcript captured"}</p>
            </div>

            {/* Score */}
            <div className="section score-box">
              <div className="big-score-wrapper">
                <div className="big-score">
                  {analysis.overall_score || 0}
                  <span>/10</span>
                </div>
                <div className="score-context">
                  {analysis.overall_score >= 8
                    ? "Excellent — nearly presentation-ready"
                    : analysis.overall_score >= 6
                    ? "Good foundation — a few tweaks will elevate it"
                    : analysis.overall_score >= 4
                    ? "Getting there — let's sharpen the message"
                    : "Let's rebuild this together"}
                </div>
              </div>
              <div className="scores-grid">
                <ScoreCircle
                  score={analysis.opening_analysis?.score}
                  label="Opening"
                  delay={0}
                />
                <ScoreCircle
                  score={analysis.structure_analysis?.score}
                  label="Structure"
                  delay={80}
                />
                <ScoreCircle
                  score={analysis.clarity_analysis?.score}
                  label="Clarity"
                  delay={160}
                />
                <ScoreCircle
                  score={analysis.impact_analysis?.score}
                  label="Impact"
                  delay={240}
                />
                <ScoreCircle
                  score={analysis.conclusion_analysis?.score}
                  label="Conclusion"
                  delay={320}
                />
                <ScoreCircle
                  score={analysis.confidence_analysis?.score}
                  label="Confidence"
                  delay={400}
                />
                <ScoreCircle
                  score={analysis.articulation_score}
                  label="Articulation"
                  delay={480}
                />
              </div>
            </div>

            {/* Opening */}
            {analysis.opening_analysis && (
              <div className="section">
                <h3>🪝 Opening</h3>
                {analysis.opening_analysis.their_words && (
                  <div className="quote-block">
                    "{analysis.opening_analysis.their_words}"
                  </div>
                )}
                {analysis.opening_analysis.issue && (
                  <p className="issue">
                    ⚠️ {analysis.opening_analysis.issue}
                  </p>
                )}
                {analysis.opening_analysis.better_opening && (
                  <div className="better-block">
                    <span className="better-label">💡 Try instead:</span>
                    <p>"{analysis.opening_analysis.better_opening}"</p>
                  </div>
                )}
              </div>
            )}

            {/* Structure */}
            {analysis.structure_analysis && (
              <div className="section">
                <h3>🏗️ Structure</h3>
                <p className="dim">{analysis.structure_analysis.flow}</p>
                {analysis.structure_analysis.suggestion && (
                  <div className="better-block">
                    <span className="better-label">💡 Tip:</span>
                    <p>{analysis.structure_analysis.suggestion}</p>
                  </div>
                )}
              </div>
            )}

            {/* Impact */}
            {analysis.impact_analysis && (
              <div className="section">
                <h3>💰 Impact</h3>
                {analysis.impact_analysis.missing_impact && (
                  <p className="issue">
                    ⚠️ Missing: {analysis.impact_analysis.missing_impact}
                  </p>
                )}
                {analysis.impact_analysis.suggested_impact_statement && (
                  <div className="better-block">
                    <span className="better-label">💡 Add this:</span>
                    <p>
                      "{analysis.impact_analysis.suggested_impact_statement}"
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Conclusion */}
            {analysis.conclusion_analysis && (
              <div className="section">
                <h3>🎯 Conclusion</h3>
                {analysis.conclusion_analysis.how_they_ended && (
                  <div className="quote-block">
                    "{analysis.conclusion_analysis.how_they_ended}"
                  </div>
                )}
                {analysis.conclusion_analysis.better_conclusion && (
                  <div className="better-block">
                    <span className="better-label">💡 Try instead:</span>
                    <p>
                      "{analysis.conclusion_analysis.better_conclusion}"
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Reframes */}
            {analysis.reframes?.length > 0 && (
              <div className="section reframes-box">
                <h3>💬 Reframe These</h3>
                {analysis.reframes.map((r, i) => (
                  <div key={i} className="reframe-item">
                    <div className="reframe-original">
                      <span className="label">❌ You said:</span>
                      <p>"{r.original}"</p>
                      {r.issue && (
                        <span className="issue-small">{r.issue}</span>
                      )}
                    </div>
                    <div className="reframe-arrow">↓</div>
                    <div className="reframe-better">
                      <span className="label">✅ Try:</span>
                      <p>"{r.better_version}"</p>
                      {r.why_better && (
                        <span className="why-better">{r.why_better}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Clarity */}
            {analysis.clarity_analysis?.jargon_found?.length > 0 && (
              <div className="section">
                <h3>✨ Clarity</h3>
                <div className="chips">
                  {analysis.clarity_analysis.jargon_found.map((j, i) => (
                    <span key={i} className="chip">
                      {j}
                    </span>
                  ))}
                </div>
                {analysis.clarity_analysis.simplification_tips && (
                  <p className="dim">
                    {analysis.clarity_analysis.simplification_tips}
                  </p>
                )}
              </div>
            )}

            {/* Confidence */}
            {analysis.confidence_analysis && (
              <div className="section">
                <h3>💪 Confidence</h3>
                {analysis.confidence_analysis.hedging_words_found?.length >
                  0 && (
                  <div className="chips">
                    {analysis.confidence_analysis.hedging_words_found.map(
                      (w, i) => (
                        <span key={i} className="chip orange">
                          {w}
                        </span>
                      )
                    )}
                  </div>
                )}
                {analysis.confidence_analysis.confidence_tip && (
                  <p className="dim">
                    {analysis.confidence_analysis.confidence_tip}
                  </p>
                )}
              </div>
            )}

            {/* Articulation */}
            {analysis.articulation_feedback && (
              <div className="section">
                <h3>🗣️ Articulation</h3>
                <p className="dim">{analysis.articulation_feedback}</p>
              </div>
            )}

            {/* Strengths */}
            {analysis.strengths?.length > 0 && (
              <div className="section strengths-box">
                <h3>🌟 Your Strengths</h3>
                {analysis.strengths.map((s, i) => (
                  <div key={i} className="strength">
                    ✓ {s}
                  </div>
                ))}
              </div>
            )}

            {/* Focus Area */}
            {analysis.top_improvement && (
              <div className="section focus-box">
                <h3>🎯 #1 Focus Area</h3>
                <div className="focus-area">
                  {analysis.top_improvement.area}
                </div>
                <p className="dim">
                  {analysis.top_improvement.practice_tip}
                </p>
                {analysis.top_improvement.current && (
                  <div className="focus-compare">
                    <div className="focus-current">
                      <span className="label">Now:</span>
                      <p>{analysis.top_improvement.current}</p>
                    </div>
                    <div className="focus-target">
                      <span className="label">Goal:</span>
                      <p>{analysis.top_improvement.target}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="actions">
              <button className="cta" onClick={tryAgain}>
                🔄 Practice Again
              </button>
              <p className="actions-hint">
                Try the same scenario or pick a different audience
              </p>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <span>
          Powered by <strong>Amazon Nova</strong> · Built for the 2025
          Hackathon
        </span>
      </footer>
    </div>
  );
}