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
  const [feedback, setFeedback] = useState(null); // { isCorrect, correctKey }
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadQuestion = () => {
    setSelected(null);
    setFeedback(null);
    api
      .currentQuestion(sessionId)
      .then(setCurrent)
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    loadQuestion();
  }, [sessionId]);

  const handleNext = async () => {
    if (feedback) {
      // already submitted this question - move on
      if (feedback.sessionStatus === "completed") {
        navigate(`/result/${sessionId}`);
      } else {
        loadQuestion();
      }
      return;
    }
    if (!selected || !current) return;
    setSubmitting(true);
    try {
      const resp = await api.submitAnswer(sessionId, user.id, current.question.id, selected);
      setFeedback({
        isCorrect: resp.is_correct,
        correctKey: resp.correct_option_key,
        sessionStatus: resp.session_status,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <p className="error">{error}</p>;
  if (!current) return <p className="muted">Loading question…</p>;

  const pct = Math.round(((current.question_number - 1) / current.total_questions) * 100);

  return (
    <div>
      <div className="breadcrumb">
        Question {current.question_number} of {current.total_questions}
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{current.question.text}</h2>
        {current.question.options.map((opt) => {
          let cls = "option";
          if (feedback) {
            if (opt.key === feedback.correctKey) cls += " correct";
            else if (opt.key === selected) cls += " incorrect";
          } else if (opt.key === selected) {
            cls += " selected";
          }
          return (
            <button
              key={opt.key}
              className={cls}
              disabled={!!feedback}
              onClick={() => setSelected(opt.key)}
            >
              {opt.key}. {opt.text}
            </button>
          );
        })}
        <button
          className="btn"
          style={{ marginTop: 8 }}
          disabled={(!feedback && !selected) || submitting}
          onClick={handleNext}
        >
          {feedback
            ? feedback.sessionStatus === "completed"
              ? "See Result"
              : "Next"
            : submitting
            ? "Submitting…"
            : "Submit Answer"}
        </button>
      </div>
    </div>
  );
}
