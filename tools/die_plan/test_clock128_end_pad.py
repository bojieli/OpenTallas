#!/usr/bin/env python3
"""DIE-QC-42: TrackRouter end_pad_um keeps shield ties planned on the ACTUAL segment ends, and the shield FAIL report
is JSON-safe.  QC R7BFR2: the adapter widened a0/a1 by the .056 VIA78 patch before router.place, so tie_ext measured
the shield ext from the padded ends and 88 drawn M8 shield stripes stopped 0.036 um short of their M9 VSS tie.
python3 -m pytest tools/die_plan/test_clock128_end_pad.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_128 as C  # noqa: E402

ND = dict(width=0.08, space=0.32)
TR = {"M8": dict(pitch_um=0.08, offset_um=0.04), "M9": dict(pitch_um=0.08, offset_um=0.04)}
PAD = 0.056
# one VSS M9 column, centre x 12.16 (QC 18092.16 pattern); the M8 track is free
PG = [("VSS", "M9", 11.824, 0.0, 12.496, 40.0)]
A0, A1 = 8.928, 10.60       # short driver jog; nearest VSS tie lies 1.56 um right of its end (needs ext > e0)


def _router(**kw):
    r = C.TrackRouter(ND, "VSS", TR, 8.64, **kw)
    r.reserve(C.pg_shapes(PG))
    return r


def _ties(c, e):
    st = C.shield_stripes([("M8", A0, c, A1, c, e)], ND)
    return C.shield_ties(st, PG, ND["width"]), st


def test_caller_side_widening_leaves_shield_short_of_its_tie():
    """the QC R7BFR2 bug class: widen outside place() -> ext measured from padded ends -> untied"""
    c, m, e = _router().place("M8", 20.0, A0 - PAD, A1 + PAD, "ck_a")
    assert m == C.DRAWN and e is not None
    assert _ties(c, e)[0]["untied"]


def test_end_pad_router_shield_reaches_its_tie():
    c, m, e = _router(end_pad_um={"M8": PAD}).place("M8", 20.0, A0, A1, "ck_a")
    assert m == C.DRAWN and e is not None
    assert not _ties(c, e)[0]["untied"]
    # the drawn shield footprint equals the reserved one (padded span + tie ext)
    c0, _, e0 = _router().place("M8", 20.0, A0 - PAD, A1 + PAD, "ck_a")
    assert c0 == c and abs(e - (e0 + PAD)) < 1e-9


def test_end_pad_only_on_named_layer_and_none_is_old_behaviour():
    a = _router().place("M9", 20.0, 3.0, 9.0, "ck_v")
    b = _router(end_pad_um={"M8": PAD}).place("M9", 20.0, 3.0, 9.0, "ck_v")
    assert a == b
    assert _router(end_pad_um=None).place("M8", 20.0, A0, A1, "ck_a") == _router().place("M8", 20.0, A0, A1, "ck_a")


def test_tie_failure_record_is_json_safe():
    c, _, e = _router().place("M8", 20.0, A0 - PAD, A1 + PAD, "ck_a")
    ties, st = _ties(c, e)
    assert isinstance(ties["used_grid"], set) and ties["untied"]
    back = json.loads(json.dumps(C.tie_failure_record(ties, st)))
    assert back["vss_tied"] is False and back["untied_stripes"] == len(ties["untied"]) == len(back["untied_detail"])
    assert back["untied_detail"][0][0] == "M8"
