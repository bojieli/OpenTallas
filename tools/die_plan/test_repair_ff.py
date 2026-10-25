"""Fresh-process repair contract and preserved-failure checkpoint controls."""
from pathlib import Path
import shutil
import subprocess
import pytest

HERE = Path(__file__).resolve().parent


def run(tmp_path, before=(-57, 1027), after=(0, 0), library='cells_FF.lib', mode='placement'):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    for name in (library, 'input.odb', 'input.sdc', 'ff.sdc', 'rc.tcl'):
        (tmp_path / name).touch()
    script = '''
set calls {}
proc read_liberty {x} {lappend ::calls [list lib $x]}
proc read_db {x} {}
proc read_sdc {x} {lappend ::calls [list sdc $x]}
proc all_clocks {} {return {clk vclk}}
proc get_property {clk property} {if {$clk eq "clk"} {return pin};return {}}
proc set_propagated_clock {clk} {lappend ::calls [list propagate $clk]}
proc estimate_parasitics {basis} {lappend ::calls [list estimate $basis]}
proc repair_timing {args} {set ::repaired 1; lappend ::calls [linsert $args 0 repair]}
proc detailed_placement {} {}
proc check_placement {args} {}
proc write_db {p} {close [open $p w]}
proc write_sdc {p} {close [open $p w]}
namespace eval sta {
  proc time_sta_ui {x} {return $x}
  proc worst_slack_cmd {x} {return [expr {$::repaired ? $::after_w : $::before_w}]}
  proc endpoint_violation_count {x} {return [expr {$::repaired ? $::after_n : $::before_n}]}
}
set repaired 0
'''
    values = dict(PLIBS=tmp_path / library, ODB=tmp_path/'input.odb', SDC=tmp_path/'input.sdc',
                  FF_SDC=tmp_path/'ff.sdc', RCFILE=tmp_path/'rc.tcl', OUT_DIR=tmp_path/'out', OT_REPAIR_MODE=mode)
    script += '\n'.join(f'set ::env({k}) {{{v}}}' for k,v in values.items())+'\n'
    script += f'set before_w {before[0]}; set before_n {before[1]}; set after_w {after[0]}; set after_n {after[1]}\n'
    script += f'if {{[catch {{source {{{HERE / "repair_ff.tcl"}}}}} msg]}} {{puts stderr $msg; exit 1}}\nputs $calls\n'
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_isolated_ff_contract(tmp_path):
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert 'propagate clk' in r.stdout and 'propagate vclk' not in r.stdout
    assert 'repair -hold -hold_margin 0 -setup_margin 0' in r.stdout
    assert 'FF hold only; TT setup/signoff required' in r.stdout
    assert (tmp_path/'out/repair_ff.odb').exists()
    assert 'NOT_RUN_TT_REQUIRED' in (tmp_path/'out/repair_ff.tsv').read_text()


def test_nonff_and_structural_fail_closed(tmp_path):
    r = run(tmp_path, library='cells_TT.lib')
    assert r.returncode == 1 and 'explicit existing FF library' in r.stderr
    r = run(tmp_path, before=(-101, 1027))
    assert r.returncode == 1 and 'structural FF failure' in r.stderr
    assert not (tmp_path/'out/repair_ff.odb').exists()


def test_residual_failure_keeps_checkpoint(tmp_path):
    r = run(tmp_path, after=(-1, 2))
    assert r.returncode == 1 and 'checkpoint retained' in r.stderr
    assert (tmp_path/'out/repair_ff.odb').exists()


def test_global_route_repair_requires_qualified_incremental_wrapper(tmp_path):
    r = run(tmp_path, mode='global_routing')
    assert r.returncode == 1 and 'incremental routing' in r.stderr
    assert not (tmp_path/'out/repair_ff.odb').exists()
