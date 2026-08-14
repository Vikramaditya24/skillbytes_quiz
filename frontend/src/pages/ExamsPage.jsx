import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function ExamsPage() {
  const [exams, setExams] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.listExams().then(setExams).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h2>Choose an Exam</h2>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        {exams.map((exam) => (
          <div key={exam.id} className="tile" onClick={() => navigate(`/exams/${exam.id}/subjects`)}>
            <h3>{exam.name}</h3>
            <p>{exam.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
