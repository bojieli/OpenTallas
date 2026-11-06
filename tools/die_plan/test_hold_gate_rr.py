"""KW-FIX-17 11-05 (COORD 16:2x class): the post-CTS hold_gate.tcl structural stop counts register-to-register FF
hold only; in/out-port paths beyond the stop are an ADVISORY line (die STA checks them).  OT_HOLD_STOP_SCOPE=all
restores the all-path stop; the split fails closed when unavailable.
    python3 -m pytest -q tools/die_plan/test_hold_gate_rr.py"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
from test_hold_gate_ring import STUBS  # noqa: E402


def _run(tmp_path, wns, n, rr=None, scope=None, reports=False, in_min=-90):
    """rr: list of reg->reg path slacks returned by find_timing_paths; None = commands missing (split unavailable)."""
    if shutil.which("tclsh") is None:
        pytest.skip("no tclsh")
    stubs = STUBS.replace("proc sta::worst_slack_cmd {args} {return 1}", f"proc sta::worst_slack_cmd {{args}} {{return {wns}}}")
    stubs = stubs.replace("proc sta::endpoint_violation_count {args} {return 0}",
                          f"proc sta::endpoint_violation_count {{args}} {{return {n}}}")
    if rr is not None:
        paths = " ".join(f"P{i}" for i in range(len(rr)))
        slk = " ".join(f"P{i} {s}" for i, s in enumerate(rr))
        stubs += ("proc all_registers {args} { puts \"REG $args\"; return {r1 r2} }\n"
                  f"proc find_timing_paths {{args}} {{ puts \"FTP $args\"; return {{{paths}}} }}\n"
                  f"array set ::rr_slack {{{slk}}}\n"
                  "rename get_property ot_gp0\n"
                  "proc get_property {o k} { if {$k eq \"slack\"} { return $::rr_slack($o) }; return [ot_gp0 $o $k] }\n")
    (tmp_path / "hold_gate.tcl").write_text(stubs + (HERE / "hold_gate.tcl").read_text())
    env = dict(os.environ)
    for k in ("OT_HOLD_IN_MIN", "OT_TAP_WINDOW", "OT_HOLD_PREROUTE_STOP", "OT_HOLD_STOP_PS", "OT_HOLD_STOP_SCOPE",
              "REPORTS_DIR"):
        env.pop(k, None)
    env["OT_HOLD_IN_MIN"] = str(in_min)
    if scope is not None:
        env["OT_HOLD_STOP_SCOPE"] = scope
    if reports:
        (tmp_path / "rep").mkdir()
        env["REPORTS_DIR"] = str(tmp_path / "rep")
    return subprocess.run(["tclsh", str(tmp_path / "hold_gate.tcl")], capture_output=True, text=True, env=env)


def test_port_paths_beyond_stop_do_not_stop_when_reg2reg_ok(tmp_path):
    # hd_ctl_n shape: all-path -281.50 / 1175 on the -250 stop (in_min -90), reg->reg well inside
    r = _run(tmp_path, -281.50, 1175, rr=[-73.8, -12.0, 5.0], reports=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ("OT_HOLD_PORT ADVISORY stage=post_cts: FF hold ws -281.50 ps over 1175 endpoints includes in/out-port paths; "
            "register-to-register ws -73.80 over 2 endpoints; the structural stop -250.0") in r.stdout
    assert "OT_HOLD_GATE FAIL" not in r.stdout
    assert "OT_HOLD_GATE INFO FF wns_ps -281.50 endpoints 1175" in r.stdout
    assert "ot_hold_port_advisory_post_cts.rpt" in os.listdir(tmp_path / "rep")
    ftp = [ln for ln in r.stdout.splitlines() if ln.startswith("FTP")][0]
    assert "-path_delay min" in ftp and "-slack_max 0" in ftp


def test_reg2reg_beyond_stop_still_stops(tmp_path):
    r = _run(tmp_path, -281.50, 1175, rr=[-260.0, -10.0])
    assert r.returncode != 0
    assert "OT_HOLD_GATE FAIL FF wns_ps -281.50 endpoints 1175" in r.stdout
    assert "ADVISORY" not in r.stdout


def test_no_failing_reg2reg_paths_proceeds(tmp_path):
    r = _run(tmp_path, -300.0, 40, rr=[], reports=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "register-to-register ws - over 0 endpoints" in r.stdout


def test_scope_all_restores_all_path_stop(tmp_path):
    r = _run(tmp_path, -281.50, 1175, rr=[-73.8], scope="all")
    assert r.returncode != 0 and "OT_HOLD_GATE FAIL" in r.stdout
    assert "FTP" not in r.stdout


def test_split_unavailable_fails_closed(tmp_path):
    r = _run(tmp_path, -281.50, 1175, rr=None)
    assert r.returncode != 0
    assert "register-to-register split unavailable" in r.stdout and "OT_HOLD_GATE FAIL" in r.stdout


def test_split_not_run_above_stop(tmp_path):
    r = _run(tmp_path, -180.0, 50, rr=[-300.0])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FTP" not in r.stdout and "ADVISORY" not in r.stdout
