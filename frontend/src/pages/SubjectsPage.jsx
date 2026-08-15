import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function SubjectsPage() {
  const { examId } = useParams(); const [subjects, setSubjects] = useState([]); const [error, setError] = useState(""); const navigate = useNavigate();
  useEffect(() => { api.listSubjects(examId).then(setSubjects).catch((e) => setError(e.message)); }, [examId]);
  return <div>
    <div className="breadcrumb"><Link to="/exams">Exams</Link><span>/</span>Subjects</div>
    <div className="page-header"><h1>Choose a Subject</h1><p className="muted">Select the area you want to practise.</p></div>
    {error && <p className="error">{error}</p>}
    <div className="grid">{subjects.map((s) => <div key={s.id} className="tile" onClick={() => navigate(`/subjects/${s.id}/chapters`)}>
      <div><h3>{s.name}</h3></div><div className="tile-action">Choose chapter →</div>
    </div>)}</div>
  </div>;
}
