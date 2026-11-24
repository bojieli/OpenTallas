"""RST-NEAREST-1124 / PIN-REACH-1124: unreachable wavefront parts attach nearest-first; a pin out of hop is reported."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
import plan_gate_pre as G  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def plan(pins, order="nearest"):
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront", parent_pins=pins, attach_order=order)
    return schema.Plan(raw)


def test_unreachable_attach_is_nearest_first_not_alphabetical():
    # pa and pm1 are pinned to pb, out of hop: both unreachable.  pa sorts first; alphabetically it would take the nearest
    # part that is already reached (pm2 or pb, farther than pm1).  Nearest-first attaches pm1 to pm2, then pa to pm1 (117 um).
    P = plan({"pa": "pb", "pm1": "pb"})
    s = RT.wf_solve(P)
    assert s["unreachable"] == ["pa", "pm1"]
    assert s["parent"]["pm1"][0] == "pm2"
    assert s["parent"]["pa"][0] == "pm1" and s["parent"]["pa"][2] < s["parent"]["pm1"][2]
    assert s["est_rel"]["pa"] > s["est_rel"]["pm1"] > s["est_rel"]["pm2"]


def test_reachable_plan_unchanged():
    P = plan({})
    s = RT.wf_solve(P)
    assert s["unreachable"] == [] and s["parent"]["pa"][0] == "pm1" and s["parent"]["pb"][0] == "pm2"


def test_pinned_out_of_reach_is_reported():
    assert RT.pinned_out_of_reach(plan({})) == []
    rows = RT.pinned_out_of_reach(plan({"pa": "pb", "pm1": "pb"}))
    assert [(p, q) for p, q, _d in rows] == [("pa", "pb"), ("pm1", "pb")] and all(d > 275 for _p, _q, d in rows)
    assert RT.pinned_out_of_reach(plan({"pa": "pm1"})) == []


def test_pre_line_is_warn_only(tmp_path):
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront", parent_pins={"pa": "pb"})
    p = tmp_path / "die_plan.json"
    p.write_text(json.dumps(raw))
    out = G.rstpin_findings(str(tmp_path), str(p))
    assert len(out) == 1 and out[0].startswith("WARN RSTPIN pa: pinned parent pb")
    raw["reset"].pop("parent_pins")
    p.write_text(json.dumps(raw))
    assert G.rstpin_findings(str(tmp_path), str(p)) == []
    assert "RSTPIN" in G.CLASSES


def test_default_attach_order_is_the_old_alphabetical_one():
    # knob absent / "alphabetical": pa (sorts first) attaches to the nearest part reached BEFORE it, not to pm1
    for order in ("alphabetical", None):
        raw = copy.deepcopy(TINY)
        raw.setdefault("reset", {}).update(release="wavefront", parent_pins={"pa": "pb", "pm1": "pb"})
        if order:
            raw["reset"]["attach_order"] = order
        s = RT.wf_solve(schema.Plan(raw))
        assert s["unreachable"] == ["pa", "pm1"] and s["parent"]["pa"][0] != "pm1"
    assert RT.wf_solve(plan({"pa": "pb", "pm1": "pb"}))["parent"]["pa"][0] == "pm1"


def test_rstnames_reports_a_parent_change_against_the_base(tmp_path):
    base = copy.deepcopy(TINY)
    base.setdefault("reset", {}).update(release="wavefront")
    new = copy.deepcopy(TINY)
    new.setdefault("reset", {}).update(release="wavefront", parent_pins={"pa": "pb", "pm1": "pb"}, attach_order="nearest")
    pb, pn = tmp_path / "base.json", tmp_path / "die_plan.json"
    pb.write_text(json.dumps(base))
    pn.write_text(json.dumps(new))
    out = G.rstnames_findings(str(tmp_path), str(pn), str(pb))
    assert len(out) == 1 and out[0].startswith("WARN RSTNAMES") and "pa" in out[0]
    assert G.rstnames_findings(str(tmp_path), str(pb), str(pb)) == []
    assert G.rstnames_findings(str(tmp_path), str(pn), None) == []
    assert "RSTNAMES" in G.CLASSES
