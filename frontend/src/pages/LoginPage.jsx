import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

function initials(name) {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function LoginPage() {
  const [users, setUsers] = useState([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { login, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) { navigate("/progress"); return; }
    api.listUsers().then(setUsers).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const handleLogin = async () => {
    if (!selected || submitting) return;
    setError(""); setSubmitting(true);
    try {
      const res = await api.login(selected);
      login(res.user);
      navigate("/progress");
    } catch (e) { setError(e.message); setSubmitting(false); }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-mark">S</div>
        <h1>Welcome to Skillbytes</h1>
        <p className="muted">
          A quiz experience with learner-level performance analytics. Pick a demo learner below to explore the app.
        </p>

        {error && <p className="error" style={{ marginBottom: 18 }}>{error}</p>}

        <span className="field-label">Demo learner</span>

        {loading ? (
          <div className="learner-list" style={{ overflow: "hidden" }}>
            <div className="skeleton-row" />
            <div className="skeleton-row" />
            <div className="skeleton-row" />
          </div>
        ) : (
          <div className="learner-list">
            {users.map((u) => (
              <button
                key={u.id}
                type="button"
                className={`learner-option${selected === u.id ? " selected" : ""}`}
                onClick={() => setSelected(u.id)}
              >
                <span className="learner-avatar">{initials(u.name)}</span>
                <span className="learner-info">
                  <div className="learner-name">{u.name}</div>
                  <div className="learner-email">{u.email}</div>
                </span>
                <span className="radio-dot" />
              </button>
            ))}
          </div>
        )}

        {!loading && (
          <>
            <button className="btn" style={{ width: "100%" }} disabled={!selected || submitting} onClick={handleLogin}>
              {submitting ? "Signing in…" : "Continue"}
            </button>
            <p className="small-note" style={{ marginTop: 14, textAlign: "center" }}>
              Dummy authentication is used as permitted by the assignment.
            </p>
          </>
        )}
      </div>
    </div>
  );
}