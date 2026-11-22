"""VISUAL-NOBLOCK (FLOW-OPS-R2 11-22, COORD; owner rule "visual review never blocks"): a type row whose own AUTO-GEOM PASSED
routes at once even under a required review_before_route policy or the route visual gate; the verdict is advisory
(visual_pending).  Hard holds stay for an explicit BAD verdict, or when there is no AUTO-GEOM PASS (no render)."""
import pytest

import kit_wave as K

POLICY = {"event": "J", "items": ["t1"], "required": True}
CFG = {"dies": {"s81": {"event": "J", "review_before_route": POLICY}}}
ROW = {"die": "s81", "event": "J", "item": "t1", "attempt": 1, "kit": "epyc9:/k", "status": "PASS",
       "geom_verdict": "PASS", "geom_dir": "epyc9:/k/geom"}


@pytest.fixture
def verdict(monkeypatch):
    box = {"v": None}
    monkeypatch.setattr(K, "exact_kit_visual_verdict", lambda *_a, **_k: box["v"])
    monkeypatch.setattr(K.FG, "stops_off_die", lambda *_a, **_k: True)
    return box


@pytest.mark.parametrize("v", [None, "ISSUES", "PENDING"])
@pytest.mark.parametrize("gv", ["PASS", "PASS-COND"])
def test_required_review_is_advisory_after_auto_geom_pass(verdict, v, gv):
    verdict["v"] = v
    row = dict(ROW, geom_verdict=gv)
    assert K.required_route_hold(CFG, row) is None
    assert K.route_hold_reason(CFG, dict(ROW)) is None
    assert row["visual_pending"].startswith("WAIT-VISUAL (advisory): AUTO-GEOM PASS")


def test_bad_verdict_still_holds(verdict):
    verdict["v"] = "BAD"
    assert K.required_route_hold(CFG, dict(ROW)).startswith("WAIT-FORM")
    assert K.route_hold_reason(CFG, dict(ROW)).startswith("WAIT-FORM")


@pytest.mark.parametrize("geom", [{"geom_verdict": "FAIL"}, {"geom_verdict": None}, {"geom_dir": None}])
def test_no_auto_geom_pass_keeps_required_hold(verdict, geom):
    row = dict(ROW, **geom)
    assert K.required_route_hold(CFG, row).startswith("WAIT-VISUAL")
    verdict["v"] = "ISSUES"
    assert K.required_route_hold(CFG, dict(row)).startswith("WAIT-FORM")


def test_route_mode_visual_hold(monkeypatch):
    monkeypatch.setattr(K, "minimal_profile", lambda: False)
    monkeypatch.setattr(K, "verdict_applies", lambda *_a, **_k: True)
    box = {}
    monkeypatch.setattr(K, "visual_verdicts", lambda: box)
    cfg = {"dies": {"hbm": {}}}
    rec = dict(ROW, die="hbm", kind="type")            # hbm keeps holds unless its own AUTO-GEOM passed
    assert K.visual_hold(cfg, dict(rec)) is None
    assert K.visual_hold(cfg, dict(rec, geom_verdict="PASS-COND")) is None      # granted geom FAIL still has its render
    assert K.visual_hold(cfg, dict(rec, geom_verdict=None)).startswith("WAIT-VISUAL")
    box[("hbm", "t1", 1)] = "ISSUES"
    assert K.visual_hold(cfg, dict(rec)) is None
    assert K.visual_hold(cfg, dict(rec, geom_dir=None)).startswith("WAIT-FORM")
    box[("hbm", "t1", 1)] = "BAD"
    assert K.visual_hold(cfg, dict(rec)).startswith("WAIT-FORM")
