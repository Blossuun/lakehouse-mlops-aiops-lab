from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    # Guard against naive datetime being interpreted as local time.
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("iso() requires timezone-aware datetime (UTC expected).")
    return (
        dt.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
