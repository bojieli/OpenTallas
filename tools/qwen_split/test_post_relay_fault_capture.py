import copy

import pytest
from post_relay_fault_capture import prepare
from fault_inventory import collect, E


def fixture(tmp_path):
    rtl = 'module P(input wire ck,rst_n,output wire [3:0] fault); endmodule\n'
    rtl += 'module C(input wire [1:0] a); endmodule\nmodule qfd_sys_face(input wire ck,rst_n); endmodule\n'
    mods = {m.name:m for m in E.P.parse_modules(rtl,'source.sv')}
    p = tmp_path/'die.v'
    p.write_text('module die();\nwire ck,r0,r1;\nwire [3:0] f;\n'
                 'P p0 (.ck(ck),.rst_n(r0),.fault(f));\n'
                 'P p1 (.ck(ck),.rst_n(r1));\nC c (.a(f[1:0]));\n'
                 'qfd_sys_face sys_face (.ck(ck),.rst_n(r0));\nendmodule\n')
    return p, mods, collect(p,mods,{('P','fault')})


def test_real_unused_bits_captured_on_exact_clock_reset_pair(tmp_path):
    die, mods, rows = fixture(tmp_path)
    plan = prepare(die,mods,rows)
    assert plan['actual_source_bits'] == 6
    assert plan['clock_reset_groups'] == 2
    assert plan['capture_flop_bits'] == 14
    assert plan['actual_sys_face_obs_fault_input'] is False
    assert plan['die_emission_eligible'] is False
    assert plan['physical_qualification_eligible'] is False
    assert [c['instance'] for c in plan['source_connections']] == ['p1']
    assert 'f[3], f[2]' in plan['fragment']
    assert {n['reset'] for n in plan['nodes']} == {'r0','r1'}


@pytest.mark.parametrize('change', ['master', 'width', 'clock', 'reset', 'unclassified', 'duplicate', 'connection'])
def test_stale_source_inventory_fails_closed(tmp_path, change):
    die, mods, rows = fixture(tmp_path)
    rows = copy.deepcopy(rows)
    if change == 'master': rows[0]['master'] = 'other'
    if change == 'width': rows[0]['port_width'] = 5
    if change == 'clock': rows[0]['clock'] = 'another'
    if change == 'reset': rows[0]['reset'] = 'another'
    if change == 'unclassified': rows[0]['classification'] = 'REVIEW_UNCLASSIFIED'
    if change == 'duplicate': rows[0]['unused_bits'] += rows[0]['unused_bits']
    if change == 'connection': rows[0]['connection'] = ''
    with pytest.raises(ValueError): prepare(die,mods,rows)
