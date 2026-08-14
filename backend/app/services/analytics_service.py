from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.aggregations import formulas, pipelines
from app.core.config import settings
from app.repositories.base import to_object_id
from app.schemas.analytics import (
    DifficultyEntry,
    DifficultyResponse,
    FatigueResponse,
    FatigueSessionEntry,
    FatigueWindow,
    LearningVelocityEntry,
    LearningVelocityResponse,
)


class AnalyticsService:
    """
    Reads only from `question_attempts` (+ light lookups to users/questions for
    display names). Never writes. All grouping/math done in Mongo aggregation;
    Python only composes the final scores on the already-small grouped result
    set, per the "do not fake analytics in Python" instruction.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def learning_velocity(self) -> LearningVelocityResponse:
        rows = await self.db.question_attempts.aggregate(
            pipelines.learning_velocity_pipeline()
        ).to_list(length=None)

        if not rows:
            return LearningVelocityResponse(weights=self._lvi_weights(), results=[])

        user_ids = [to_object_id(r["_id"]) for r in rows]
        users = {
            str(u["_id"]): u["name"]
            async for u in self.db.users.find({"_id": {"$in": user_ids}})
        }

        entries: list[LearningVelocityEntry] = []
        for r in rows:
            acc = formulas.accuracy_pct(r["correct_attempts"], r["total_attempts"])
            speed = formulas.speed_score(
                r["avg_response_time_ms"], r["min_response_time_ms"], r["max_response_time_ms"]
            )
            consistency, low_sample = formulas.consistency_score(
                r["avg_response_time_ms"], r.get("std_response_time_ms") or 0.0, r["total_attempts"]
            )
            lvi = formulas.learning_velocity_index(acc, speed, consistency)
            entries.append(
                LearningVelocityEntry(
                    user_id=r["_id"],
                    user_name=users.get(r["_id"], "Unknown"),
                    total_attempts=r["total_attempts"],
                    accuracy_pct=acc,
                    avg_response_time_ms=round(r["avg_response_time_ms"], 2),
                    consistency_score=consistency,
                    speed_score=speed,
                    accuracy_score=acc,
                    learning_velocity_index=lvi,
                    low_sample=low_sample,
                )
            )
        entries.sort(key=lambda e: e.learning_velocity_index, reverse=True)
        return LearningVelocityResponse(weights=self._lvi_weights(), results=entries)

    async def fatigue_analysis(self) -> FatigueResponse:
        window_size = settings.fatigue_window_size
        rows = await self.db.question_attempts.aggregate(
            pipelines.fatigue_pipeline(window_size)
        ).to_list(length=None)

        by_session: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_session[r["_id"]["session_id"]].append(r)

        session_ids = [to_object_id(sid) for sid in by_session]
        sessions = {
            str(s["_id"]): s
            async for s in self.db.quiz_sessions.find({"_id": {"$in": session_ids}})
        }
        user_ids = list({s["user_id"] for s in sessions.values()})
        user_oids = [to_object_id(uid) for uid in user_ids]
        users = {
            str(u["_id"]): u["name"]
            async for u in self.db.users.find({"_id": {"$in": user_oids}})
        }

        results: list[FatigueSessionEntry] = []
        for session_id, windows_raw in by_session.items():
            windows_raw = sorted(windows_raw, key=lambda w: w["_id"]["window_index"])
            baseline = windows_raw[0]
            baseline_acc = formulas.accuracy_pct(
                baseline["correct_attempts"], baseline["attempts"]
            )
            baseline_time = baseline["avg_response_time_ms"]

            windows: list[FatigueWindow] = []
            any_flag = False
            for w in windows_raw:
                idx = int(w["_id"]["window_index"])
                acc = formulas.accuracy_pct(w["correct_attempts"], w["attempts"])
                avg_time = round(w["avg_response_time_ms"], 2)
                acc_delta, time_delta = formulas.fatigue_deltas(
                    baseline_acc, baseline_time, acc, avg_time
                )
                flagged = idx > 0 and formulas.fatigue_flag(acc_delta, time_delta)
                any_flag = any_flag or flagged
                start = idx * window_size + 1
                end = start + window_size - 1
                windows.append(
                    FatigueWindow(
                        window_index=idx,
                        question_range=f"{start}-{end}",
                        attempts=w["attempts"],
                        accuracy_pct=acc,
                        avg_response_time_ms=avg_time,
                        accuracy_delta_pct=acc_delta,
                        response_time_delta_pct=time_delta,
                        fatigue_flag=flagged,
                    )
                )

            session_doc = sessions.get(session_id, {})
            user_id = session_doc.get("user_id", "")
            results.append(
                FatigueSessionEntry(
                    session_id=session_id,
                    user_id=user_id,
                    user_name=users.get(user_id, "Unknown"),
                    windows=windows,
                    overall_fatigue_flag=any_flag,
                )
            )

        results.sort(key=lambda e: e.session_id)
        return FatigueResponse(
            window_size=window_size,
            disclaimer=(
                "This is a descriptive heuristic (accuracy drop + response-time "
                "increase vs. this session's first window) - it does not "
                "scientifically diagnose fatigue."
            ),
            results=results,
        )

    async def question_difficulty(self) -> DifficultyResponse:
        rows = await self.db.question_attempts.aggregate(
            pipelines.question_difficulty_pipeline()
        ).to_list(length=None)

        if not rows:
            return DifficultyResponse(weights=self._difficulty_weights(), results=[])

        # Normalize response time within each question's own chapter cohort
        # (Milestone 0 Section E rationale, preserved after removing z-scoring).
        by_chapter: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_chapter[r["chapter_id"]].append(r)

        question_ids = [to_object_id(r["_id"]) for r in rows]
        questions = {
            str(q["_id"]): q["text"]
            async for q in self.db.questions.find({"_id": {"$in": question_ids}})
        }

        entries: list[DifficultyEntry] = []
        for chapter_id, chapter_rows in by_chapter.items():
            times = [r["avg_response_time_ms"] for r in chapter_rows]
            min_t, max_t = min(times), max(times)
            for r in chapter_rows:
                acc = formulas.accuracy_pct(r["correct_attempts"], r["total_attempts"])
                time_score = formulas.relative_time_difficulty(
                    r["avg_response_time_ms"], min_t, max_t
                )
                score = formulas.difficulty_score(acc, time_score)
                entries.append(
                    DifficultyEntry(
                        question_id=r["_id"],
                        question_text=questions.get(r["_id"], "Unknown"),
                        chapter_id=chapter_id,
                        total_attempts=r["total_attempts"],
                        accuracy_pct=acc,
                        avg_response_time_ms=round(r["avg_response_time_ms"], 2),
                        difficulty_score=score,
                        low_sample=r["total_attempts"] < settings.low_sample_threshold,
                    )
                )

        entries.sort(key=lambda e: e.difficulty_score, reverse=True)
        return DifficultyResponse(weights=self._difficulty_weights(), results=entries)

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
