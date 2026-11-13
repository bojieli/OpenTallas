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


def test_leafcell_one_hb4_per_capped_leaf_on_its_own_leg_in_a_channel(tmp_path):
    # COORD 11-12: a leaf at the 1500-um wire cap gets ONE HB4xp67 in series on its own leg r10_a (650, 300) -> n10_a
    # (650, 450, inside p0 from y 400): the leg's channel point closest to the leaf side, detour 0, never inside a type;
    # a capped leaf whose leg passes no channel within --max-detour-um gets none; the rest of the tree is unchanged
    _clk, _arr, plan = _fixture(tmp_path, (650.0, 450.0))
    run = tmp_path / "run"
    run.mkdir()
    cells = {"n9_a": dict(x=650.0, y=100.0, kind="node", level=9), "r10_a": dict(x=650.0, y=300.0, kind="rep", level=10),
             "n10_a": dict(x=650.0, y=450.0, kind="node", level=10), "td0": dict(x=650.0, y=450.0, kind="tapdrv", level=11),
             "n9_c": dict(x=500.0, y=650.0, kind="node", level=9), "n10_c": dict(x=550.0, y=650.0, kind="node", level=10),
             "n10_b": dict(x=100.0, y=100.0, kind="node", level=10)}
    nets = [dict(name="w_n9_a", drv="n9_a", branches=[[200.0, "M8", "r10_a", 200.0]]),
            dict(name="w_r10_a", drv="r10_a", branches=[[300.0, "M8", "n10_a", 150.0]]),
            dict(name="w_n10_a", drv="n10_a", branches=[[4.32, "M8", "td0", 4.32]]),
            dict(name="w_n9_c", drv="n9_c", branches=[[50.0, "M8", "n10_c", 50.0]]),
            dict(name="w_n10_b", drv="n10_b", branches=[[4.32, "M8", "port:t_b", 4.32]])]
    (run / "nets.json").write_text(json.dumps(dict(ports=[["input", "root"], ["output", "t_b"]], nets=nets)))
    (run / "place.json").write_text(json.dumps(cells))
    (run / "tree.json").write_text(json.dumps(dict(taps=[], meta={})))
    pads = tmp_path / "lp.json"
    pads.write_text(json.dumps({"n10_a": 1500.0, "n10_b": 800.0, "n10_c": 1500.0}))
    out = tmp_path / "lc"
    assert R.main(["leafcell", str(run), str(out), "--plan", str(plan), "--leaves", str(pads), "--max-detour-um", "50"]) == 0
    rep = json.loads((out / "leafcell.json").read_text())
    assert rep["cells"] == 1 and rep["cells_inside_types"] == 0 and rep["rows"][0]["leaf"] == "n10_a"
    assert rep["rows"][0]["detour_um"] == 0.0 and [r[0] for r in rep["no_channel"]] == ["n10_c"]   # n10_c leg in p0
    pl = json.loads((out / "place.json").read_text())
    x, y = pl["lh_n10_a"]["x"], pl["lh_n10_a"]["y"]
    assert pl["lh_n10_a"]["lib"] == "HB4xp67_ASAP7_75t_R" and x == 650.0 and 300.0 <= y <= 400.0
    assert not any(r[0] < x < r[2] and r[1] < y < r[3] for r in R.type_rects(plan))
    nj = {n["name"]: n for n in json.loads((out / "nets.json").read_text())["nets"]}
    b1, b2 = nj["w_r10_a"]["branches"][0], nj["w_lh_n10_a"]["branches"][0]
    assert b1[2] == "lh_n10_a" and b2[2] == "n10_a" and abs(b1[0] + b2[0] - 300.0) < 1e-6   # electrical length kept
    assert abs(b2[0] - 150.0 * (1 - rep["rows"][0]["frac"])) < 0.2          # the cell drives only the physical rest
    assert nj["w_n10_b"] == nets[4] and nj["w_n9_a"] == nets[0]
    v = (out / "ctree.v").read_text()
    assert "HB4xp67_ASAP7_75t_R lh_n10_a (.A(w_r10_a), .Y(w_lh_n10_a));" in v and f"{BUF} n10_a (.A(w_lh_n10_a)" in v
