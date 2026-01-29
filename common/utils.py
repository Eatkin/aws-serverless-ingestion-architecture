import hashlib


def get_stable_hash(data: str) -> str:
    """Creates a deterministic string hash."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
