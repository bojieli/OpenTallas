"""HEAD-CORE-R20 plan delta: 26 declared slots + spine trunk M9 riser (fail-closed checks)."""
import copy, importlib.util, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tools/s81_head/head_r19_island_riser_delta.py"
PLAN = ROOT / "physical/die_plan/s81_head/die_plan.json"
DELTA = ROOT / "results/s81_head_r20_plan/slot_delta_r19.json"
spec = importlib.util.spec_from_file_location("hrd", TOOL); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def test_plan_carries_delta():
    P = json.loads(PLAN.read_text()); D = json.loads(DELTA.read_text())
    for tn, v in D["types"].items():
        isl = {tuple(r) for r in P["partition_types"][tn]["clock"]["die_islands_um"]}
        for s in v.get("slots", []):
            assert tuple(s["rect_um"]) in isl
    t = P["clock"]["spine"]["trunk"]
    assert t == dict(layer="M9", node_x_um=8760.96, lane_x_um=8769.6, riser_um=8.64)


def test_reapply_fails_closed(tmp_path):
    p = tmp_path / "plan.json"; p.write_text(PLAN.read_text())
    r = subprocess.run([sys.executable, str(TOOL), str(p), str(DELTA), "--report", str(tmp_path / "r.json")])
    assert r.returncode == 1 and "already declared" in (tmp_path / "r.json").read_text()
    assert p.read_text() == PLAN.read_text()


def test_lane_on_stripe_fails():
    P = json.loads(PLAN.read_text())
    assert all(x["verdict"] == "PASS" for x in M.lane_check(P, [12.96], 0.5))
    old = M.LANE_X
    try:
        M.LANE_X = M.NODE_X
        assert all(x["verdict"] == "FAIL" for x in M.lane_check(P, [12.96], 0.5))
    finally:
        M.LANE_X = old


def test_overlap():
    assert M.overlaps([0, 0, 2, 2], [1, 1, 3, 3]) and not M.overlaps([0, 0, 1, 1], [1, 0, 2, 1])
