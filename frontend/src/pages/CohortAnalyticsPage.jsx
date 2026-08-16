import { useEffect, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceDot,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";
import { api } from "../api/client.js";
import { useAuth } from "../App.jsx";

const TABS = ["Learning Velocity", "Fatigue Analysis", "Question Difficulty"];
const GRID = "#262c37";
const TICK = "#8b93a3";
const TOOLTIP_STYLE = { background: "#1c212b", border: "1px solid #262c37", borderRadius: 10 };
const TOOLTIP_LABEL = { color: "#f2f4f8" };

function seconds(ms) {
  if (ms == null) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function ErrorState({ error }) {
  return (
    <div className="state-card">
      <div className="state-icon danger">!</div>
      <h3>Couldn't load this view</h3>
      <p>{error}</p>
    </div>
  );
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

/* ---------- custom XAxis tick that highlights the current user's name ---------- */
function NameTick({ x, y, payload, meName }) {
  const isMe = payload.value === meName;
  return (
    <text
      x={x} y={y} dy={10}
      textAnchor="end"
      transform={`rotate(-55, ${x}, ${y})`}
      fontSize={9}
      fontWeight={isMe ? 700 : 400}
      fill={isMe ? "#e8b04b" : TICK}
    >
      {payload.value}
    </text>
  );
}

function LearningVelocityTab() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [flashRow, setFlashRow] = useState(false);
  const rowRef = useRef(null);

  useEffect(() => { api.learningVelocity().then(setData).catch((e) => setError(e.message)); }, []);
  if (error) return <ErrorState error={error} />;
  if (!data) return <div className="skeleton-chart" />;

  const results = data.results;
  const chartData = results.map((r, i) => ({ name: r.user_name, LVI: r.learning_velocity_index, rank: i + 1, isMe: r.user_id === user.id }));
  const currentIndex = results.findIndex((r) => r.user_id === user.id);
  const currentEntry = currentIndex >= 0 ? results[currentIndex] : null;
  const cohortSize = results.length;
  const rank = currentIndex >= 0 ? currentIndex + 1 : null;
  const avgLvi = cohortSize ? Math.round((results.reduce((s, r) => s + r.learning_velocity_index, 0) / cohortSize) * 10) / 10 : null;
  const percentile = rank && cohortSize > 1 ? Math.round(((cohortSize - rank) / (cohortSize - 1)) * 100) : null;
  const delta = currentEntry ? Math.round((currentEntry.learning_velocity_index - avgLvi) * 10) / 10 : null;

  const jumpToMe = () => {
    rowRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setFlashRow(true);
    setTimeout(() => setFlashRow(false), 1500);
  };

  return <div>
    {currentEntry && (
      <div className="standing-card">
        <div>
          <div className="standing-label">Your standing</div>
          <div className="standing-stats">
            <div className="standing-stat">
              <div className="stat-label">Rank</div>
              <div className="stat-value">#{rank} <span style={{ fontSize: 13, color: "var(--ink-muted)", fontFamily: "var(--font-sans)" }}>of {cohortSize}</span></div>
            </div>
            <div className="standing-stat">
              <div className="stat-label">Your LVI</div>
              <div className="stat-value">{currentEntry.learning_velocity_index}</div>
            </div>
            <div className="standing-stat">
              <div className="stat-label">Vs. cohort avg ({avgLvi})</div>
              <div className={`stat-value ${delta > 0 ? "positive" : delta < 0 ? "negative" : ""}`}>{delta > 0 ? "+" : ""}{delta}</div>
            </div>
            {percentile != null && (
              <div className="standing-stat">
                <div className="stat-label">Ahead of</div>
                <div className="stat-value">{percentile}%</div>
              </div>
            )}
          </div>
        </div>
        <button className="btn secondary" onClick={jumpToMe}>Jump to my row ↓</button>
      </div>
    )}

    <div className="explain"><strong>Learning Velocity Index.</strong> Accuracy contributes {data.weights.accuracy * 100}%, relative speed {data.weights.speed * 100}%, and response-time consistency {data.weights.consistency * 100}%. The ranking is cohort-wide; low-sample rows are marked rather than hidden.</div>

    <div className="card chart-card compact">
      <div className="chart-scroll"><div className="chart-min-width" style={{ minWidth: Math.max(720, chartData.length * 34) }}>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
            <XAxis dataKey="name" interval={0} height={75} tick={(props) => <NameTick {...props} meName={user.name} />} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: TICK }} />
            <Tooltip
              formatter={(v, n, p) => [`${v} (rank #${p.payload.rank})`, "LVI"]}
              contentStyle={TOOLTIP_STYLE}
              labelStyle={TOOLTIP_LABEL}
            />
            {avgLvi != null && (
              <ReferenceLine y={avgLvi} stroke="#8b93a3" strokeDasharray="4 4" label={{ value: `Cohort avg ${avgLvi}`, position: "insideTopRight", fill: TICK, fontSize: 10 }} />
            )}
            <Bar dataKey="LVI" radius={[3, 3, 0, 0]} barSize={14}>
              {chartData.map((d, i) => <Cell key={i} fill={d.isMe ? "#e8b04b" : "#8b6fe0"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div></div>
      <div className="small-note" style={{ marginTop: 8 }}>Your bar is highlighted in amber; the dashed line marks the cohort average.</div>
    </div>

    <div className="card table-wrap">
      <table>
        <thead><tr><th>#</th><th>Learner</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Consistency</th><th>LVI</th></tr></thead>
        <tbody>{results.map((r, i) => {
          const isMe = r.user_id === user.id;
          return (
            <tr
              key={r.user_id}
              ref={isMe ? rowRef : null}
              className={`row-jump-target ${r.low_sample ? "low-sample " : ""}${isMe ? "current-user" : ""}${isMe && flashRow ? " row-flash" : ""}`}
            >
              <td className="rank">{i + 1}</td><td><strong>{r.user_name}</strong>{isMe && <span className="badge" style={{ marginLeft: 7 }}>you</span>}</td>
              <td>{r.total_attempts}</td><td>{r.accuracy_pct}%</td><td>{seconds(r.avg_response_time_ms)}</td>
              <td>{r.consistency_score == null ? "—" : r.consistency_score}{r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}</td>
              <td><strong>{r.learning_velocity_index}</strong></td>
            </tr>
          );
        })}</tbody>
      </table>
    </div>
  </div>;
}

function FatigueTab() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);
  const [onlyMine, setOnlyMine] = useState(true);

  useEffect(() => {
    api.fatigue().then((d) => {
      setData(d);
      const mine = d.results.find((r) => r.user_id === user.id);
      if (mine) setSelectedSession(mine.session_id);
      else if (d.results.length) setSelectedSession(d.results[0].session_id);
    }).catch((e) => setError(e.message));
  }, []);

  const visibleResults = data ? (onlyMine ? data.results.filter((r) => r.user_id === user.id) : data.results) : [];

  useEffect(() => {
    if (!visibleResults.length) return;
    if (!visibleResults.some((r) => r.session_id === selectedSession)) {
      setSelectedSession(visibleResults[0].session_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyMine, data]);

  if (error) return <ErrorState error={error} />;
  if (!data) return <div className="skeleton-chart" />;

  const session = visibleResults.find((s) => s.session_id === selectedSession);
  const chartData = session ? session.windows.map((w) => ({ window: `Q${w.question_range}`, Accuracy: w.accuracy_pct, "Avg response": Number((w.avg_response_time_ms / 1000).toFixed(2)) })) : [];
  const hasOwnSessions = data.results.some((r) => r.user_id === user.id);

  const flaggedWindows = session ? session.windows.filter((w) => w.fatigue_flag) : [];
  const worstAccDrop = session && session.windows.length ? Math.min(...session.windows.map((w) => w.accuracy_delta_pct)) : null;
  const worstTimeIncrease = session && session.windows.length ? Math.max(...session.windows.map((w) => w.response_time_delta_pct)) : null;

  return <div>
    <div className="explain"><strong>Fatigue Analysis.</strong> The assignment's example uses five-question windows. Each window is compared with the first window; the flag requires both a meaningful accuracy drop and a response-time increase. This is a descriptive heuristic, not a clinical or causal measure.</div>

    <div className="filter-row">
      <label className={`toggle-chip${onlyMine ? " active" : ""}`}>
        <input type="checkbox" checked={onlyMine} disabled={!hasOwnSessions} onChange={(e) => setOnlyMine(e.target.checked)} />
        Only my sessions
      </label>
      {!hasOwnSessions && <span className="small-note">You don't have any completed sessions yet.</span>}
    </div>

    <div className="session-picker">
      {visibleResults.map((s) => {
        const isMe = s.user_id === user.id;
        const isSelected = s.session_id === selectedSession;
        return (
          <button
            key={s.session_id}
            type="button"
            className={`session-card${isSelected ? " selected" : ""}`}
            onClick={() => setSelectedSession(s.session_id)}
          >
            <div className="session-user">{s.user_name}{isMe && <span className="badge">you</span>}</div>
            <div className="session-id">#{s.session_id.slice(-6)}</div>
            <div className="session-flags">
              {s.overall_fatigue_flag
                ? <span className="badge flag">fatigue signal</span>
                : <span className="badge success">clear</span>}
            </div>
          </button>
        );
      })}
    </div>

    {session ? <>
      <div className="card session-summary">
        <div>
          <div className="stat-label">Status</div>
          <div className={`stat-value ${session.overall_fatigue_flag ? "flag" : "clear"}`}>
            {session.overall_fatigue_flag ? "Fatigue signal" : "No signal"}
          </div>
        </div>
        <div>
          <div className="stat-label">Windows</div>
          <div className="stat-value">{session.windows.length}</div>
        </div>
        <div>
          <div className="stat-label">Windows flagged</div>
          <div className="stat-value">{flaggedWindows.length}</div>
        </div>
        <div>
          <div className="stat-label">Worst accuracy drop</div>
          <div className="stat-value">{worstAccDrop != null ? `${worstAccDrop} pp` : "—"}</div>
        </div>
        <div>
          <div className="stat-label">Worst time increase</div>
          <div className="stat-value">{worstTimeIncrease != null ? `+${worstTimeIncrease}%` : "—"}</div>
        </div>
      </div>

      <div className="card chart-card compact">
        <ResponsiveContainer width="100%" height={290}>
          <LineChart data={chartData} margin={{ top: 8, right: 18, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
            <XAxis dataKey="window" tick={{ fontSize: 11, fill: TICK }} />
            <YAxis yAxisId="accuracy" domain={[0, 100]} tick={{ fontSize: 11, fill: TICK }} unit="%" />
            <YAxis yAxisId="time" orientation="right" tick={{ fontSize: 11, fill: TICK }} unit="s" />
            <Tooltip formatter={(v, n) => [n === "Avg response" ? `${v} s` : `${v}%`, n]} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL} />
            <Legend wrapperStyle={{ fontSize: 11, color: TICK }} />
            <Line yAxisId="accuracy" type="monotone" dataKey="Accuracy" stroke="#4ade80" strokeWidth={2} />
            <Line yAxisId="time" type="monotone" dataKey="Avg response" stroke="#e8b04b" strokeWidth={2} />
            {flaggedWindows.map((w) => (
              <ReferenceDot key={w.window_index} yAxisId="accuracy" x={`Q${w.question_range}`} y={w.accuracy_pct} r={7} stroke="#e2954a" strokeWidth={2} fill="transparent" />
            ))}
          </LineChart>
        </ResponsiveContainer>
        {flaggedWindows.length > 0 && <div className="small-note" style={{ marginTop: 8 }}>Amber rings mark windows that triggered the fatigue flag.</div>}
      </div>

      <div className="card table-wrap">
        <table>
          <thead><tr><th>Window</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Δ accuracy</th><th>Δ time</th><th>Signal</th></tr></thead>
          <tbody>
            {session.windows.map((w) => (
              <tr key={w.window_index} className={w.fatigue_flag ? "flagged-row" : ""}>
                <td>Q{w.question_range}</td>
                <td>{w.attempts}</td>
                <td>{w.accuracy_pct}%</td>
                <td>{seconds(w.avg_response_time_ms)}</td>
                <td>{w.accuracy_delta_pct > 0 ? "+" : ""}{w.accuracy_delta_pct} pp</td>
                <td>{w.response_time_delta_pct > 0 ? "+" : ""}{w.response_time_delta_pct}%</td>
                <td>{w.fatigue_flag ? <span className="badge flag">fatigue</span> : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </> : <div className="state-card"><h3>No session data</h3><p>{onlyMine ? "You don't have a completed session matching this filter." : "No completed quiz attempts are available for cohort fatigue analysis."}</p></div>}
  </div>;
}

function DifficultyTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.questionDifficulty().then(setData).catch((e) => setError(e.message)); }, []);
  console.log(data)
  if (error) return <ErrorState error={error} />;
  if (!data) return <div className="skeleton-chart" />;

  const chartData = data.results.slice(0, 50).map((r,index) => ({ name: "Q-"+String(index + 1).padStart(2, '0'), Difficulty: r.difficulty_score }));
  return <div>
    <div className="explain"><strong>Question Difficulty Index.</strong> Difficulty combines {data.weights.inverted_accuracy * 100}% inverted accuracy with {data.weights.relative_time * 100}% relative response time. Higher means harder. Response time is normalized within the question's chapter so naturally slower chapters do not bias the entire ranking.</div>
    <div className="card chart-card compact">
      <div className="chart-scroll"><div className="chart-min-width" style={{ minWidth: Math.max(900, chartData.length * 24) }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
            <XAxis dataKey="name" interval={0} angle={-55} textAnchor="end" height={75} tick={{ fontSize: 9, fill: TICK }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: TICK }} />
            <Tooltip formatter={(v) => [v, "Difficulty"]} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL} />
            <Bar dataKey="Difficulty" fill="#8b6fe0" radius={[3, 3, 0, 0]} barSize={9} />
          </BarChart>
        </ResponsiveContainer>
      </div></div>
    </div>
    <div className="card table-wrap"><table><thead><tr><th>Q-No</th><th>Question</th><th>Attempts</th><th>Accuracy</th><th>Avg response</th><th>Difficulty</th></tr></thead>
      <tbody>{data.results.slice(0, 50).map((r, i) => <tr key={r.question_id} className={r.low_sample ? "low-sample" : ""}><td className="rank">{"Q-"+String(i + 1).padStart(2, '0')}</td><td style={{ minWidth: 320 }}>{r.question_text}</td><td>{r.total_attempts}</td><td>{r.accuracy_pct}%</td><td>{seconds(r.avg_response_time_ms)}</td><td><strong>{r.difficulty_score}</strong>{r.low_sample && <span className="badge" style={{ marginLeft: 6 }}>low sample</span>}</td></tr>)}</tbody>
    </table></div>
  </div>;
}