import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from "recharts";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

const TABS = ["Learning Velocity", "Fatigue Analysis", "Question Difficulty"];

function seconds(ms) {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

export default function CohortAnalyticsPage() {
  const [tab, setTab] = useState(0);
  return (
    <div>
      <div className="page-header">
        <h1>Cohort Analytics</h1>
        <p className="muted">Cross-learner analytics derived from the shared question-attempt event stream. These views are intentionally separate from your personal dashboard.</p>
      </div>
      <div className="tabs">
        {TABS.map((t, i) => <div key={t} className={`tab ${i === tab ? "active" : ""}`} onClick={() => setTab(i)}>{t}</div>)}
      </div>
      {tab === 0 && <LearningVelocityTab />}
      {tab === 1 && <FatigueTab />}
      {tab === 2 && <DifficultyTab />}
    </div>
  );
}

function LearningVelocityTab() {
  const { user } = useAuth();
  const [data, setData] = useState(null); const [error, setError] = useState("");
  useEffect(() => { api.learningVelocity().then(setData).catch((e) => setError(e.message)); }, []);
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading cohort analytics…</p>;

  const chartData = data.results.map((r, i) => ({ name: r.user_name, LVI: r.learning_velocity_index, rank: i + 1 }));
  return <div>
    <div className="explain"><strong>Learning Velocity Index.</strong> Accuracy contributes {data.weights.accuracy * 100}%, relative speed {data.weights.speed * 100}%, and response-time consistency {data.weights.consistency * 100}%. The ranking is cohort-wide; low-sample rows are marked rather than hidden.</div>
    <div className="card chart-card compact">
      <div className="chart-scroll"><div className="chart-min-width" style={{ minWidth: Math.max(720, chartData.length * 34) }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#263241" />
            <XAxis dataKey="name" interval={0} angle={-55} textAnchor="end" height={75} tick={{ fontSize: 9, fill: "#9aa7b5" }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#9aa7b5" }} />
            <Tooltip formatter={(v) => [v, "LVI"]} contentStyle={{ background: "#111720", border: "1px solid #263241", borderRadius: 7 }} />
            <Bar dataKey="LVI" fill="#7aa2ff" barSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div></div>
    </div>
    <div className="card table-wrap">
      <table>
        <thead><tr><th>#</th><th>Learner</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Consistency</th><th>LVI</th></tr></thead>
        <tbody>{data.results.map((r, i) =>
          <tr key={r.user_id} className={`${r.low_sample ? "low-sample " : ""}${r.user_id === user.id ? "current-user" : ""}`}>
            <td className="rank">{i + 1}</td><td><strong>{r.user_name}</strong>{r.user_id === user.id && <span className="badge" style={{ marginLeft: 7 }}>you</span>}</td>
            <td>{r.total_attempts}</td><td>{r.accuracy_pct}%</td><td>{seconds(r.avg_response_time_ms)}</td>
            <td>{r.consistency_score == null ? "—" : r.consistency_score}{r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}</td>
            <td><strong>{r.learning_velocity_index}</strong></td>
          </tr>
        )}</tbody>
      </table>
    </div>
  </div>;
}

function FatigueTab() {
  const [data, setData] = useState(null); const [error, setError] = useState(""); const [selectedSession, setSelectedSession] = useState(null);
  useEffect(() => { api.fatigue().then((d) => { setData(d); if (d.results.length) setSelectedSession(d.results[0].session_id); }).catch((e) => setError(e.message)); }, []);
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading cohort fatigue analytics…</p>;
  const session = data.results.find((s) => s.session_id === selectedSession);
  const chartData = session ? session.windows.map((w) => ({ window: `Q${w.question_range}`, Accuracy: w.accuracy_pct, "Avg response": Number((w.avg_response_time_ms / 1000).toFixed(2)) })) : [];

  return <div>
    <div className="explain"><strong>Fatigue Analysis.</strong> The assignment's example uses five-question windows. Each window is compared with the first window; the flag requires both a meaningful accuracy drop and a response-time increase. This is a descriptive heuristic, not a clinical or causal measure.</div>
    <div className="card tight">
      <label className="small-note">Quiz session</label>
      <select className="select" style={{ maxWidth: 520, marginTop: 6 }} value={selectedSession || ""} onChange={(e) => setSelectedSession(e.target.value)}>
        {data.results.map((s) => <option key={s.session_id} value={s.session_id}>{s.user_name} · {s.session_id.slice(-6)}{s.overall_fatigue_flag ? " · fatigue signal" : ""}</option>)}
      </select>
    </div>
    {session ? <>
      <div className="card chart-card compact">
        <ResponsiveContainer width="100%" height={290}>
          <LineChart data={chartData} margin={{ top: 8, right: 18, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#263241" />
            <XAxis dataKey="window" tick={{ fontSize: 11, fill: "#9aa7b5" }} />
            <YAxis yAxisId="accuracy" domain={[0, 100]} tick={{ fontSize: 11, fill: "#9aa7b5" }} unit="%" />
            <YAxis yAxisId="time" orientation="right" tick={{ fontSize: 11, fill: "#9aa7b5" }} unit="s" />
            <Tooltip formatter={(v, n) => [n === "Avg response" ? `${v} s` : `${v}%`, n]} contentStyle={{ background: "#111720", border: "1px solid #263241", borderRadius: 7 }} />
            <Line yAxisId="accuracy" type="monotone" dataKey="Accuracy" stroke="#5bd6a1" strokeWidth={2} />
            <Line yAxisId="time" type="monotone" dataKey="Avg response" stroke="#7aa2ff" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="card table-wrap"><table><thead><tr><th>Window</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Δ accuracy</th><th>Δ time</th><th>Signal</th></tr></thead>
        <tbody>{session.windows.map((w) => <tr key={w.window_index}><td>Q{w.question_range}</td><td>{w.attempts}</td><td>{w.accuracy_pct}%</td><td>{seconds(w.avg_response_time_ms)}</td><td>{w.accuracy_delta_pct > 0 ? "+" : ""}{w.accuracy_delta_pct} pp</td><td>{w.response_time_delta_pct > 0 ? "+" : ""}{w.response_time_delta_pct}%</td><td>{w.fatigue_flag ? <span className="badge flag">fatigue</span> : "—"}</td></tr>)}</tbody>
      </table></div>
    </> : <div className="card empty"><h3>No session data</h3><p className="muted">No completed quiz attempts are available for cohort fatigue analysis.</p></div>}
  </div>;
}

function DifficultyTab() {
  const [data, setData] = useState(null); const [error, setError] = useState("");
  useEffect(() => { api.questionDifficulty().then(setData).catch((e) => setError(e.message)); }, []);
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading question difficulty…</p>;

  const chartData = data.results.slice(0, 40).map((r) => ({ name: r.question_id.slice(-6), Difficulty: r.difficulty_score }));
  return <div>
    <div className="explain"><strong>Question Difficulty Index.</strong> Difficulty combines {data.weights.inverted_accuracy * 100}% inverted accuracy with {data.weights.relative_time * 100}% relative response time. Higher means harder. Response time is normalized within the question's chapter so naturally slower chapters do not bias the entire ranking.</div>
    <div className="card chart-card compact">
      <div className="chart-scroll"><div className="chart-min-width" style={{ minWidth: Math.max(900, chartData.length * 24) }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#263241" />
            <XAxis dataKey="name" interval={0} angle={-55} textAnchor="end" height={75} tick={{ fontSize: 9, fill: "#9aa7b5" }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#9aa7b5" }} />
            <Tooltip formatter={(v) => [v, "Difficulty"]} contentStyle={{ background: "#111720", border: "1px solid #263241", borderRadius: 7 }} />
            <Bar dataKey="Difficulty" fill="#e9bd67" barSize={9} />
          </BarChart>
        </ResponsiveContainer>
      </div></div>
    </div>
    <div className="card table-wrap"><table><thead><tr><th>#</th><th>Question</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Difficulty</th></tr></thead>
      <tbody>{data.results.slice(0, 50).map((r, i) => <tr key={r.question_id} className={r.low_sample ? "low-sample" : ""}><td className="rank">{i + 1}</td><td style={{ minWidth: 320 }}>{r.question_text}</td><td>{r.total_attempts}</td><td>{r.accuracy_pct}%</td><td>{seconds(r.avg_response_time_ms)}</td><td><strong>{r.difficulty_score}</strong>{r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}</td></tr>)}</tbody>
    </table></div>
  </div>;
}
