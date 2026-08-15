import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

export default function ResultPage() {
  const { sessionId } = useParams(); const { user } = useAuth(); const [result, setResult] = useState(null); const [error, setError] = useState(""); const navigate = useNavigate();
  useEffect(() => { api.getResult(sessionId, user.id).then(setResult).catch((e) => setError(e.message)); }, [sessionId, user.id]);
  if (error) return <p className="error">{error}</p>;
  if (!result) return <p className="muted">Loading your result…</p>;
  return <div className="card center" style={{ maxWidth: 560, margin: "60px auto", padding: 32 }}>
    <div className="small-note">QUIZ COMPLETE</div>
    <h1 style={{ margin: "8px 0 0" }}>Nice work, {user.name.split(" ")[0]}</h1>
    <div className="score-hero">{result.score}<span style={{ fontSize: 22, color: "var(--text-dim)" }}> / {result.total_questions}</span></div>
    <p className="muted" style={{ marginBottom: 24 }}>{result.accuracy_pct}% accuracy · no negative marking</p>
    <div className="callout" style={{ textAlign: "left", marginBottom: 22 }}>
      Your result is now part of your personal progress history. Return to My Progress to see how this attempt contributes to your analytics.
    </div>
    <button className="btn" onClick={() => navigate("/progress")}>View My Progress</button>
    <button className="btn secondary" style={{ marginLeft: 8 }} onClick={() => navigate("/exams")}>Take another quiz</button>
  </div>;
}
