"""Lab 1D tests for the manual's heuristic-v1 scoring implementation.

Place this file at tests/test_score.py.
Run from the repository root: python -m pytest tests/test_score.py -v

These tests verify the project's chosen rules, not ecological accuracy.
They do not verify a future LLM integration or runtime authorization.
"""

import pytest
from pydantic import ValidationError

from rut.score import Signals, score


OPTIONAL_FIELDS = {
    "front_passed_24h",
    "temp_vs_normal_f",
    "wind_mph",
    "precip_prob",
    "crash_index",
}


def checked_score(signals):
    """Check version and bounds for every successful score used below."""
    result = score(signals)
    assert result["score_version"] == "heuristic-v1"
    assert 0 <= result["hunt_score"] <= 100
    return result


# Item 1: Required scoring scenarios and invalid inputs.
def test_peak_without_optional_data():
    result = checked_score(Signals(phase="peak"))
    assert result["hunt_score"] == 40
    assert result["why"] == ["phase:peak=40"]
    assert set(result["missing"]) == OPTIONAL_FIELDS


def test_second_rut_with_moderate_wind():
    result = checked_score(Signals(phase="second_rut", wind_mph=8))
    assert result["hunt_score"] == 45  # 35 base + 10 wind bonus.
    assert "moderate-wind:+10" in result["why"]
    assert set(result["missing"]) == OPTIONAL_FIELDS - {"wind_mph"}


@pytest.mark.parametrize(
    "precip_prob,expected_score,penalty_expected",
    [
        (49.9, 40, False),
        (50, 30, True),
        (90, 30, True),
    ],
)
def test_rain_penalty_threshold(precip_prob, expected_score, penalty_expected):
    result = checked_score(Signals(phase="peak", precip_prob=precip_prob))
    assert result["hunt_score"] == expected_score
    assert ("rain-probability>=50%:-10" in result["why"]) == penalty_expected


def test_negative_wind_is_rejected():
    with pytest.raises(ValidationError) as error:
        Signals(phase="peak", wind_mph=-1)
    assert any(item["loc"] == ("wind_mph",) for item in error.value.errors())


@pytest.mark.parametrize(
    "field",
    ["temp_vs_normal_f", "wind_mph", "precip_prob", "crash_index"],
)
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
def test_nonfinite_numeric_values_are_rejected(field, value):
    with pytest.raises(ValidationError) as error:
        Signals(phase="peak", **{field: value})
    assert any(item["loc"] == (field,) for item in error.value.errors())


def test_unknown_phase_is_rejected_by_score():
    # In the manual, the scoring function validates phase membership.
    signals = Signals(phase="not_a_real_phase")
    with pytest.raises(ValueError, match="unknown phase"):
        score(signals)


# Item 2: Missing means None, not a silently invented False or zero.
def test_omitted_values_remain_none():
    signals = Signals(phase="peak")
    before = signals.model_dump()
    result = checked_score(signals)
    for field in OPTIONAL_FIELDS:
        assert getattr(signals, field) is None
    assert set(result["missing"]) == OPTIONAL_FIELDS
    assert signals.model_dump() == before


def test_explicit_none_values_remain_missing():
    signals = Signals(
        phase="peak", **{field: None for field in OPTIONAL_FIELDS}
    )
    result = checked_score(signals)
    assert set(result["missing"]) == OPTIONAL_FIELDS
    assert result["hunt_score"] == 40


def test_observed_false_and_zero_are_not_missing():
    signals = Signals(
        phase="peak",
        front_passed_24h=False,
        temp_vs_normal_f=0,
        wind_mph=0,
        precip_prob=0,
        crash_index=0,
    )
    result = checked_score(signals)
    assert signals.front_passed_24h is False
    assert result["missing"] == []
    assert result["hunt_score"] == 40
    # Same score as missing inputs, but different evidence and explanation.
    assert "animal-crash-proxy:+0" in result["why"]
    assert "post-front:+15" not in result["why"]


# Item 3: Every supported phase returns the expected score version.
@pytest.mark.parametrize(
    "phase",
    ["peak", "second_rut", "pre_rut", "post_rut", "late_tail", "outside"],
)
def test_score_version_for_each_supported_phase(phase):
    result = checked_score(Signals(phase=phase))
    assert result["score_version"] == "heuristic-v1"


# Item 4: Lock down the project-defined crash scaling.
# The rain threshold is covered above. These are assumptions, not science.
@pytest.mark.parametrize(
    "crash_index,bonus",
    [(0, 0), (1, 0), (1.5, 5), (2, 10), (3, 10)],
)
def test_crash_bonus_scaling(crash_index, bonus):
    result = checked_score(Signals(phase="peak", crash_index=crash_index))
    assert result["hunt_score"] == 40 + bonus
    assert f"animal-crash-proxy:+{bonus}" in result["why"]


# Item 5: A local deterministic calculation, not an LLM calculation.
# This test does NOT prove that a future LLM integration respects the score.
def test_same_input_produces_same_score_and_explanation():
    signals = Signals(
        phase="peak",
        front_passed_24h=True,
        temp_vs_normal_f=-6,
        wind_mph=8,
        precip_prob=0,
        crash_index=1.5,
    )
    before = signals.model_dump()
    first = checked_score(signals)
    second = checked_score(signals)
    assert first == second
    assert first["hunt_score"] == 80  # 40 + 15 + 10 + 10 + 5.
    assert first["missing"] == []
    assert signals.model_dump() == before


def test_score_cannot_fall_below_zero():
    result = checked_score(
        Signals(phase="outside", wind_mph=25, precip_prob=80)
    )
    assert result["hunt_score"] == 0
