from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import Report, check_clock_branch_buffers


def _t(bxy, legs_ok=True, parent="b0"):
    far = 100.0 if legs_ok else 500.0
    return dict(hard_cores=[dict(inst="tileA", origin_um=[0, 0], outline_um=[50, 50]),
                            dict(inst="tileB", origin_um=[0, 300], outline_um=[50, 50])],
                clock=dict(taps=[dict(name="tileA", xy=[50, 25], parent=parent),
                                 dict(name="tileB", xy=[50, 25 + 2 * far], parent=parent)],
                           branch_buffers=[dict(name="b0", xy=bxy, drives=["tileA", "tileB"])]))


def test_corridor_buffer_ok():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([60, 125])}), r)
    assert not r.errors() and out["buffers"] == 1 and out["worst_leg_um"] == 110.0


def test_buffer_on_hard_core_fails():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([25, 25])}), r)
    assert out["types"] == ["root"] and any("inside hard core" in e["msg"] if isinstance(e, dict) else "inside hard core" in str(e) for e in r.errors())


def test_leg_over_reach_fails():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([50, 525], legs_ok=False)}), r)
    assert out["types"] == ["root"]


def test_parent_must_match():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([60, 125], parent="nope")}), r)
    assert out["types"] == ["root"] and len(r.errors()) >= 2
