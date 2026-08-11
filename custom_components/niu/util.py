"""Shared helpers for parsing values returned by the Niu cloud API."""
from __future__ import annotations

from datetime import datetime

from homeassistant.util import dt as dt_util


def as_float(value) -> float | None:
    """Best-effort conversion of a Niu API value to a float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value) -> int | None:
    """Best-effort conversion of a Niu API value to an int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def epoch_ms_to_datetime(value) -> datetime | None:
    """Convert a Niu API millisecond epoch timestamp to an aware datetime."""
    ms = as_float(value)
    if not ms:
        return None
    return dt_util.utc_from_timestamp(ms / 1000)


def is_truthy_flag(value) -> bool:
    """Interpret one of Niu's 0/1 (int or string) flag fields as a bool."""
    return value in (1, "1", True)
