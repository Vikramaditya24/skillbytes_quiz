import { Routes, Route, Navigate, Link, useLocation, useNavigate } from "react-router-dom";
import { createContext, useContext, useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import MyProgressPage from "./pages/MyProgressPage.jsx";
import ExamsPage from "./pages/ExamsPage.jsx";
import SubjectsPage from "./pages/SubjectsPage.jsx";
import ChaptersPage from "./pages/ChaptersPage.jsx";
import QuizPage from "./pages/QuizPage.jsx";
import ResultPage from "./pages/ResultPage.jsx";
import CohortAnalyticsPage from "./pages/CohortAnalyticsPage.jsx";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function useStoredUser() {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("sb_user");
    return raw ? JSON.parse(raw) : null;
  });
  const login = (u) => { localStorage.setItem("sb_user", JSON.stringify(u)); setUser(u); };
  const logout = () => { localStorage.removeItem("sb_user"); setUser(null); };
  return { user, login, logout };
}

function RequireAuth({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}

function TopBar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  if (!user) return null;

  const isProgress = location.pathname === "/progress";
  const isQuizFlow = /^\/(exams|subjects|quiz|result)/.test(location.pathname);
  const isCohort = location.pathname === "/cohort";

  return (
    <header className="topbar">
      <Link to="/progress" className="brand">
        <span className="brand-mark">S</span>
        <span>Skillbytes Quiz</span>
      </Link>
      <nav>
        <Link to="/progress" className={isProgress ? "active" : ""}>My Progress</Link>
        <Link to="/exams" className={isQuizFlow ? "active" : ""}>Take a Quiz</Link>
        <Link to="/cohort" className={isCohort ? "active" : ""}>Cohort Analytics</Link>
        <a
          href="/logout"
          className="user-link"
          onClick={(e) => { e.preventDefault(); logout(); navigate("/login"); }}
        >
          {user.name} · Logout
        </a>
      </nav>
    </header>
  );
}

export default function App() {
  const auth = useStoredUser();
  return (
    <AuthContext.Provider value={auth}>
      <TopBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/progress" element={<RequireAuth><MyProgressPage /></RequireAuth>} />
        <Route path="/exams" element={<RequireAuth><ExamsPage /></RequireAuth>} />
        <Route path="/exams/:examId/subjects" element={<RequireAuth><SubjectsPage /></RequireAuth>} />
        <Route path="/subjects/:subjectId/chapters" element={<RequireAuth><ChaptersPage /></RequireAuth>} />
        <Route path="/quiz/:sessionId" element={<RequireAuth><QuizPage /></RequireAuth>} />
        <Route path="/result/:sessionId" element={<RequireAuth><ResultPage /></RequireAuth>} />
        <Route path="/cohort" element={<RequireAuth><CohortAnalyticsPage /></RequireAuth>} />
        <Route path="*" element={<Navigate to={auth.user ? "/progress" : "/login"} replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}
