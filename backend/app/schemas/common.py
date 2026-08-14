from datetime import datetime, timezone
from typing import Annotated, Any

from bson import ObjectId
from pydantic import BeforeValidator, ConfigDict

# Accepts a bson.ObjectId or a valid ObjectId-string on input; always serializes as str.
PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


class MongoBaseModel:
    """Mixin config for models read back from Mongo documents (which use `_id`)."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def oid_str() -> str:
    return str(ObjectId())
