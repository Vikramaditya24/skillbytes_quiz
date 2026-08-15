import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function ResultPage() {
  const { sessionId } = useParams();
  const { user } = useAuth();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [ringReady, setRingReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.getResult(sessionId, user.id).then(setResult).catch((e) => setError(e.message));
  }, [sessionId, user.id]);

  useEffect(() => {
    if (!result) return;
    const t = requestAnimationFrame(() => setRingReady(true));
    return () => cancelAnimationFrame(t);
  }, [result]);

  if (error) {
    return (
      <div className="result-shell">
        <div className="state-card">
          <div className="state-icon danger">!</div>
          <h3>Couldn't load your result</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="result-shell">
        <div className="card center" style={{ padding: 40 }}>
          <p className="muted">Loading your result…</p>
        </div>
      </div>
    );
  }

  const incorrect = result.total_questions - result.score;
  const offset = CIRCUMFERENCE * (1 - result.accuracy_pct / 100);

  return (
    <div className="result-shell">
      <div className="card result-card">
        <div className="small-note">QUIZ COMPLETE</div>
        <h1 style={{ margin: "8px 0 0", fontFamily: "var(--font-display)", fontSize: 24 }}>
          Nice work, {user.name.split(" ")[0]}
        </h1>

        <div className="result-ring-wrap">
          <svg width="168" height="168" viewBox="0 0 128 128">
            <circle className="result-ring-track" cx="64" cy="64" r={RADIUS} />
            <circle
              className="result-ring-fill"
              cx="64" cy="64" r={RADIUS}
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={ringReady ? offset : CIRCUMFERENCE}
            />
          </svg>
          <div className="result-ring-center">
            <div className="score-hero">{result.score}<span style={{ fontSize: 16, color: "var(--ink-muted)" }}>/{result.total_questions}</span></div>
            <div className="ring-pct">{result.accuracy_pct}% accuracy</div>
          </div>
        </div>

        <div className="result-split">
          <span className="result-chip correct"><span className="dot" /> {result.score} correct</span>
          <span className="result-chip incorrect"><span className="dot" /> {incorrect} incorrect</span>
        </div>

        <div className="callout" style={{ textAlign: "left", marginBottom: 22 }}>
          Your result is now part of your personal progress history. Return to My Progress to see how this attempt contributes to your analytics.
        </div>

        <div className="result-actions">
          <button className="btn" onClick={() => navigate("/progress")}>View my progress</button>
          <button className="btn secondary" onClick={() => navigate("/exams")}>Take another quiz</button>
        </div>
      </div>
    </div>
  );
}