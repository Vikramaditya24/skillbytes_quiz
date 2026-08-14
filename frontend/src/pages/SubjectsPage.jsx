import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function SubjectsPage() {
  const { examId } = useParams();
  const [subjects, setSubjects] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.listSubjects(examId).then(setSubjects).catch((e) => setError(e.message));
  }, [examId]);

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/exams">Exams</Link>
        <span>/</span> Subjects
      </div>
      <h2>Choose a Subject</h2>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        {subjects.map((s) => (
          <div key={s.id} className="tile" onClick={() => navigate(`/subjects/${s.id}/chapters`)}>
            <h3>{s.name}</h3>
          </div>
        ))}
      </div>
    </div>
  );
}
