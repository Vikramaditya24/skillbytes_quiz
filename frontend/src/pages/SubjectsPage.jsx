import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation, Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function SubjectsPage() {
  const { examId } = useParams();
  const location = useLocation();
  const examName = location.state?.examName;
  const [subjects, setSubjects] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true); setError("");
    api.listSubjects(examId).then(setSubjects).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, [examId]);

  const openSubject = (s) => {
    navigate(`/subjects/${s.id}/chapters`, { state: { examId, examName, subjectName: s.name } });
  };

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/exams">Exams</Link>
        {examName && <><span>›</span><span>{examName}</span></>}
      </div>
      <div className="page-header">
        <div className="eyebrow">Step 2 of 3</div>
        <h1>Choose a subject</h1>
        <p className="muted">Select the area you want to practise.</p>
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
          <h3>Couldn't load subjects</h3>
          <p>{error}</p>
          <button className="btn secondary" onClick={load}>Try again</button>
        </div>
      )}

      {!loading && !error && subjects?.length === 0 && (
        <div className="state-card">
          <div className="state-icon neutral">—</div>
          <h3>No subjects yet</h3>
          <p>This exam doesn't have any subjects added yet.</p>
          <button className="btn secondary" onClick={() => navigate("/exams")}>Back to exams</button>
        </div>
      )}

      {!loading && !error && subjects?.length > 0 && (
        <div className="content-grid">
          {subjects.map((s, i) => (
            <div key={s.id} className="content-card" onClick={() => openSubject(s)}>
              <div className={`content-icon ${i % 2 === 0 ? "tone-a" : "tone-b"}`}>
                {s.name.slice(0, 2).toUpperCase()}
              </div>
              <div><h3>{s.name}</h3></div>
              <div className="tile-action">Choose chapter <span className="arrow">→</span></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}