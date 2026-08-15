from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration. All tunable constants referenced by the
    analytics/quiz logic live here (not scattered as magic numbers) so the
    README can point to one place for "where do I change X".
    """

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "skillbytes_quiz"

    # Public URLs used by deploy target(s)
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # Quiz behavior
    quiz_session_size: int = 15  # questions sampled per session (see README: Assumptions #3)

    # Analytics tunables
    fatigue_window_size: int = 5  # matches spec's "Questions 1-5 / 6-10 / 11-15" example
    low_sample_threshold: int = 5  # below this attempt count, results are flagged low_sample
    fatigue_accuracy_drop_threshold: float = 0.05  # 5 percentage points
    fatigue_time_increase_threshold: float = 0.10  # 10%

    # LVI weights (documented in README > Analytics Methodology)
    lvi_accuracy_weight: float = 0.5
    lvi_speed_weight: float = 0.3
    lvi_consistency_weight: float = 0.2

    # Difficulty weights
    difficulty_accuracy_weight: float = 0.7
    difficulty_time_weight: float = 0.3

    cors_origins: str = "http://localhost:5173"
    cors_origin_regex: str | None = None
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
