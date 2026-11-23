"""TYPE-DEFINES-1123: per-type verilog_defines in the bind (tools/die_plan/type_define_effect.py).

Static classification (no Yosys) plus the bind_tiny die end to end (Yosys elab -> bind): a define read by the dissolved
parent `par` is realized for the type that requests it, a define that also changes another type fails the bind, and a
define nothing reads fails the bind."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import type_define_effect as TDE  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


def _plan(types):
    return {"partition_types": {t: {"verilog_defines": d} for t, d in types.items()}}


def test_classify_body_leaf_cohosted_dead_diewide(tmp_path):
    body = tmp_path / "par.sv"
    body.write_text("module par();\n`ifdef OT_BODY\n lf #(.K(2)) u();\n`else\n lf u();\n`endif\nendmodule\n"
                    "module cohost(input wire a, output wire y);\n`ifdef OT_COHOST\n assign y = ~a;\n`else\n"
                    " assign y = a;\n`endif\nendmodule\n")
    leaf = tmp_path / "lf.sv"
    leaf.write_text("module lf #(parameter K=1)(input wire a,\n`ifdef OT_PORT\n input wire b,\n`endif\n"
                    " output wire y);\n`ifdef OT_LEAF\n assign y = a;\n`endif\nendmodule\n")
    plan = _plan({"ta": ["OT_BODY", "OT_COHOST", "OT_LEAF", "OT_PORT", "OT_NOPE", "OT_DIE"]})
    ab = {"top": "tdie", "dissolve": ["par"], "defines": ["OT_DIE"]}
    rows = {r["define"]: r for r in TDE.classify(plan, ab, {"tops": [], "full": [str(body)], "lib": [str(leaf)]},
                                                 [str(tmp_path)])}
    assert rows["OT_BODY"]["verdict"] == "BIND_IGNORED"
    assert rows["OT_COHOST"]["verdict"] == "KIT"          # read inside a co-hosted leaf, not the kept parent
    assert rows["OT_LEAF"]["verdict"] == "KIT" and not rows["OT_LEAF"]["ports"]
    assert rows["OT_PORT"]["verdict"] == "KIT" and rows["OT_PORT"]["ports"]
    assert rows["OT_NOPE"]["verdict"] == "DEAD"
    assert rows["OT_DIE"]["verdict"] == "DIE_WIDE"
    bad = {r["define"] for r in TDE.failures(list(rows.values()))}
    assert bad == {"OT_BODY", "OT_NOPE"}
    assert {r["define"] for r in TDE.failures(list(rows.values()), realized={("ta", "OT_BODY")})} == {"OT_NOPE"}


def test_classify_not_selected_when_preferred_copy_lacks_hunk(tmp_path):
    (tmp_path / "rtl").mkdir()
    edited = tmp_path / "rtl" / "crr.sv"
    edited.write_text("module crr #(parameter integer PRE = `ifdef OT_PRE2 2 `else 0 `endif)(input wire d);\nendmodule\n")
    portfix = tmp_path / "portfix_crr.sv"
    portfix.write_text("module crr #(parameter integer PRE = 0)(input wire d);\nendmodule\n")
    rows = TDE.classify(_plan({"leaf": ["OT_PRE2"]}), {"top": "t"}, {"tops": [], "full": [], "lib": [str(portfix)]},
                        [str(tmp_path / "rtl")], prefer=[str(portfix)])
    assert rows[0]["verdict"] == "NOT_SELECTED"
    assert rows[0]["shadowed_readers"][0]["selected"]["crr"] == str(portfix)
    assert TDE.failures(rows) == rows


# ------------------------------------------------------------------------------------------------ bind_tiny end to end
def _tiny(tmp_path, types_defs, die_ifdef=False):
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    par = (src / "par.sv").read_text()
    par = par.replace("lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n    lf_b u_b",
                      "`ifdef OT_TDX\n    lf_a #(.ID(K + 8)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n`else\n"
                      "    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n`endif\n    lf_b u_b", 1)
    assert "OT_TDX" in par
    (src / "par.sv").write_text(par)
    if die_ifdef:
        die = (src / "die.v").read_text()
        die = die.replace("lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));",
                          "`ifdef OT_TDX\n  lf_sink snk (.clk(ck), .flt(fo), .d0(y1), .d1(y0), .q(sq));\n`else\n"
                          "  lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));\n`endif")
        (src / "die.v").write_text(die)
    p = json.loads((src / "die_plan.json").read_text())
    p["asbuilt"]["base"] = str(src)
    for t, d in types_defs.items():
        p["partition_types"][t]["verilog_defines"] = d
    f = src / "die_plan_td.json"
    f.write_text(json.dumps(p))
    return f


def _run(plan, out, *cmds):
    import bind
    for c in cmds:
        args = [c, str(plan), "--out", str(out), "--mem", "4"]
        if c == "bind":
            args.append("--strict")
        rc = bind.main(args)
        if rc:
            return rc
    return 0


@needs_yosys
def test_tiny_body_define_is_realized_for_its_type(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "on")
    out = tmp_path / "o"
    assert _run(_tiny(tmp_path, {"ta": ["OT_TDX"]}), out, "elab", "bind") == 0
    rec = json.loads((out / "type_defines.json").read_text())
    assert rec["verdict"] == "REALIZED" and rec["added"] == ["OT_TDX"]
    assert rec["realized"] == [["ta", "OT_TDX"]] and set(rec["changed_by_type"]) == {"ta"}
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert re.search(r"\.P_u_a_ID\(9\)", top) and re.search(r"\.P_u_a_ID\(10\)", top)
    assert (out / "asbuilt.define_off.json").is_file()
    assert json.loads((out / "bind_report.json").read_text())["n_errors"] == 0


@needs_yosys
def test_tiny_define_that_changes_another_type_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "on")
    out = tmp_path / "o"
    rc = _run(_tiny(tmp_path, {"ta": ["OT_TDX"]}, die_ifdef=True), out, "elab", "bind")
    rec = json.loads((out / "type_defines.json").read_text())
    assert rec["verdict"] == "CONFLICT" and "ts" in rec["outside"]
    errs = json.loads((out / "bind_report.json").read_text())["errors"]
    assert rc != 0 and any(e.startswith("TYPE_DEFINE_CONFLICT") for e in errs)
    assert any(e.startswith("TYPE_DEFINE_NOEFFECT ta: OT_TDX BIND_IGNORED") for e in errs)


@needs_yosys
def test_tiny_dead_define_fails_and_warn_mode_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "on")
    out = tmp_path / "o"
    plan = _tiny(tmp_path, {"ts": ["OT_NOTHING_READS_THIS"]})
    rc = _run(plan, out, "elab", "bind")
    errs = json.loads((out / "bind_report.json").read_text())["errors"]
    assert rc != 0 and any("TYPE_DEFINE_NOEFFECT ts: OT_NOTHING_READS_THIS DEAD" in e for e in errs)
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "warn")
    out2 = tmp_path / "o2"
    assert _run(plan, out2, "elab", "bind") == 0


@needs_yosys
def test_tiny_no_defines_writes_none_needed(tmp_path):
    out = tmp_path / "o"
    assert _run(_tiny(tmp_path, {}), out, "elab", "bind") == 0
    assert json.loads((out / "type_defines.json").read_text())["verdict"] == "NONE_NEEDED"
    assert not (out / TDE.VARIANT_DIR).exists()

@needs_yosys
def test_tiny_default_mode_reports_and_preserves_define_off(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_BIND_TYPE_DEFINES", raising=False)
    out = tmp_path / "o"
    assert _run(_tiny(tmp_path, {"ta": ["OT_TDX"]}), out, "elab", "bind") == 0
    rec = json.loads((out / "type_defines.json").read_text())
    assert rec["verdict"] == "BIND_IGNORED"
    assert not (out / TDE.VARIANT_DIR).exists()
    report = json.loads((out / "bind_report.json").read_text())
    assert any("TYPE_DEFINE_NOEFFECT ta: OT_TDX" in w for w in report["warnings"])
