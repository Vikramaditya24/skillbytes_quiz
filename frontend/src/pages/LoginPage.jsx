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
    if (user) { navigate("/progress"); return; }
    api.listUsers().then(setUsers).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const handleLogin = async () => {
    if (!selected) return;
    setError("");
    try {
      const res = await api.login(selected);
      login(res.user);
      navigate("/progress");
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="card center" style={{ maxWidth: 500, margin: "80px auto 0", padding: 32 }}>
      <span className="brand-mark" style={{ margin: "0 auto 14px" }}>S</span>
      <h1 style={{ margin: "0 0 8px", letterSpacing: "-.04em" }}>Skillbytes Quiz</h1>
      <p className="muted" style={{ lineHeight: 1.55, margin: "0 auto 24px", maxWidth: 390 }}>
        A quiz experience with learner-level performance analytics. Select a demo learner to explore the application.
      </p>
      {loading && <p className="muted">Loading predefined learners…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && (
        <div style={{ textAlign: "left" }}>
          <label className="small-note" htmlFor="user">Demo learner</label>
          <select id="user" className="select" style={{ margin: "6px 0 14px" }} value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">Choose a learner…</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.name} · {u.email}</option>)}
          </select>
          <button className="btn" style={{ width: "100%" }} disabled={!selected} onClick={handleLogin}>Continue</button>
          <p className="small-note" style={{ marginTop: 12, textAlign: "center" }}>
            Dummy authentication is used as permitted by the assignment.
          </p>
        </div>
      )}
    </div>
  );
}
