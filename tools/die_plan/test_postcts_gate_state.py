"""postcts_gate.tcl private corner state (PATH-QC 2026-10-25).

VMR vmr_readiness 10-25: the kit LAYER_PARASITICS_FILE (an RC-correlation wrapper) runs `foreach {l r c} {...}` at
global scope, so the gate's `c` became 1.62979E-01 and TT + FF both wrote postcts_gate_1.62979E-01.json: FF overwrote
the TT evidence.  The gate must capture corner / file tag / bound / tol before any external source and use only those.
The real script runs under tclsh with OpenROAD commands stubbed and the library selector call replaced by a receipt
stub (the selector itself is covered by test_timing_libs.py)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GATE = HERE / "postcts_gate.tcl"

STUBS = r"""
proc read_db {args} {}
proc read_sdc {args} {}
proc all_clocks {} { return {clk vclk} }
proc get_clocks {args} { return [lindex $args end] }
proc get_full_name {o} { return $o }
proc set_clock_latency {args} { set ::ot_test_latency [lrange $args 1 end] }
proc set_propagated_clock {args} {}
proc estimate_parasitics {args} {}
proc get_property {object property} {
  if {$property eq "sources"} { return [expr {$object eq "vclk" ? "" : "clock_source"}] }
  return 833
}
namespace eval sta { proc worst_slack_cmd {k} { return 1e-11 } }
"""

# A hostile RC file: clobbers every global name the gate used to read after sourcing it.
RC = "foreach {l r c} {M7 1.25096E-02 1.62979E-01} {}\nset C XX\nset bound 999\nset tol 0\n"
PINREG = ("proc ot_pinreg_set {} { return [dict create a pa b pb] }\n"
          "proc ot_pinreg_arr {p clk} { return [expr {$::env(OT_CORNER) eq \"FF\" ? 200.0 : 251.0}] }\n")


def _mock(text, work):
    lines = []
    for ln in text.splitlines():
        if re.match(r"^ot_lib_load ", ln):
            ln = 'set fp [open /work/postcts_gate_lib_receipt.json w]; close $fp'
        lines.append(ln)
    return STUBS + "\n".join(lines).replace("/work", str(work)) + "\n"


def _run(text, tmp_path, corner, policy=None, pinreg=PINREG, extra_env=None):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    (work / "constraint.sdc").write_text("")
    (work / "rc.tcl").write_text(RC)
    (work / "pinreg_measure.tcl").write_text(pinreg)
    # band_policy() runs from /work as in the kit (gen_phys copies core_clock_band.py); signoff is stubbed to a kit
    # without a hard-core latency contract (its own import chain is covered by the signoff tests)
    if (HERE / "core_clock_band.py").exists():   # HEAD src (older) has no core_clock_band.py
        shutil.copyfile(HERE / "core_clock_band.py", work / "core_clock_band.py")
    (work / "signoff.py").write_text("def hard_core_latency_contract(_kit):\n    return False\n")
    if policy is not None:
        (work / "master_slice.json").write_text(json.dumps({"core_tree": {"model_qualification": {"band_policy": policy}}}))
    script = tmp_path / "gate.tcl"
    script.write_text(_mock(text, work))
    env = {"PATH": "/usr/bin:/bin", "OT_CORNER": corner, "OT_VCLK_TT": "250", "OT_VCLK_FF": "202.5",
           "ODB": "x.odb", "LAYER_PARASITICS_FILE": str(work / "rc.tcl")}
    env.update(extra_env or {})
    return subprocess.run(["tclsh", str(script)], text=True, capture_output=True, env=env, cwd=tmp_path), work


@pytest.fixture(autouse=True)
def _tclsh():
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")


def test_tt_and_ff_write_distinct_files_with_their_own_bounds(tmp_path):
    for corner in ("TT", "FF"):
        r, work = _run(GATE.read_text(), tmp_path, corner)
        assert r.returncode == 0, r.stderr
    tt = json.loads((work / "postcts_gate_tt.json").read_text())
    ff = json.loads((work / "postcts_gate_ff.json").read_text())
    assert (tt["corner"], tt["bound_ps"], tt["tol_ps"], tt["pinreg_mean_ps"]) == ("TT", 250.0, 20.0, 251.0)
    assert (ff["corner"], ff["bound_ps"], ff["tol_ps"], ff["pinreg_mean_ps"]) == ("FF", 202.5, 20.0, 200.0)
    assert tt["verdict"] == ff["verdict"] == "PASS"
    assert not list(work.glob("postcts_gate_1.6*.json"))


def test_unknown_corner_rejected(tmp_path):
    r, _ = _run(GATE.read_text(), tmp_path, "tt")
    assert r.returncode != 0 and "OT_CORNER must be" in r.stderr


def test_pre_fix_script_loses_tt_evidence(tmp_path):
    """Control: the 20b4554a0f form shows the clobber (TT file never written, one numeric file shared)."""
    old = subprocess.run(["git", "-C", str(HERE), "show", "20b4554a0f:tools/die_plan/postcts_gate.tcl"],
                         text=True, capture_output=True)
    if old.returncode:
        pytest.skip("pre-fix revision not available")
    for corner in ("TT", "FF"):
        _, work = _run(old.stdout, tmp_path, corner)
    assert not (work / "postcts_gate_tt.json").exists()
    assert len(list(work.glob("postcts_gate_1.6*.json"))) == 1


# KW-FIX-4 / OWNER 11-03 (only sign-off blocks): a measured band miss under the "gate" policy is ADVISORY (verdict PASS,
# named in the log line); OT_POSTCTS_BAND_GATE=1 restores the blocking FAIL.
@pytest.mark.parametrize("policy,band_gate,verdict,band", [(None,None,"PASS","ADVISORY"),("gate",None,"PASS","ADVISORY"),
                                                           ("info",None,"PASS","INFO"),(None,"1","FAIL","FAIL"),
                                                           ("gate","1","FAIL","FAIL"),("info","1","PASS","INFO")])
def test_explicit_target_policy_preserves_measured_miss(tmp_path, policy, band_gate, verdict, band):
    extra = {} if band_gate is None else {"OT_POSTCTS_BAND_GATE": band_gate}
    r, work = _run(GATE.read_text(), tmp_path, "TT", policy, PINREG.replace("251.0", "196.56"), extra)
    assert r.returncode == 0, r.stderr
    d = json.loads((work / "postcts_gate_tt.json").read_text())
    assert d["verdict"] == verdict and d["band_verdict"] == band
    assert d["pinreg_mean_ps"] == 196.56 and d["dev_ps"] == 53.44
    line = [l for l in r.stdout.splitlines() if l.startswith("OT_POSTCTS_GATE ")][-1]
    assert line.endswith(" " + verdict) and ("ADVISORY band dev > tol" in line) == (band == "ADVISORY")
    assert ("FAIL" in line) == (verdict == "FAIL")  # run_kit.sh stops on 'OT_POSTCTS_GATE.*FAIL'


def test_advisory_line_still_parsed_by_canary_baseline(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("canary_baseline", HERE.parent / "flow_canary/baseline.py")
    if spec is None or not (HERE.parent / "flow_canary/baseline.py").is_file():
        pytest.skip("flow_canary not checked out")
    bl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bl)
    r, _ = _run(GATE.read_text(), tmp_path, "TT", None, PINREG.replace("251.0", "196.56"))
    assert bl.GATE_RE.findall(r.stdout) == [("TT", "196.56", "250.00", "PASS")]


def test_info_cannot_accept_empty_pinregister_set(tmp_path):
    r, work = _run(GATE.read_text(), tmp_path, "TT", "info", "proc ot_pinreg_set {} { return {} }\n")
    assert r.returncode == 0, r.stderr
    assert json.loads((work / "postcts_gate_tt.json").read_text())["verdict"] == "FAIL"


def test_unknown_band_policy_fails_closed(tmp_path):
    r, _ = _run(GATE.read_text(), tmp_path, "TT", "waive")
    assert r.returncode != 0 and "invalid model_qualification" in r.stderr


def test_multiple_real_clocks_keep_corner_virtual_binding(tmp_path):
    text = GATE.read_text()
    # Retain both actual source clocks and prove FF reference is bound exactly.
    text = text.replace('set ot_pg_C $C', 'rename all_clocks _old_all_clocks\nproc all_clocks {} {return {clk fclk_in_0 fclk_in_1 vclk}}\nset ot_pg_C $C')
    text += '\nif {$::ot_test_latency ne "202.5 vclk"} {error "wrong FF virtual reference: $::ot_test_latency"}\n'
    r, _ = _run(text, tmp_path, "FF")
    assert r.returncode == 0, r.stderr


def test_ambiguous_virtual_clocks_fail_closed(tmp_path):
    text = GATE.read_text().replace('set ot_pg_C $C', 'rename all_clocks _old_all_clocks\nproc all_clocks {} {return {clk fclk vclk vclk}}\nset ot_pg_C $C')
    r, _ = _run(text, tmp_path, "FF")
    assert r.returncode != 0 and 'exactly one source-less' in r.stderr
