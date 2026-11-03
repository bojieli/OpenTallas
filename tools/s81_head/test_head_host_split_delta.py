import copy, json, subprocess, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_host_split_delta as hs


def _bus(name, d, w, face, win):
    return dict(name=name, dir=d, width=w, kind='data', leaf='u_core.' + name, face=face, window_um=win,
                layers=['M4', 'M6'], order='lsb_low')


def _macro(lane, i, x, y):
    return dict(inst=f'u_core.{lane}.u_ln.m{i}', module='ot_sram_1r1w2c_256x64_m1', origin_um=[x, y],
                outline_um=[34.584, 41.352], orient='R0')


def fixture():
    host = dict(module='ot_s81hd_host_ep', outline_um=[1296.0, 570.24], hard=False, cells=200004,
                clock=dict(tap_um=[648.0, 285.12], start_capture_um=[409.184, 552.992],
                           edge_clocks=[dict(port='fclk_in_coll_i0', tap_um=[2.144, 223.136]),
                                        dict(port='fclk_in_coll_i1', tap_um=[1180.0, 2.656])],
                           landing_contract=dict(pins=[])),
                reset=dict(sync_stages=2, start_role='bootstrap', local_taps_um=[[1222.56, 276.48], [276.48, 324.0]]),
                contents=[dict(inst='u_core', module='ot_s81hd_host_ep_core', bind={'ck': 'clk', 'rst_n': 'rst_n', 'start_i': 'start'},
                               params={'BOOT_HEADER_EDGE': 501})],
                buses=[_bus('coll_i0', 'in', 514, 'W', [120.0, 326.0]), _bus('coll_o0', 'out', 512, 'W', [342.0, 547.2]),
                       _bus('coll_i1', 'in', 514, 'S', [1076.88, 1282.88]), _bus('coll_o1', 'out', 512, 'S', [855.68, 1060.88]),
                       _bus('h_tx_i', 'in', 277, 'N', [400.298, 469.564]), _bus('h_rx_o', 'out', 276, 'N', [323.048, 392.298])],
                sources=[], hard_cores=[_macro('u_lane0', 0, 77.76, 120.96), _macro('u_lane1', 0, 924.48, 77.76)],
                count_straps=[dict(name='strap_ca_pad')], reset_start_raw_exports=[dict(port='rst_start_raw_0')])
    ports = [dict(id='coll_HOST1_u__0', src=dict(part='lk_HOST1', bus='coll_o0'), dst=dict(part='host', bus='coll_i1'), width=514, kind='data'),
             dict(id='coll_HOST1_d__0', src=dict(part='host', bus='coll_o1'), dst=dict(part='lk_HOST1', bus='coll_i0'), width=512, kind='data'),
             dict(id='coll_HOST0_u__1', src=dict(part='sst5', bus='u_o'), dst=dict(part='host', bus='coll_i0'), width=514, kind='data'),
             dict(id='coll_HOST0_d__0', src=dict(part='host', bus='coll_o0'), dst=dict(part='sst5', bus='d_i'), width=512, kind='data'),
             dict(id='host_tx__6__h5n', src=dict(part='host_nstrip', bus='h_tx_ft_o'), dst=dict(part='host', bus='h_tx_i'), width=277, kind='data'),
             dict(id='host_rx__0__h5n', src=dict(part='host', bus='h_rx_o'), dst=dict(part='host_nstrip', bus='h_rx_ft_i'), width=276, kind='data')]
    plan = dict(partition_types={'hd_host': host, 'hd_x': dict(module='x')},
                partitions=[dict(name='host', type='hd_host', origin_um=[8760.96, 1330.56], orient='R0')],
                ports=ports, lanes=[dict(id=p['id'], ports=[p['id']]) for p in ports],
                clock=dict(landing_network=dict(edges=[dict(id='c1', src=dict(part='lk_HOST1', bus='fclk_out_coll_o0'), dst=dict(part='host', bus='fclk_in_coll_i1')),
                                                       dict(id='c2', src=dict(part='host', bus='cland_up_ready_h_rx_o'), dst=dict(part='host_nstrip', bus='x'))],
                                                start_tree=dict(uses=[dict(part='host', pin='cland_tstart_in')])), tap_window=dict(per_type_ps={'hd_host': 20.0})),
                reset=dict(in_sites={'hd_host': [810.016, 561.568]}), latency=dict(lanes={}))
    side = dict(ports=[dict(port=p['id'], src=p['src']['part'], dst=p['dst']['part']) for p in ports],
                regions=[dict(tag='host', parts=2)], count_aligned={}, collector={})
    return plan, side


def test_split_geometry_and_ports():
    plan, side = fixture()
    p, s, r = hs.apply(plan, side)
    assert 'hd_host' not in p['partition_types']
    w, e = p['partition_types']['hd_host_w'], p['partition_types']['hd_host_e']
    assert w['outline_um'] == e['outline_um'] == [648.0, 570.24]
    assert [c['module'] for c in w['contents']] == ['ot_s81hd_host_w_core']
    assert [c['module'] for c in e['contents']] == ['ot_s81hd_host_e_core'] and e['contents'][0]['params'] == {}
    assert w['contents'][0]['params'] == {'BOOT_HEADER_EDGE': 501}          # HBC dates stay with W
    bw = {b['name']: b for b in w['buses']}; be = {b['name']: b for b in e['buses']}
    assert set(bw) == {'coll_i0', 'coll_o0', 'h_tx_i', 'h_rx_o', 'l1_rx_i', 'l1_tx_o'}
    assert set(be) == {'coll_i1', 'coll_o1', 'l1_rx_o', 'l1_tx_i'}
    assert be['coll_i1']['window_um'] == [428.88, 634.88] and be['coll_o1']['window_um'] == [207.68, 412.88]
    for a, b in (('l1_rx_i', 'l1_rx_o'), ('l1_tx_o', 'l1_tx_i')):
        assert bw[a]['window_um'] == be[b]['window_um'] and bw[a]['width'] == be[b]['width']
        assert (bw[a]['face'], be[b]['face']) == ('E', 'W') and bw[a]['dir'] != be[b]['dir']
    assert bw['l1_rx_i']['width'] == 558 and bw['l1_tx_o']['width'] == 554
    assert [h['origin_um'] for h in w['hard_cores']] == [[77.76, 120.96]]
    assert [h['origin_um'] for h in e['hard_cores']] == [[276.48, 77.76]]
    assert e['clock']['edge_clocks'][0]['port'] == 'fclk_in_coll_i1' and e['clock']['edge_clocks'][0]['tap_um'] == [532.0, 2.656]
    assert [x['port'] for x in w['clock']['edge_clocks']] == ['fclk_in_coll_i0']
    assert w['clock']['tap_um'] == e['clock']['tap_um'] == [324.0, 285.12]
    assert e['reset']['local_taps_um'] == [[574.56, 276.48]] and w['reset']['local_taps_um'] == [[276.48, 324.0]]
    assert 'start_capture_um' in w['clock'] and 'start_capture_um' not in e['clock']
    for t in (w, e):                                                         # RAW: CA-derived records dropped
        assert 'landing_contract' not in t['clock'] and 'count_straps' not in t and 'reset_start_raw_exports' not in t
    parts = {q['name']: q for q in p['partitions']}
    assert parts['host_w']['origin_um'] == [8760.96, 1330.56] and parts['host_e']['origin_um'] == [9408.96, 1330.56]
    ends = {x['id']: (x['src']['part'], x['dst']['part']) for x in p['ports']}
    assert ends['coll_HOST1_u__0'] == ('lk_HOST1', 'host_e') and ends['coll_HOST1_d__0'] == ('host_e', 'lk_HOST1')
    assert ends['coll_HOST0_u__1'] == ('sst5', 'host_w') and ends['host_rx__0__h5n'] == ('host_w', 'host_nstrip')
    assert ends['host_l1rx__0'] == ('host_e', 'host_w') and ends['host_l1tx__0'] == ('host_w', 'host_e')
    assert {'host_l1rx', 'host_l1tx'} <= {l['id'] for l in p['lanes']}
    assert p['latency']['lanes']['host_l1rx']['cycles'] == 4 and p['latency']['lanes']['host_l1tx']['boundary'] == 2
    assert {l['id']: l.get('fixed_cycles') for l in p['lanes'] if l['id'].startswith('host_l1')} == {'host_l1rx': 2, 'host_l1tx': 2}
    assert p['reset']['in_sites'] == {'hd_host_e': [162.016, 561.568], 'hd_host_w': [600.992, 561.568]}
    ln = p['clock']['landing_network']
    assert [e['dst']['part'] for e in ln['edges']] == ['host_e', 'host_nstrip'] and ln['edges'][1]['src']['part'] == 'host_w'
    assert ln['start_tree']['uses'][0]['part'] == 'host_w'
    assert p['clock']['tap_window']['per_type_ps'] == {'hd_host_w': 20.0, 'hd_host_e': 20.0}
    sp = {x['port']: (x['src'], x['dst']) for x in s['ports']}
    assert sp['coll_HOST1_u__0'] == ('lk_HOST1', 'host_e') and sp['coll_HOST0_d__0'] == ('host_w', 'sst5')
    assert s['regions'][0]['parts'] == 3 and r['status'] == 'RAW_RECOMPOSE_REQUIRED' and r['sidecar_stale'] == ['count_aligned', 'collector']
    assert r['data_cycles_added'] == {'E->W (host1 RX, lane1 fault)': 4, 'W->E (lane1 STATUS TX)': 4,
                                   'HOST1 egress link (lane1 tx flits, co_m)': 1,
                                   'HOST0 ingress (lane0 RX stage, HBC/HFWD/lane0 faults)': 1}
    assert [l.get('fixed_cycles') for l in p['lanes'] if 'coll_HOST1_d__0' in l['ports']] == [1]
    assert [l.get('fixed_cycles') for l in p['lanes'] if 'coll_HOST0_u__1' in l['ports']] == [1]   # DH58 W lane0 stage
    assert plan['partition_types']['hd_host']['outline_um'] == [1296.0, 570.24]   # input untouched


def test_refuses_changed_inputs():
    plan, _ = fixture()
    bad = copy.deepcopy(plan); bad['partition_types']['hd_host']['outline_um'] = [1300.0, 570.24]
    with pytest.raises(ValueError):
        hs.apply(bad)
    bad = copy.deepcopy(plan); bad['partition_types']['hd_host']['hard_cores'][1]['origin_um'] = [1280.0, 77.76]
    with pytest.raises(ValueError):                                         # macro would cross the E outline
        hs.apply(bad)
    bad = copy.deepcopy(plan); bad['ports'].pop()
    with pytest.raises(ValueError):
        hs.apply(bad)


def test_cli_refuses_existing_out(tmp_path):
    plan, side = fixture()
    (tmp_path / 'p.json').write_text(json.dumps(plan))
    out = tmp_path / 'o'
    cmd = [sys.executable, str(Path(hs.__file__)), str(tmp_path / 'p.json'), '--out', str(out)]
    assert subprocess.run(cmd, capture_output=True).returncode == 0 and (out / 'source_plan.json').is_file()
    assert subprocess.run(cmd, capture_output=True).returncode != 0


def test_plan_sources_from_base_list():
    base = ['rtl/a.sv', 'physical/m/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1_bb.v',
            'rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv']
    w, e = hs.plan_sources(base, False), hs.plan_sources(base, True)
    assert w == base + [hs.W_CORE] and not any(x.endswith('m1.v') or 'reset_sync' in x for x in w)
    assert 'rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv' not in e and e[-1] == hs.E_CORE


def test_sources_closure():
    assert hs.W_CORE in hs.W_SOURCES and hs.E_CORE in hs.E_SOURCES
    assert 'rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv' in hs.W_SOURCES        # frame mux
    assert not any('hostb' in s for s in hs.E_SOURCES)
