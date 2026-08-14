from bson import ObjectId
from bson.errors import InvalidId


def to_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise ValueError(f"'{value}' is not a valid id") from exc


def serialize(doc: dict) -> dict:
    """Mongo doc -> plain dict with `id` (str) instead of `_id` (ObjectId)."""
    if doc is None:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc
