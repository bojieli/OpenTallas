"""CP2 tool tests (hard cores in the pair proof): core views, proof-leaf cores, early core taps, core latency table,
spine branch model.   python3 -m pytest -q tools/die_plan/test_cp2.py"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cores as C  # noqa: E402
import gen  # noqa: E402
import gen_phys  # noqa: E402
import pair  # noqa: E402
import schema as S  # noqa: E402
import spine  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())

LEF = """VERSION 5.8 ;
MACRO ot_tcore
  CLASS BLOCK ;
  SIZE 86.4 BY 86.4 ;
  PIN clk
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 40.0 85.0 40.024 86.4 ;
    END
  END clk
  PIN ck2
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 10.0 85.0 10.024 86.4 ;
    END
  END ck2
""" + "".join(f"""  PIN a[{i}]
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 {10 + i} 0.2 {10.024 + i} ;
    END
  END a[{i}]
""" for i in range(4)) + "".join(f"""  PIN y[{i}]
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 86.2 {10 + i} 86.4 {10.024 + i} ;
    END
  END y[{i}]
""" for i in range(2)) + """  PIN rst_n
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 50 0.2 50.024 ;
    END
  END rst_n
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
  END VDD
END ot_tcore
END LIBRARY
"""


def lib_text(rise=400.0, fall=420.0, rise2=100.0):
    def ck(name, r, f):
        return f"""    pin("{name}") {{
      direction : input;
      clock : true;
      capacitance : 2.0;
      timing() {{
        timing_type : min_clock_tree_path;
        cell_rise(scalar) {{ values("{r - 50}"); }}
        cell_fall(scalar) {{ values("{f - 50}"); }}
      }}
      timing() {{
        timing_type : max_clock_tree_path;
        cell_rise(scalar) {{
          values("{r}");
        }}
        cell_fall(scalar) {{
          values("{f}");
        }}
      }}
    }}
"""
    return ("library (ot_tcore_tt) {\n  time_unit : \"1ps\";\n  cell (ot_tcore) {\n" + ck("clk", rise, fall) +
            ck("ck2", rise2, rise2) + "    bus(\"a\") {\n      direction : input;\n      pin(\"a[0]\") { capacitance : 1; }\n"
            "    }\n  }\n}\n")


def views(d):
    v = Path(d) / "core_views" / "tcore" / "views" / "ot_tcore"
    v.mkdir(parents=True)
    (v / "ot_tcore.lef").write_text(LEF)
    (v / "ot_tcore_tt.lib").write_text(lib_text())
    (v / "ot_tcore_ff.lib").write_text(lib_text(300, 320, 80))
    b = Path(d) / "core_views" / "tcore_b" / "views" / "ot_tcore"     # a second variant dir (xrt1 / xrt1_b case)
    b.mkdir(parents=True)
    (b / "ot_tcore.lef").write_text(LEF)
    (b / "ot_tcore_tt.lib").write_text(lib_text(999, 999))
    return Path(d) / "core_views"


def with_core(lib=None, lef="physical/ref_tile/tcore/views/ot_tcore/ot_tcore.lef"):
    p = copy.deepcopy(EX)
    p["partition_types"]["src"]["hard_cores"] = [dict(inst="u_x.u_core", module="ot_tcore", origin_um=[86.4, 86.4],
                                                      outline_um=[86.4, 86.4], orient="R0", lef=lef, lib=lib,
                                                      track_offset_um=[0.0, 0.0])]
    if lib is None:
        p["partition_types"]["src"]["hard_cores"][0].pop("lib")
    return p


def test_lef_and_lib_parse():
    with tempfile.TemporaryDirectory() as d:
        vr = views(d)
        f = vr / "tcore" / "views" / "ot_tcore"
        pins = C.lef_pins(f / "ot_tcore.lef")
        assert pins["a"]["width"] == 4 and pins["a"]["dir"] == "INPUT"
        assert pins["y"]["width"] == 2 and pins["y"]["dir"] == "OUTPUT"
        assert pins["clk"]["width"] == 0 and pins["VDD"]["use"] == "POWER"
        assert abs(pins["clk"]["xy"][0] - 40.012) < 1e-6
        ck = C.lib_clocks(f / "ot_tcore_tt.lib")
        assert set(ck) == {"clk", "ck2"}             # a[0] is not a clock
        assert ck["clk"]["rise"] == 400.0 and ck["clk"]["fall"] == 420.0 and ck["clk"]["min_rise"] == 350.0
        assert ck["ck2"]["rise"] == 100.0


def test_find_and_fill_views():
    with tempfile.TemporaryDirectory() as d:
        vr = views(d)
        lef, tt, ff = C.find_views(vr, "ot_tcore", "physical/ref_tile/tcore_b/views/ot_tcore/ot_tcore.lef")
        assert "/tcore_b/" in lef and tt.endswith("tcore_b/views/ot_tcore/ot_tcore_tt.lib") and ff is None
        lef, tt, ff = C.find_views(vr, "ot_tcore")           # no hint: the shortest tile dir name, never random
        assert "/tcore/" in lef and ff.endswith("ot_tcore_ff.lib")
        raw = with_core(lib=None)
        done, miss = C.fill_views(raw, vr)
        hc = raw["partition_types"]["src"]["hard_cores"][0]
        assert len(done) == 1 and not miss and hc["lib"].endswith("/tcore/views/ot_tcore/ot_tcore_tt.lib")
        assert Path(hc["lef"]).is_absolute()
        assert C.find_views(vr, "nope") == (None, None, None)


def cp2_pair(d, core_taps=True):
    vr = views(d)
    raw = with_core()
    C.fill_views(raw, vr)
    assert not S.validate(raw)
    plan, leaves = pair.extract(raw, ["pa", "pm1"], cores=True, core_taps=core_taps)
    added = plan.pop("core_taps_added", None)
    return raw, plan, leaves, added


def test_pair_cores_leaf_and_core_taps():
    with tempfile.TemporaryDirectory() as d:
        raw, plan, leaves, added = cp2_pair(d)
        assert not S.validate(plan), S.validate(plan)[:5]
        assert "(* keep *) ot_tcore u_core (" in leaves
        assert ".clk(clk)" in leaves and ".ck2(clk)" in leaves
        assert ".a(u_core_ci[3:0])" in leaves and ".rst_n(u_core_ci[4])" in leaves
        assert ".y(u_core_cw[1:0])" in leaves and "u_core_co <= u_core_cw" in leaves
        assert "reg [4:0] u_core_ci;" in leaves                  # 4 + rst_n; clocks are not stub-driven
        hc = plan["partition_types"]["src"]["hard_cores"][0]
        assert hc["inst"] == "u_leaf.u_core"
        # early core tap only for clk (400 > 250 - 40), not for ck2 (100)
        ck = plan["partition_types"]["src"]["clock"]
        assert ck["core_taps"] == "early" and [t["name"] for t in ck["taps"]] == ["u_leaf.u_core.clk"]
        assert ck["taps"][0]["insertion_ps"] == 400.0 and added["src"] == [("u_leaf.u_core.clk", 400.0)]
        x, y = ck["taps"][0]["xy"]
        assert not (86.4 - 8.6 < x < 172.8 + 8.6 and 86.4 - 8.6 < y < 172.8 + 8.6)   # in a channel, off the core
        assert "core_taps" not in plan["partition_types"]["mid"].get("clock", {})
        P = S.Plan(plan)
        assert S.core_taps(P, "mid") == [] and [n for n, *_ in S.core_taps(P, "src")] == ["clk_c0"]
        assert S.core_tap_early_ps(P, ck["taps"][0]) == 150.0
        # the full die's spine geometry is kept (spine.py)
        sp = plan["clock"]["spine"]
        assert sp["die_root_um"] == [1728.0, 432.0] and sp["die_outline_um"] == [3456.0, 864.0]
        assert sp["part_die_origin_um"] == {"pa": [0.0, 0.0], "pm1": [864.0, 0.0]}


def test_pair_cores_needs_views():
    raw = with_core(lef=None)
    raw["partition_types"]["src"]["hard_cores"][0].pop("lef")
    with pytest.raises(SystemExit):
        pair.extract(raw, ["pa", "pm1"], cores=True)


def test_gen_phys_core_files_and_default_unchanged():
    with tempfile.TemporaryDirectory() as d:
        raw, plan, leaves, _ = cp2_pair(d)
        out = Path(d) / "pp"
        out.mkdir()
        (out / "leaves.sv").write_text(leaves)
        for t in plan["partition_types"].values():
            t["sources"] = [str(out / "leaves.sv")]
        kits = gen_phys.write_phys(plan, Path(d) / "kits", str(HERE.parent.parent), proof=True)
        ks = {k.name: k for k in kits}
        src, mid = ks["src"], ks["mid"]
        rows = (src / "core_latency.txt").read_text().split("\n")
        assert "u_leaf.u_core clk 400 clk_c0" in rows and "u_leaf.u_core ck2 100 grid" in rows
        assert (src / "core_taps.txt").read_text().split("\n")[1] == "clk_c0 u_leaf.u_core clk 150 400"
        sdc = (src / "constraint.sdc").read_text()
        assert "set_clock_latency -source -clock clk -150.0000 [get_ports clk_c0]" in sdc
        assert "clk_c0" in sdc.split("create_clock -name clk ")[1].split("\n")[0]
        cfg = (src / "config.mk").read_text()
        assert "OT_CORE_LAT = /work/core_latency.txt" in cfg and "OT_CORE_TAPS = /work/core_taps.txt" in cfg
        assert "/work/macros/ot_tcore_tt.lib" in cfg and "place_macro -macro_name {u_leaf.u_core}" in \
            (src / "macro_place.tcl").read_text()
        assert "place_pin -pin_name clk_c0 " in (src / "io.tcl").read_text()
        assert "input  wire clk_c0" in (src / "rtl" / "s_src.sv").read_text() if (src / "rtl" / "s_src.sv").exists() \
            else any("input  wire clk_c0" in f.read_text() for f in (src / "rtl").glob("*.sv"))
        bud = json.loads((src / "budget.json").read_text())
        assert bud["clock"]["core_taps"][0]["port"] == "clk_c0" and len(bud["core_latency"]) == 2
        # a type without hard cores: no core files, no env, no extra ports (default behaviour unchanged)
        assert not (mid / "core_latency.txt").exists() and not (mid / "core_taps.txt").exists()
        assert "OT_CORE" not in (mid / "config.mk").read_text()
        assert "clk_c" not in (mid / "constraint.sdc").read_text()
        # the die top drives the core tap from the die clock
        assert ".clk_c0(clk)" in (Path(d) / "kits" / "_rtl" / "tiny_top.sv").read_text() if \
            (Path(d) / "kits" / "_rtl" / "tiny_top.sv").exists() else \
            any(".clk_c0(clk)" in f.read_text() for f in (Path(d) / "kits" / "_rtl").glob("*_top.sv"))


def test_htree_path():
    L, legs = spine.htree_path((500.0, 500.0), (1000.0, 1000.0), (100.0, 100.0), 250.0)
    assert legs == [250.0, 250.0, 125.0, 125.0, 50.0] and L == 800.0
    # every leaf-centre point of a symmetric H-tree has the same branch length
    a, _ = spine.htree_path((500.0, 500.0), (1000.0, 1000.0), (125.0, 125.0), 250.0)
    b, _ = spine.htree_path((500.0, 500.0), (1000.0, 1000.0), (875.0, 625.0), 250.0)
    assert a == b == 750.0
    # an off-centre root: level 1 splits at the root x, so the two halves differ
    c, lc = spine.htree_path((300.0, 500.0), (1000.0, 1000.0), (100.0, 500.0), 250.0)
    assert lc[0] == 150.0


def test_branch_table_and_sta_die():
    with tempfile.TemporaryDirectory() as d:
        _, plan, _, _ = cp2_pair(d)
        plan["clock"]["spine"]["branch_ps_per_mm"] = 100.0
        P = S.Plan(plan)
        tab = spine.branch_table(P)
        assert set(tab["parts"]) == {"pa", "pm1"} and tab["branch_ps_per_mm"] == 100.0
        t = tab["parts"]["pa"]["taps"]
        assert {"clk", "clk_t1", "clk_c0"} <= set(t) and t["clk_c0"]["early_ps"] == 150.0 and t["clk"]["early_ps"] == 0
        assert min(v["branch_ps"] - tab["ref_branch_ps"] for r in tab["parts"].values() for v in r["taps"].values()) == 0
        assert abs(t["clk_c0"]["offset_ps"] - (t["clk_c0"]["branch_ps"] - tab["ref_branch_ps"] - 150.0)) < 0.01
        # die frame: the pair origin maps back onto the full die (pm1 sits at x 864 in both)
        assert tab["parts"]["pm1"]["taps"]["clk"]["xy_die"][0] > 864.0
        mv = Path(d) / "mv"
        gen_phys.write_mock_views(plan, mv)
        kd = gen_phys.write_assembly(plan, Path(d) / "asm", mv)
        sta = (kd / "sta_die.tcl").read_text()
        assert 'set SPINE [expr {[info exists ::env(SPINE)] ? $::env(SPINE) : "branch"}]' in sta
        assert "create_generated_clock -name ck_pa_clk_c0 -source [get_ports clk] -divide_by 1 [get_pins pa/clk_c0]" in sta
        assert "set_propagated_clock [all_clocks]" in sta
        js = json.loads((kd / "spine_branch.json").read_text())
        assert js["parts"]["pa"]["taps"]["clk_c0"]["offset_ps"] == t["clk_c0"]["offset_ps"]
        # a full die (no die_root_um): the routed spine stays the default
        full = gen_phys.sta_die_tcl(S.Plan(copy.deepcopy(EX)), spine.branch_table(S.Plan(copy.deepcopy(EX))))
        assert ': "routed"}]' in full


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh not installed")
def test_tcl_hooks_complete():
    for f in ("clock_taps.tcl", "tap_balance.tcl"):
        r = subprocess.run(["tclsh"], input=f"set fh [open {HERE / f}]; puts [info complete [read $fh]]",
                           capture_output=True, text=True)
        assert r.stdout.strip() == "1", f
    tb = (HERE / "tap_balance.tcl").read_text()
    assert "OT_CORE_LAT" in tb and "OT_TAP_CORE" in tb and "^clk(_t[0-9]+|_c[0-9]+)?$" in tb
    assert "OT_CORE_TAPS" in (HERE / "clock_taps.tcl").read_text()
