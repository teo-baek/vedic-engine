"""Statelessness guard — this service must never grow storage or identity.

The whole reason this code lives in its own repository is that PyJHora is AGPL-licensed.
That separation only holds if the service stays a pure function: birth data in, astronomy
out. The moment it stores a user, it stops being a calculator and starts being the product.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import BIRTHS_BY_KEY
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent

#: Source files that make up the service (tests excluded — they may import what they like).
SERVICE_FILES = sorted(
    [
        ROOT / "main.py",
        ROOT / "constants.py",
        ROOT / "schemas.py",
        *(ROOT / "wrappers").glob("*.py"),
    ]
)

#: Anything that would imply persistence or a database connection.
FORBIDDEN_IMPORTS = (
    "sqlalchemy", "asyncpg", "psycopg", "sqlite3", "pymongo", "redis",
    "alembic", "boto3", "google.cloud.storage", "firebase",
)

#: Anything that would imply the engine knows *who* it is calculating for.
FORBIDDEN_IDENTIFIERS = ("user_id", "profile_id", "account_id", "session_id", "email")


def _service_source() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in SERVICE_FILES}


def test_no_database_or_storage_imports() -> None:
    for path, source in _service_source().items():
        for module in FORBIDDEN_IMPORTS:
            pattern = rf"^\s*(import|from)\s+{re.escape(module)}\b"
            assert not re.search(pattern, source, re.MULTILINE), f"{path.name} imports {module}"


def test_no_user_identifiers() -> None:
    for path, source in _service_source().items():
        for identifier in FORBIDDEN_IDENTIFIERS:
            assert identifier not in source, f"{path.name} mentions {identifier}"


def test_no_file_writes() -> None:
    """No open(..., 'w'), no Path.write_*, no pickling to disk."""
    writers = (r"open\([^)]*['\"][wax]", r"\.write_text\(", r"\.write_bytes\(", r"pickle\.dump")
    for path, source in _service_source().items():
        for pattern in writers:
            assert not re.search(pattern, source), f"{path.name} writes to disk ({pattern})"


def test_no_outbound_network_calls() -> None:
    """PyJHora pulls in geocoding libraries; this service must never actually call out."""
    for path, source in _service_source().items():
        for module in ("requests", "httpx", "geocoder", "geopy", "urllib.request"):
            pattern = rf"^\s*(import|from)\s+{re.escape(module)}\b"
            assert not re.search(pattern, source, re.MULTILINE), f"{path.name} imports {module}"


def test_repeated_identical_requests_return_identical_results(client: TestClient) -> None:
    """No accumulation, no drift, no warm-up effects between calls."""
    birth = BIRTHS_BY_KEY["seoul_1990"].body()
    first = client.post("/v1/chart", json=birth).json()
    for _ in range(3):
        assert client.post("/v1/chart", json=birth).json() == first


def test_requests_do_not_leak_into_each_other(client: TestClient) -> None:
    """PyJHora keeps ayanamsa in process-wide state; interleaved calls must not disturb it."""
    seoul = BIRTHS_BY_KEY["seoul_1990"].body()
    sydney = BIRTHS_BY_KEY["sydney_2001"].body()

    seoul_alone = client.post("/v1/chart", json=seoul).json()
    sydney_alone = client.post("/v1/chart", json=sydney).json()

    for _ in range(2):
        client.post("/v1/strength", json=sydney)
        client.post("/v1/yoga", json=seoul)
        assert client.post("/v1/chart", json=seoul).json() == seoul_alone
        assert client.post("/v1/chart", json=sydney).json() == sydney_alone
