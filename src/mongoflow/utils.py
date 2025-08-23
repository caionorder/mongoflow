"""Utility functions for MongoFlow."""

from datetime import datetime
from typing import Any, Dict, List, Union

from bson import ObjectId


def convert_object_id(id: Union[str, ObjectId]) -> ObjectId:
    """
    Convert string to ObjectId if needed.

    Args:
        id: String or ObjectId

    Returns:
        ObjectId instance
    """
    if isinstance(id, str):
        return ObjectId(id)
    return id


def serialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize MongoDB document for JSON compatibility.

    Args:
        document: MongoDB document

    Returns:
        Serialized document
    """
    if document is None:
        return None

    # Convert ObjectId to string
    if "_id" in document and isinstance(document["_id"], ObjectId):
        document["_id"] = str(document["_id"])

    # Convert datetime objects
    for key, value in document.items():
        if isinstance(value, datetime):
            document[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            document[key] = str(value)
        elif isinstance(value, dict):
            document[key] = serialize_document(value)
        elif isinstance(value, list):
            document[key] = [
                serialize_document(item) if isinstance(item, dict) else item
                for item in value
            ]

    return document


def deserialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize document from JSON format.

    Args:
        document: Serialized document

    Returns:
        MongoDB-ready document
    """
    if document is None:
        return None

    # Convert string ID to ObjectId
    if "_id" in document and isinstance(document["_id"], str):
        document["_id"] = ObjectId(document["_id"])

    return document


def convert_ids(documents: Union[Dict, List[Dict]]) -> Union[Dict, List[Dict]]:
    """
    Convert _id fields from ObjectId to string.

    Args:
        documents: Single document or list of documents

    Returns:
        Documents with string IDs
    """
    if isinstance(documents, list):
        return [serialize_document(doc) for doc in documents]
    elif isinstance(documents, dict):
        return serialize_document(documents)
    return documents
