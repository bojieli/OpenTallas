"""Regression for physical site/track alignment; not routing signoff."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
HOOK=ROOT/'physical/abi3/v41_macro_local_place_tracks_pg.tcl'

def test_joint_grid_handles_actual_failed_database_origins():
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    text=HOOK.read_text()
    proc=text[text.index('proc ot_snap_joint'):text.index('set macro_x [ot_snap_joint')]
    script=proc+'''
set x [ot_snap_joint 60 10.044 0.054 0.0 0.048]
set y [ot_snap_joint 60 10.260 0.270 0.0 0.048]
if {$x != 60.048 || $y != 60.480} {error "incorrect joint-grid origin"}
if {round(($x-10.044)*1000)%54 != 0} {error "site mismatch"}
if {round(($y-10.260)*1000)%270 != 0} {error "row mismatch"}
if {round($x*1000)%48 != 0 || round($y*1000)%48 != 0} {error "track mismatch"}
# Reject grids without a common point rather than silently relaxing either.
if {![catch {ot_snap_joint 60 0.001 0.054 0.0 0.048}]} {error "incompatible grids accepted"}
puts PASS
'''
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and p.stdout.strip()=='PASS',p.stderr

def test_placement_serialization_preserves_nanometre_grid():
    text=HOOK.read_text()
    assert '[format "%.3f %.3f" $macro_x $macro_y]' in text
    assert text.count('[format "%.3f %.3f" $x $y]')==2

def test_fixed_cells_follow_alternating_row_power_orientation():
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    text=HOOK.read_text()
    proc=text[text.index('proc ot_row_orient'):text.index('set placed 0\nforeach n $left')]
    script='''
proc block {cmd} {return {row0 row1}}
proc row0 {cmd} {if {$cmd eq "getOrigin"} {return {10044 66690}}; return MX}
proc row1 {cmd} {if {$cmd eq "getOrigin"} {return {10044 66960}}; return R0}
'''+proc+'''
if {[ot_row_orient block 66.690 1000] ne "MX"} {error "wrong power row"}
if {[ot_row_orient block 66.960 1000] ne "R0"} {error "wrong power row"}
if {![catch {ot_row_orient block 66.700 1000}]} {error "missing row accepted"}
puts PASS
'''
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and p.stdout.strip()=='PASS',p.stderr
    assert text.count('-orientation [ot_row_orient $block $y $dbu]')==2
