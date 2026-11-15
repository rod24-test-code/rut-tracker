from pydantic import BaseModel, ConfigDict, Field

WEIGHTS = {
    "peak": 40, "second_rut": 35, "pre_rut": 30,
    "post_rut": 20, "late_tail": 15, "outside": 0,
}

class Signals(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    phase: str
    front_passed_24h: bool | None = None
    temp_vs_normal_f: float | None = None
    wind_mph: float | None = Field(default=None, ge=0, le=150)
    precip_prob: float | None = Field(default=None, ge=0, le=100)
    crash_index: float | None = Field(default=None, ge=0)

def score(signals: Signals) -> dict:
    if signals.phase not in WEIGHTS:
        raise ValueError("unknown phase")
    total = WEIGHTS[signals.phase]
    reasons = [f"phase:{signals.phase}={total}"]
    missing = []
    for field in (
        "front_passed_24h", "temp_vs_normal_f",
        "wind_mph", "precip_prob", "crash_index",
    ):
        if getattr(signals, field) is None:
            missing.append(field)
    if signals.front_passed_24h is True:
        total += 15
        reasons.append("post-front:+15")
    if signals.temp_vs_normal_f is not None and signals.temp_vs_normal_f <= -5:
        total += 10
        reasons.append("below-normal:+10")
    if signals.wind_mph is not None:
        if 3 <= signals.wind_mph <= 12:
            total += 10
            reasons.append("moderate-wind:+10")
        elif signals.wind_mph > 18:
            total -= 10
            reasons.append("strong-wind:-10")
    if signals.precip_prob is not None and signals.precip_prob >= 50:
        total -= 10
        reasons.append("rain-probability>=50%:-10")
    if signals.crash_index is not None:
        bonus = round(min(10, max(0, (signals.crash_index - 1) * 10)))
        total += bonus
        reasons.append(f"animal-crash-proxy:+{bonus}")
    return {
        "hunt_score": max(0, min(100, total)),
        "why": reasons,
        "missing": missing,
        "score_version": "heuristic-v1",
    }