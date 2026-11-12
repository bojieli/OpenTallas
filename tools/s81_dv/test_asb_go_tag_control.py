#!/usr/bin/env python3
"""DIE-S81-88 11-12: the LP schedule's go_tag station control pin (frame_schedule.py since c79a872d61) is traced and
emitted by frame_schedule_asb.schedule(); a control pin the trace lacks fails with a named assertion, not a KeyError."""
import copy
from unittest.mock import patch
import frame_schedule_asb as F


def fixture():
    ctl = dict(go=dict(source='cf.cc', flat_link_edges=1, added_edges=0, link_edges=3),
               go_tag=dict(source='s0.lc', flat_link_edges=0, added_edges=0, link_edges=1))
    lp = dict(spec='fixture', added_edges_per_crossing=3,
              topology=dict(master='col_h9', nodes=dict(n0=dict(a='e0.r0', b='zero.b', link_a=9, link_b=0,
                  evidence_a=dict(flat_link_edges=1, added_edges=8))), root='n0', root_link=9),
              station_inputs=dict(e0=dict(added_edges=[0], inputs=dict(xs_v=dict(paths=[dict(source='cf.xa',
                  flat_link_edges=3, added_edges=0)])), control=ctl)))
    meas = dict(nodes=dict(n0=dict(a=[['e0.r0', 4]])), root=[['n0', 1]], links={},
                stations=dict(e0=dict(inputs=dict(xs_v=[['cf.xa', 3]]),
                                      control=dict(go=[['cf.cc', 3]], go_tag=[['s0.lc', 1]]))))
    ab = copy.deepcopy(meas)
    ab['stations']['e0']['inputs']['xs_v'] = [['cf.xa', 4]]
    ab['stations']['e0']['control'] = dict(go=[['cf.cc', 4]], go_tag=[['s0.lc', 2]])
    ab['landing_lk'] = 0x492
    ab['links'] = {'->xo': [['x', 2]], 'fint r0->r1': [2]}
    return lp, meas, ab


def run(lp, meas, ab):
    pm = dict(latency_edges=dict(x_i0_to_xo_o0=2, seam_K_plus_1=3))
    with patch.object(F, 'plan_lanes', return_value={('r0', 'r1'): [2]}):
        return F.schedule(meas, meas, ab, lp, pm, 'col_h9', 'x', {})


def main():
    assert F.CONTROL_PINS == ('go', 'cfg_v', 'go_tag')
    lp, meas, ab = fixture()
    out = run(lp, meas, ab)[0]
    c = out['station_inputs']['e0']['control']
    assert c['go']['link_edges'] == 4 and c['go_tag']['link_edges'] == 2, c   # LP + (as-built - twin), per pin
    assert c['go']['link_edges'] - c['go_tag']['link_edges'] == 2              # go_tag lead over go kept
    lp2, meas2, ab2 = fixture()
    del ab2['stations']['e0']['control']['go_tag']                             # as-built element without the pin
    try:
        run(lp2, meas2, ab2)
    except AssertionError as e:
        assert 'control pin not present' in str(e) and 'go_tag' in str(e), e
    else:
        raise AssertionError('missing go_tag trace was not refused')
    print('test_asb_go_tag_control PASS: go_tag traced and emitted, missing control pin refused by name')


if __name__ == '__main__':
    main()
