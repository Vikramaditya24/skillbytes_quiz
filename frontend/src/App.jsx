import { Routes, Route, Navigate, Link, useLocation, useNavigate } from "react-router-dom";
import { createContext, useContext, useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import ExamsPage from "./pages/ExamsPage.jsx";
import SubjectsPage from "./pages/SubjectsPage.jsx";
import ChaptersPage from "./pages/ChaptersPage.jsx";
import QuizPage from "./pages/QuizPage.jsx";
import ResultPage from "./pages/ResultPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function useStoredUser() {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("sb_user");
    return raw ? JSON.parse(raw) : null;
  });
  const login = (u) => {
    localStorage.setItem("sb_user", JSON.stringify(u));
    setUser(u);
  };
  const logout = () => {
    localStorage.removeItem("sb_user");
    setUser(null);
  };
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
  return (
    <div className="topbar">
      <div className="brand">Skillbytes Quiz</div>
      <nav>
        <Link to="/exams" className={location.pathname.startsWith("/exams") ? "active" : ""}>
          Exams
        </Link>
        <Link to="/dashboard" className={location.pathname === "/dashboard" ? "active" : ""}>
          Analytics
        </Link>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            logout();
            navigate("/login");
          }}
        >
          {user.name} · Logout
        </a>
      </nav>
    </div>
  );
}

export default function App() {
  const auth = useStoredUser();
  return (
    <AuthContext.Provider value={auth}>
      <TopBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/exams"
          element={
            <RequireAuth>
              <ExamsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/exams/:examId/subjects"
          element={
            <RequireAuth>
              <SubjectsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/subjects/:subjectId/chapters"
          element={
            <RequireAuth>
              <ChaptersPage />
            </RequireAuth>
          }
        />
        <Route
          path="/quiz/:sessionId"
          element={
            <RequireAuth>
              <QuizPage />
            </RequireAuth>
          }
        />
        <Route
          path="/result/:sessionId"
          element={
            <RequireAuth>
              <ResultPage />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to={auth.user ? "/exams" : "/login"} replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}
