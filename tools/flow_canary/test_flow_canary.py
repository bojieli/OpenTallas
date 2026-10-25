"""flow_canary (FLOW-CANARY 2026-10-25) + reg_fanout_gate (COORD 10-25).
    python3 -m pytest -q tools/flow_canary/test_flow_canary.py"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "die_plan")]
import canary as C  # noqa: E402
import trigger as T  # noqa: E402
import reg_fanout_gate as RF  # noqa: E402

# one data bit a -> o through two face flops, plus a registered reset wavefront out rst_o_0
NET = r"""
module top(clk, arst_n, a, o, rst_o_0);
  input clk; input arst_n; input a; output o; output rst_o_0;
  wire q; wire _0_; wire r; wire rb;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q$_DFF_P_  (.CLK(clk), .D(a), .QN(q));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q$_DFF_P_  (.CLK(clk), .D(q), .QN(_0_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o));
  DFFHQNx1_ASAP7_75t_R \u_rrl_0.r$_DFF_P_  (.CLK(clk), .D(arst_n), .QN(rb));
  INVx3_ASAP7_75t_R _3_ (.A(rb), .Y(rst_o_0));
endmodule
"""


def test_face_cover_checks_rst_o(tmp_path):
    (tmp_path / "n.v").write_text(NET)
    ok = C.face_cover(tmp_path / "n.v", None)
    assert ok["verdict"] == "PASS" and ok["wave_ports"] == ["rst_o_0"] and ok["checked"] == 3
    # the 10-25 bug: insbuf left a kept BUF on the relay q net -> rst_o register net shared; main's SKIP_RE hid it
    bad = NET.replace("endmodule", "  BUFx2_ASAP7_75t_R _9_ (.A(rb), .Y(dangle));\nendmodule")
    (tmp_path / "b.v").write_text(bad)
    r = C.face_cover(tmp_path / "b.v", None)
    assert r["verdict"] == "FAIL" and "shared" in r["fails"]
    import face_guard
    assert face_guard.guard(bad)["verdict"] == "PASS"          # the masking this stage exists for


def _fan(n):
    loads = "\n".join(f"  NAND2x1_ASAP7_75t_R _l{i}_ (.A(q), .B(a), .Y(y{i}));" for i in range(n))
    return (f"module top(clk, arst_n, a);\n  input clk; input arst_n; input a;\n  wire q;\n"
            f"  DFFHQNx1_ASAP7_75t_R \\u_rep.q$_DFF_P_  (.CLK(clk), .D(a), .QN(q));\n{loads}\n"
            + "".join(f"  DFFASRHQNx1_ASAP7_75t_R \\u_s{i}.q  (.CLK(clk), .D(a), .RESETN(q), .SETN(a), .QN(z{i}));\n"
                      for i in range(100)) + "endmodule\n")


def test_reg_fanout_gate():
    r = RF.fanout(_fan(64))
    assert r["verdict"] == "PASS" and r["over"] == 0             # 64 data loads; 100 reset-pin loads not counted
    r = RF.fanout(_fan(65))
    assert r["verdict"] == "FAIL" and r["worst"][0]["loads"] == 65 and r["worst"][0]["regs"][0].startswith("u_rep.q")
    assert r["worst"][0]["ctrl_loads"] == 100


def test_reg_fanout_cli(tmp_path):
    (tmp_path / "n.v").write_text(_fan(70))
    assert RF.main([str(tmp_path / "n.v"), "--out", str(tmp_path / "r.json")]) == 1
    assert json.loads((tmp_path / "r.json").read_text())["verdict"] == "FAIL"
    (tmp_path / "x.v").write_text("module (")
    assert RF.main([str(tmp_path / "x.v")]) == 2                  # crash = NOT RUN, never a PASS


def test_run_kit_has_reg_fanout_gate():
    import gen_phys
    rk = gen_phys.RUN_KIT
    i_fg, i_rf, i_lec = rk.index("/work/face_guard.py"), rk.index("/work/reg_fanout_gate.py"), rk.index("/work/lec.py")
    assert i_fg < i_rf < i_lec and "FAIL_PREFLOOR reg_fanout" in rk and "rc=7" in rk
    assert 'with_name("reg_fanout_gate.py")' in (HERE.parent / "die_plan" / "gen_phys.py").read_text()


def test_parse_lint():
    log = "/work/t.sv:2: ERROR: Identifier `\\foo' is implicitly declared and `default_nettype is set to none.\n"
    r = C.parse_lint(log, 1)
    assert r["verdict"] == "FAIL" and r["implicit"] == ["foo"]
    r = C.parse_lint("Warning: Wire top.\\x is used but has no driver.\nEnd of script.\n", 0)
    assert r["verdict"] == "PASS" and r["n_undriven"] == 1


def test_lint_script(tmp_path):
    (tmp_path / "macros").mkdir()
    for f in ("m_tt.lib", "m_ff.lib", "m_ss.lib"):
        (tmp_path / "macros" / f).write_text("")
    (tmp_path / "config.mk").write_text("export VERILOG_FILES = /work/rtl/a.sv /work/rtl/b.sv\n")
    s = C.lint_script(tmp_path, "top")
    assert "-noautowire /work/rtl/a.sv" in s and "m_tt.lib" in s and "m_ff.lib" not in s and "m_ss.lib" not in s and "hierarchy -check -top top" in s


def test_signoff_vs_golden():
    so = dict(verdict="SIGNED", checks=dict(setup_tt=dict(wns_ps=10.0), hold_ff=dict(wns_ps=2.0)),
              corners=dict(tt=dict(parasitics="spef"), ff=dict(parasitics="spef")))
    g = dict(verdict="SIGNED", setup_tt_wns=18.24, hold_ff_wns=8.62)
    assert C.chk_signoff(so, g, 15)["verdict"] == "PASS"
    assert C.chk_signoff(dict(so, verdict="NOT SIGNED"), g, 15)["verdict"] == "FAIL"
    so2 = dict(so, verdict="NOT SIGNED", checks=dict(setup_tt=dict(wns_ps=-50.0), hold_ff=dict(wns_ps=-20.0)))
    assert C.chk_signoff(so2, dict(verdict="NOT SIGNED", setup_tt_wns=-27.2, hold_ff_wns=-20.85), 15)["verdict"] == "FAIL"
    assert C.chk_signoff(None, g, 15)["verdict"] == "NOT RUN"
    assert C.chk_signoff(so, None, 15)["why"].startswith("BASELINE")


def test_check_run_missing_evidence_fails(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "config.mk").write_text("export SET_RC_TCL = /work/setRC_rcx.tcl\n")
    (tmp_path / "canary_meta.json").write_text(json.dumps(dict(kit=str(kit), spec=dict(die="x", item="y"))))
    r = C.check_run(tmp_path)
    assert r["verdict"] == "FAIL" and "lint" in r["failing"] and "signoff" in r["failing"]
    assert r["stages"]["rc_file"]["verdict"] == "FAIL" and "LAYER_PARASITICS_FILE" in r["stages"]["rc_file"]["why"]


def test_check_run_rc_and_tcl_errors(tmp_path):
    kit = tmp_path / "kit"
    logs = kit / "run/logs/asap7/dp_y/base"
    logs.mkdir(parents=True)
    (kit / "run/results/asap7/dp_y/base").mkdir(parents=True)
    (kit / "config.mk").write_text("export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl\n")
    for f in ("3_3_place_gp.log", "5_1_grt.log"):
        (logs / f).write_text("source /work/setRC_rcx.tcl\n")
    (logs / "4_1_cts.log").write_text("source /work/setRC_rcx.tcl\nError: cts.tcl, 87 can't read \"la_d\": no such variable\n")
    (tmp_path / "canary_meta.json").write_text(json.dumps(dict(kit=str(kit), spec=dict(die="x", item="y"))))
    r = C.check_run(tmp_path)
    assert r["stages"]["rc_file"]["verdict"] == "PASS"
    assert r["stages"]["tcl_errors"]["verdict"] == "FAIL" and "la_d" in r["stages"]["tcl_errors"]["why"]
    (logs / "5_1_grt.log").write_text("source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\n")
    assert C.check_run(tmp_path)["stages"]["rc_file"]["verdict"] == "FAIL"


def test_spec_complete():
    specs, d = C.load_spec()
    assert set(specs) == {"s81", "s81_head", "qwen_compute", "qwen_kvsys", "hbm"}
    for c in specs.values():
        kv = dict(src="/S", gen="/G", run="/R", item=c["item"], top=c["top"], image="i", mem=c["mem_gb"], cpus=8)
        kv["kit"] = C.fmt(c["kit"], **kv)
        assert "{" not in C.fmt(c["gen"], **kv) + C.fmt(c["run"], **kv) + " ".join(C.fmt(c.get("prep", []), **kv))
        assert c["mem_gb"] >= 16
    assert T.touched(["tools/die_plan/gen_phys.py", "docs/x.md", "tools/die_plan/cts_post.tcl"], d["watch"]) == \
        ["tools/die_plan/cts_post.tcl", "tools/die_plan/gen_phys.py"]


def test_submit_dry(tmp_path):
    assert C.main(["submit", "--src", str(tmp_path), "--root", str(tmp_path / "runs"), "--dry", "--die", "s81"]) == 0
    run = next((tmp_path / "runs").iterdir())
    job = (run / "job.sh").read_text()
    assert "gen.py phys physical/die_plan/s81/die_plan.json" in job and "canary.py lint" in job and "canary.py check" in job
    assert (run / "canary.py").is_file() and (run / "reg_fanout_gate.py").is_file()
    assert T.live_dies(tmp_path / "runs") == {"s81"}
    # a live canary blocks the trigger (no checkout under it)
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path / "src")], check=True)
    assert T.main(["--src", str(tmp_path / "src"), "--root", str(tmp_path / "runs"), "--state", str(tmp_path / "st.json")]) == 2  # no origin: fetch fails, NOT RUN
