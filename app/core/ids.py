from uuid import uuid4


def generate_id(prefix: str, length: int = 10) -> str:
    return f"{prefix}_{uuid4().hex[:length]}"
