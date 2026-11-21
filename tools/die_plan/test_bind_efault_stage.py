"""tests for the opt-in staged efault form (bind_efault_stage.py, asbuilt.efault_stage):
python3 -m pytest tools/die_plan/test_bind_efault_stage.py

Unit: config checks, the depth / AGE law, station sites <= reach on the Manhattan path, fail-closed cases.
End to end (Yosys): bind_tiny lanes, plan cell u_efault in type ts over the epochs of its 4 in buses (sources 900 um from
the L1 centre, reach 300 -> D 2, AGE 4 -> 6).  Key absent = no station, no receipt, the cell as before; key on = one
2-stage keep chain per eq bit, AGE + 2, site rows per stage, bind verify PASS on both.
The RTL equivalence (staged fault == unstaged fault D edges later) is rtl/test/kv_efault_stage_1120/run.sh."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import bind_efault_stage as ES  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
ROOT = HERE.parents[1]
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


def cell(buses, age=7, **extra):
    return {"module": "ot_dp_efault", "params": dict({"AGE": age, "N": len(buses)}, **extra),
            "conns": {"clk": [{"net": "clk"}], "rst_n": [{"net": "rst_n"}], "eq": [{"epoch": b} for b in buses]}}


def cfg(**kw):
    return ES.config({ES.KEY: dict({"types": ["kv3_hub_Wo"], "reach_um": 300}, **kw)})


# ------------------------------------------------------------------------------------------------ unit
def test_config():
    assert ES.config({}) is None and ES.config(None) is None
    c = cfg(cells=["u_efault"], depth=1, sites={"kv3_hub_Wo": {}})
    assert ES.selected(c, "kv3_hub_Wo") and not ES.selected(c, "kv3_hub_Wox") and ES.selected(c, "x", "kv3_hub_Wo")
    assert c["reach"] == 300.0 and c["depth"] == 1 and c["cells"] == {"u_efault"}
    for bad in ({"types": [], "reach_um": 300}, {"types": ["a"]}, {"types": ["a"], "reach_um": 0},
                {"types": ["a"], "reach_um": True}, {"types": ["a"], "reach_um": 300, "depth": -1},
                {"types": ["a"], "reach_um": 300, "depth": 1.5}, {"types": ["a"], "reach_um": 300, "cells": []},
                {"types": ["a"], "reach_um": 300, "hop": 1}, {"types": ["a"], "reach_um": 300, "sites": 3}, "x"):
        with pytest.raises(ValueError):
            ES.config({ES.KEY: bad})


def test_sites_file_relative_to_base(tmp_path):
    (tmp_path / "s.json").write_text(json.dumps({"t": {"u_efault": {"at_um": [1, 2]}}}))
    c = ES.config({ES.KEY: {"types": ["t"], "reach_um": 300, "sites": "s.json"}}, base=str(tmp_path))
    assert c["sites"]["t"]["u_efault"]["at_um"] == [1, 2]
    with pytest.raises(ValueError, match="cannot read"):
        ES.config({ES.KEY: {"types": ["t"], "reach_um": 300, "sites": "nope.json"}}, base=str(tmp_path))


def test_need_and_path():
    assert [ES.need(d, 300) for d in (0, 1, 300, 300.0000001, 301, 600, 601, 900, 2700)] == [0, 0, 0, 0, 1, 1, 2, 2, 8]
    assert ES.path_point((0, 0), (100, -50), 60) == (60, 0) and ES.path_point((0, 0), (100, -50), 130) == (100, -30)
    assert ES.path_point((0, 0), (-100, 50), 150) == (-100, 50)
    s = ES.stage_sites((0, 0), (900, 300), 3)
    assert s == [[300.0, 0.0], [600.0, 0.0], [900.0, 0.0]]
    pts = [(0, 0)] + [tuple(x) for x in s] + [(900, 300)]
    assert all(ES.md(a, b) == pytest.approx(300) for a, b in zip(pts, pts[1:]))
    assert ES.l1_centre([(0, 0), (1000, 0), (0, 800), (1000, 800)]) == (500.0, 400.0)


def test_plan_cell_depth_age_and_hops():
    """26 ranks spread over a 1279 x 1676 type: every bit gets the same D, AGE + D, every hop <= reach"""
    buses = [f"b{i}" for i in range(26)]
    xy = {b: (49.0 * i % 1279, 64.0 * i % 1676) for i, b in enumerate(buses)}
    xy["b0"], xy["b25"] = (0.0, 0.0), (1279.0, 1676.0)
    c = cfg()
    p = ES.plan_cell(c, "kv3_hub_Wo", "u_efault", cell(buses), xy.get)
    at = tuple(p["at_um"])
    far = max(ES.md(xy[b], at) for b in buses)
    D = ES.need(far, 300)
    assert D >= 4 and p["depth"] == D and p["age_old"] == 7 and p["age_new"] == 7 + D
    assert len(p["chains"]) == 26 and all(len(ch["regs_um"]) == D for ch in p["chains"])
    assert p["max_hop_um"] <= 300
    for ch in p["chains"]:
        pts = [tuple(ch["src_um"])] + [tuple(r) for r in ch["regs_um"]] + [at]
        hops = [ES.md(a, b) for a, b in zip(pts, pts[1:])]
        assert max(hops) <= 300 + 1e-3 and sum(hops) == pytest.approx(ch["dist_um"], abs=0.01)
    # forced depth wins when larger; sites at_um / src_um override the plan points
    p2 = ES.plan_cell(cfg(depth=D + 2), "kv3_hub_Wo", "u_efault", cell(buses), xy.get)
    assert p2["depth"] == D + 2 and p2["age_new"] == 7 + D + 2
    p3 = ES.plan_cell(c, "t", "u_efault", cell(["a", "b"], age="5"), {"a": (0, 0)}.get,
                      {"u_efault": {"at_um": [0, 0], "src_um": {"b": [700, 0]}}})
    assert p3["depth"] == 2 and p3["age_new"] == 7 and p3["at_um"] == [0.0, 0.0]
    assert p3["chains"][0]["regs_um"] == [[0.0, 0.0], [0.0, 0.0]]          # a source at the site: padded in place
    assert p3["chains"][1]["regs_um"] == [[466.667, 0.0], [233.333, 0.0]]


def test_plan_cell_within_reach_and_repeated_bus():
    p = ES.plan_cell(cfg(), "t", "u_efault", cell(["a", "b", "a"]), {"a": (0, 0), "b": (200, 100)}.get)
    assert p["depth"] == 0 and p["age_new"] == 7 and all(ch["regs_um"] == [] for ch in p["chains"])
    assert [ch["bits"] for ch in p["chains"]] == [[0, 2], [1]]        # one chain per distinct source


def test_plan_cell_fail_closed():
    src = {"a": (0, 0), "b": (900, 0)}.get
    bad = [cell(["a", "c"]),                                        # no source point for c
           dict(cell(["a", "b"]), params={"AGE": 7, "N": 3}),       # N != eq entries
           cell(["a", "b"], age="REL_AGE"),                         # symbolic AGE
           cell(["a", "b"], age=True),
           cell(["a", "b"], EQ_PIPE=1),                             # the cell's own pipe set
           cell(["a", "b"], EQ_PIPE_V="8'h10"),
           dict(cell(["a"]), conns={"eq": [{"bus": "a", "bits": [0, 0]}]}),     # not an epoch entry
           dict(cell(["a"]), conns={})]
    for c in bad:
        with pytest.raises(ValueError):
            ES.plan_cell(cfg(), "t", "u_efault", c, src)
    assert ES.plan_cell(cfg(), "t", "u_efault", cell(["a", "b"], EQ_PIPE=0, EQ_PIPE_V="8'h00"), src)["depth"] == 1   # centre 450 um from each
    for row in ({"u_efault": {"src_um": {"zz": [0, 0]}}}, {"u_efault": {"at_um": [0]}}, {"u_efault": {"extra": 1}},
                {"u_efault": {"src_um": {"a": [0, "x"]}}}):
        with pytest.raises(ValueError):
            ES.plan_cell(cfg(), "t", "u_efault", cell(["a", "b"]), src, row)
    cells = {"u_efault": cell(["a"]), "u_id": {"module": "ot_dp_id_src"}}
    assert ES.staged_cells(cfg(), cells) == ["u_efault"]
    assert ES.staged_cells(cfg(cells=["u_efault"]), cells) == ["u_efault"]
    with pytest.raises(ValueError):
        ES.staged_cells(cfg(cells=["u_id"]), cells)
    with pytest.raises(ValueError):
        ES.staged_cells(cfg(cells=["u_efault", "u_nope"]), cells)


def test_site_rows():
    assert ES.site_rows("u_efs2_efault_3", [[1.0, 2.0], [3.0, 4.0]]) == {"u_efs2_efault_3.r[0]": [1.0, 2.0],
                                                                         "u_efs2_efault_3.q": [3.0, 4.0]}


def test_avoid_macros_off_box_and_depth_grows():
    """avoid_macros: a stage that falls in a macro box moves off it (2 um gap); D grows when the move breaks the reach"""
    assert cfg()["avoid_macros"] is False and cfg(avoid_macros=True)["avoid_macros"] is True
    with pytest.raises(ValueError):
        cfg(avoid_macros=1)
    src = {"a": (0, 0)}.get
    row = {"u_efault": {"at_um": [900, 0]}}
    p0 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, row)
    assert p0["depth"] == 2 and p0["chains"][0]["regs_um"] == [[300.0, 0.0], [600.0, 0.0]] and "moved_off_macro" not in p0
    # a small box round the first stage: it moves 3 um down (2 um gap), D stays 2, every hop still <= 300
    r8 = {"u_efault": {"at_um": [800, 0]}}
    small = [(260.0, -1.0, 270.0, 10.0)]
    p1 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, r8, small)
    regs = p1["chains"][0]["regs_um"]
    assert p1["depth"] == 2 and p1["moved_off_macro"] == 1 and regs[0] == [266.667, -3.0] and regs[1] == [533.333, 0.0]
    assert ES.chain_hop((0, 0), regs, (800, 0)) <= 300 and p1["max_hop_um"] <= 300
    # a box the D-2 stage leaves sideways (300 -> 248: hop 352): D grows to 3, whose sites clear the box
    box = [(250.0, -50.0, 350.0, 100.0)]
    p4 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, row, box)
    regs = p4["chains"][0]["regs_um"]
    assert p4["depth"] == 3 and p4["age_new"] == 10 and p4["max_hop_um"] <= 300
    assert not any(b[0] < x < b[2] and b[1] < y < b[3] for x, y in regs for b in box)
    # a long macro across the x-first path: the chain takes the y-first L path, D unchanged
    src2 = {"a": (0, 0)}.get
    wall = [(100.0, -400.0, 800.0, 10.0)]
    p5 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src2, {"u_efault": {"at_um": [900, 300]}}, wall)
    ch = p5["chains"][0]
    assert p5["depth"] == 3 and ch.get("yfirst") is True and p5["max_hop_um"] <= 300
    assert not any(b[0] < x < b[2] and b[1] < y < b[3] for x, y in ch["regs_um"] for b in wall)
    assert ES.path_point_y((0, 0), (100, -50), 30) == (0, -30) and ES.path_point_y((0, 0), (100, -50), 80) == (30, -50)
    # no off-macro answer within D + 8: fail closed
    with pytest.raises(ValueError, match="no off-macro station sites"):
        ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, row, [(-10.0, -500.0, 890.0, 500.0)])
    # no box hit: same sites as without, moved 0
    p2 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, row, [(1000.0, 1000.0, 1100.0, 1100.0)])
    assert p2["chains"][0]["regs_um"] == p0["chains"][0]["regs_um"] and p2["moved_off_macro"] == 0
    # within reach: no stations, nothing moved
    p3 = ES.plan_cell(cfg(), "t", "u_efault", cell(["a"]), src, {"u_efault": {"at_um": [100, 0]}}, box)
    assert p3["depth"] == 0 and p3["moved_off_macro"] == 0
    assert ES.off_macro(box, (300, 0)) is not None and ES.off_macro([], (1, 2)) == [1.0, 2.0]


# ------------------------------------------------------------------------------------------------ end to end
BUSES = ["d0_i", "d1_i", "f0_i", "f1_i"]
SITES = {"ts": {"u_efault": {"src_um": {"d0_i": [0, 0], "d1_i": [1000, 0], "f1_i": [1000, 800]}}}}


def _plan(tmp_path, key=None, name="plan.json"):
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    a = p["asbuilt"]
    a["base"] = str(EX)
    a["files"] = a["files"] + [str(ROOT / "rtl" / "lib" / "ot_dp_efault.sv")]
    pc = tmp_path / "plan_cells_efault.json"
    pc.write_text(json.dumps({"schema": "opentallas.kv_p4.cell_conns.v1",
                              "types": {"ts": {"cells": {"u_efault": cell(BUSES, age=4)},
                                               "leaf_binds": [], "bus_drivers": [], "rewired": []}}}))
    a["plan_cells"] = str(pc)
    p["partition_types"]["ts"]["relay_sites"] = {"u_bin_f0_i.q[0]": [0, 800]}     # f0_i: the plan point path
    if key is not None:
        a[ES.KEY] = key
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def _bind(plan, out, *cmds):
    for c in cmds:
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        if rc:
            return rc
    return 0


def _files(out):
    return {str(f.relative_to(out)): f.read_bytes() for f in sorted(Path(out).rglob("*")) if f.is_file()}


@needs_yosys
def test_key_absent_no_change_and_key_on_stations(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")     # the tiny cores have no signed parameter record (unrelated gate)
    base, on = tmp_path / "base", tmp_path / "on"
    assert _bind(_plan(tmp_path), base, "elab", "bind", "verify") == 0
    key = {"types": ["ts"], "reach_um": 300, "sites": SITES}
    assert _bind(_plan(tmp_path, key, "plan_on.json"), on, "elab", "bind", "verify") == 0
    fb, fo = _files(base), _files(on)
    assert "bind_efault_stage.json" not in fb and "ot_dp_dly_keep" not in fb["rtl/bind_cells.sv"].decode()
    tb = fb["rtl/bt_ts.sv"].decode()
    assert "efs" not in tb and "ot_dp_efault #(.AGE(4), .N(4)) u_u_efault" in tb
    rtl = fo["rtl/bt_ts.sv"].decode()
    st = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\((\d+)\)\) (u_efs\w+) \(\.clk\(clk\), \.d\((\w+)\), \.q\((\w+)\)\);", rtl)
    assert [(d, nm, s) for d, nm, s, _q in st] == [("2", f"u_efs2_efault_{i}", f"{b}_eq") for i, b in enumerate(BUSES)]
    assert "ot_dp_efault #(.AGE(6), .N(4)) u_u_efault" in rtl
    m = re.search(r"\.eq\(([^)]*)\)", rtl[rtl.index("u_u_efault ("):])
    assert m and m.group(1) == "{u_efs2_efault_3_q, u_efs2_efault_2_q, u_efs2_efault_1_q, u_efs2_efault_0_q}"
    assert "module ot_dp_dly_keep" in fo["rtl/bind_cells.sv"].decode()
    rec = json.loads(fo["bind_efault_stage.json"])
    assert rec["option"] == key and list(rec["types"]) == ["ts"]
    r = rec["types"]["ts"]["u_efault"]
    assert r["depth"] == 2 and r["age_old"] == 4 and r["age_new"] == 6 and r["at_um"] == [500.0, 400.0]
    assert r["cells"] == 4 and r["flops"] == 8 and r["max_hop_um"] == 300.0 and len(r["sites"]) == 8
    assert [c["src_um"] for c in r["chains"]] == [[0, 0], [1000, 0], [0, 800], [1000, 800]]
    assert r["sites"]["u_efs2_efault_0.r[0]"] == [300.0, 0.0] and r["sites"]["u_efs2_efault_0.q"] == [500.0, 100.0]
    assert r["sites"]["u_efs2_efault_3.r[0]"] == [700.0, 800.0] and r["sites"]["u_efs2_efault_3.q"] == [500.0, 700.0]
    vb, vo = json.loads(fb["verify_report.json"]), json.loads(fo["verify_report.json"])
    assert vb["verdict"] == "PASS" and vo["verdict"] == "PASS"
    changed = {k for k in set(fb) | set(fo) if fb.get(k) != fo.get(k)}
    assert all(not k.startswith("rtl/") or k in ("rtl/bt_ts.sv", "rtl/bind_cells.sv") for k in changed), changed


@needs_yosys
def test_fail_closed_bind(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    # a key that stages nothing stops the bind
    assert _bind(_plan(tmp_path, {"types": ["nope"], "reach_um": 300}, "p0.json"), tmp_path / "o0", "elab", "bind") != 0
    # an eq source with no point (d0_i: no sites src_um, no relay_sites, no band): an EMIT error, no staged RTL
    out = tmp_path / "o1"
    _bind(_plan(tmp_path, {"types": ["ts"], "reach_um": 300}, "p1.json"), out, "elab", "bind")
    rep = json.loads((out / "bind_report.json").read_text())
    assert rep["n_errors"] >= 1 and any("efault_stage ts.u_efault: eq bus d0_i: no source point" in e for e in rep["errors"])
    assert not (out / "rtl" / "bt_ts.sv").exists() or "u_efs" not in (out / "rtl" / "bt_ts.sv").read_text()
    # efault_stage without plan_cells
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(EX)
    p["asbuilt"][ES.KEY] = {"types": ["ts"], "reach_um": 300}
    f = tmp_path / "np.json"
    f.write_text(json.dumps(p))
    assert _bind(f, tmp_path / "np", "elab", "bind") != 0


@pytest.mark.skipif(not shutil.which("iverilog"), reason="no iverilog")
def test_rtl_equivalence_bench(tmp_path):
    r = subprocess.run(["bash", str(ROOT / "rtl/test/kv_efault_stage_1120/run.sh"), str(tmp_path / "tb")],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "SUMMARY fail 0" in r.stdout, r.stdout + r.stderr
