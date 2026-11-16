"""FABLE-FIX-S81-COLTAP 11-16: clock.core_tap_lead_ps = the declared in-type run of a type's early core taps.  The spine delivers
the tap that much earlier and tap_balance pads the core pin back to the type target (col: 200 = the F2r numbers 215.39 / 184.57 /
53.17 instead of 15.39 / 0 / 0, which left the element halves at 520 / 542 ps against 450)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as G  # noqa: E402
import schema as S  # noqa: E402


def _plan():
    P = S.Plan.__new__(S.Plan)
    P.clock = {"insertion_ps": 250.0}
    return P


OV = {"clock": {"insertion_ps": 450, "insertion_ff_ps": 364.5, "insertion_target_override": {"reason": "x"}}}
LEAD = {"clock": dict(OV["clock"], core_tap_lead_ps=200)}


def test_absent_key_is_todays_price():
    P = _plan()
    assert S.core_tap_lead_ps(OV) == 0.0 == S.core_tap_lead_ps(None, "FF") == S.core_tap_lead_ps({"clock": None})
    assert S.core_tap_early_ps(P, dict(insertion_ps=465.39, insertion_ff_ps=361.26), "TT", OV) == pytest.approx(15.39)
    assert S.core_tap_early_ps(P, dict(insertion_ps=434.57), "TT", OV) == 0.0


def test_col_lead_200_gives_the_f2r_early_at_both_corners():
    P = _plan()
    for ins, tt in ((465.39, 215.39), (434.57, 184.57), (303.17, 53.17)):
        tp = dict(insertion_ps=ins)
        assert S.core_tap_early_ps(P, tp, "TT", LEAD) == pytest.approx(tt)
        # FF: the lead scales like the chain it is (0.81 x 200 = 162 = 364.5 - 202.5), so FF equals the die-basis price too
        die_ff = max(0.0, S.core_tap_insertion_ps(tp, "FF") - S.common_latency_ps(P, "FF"))
        assert S.core_tap_early_ps(P, tp, "FF", LEAD) == pytest.approx(die_ff)
    assert S.core_tap_lead_ps(LEAD, "FF") == pytest.approx(162.0)
    with pytest.raises(ValueError):
        S.core_tap_lead_ps(LEAD, "SS")


def test_plain_type_takes_the_lead_too():
    P = _plan()
    plain = {"clock": {"insertion_ps": 250, "core_tap_lead_ps": 60}}
    assert S.core_tap_early_ps(P, dict(insertion_ps=430.0), "TT", plain) == pytest.approx(240.0)
    assert S.core_tap_early_ps(P, dict(insertion_ps=150.0), "TT", plain) == 0.0     # 150 - 250 + 60 < 0: never negative


def test_rebound_tap_carries_the_lead_and_keeps_the_clamp():
    P = _plan()
    assert G.view_core_tap_values(P, dict(insertion_ps=465.39), 533.0, "TT", OV) == (pytest.approx(83.0), 533.0)
    assert G.view_core_tap_values(P, dict(insertion_ps=465.39), 533.0, "TT", LEAD) == (pytest.approx(283.0), 533.0)
    e, ins = G.view_core_tap_values(P, dict(insertion_ps=465.39), 900.0, "TT", LEAD)      # at most the common latency early
    assert (e, ins) == (450.0, 900.0)
    # a view with no tree arc keeps the plan values, lead included
    assert G.view_core_tap_values(P, dict(insertion_ps=465.39), 0.0, "TT", LEAD)[0] == pytest.approx(215.39)


def test_schema_key():
    ck = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["core_tap_lead_ps"] == {"type": "number", "minimum": 0, "maximum": 450}
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk == json.loads(json.dumps(S.SCHEMA))
