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
  const [history, setHistory] = useState({}); // { [questionNumber]: boolean }

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
      setHistory((h) => ({ ...h, [current.question_number]: resp.is_correct }));
    } catch (e) { setError(e.message); } finally { setSubmitting(false); }
  };

  if (error) {
    return (
      <div className="quiz-shell">
        <div className="state-card">
          <div className="state-icon danger">!</div>
          <h3>Something went wrong</h3>
          <p>{error}</p>
          <button className="btn secondary" onClick={() => navigate("/progress")}>Back to My Progress</button>
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className="quiz-shell">
        <div className="card quiz-card">
          <div className="quiz-skeleton-line" style={{ width: 140, height: 12, marginBottom: 20 }} />
          <div className="quiz-skeleton-line" style={{ width: "90%", height: 26, marginBottom: 10 }} />
          <div className="quiz-skeleton-line" style={{ width: "60%", height: 26, marginBottom: 26 }} />
          <div className="quiz-skeleton-line" style={{ height: 50, marginBottom: 10, borderRadius: 14 }} />
          <div className="quiz-skeleton-line" style={{ height: 50, marginBottom: 10, borderRadius: 14 }} />
          <div className="quiz-skeleton-line" style={{ height: 50, marginBottom: 10, borderRadius: 14 }} />
          <div className="quiz-skeleton-line" style={{ height: 50, borderRadius: 14 }} />
        </div>
      </div>
    );
  }

  const total = current.total_questions;

  return (
    <div className="quiz-shell">
      <div className="quiz-meta">
        <span>Quiz in progress</span>
        <strong style={{ color: "var(--ink)" }}>Question {current.question_number} of {total}</strong>
      </div>

      <div className="quiz-trail">
        {Array.from({ length: total }, (_, i) => {
          const qNum = i + 1;
          let cls = "trail-node";
          if (qNum === current.question_number) cls += " current";
          else if (history[qNum] === true) cls += " done-correct";
          else if (history[qNum] === false) cls += " done-incorrect";
          return <span key={qNum} className={cls} />;
        })}
      </div>

      <div className="card quiz-card">
        <div className="quiz-card-inner" key={current.question.id}>
          <div className="small-note">Choose one answer · previous questions cannot be revisited</div>
          <h2 className="quiz-question">{current.question.text}</h2>
          {current.question.options.map((opt) => {
            let cls = "option";
            if (feedback) {
              if (opt.key === feedback.correctKey) cls += " correct";
              else if (opt.key === selected) cls += " incorrect";
            } else if (opt.key === selected) cls += " selected";
            return (
              <button key={opt.key} className={cls} disabled={!!feedback || submitting} onClick={() => setSelected(opt.key)}>
                <strong>{opt.key}</strong>&nbsp;&nbsp;{opt.text}
              </button>
            );
          })}
          {feedback && (
            <div className={`quiz-feedback ${feedback.isCorrect ? "correct" : "incorrect"}`}>
              {feedback.isCorrect ? "✓✓ Correct answer." : "✕ Not quite — the correct answer is highlighted."}
            </div>
          )}
          <div className="answer-actions">
            <button className="btn" disabled={(!feedback && !selected) || submitting} onClick={handleNext}>
              {feedback ? (feedback.sessionStatus === "completed" ? "View result" : "Next question") : (submitting ? "Submitting…" : "Submit answer")}
            </button>
          </div>
        </div>
      </div>
      <p className="small-note" style={{ textAlign: "center", marginTop: 14 }}>
        Your answer and response duration are recorded server-side as a quiz attempt event.
      </p>
    </div>
  );
}