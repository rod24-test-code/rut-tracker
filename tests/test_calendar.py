from datetime import date, timedelta
import pytest
from rut.calendar import phase_for

@pytest.mark.parametrize("value,expected", [
    ("2026-10-25", "outside"),
    ("2026-10-26", "pre_rut"),
    ("2026-11-08", "pre_rut"),
    ("2026-11-09", "peak"),
    ("2026-11-23", "peak"),
    ("2026-11-24", "post_rut"),
    ("2026-12-07", "post_rut"),
    ("2026-12-08", "second_rut"),
    ("2026-12-14", "second_rut"),
    ("2026-12-20", "second_rut"),
    ("2026-12-21", "late_tail"),
    ("2026-12-31", "late_tail"),
    ("2027-01-01", "outside"),
])
def test_boundaries(value, expected):
    assert phase_for(date.fromisoformat(value))[0] == expected

def test_no_gaps_in_tracking_window():
    first = date(2026, 10, 26)
    last = date(2026, 12, 31)
    for offset in range((last - first).days + 1):
        assert phase_for(first + timedelta(days=offset))[0] != "outside"