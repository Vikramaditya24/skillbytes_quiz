from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PyObjectId


class UserOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = ""
    name: str
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    user_id: str


class LoginResponse(BaseModel):
    """
    Dummy auth per assignment spec: no JWT, no password. Selecting a predefined
    user returns a session token that is just the user_id, echoed back by the
    frontend on subsequent requests (sent as a header). This is intentionally
    minimal - see README > Assumptions for why we did not build real auth.
    """

    user: UserOut
    session_token: str
