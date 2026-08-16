"""
Raw MongoDB aggregation pipelines. Kept separate from app/services/analytics.py
(score formulas) for readability: this file answers "what does Mongo group and
compute", the service file answers "how do we turn those numbers into a score".

All three pipelines read only from `question_attempts` - the single canonical
event stream. Behavior: Never writes duplicates or derived data.
"""


def learning_velocity_pipeline(user_id: str | None = None) -> list[dict]:
    """
    Group by user_id.

    Per user:
      - attempt count
      - correct count
      - average response time
      - sum-of-squares of response time for population stddev

    Speed normalization is intentionally NOT performed here. The service layer
    receives all learner rows so average response times can be normalized
    against the same cohort-wide range.

    When user_id is given, filtering is applied AFTER the per-user grouping.
    This preserves the cohort-wide aggregation inputs while allowing callers
    to request a single learner's result.
    """
    stages: list[dict] = [
        {
            "$group": {
                "_id": "$user_id",
                "total_attempts": {"$sum": 1},
                "correct_attempts": {
                    "$sum": {
                        "$cond": ["$is_correct", 1, 0]
                    }
                },
                "avg_response_time_ms": {
                    "$avg": "$response_duration_ms"
                },
                "sum_response_time_sq": {
                    "$sum": {
                        "$multiply": [
                            "$response_duration_ms",
                            "$response_duration_ms",
                        ]
                    }
                },
            }
        }
    ]

    if user_id is not None:
        stages.append(
            {
                "$match": {
                    "_id": user_id,
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
    within each question's own chapter cohort (rationale:
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