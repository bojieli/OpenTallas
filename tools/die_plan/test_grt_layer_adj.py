"""QC-DRT-LAYERS 11-25: per-layer GRT adjustment (grt_layers.tcl ot_grt_layer_adjust, OT_GRT_LAYER_ADJ)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = (HERE / "grt_layers.tcl").read_text()

# mocked OpenROAD: tech layers M1..M9 at routing levels 1..9, block range M2-M8
MOCK = r"""
namespace eval ord {}
proc ord::get_db_tech {} { return TECH }
proc ord::get_db_block {} { return BLK }
proc TECH {cmd name} { if {[regexp {^M([1-9])$} $name -> n]} { return L$n }; return NULL }
foreach n {1 2 3 4 5 6 7 8 9} { proc L$n {cmd} [list return $n] }
proc BLK {cmd} { if {$cmd eq "getMinRoutingLayer"} { return 2 }; return 8 }
proc set_routing_layers {args} {}
proc set_global_routing_layer_adjustment {l a} { puts "SET $l $a" }
"""


def run(env_lines):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    script = MOCK + env_lines + "\nset ::env(MIN_ROUTING_LAYER) M2\nset ::env(MAX_ROUTING_LAYER) M8\n" + SRC
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, timeout=60)
    return r, re.findall(r"^SET (M\d) (\S+)$", r.stdout, re.M)


def default_pairs():
    m = re.search(r'set ::ot_grt_layer_adj_default "([^"]*)"', SRC)
    assert m and "@" not in m.group(1)
    v = m.group(1).split()
    return list(zip(v[::2], v[1::2]))


def test_default_applied_and_calibrated():
    pairs = default_pairs()
    adj = {l: float(a) for l, a in pairs}
    # calibration direction: M2/M3 derated harder than the ORFS asap7 0.25, upper layers not derated harder
    assert adj["M2"] > 0.25 and adj["M3"] > 0.25
    assert all(adj.get(f"M{k}", 0.25) <= 0.25 for k in range(4, 9))
    r, sets = run("")
    assert r.returncode == 0, r.stderr
    assert sets == pairs


def test_env_override_off_and_range():
    r, sets = run('set ::env(OT_GRT_LAYER_ADJ) "M2 0.6 M9 0.5 M3 0.3"')
    assert r.returncode == 0, r.stderr
    assert sets == [("M2", "0.6"), ("M3", "0.3")]          # M9 outside MIN..MAX_ROUTING_LAYER: skipped
    for off in ("0", "off", ""):
        r, sets = run(f'set ::env(OT_GRT_LAYER_ADJ) "{off}"')
        assert r.returncode == 0 and sets == [] and "kept" in r.stdout


def test_bad_values_and_own_fastroute():
    for bad in ("M2", "M2 1.0", "M2 x", "MX 0.3"):
        r, _ = run(f'set ::env(OT_GRT_LAYER_ADJ) "{bad}"')
        assert "OT_GRT_LAYER_ADJ" in r.stderr and not _, bad   # Tcl error (stdin tclsh keeps rc 0), nothing set
    r, sets = run('set ::env(FASTROUTE_TCL) /work/fastroute.tcl')
    assert r.returncode == 0 and sets == []
    r, sets = run('set ::env(FASTROUTE_TCL) /OpenROAD-flow-scripts/flow/platforms/asap7/fastroute.tcl')
    assert r.returncode == 0 and sets == default_pairs()


def test_hook_runs_before_global_route_hooks():
    s = (HERE / "grt_pre.tcl").read_text()
    assert s.index("source [file join $gp_dir grt_layers.tcl]") < s.index("source [file join $gp_dir vclk_corner.tcl]")
    assert SRC.rstrip().endswith("ot_grt_layer_adjust")
