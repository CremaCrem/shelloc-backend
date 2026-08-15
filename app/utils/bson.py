from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from typing import Any

def validate_object_id(id_str: str) -> ObjectId:
    """
    Validates a string to ensure it's a valid MongoDB ObjectId.
    Returns the ObjectId object if valid, raises HTTPException(400) if not.
    """
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ObjectId format: '{id_str}'"
        )

def serialize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """
    Helper to convert a MongoDB document's _id to a string id for Pydantic.
    """
    if not doc:
        return doc
    
    # Create a copy to avoid mutating the original dict
    serialized = dict(doc)
    
    if "_id" in serialized:
        serialized["id"] = str(serialized.pop("_id"))
        
    return serialized
