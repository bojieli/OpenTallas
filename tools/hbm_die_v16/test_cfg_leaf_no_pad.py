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
    # not a leaf: unchanged (multicast data stays equal age; plain-ingress regex unchanged)
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


def test_launch_floor():
    rows = [dict(driver='hleaf_SW.b_cfg_addr+b_cfg_data'), dict(driver='hleaf_SW.b_cfg_target+b_cfg_v'),
            dict(driver='hleaf_SW.b_launch_v'), dict(driver='hleaf_SW.s_ready'), dict(driver='x.b_launch_v')]
    lr = RL.leaf_copy_rows(rows, {'hleaf_SW': 'ot_hbm_host_cfg_leaf_sw', 'x': 'ot_other'})
    assert dict(lr) == {('hleaf_SW', 'b'): ([0, 1], [2])}, dict(lr)
    age = {(0, 'xl'): 38, (1, 'xl'): 38, (0, 'cp'): 33, (1, 'cp'): 33, (2, 'xl'): 37, (2, 'cp'): 37, (2, 'smw'): 37}
    def eff(b, s=None):
        if s is None:
            return [(k[1], v) for k, v in age.items() if k[0] == b]
        return age.get((b, s))
    assert RL.launch_floor([0, 1], [2], eff) == {2: 1}     # r16q replay case: launch 37 < word 38 at xl_SW_ctl
    age[2, 'xl'] = age[2, 'cp'] = age[2, 'smw'] = 38
    assert RL.launch_floor([0, 1], [2], eff) == {}


ING = 'ot_hbm_host_static_ingress_obs'


def test_ingress_obs():
    """HBMc/CHAIN-ING 10-21: the d4g ingress master ot_hbm_host_static_ingress_obs (exact name; CFG never matched it)"""
    pay = {'cfg_addr', 'cfg_data', 'desc_base', 'desc_limit', 'desc_loops'}
    ctl = {'cfg_target', 'cfg_v', 'desc_v'}
    assert DS.bus_class(ING, pay, 8) == 'cfg_no_pad' and DS.bus_class(ING, ctl, 9) == 'cfg_no_pad'
    assert DS.bus_flag(ING, 'launch_v') == 'launch' and DS.bus_class(ING, {'launch_v'}, 9) == 'equal_age_pad'
    assert DS.bus_class(ING, ctl | {'launch_v'}, 9) == 'equal_age_pad'          # mixed bus never no-pad
    for f in (dict(cfg_leaf=False), dict(ingress=False)):                       # legacy / leaf_only (r18 S4 rule)
        assert DS.bus_class(ING, pay, 8, **f) == 'equal_age_pad' and DS.bus_flag(ING, 'launch_v', **f) is False
    assert DS.bus_class(ING, {'obs_q_d', 'obs_q_v'}, 2) == 'equal_age_pad' and DS.bus_flag(ING, 'fault') is False
    # exact master only: no broad regex
    assert DS.bus_class('ot_hbm_host_static_ingress_obs2', pay, 8) == 'equal_age_pad'
    assert DS.bus_flag('ot_hbm_host_static_ingress_obsx', 'launch_v') is False
    # the GUARD join keeps the deepest age; targets do not
    assert DS.guard_sink('cfg_no_pad', ING, 'ot_hbm_status_join_fa') and DS.guard_sink('cfg_no_pad', ING, 'ot_hbm_status_join')
    assert not DS.guard_sink('cfg_no_pad', ING, 'ot_hbm_host_cfg_leaf_ne2')
    assert not DS.guard_sink('cfg_no_pad', 'ot_hbm_host_cfg_leaf_nw', 'ot_hbm_status_join_fa')
    assert not DS.guard_sink('cfg_no_pad', ING, 'ot_hbm_status_join_fa', ingress=False)
    # layer: one word per sink across the payload and strobe rows; launch separate
    assert RL.port_key(ING, 'cfg_no_pad', 'cfg_data', 'cfg_data') == RL.port_key(ING, 'cfg_no_pad', 'desc_v', 'desc_v') \
        == ('cfgword', 'cfgword')
    assert RL.port_key(ING, 'equal_age_pad', 'launch_v', 'launch_v') == ('launch_v', 'launch_v')
    assert RL.port_key(ING, 'equal_age_pad', 'cfg_v', 'cfg_v') == ('cfg_v', 'cfg_v')       # legacy class: per port
    assert RL.port_key(ING, 'p2p', 'obs_q_d', 'obs_q_d') == ('obs_q_d', 'obs_q_d')


def test_ingress_order_and_guard():
    mo = {'host_cp_ingress': ING, 'host_status': 'ot_hbm_status_join_fa', 'hleaf_NE': 'ot_hbm_host_cfg_leaf_ne2',
          'hcollgi_SW': 'ot_hgi_coll_gq_issue'}
    rows = [dict(driver='host_cp_ingress.cfg_addr+cfg_data+desc_base+desc_limit+desc_loops'),
            dict(driver='host_cp_ingress.cfg_target+cfg_v+desc_v'), dict(driver='host_cp_ingress.launch_v'),
            dict(driver='host_cp_ingress.obs_q_d+obs_q_idx+obs_q_v')]
    assert dict(RL.leaf_copy_rows(rows, mo)) == {('host_cp_ingress', 'i'): ([0, 1], [2])}
    # r18 S4 shape: word per sink (hcollgi_SW 11 .. hleaf_NE 58), join padded to 58, launch equal age 58
    consts = [dict(driver=rows[0]['driver'], sink_edges={'hcollgi_SW': 11, 'hleaf_NE': 58}),
              dict(driver=rows[1]['driver'], sink_edges={'hcollgi_SW': 11, 'hleaf_NE': 58, 'host_status': 58}),
              dict(driver=rows[2]['driver'], sink_edges={'hcollgi_SW': 58, 'hleaf_NE': 58, 'host_status': 58})]
    probs, out = RL.cfg_launch_order(consts, mo)
    assert probs == [] and len(out) == 3 and [r['guard'] for r in out] == [False, False, True], (probs, out)
    consts[1]['sink_edges']['host_status'] = 0                 # join per-sink (unpadded): GUARD would expire early
    probs, _ = RL.cfg_launch_order(consts, mo)
    assert len(probs) == 1 and probs[0].startswith('CFG-GUARD-ORDER') and 'host_status' in probs[0], probs
    consts[1]['sink_edges']['host_status'] = 58; consts[2]['sink_edges']['hleaf_NE'] = 57
    probs, _ = RL.cfg_launch_order(consts, mo)
    assert len(probs) == 1 and probs[0].startswith('CFG-LAUNCH-ORDER host_cp_ingress.i_launch_v -> hleaf_NE'), probs
    # floors: the join is raised to the latest target word (one row only: the strobe row it sits on)
    age = {(0, 'gi'): 11, (0, 'ne'): 59, (1, 'gi'): 11, (1, 'ne'): 58, (1, 'hs'): 58, (2, 'gi'): 58, (2, 'ne'): 58, (2, 'hs'): 58}
    def eff(b, s=None):
        if s is None:
            return [(k[1], v) for k, v in age.items() if k[0] == b]
        return age.get((b, s))
    assert RL.guard_floor([0, 1], eff, lambda s: s == 'hs') == {(1, 'hs'): 1}
    assert RL.launch_floor([0, 1], [2], eff) == {2: 1}
    age[1, 'hs'] = 59
    assert RL.guard_floor([0, 1], eff, lambda s: s == 'hs') == {}


def test_equal_age_land():
    """HBMc/TOKEN 10-22: r18 pgp_NE.command (rf0076) stations N 55/44/25/14 got station-equal pads 0/11/30/41 -> landed
    edge ages 30/35/45/50 (spread 20).  EQUAL-AGE-LAND: every sink at the deepest sink's zero-pad age (30)."""
    sdep = {'su_NE0': 55, 'su_NE2': 44, 'su_NE3': 25, 'su_NE1': 14}
    st = RL.equal_age_land_stages(sdep, lambda s: None)
    assert st == {'su_NE0': 1, 'su_NE2': 7, 'su_NE3': 16, 'su_NE1': 22}, st   # pads 0/6/15/21
    land = {s: -(-n // 2) + 1 + 1 + (st[s] - 1) for s, n in sdep.items()}
    assert set(land.values()) == {30}, land
    # legacy station-equal pads reproduce the r18 ages and are flagged
    legacy = {('rf0076', s): -(-n // 2) + 1 + 1 + p for (s, n), p in zip(sdep.items(), (0, 11, 30, 41))}
    assert sorted(legacy.values()) == [30, 35, 45, 50]
    ages, probs = RL.equal_age_land_check(legacy, {'rf0076'})
    assert len(probs) == 1 and probs[0].startswith('EQUAL-AGE-LAND rf0076'), probs
    ages, probs = RL.equal_age_land_check({('rf0076', s): v for s, v in land.items()}, {'rf0076'})
    assert probs == [] and set(ages['rf0076'].values()) == {30}
    # a known land-plan E enters the age: E 2 on the deepest sink raises every other sink by one
    st2 = RL.equal_age_land_stages(sdep, lambda s: 2 if s == 'su_NE0' else None)
    assert st2 == {'su_NE0': 1, 'su_NE2': 8, 'su_NE3': 17, 'su_NE1': 23}, st2
    # odd/even station parity: N 3 and N 4 land on the same edge (ceil), N 5 one later
    assert RL.equal_age_land_stages({'a': 3, 'b': 4, 'c': 5}, lambda s: None) == {'a': 2, 'b': 2, 'c': 1}


if __name__ == '__main__':
    for t in (test_classes, test_port_key, test_cfg_launch_order, test_launch_floor, test_ingress_obs,
              test_ingress_order_and_guard, test_equal_age_land):
        t()
    print('CFG_LEAF_NO_PAD tests PASS')
