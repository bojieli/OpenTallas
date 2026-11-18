"""WAVE-FLOW-R2 11-17 (COORD lever 6): tap_insertion.tcl prints one OT_TAP_INSERTION line per tap, advisory, wired into cts_post.tcl and the kit file list."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = HERE / "tap_insertion.tcl"


def run(prelude, env=None):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.tcl"
        p.write_text(prelude + "\nsource " + str(TCL) + "\nputs END_OK\n")
        e = {"PATH": "/usr/bin:/bin"}
        e.update(env or {})
        return subprocess.run([tclsh, str(p)], capture_output=True, text=True, env=e)


def test_one_line_per_tap():
    r = run('proc tb_measure {est} { return [dict create clk_t0 {200.0 150.0 212.5 40 bt0} clk_t1 {230.0 100.0 260.0 1700 bt1}] }')
    assert r.returncode == 0 and "END_OK" in r.stdout, r.stderr
    lines = [x for x in r.stdout.splitlines() if x.startswith("OT_TAP_INSERTION tap=")]
    assert lines == ["OT_TAP_INSERTION tap=clk_t0 sinks=40 ins_ps=212.5 skew_ps=62.5",
                     "OT_TAP_INSERTION tap=clk_t1 sinks=1700 ins_ps=260.0 skew_ps=160.0"]
    assert "OT_TAP_INSERTION total taps=2" in r.stdout


def test_advisory_never_fails_the_flow():
    bad = run('proc tb_measure {est} { error "boom" }')
    assert bad.returncode == 0 and "END_OK" in bad.stdout and "OT_TAP_INSERTION WARN: not printed: boom" in bad.stdout
    none = run("")
    assert none.returncode == 0 and "tb_measure is not loaded" in none.stdout
    off = run('proc tb_measure {est} { return {} }', {"OT_TAP_INSERTION": "0"})
    assert "skipped" in off.stdout and "tap=" not in off.stdout


def test_wired_into_the_cts_hook_and_the_kit_file_list():
    post = (HERE / "cts_post.tcl").read_text()
    assert "tap_insertion.tcl" in post and post.index("tap_balance.tcl") < post.index("tap_insertion.tcl") < post.index("pg_connect.tcl")
    gp = (HERE / "gen_phys.py").read_text()
    assert re.search(r'"tap_balance\.tcl".*"tap_insertion\.tcl"|"tap_insertion\.tcl".*"cts_post\.tcl"', gp, re.S)
