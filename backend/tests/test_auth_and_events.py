from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio

REQUIRED_EVENT_FIELDS = {
    "session_id", "user_id", "question_id", "exam_id", "subject_id", "chapter_id",
    "question_sequence_number", "shown_at", "answered_at", "response_duration_ms",
    "selected_option_key", "is_correct",
}


class TestDummyAuth:
    async def test_login_with_valid_user_id_succeeds(self, client, db):
        user = await db.users.insert_one(
            {"name": "Aditya", "email": "a@x.com", "created_at": datetime.now(timezone.utc)}
        )
        resp = await client.post("/auth/login", json={"user_id": str(user.inserted_id)})
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["name"] == "Aditya"
        # dummy auth: session_token is just the user id, no JWT
        assert body["session_token"] == str(user.inserted_id)

    async def test_login_with_unknown_user_id_returns_404(self, client):
        resp = await client.post("/auth/login", json={"user_id": "000000000000000000000000"})
        assert resp.status_code == 404

    async def test_list_users_populates_login_picker(self, client, db):
        await db.users.insert_many(
            [
                {"name": "A", "email": "a@x.com", "created_at": datetime.now(timezone.utc)},
                {"name": "B", "email": "b@x.com", "created_at": datetime.now(timezone.utc)},
            ]
        )
        resp = await client.get("/auth/users")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestEventShape:
    """
    Confirms every question_attempt document written by the quiz flow contains
    all 10 fields named in the spec's Event Tracking section (quiz_id is
    represented by session_id - see README > Assumptions for the naming note).
    """

    async def test_attempt_document_has_all_required_fields(self, db):
        from tests.test_quiz_progression import OWNER, seed_minimal_catalog, seed_session
        from app.services.quiz_service import QuizService

        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "A")

        attempt = await db.question_attempts.find_one({"session_id": session_id})
        assert REQUIRED_EVENT_FIELDS.issubset(attempt.keys())
        assert attempt["response_duration_ms"] >= 0


class TestNoArchetypeLeak:
    """
    Seed data tags users with an internal `_archetype` field for generating
    deterministic behavior (see scripts/seed.py). It must never appear in any
    API response - it's a display-identity leak, and defeats the point of
    giving seed users realistic names.
    """

    async def test_user_out_schema_has_no_archetype_field(self, client, db):
        await db.users.insert_one(
            {
                "name": "Test User",
                "email": "t@x.com",
                "created_at": datetime.now(timezone.utc),
                "_archetype": "high_accuracy_fast",
            }
        )
        resp = await client.get("/auth/users")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert "_archetype" not in body[0]
        assert "archetype" not in body[0]

    async def test_login_response_has_no_archetype_field(self, client, db):
        user = await db.users.insert_one(
            {
                "name": "Test User",
                "email": "t2@x.com",
                "created_at": datetime.now(timezone.utc),
                "_archetype": "declining",
            }
        )
        resp = await client.post("/auth/login", json={"user_id": str(user.inserted_id)})
        assert resp.status_code == 200
        body = resp.json()
        assert "_archetype" not in body["user"]
        assert "archetype" not in body["user"]
