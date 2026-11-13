"""KW-FIX-44 PLACE-NOCONVERGE gate: gp_noconverge.py --gate verdicts, the PRE_RESIZE Tcl hook, gen_phys install,\nand agreement with the DIE-HBM-97 classifier (kit_wave.gpl_cap_noconverge)."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gp_noconverge as G

CAP = "[WARNING GPL-1010] GPL reached the maximum number of iterations for nesterov 5000. Placement may have failed to converge.\n"
TAIL = "[INFO GPL-1014] Final placement area: 19569.01 (+0.00%)\n"


def log(last, cap=True, n=50):
    rows = "".join(f"     {10 * (i + 1):5d} |   {0.9 - (0.9 - last) * i / (n - 1):.4f} |  6.43e+07 |   -0.04% |  2.67e+11 |      \n"
                   for i in range(n))
    return "[INFO GPL-0084] ---- Execute Nesterov Global Placement.\n" + rows + (CAP if cap else "") + TAIL


def test_kv_line_vc_shape_stops():
    v, why = G.gate(log(0.3704))
    assert v == "STOP" and why.startswith("PLACE-NOCONVERGE: ") and "0.3704 > 0.1" in why and "5000" in why


def test_converged_run_passes():
    assert G.gate(log(0.0990, cap=False))[0] == "OK"


def test_cap_at_or_below_limit_passes():
    assert G.gate(log(0.1000))[0] == "OK"
    assert G.gate(log(0.0950))[0] == "OK"


def test_rows_after_the_cap_line_are_ignored():
    # only the overflow at the cap decides; a later pass's rows do not mask it
    t = log(0.37) + "     10 |   0.0500 |  6.4e+07 |  0% |  1e+11 |\n"
    assert G.gate(t)[0] == "STOP"


def test_threshold_is_configurable():
    assert G.gate(log(0.37), overflow=0.4)[0] == "OK"


def test_cli_exit_codes_and_marker(tmp_path):
    lg, mk = tmp_path / "3_3_place_gp.log", tmp_path / "FAIL_PLACE_NOCONVERGE"
    lg.write_text(log(0.37))
    assert G.main(["--gate", str(lg), "--marker", str(mk)]) == 3
    assert mk.read_text().startswith("PLACE-NOCONVERGE: global placement stopped")
    lg.write_text(log(0.05, cap=False))
    assert G.main(["--gate", str(lg)]) == 0
    assert G.main(["--gate", str(tmp_path / "missing.log")]) == 0


def run_hook(kit, env):
    """a script file, as OpenROAD sources the hook: a Tcl error ends it (stdin tclsh would go on to the next line)"""
    drv = kit / "drv.tcl"
    drv.write_text(f"source {kit}/gp_noconverge_gate.tcl\nputs HOOK_DONE\n")
    return subprocess.run(["tclsh", str(drv)], text=True, capture_output=True, env=env)


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")
@pytest.mark.parametrize("last,cap,env,stops", [(0.37, True, {}, True), (0.05, False, {}, False),
                                                (0.37, True, {"OT_GPL_NOCONV": "0"}, False),
                                                (0.37, True, {"OT_GPL_NOCONV_OVERFLOW": "0.5"}, False)])
def test_tcl_hook(tmp_path, last, cap, env, stops):
    kit = tmp_path / "kit"; logs = kit / "run" / "logs"; logs.mkdir(parents=True)
    shutil.copy(HERE.parent / "die_plan" / "gp_noconverge_gate.tcl", kit)
    shutil.copy(HERE / "gp_noconverge.py", kit)
    (logs / "3_3_place_gp.log").write_text(log(last, cap))
    e = dict(os.environ, LOG_DIR=str(logs), **env)
    r = run_hook(kit, e)
    out = r.stdout + r.stderr
    assert ("HOOK_DONE" not in out) == stops, out
    assert (kit / "FAIL_PLACE_NOCONVERGE").exists() == stops
    if stops:
        assert "PLACE-NOCONVERGE: global placement stopped" in out


def test_tcl_hook_without_log_is_inert(tmp_path):
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    kit = tmp_path / "kit"; kit.mkdir()
    shutil.copy(HERE.parent / "die_plan" / "gp_noconverge_gate.tcl", kit)
    r = run_hook(kit, dict(os.environ, LOG_DIR=str(kit / "none")))
    assert "HOOK_DONE" in r.stdout and "NOT RUN" in r.stdout


def test_restarted_passes_first_capped_pass_above_limit_decides():
    ok_pass = log(0.05)                     # capped at 0.05: not this class
    assert G.gate(ok_pass)[0] == "OK"
    assert G.gate(ok_pass + log(0.30))[0] == "STOP"
    assert G.gate(log(0.30) + log(0.05, cap=False))[0] == "STOP"


@pytest.mark.parametrize("text", [log(0.3704), log(0.0990, cap=False), log(0.1000), log(0.05) + log(0.30),
                                  log(0.30) + log(0.05, cap=False), "", "no table\n" + CAP])
def test_gate_agrees_with_the_wave_classifier(text):
    """the stop (this gate) and the label (kit_wave.gpl_cap_noconverge, DIE-HBM-97) read a log the same way"""
    import kit_wave as KW
    assert (G.gate(text)[0] == "STOP") == bool(KW.gpl_cap_noconverge(text))


def test_stopped_run_still_carries_the_classifier_evidence(tmp_path):
    """the gate stops at 3_4, so 3_3_place_gp.log is complete: the wave/autopilot probes still see GPL-1010 + its row"""
    import kit_wave as KW
    assert KW.gpl_cap_noconverge(log(0.37)).startswith("GPL-1010 Nesterov pass cap hit at iteration 500 with overflow 0.370")


def test_gen_installs_the_gate_once(tmp_path):
    sys.path.insert(0, str(HERE.parent / "die_plan"))
    import gen_phys
    got = gen_phys.install_gp_noconverge_gate(tmp_path, ["export PLACE_DENSITY = 0.5"])
    assert got[:2] == [
        "# KW-FIX-44 PLACE-NOCONVERGE: GPL at its iteration cap with overflow > 0.1 ends the run before resize",
        "export PRE_RESIZE_TCL = /work/gp_noconverge_gate.tcl"]
    # R-FLOW 11-13 (RULEBOOK-1113): the same hook carries the default place fanout limit (gen env OT_PLACE_MAX_FANOUT wins)
    assert [c for c in got[2:] if c.startswith("export ")] == [
        "export OT_PLACE_MAX_FANOUT = " + (os.environ.get("OT_PLACE_MAX_FANOUT") or "32")] or os.environ.get("OT_RFLOW") == "0"
    assert (tmp_path / "gp_noconverge_gate.tcl").is_file() and (tmp_path / "gp_noconverge.py").is_file()
    other = tmp_path / "o"; other.mkdir()
    assert gen_phys.install_gp_noconverge_gate(other, ["export PRE_RESIZE_TCL = /work/mine.tcl"]) == []
    assert not (other / "gp_noconverge_gate.tcl").exists()
