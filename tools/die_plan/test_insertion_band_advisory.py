"""KW-FIX-4/BAND 11-03 (OWNER 19:12, all dies): the in-flow per-corner clock-insertion window is ADVISORY.

  * run_kit_hbm.sh (HBM cores) and gen_phys RUN_KIT (die_plan kits): a failing postcts_gate.tcl verdict prints
    OT_POSTCTS_ADVISORY, writes no FAIL_POSTCTS and leaves rc 0; 'export OT_POSTCTS_BAND_GATE = 1' restores the stop.
  * vclk_measured_hold.tcl (GRT measured FF reference): an out-of-band mean binds anyway, writes
    vclk_measured_band.json, no 'fix the clock' error unless OT_POSTCTS_BAND_GATE=1.
  * signoff.py records the band as signoff.json insertion_band (information only).
  * OT_HOLD_GATE structural hold screen lines are byte-identical.
    python3 -m pytest -q tools/die_plan/test_insertion_band_advisory.py"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import signoff  # noqa: E402

HBM_RUN = ROOT / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh"


def _snippet(text, start, end):
    """the gate block of a runner's docker 'bash -lc \"...\"' string, unescaped to plain bash."""
    i = text.index(start)
    j = text.index(end, i) + len(end)
    s = text[i:j]
    return s.replace("\\$", "$").replace('\\"', '"').replace(" \\\n", "\n")


def _run(snippet, tmp, verdict, band_gate=False):
    work = tmp / "work"
    work.mkdir()
    (work / "config.mk").write_text("export OT_VCLK_TT = 250\n" + ("export OT_POSTCTS_BAND_GATE = 1\n" if band_gate else ""))
    bind = tmp / "bin"
    bind.mkdir()
    (bind / "openroad").write_text(
        "#!/bin/bash\necho \"OT_POSTCTS_GATE $OT_CORNER (global_routing) pinreg n 10 mean 275.01 bound 250.00 dev 25.01 "
        f"tol 20.0 setup_est 1 hold_est 1 {verdict}\"\necho \"BG=$OT_POSTCTS_BAND_GATE\" >> {work}/env.log\nexit 0\n")
    (bind / "openroad").chmod(0o755)
    body = snippet.replace("/work", str(work))
    if body.rstrip().endswith("fi; fi; fi;"):        # gen_phys: the block also closes the enclosing GOAL=route 'if'
        body = "if true; then\n" + body
    script = f"set -u\nrc=0; O5=x.odb\n{body}\necho RC=$rc\n"
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env=dict(os.environ, PATH=f"{bind}:{os.environ['PATH']}"))
    assert r.returncode == 0, r.stderr
    return r.stdout, work


HBM_START = "    BG=\\$(grep -c '^export OT_POSTCTS_BAND_GATE = 1' /work/config.mk); rm -f /work/postcts_advisory.log;"
HBM_END = "band recorded in signoff.json insertion_band)\\\" | tee -a /work/postcts_advisory.log; fi; fi; done;"
GP_END = "| tee -a /work/postcts_advisory.log; fi; fi; fi;"


@pytest.mark.parametrize("runner", ["hbm", "gen_phys"])
def test_failing_insertion_gate_is_advisory_and_flow_continues(tmp_path, runner):
    text, end = (HBM_RUN.read_text(), HBM_END) if runner == "hbm" else (gen_phys.RUN_KIT, GP_END)
    out, work = _run(_snippet(text, HBM_START, end), tmp_path, "FAIL")
    assert "RC=0" in out
    assert not (work / "FAIL_POSTCTS").exists()
    adv = (work / "postcts_advisory.log").read_text()
    assert "OT_POSTCTS_ADVISORY" in adv and "TT" in adv and "FF" in adv
    assert set((work / "env.log").read_text().split()) == {"BG=0"}     # postcts_gate.tcl sees the advisory policy


@pytest.mark.parametrize("runner", ["hbm", "gen_phys"])
def test_explicit_band_gate_restores_the_stop(tmp_path, runner):
    text, end = (HBM_RUN.read_text(), HBM_END) if runner == "hbm" else (gen_phys.RUN_KIT, GP_END)
    out, work = _run(_snippet(text, HBM_START, end), tmp_path, "FAIL", band_gate=True)
    assert "RC=6" in out
    assert "insertion gate" in (work / "FAIL_POSTCTS").read_text()
    assert set((work / "env.log").read_text().split()) == {"BG=1"}


@pytest.mark.parametrize("runner", ["hbm", "gen_phys"])
def test_passing_gate_unchanged(tmp_path, runner):
    text, end = (HBM_RUN.read_text(), HBM_END) if runner == "hbm" else (gen_phys.RUN_KIT, GP_END)
    out, work = _run(_snippet(text, HBM_START, end), tmp_path, "PASS")
    assert "RC=0" in out and not (work / "FAIL_POSTCTS").exists() and not (work / "postcts_advisory.log").exists()


def test_hold_gate_screen_unchanged():
    """OT_HOLD_GATE stays a stop exactly as before (rc 4, FAIL_POSTCTS) in both runners."""
    assert ("if [ \\$hgrc != 0 ] || ! grep -qE 'OT_HOLD_GATE (PASS|INFO)' /work/hold_gate.log; then grep OT_HOLD_GATE "
            "/work/hold_gate.log | sed 's/^/FAIL_POSTCTS /' | tee /work/FAIL_POSTCTS; rc=4; fi; fi; fi;") in HBM_RUN.read_text()
    assert ("if [ \\$rc != 0 ]; then { grep -h 'OT_HOLD_GATE FAIL' /work/hold_gate.log || echo 'NOT RUN (no OT_HOLD_GATE "
            "verdict, see hold_gate.log)'; } | sed 's/^/FAIL_POSTCTS FF structural hold gate: /' | tee -a /work/FAIL_POSTCTS; "
            "rc=4; fi; fi; fi;") in gen_phys.RUN_KIT


TCL_STUBS = r"""
proc all_clocks {} { return {vclk} }
proc get_property {o k} { return {} }
proc get_full_name {o} { return $o }
proc estimate_parasitics {args} {}
proc set_clock_latency {args} { set ::bound $args }
source $::env(VMH)
proc ot_vmh_reference {} { return {rebind 202.5 40} }
proc ot_vmh_pinreg_mean {} { return [list $::env(MEAN) 100 0 1] }
if {[catch {ot_vclk_measured_bind} m]} { puts "ERR $m"; exit 3 }
puts "BOUND $::bound"
"""


def _tcl(tmp, mean, gate=None):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    shutil.copyfile(HERE / "vclk_measured_hold.tcl", tmp / "vclk_measured_hold.tcl")
    (tmp / "t.tcl").write_text(TCL_STUBS)
    env = dict(os.environ, VMH=str(tmp / "vclk_measured_hold.tcl"), MEAN=str(mean))
    env.pop("OT_POSTCTS_BAND_GATE", None)
    if gate:
        env["OT_POSTCTS_BAND_GATE"] = gate
    return subprocess.run(["tclsh", str(tmp / "t.tcl")], capture_output=True, text=True, env=env)


def test_grt_measured_band_advisory_binds_and_records(tmp_path):
    r = _tcl(tmp_path, 260.0)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fix the clock" not in r.stdout and "OT_VCLK_MEASURED_BAND FF mean 260.000" in r.stdout and "ADVISORY" in r.stdout
    assert "BOUND -source 260.0 vclk" in r.stdout
    d = json.loads((tmp_path / "vclk_measured_band.json").read_text())
    assert d["band_verdict"] == "ADVISORY" and d["bound_ps"] == 202.5 and d["tol_ps"] == 40 and abs(d["dev_ps"] - 57.5) < 1e-6


def test_grt_measured_band_in_window_and_opt_in_stop(tmp_path):
    (tmp_path / "a").mkdir()
    r = _tcl(tmp_path / "a", 210.0)
    assert r.returncode == 0 and json.loads((tmp_path / "a/vclk_measured_band.json").read_text())["band_verdict"] == "PASS"
    (tmp_path / "b").mkdir()
    r = _tcl(tmp_path / "b", 260.0, gate="1")
    assert r.returncode == 3 and "sign-off band FAIL; fix the clock, not the hold" in r.stdout
    assert json.loads((tmp_path / "b/vclk_measured_band.json").read_text())["band_verdict"] == "FAIL"


def test_signoff_records_insertion_band(tmp_path):
    assert signoff.insertion_band_record(tmp_path) is None
    (tmp_path / "postcts_gate_tt.json").write_text(json.dumps(dict(
        corner="TT", pinreg_n=1219, pinreg_mean_ps=275.01, pinreg_min_ps=231.91, pinreg_max_ps=290.27, bound_ps=250.0,
        dev_ps=25.01, tol_ps=20.0, setup_wns_est_ps=20.8, hold_wns_est_ps=2.23, parasitics="global_routing",
        verdict="PASS", band_policy="gate", band_verdict="ADVISORY")))
    (tmp_path / "postcts_gate_ff.json").write_text(json.dumps(dict(
        corner="FF", pinreg_n=1219, pinreg_mean_ps=210.0, bound_ps=202.5, dev_ps=7.5, tol_ps=20.0, verdict="PASS",
        band_verdict="PASS")))
    b = signoff.insertion_band_record(tmp_path)
    assert b["verdict"] == "ADVISORY" and b["outside"] == ["tt"]
    assert b["corners"]["tt"]["window_ps"] == [230.0, 270.0] and b["corners"]["tt"]["mean_ps"] == 275.01
    assert b["corners"]["ff"]["in_window"] is True
    (tmp_path / "vclk_measured_band.json").write_text(json.dumps(dict(band_verdict="ADVISORY", pinreg_mean_ps=260.0)))
    b = signoff.insertion_band_record(tmp_path)
    assert b["outside"] == ["tt", "grt_ff"] and b["grt_measured_ff"]["pinreg_mean_ps"] == 260.0
    json.dumps(b)


def test_signoff_band_is_information_only():
    src = (HERE / "signoff.py").read_text()
    ev = src[src.index("def evaluate(rec"):src.index("\ndef ", src.index("def evaluate(rec") + 10)]
    assert "insertion_band\"" not in ev and "insertion_band_record" not in ev
    i = src.index("band = insertion_band_record(")
    assert src.rindex("evaluate(rec, a.insertion_target)", 0, i) > src.rindex("\ndef ", 0, i)   # after the verdict
