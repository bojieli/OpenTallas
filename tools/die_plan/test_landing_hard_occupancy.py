"""Hard DB blockages apply to all cland placements, including non-ring helpers."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE=Path(__file__).resolve().parent
pytestmark=pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh unavailable')


def run(tmp_path,soft=0,blocks=True,capacity=False):
    # Exact HEAD q[271] failure geometry: 1080-dbu FIRM FF at x344628
    # intersects a clock reservation beginning x345600, although its row is full.
    setup=r'''
proc box {m args} {dict get {xMin 345600 yMin 349920 xMax 354240 yMax 358560} $m}
proc block {m args} {switch $m {getBBox {return box} isSoft {return @SOFT@}}}
set instances {}
proc blk {m args} {switch $m {getInsts {return $::instances} getBlockages {return @BLOCKS@}}}
set ff_blk blk;set ff_dbu 1000;set ff_x0 4320;set ff_y0 4320
set ff_x1 704160;set ff_y1 801000;set ff_rh 270;set ff_sw 54
set ff_orient [dict create 349920 R0];set cland_cursor {}
set ::env(RESULTS_DIR) {@OUT@}
set cland_groups {};set cland_optional_groups {};set cland_status {}
source {@SOURCE@}
proc master {m args} {switch $m {getName {return DFFHQNx1_ASAP7_75t_R} getWidth {return 1080} getHeight {return 270} isBlock {return 0}}}
proc ins {m args} {switch $m {getName {return u_cland_test/q} getMaster {return master} getPlacementStatus {return PLACED} setPlacementStatus {} setOrient {} setLocation {set ::location $args}}}
set instances {ins}
set cland_fh [open /dev/null w]
@CALL@
'''
    if capacity:
        call='if {[catch {cland_band_fit u_cland_test {345.6 349.92 354.24 350.19} ring:test} e]} {puts "CAPACITY_FAIL $e"} else {puts CAPACITY_PASS}'
    else:
        call='cland_put ins {344.628 349.92 356 350.19} tilehop:actual_q271 0.6 1\nputs "LOCATION $::location"'
    script=(setup.replace('@SOFT@',str(soft)).replace('@BLOCKS@','block' if blocks else '{}')
            .replace('@OUT@',str(tmp_path)).replace('@SOURCE@',str(HERE/'landing_placement.tcl')).replace('@CALL@',call))
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert not result.stderr,result.stderr
    return result.stdout


def test_exact_head_failure_skips_hard_clock_reservation(tmp_path):
    assert 'LOCATION 354240 349920' in run(tmp_path)


def test_full_row_and_soft_blockage_keep_previous_location(tmp_path):
    assert 'LOCATION 344628 349920' in run(tmp_path,blocks=False)
    assert 'LOCATION 344628 349920' in run(tmp_path,soft=1)


def test_capacity_bound_sees_same_hard_blockage(tmp_path):
    assert 'CAPACITY_FAIL' in run(tmp_path,capacity=True)
    assert 'CAPACITY_PASS' in run(tmp_path,capacity=True,blocks=False)
