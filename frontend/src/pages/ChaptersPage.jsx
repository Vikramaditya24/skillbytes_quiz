import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation, Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

export default function ChaptersPage() {
  const { subjectId } = useParams();
  const location = useLocation();
  const { examId, examName, subjectName } = location.state || {};
  const [chapters, setChapters] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  const load = () => {
    setLoading(true); setError("");
    api.listChapters(subjectId).then(setChapters).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, [subjectId]);

  const startQuiz = async (chapterId) => {
    setStarting(chapterId); setError("");
    try {
      const session = await api.startQuiz(chapterId, user.id);
      navigate(`/quiz/${session.id}`);
    } catch (e) { setError(e.message); setStarting(null); }
  };

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/exams">Exams</Link>
        {examName && <><span>›</span><Link to={examId ? `/exams/${examId}/subjects` : "/exams"}>{examName}</Link></>}
        {subjectName && <><span>›</span><span>{subjectName}</span></>}
      </div>
      <div className="page-header">
        <div className="eyebrow">Step 3 of 3</div>
        <h1>Choose a chapter</h1>
        <p className="muted">Each attempt samples a short quiz from the selected chapter.</p>
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
          <h3>Couldn't start your quiz</h3>
          <p>{error}</p>
          <button className="btn secondary" onClick={load}>Try again</button>
        </div>
      )}

      {!loading && !error && chapters?.length === 0 && (
        <div className="state-card">
          <div className="state-icon neutral">—</div>
          <h3>No chapters yet</h3>
          <p>This subject doesn't have any chapters added yet.</p>
        </div>
      )}

      {!loading && !error && chapters?.length > 0 && (
        <div className="content-grid">
          {chapters.map((c, i) => (
            <div
              key={c.id}
              className={`content-card${starting === c.id ? " busy" : ""}`}
              onClick={() => !starting && startQuiz(c.id)}
            >
              <div className={`content-icon ${i % 2 === 0 ? "tone-a" : "tone-b"}`}>
                {c.name.slice(0, 2).toUpperCase()}
              </div>
              <div><h3>{c.name}</h3></div>
              <div className="tile-action">
                {starting === c.id ? "Starting quiz…" : <>Start 15-question quiz <span className="arrow">→</span></>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}