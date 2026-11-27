"""FLEET-OPS 11-25: PRE checks of one lane are capped by a host flock slot while the host is overloaded"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_gate_pre as P  # noqa: E402


def env(tmp, **kw):
    e = {"OT_PRE_SLOT_DIR": str(tmp / "slots"), "OT_PRE_LANE_CAP": "1", "OT_PRE_LOAD_X": "0", "OT_PRE_LANE_WAIT_S": "0"}
    e.update(kw)
    return e


def test_second_check_of_a_lane_waits_then_runs_anyway_and_other_lanes_are_not_gated(tmp_path):
    P._LANE_SLOT.clear()
    # The tree path supplies a lane label only. Keep the synthetic labels outside
    # the real temporary slot directory, which can already sit under /claude/.
    a, b = "/fixture/claude/laneA/t", "/fixture/claude/laneB/t"
    assert P.lane_slot(str(a), env(tmp_path)) == 0
    out = io.StringIO()
    assert P.lane_slot(str(a), env(tmp_path), out) is None and "running anyway" in out.getvalue()      # slot taken: waits (0 s here), then proceeds
    assert P.lane_slot(str(b), env(tmp_path)) == 0                                                      # another lane has its own slots
    for fd in P._LANE_SLOT:
        os.close(fd)
    P._LANE_SLOT.clear()
    assert P.lane_slot(str(a), env(tmp_path)) == 0                                                      # a closed fd (a dead check) frees the slot
    for fd in P._LANE_SLOT:
        os.close(fd)
    P._LANE_SLOT.clear()


def test_idle_host_and_cap_zero_are_never_gated(tmp_path):
    P._LANE_SLOT.clear()
    t = tmp_path / "claude" / "laneA" / "t"
    t.mkdir(parents=True)
    assert P.lane_slot(str(t), env(tmp_path, OT_PRE_LOAD_X="100000")) is None
    assert P.lane_slot(str(t), env(tmp_path, OT_PRE_LANE_CAP="0")) is None
    assert not P._LANE_SLOT
