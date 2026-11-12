"""dieclock_routed realize: balance cells at die-channel sites only (COORD 11-12 decision B)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dieclock_routed as R  # noqa: E402

BUF = "BUFx24_ASAP7_75t_R"


def _fixture(tmp, node_xy):
    clk = tmp / "clk"
    clk.mkdir()
    (clk / "ctree.v").write_text("\n".join([
        "module ctree (root, t_a, t_b);", "  input root;", "  output t_a, t_b;", "  wire w_n0;",
        f"  {BUF} n0 (.A(root), .Y(w_n0));",
        f"  {BUF} ka (.A(w_n0), .Y(t_a));",
        f"  {BUF} kb (.A(w_n0), .Y(t_b));",
        "endmodule"]) + "\n")
    (clk / "ctree_ck89.tcl").write_text("\n".join(
        "place_inst -name %s -location {%.3f %.3f} -status PLACED" % (n, x, y)
        for n, (x, y) in (("n0", node_xy), ("ka", (100.0, 500.0)), ("kb", (900.0, 500.0)))) + "\n")
    arr = tmp / "arr.txt"
    arr.write_text("T t_a 100.0 100.0 10\nT t_b 210.0 210.0 10\n")
    plan = tmp / "plan.json"
    plan.write_text(json.dumps(dict(
        partition_types={"tile": {"outline_um": [400.0, 300.0]}},
        partitions=[dict(name="p0", type="tile", origin_um=[300.0, 400.0], orient="R0"),
                    dict(name="p1", type="tile", origin_um=[700.0, 400.0], orient="R0")])))
    return clk, arr, plan


def _placed(out):
    return {m.group(1): (float(m.group(2)), float(m.group(3)))
            for m in (re.match(r"place_inst -name (dlyg\S+) -location \{(\S+) (\S+)\}", ln)
                      for ln in (out / "ctree_ck89.tcl").read_text().splitlines()) if m}


def test_realize_channel_sites_never_inside_a_type(tmp_path):
    # n0 sits inside p0, which abuts p1: the nearest channel point is past p0's top/bottom edge, not inside p1
    clk, arr, plan = _fixture(tmp_path, (650.0, 450.0))
    out = tmp_path / "rz"
    R.main(["realize", str(clk), str(arr), str(out), "--step-ps", "55", "--plan", str(plan)])
    rep = json.loads((out / "realize.json").read_text())
    assert rep["cell"] == "HB4xp67_ASAP7_75t_R" and rep["sites"] == "channel"
    assert rep["delay_cells"] == 2 and rep["cells_inside_types"] == 0 and rep["chains_moved"] == 1
    rects = R.type_rects(plan)
    for x, y in _placed(out).values():
        assert not any(r[0] < x < r[2] and r[1] < y < r[3] for r in rects)
        assert abs(y - 400.0) < 1.0 and x == 650.0          # bottom edge of p0 (50.5 um), not the p1 side
    v = (out / "ctree.v").read_text()
    assert "HB4xp67_ASAP7_75t_R dlyg1_0_0 (.A(w_n0)" in v and ".A(w_dlyg1_0_1)" in v


def test_realize_channel_needs_plan_and_branch_mode_keeps_site(tmp_path):
    clk, arr, plan = _fixture(tmp_path, (650.0, 450.0))
    try:
        R.main(["realize", str(clk), str(arr), str(tmp_path / "x"), "--step-ps", "55"])
        raise AssertionError("channel sites without a plan must refuse")
    except SystemExit as e:
        assert "--plan" in str(e)
    out = tmp_path / "rb"
    R.main(["realize", str(clk), str(arr), str(out), "--step-ps", "55", "--sites", "branch"])
    assert set(_placed(out).values()) == {(650.0, 450.0)}
