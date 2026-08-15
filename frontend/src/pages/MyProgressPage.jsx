import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

function Kpi({ label, value, sub }) {
  return <div className="card kpi">
    <div className="kpi-label">{label}</div>
    <div className="kpi-value">{value}</div>
    {sub && <div className="kpi-sub">{sub}</div>}
  </div>;
}

function seconds(ms) {
  if (ms == null) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

export default function MyProgressPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    setError("");
    api.myProgress(user.id).then(setData).catch((e) => setError(e.message));
  }, [user.id]);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading your progress…</p>;

  if (!data.has_data) {
    return (
      <div>
        <div className="page-header">
          <h1>Welcome, {user.name.split(" ")[0]}</h1>
          <p className="muted">Your learner dashboard will build as you complete quizzes.</p>
        </div>
        <div className="card empty">
          <h3>No completed quizzes yet</h3>
          <p className="muted">Complete your first quiz to start building your performance history and see how your accuracy and response time change during an attempt.</p>
          <button className="btn" onClick={() => navigate("/exams")}>Start your first quiz</button>
        </div>
      </div>
    );
  }

  const lvi = data.learning_velocity;
  const fatigue = data.latest_session_fatigue;
  const progression = fatigue?.question_progression || [];
  const chartData = progression.map((p) => ({
    question: `Q${p.question_number}`,
    Accuracy: p.accuracy_pct,
    "Response time": Number((p.avg_response_time_ms / 1000).toFixed(2)),
  }));

  return (
    <div>
      <div className="page-header">
        <h1>Welcome back, {user.name.split(" ")[0]}</h1>
        <p className="muted">Your personal performance dashboard. Cohort comparisons are kept separate under Cohort Analytics.</p>
      </div>

      <div className="kpi-grid">
        <Kpi label="Learning Velocity Index" value={lvi.learning_velocity_index} sub={lvi.low_sample ? "Small sample — interpret cautiously" : "Overall score out of 100"} />
        <Kpi label="Accuracy" value={`${lvi.accuracy_pct}%`} sub={`${lvi.total_attempts} questions answered`} />
        <Kpi label="Avg response time" value={seconds(lvi.avg_response_time_ms)} sub="Across your recorded attempts" />
        <Kpi label="Consistency" value={lvi.consistency_score == null ? "—" : lvi.consistency_score} sub={lvi.consistency_score == null ? "More attempts needed" : "Response-time consistency / 100"} />
      </div>

      <div className="section-heading">
        <div><h3>Learning Velocity Index</h3><p className="muted">A compact view of the three components behind your score.</p></div>
      </div>
      <div className="card">
        <div className="component-grid">
          <div><div className="kpi-label">Accuracy · 50%</div><div className="kpi-value" style={{ fontSize: 22 }}>{lvi.accuracy_score}</div></div>
          <div><div className="kpi-label">Speed · 30%</div><div className="kpi-value" style={{ fontSize: 22 }}>{lvi.speed_score}</div></div>
          <div><div className="kpi-label">Consistency · 20%</div><div className="kpi-value" style={{ fontSize: 22 }}>{lvi.consistency_score == null ? "—" : lvi.consistency_score}</div></div>
        </div>
        <div className="explain" style={{ margin: "16px 0 0" }}>
          LVI combines accuracy, relative response speed, and response-time consistency. Accuracy carries the most weight; speed and consistency provide secondary signals.
        </div>
      </div>

      <div className="section-heading">
        <div>
          <h3>Most recent quiz · performance progression</h3>
          <p className="muted">Question-by-question view of how accuracy and response time changed during the attempt.</p>
        </div>
        {fatigue?.overall_fatigue_flag && <span className="badge flag">fatigue signal detected</span>}
      </div>

      {progression.length ? (
        <div className="card chart-card">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 10, right: 14, left: -8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#263241" />
              <XAxis dataKey="question" tick={{ fontSize: 11, fill: "#9aa7b5" }} />
              <YAxis yAxisId="accuracy" domain={[0, 100]} tick={{ fontSize: 11, fill: "#9aa7b5" }} unit="%" />
              <YAxis yAxisId="time" orientation="right" tick={{ fontSize: 11, fill: "#9aa7b5" }} unit="s" />
              <Tooltip
                formatter={(value, name) => [name === "Response time" ? `${value} s` : `${value}%`, name]}
                contentStyle={{ background: "#111720", border: "1px solid #263241", borderRadius: 7 }}
              />
              <Line yAxisId="accuracy" type="monotone" dataKey="Accuracy" stroke="#5bd6a1" strokeWidth={2} dot={{ r: 3 }} />
              <Line yAxisId="time" type="monotone" dataKey="Response time" stroke="#7aa2ff" strokeWidth={2} dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
          <div className="small-note">Accuracy is shown as a percentage; response time uses seconds for readability. The fatigue heuristic remains a descriptive signal, not a diagnosis.</div>
        </div>
      ) : (
        <div className="card empty"><h3>Not enough progression data</h3><p className="muted">Complete a quiz with recorded question attempts to see performance through the attempt.</p></div>
      )}

      <div className="section-heading">
        <div><h3>Recent activity</h3><p className="muted">Your latest completed quiz sessions.</p></div>
      </div>
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Chapter</th><th>Score</th><th>Accuracy</th><th>Completed</th></tr></thead>
          <tbody>
            {data.recent_sessions.map((s) => (
              <tr key={s.session_id}>
                <td>{s.chapter_name}</td>
                <td><strong>{s.score}/{s.total_questions}</strong></td>
                <td>{s.accuracy_pct}%</td>
                <td>{s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="btn" onClick={() => navigate("/exams")}>Take another quiz</button>
    </div>
  );
}
