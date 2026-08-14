const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listUsers: () => request("/auth/users"),
  login: (userId) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ user_id: userId }) }),

  listExams: () => request("/exams"),
  listSubjects: (examId) => request(`/exams/${examId}/subjects`),
  listChapters: (subjectId) => request(`/subjects/${subjectId}/chapters`),

  startQuiz: (chapterId, userId) =>
    request(`/chapters/${chapterId}/quiz-sessions`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  currentQuestion: (sessionId) => request(`/quiz-sessions/${sessionId}/current-question`),
  submitAnswer: (sessionId, userId, questionId, selectedOptionKey) =>
    request(`/quiz-sessions/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        question_id: questionId,
        selected_option_key: selectedOptionKey,
      }),
    }),
  getResult: (sessionId) => request(`/quiz-sessions/${sessionId}/result`),

  learningVelocity: () => request("/analytics/learning-velocity"),
  fatigue: () => request("/analytics/fatigue"),
  questionDifficulty: () => request("/analytics/question-difficulty"),
};
