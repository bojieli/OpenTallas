"""HEAD-R17 (ROOT-MERGE-32): head_infra_delta_r4.py declares every clock slot island INSIDE its type outline by
construction (die_islands rule, 12.2a1 one-owner pushdown); edge sites are snapped inward and reported."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import head_infra_delta_r4 as D  # noqa: E402

TOOL = ROOT / "tools" / "s81_head" / "head_infra_delta_r4.py"


def test_snap_inside_clamps_edges():
    assert D.snap_inside(0.0, 354.24, 708.48, 1036.8) == (4.32, 354.24)
    assert D.snap_inside(708.313, 354.24, 708.48, 1036.8) == (704.16, 354.24)
    assert D.snap_inside(686.88 + 4.32, 0.0, 1382.4, 2073.6) == (691.2, 4.32)
    assert D.snap_inside(100.0, 200.0, 708.48, 1036.8) == (100.0, 200.0)


def test_delta_islands_inside_and_deduped(tmp_path):
    plan = dict(partition_types=dict(
        hd_tile=dict(outline_um=[708.48, 1036.8], clock=dict(tap_um=[354.24, 518.4]),
                     hard_cores=[dict(origin_um=[20.0, 400.0], outline_um=[300.0, 300.0])])))
    census = dict(types=dict(hd_tile=dict(rows_y=[354.24], slots=[
        dict(xy=[0.0, 354.24], roles=["node"]), dict(xy=[0.267, 354.24], roles=["rep"]),
        dict(xy=[708.48, 354.24], roles=["node"]), dict(xy=[354.24, 354.24], roles=["driver"])])))
    p, c, o = tmp_path / "p.json", tmp_path / "c.json", tmp_path / "o.json"
    p.write_text(json.dumps(plan)); c.write_text(json.dumps(census))
    r = subprocess.run([sys.executable, str(TOOL), str(p), str(c), str(o)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    t = json.loads(o.read_text())["partition_types"]["hd_tile"]
    W, H = t["outline_um"]
    rects = t["clock"]["die_islands_um"]
    assert len(rects) == 3                       # the two x=0 edge sites share one island
    assert all(x0 >= 0 and y0 >= 0 and x1 <= W and y1 <= H for x0, y0, x1, y1 in rects)
    assert all(abs((x1 - x0) - D.SIDE) < 1e-6 and abs((y1 - y0) - D.SIDE) < 1e-6 for x0, y0, x1, y1 in rects)
    rep = json.loads(r.stdout)["types"]["hd_tile"]
    assert rep["snapped"] == 3 and rep["max_snap_um"] == 4.32


def test_committed_head_plan_islands_inside():
    P = json.loads((ROOT / "physical/die_plan/s81_head/die_plan.json").read_text())
    for tn, t in P["partition_types"].items():
        W, H = t["outline_um"]
        for r in (t.get("clock") or {}).get("die_islands_um", []) or []:
            assert r[0] >= -1e-6 and r[1] >= -1e-6 and r[2] <= W + 1e-6 and r[3] <= H + 1e-6, (tn, r)
