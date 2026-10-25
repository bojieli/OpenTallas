"""OpenSTA source insertion is removed on launch but retained on capture by clk_skew."""
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('insertion', [-120.0, 0.0, 80.0])
@pytest.mark.parametrize('delay,expected', [('max', -50.0), ('min', 35.0)])
def test_path_skew_restores_signed_launch_source_insertion(insertion, delay, expected):
    script = r'''
set ::ot_ps_lib_only 1
source @SOURCE@
proc get_pins {args} {return pin}
proc get_property {obj prop} {return 833.0}
proc find_timing_paths {args} {return pe}
proc clkedge {method} {return 0}
proc tp {method} {return 2e-10}
proc pe {method} {
  switch $method {
    is_check {return 1}
    is_latch_check {return 0}
    check_role {return $::role}
    target_clk_path {return tp}
    target_clk {return clk}
    target_clk_edge {return clkedge}
    clk_skew {return $::sk}
    data_required_time {return $::req}
    margin {return 2e-11}
  }
}
set ::ot_ps_R [dict create launch [list launch/CK clk 250 200]]
set ::ot_ps_insertion [dict create clk [list @INS@ @INS@]]
set role @ROLE@
set sk @SKEW@
set req @REQ@
puts [ot_ps_path launch capture/D @DELAY@]
'''
    if delay == 'max':
        skew = (60 - insertion - 10) * 1e-12
        req = (200 + 833 - 20 + 10) * 1e-12
    else:
        skew = (-40 - insertion - 5) * 1e-12
        req = (200 + 20 - 5) * 1e-12
    for key, value in {'SOURCE': Path(__file__).with_name('pair_skew.tcl'), 'INS': insertion,
                       'ROLE': 'setup' if delay == 'max' else 'hold', 'SKEW': skew,
                       'REQ': req, 'DELAY': delay}.items():
        script = script.replace('@' + key + '@', str(value))
    p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
    assert not p.stderr, p.stderr
    got = [float(x) for x in p.stdout.split()]
    assert got[0] == pytest.approx(expected, abs=1e-6)
    assert got[1] == pytest.approx(10 if delay == 'max' else 5, abs=1e-6)
