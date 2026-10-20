from types import SimpleNamespace

import kv_grp_safe2_ages as A
import kv_pin_repair as P
import relay_stages_export as X


def test_control_and_est_clock_do_not_inherit_hbm_instance_domain():
    by = {n: SimpleNamespace(name=n, master=master, kind='static', domain='hbm') for n, master in
          [('g', 'qkd_kvs_grp_s2'), ('h', 'qkd_kvs_grp_h_s2'), ('pc', 'qkd_kvs_pc')]}
    m = dict(insts=list(by.values()), buses=[
        ('ctl', 'kv_oneway', 194, [('g', 'o_dn'), ('h', 'i_ctl')]),
        ('est', 'kv_oneway', 1, [('g', 'y__est__0_1'), ('pc', 'x__est__0_1')])],
        relay_stages={'ctl': 0, 'est': 0})
    doc = X.export_model(m, 'safe2-clock-source', reach=405)
    assert {b['domain'] for b in doc['buses']} == {'core'}
    assert X.QX.DRS.validate(doc) == []
    assert P.launch_domain(by, ('g', 'o_dn'), ('h', 'i_ctl')) == 'core'


def test_hbm_pc_faces_retain_their_measured_clock(monkeypatch):
    monkeypatch.setattr(P, 'PORT_DOMAINS', 'results/arch/qwen_kv_domsplit_1019/ports')
    monkeypatch.setattr(P, '_PD', {})
    assert P.port_domain('qkd_kvs_grp_s2', 'o_pc0_h') == 'hbm'
    assert P.port_domain('qkd_kvs_grp_s2', 'o_pc0') == 'core'


def test_farthest_group_prices_all_eight_captures_and_real_external_relays():
    order = (4, 5, 0, 1, 2, 3, 6, 7)
    rs = {'ks_kvs_hroot_WS__o_ch0': 3}
    rs.update({f'ks_slg_WS_{g}__o_dn': 4 for g in reversed(order[1:])})
    rs.update({f'ks_slg_WS_{g}__o_ctl': 2 for g in order})
    result = A.plan_receipt(dict(relay_stages=rs), ['WS'], order)
    first, last = result['groups'][0], result['groups'][-1]
    assert first['instance'] == 'slg_WS_7' and first['control_face_edges'] == 1
    assert last['instance'] == 'slg_WS_4' and last['control_face_edges'] == 8
    assert last['control']['relay_edges'] == 31
    assert last['gather_face_edges'] == 7 and last['gather']['relay_edges'] == 16
    assert result['missing_external_buses'] == []
    assert result['qualified'] is False


def test_missing_lane_is_unknown_not_a_zero_cycle_path():
    result = A.plan_receipt({}, ['WS'], (4, 5, 0, 1, 2, 3, 6, 7))
    assert all(r['control']['relay_edges'] is None for r in result['groups'])
    assert 'ks_kvs_hroot_WS__o_ch0' in result['missing_external_buses']
