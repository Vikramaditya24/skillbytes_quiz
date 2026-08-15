"""
Pure unit tests against known inputs/expected outputs - no DB, no FastAPI.
Covers the edge cases called out in Milestone 0 / engineering review:
low-sample consistency, equal-response-time speed/difficulty scoring.
"""

from app.aggregations import formulas


class TestAccuracy:
    def test_basic(self):
        assert formulas.accuracy_pct(7, 10) == 70.0

    def test_zero_total(self):
        assert formulas.accuracy_pct(0, 0) == 0.0

    def test_perfect(self):
        assert formulas.accuracy_pct(5, 5) == 100.0


class TestSpeedScore:
    def test_fastest_gets_100(self):
        assert formulas.speed_score(1000, 1000, 5000) == 100.0

    def test_slowest_gets_0(self):
        assert formulas.speed_score(5000, 1000, 5000) == 0.0

    def test_midpoint_gets_50(self):
        assert formulas.speed_score(3000, 1000, 5000) == 50.0

    def test_equal_min_max_returns_neutral(self):
        # Edge case: every attempt took the same time (or n==1) - no
        # meaningful relative position, so we return a neutral 50, not 0/100.
        assert formulas.speed_score(3000, 3000, 3000) == 50.0


class TestConsistencyScore:
    def test_single_sample_is_none_and_flagged(self):
        score, low_sample = formulas.consistency_score(mean_ms=3000, std_ms=0, sample_size=1)
        assert score is None
        assert low_sample is True

    def test_zero_mean_is_none_and_flagged(self):
        score, low_sample = formulas.consistency_score(mean_ms=0, std_ms=0, sample_size=3)
        assert score is None
        assert low_sample is True

    def test_zero_variance_gives_max_score(self):
        # CV = 0 -> consistency = 100/(1+0) = 100
        score, low_sample = formulas.consistency_score(mean_ms=3000, std_ms=0, sample_size=10)
        assert score == 100.0
        assert low_sample is False

    def test_below_threshold_sample_is_flagged_but_scored(self):
        score, low_sample = formulas.consistency_score(mean_ms=3000, std_ms=600, sample_size=3)
        assert score is not None
        assert low_sample is True  # n=3 < LOW_SAMPLE_THRESHOLD default (5)

    def test_higher_variance_gives_lower_score(self):
        low_var_score, _ = formulas.consistency_score(3000, 300, 10)
        high_var_score, _ = formulas.consistency_score(3000, 1500, 10)
        assert low_var_score > high_var_score


class TestLearningVelocityIndex:
    def test_weights_sum_and_combine_correctly(self):
        lvi = formulas.learning_velocity_index(accuracy=80, speed=60, consistency=90)
        expected = 0.5 * 80 + 0.3 * 60 + 0.2 * 90
        assert lvi == round(expected, 2)

    def test_none_consistency_uses_neutral_default(self):
        lvi = formulas.learning_velocity_index(accuracy=80, speed=60, consistency=None)
        expected = 0.5 * 80 + 0.3 * 60 + 0.2 * 50
        assert lvi == round(expected, 2)

    def test_higher_accuracy_outranks_higher_speed_at_default_weights(self):
        # Accuracy weight (0.5) dominates speed (0.3): a big accuracy edge
        # should win even against a big speed disadvantage.
        high_acc_avg_speed = formulas.learning_velocity_index(95, 80, 80)
        avg_acc_high_speed = formulas.learning_velocity_index(70, 100, 80)
        assert high_acc_avg_speed > avg_acc_high_speed


class TestDifficultyScore:
    def test_low_accuracy_and_long_time_is_hardest(self):
        hard = formulas.difficulty_score(accuracy=20, time_score_within_chapter=90)
        easy = formulas.difficulty_score(accuracy=95, time_score_within_chapter=10)
        assert hard > easy

    def test_not_pure_inverted_accuracy(self):
        # Two questions at the same accuracy but different relative time
        # must NOT get equal difficulty scores (guards against "1 - accuracy").
        a = formulas.difficulty_score(accuracy=60, time_score_within_chapter=10)
        b = formulas.difficulty_score(accuracy=60, time_score_within_chapter=90)
        assert a != b


class TestRelativeTimeDifficulty:
    def test_slowest_is_hardest(self):
        assert formulas.relative_time_difficulty(5000, 1000, 5000) == 100.0

    def test_fastest_is_easiest(self):
        assert formulas.relative_time_difficulty(1000, 1000, 5000) == 0.0

    def test_equal_min_max_returns_neutral(self):
        assert formulas.relative_time_difficulty(2000, 2000, 2000) == 50.0


class TestFatigueDeltasAndFlag:
    def test_no_change_no_flag(self):
        acc_delta, time_delta = formulas.fatigue_deltas(80, 3000, 80, 3000)
        assert acc_delta == 0.0
        assert time_delta == 0.0
        assert formulas.fatigue_flag(acc_delta, time_delta) is False

    def test_accuracy_drop_and_time_rise_flags(self):
        acc_delta, time_delta = formulas.fatigue_deltas(80, 3000, 60, 3600)
        assert acc_delta == -20.0
        assert time_delta == 20.0
        assert formulas.fatigue_flag(acc_delta, time_delta) is True

    def test_only_accuracy_drop_does_not_flag(self):
        # Requires BOTH signals per Milestone 0 - accuracy drop alone (e.g.
        # harder questions later) shouldn't be mislabeled as fatigue.
        acc_delta, time_delta = formulas.fatigue_deltas(80, 3000, 60, 2900)
        assert formulas.fatigue_flag(acc_delta, time_delta) is False

    def test_only_time_rise_does_not_flag(self):
        acc_delta, time_delta = formulas.fatigue_deltas(80, 3000, 82, 3600)
        assert formulas.fatigue_flag(acc_delta, time_delta) is False

    def test_zero_baseline_time_treated_as_no_change(self):
        _, time_delta = formulas.fatigue_deltas(80, 0, 60, 3000)
        assert time_delta == 0.0
