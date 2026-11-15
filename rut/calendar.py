from datetime import date

PEAK = date(2026, 11, 16)
PHASES = [
    ("pre_rut", -21, -8),
    ("peak", -7, 7),
    ("post_rut", 8, 21),
    ("second_rut", 22, 34),
    ("late_tail", 35, 45),
]

def phase_for(day: date) -> tuple[str, int]:
    offset = (day - PEAK).days
    for name, first, last in PHASES:
        if first <= offset <= last:
            return name, offset
    return "outside", offset