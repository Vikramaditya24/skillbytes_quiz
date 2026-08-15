import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

export default function ChaptersPage() {
  const { subjectId } = useParams(); const [chapters, setChapters] = useState([]); const [error, setError] = useState(""); const [starting, setStarting] = useState(null);
  const { user } = useAuth(); const navigate = useNavigate();
  useEffect(() => { api.listChapters(subjectId).then(setChapters).catch((e) => setError(e.message)); }, [subjectId]);
  const startQuiz = async (chapterId) => {
    setStarting(chapterId); setError("");
    try { const session = await api.startQuiz(chapterId, user.id); navigate(`/quiz/${session.id}`); }
    catch (e) { setError(e.message); setStarting(null); }
  };
  return <div>
    <div className="breadcrumb"><Link to="/exams">Exams</Link><span>/</span>Chapters</div>
    <div className="page-header"><h1>Choose a Chapter</h1><p className="muted">Each attempt samples a short quiz from the selected chapter.</p></div>
    {error && <p className="error">{error}</p>}
    <div className="grid">{chapters.map((c) => <div key={c.id} className="tile" onClick={() => startQuiz(c.id)}>
      <div><h3>{c.name}</h3></div><div className="tile-action">{starting === c.id ? "Starting quiz…" : "Start 15-question quiz →"}</div>
    </div>)}</div>
  </div>;
}
