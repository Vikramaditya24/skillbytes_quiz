"""
Transparent, explainable analytics formulas (per engineering-review correction:
winsorization/z-scoring was removed as unnecessary complexity for this
assignment). Every function here is pure (no I/O) and isolated from Mongo/FastAPI
so it can be unit-tested directly against known inputs/expected outputs.
"""

from app.core.config import settings


def accuracy_pct(correct: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(100 * correct / total, 2)


def speed_score(value_ms: float, min_ms: float, max_ms: float) -> float:
    """
    Relative score based on the observed response-time range: fastest observed
    time -> 100, slowest observed time -> 0, linear in between. Faster = higher
    score, which is what "speed" should mean.

    Edge case: min == max (every attempt took the same time, or n==1) - range
    is zero, so relative position is undefined. We return a neutral 50 rather
    than dividing by zero or arbitrarily picking 0/100.
    """
    if max_ms == min_ms:
        return 50.0
    ratio = (max_ms - value_ms) / (max_ms - min_ms)
    return round(100 * max(0.0, min(1.0, ratio)), 2)


def consistency_score(mean_ms: float, std_ms: float, sample_size: int) -> tuple[float | None, bool]:
    """
    100 / (1 + coefficient_of_variation). Lower variance relative to the mean
    -> higher score. Returns (score, low_sample_flag).

    Edge cases handled:
    - n < 2: stddev of a single point is not a meaningful measure of spread.
      Returns (None, True) rather than fabricating a number - the dashboard
      renders "insufficient data" for these instead of a misleading value.
    - mean == 0: CV is undefined (division by zero); same treatment.
    - n >= 2 but n < LOW_SAMPLE_THRESHOLD: score is computed (it IS meaningful
      with 2+ points) but still flagged low_sample=True, since 2-4 points is
      weak evidence for a confident consistency claim.
    """
    if sample_size < 2 or mean_ms == 0:
        return None, True
    cv = std_ms / mean_ms
    score = round(100 / (1 + cv), 2)
    return score, sample_size < settings.low_sample_threshold


def learning_velocity_index(accuracy: float, speed: float, consistency: float | None) -> float:
    """
    LVI = 50% accuracy + 30% speed + 20% consistency.
    When consistency is None (low sample), it is treated as neutral (50) for
    the composite score only - the entry is still flagged low_sample in the
    API response so the frontend can visually distinguish it from actual low consistency.
    """
    consistency_for_score = consistency if consistency is not None else 50.0
    lvi = (
        settings.lvi_accuracy_weight * accuracy
        + settings.lvi_speed_weight * speed
        + settings.lvi_consistency_weight * consistency_for_score
    )
    return round(lvi, 2)


def difficulty_score(accuracy: float, time_score_within_chapter: float) -> float:
    """
    difficulty = 70% inverted accuracy + 30% relative time difficulty.
    Inverted accuracy: harder questions have LOWER accuracy, so (100 - accuracy).
    time_score_within_chapter should already be "higher = took relatively
    longer within its own chapter cohort" (see analytics_service.py), NOT the
    speed_score above (which is inverted the other way - faster=higher).
    """
    inverted_accuracy = 100 - accuracy
    return round(
        settings.difficulty_accuracy_weight * inverted_accuracy
        + settings.difficulty_time_weight * time_score_within_chapter,
        2,
    )


def relative_time_difficulty(value_ms: float, min_ms: float, max_ms: float) -> float:
    """
    Mirror image of speed_score: SLOWEST observed time (within cohort) -> 100
    (hardest), fastest -> 0. Same zero-range edge case handling.
    """
    if max_ms == min_ms:
        return 50.0
    ratio = (value_ms - min_ms) / (max_ms - min_ms)
    return round(100 * max(0.0, min(1.0, ratio)), 2)


def fatigue_deltas(
    baseline_accuracy_pct: float, baseline_avg_time_ms: float, accuracy: float, avg_time_ms: float
) -> tuple[float, float]:
    """
    accuracy_delta_pct: percentage-point change vs the session's first window.
    response_time_delta_pct: relative % change vs the session's first window.
    Baseline avg_time of 0 is treated as 0% change (degenerate case, avoids
    division by zero without fabricating a spike).
    """
    accuracy_delta = round(accuracy - baseline_accuracy_pct, 2)
    if baseline_avg_time_ms == 0:
        time_delta_pct = 0.0
    else:
        time_delta_pct = round(100 * (avg_time_ms - baseline_avg_time_ms) / baseline_avg_time_ms, 2)
    return accuracy_delta, time_delta_pct


def fatigue_flag(accuracy_delta_pct: float, response_time_delta_pct: float) -> bool:
    """
    Flags fatigue only when BOTH accuracy drops AND response time rises beyond
    the configured thresholds vs. the session's baseline window. This is an
    explicit descriptive heuristic, not a scientific/causal detector - the API
    response and README both say so (per engineering-review instruction #7).
    """
    accuracy_dropped = accuracy_delta_pct <= -(settings.fatigue_accuracy_drop_threshold * 100)
    time_increased = response_time_delta_pct >= (settings.fatigue_time_increase_threshold * 100)
    return accuracy_dropped and time_increased
