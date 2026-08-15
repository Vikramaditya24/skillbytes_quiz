from collections import defaultdict
from math import sqrt

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.aggregations import formulas, pipelines
from app.core.config import settings
from app.repositories.base import to_object_id
from app.schemas.analytics import (
    DifficultyEntry,
    DifficultyResponse,
    FatigueResponse,
    FatigueSessionEntry,
    FatiguePoint,
    FatigueWindow,
    LearningVelocityEntry,
    LearningVelocityResponse,
    PersonalProgressResponse,
    RecentSessionSummary,
)


class AnalyticsService:
    """
    Reads analytics from `question_attempts` and performs light lookups for
    display metadata.

    MongoDB performs the grouping/aggregation. Python only derives the final
    metric components from the already-grouped result set and composes the
    response models.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def learning_velocity(
        self,
        user_id: str | None = None,
    ) -> LearningVelocityResponse:
        rows = await self.db.question_attempts.aggregate(
            pipelines.learning_velocity_pipeline(user_id=user_id)
        ).to_list(length=None)

        if not rows:
            return LearningVelocityResponse(
                weights=self._lvi_weights(),
                results=[],
            )

        # Real application users use ObjectId values. Some aggregation tests
        # use simple string IDs, so only attempt the optional name lookup for
        # IDs that can actually be converted to ObjectId.
        valid_user_ids = []

        for r in rows:
            try:
                valid_user_ids.append(to_object_id(r["_id"]))
            except ValueError:
                continue

        users = {}

        if valid_user_ids:
            users = {
                str(u["_id"]): u["name"]
                async for u in self.db.users.find(
                    {"_id": {"$in": valid_user_ids}}
                )
            }

        entries: list[LearningVelocityEntry] = []

        for r in rows:
            total_attempts = r["total_attempts"]
            mean_ms = r["avg_response_time_ms"]

            acc = formulas.accuracy_pct(
                r["correct_attempts"],
                total_attempts,
            )

            speed = formulas.speed_score(
                mean_ms,
                r["min_response_time_ms"],
                r["max_response_time_ms"],
            )

            # Mongo's $stdDevPop is not implemented by mongomock.
            # We therefore aggregate sum(x^2) in Mongo and derive the
            # population variance from:
            #
            # Var(X) = E[X^2] - E[X]^2
            if total_attempts:
                mean_square = (
                    r.get("sum_response_time_sq", 0.0) / total_attempts
                )
                variance = mean_square - (mean_ms * mean_ms)
            else:
                variance = 0.0

            std_ms = sqrt(max(0.0, variance))

            consistency, low_sample = formulas.consistency_score(
                mean_ms,
                std_ms,
                total_attempts,
            )

            lvi = formulas.learning_velocity_index(
                acc,
                speed,
                consistency,
            )

            entries.append(
                LearningVelocityEntry(
                    user_id=r["_id"],
                    user_name=users.get(r["_id"], "Unknown"),
                    total_attempts=total_attempts,
                    accuracy_pct=acc,
                    avg_response_time_ms=round(mean_ms, 2),
                    consistency_score=consistency,
                    speed_score=speed,
                    accuracy_score=acc,
                    learning_velocity_index=lvi,
                    low_sample=low_sample,
                )
            )

        entries.sort(
            key=lambda entry: entry.learning_velocity_index,
            reverse=True,
        )

        return LearningVelocityResponse(
            weights=self._lvi_weights(),
            results=entries,
        )

    async def fatigue_analysis(
        self,
        user_id: str | None = None,
    ) -> FatigueResponse:
        window_size = settings.fatigue_window_size

        rows = await self.db.question_attempts.aggregate(
            pipelines.fatigue_pipeline(
                window_size,
                user_id=user_id,
            )
        ).to_list(length=None)

        point_rows = await self.db.question_attempts.aggregate(
            pipelines.fatigue_question_pipeline(
                user_id=user_id,
            )
        ).to_list(length=None)

        # Aggregate results by quiz session.
        by_session: dict[str, list[dict]] = defaultdict(list)
        points_by_session: dict[str, list[dict]] = defaultdict(list)

        for r in rows:
            session_id = r["_id"]["session_id"]
            by_session[session_id].append(r)

        for r in point_rows:
            session_id = r["_id"]["session_id"]
            points_by_session[session_id].append(r)

        if not by_session:
            return FatigueResponse(
                window_size=window_size,
                disclaimer=(
                    "This is a descriptive heuristic (accuracy drop + "
                    "response-time increase vs. this session's first window) - "
                    "it does not scientifically diagnose fatigue."
                ),
                results=[],
            )

        # Real application sessions use ObjectId IDs. Test fixtures may use
        # simple string session IDs, so only query MongoDB for IDs that can be
        # converted to ObjectId.
        valid_session_ids = []

        for session_id in by_session:
            try:
                valid_session_ids.append(to_object_id(session_id))
            except ValueError:
                continue

        sessions = {}

        if valid_session_ids:
            sessions = {
                str(session["_id"]): session
                async for session in self.db.quiz_sessions.find(
                    {"_id": {"$in": valid_session_ids}}
                )
            }

        # The grouped fatigue rows may still carry the user_id from the
        # source attempts. Keep that as a fallback for synthetic/test sessions
        # that do not have a corresponding quiz_sessions document.
        session_user_ids: dict[str, str] = {}

        for r in rows:
            session_id = r["_id"]["session_id"]
            source_user_id = r.get("user_id")

            if source_user_id:
                session_user_ids[session_id] = str(source_user_id)

        # Resolve user IDs for display-name lookup.
        valid_user_ids = []

        for resolved_user_id in session_user_ids.values():
            try:
                valid_user_ids.append(to_object_id(resolved_user_id))
            except ValueError:
                continue

        # Also include users from the actual quiz_sessions documents.
        for session in sessions.values():
            session_user_id = session.get("user_id")

            if not session_user_id:
                continue

            try:
                valid_user_ids.append(to_object_id(str(session_user_id)))
            except ValueError:
                continue

        users = {}

        if valid_user_ids:
            users = {
                str(user["_id"]): user["name"]
                async for user in self.db.users.find(
                    {"_id": {"$in": valid_user_ids}}
                )
            }

        results: list[FatigueSessionEntry] = []

        # IMPORTANT:
        # session_id is defined by this loop before it is used. Every
        # session's windows, user resolution and question progression belong
        # inside this loop.
        for session_id, windows_raw in by_session.items():
            windows_raw = sorted(
                windows_raw,
                key=lambda window: window["_id"]["window_index"],
            )

            if not windows_raw:
                continue

            baseline = windows_raw[0]

            baseline_acc = formulas.accuracy_pct(
                baseline["correct_attempts"],
                baseline["attempts"],
            )

            baseline_time = baseline["avg_response_time_ms"]

            windows: list[FatigueWindow] = []
            any_flag = False

            for window in windows_raw:
                idx = int(window["_id"]["window_index"])

                acc = formulas.accuracy_pct(
                    window["correct_attempts"],
                    window["attempts"],
                )

                avg_time = round(
                    window["avg_response_time_ms"],
                    2,
                )

                acc_delta, time_delta = formulas.fatigue_deltas(
                    baseline_acc,
                    baseline_time,
                    acc,
                    avg_time,
                )

                flagged = (
                    idx > 0
                    and formulas.fatigue_flag(
                        acc_delta,
                        time_delta,
                    )
                )

                any_flag = any_flag or flagged

                start = idx * window_size + 1
                end = start + window_size - 1

                windows.append(
                    FatigueWindow(
                        window_index=idx,
                        question_range=f"{start}-{end}",
                        attempts=window["attempts"],
                        accuracy_pct=acc,
                        avg_response_time_ms=avg_time,
                        accuracy_delta_pct=acc_delta,
                        response_time_delta_pct=time_delta,
                        fatigue_flag=flagged,
                    )
                )

            # First try the real quiz-session record.
            session_doc = sessions.get(session_id, {})

            resolved_user_id = session_doc.get("user_id")

            # If this is a synthetic/test session with no quiz_sessions
            # document, fall back to the user_id carried by the attempts.
            if not resolved_user_id:
                resolved_user_id = session_user_ids.get(
                    session_id,
                    "",
                )

            resolved_user_id = str(resolved_user_id) if resolved_user_id else ""

            progression_rows = sorted(
                points_by_session.get(session_id, []),
                key=lambda row: row["_id"]["question_number"],
            )

            progression: list[FatiguePoint] = []

            for point in progression_rows:
                question_number = int(
                    point["_id"]["question_number"]
                )

                point_acc = formulas.accuracy_pct(
                    point["correct_attempts"],
                    point["attempts"],
                )

                point_time = round(
                    point["avg_response_time_ms"],
                    2,
                )

                acc_delta, time_delta = formulas.fatigue_deltas(
                    baseline_acc,
                    baseline_time,
                    point_acc,
                    point_time,
                )

                progression.append(
                    FatiguePoint(
                        question_number=question_number,
                        accuracy_pct=point_acc,
                        avg_response_time_ms=point_time,
                        accuracy_delta_pct=acc_delta,
                        response_time_delta_pct=time_delta,
                    )
                )

            results.append(
                FatigueSessionEntry(
                    session_id=session_id,
                    user_id=resolved_user_id,
                    user_name=users.get(
                        resolved_user_id,
                        "Unknown",
                    ),
                    windows=windows,
                    question_progression=progression,
                    overall_fatigue_flag=any_flag,
                )
            )

        results.sort(
            key=lambda entry: entry.session_id,
        )

        return FatigueResponse(
            window_size=window_size,
            disclaimer=(
                "This is a descriptive heuristic (accuracy drop + "
                "response-time increase vs. this session's first window) - "
                "it does not scientifically diagnose fatigue."
            ),
            results=results,
        )

    async def my_progress(
        self,
        user_id: str,
    ) -> PersonalProgressResponse:
        """
        Composite "My Progress" view.

        Personal LVI and fatigue are calculated using the same shared
        analytics pipelines as the cohort endpoints, but are filtered to
        the supplied user ID.
        """

        lvi_response = await self.learning_velocity(
            user_id=user_id,
        )

        my_lvi = (
            lvi_response.results[0]
            if lvi_response.results
            else None
        )

        fatigue_response = await self.fatigue_analysis(
            user_id=user_id,
        )

        # Most recent completed sessions belonging only to this user.
        recent_sessions_cursor = (
            self.db.quiz_sessions.find(
                {
                    "user_id": user_id,
                    "status": "completed",
                }
            )
            .sort("started_at", -1)
            .limit(5)
        )

        recent_sessions_raw = [
            session
            async for session in recent_sessions_cursor
        ]

        # Chapter IDs in the real application are ObjectIds. Skip malformed
        # IDs rather than making the entire personal dashboard fail.
        chapter_ids = []

        for session in recent_sessions_raw:
            chapter_id = session.get("chapter_id")

            if not chapter_id:
                continue

            try:
                chapter_ids.append(to_object_id(chapter_id))
            except ValueError:
                continue

        chapters = {}

        if chapter_ids:
            chapters = {
                str(chapter["_id"]): chapter["name"]
                async for chapter in self.db.chapters.find(
                    {"_id": {"$in": chapter_ids}}
                )
            }

        recent_sessions = [
            RecentSessionSummary(
                session_id=str(session["_id"]),
                chapter_name=chapters.get(
                    str(session["chapter_id"]),
                    "Unknown chapter",
                ),
                score=session["score"],
                total_questions=session["total_questions"],
                accuracy_pct=(
                    round(
                        100
                        * session["score"]
                        / session["total_questions"],
                        2,
                    )
                    if session["total_questions"]
                    else 0.0
                ),
                completed_at=session["completed_at"],
            )
            for session in recent_sessions_raw
        ]

        latest_fatigue = None

        if recent_sessions_raw:
            latest_session_id = str(
                recent_sessions_raw[0]["_id"]
            )

            latest_fatigue = next(
                (
                    fatigue
                    for fatigue in fatigue_response.results
                    if fatigue.session_id == latest_session_id
                ),
                None,
            )

        return PersonalProgressResponse(
            has_data=my_lvi is not None,
            learning_velocity=my_lvi,
            recent_sessions=recent_sessions,
            latest_session_fatigue=latest_fatigue,
        )

    async def question_difficulty(self) -> DifficultyResponse:
        rows = await self.db.question_attempts.aggregate(
            pipelines.question_difficulty_pipeline()
        ).to_list(length=None)

        if not rows:
            return DifficultyResponse(
                weights=self._difficulty_weights(),
                results=[],
            )

        # Normalize response time within each question's chapter cohort.
        by_chapter: dict[str, list[dict]] = defaultdict(list)

        for r in rows:
            by_chapter[r["chapter_id"]].append(r)

        # Question IDs can be ObjectIds in production but simple strings in
        # deterministic test fixtures.
        question_ids = []

        for r in rows:
            try:
                question_ids.append(to_object_id(r["_id"]))
            except ValueError:
                continue

        questions = {}

        if question_ids:
            questions = {
                str(question["_id"]): question["text"]
                async for question in self.db.questions.find(
                    {"_id": {"$in": question_ids}}
                )
            }

        entries: list[DifficultyEntry] = []

        for chapter_id, chapter_rows in by_chapter.items():
            times = [
                row["avg_response_time_ms"]
                for row in chapter_rows
            ]

            min_t = min(times)
            max_t = max(times)

            for r in chapter_rows:
                acc = formulas.accuracy_pct(
                    r["correct_attempts"],
                    r["total_attempts"],
                )

                time_score = formulas.relative_time_difficulty(
                    r["avg_response_time_ms"],
                    min_t,
                    max_t,
                )

                score = formulas.difficulty_score(
                    acc,
                    time_score,
                )

                entries.append(
                    DifficultyEntry(
                        question_id=r["_id"],
                        question_text=questions.get(
                            r["_id"],
                            "Unknown",
                        ),
                        chapter_id=chapter_id,
                        total_attempts=r["total_attempts"],
                        accuracy_pct=acc,
                        avg_response_time_ms=round(
                            r["avg_response_time_ms"],
                            2,
                        ),
                        difficulty_score=score,
                        low_sample=(
                            r["total_attempts"]
                            < settings.low_sample_threshold
                        ),
                    )
                )

        entries.sort(
            key=lambda entry: entry.difficulty_score,
            reverse=True,
        )

        return DifficultyResponse(
            weights=self._difficulty_weights(),
            results=entries,
        )

    @staticmethod
    def _lvi_weights() -> dict[str, float]:
        return {
            "accuracy": settings.lvi_accuracy_weight,
            "speed": settings.lvi_speed_weight,
            "consistency": settings.lvi_consistency_weight,
        }

    @staticmethod
    def _difficulty_weights() -> dict[str, float]:
        return {
            "inverted_accuracy": settings.difficulty_accuracy_weight,
            "relative_time": settings.difficulty_time_weight,
        }