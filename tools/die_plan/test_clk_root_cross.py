"""CLK-ROOT-CROSS (DIE-HBM-97 11-10, COORD vecd-clkroot-gen): root repeater for clock ports boxed in by macros.

Geometry from hnx_vms_bank_q0_faces__vecd4ae (v32e0 / v512b 4_cts, 11-10): two stacked 174.744 x 70.488 SRAMs with an
17.3-um gap at y 146.868..164.172 whose rows are cut (--macro-gap-block); clk and clk_e enter on M5 in that gap."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import clk_root_cross as C  # noqa: E402
import core_flow  # noqa: E402

U_A = [47.616, 76.38, 222.36, 146.868]
U_B = [47.616, 164.172, 222.36, 234.66]


def rows():
    out = []
    y = 4.32
    while y < 300:
        segs = [(4.32, 43.25), (226.69, 265.68)] if 146.0 < y < 164.2 else [(4.32, 265.68)]
        for x0, x1 in segs:
            out.append({"box": [x0, y, x1, y + 0.27], "site": 0.054})
        y += 0.27
    return out


def design(ports, busy=()):
    return {"macros": [U_A, U_B], "halo": 1.0, "rows": rows(), "busy": [list(b) for b in busy], "cell_w": 1.62,
            "ports": ports}


CLK = {"net": "clk", "port": [133.608, 155.52], "sinks": [{"inst": "clkbuf_0_clk", "xy": [134.9, 74.2], "macro": False}]}
CLK_E = {"net": "clk_e", "port": [133.704, 155.52], "sinks": [{"inst": "clkbuf_0_clk_e", "xy": [240.0, 120.0],
                                                                  "macro": False}]}


def _clear_of_macros(p, halo=1.0):
    cx, cy = p["x"] + 0.81, p["y"] + 0.135
    return not any(m[0] - halo < cx < m[2] + halo and m[1] - halo < cy < m[3] + halo for m in (U_A, U_B))


def test_one_port_across_macro_gets_one_repeater_off_macro():
    r = C.plan(design([CLK]))
    assert not r["errors"]
    (p,) = r["placements"]
    assert p["net"] == "clk" and p["reason"] == "cross"
    assert _clear_of_macros(p)
    # repeater -> sink and port -> repeater both have a macro-free L route
    assert C.l_routes_clear([U_A, U_B], p["x"] + 0.81, p["y"], 134.9, 74.2)
    assert C.l_routes_clear([U_A, U_B], 133.608, 155.52, p["x"] + 0.81, p["y"])
    # the sink side channel: the west or east exit at the gap height
    assert p["x"] < U_A[0] or p["x"] > U_A[2]
    assert abs(p["y"] - 155.52) < 10


def test_two_ports_second_boxed_in_both_get_distinct_sites():
    r = C.plan(design([CLK, CLK_E]))
    assert not r["errors"]
    by = {p["net"]: p for p in r["placements"]}
    assert set(by) == {"clk", "clk_e"}
    assert by["clk_e"]["reason"] == "enclosed"          # route clear along the gap, but the port is enclosed
    a, b = by["clk"], by["clk_e"]
    assert not (abs(a["y"] - b["y"]) < 0.27 and abs(a["x"] - b["x"]) < 1.62)   # no overlap
    assert all(_clear_of_macros(p) for p in (a, b))
    assert b["x"] > U_A[2]                               # clk_e exits toward its east sink


def test_port_with_clear_route_and_not_enclosed_gets_none():
    p = {"net": "clk_w", "port": [0.0, 30.0], "sinks": [{"inst": "b", "xy": [20.0, 40.0], "macro": False}]}
    r = C.plan(design([p]))
    assert r["placements"] == [] and r["skipped"][0]["why"] == "route clear"


def test_multi_sink_and_macro_sink_are_skipped():
    p1 = dict(CLK, sinks=CLK["sinks"] * 2)
    p2 = {"net": "clk_macro0", "port": [133.6, 155.5], "sinks": [{"inst": "u_a", "xy": [60.0, 100.0], "macro": True}]}
    r = C.plan(design([p1, p2]))
    assert r["placements"] == [] and {s["why"] for s in r["skipped"]} == {"2 sinks", "sink is a macro pin"}


def test_no_site_fails_closed(tmp_path):
    d = design([CLK])
    d["rows"] = [r for r in d["rows"] if r["box"][1] < 20]       # nothing within 4 x 30 um of the port
    r = C.plan(d)
    assert r["errors"] and r["errors"][0]["net"] == "clk" and not r["placements"]
    i, o = tmp_path / "i.json", tmp_path / "o.json"
    i.write_text(json.dumps(d))
    assert subprocess.run([sys.executable, "-I", str(HERE / "clk_root_cross.py"), "plan", str(i), str(o)]).returncode == 1


def test_enclosed_detection():
    assert C.enclosing_gap([U_A, U_B], 133.6, 155.5) == ("y", U_A[3], U_B[1])
    assert C.enclosing_gap([U_A, U_B], 10.0, 155.5) is None
    assert C.needs_repeater([U_A, U_B], (133.6, 155.5), (134.9, 74.2)) == "cross"


def test_stage_copies_files_and_returns_first_hook_line(tmp_path):
    line = core_flow.stage_clk_root_cross(tmp_path)
    assert line == "source /work/clk_root_cross.tcl\n"
    assert (tmp_path / "clk_root_cross.tcl").read_bytes() == (ROOT / "physical/common_flow/clk_root_cross.tcl").read_bytes()
    assert (tmp_path / "clk_root_cross.py").read_bytes() == (HERE / "clk_root_cross.py").read_bytes()


def test_hbm_generator_runs_the_pass_before_the_post_cts_balance(tmp_path):
    """post_cts_setup_hook: the root pass is sourced before the kit's previous POST_CTS hook (tap / leaf balance)"""
    sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
    import gen_core_kit_hbm as G
    cfg = ["override export POST_CTS_TCL = /work/core_tap_align.tcl"]
    G.post_cts_setup_hook(tmp_path, cfg)
    txt = (tmp_path / "post_cts_setup.tcl").read_text()
    i, j = txt.index("source /work/clk_root_cross.tcl"), txt.index("source {/work/core_tap_align.tcl}")
    assert i < j and (tmp_path / "clk_root_cross.py").is_file() and (tmp_path / "clk_root_cross.tcl").is_file()
    assert cfg[-1] == "override export POST_CTS_TCL = /work/post_cts_setup.tcl"


def test_tcl_reads_the_plan_keys_the_python_writes(tmp_path):
    """the Tcl parses json.dump(indent=1, sort_keys=True) output with regexps: keep the two in step"""
    r = C.plan(design([CLK]))
    txt = json.dumps(r, indent=1, sort_keys=True)
    tcl = (ROOT / "physical/common_flow/clk_root_cross.tcl").read_text()
    for k in ('"net": ', '"x": ', '"y": ', '"reason": '):
        assert k in txt and k in tcl
