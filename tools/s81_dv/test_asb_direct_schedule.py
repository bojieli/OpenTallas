#!/usr/bin/env python3
"""Current return paths do not inherit errors in old LP return calendars."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import frame_schedule_asb as F


def main():
    lp = dict(spec='fixture', added_edges_per_crossing=3,
              topology=dict(master='col_h9', nodes=dict(n0=dict(a='e0.r0', b='zero.b', link_a=9, link_b=0,
                  evidence_a=dict(flat_link_edges=1, added_edges=8))), root='n0', root_link=9),
              station_inputs=dict(e0=dict(added_edges=[0], inputs=dict(xs_v=dict(paths=[dict(source='cf.xa',
                  flat_link_edges=3, added_edges=0)])), control=dict(go=dict(source='cf.cc', flat_link_edges=1,
                  added_edges=0, link_edges=1)))))
    historic = dict(nodes=dict(n0=dict(a=[['e0.r0', 4]])), root=[['n0', 1]],
                    stations=dict(e0=dict(inputs=dict(xs_v=[['cf.xa', 3]]), control=dict(go=[['cf.cc', 3]]))), links={})
    actual = copy.deepcopy(historic)
    actual['nodes']['n0']['a'] = [['e0.r0', 7]]
    actual['root'] = [['n0', 2]]
    actual['stations']['e0']['inputs']['xs_v'] = [['cf.xa', 5]]
    actual['stations']['e0']['control']['go'] = [['cf.cc', 5]]
    actual['landing_lk'] = 0x492
    actual['links'] = {'->xo': [['x', 2]], 'fint r0->r1': [2]}
    pm = dict(latency_edges=dict(x_i0_to_xo_o0=2, seam_K_plus_1=3))
    def build(old=lp, ab=actual, lanes=None):
        with patch.object(F, 'plan_lanes', return_value={('r0','r1'): [2]} if lanes is None else lanes):
            return F.schedule(historic, historic, ab, old, pm, 'col_h9', 'x', {})
    out, rows, plan, fails = build()
    assert not fails
    assert out['topology']['nodes']['n0']['link_a'] == 7
    assert out['topology']['root_link'] == 2
    assert out['station_inputs']['e0']['added_edges'] == [2]
    assert out['station_inputs']['e0']['control']['go']['added_edges'] == 2
    assert out['landing_lk'] == 0x492
    # An erroneous old return crossing assignment cannot bias the current calendar.
    wrong_old = copy.deepcopy(lp)
    wrong_old['topology']['nodes']['n0']['link_a'] += 3
    wrong_old['topology']['root_link'] -= 3
    again = build(wrong_old)[0]
    assert again['topology']['nodes']['n0']['link_a'] == 7 and again['topology']['root_link'] == 2
    # A measured physical seam disagreement remains a failing plan check.
    assert build(lanes={('r0','r1'): [6]})[3] == ['frame_int r0->r1 (band port to band port)']
    wrong = copy.deepcopy(actual); wrong['nodes']['n0']['a'] = [['e1.r0', 7]]
    try:
        build(ab=wrong)
    except AssertionError as e:
        assert 'return source differs' in str(e)
    else:
        raise AssertionError('source mutant accepted')
    # Minimal independent trace vehicle: 2 FFs and a mux. A clock/select never carries data.
    mod = dict(ports=dict(x=dict(direction='input', bits=[2]), clk=dict(direction='input', bits=[3]),
                         s=dict(direction='input', bits=[4]), xo=dict(direction='output', bits=[8])), cells={})
    def cell(t, con, dirs): return dict(type=t, connections=con, port_directions=dirs)
    mod['cells']['a'] = cell('$dff', dict(D=[2], Q=[5], CLK=[3]), dict(D='input', Q='output', CLK='input'))
    mod['cells']['b'] = cell('$dff', dict(D=[5], Q=[6], CLK=[3]), dict(D='input', Q='output', CLK='input'))
    mod['cells']['m'] = cell('$mux', dict(A=[6], B=['0'], S=[4], Y=[8]), dict(A='input',B='input',S='input',Y='output'))
    js = dict(modules=dict(top=mod))
    assert F.trace(js, 'top')[3][8] == {('x', 2)}
    mod['cells']['b']['connections']['D'] = [2]  # remove a real stage
    assert F.trace(js, 'top')[3][8] == {('x', 1)}
    print('test_asb_direct_schedule PASS: direct return/root, old-calendar mutant, physical-plan mutant, source mutant, traced-stage mutant')

if __name__ == '__main__': main()
