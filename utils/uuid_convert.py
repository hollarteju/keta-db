import uuid

def str_to_uuid(value: str) -> uuid.UUID:
    """Convert DB string value to UUID object."""
    return uuid.UUID(value) if value else None

def uuid_to_str(value: uuid.UUID) -> str:
    """Convert UUID object to string for DB insert."""
    return str(value) if value else None