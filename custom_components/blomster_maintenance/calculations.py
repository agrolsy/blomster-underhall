from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class MeterSample:
    value: float
    recorded_at: datetime


def accumulated_meter_total(samples: Iterable[MeterSample]) -> float:
    """Sum a resettable meter without counting a reset as negative usage."""
    ordered = sorted(samples, key=lambda sample: sample.recorded_at)
    if not ordered:
        raise ValueError("At least one sample is required")
    total = max(0.0, ordered[0].value)
    previous = ordered[0].value
    for sample in ordered[1:]:
        if sample.value < 0:
            continue
        total += sample.value - previous if sample.value >= previous else sample.value
        previous = sample.value
    return total


def history_is_complete(
    samples: Iterable[MeterSample],
    installation_date: datetime,
    now: datetime,
    tolerance: timedelta = timedelta(hours=6),
) -> bool:
    """Require coverage from installation until recently before trusting import."""
    ordered = sorted(samples, key=lambda sample: sample.recorded_at)
    return bool(
        len(ordered) >= 2
        and ordered[0].recorded_at <= installation_date + tolerance
        and ordered[-1].recorded_at >= now - tolerance
    )
