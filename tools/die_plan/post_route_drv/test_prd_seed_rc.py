"""FLOW-25: a seed with routed data wires repairs on placement parasitics (RSZ-0074 class)."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HOOK = Path(__file__).parent / "prd_hook.tcl"
MK = Path(__file__).parent / "prd_mk.sh"


def _section():
    s = HOOK.read_text()
    a = s.index("proc ot_prd_wired_data_nets")
    b = s.index("global_route -start_incremental", a)
    return s[a:b]




def _run(nets, env_rc=None, wrapper=True, clock=()):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    lines = []
    for n, sig, sp, w in nets:
        lines.append(f'proc {n} {{m}} {{ switch $m {{ getName {{return {n}}} getSigType {{return {sig}}} '
                     f'isSpecial {{return {sp}}} getWire {{return {w}}} }} }}')
    names = " ".join(n for n, *_ in nets)
    clks = " ".join(clock)
    tcl = "\n".join(lines) + f"""
proc ot_clk_dbnets {{}} {{ return {{{clks}}} }}
proc block {{m}} {{ return {{{names}}} }}
namespace eval ord {{ proc get_db_block {{}} {{ return block }} }}
proc estimate_parasitics {{args}} {{ puts "EST $args" }}
{"proc ::ot_prd_native_estimate {args} {}" if wrapper else ""}
{f'set ::env(OT_PRD_REPAIR_RC) {env_rc}' if env_rc is not None else 'unset -nocomplain ::env(OT_PRD_REPAIR_RC)'}
{_section()}
puts "PLACE $::ot_prd_rc_place"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".tcl") as f:   # tclsh from stdin ignores errors: run a file
        f.write(tcl)
        f.flush()
        r = subprocess.run(["tclsh", f.name], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


FRESH = [("a", "SIGNAL", 0, "NULL"), ("c", "SIGNAL", 0, "w1"), ("k", "CLOCK", 0, "w2"), ("v", "POWER", 1, "w3")]
WIRED = FRESH + [("d", "SIGNAL", 0, "w4")]


def test_fresh_seed_keeps_grt_source():
    rc, out = _run(FRESH, clock=("c",))     # clock nets may be pre-routed in a grt seed: not counted
    assert rc == 0 and "PLACE 0" in out and "EST" not in out and "seed: 0 data nets" in out


def test_wired_seed_repairs_on_placement():
    rc, out = _run(WIRED, clock=("c",))
    assert rc == 0 and "PLACE 1" in out and "EST -placement" in out and "seed: 1 data nets" in out


def test_grt_opt_out_and_explicit_placement():
    rc, out = _run(WIRED, env_rc="grt", clock=("c",))
    assert rc == 0 and "PLACE 0" in out
    rc, out = _run(FRESH, env_rc="placement", clock=("c",))
    assert rc == 0 and "PLACE 1" in out


def test_bad_value_refused():
    rc, out = _run(WIRED, env_rc="steiner")
    assert rc != 0 and "want placement|grt" in out


def test_frozen_clock_path_warns_not_fails():
    rc, out = _run(WIRED, wrapper=False, clock=("c",))
    assert rc == 0 and "PLACE 0" in out and "frozen-clock RC path keeps" in out
    rc, out = _run(FRESH, env_rc="placement", wrapper=False)
    assert rc != 0 and "needs the routed-SPEF estimate wrapper" in out


def test_mk_pins_value():
    s = MK.read_text()
    assert re.search(r"placement\|grt\) echo \"OT_PRD_REPAIR_RC=\$OT_PRD_REPAIR_RC\"", s)
