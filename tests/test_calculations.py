from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

SPEC = spec_from_file_location(
    "blomster_calculations",
    Path(__file__).parents[1] / "custom_components/blomster_maintenance/calculations.py",
)
assert SPEC and SPEC.loader
calculations = module_from_spec(SPEC)
sys.modules[SPEC.name] = calculations
SPEC.loader.exec_module(calculations)
MeterSample = calculations.MeterSample


def sample(value: float, hour: int) -> MeterSample:
    return MeterSample(value, datetime(2026, 7, 6, hour, tzinfo=timezone.utc))


def test_accumulated_meter_without_reset() -> None:
    assert calculations.accumulated_meter_total([sample(2, 0), sample(5, 1), sample(9, 2)]) == 9


def test_accumulated_meter_with_daily_reset() -> None:
    assert calculations.accumulated_meter_total([sample(4, 0), sample(10, 1), sample(1, 2), sample(3, 3)]) == 13


def test_samples_are_sorted_and_negative_values_ignored() -> None:
    assert calculations.accumulated_meter_total([sample(8, 2), sample(-1, 1), sample(3, 0)]) == 8


def test_complete_history_requires_both_ends_of_period() -> None:
    installation = datetime(2026, 7, 6, tzinfo=timezone.utc)
    now = installation + timedelta(days=1)
    complete = [MeterSample(0, installation), MeterSample(5, now - timedelta(hours=1))]
    missing_start = [MeterSample(2, installation + timedelta(hours=8)), MeterSample(5, now)]
    stale_end = [MeterSample(0, installation), MeterSample(5, now - timedelta(hours=8))]
    assert calculations.history_is_complete(complete, installation, now)
    assert not calculations.history_is_complete(missing_start, installation, now)
    assert not calculations.history_is_complete(stale_end, installation, now)
