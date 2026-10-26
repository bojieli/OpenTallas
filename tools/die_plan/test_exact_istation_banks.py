import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import kit_istations as K


def test_bank_shape_requires_payload_and_epoch():
    e = dict(regs_um=[[10, 20]], bit_sites_um=[[[1.08, 2.16], [2.7, 2.16]]],
             bit_site_cell_um=[1.404, .27], face_bit_sites_um=[[1.08, 0], [2.7, 0]])
    assert K.exact_banks(e, 1)[0] == e['bit_sites_um']
    e['bit_sites_um'][0].pop()
    with pytest.raises(ValueError, match=r'width\+1'):
        K.exact_banks(e, 1)


def _runtime(tmp_path, *, epoch=True, footprint=1.404):
    # Exercise real generated Tcl on named payload/epoch flop objects. The
    # placement effects are checked independently of generated text spelling.
    script = r'''
set ff_blk block
set ff_dbu 1000
set ff_orient [dict create 2160 R0]
set ff_sw 54
set ff_x0 0; set ff_y0 0; set ff_x1 10000; set ff_y1 10000
set is_n 0; set is_fh [open /dev/null w]
proc block {m args} { return {FLOPS} }
proc master {m args} {
  switch $m { getName {return DFFHQNx1} getWidth {return 1404} getHeight {return 270} }
}
proc f0 {m args} {
  switch $m {
    getName {return {u_ist_i_a_0/q\[0\]$_DFF_P_}}
    getMaster {return master}
    setLocation {set ::p0 $args}
  }
}
proc f1 {m args} {
  switch $m {
    getName {return {u_ist_i_a_0/eq$_DFF_P_}}
    getMaster {return master}
    setLocation {set ::p1 $args}
  }
}
'''.replace('FLOPS', 'f0 f1' if epoch else 'f0')
    script += K.EXACT_BANK_TCL
    script += '\nif {[catch {is_exact_bank u_ist_i_a_0 1 {{1.08 2.16} {2.7 2.16}} ' + str(footprint) + r''' .27 test} msg]} {
  puts "REJECT $msg"; exit 7
}
puts "LOCATIONS $p0 | $p1"
'''
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_exact_bank_places_actual_named_payload_and_epoch(tmp_path):
    r = _runtime(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'LOCATIONS 1080 2160 | 2700 2160' in r.stdout


def test_missing_epoch_fails_closed(tmp_path):
    r = _runtime(tmp_path, epoch=False)
    assert r.returncode == 7
    assert 'expected 2 payload+epoch flops, got 1' in r.stdout


def test_real_cell_larger_than_reserved_bank_fails_closed(tmp_path):
    r = _runtime(tmp_path, footprint=1.0)
    assert r.returncode == 7
    assert 'exceeds its footprint' in r.stdout


def test_outgoing_stage_and_face_banks_reach_generated_kit(tmp_path):
    kd = tmp_path / 'kit'
    kd.mkdir()
    sv = kd / 'test_bound.sv'
    sv.write_text('''module test_bound(input clk, rst_n, raw, epoch, output [1:0] o_a);
    ot_dp_st #(.W(1)) u_bout_o_a (.clk(clk), .rst_n(rst_n), .d(raw), .ea(epoch), .q(o_a[0]), .eq(o_a[1]));
endmodule
''')
    (kd / 'kit_rtl.json').write_text(json.dumps(dict(bound_module='test_bound', files=[str(sv)])))
    e = dict(conn='bus:o_a', from_um=[8, 8], to_um=[0, 0], regs_um=[[6, 6], [3, 3]],
             bit_sites_um=[[[5.4, 5.4], [7.02, 5.4]], [[2.7, 2.7], [4.32, 2.7]]],
             face_bit_sites_um=[[1.08, 0], [2.7, 0]], bit_site_cell_um=[1.404, .27])
    plan = dict(partition_types=dict(t=dict(buses=[dict(name='o_a', dir='out', width=1)],
                                          contents=[], internal_stations=[e])))
    pf = tmp_path / 'plan.json'
    pf.write_text(json.dumps(plan))
    assert K.main([str(pf), 't', str(kd)]) == 0
    placed = (kd / 'istations.tcl').read_text()
    assert 'is_exact_bank {u_ist_o_a_0} 1 {{5.4 5.4} {7.02 5.4}}' in placed
    assert 'is_exact_bank {u_ist_o_a_1} 1 {{2.7 2.7} {4.32 2.7}}' in placed
    assert 'is_exact_bank {u_bout_o_a} 1 {{1.08 0} {2.7 0}}' in placed
    # Geometry adds no third register stage and never changes the RTL interface.
    text = sv.read_text()
    assert 'u_ist_o_a_0' in text and 'u_ist_o_a_1' in text and 'u_ist_o_a_2' not in text
