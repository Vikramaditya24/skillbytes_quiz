import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function ExamsPage() {
  const [exams, setExams] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true); setError("");
    api.listExams().then(setExams).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openExam = (exam) => {
    navigate(`/exams/${exam.id}/subjects`, { state: { examName: exam.name } });
  };

  return (
    <div>
      <div className="page-header">
        <div className="eyebrow">Take a quiz</div>
        <h1>Choose an exam</h1>
        <p className="muted">Pick an exam, then a subject and chapter. Each quiz presents one question at a time.</p>
      </div>

      {loading && (
        <div className="content-grid">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      )}

      {!loading && error && (
        <div className="state-card">
          <div className="state-icon danger">!</div>
          <h3>Couldn't load exams</h3>
          <p>{error}</p>
          <button className="btn secondary" onClick={load}>Try again</button>
        </div>
      )}

      {!loading && !error && exams?.length === 0 && (
        <div className="state-card">
          <div className="state-icon neutral">—</div>
          <h3>No exams available yet</h3>
          <p>Check back once exams have been added to the catalog.</p>
        </div>
      )}

      {!loading && !error && exams?.length > 0 && (
        <div className="content-grid">
          {exams.map((exam, i) => (
            <div key={exam.id} className="content-card" onClick={() => openExam(exam)}>
              <div className={`content-icon ${i % 2 === 0 ? "tone-a" : "tone-b"}`}>
                {exam.name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <h3>{exam.name}</h3>
                {exam.description && <p>{exam.description}</p>}
              </div>
              <div className="tile-action">Choose subject <span className="arrow">→</span></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}