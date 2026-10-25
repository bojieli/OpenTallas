"""tests for the registered-pin hard-partition rule (COORD 2026-10-25 11:31, PATH-QC-PHYB):
tools/die_plan/hard_pinreg.py (lib checker, declaration) + tools/die_plan/bind.py reg_hard (no station on the macro side).

    python3 -m pytest tools/die_plan/test_hard_pinreg.py
The bind cases need Yosys ($OT_BIND_YOSYS or docker), like test_bind.py; the lib / declaration cases do not.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import check  # noqa: E402
import hard_pinreg as HP  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
REPO = HERE.parents[1]


def lib_text(cell="lf_rphy", setup=True, hold=True, c2q=True, w=8):
    def tim(kind):
        return f'      timing () {{\n        related_pin : "clk";\n        timing_type : {kind};\n      }}\n'
    ins = (tim("setup_rising") if setup else "") + (tim("hold_rising") if hold else "")
    return (f"library ({cell}_tt) {{\n  type ({cell}_b_t) {{\n    base_type : array;\n    data_type : bit;\n"
            f"    bit_width : {w};\n    bit_from : {w - 1};\n    bit_to : 0;\n  }}\n  cell ({cell}) {{\n"
            f"    pin (clk) {{\n      direction : input;\n      clock : true;\n    }}\n"
            f"    pin (rst_n) {{\n      direction : input;\n{tim('setup_rising')}{tim('hold_rising')}    }}\n"
            f"    bus (i) {{\n      bus_type : {cell}_b_t;\n      direction : input;\n{ins}    }}\n"
            f"    bus (o) {{\n      bus_type : {cell}_b_t;\n      direction : output;\n"
            f"{tim('rising_edge') if c2q else tim('combinational')}    }}\n  }}\n}}\n")


def test_lib_checker_on_the_phy_views():
    """the QC PHY views (UCIe KV + SerDes s597) carry the registered-pin claim at every corner"""
    for d, cell in (("physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy", "ot_qkvd_ucie_x64_phy"),
                    ("physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597",
                     "ot_qfd_serdes_112g_x12_phy_s597")):
        for c in ("tt", "ff", "ss"):
            f = REPO / d / f"{cell}_{c}.lib"
            if not f.exists():
                pytest.skip(f"{f} not in this checkout")
            errs, s = HP.check_lib(f, cell)
            assert errs == [] and s["inputs"] == 3 and s["outputs"] == 3 and s["clocks"] == ["clk"], (f, errs)


def test_lib_checker_fails_closed(tmp_path):
    ok = tmp_path / "ok_tt.lib"
    ok.write_text(lib_text())
    assert HP.check_lib(ok, "lf_rphy") [0] == []
    assert HP.check_lib(ok, "lf_rphy", {"i": ("input", 8), "o": ("output", 8), "clk": ("input", 1)})[0] == []
    for kw, word in ((dict(hold=False), "setup AND hold"), (dict(setup=False), "setup AND hold"),
                     (dict(c2q=False), "clock-to-q")):
        f = tmp_path / f"bad_{word[:5]}_{len(kw)}.lib"
        f.write_text(lib_text(**kw))
        errs, _ = HP.check_lib(f, "lf_rphy")
        assert errs and word in errs[0], errs
    # bind form: an as-built pin missing from the lib, or of another width, fails
    assert "not in the lib" in HP.check_lib(ok, "lf_rphy", {"x": ("input", 1)})[0][0]
    assert "!= lib" in HP.check_lib(ok, "lf_rphy", {"i": ("input", 7)})[0][0]
    assert "no cell" in HP.check_lib(ok, "other")[0][0]


def test_corner_siblings_and_declaration(tmp_path):
    (tmp_path / "lf_rphy_tt.lib").write_text(lib_text())
    (tmp_path / "lf_rphy_ff.lib").write_text(lib_text(hold=False))          # the FF view lacks hold: must fail
    core = dict(inst="u_phy", module="lf_rphy", status="reuse", registered_pins=True, lib="lf_rphy_tt.lib")
    raw = {"partition_types": {"th": {"hard": True, "contents": [core]}}}
    names = [n for n, _ in HP.lib_views(core, (tmp_path,))]
    assert names == ["lf_rphy_tt.lib", "lf_rphy_ff.lib"]
    errs, _ = HP.check_plan(raw, (tmp_path,))
    assert len(errs) == 1 and "lf_rphy_ff.lib" in errs[0] and "hold" in errs[0]
    (tmp_path / "lf_rphy_ff.lib").write_text(lib_text())
    errs, summ = HP.check_plan(raw, (tmp_path,))
    assert errs == [] and len(summ["th"]["libs"]) == 2
    # declaration errors (fail closed)
    bad = [({"hard": False, "contents": [core]}, "not hard"),
           ({"hard": True, "contents": [core, dict(core, inst="u_x")]}, "2 entries"),
           ({"hard": True, "contents": [core, dict(inst="u_pstn", module="m", status="new")]}, "not the only content"),
           ({"hard": True, "contents": [dict(core, lib=None)]}, "no lib"),
           ({"hard": True, "contents": [core], "ft_slots": [dict(name="f")]}, "ft slots")]
    for t, word in bad:
        _, e = HP.registered_types({"partition_types": {"th": t}})
        assert e and word in e[0], (word, e)
    # G0 wrapper: an ERROR (not a G0C WARN) with the type
    class P:
        pass
    P.raw = {"partition_types": {"th": {"hard": True, "contents": [dict(core, lib="missing_tt.lib")]}}}
    R = check.Report()
    check.check_registered_pins(P, R, tmp_path)
    assert [(i["level"], i["check"], i.get("type")) for i in R.items] == [("ERROR", "hard_pinreg", "th")]
    # no declaration: nothing
    assert HP.registered_types({"partition_types": {"th": {"hard": True, "contents": [dict(core, registered_pins=False)]}}}) == ({}, [])


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_bind_registered_hard_partition(tmp_path):
    """bind_tiny + a hard partition H holding one registered-pin macro lf_rphy (in from A1, out to S): with the
    declaration H has no ot_dp_st, its out epoch is the delivered reset level, the neighbours are byte-identical to
    the undeclared bind (they keep their stations), bind_verify PASS (one stage less per registered end), and a lib
    without hold arcs is refused."""
    src = tmp_path / "src"
    src.mkdir()
    for f in ("leaves.sv", "par.sv"):
        shutil.copy(EX / f, src / f)
    (src / "phy.sv").write_text(
        "module lf_rphy (input wire clk, input wire rst_n, input wire [7:0] i, output reg [7:0] o);\n"
        "    reg [7:0] r;\n    always @(posedge clk) begin r <= i; o <= ~r; end\nendmodule\n"
        "module lf_use (input wire clk, input wire [7:0] d, output reg [7:0] q);\n"
        "    always @(posedge clk) q <= d;\nendmodule\n")
    (src / "lf_rphy_tt.lib").write_text(lib_text())
    (src / "lf_bad_tt.lib").write_text(lib_text(hold=False))
    die = (EX / "die.v").read_text().replace(
        "  lf_sink snk", "  wire [7:0] po; wire [7:0] uq;\n  lf_rphy phy (.clk(ck), .rst_n(rs), .i(y1), .o(po));\n"
        "  lf_use use0 (.clk(ck), .d(po), .q(uq));\n  lf_sink snk")
    (src / "die.v").write_text(die)

    def plan(tag, **core_kw):
        p = json.loads((EX / "die_plan.json").read_text())
        a = p["asbuilt"]
        a["base"] = str(src)
        a["files"] = a["files"] + ["phy.sv"]
        a["map"]["parts"]["phy"] = "H"
        a["map"]["parts"]["use0"] = "S"
        p["partition_types"]["th"] = {"module": "bt_th", "hard": True, "reset": {"sync_stages": 2},
                                      "contents": [dict(inst="phy", module="lf_rphy", status="reuse", **core_kw)]}
        p["partitions"].append({"name": "H", "type": "th"})
        f = tmp_path / f"die_plan_{tag}.json"
        f.write_text(json.dumps(p))
        return f

    def run(f, out, *cmds):
        for c in cmds:
            rc = bind.main([c, str(f), "--out", str(out), "--mem", "4"])
            if rc:
                return rc
        return 0

    rep = lambda o: json.loads((o / "bind_report.json").read_text())  # noqa: E731
    o0, o1 = tmp_path / "o0", tmp_path / "o1"
    assert run(plan("plain"), o0, "elab", "bind") == 0, rep(o0)["errors"][:5]
    assert run(plan("reg", registered_pins=True, lib="lf_rphy_tt.lib"), o1, "elab", "bind", "verify") == 0, \
        rep(o1)["errors"][:5]
    r = rep(o1)
    v = json.loads((o1 / "verify_report.json").read_text())
    assert r["n_errors"] == 0 and v["verdict"] == "PASS", (r["errors"][:3], v["counts"], v["mismatches"][:3])
    assert r["registered_pins"]["H"]["stations_removed"] == 2 and r["registered_pins"]["H"]["station_bits_removed"] == 18
    th0, th1 = (o0 / "rtl" / "bt_th.sv").read_text(), (o1 / "rtl" / "bt_th.sv").read_text()
    assert th0.count("ot_dp_st") == 2 and "ot_reset_sync" in th0
    assert "ot_dp_st" not in th1 and "ot_reset_sync" not in th1 and "ot_dp_dly" not in th1
    assert "wire rst_n = arst_n;" in th1
    assert re.search(r"assign \w+ = \{rst_n, w_phy__o\};", th1), th1
    assert re.search(r"assign (\w+)_q = \1\[7:0\];", th1), th1
    # the neighbours keep their stations: every other generated file is byte-identical
    for f0 in sorted((o0 / "rtl").glob("*.sv")):
        if f0.name != "bt_th.sv":
            assert f0.read_text() == (o1 / "rtl" / f0.name).read_text(), f0.name
    # latency: bound stages unchanged (the macro pin register is the H-side stage); the trace expects one stage less
    lat = [b for b in json.loads((o1 / "bind_latency.json").read_text())["buses"] if "H" in (b["src"], b["dst"])]
    assert len(lat) == 2 and all(b["bound_stages"] == 2 and b["macro_pin_reg_ends"] for b in lat)
    s0, s1 = (json.loads((o / "bind_sinks.json").read_text()) for o in (o0, o1))
    assert s0["use0.d[0]"][2] == 2 and s1["use0.d[0]"][2] == 1 and s1["phy.i[3]"][2] == s0["phy.i[3]"][2] - 1
    # fail closed: a lib without hold arcs on the FDI inputs is refused
    o2 = tmp_path / "o2"
    run(plan("bad", registered_pins=True, lib="lf_bad_tt.lib"), o2, "elab", "bind")
    assert any("lib check FAIL" in e and "hold" in e for e in rep(o2)["errors"]), rep(o2)["errors"][:3]
