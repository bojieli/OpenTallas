"""test_seat_resite.py -- FP-CONVERGE-S81: plan-level first/last register re-site (pass + mutant)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_seatgap as S  # noqa: E402
import seat_resite as R  # noqa: E402


def _type(regs, frm=(100.0, 200.0), to=(900.0, 200.0)):
    # core A: x 0..100 (pin on its E face at x=100); core B: x 900..1000 (pin on its W face at x=900); outline 1000 x 400
    return {"outline_um": [1000, 400],
            "hard_cores": [{"inst": "u_a", "origin_um": [0, 150], "outline_um": [100, 100]},
                           {"inst": "u_b", "origin_um": [900, 150], "outline_um": [100, 100]}],
            "internal_stations": [{"conn": "core:u_a|core:u_b", "launch": "u_a", "capture": "u_b", "from_um": list(frm), "to_um": list(to),
                                   "regs_um": regs}]}


def test_clean_chain_has_no_rows():
    t = _type([[300.0, 200.0], [600.0, 200.0]])
    assert S.seat_orient(t)[0] == 0
    ops, sk = R.type_fixes("T", t)
    assert ops == [] and sk == []


def test_first_register_inside_the_face_is_moved_to_the_free_side():
    t = _type([[60.0, 200.0], [600.0, 200.0]])                 # regs[0] is 40 um INSIDE core A's east face
    assert S.seat_orient(t)[0] == 1
    ops, sk = R.type_fixes("T", t)
    assert len(ops) == 1 and not sk
    new = ops[0]["value"]
    assert ops[0]["old"] == [[60.0, 200.0], [600.0, 200.0]] and new[1] == [600.0, 200.0]    # only the end register moved, count kept
    t2 = _type(new)
    assert S.seat_orient(t2)[0] == 0                              # no longer against
    assert not any(r[0] < new[0][0] < r[2] and r[1] < new[0][1] < r[3] for r in __import__("adv_geom_static").hard_rects(t))   # outside every core
    assert R.man((100.0, 200.0), new[0]) <= R.CAP and R.man(new[0], new[1]) <= R.CAP


def test_last_register_against_is_moved_too():
    t = _type([[300.0, 200.0], [940.0, 200.0]])               # regs[-1] 40 um inside core B's west face
    ops, _ = R.type_fixes("T", t)
    assert len(ops) == 1 and S.seat_orient(_type(ops[0]["value"]))[0] == 0


def test_mutant_no_legal_site_is_skipped_not_forced():
    t = _type([[60.0, 200.0], [600.0, 200.0]])
    t["outline_um"] = [100, 100]                                  # no lattice site fits inside the inset outline: skipped
    ops, sk = R.type_fixes("T", t)
    assert ops == [] and sk and "no legal site" in sk[0][3]


def test_mutant_hop_over_cap_is_rejected():
    t = _type([[60.0, 200.0], [600.0, 200.0]])
    old = R.CAP
    try:
        R.CAP = 10.0                                              # nothing within 10 um of both pin and the next register
        ops, sk = R.type_fixes("T", t)
    finally:
        R.CAP = old
    assert ops == [] and sk


def test_orient_lines_report_only_plan_view(tmp_path):
    t = _type([[60.0, 200.0], [600.0, 200.0]])
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {"T": t}}))
    ls = R.orient_lines("/x/T", plan=str(p), environ={"OT_KIT_TYPE": "T"})
    assert len(ls) == 1 and ls[0].startswith("WARN ADV-SEAT-ORIENT-PREFLIGHT T: 1 of 2")
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"partition_types": {"T": _type([[300.0, 200.0]])}}))
    assert R.orient_lines("/x/T", plan=str(ok), environ={"OT_KIT_TYPE": "T"}) == []
    assert R.orient_lines("/x/T", plan=None, environ={"OT_KIT_TYPE": "T"})[0].startswith("SKIP")


def test_flip_recommendation_lists_cores_with_mostly_against_pins():
    t = _type([[60.0, 200.0]])
    t["internal_stations"] = t["internal_stations"] * 5
    assert R.flip_recommendations(t, min_share=0.5, min_hops=4) and R.flip_recommendations(_type([[300.0, 200.0]])) == []
