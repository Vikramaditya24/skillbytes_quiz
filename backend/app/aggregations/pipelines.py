"""
Raw MongoDB aggregation pipelines. Kept separate from app/services/analytics.py
(score formulas) for readability: this file answers "what does Mongo group and
compute", the service file answers "how do we turn those numbers into a score".

All three pipelines read only from `question_attempts` - the single canonical
event stream (per Milestone 0 Section C: "Never writes. No duplicated/derived
analytics collection").
"""


def learning_velocity_pipeline(user_id: str | None = None) -> list[dict]:
    """
    Group by user_id. Per user: attempt count, correct count, avg/std/min/max
    response time. Min/max/std computed in Mongo ($stdDevPop) rather than
    pulled into Python, per the "no application-side full-table pulls" rule.

    When `user_id` is given, a $match is prepended so the exact same pipeline
    powers both the cohort-wide ranking and a single learner's "My Progress"
    numbers - one formula, two scopes, no duplicated logic.
    """
    stages: list[dict] = []
    if user_id is not None:
        stages.append({"$match": {"user_id": user_id}})
    stages.append(
        {
            "$group": {
                "_id": "$user_id",
                "total_attempts": {"$sum": 1},
                "correct_attempts": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_response_time_ms": {"$avg": "$response_duration_ms"},
                "sum_response_time_sq": {
                    "$sum": {
                        "$multiply": [
                            "$response_duration_ms",
                            "$response_duration_ms",
                        ]
                    }
                },
                "min_response_time_ms": {"$min": "$response_duration_ms"},
                "max_response_time_ms": {"$max": "$response_duration_ms"},
            }
        }
    )
    return stages


def fatigue_pipeline(window_size: int, user_id: str | None = None) -> list[dict]:
    """
    Group by (session_id, window). Window index = floor((seq-1)/window_size).
    One document per session per window; the service layer reassembles windows
    into per-session series and computes deltas against each session's window 0.
    Same $match-prepend pattern as learning_velocity_pipeline for per-user scope.
    """
    stages: list[dict] = []
    if user_id is not None:
        stages.append({"$match": {"user_id": user_id}})
    stages += [
        {
            "$addFields": {
                "window_index": {
                    "$floor": {
                        "$divide": [{"$subtract": ["$question_sequence_number", 1]}, window_size]
                    }
                }
            }
        },
        {
            "$group": {
                "_id": {"session_id": "$session_id", "window_index": "$window_index"},
                "user_id": {"$first": "$user_id"},
                "attempts": {"$sum": 1},
                "correct_attempts": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_response_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
        {"$sort": {"_id.session_id": 1, "_id.window_index": 1}},
    ]
    return stages


def question_difficulty_pipeline() -> list[dict]:
    """
    Group by question_id, carrying chapter_id through (via $first, since it's
    constant per question) so the service layer can normalize response time
    within each question's own chapter cohort (Milestone 0 Section E rationale:
    a naturally slower chapter shouldn't make every question in it look hard).
    """
    return [
        {
            "$group": {
                "_id": "$question_id",
                "chapter_id": {"$first": "$chapter_id"},
                "total_attempts": {"$sum": 1},
                "correct_attempts": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_response_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
    ]


def fatigue_question_pipeline(user_id: str | None = None) -> list[dict]:
    """Return one aggregate row per question position within each session."""
    stages: list[dict] = []
    if user_id is not None:
        stages.append({"$match": {"user_id": user_id}})
    stages += [
        {
            "$group": {
                "_id": {"session_id": "$session_id", "question_number": "$question_sequence_number"},
                "attempts": {"$sum": 1},
                "correct_attempts": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_response_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
        {"$sort": {"_id.session_id": 1, "_id.question_number": 1}},
    ]
    return stages
