import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";

export default function ResultPage() {
  const { sessionId } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.getResult(sessionId).then(setResult).catch((e) => setError(e.message));
  }, [sessionId]);

  if (error) return <p className="error">{error}</p>;
  if (!result) return <p className="muted">Loading result…</p>;

  return (
    <div className="card center" style={{ maxWidth: 420, margin: "60px auto" }}>
      <p className="muted">Quiz complete</p>
      <div className="score-hero">
        {result.score}/{result.total_questions}
      </div>
      <p className="muted">{result.accuracy_pct}% accuracy · no negative marking</p>
      <div style={{ marginTop: 20 }}>
        <button className="btn secondary" onClick={() => navigate("/exams")}>
          Back to Exams
        </button>
        <button className="btn" style={{ marginLeft: 10 }} onClick={() => navigate("/dashboard")}>
          View Analytics
        </button>
      </div>
    </div>
  );
}
