#!/usr/bin/env python3
"""HBMb/NW 10-21: host cfg leaf relay classes (die_relay_stations.bus_class / bus_flag) and the relay layer's cfg WORD
alignment key + CFG-LAUNCH-ORDER check (relay_layer_d4f.port_key / cfg_launch_order).  Pure python.  Exit 1 on failure.

Cause (results/arch/hbm_no_window_decomposition_1021/DIE17_CAUSAL.md): every hleaf_<q> copy bus was equal_age_pad, so
the near sinks got 50-59 pad stages each, booked at their pins -> the worst NW capacity windows (1.546)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'hbm_die_v15'))
import die_relay_stations as DS  # noqa: E402
import relay_layer_d4f as RL  # noqa: E402

LEAVES = ('ot_hbm_host_cfg_leaf_nw', 'ot_hbm_host_cfg_leaf_sw', 'ot_hbm_host_cfg_leaf_se2', 'ot_hbm_host_cfg_leaf_ne2',
          'ot_hbm_host_cfg_leaf2')


def test_classes():
    for m in LEAVES:
        for c in 'ab':
            word = {f'{c}_cfg_addr', f'{c}_cfg_data', f'{c}_cfg_target', f'{c}_cfg_v', f'{c}_desc_base', f'{c}_desc_v'}
            assert DS.bus_class(m, word, 9) == 'cfg_no_pad', (m, c)
            assert DS.bus_class(m, word, 9, cfg_leaf=False) == 'equal_age_pad'
            assert DS.bus_class(m, word, 1) == 'p2p'
            # the launch strobe never shares the word's bus and stays equal age
            assert DS.bus_flag(m, f'{c}_launch_v') == 'launch'
            assert DS.bus_flag(m, f'{c}_launch_v', cfg_leaf=False) is False
            assert DS.bus_class(m, {f'{c}_launch_v'}, 9) == 'equal_age_pad'
            # a mixed bus (legacy grouping) is never cfg_no_pad
            assert DS.bus_class(m, word | {f'{c}_launch_v'}, 9) == 'equal_age_pad'
        assert DS.bus_flag(m, 'a_cfg_data') is False
        assert DS.bus_flag(m, 'rst_n') is True
        assert DS.bus_class(m, {'s_ready', 's_fault'}, 2) == 'equal_age_pad'
    # not a leaf: unchanged (multicast data stays equal age; ingress regex unchanged)
    assert DS.bus_class('ot_hbm_svc_sm_xcal_rel_t', {'a_cfg_data'}, 3) == 'equal_age_pad'
    assert DS.bus_flag('ot_hfd_coll_q2_hard_v8g', 'a_launch_v') is False
    assert DS.bus_class('ot_hbm_host_static_ingress', {'cfg_addr', 'cfg_data'}, 8) == 'cfg_no_pad'


def test_port_key():
    m = 'ot_hbm_host_cfg_leaf_nw'
    k1 = RL.port_key(m, 'cfg_no_pad', 'a_cfg_v', 'cfg_v')
    k2 = RL.port_key(m, 'cfg_no_pad', 'a_cfg_data', 'cfg_data')
    k3 = RL.port_key(m, 'cfg_no_pad', 'a_desc_loops', 'desc_loops')
    assert k1 == k2 == k3 == ('a_cfgword', 'cfgword')
    assert RL.port_key(m, 'cfg_no_pad', 'b_cfg_v', 'cfg_v') == ('b_cfgword', 'cfgword')   # copies never mix
    assert RL.port_key(m, 'equal_age_pad', 'a_launch_v', 'launch_v') == ('a_launch_v', 'launch_v')
    assert RL.port_key(m, 'equal_age_pad', 'a_cfg_v', 'cfg_v') == ('a_cfg_v', 'cfg_v')     # legacy class: per port
    assert RL.port_key('ot_other', 'cfg_no_pad', 'a_cfg_v', 'cfg_v') == ('a_cfg_v', 'cfg_v')


def test_cfg_launch_order():
    mo = {'hleaf_NW': 'ot_hbm_host_cfg_leaf_nw', 'x': 'ot_other'}
    consts = [dict(driver='hleaf_NW.a_cfg_addr+a_cfg_data', sink_edges={'xc_NW2': 22, 'hb_coll_NW': 76}),
              dict(driver='hleaf_NW.a_cfg_target+a_cfg_v+a_desc_v', sink_edges={'xc_NW2': 22, 'hb_coll_NW': 76}),
              dict(driver='hleaf_NW.a_launch_v', sink_edges={'xc_NW2': 77, 'hb_coll_NW': 77}),
              dict(driver='x.a_cfg_v', sink_edges={'y': 99})]
    probs, rows = RL.cfg_launch_order(consts, mo)
    assert probs == [] and len(rows) == 2, (probs, rows)
    consts[2]['sink_edges']['hb_coll_NW'] = 75
    probs, _ = RL.cfg_launch_order(consts, mo)
    assert len(probs) == 1 and 'hb_coll_NW' in probs[0], probs
    del consts[2]
    probs, _ = RL.cfg_launch_order(consts, mo)
    assert probs == [], probs                              # cfg-only receivers (pc_refresh_cfg) have no launch input


if __name__ == '__main__':
    for t in (test_classes, test_port_key, test_cfg_launch_order):
        t()
    print('CFG_LEAF_NO_PAD tests PASS')
