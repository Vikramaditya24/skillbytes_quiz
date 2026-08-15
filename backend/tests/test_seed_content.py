"""
Two groups of tests here have different dependency requirements:

- TestQuestionBankContent: exercises scripts/question_bank.py directly. That
  module has zero external dependencies (stdlib `random` only), so these run
  under plain pytest with no motor/mongomock/DB needed.

- TestSeedScriptIdentitiesAndCounts: imports scripts/seed.py, which imports
  `motor` at module scope (to construct its own MongoClient) even though
  these particular tests only exercise its pure helper functions
  (build_user_identities, assign_archetypes) and module-level constants. That
  makes `motor` an import-time dependency for this test class even though no
  test in it touches a database. If motor is not installed, this whole class
  fails to collect - that's a real environment dependency, not a bug in the
  tests themselves.
"""

import random
from collections import Counter

import pytest

from scripts.question_bank import GENERATORS, generate_question

CHAPTER_LOCAL_INDICES = range(3)
QUESTIONS_PER_CHAPTER = 17  # matches the real seed script's per-chapter count

OLD_PLACEHOLDER_PATTERNS = [
    "which statement is correct",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
]


class TestQuestionBankContent:
    """No DB, no motor - pure content-generation correctness."""

    @pytest.mark.parametrize("subject", list(GENERATORS.keys()))
    def test_every_question_has_exactly_four_distinct_options(self, subject):
        rng = random.Random(42)
        for chapter_idx in CHAPTER_LOCAL_INDICES:
            for q_idx in range(QUESTIONS_PER_CHAPTER):
                q = generate_question(subject, chapter_idx, q_idx, rng)
                assert len(q["options"]) == 4
                assert [o["key"] for o in q["options"]] == ["A", "B", "C", "D"]
                assert len({o["text"] for o in q["options"]}) == 4, (
                    f"duplicate option text in {subject} ch{chapter_idx} q{q_idx}: {q['options']}"
                )

    @pytest.mark.parametrize("subject", list(GENERATORS.keys()))
    def test_every_question_has_exactly_one_correct_option(self, subject):
        rng = random.Random(42)
        for chapter_idx in CHAPTER_LOCAL_INDICES:
            for q_idx in range(QUESTIONS_PER_CHAPTER):
                q = generate_question(subject, chapter_idx, q_idx, rng)
                keys = [o["key"] for o in q["options"]]
                assert q["correct_option_key"] in keys
                # exactly one option key matches correct_option_key by construction
                # (keys are unique A/B/C/D), so this also confirms "exactly one".
                assert keys.count(q["correct_option_key"]) == 1

    @pytest.mark.parametrize("subject", list(GENERATORS.keys()))
    def test_no_duplicate_question_text_within_a_single_chapter(self, subject):
        rng = random.Random(42)
        for chapter_idx in CHAPTER_LOCAL_INDICES:
            texts = [
                generate_question(subject, chapter_idx, q_idx, rng)["text"]
                for q_idx in range(QUESTIONS_PER_CHAPTER)
            ]
            duplicates = [t for t, c in Counter(texts).items() if c > 1]
            assert not duplicates, f"{subject} chapter {chapter_idx} has repeated questions: {duplicates}"

    @pytest.mark.parametrize("subject", list(GENERATORS.keys()))
    def test_no_old_placeholder_text_remains(self, subject):
        rng = random.Random(42)
        for chapter_idx in CHAPTER_LOCAL_INDICES:
            for q_idx in range(QUESTIONS_PER_CHAPTER):
                q = generate_question(subject, chapter_idx, q_idx, rng)
                for pattern in OLD_PLACEHOLDER_PATTERNS:
                    assert pattern not in q["text"], f"placeholder text found: {q['text']}"
                for opt in q["options"]:
                    assert opt["text"] not in ("Option A", "Option B", "Option C", "Option D")

    def test_generation_is_deterministic_given_same_seed(self):
        rng1 = random.Random(123)
        rng2 = random.Random(123)
        for subject in GENERATORS:
            for chapter_idx in CHAPTER_LOCAL_INDICES:
                for q_idx in range(5):
                    q1 = generate_question(subject, chapter_idx, q_idx, rng1)
                    q2 = generate_question(subject, chapter_idx, q_idx, rng2)
                    assert q1 == q2

    def test_unknown_subject_raises(self):
        with pytest.raises(ValueError):
            generate_question("Nonexistent Subject", 0, 0, random.Random(1))


class TestSeedScriptIdentitiesAndCounts:
    """Requires `motor` importable (see module docstring)."""

    def test_module_level_counts_match_assignment_spec(self):
        seed = pytest.importorskip("scripts.seed")
        assert seed.N_USERS == 50
        assert seed.N_EXAMS == 3
        assert seed.N_SUBJECTS == 10
        assert seed.N_CHAPTERS == 30
        assert seed.N_QUESTIONS == 500
        assert sum(seed.SUBJECTS_PER_EXAM) == seed.N_SUBJECTS
        assert len(seed.SUBJECT_NAMES) == seed.N_SUBJECTS
        assert len(seed.EXAM_NAMES) == seed.N_EXAMS

    def test_identity_generation_is_deterministic(self):
        seed = pytest.importorskip("scripts.seed")
        ids1 = seed.build_user_identities(random.Random(seed.RNG_SEED), seed.N_USERS)
        ids2 = seed.build_user_identities(random.Random(seed.RNG_SEED), seed.N_USERS)
        assert ids1 == ids2

    def test_identities_are_realistic_not_placeholder_style(self):
        """Guards against regressions to 'Aarav User14'-style fixture names."""
        seed = pytest.importorskip("scripts.seed")
        identities = seed.build_user_identities(random.Random(seed.RNG_SEED), seed.N_USERS)
        assert len(identities) == seed.N_USERS
        for identity in identities:
            name = identity["name"]
            assert "User" not in name, f"placeholder-style name found: {name}"
            assert len(name.split(" ")) == 2, f"expected 'First Last' name, got: {name}"
            first, last = name.split(" ")
            assert first in seed.FIRST_NAMES
            assert last in seed.LAST_NAMES

    def test_all_emails_unique(self):
        seed = pytest.importorskip("scripts.seed")
        identities = seed.build_user_identities(random.Random(seed.RNG_SEED), seed.N_USERS)
        emails = [i["email"] for i in identities]
        assert len(set(emails)) == len(emails)

    def test_archetypes_cover_all_six_patterns_and_are_roughly_balanced(self):
        seed = pytest.importorskip("scripts.seed")
        archetypes = seed.assign_archetypes(seed.N_USERS)
        assert len(archetypes) == seed.N_USERS
        counts = Counter(archetypes)
        assert set(counts.keys()) == set(seed.ARCHETYPES)
        # roughly balanced: no archetype should dominate or be starved
        assert min(counts.values()) >= (seed.N_USERS // len(seed.ARCHETYPES)) - 1
        assert max(counts.values()) <= (seed.N_USERS // len(seed.ARCHETYPES)) + 1

    def test_archetype_assignment_independent_of_name_order(self):
        """
        Archetype assignment (index-based cycling) and identity assignment
        (shuffled name pools) are generated independently - confirms there's
        no way to infer a user's archetype from their name, which is the
        actual product requirement (archetype must never leak, including
        implicitly via a naming pattern).
        """
        seed = pytest.importorskip("scripts.seed")
        rng_a = random.Random(seed.RNG_SEED)
        identities_a = seed.build_user_identities(rng_a, seed.N_USERS)
        archetypes_a = seed.assign_archetypes(seed.N_USERS)

        # Re-running identity generation with a differently-seeded RNG changes
        # names but archetype assignment (pure index cycling) is unaffected -
        # demonstrating the two are decoupled.
        rng_b = random.Random(seed.RNG_SEED + 1)
        identities_b = seed.build_user_identities(rng_b, seed.N_USERS)
        archetypes_b = seed.assign_archetypes(seed.N_USERS)

        assert identities_a != identities_b  # names changed with a different name RNG
        assert archetypes_a == archetypes_b  # archetype cycling is unaffected
