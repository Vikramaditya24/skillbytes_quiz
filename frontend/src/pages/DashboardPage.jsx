import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Legend,
} from "recharts";
import { api } from "../api/client.js";

const TABS = ["Learning Velocity", "Fatigue Analysis", "Question Difficulty"];

export default function DashboardPage() {
  const [tab, setTab] = useState(0);
  return (
    <div>
      <h2>Analytics Dashboard</h2>
      <div className="tabs">
        {TABS.map((t, i) => (
          <div key={t} className={`tab ${i === tab ? "active" : ""}`} onClick={() => setTab(i)}>
            {t}
          </div>
        ))}
      </div>
      {tab === 0 && <LearningVelocityTab />}
      {tab === 1 && <FatigueTab />}
      {tab === 2 && <DifficultyTab />}
    </div>
  );
}

function LearningVelocityTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.learningVelocity().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const chartData = data.results.slice(0, 15).map((r) => ({
    name: r.user_name,
    LVI: r.learning_velocity_index,
  }));

  return (
    <div>
      <div className="explain">
        <strong>How is this calculated?</strong> LVI = {data.weights.accuracy * 100}% Accuracy +{" "}
        {data.weights.speed * 100}% Speed + {data.weights.consistency * 100}% Consistency. Speed
        scores faster-than-cohort response times higher; Consistency scores lower variance in
        response time higher (100 / (1 + coefficient of variation)). Users with too few attempts
        to compute a reliable consistency score are ranked but marked "low sample".
      </div>
      <div className="card">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} margin={{ left: 0, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9aa1ac" }} interval={0} angle={-30} textAnchor="end" height={70} />
            <YAxis tick={{ fontSize: 11, fill: "#9aa1ac" }} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#1f232c", border: "1px solid #2a2f3a" }} />
            <Bar dataKey="LVI" fill="#6c8cff" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>#</th><th>User</th><th>Attempts</th><th>Accuracy</th><th>Avg Time (ms)</th>
              <th>Consistency</th><th>LVI</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r, i) => (
              <tr key={r.user_id} className={r.low_sample ? "low-sample" : ""}>
                <td>{i + 1}</td>
                <td>{r.user_name}</td>
                <td>{r.total_attempts}</td>
                <td>{r.accuracy_pct}%</td>
                <td>{Math.round(r.avg_response_time_ms)}</td>
                <td>{r.consistency_score === null ? "—" : r.consistency_score}
                  {r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}
                </td>
                <td><strong>{r.learning_velocity_index}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FatigueTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    api.fatigue().then((d) => {
      setData(d);
      if (d.results.length) setSelectedSession(d.results[0].session_id);
    }).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const session = data.results.find((s) => s.session_id === selectedSession);
  const chartData = session
    ? session.windows.map((w) => ({
        window: w.question_range,
        Accuracy: w.accuracy_pct,
        "Avg Time (ms)": w.avg_response_time_ms,
      }))
    : [];

  return (
    <div>
      <div className="explain">
        <strong>How is this calculated?</strong> Attempts are grouped into fixed windows of{" "}
        {data.window_size} questions each. Each window's accuracy and average response time are
        compared against the session's first window. {data.disclaimer}
      </div>
      <div className="card">
        <label className="muted" style={{ fontSize: 13 }}>Session: </label>
        <select
          value={selectedSession || ""}
          onChange={(e) => setSelectedSession(e.target.value)}
          style={{ marginLeft: 8, padding: "4px 8px", background: "var(--surface-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 6 }}
        >
          {data.results.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.user_name} — {s.session_id.slice(-6)}{s.overall_fatigue_flag ? " (fatigue flagged)" : ""}
            </option>
          ))}
        </select>
      </div>
      {session && (
        <>
          <div className="card">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                <XAxis dataKey="window" tick={{ fontSize: 11, fill: "#9aa1ac" }} />
                <YAxis tick={{ fontSize: 11, fill: "#9aa1ac" }} />
                <Tooltip contentStyle={{ background: "#1f232c", border: "1px solid #2a2f3a" }} />
                <Legend />
                <Line type="monotone" dataKey="Accuracy" stroke="#4fd1a5" strokeWidth={2} />
                <Line type="monotone" dataKey="Avg Time (ms)" stroke="#f5b942" strokeWidth={2} yAxisId={0} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Window</th><th>Attempts</th><th>Accuracy</th><th>Avg Time</th>
                  <th>Δ Accuracy</th><th>Δ Time</th><th>Flag</th>
                </tr>
              </thead>
              <tbody>
                {session.windows.map((w) => (
                  <tr key={w.window_index}>
                    <td>Q{w.question_range}</td>
                    <td>{w.attempts}</td>
                    <td>{w.accuracy_pct}%</td>
                    <td>{Math.round(w.avg_response_time_ms)}ms</td>
                    <td>{w.accuracy_delta_pct > 0 ? "+" : ""}{w.accuracy_delta_pct}pp</td>
                    <td>{w.response_time_delta_pct > 0 ? "+" : ""}{w.response_time_delta_pct}%</td>
                    <td>{w.fatigue_flag && <span className="badge flag">fatigue</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function DifficultyTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.questionDifficulty().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const chartData = data.results.slice(0, 15).map((r) => ({
    name: r.question_id.slice(-6),
    Difficulty: r.difficulty_score,
  }));

  return (
    <div>
      <div className="explain">
        <strong>How is this calculated?</strong> Difficulty = {data.weights.inverted_accuracy * 100}%
        inverted accuracy (100 − accuracy%) + {data.weights.relative_time * 100}% relative response
        time, where response time is normalized against other questions in the same chapter
        (so a naturally slower chapter doesn't make every question in it look "hard"). Higher score
        = harder. Questions with fewer than 5 attempts are marked "low sample".
      </div>
      <div className="card">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} margin={{ left: 0, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9aa1ac" }} />
            <YAxis tick={{ fontSize: 11, fill: "#9aa1ac" }} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#1f232c", border: "1px solid #2a2f3a" }} />
            <Bar dataKey="Difficulty" fill="#ff6b6b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Question</th><th>Attempts</th><th>Accuracy</th>
              <th>Avg Time (ms)</th><th>Difficulty</th>
            </tr>
          </thead>
          <tbody>
            {data.results.slice(0, 50).map((r, i) => (
              <tr key={r.question_id} className={r.low_sample ? "low-sample" : ""}>
                <td>{i + 1}</td>
                <td>{r.question_text}</td>
                <td>{r.total_attempts}</td>
                <td>{r.accuracy_pct}%</td>
                <td>{Math.round(r.avg_response_time_ms)}</td>
                <td><strong>{r.difficulty_score}</strong>
                  {r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
