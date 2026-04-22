from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple


def normalize_partial_date(
    raw_value: Optional[str],
    *,
    is_end: bool,
) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Поддерживает:
    - YYYY
    - MM.YYYY
    - DD.MM.YYYY

    Правила:
    - для начала диапазона:
      YYYY -> 01.01.YYYY 00:00:00
      MM.YYYY -> 01.MM.YYYY 00:00:00
    - для конца диапазона:
      YYYY -> 28.12.YYYY 23:59:59
      MM.YYYY -> 28.MM.YYYY 23:59:59
      DD.MM.YYYY -> DD.MM.YYYY 23:59:59
    """
    if raw_value is None:
        return None, None

    value = raw_value.strip()
    if not value:
        return None, None

    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        day, month, year = map(int, value.split("."))
        if is_end:
            return value, datetime(year, month, day, 23, 59, 59)
        return value, datetime(year, month, day, 0, 0, 0)

    if re.fullmatch(r"\d{2}\.\d{4}", value):
        month, year = map(int, value.split("."))
        day = 28 if is_end else 1
        hour, minute, second = (23, 59, 59) if is_end else (0, 0, 0)
        return value, datetime(year, month, day, hour, minute, second)

    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        month = 12 if is_end else 1
        day = 28 if is_end else 1
        hour, minute, second = (23, 59, 59) if is_end else (0, 0, 0)
        return value, datetime(year, month, day, hour, minute, second)

    return value, None