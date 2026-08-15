import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function ExamsPage() {
  const [exams, setExams] = useState([]); const [error, setError] = useState(""); const navigate = useNavigate();
  useEffect(() => { api.listExams().then(setExams).catch((e) => setError(e.message)); }, []);
  return <div>
    <div className="page-header"><h1>Take a Quiz</h1><p className="muted">Choose an exam, then a subject and chapter. Each quiz presents one question at a time.</p></div>
    {error && <p className="error">{error}</p>}
    <div className="grid">{exams.map((exam) => <div key={exam.id} className="tile" onClick={() => navigate(`/exams/${exam.id}/subjects`)}>
      <div><h3>{exam.name}</h3><p>{exam.description}</p></div><div className="tile-action">Choose subject →</div>
    </div>)}</div>
  </div>;
}
