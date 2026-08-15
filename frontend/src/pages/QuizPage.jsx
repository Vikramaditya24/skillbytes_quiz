import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

export default function QuizPage() {
  const { sessionId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState(null);
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadQuestion = () => {
    setError(""); setSelected(null); setFeedback(null);
    api.currentQuestion(sessionId, user.id).then(setCurrent).catch((e) => setError(e.message));
  };
  useEffect(() => { loadQuestion(); }, [sessionId]);

  const handleNext = async () => {
    if (feedback) {
      if (feedback.sessionStatus === "completed") navigate(`/result/${sessionId}`);
      else loadQuestion();
      return;
    }
    if (!selected || !current || submitting) return;
    setSubmitting(true); setError("");
    try {
      const resp = await api.submitAnswer(sessionId, user.id, current.question.id, selected);
      setFeedback({ isCorrect: resp.is_correct, correctKey: resp.correct_option_key, sessionStatus: resp.session_status });
    } catch (e) { setError(e.message); } finally { setSubmitting(false); }
  };

  if (error) return <div><p className="error">{error}</p><button className="btn secondary" onClick={() => navigate("/progress")}>Back to My Progress</button></div>;
  if (!current) return <p className="muted">Loading question…</p>;

  const pct = Math.round((current.question_number / current.total_questions) * 100);

  return (
    <div style={{ maxWidth: 820, margin: "0 auto" }}>
      <div className="quiz-meta">
        <span>Quiz in progress</span>
        <strong style={{ color: "var(--text)" }}>Question {current.question_number} of {current.total_questions}</strong>
      </div>
      <div className="progress-bar"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
      <div className="card" style={{ padding: "28px 30px" }}>
        <div className="small-note">Choose one answer · previous questions cannot be revisited</div>
        <h2 className="quiz-question">{current.question.text}</h2>
        {current.question.options.map((opt) => {
          let cls = "option";
          if (feedback) {
            if (opt.key === feedback.correctKey) cls += " correct";
            else if (opt.key === selected) cls += " incorrect";
          } else if (opt.key === selected) cls += " selected";
          return <button key={opt.key} className={cls} disabled={!!feedback || submitting} onClick={() => setSelected(opt.key)}>
            <strong>{opt.key}</strong>&nbsp;&nbsp;{opt.text}
          </button>;
        })}
        {feedback && (
          <div className={feedback.isCorrect ? "callout" : "error"} style={{ marginTop: 14 }}>
            {feedback.isCorrect ? "Correct answer." : "Not quite. The correct answer is highlighted."}
          </div>
        )}
        <div className="answer-actions">
          <button className="btn" disabled={(!feedback && !selected) || submitting} onClick={handleNext}>
            {feedback ? (feedback.sessionStatus === "completed" ? "View result" : "Next question") : (submitting ? "Submitting…" : "Submit answer")}
          </button>
        </div>
      </div>
      <p className="small-note" style={{ textAlign: "center" }}>Your answer and response duration are recorded server-side as a quiz attempt event.</p>
    </div>
  );
}
