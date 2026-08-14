import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

export default function LoginPage() {
  const [users, setUsers] = useState([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const { login, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate("/exams");
      return;
    }
    api
      .listUsers()
      .then(setUsers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = async () => {
    if (!selected) return;
    try {
      const res = await api.login(selected);
      login(res.user);
      navigate("/exams");
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="card center" style={{ maxWidth: 420, margin: "80px auto" }}>
      <h1>Skillbytes Quiz</h1>
      <p className="muted">Select a predefined user to continue. (Dummy authentication.)</p>
      {loading && <p className="muted">Loading users…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && (
        <>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            style={{
              width: "100%",
              padding: "10px 12px",
              marginBottom: 16,
              background: "var(--surface-2)",
              color: "var(--text)",
              border: "1px solid var(--border)",
              borderRadius: 8,
            }}
          >
            <option value="">Choose a user…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.email})
              </option>
            ))}
          </select>
          <button className="btn" disabled={!selected} onClick={handleLogin}>
            Log in
          </button>
        </>
      )}
    </div>
  );
}
