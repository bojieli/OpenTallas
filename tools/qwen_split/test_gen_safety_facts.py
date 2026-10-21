"""Small topology witnesses; no synthesis or whole-die simulation."""
from copy import deepcopy
from types import SimpleNamespace as Inst

import pytest
from die_safety.gen_check import check_facts
from qwen_split.gen_safety_facts import channels, export_model, install


def fixture():
    def inst(n, m, x, y=10, w=10, h=10, kind='block'):
        return Inst(name=n, master=m, x=x, y=y, w=w, h=h, kind=kind)
    m = dict(die=dict(w=1000., h=100.), insts=[
        inst('pll', 'pll', 0), inst('a', 'block', 30), inst('b', 'block', 450),
        inst('h0', 'qfd_rlyh0_8_ew', 100, kind='relay'),
        inst('land', 'qfd_landh_8_ew', 400, kind='relay')], buses=[
        ('clk_a', 'clock_trunk', 1, [('pll', 'ca'), ('a', 'ck'), ('h0', 'ck')]),
        ('clk_b', 'clock_trunk', 1, [('pll', 'cb'), ('b', 'ck'), ('land', 'ck')]),
        ('fck', 'clock_trunk', 1, [('h0', 'ck_o'), ('land', 'ckf')]),
        ('data', 'data', 8, [('a', 'q'), ('h0', 'a')]),
        ('data__r1', 'data', 8, [('h0', 'b'), ('land', 'a')]),
        ('data__r2', 'data', 8, [('land', 'b'), ('b', 'd')])],
        fwd_lanes=dict(lanes=[dict(bid='data', src='a', dst='b', bits=8,
            src_ck='clk_a', dst_ck='clk_b', stations=['h0'], landing='land')]))
    def pos(i, p):
        it = next(z for z in m['insts'] if z.name == i)
        return (it.x, 5.)
    return m, pos


def test_actual_chain_and_negative_witnesses():
    m, pos = fixture()
    facts = export_model(m, pos)
    assert check_facts(facts)['verdict'] == 'PASS'
    assert len(facts['wires']) == 1
    assert len(facts['wires'][0]['segments']) == 3
    assert facts['crossings'][0]['landing'] == 'land'
    assert facts['regions']['clk_a']['root'] == 'pll/ca'
    for mutation, counter in [('landing', 'no_landing'), ('root', 'no_root'), ('reach', 'hops_over')]:
        f = deepcopy(facts)
        if mutation == 'landing': f['crossings'][0]['landing'] = None
        if mutation == 'root': f['regions']['clk_b']['root'] = None
        if mutation == 'reach': f['wires'][0]['pts'][1] = [900., 5.]
        verdict = check_facts(f)
        assert verdict['verdict'] == 'FAIL' and verdict['counts'][counter] > 0


def test_export_missing_ring_and_root_are_not_inferred():
    m, pos = fixture()
    m['insts'][-1].master = 'qfd_rlyrl_8_ew'
    m['buses'] = [b for b in m['buses'] if b[0] != 'clk_b']
    r = check_facts(export_model(m, pos))
    assert r['counts']['no_landing'] == 1 and r['counts']['no_root'] == 1


def test_direct_regional_crossing_cannot_hide_behind_lanes():
    m, pos = fixture()
    m['buses'].append(('direct', 'data', 8, [('a', 'q'), ('b', 'd')]))
    r = check_facts(export_model(m, pos))
    assert r['counts']['no_landing'] == 1
    assert r['counts']['hops_over'] == 1


def test_channel_envelope_excludes_hard_blocks_but_keeps_relay_rows():
    m, pos = fixture()
    cs = channels(m)
    inside = lambda x, y: any(a <= x <= c and b <= y <= d for a,b,c,d in cs)
    assert not inside(35, 15)  # macro interior
    assert inside(105, 15)  # actual allocated relay frame's channel
    assert inside(35, 5)  # actual free horizontal band
    m['insts'] = [Inst(name='wall', master='wall', x=0, y=0, w=1000, h=100, kind='block')]
    with pytest.raises(ValueError, match='no vacant'):
        channels(m)


def test_no_site_failure_despite_individually_short_hops():
    m, pos = fixture()
    f = export_model(m, pos)
    f['channels'] = [[0., 50., 1000., 100.]]
    f['wires'] = [dict(id='unsited', pts=[[0., 5.], [300., 5.], [600., 5.]])]
    r = check_facts(f)
    assert r['counts']['hops_over'] == 0 and r['counts']['wires_no_site'] == 1


def test_case_hook_writes_final_output(tmp_path):
    import json
    m, pos = fixture()
    def emit(model, work):
        work.mkdir()
        return 'emitted'
    v = Inst(case_real=emit)
    install(v, m, lambda: pos)
    assert v.case_real(m, tmp_path / 'case') == 'emitted'
    doc = json.loads((tmp_path / 'case/gen_safety_facts.json').read_text())
    assert doc['schema'] == 'opentallas.die_gen_safety_facts.v1'
    assert len(doc['wires']) == 1


def test_foreign_reset_into_forwarded_lane_is_still_checked():
    m, pos = fixture()
    m['buses'].append(('foreign_rst', 'reset', 1, [('b', 'rst_q'), ('h0', 'en')]))
    f = export_model(m, pos)
    bad = [c for c in f['crossings'] if c['id'] == 'foreign_rst']
    assert len(bad) == 1 and bad[0]['landing'] is None
    assert check_facts(f)['counts']['no_landing'] == 1


def test_port_clock_identity_beats_unrelated_shared_macro_clock():
    m, pos = fixture()
    m['buses'].append(('extra_b', 'clock_trunk', 1, [('pll', 'cc'), ('a', 'ck_other'), ('b', 'ck_other')]))
    m['dv_cluster_clocks'] = dict(master='block', related_pins=dict(q=['ck']*8, d=['ck']*8))
    m['buses'].append(('direct', 'data', 8, [('a', 'q'), ('b', 'd')]))
    cs = [c for c in export_model(m, pos)['crossings'] if c['id'] == 'direct']
    assert len(cs) == 1 and cs[0]['src_region'] == 'clk_a' and cs[0]['dst_region'] == 'clk_b'
    m['buses'] = [b for b in m['buses'] if b[0] != 'clk_b']
    cs = [c for c in export_model(m, pos)['crossings'] if c['id'] == 'direct']
    assert cs[0]['dst_region'] == 'UNDRIVEN:b/ck'


def test_site_check_spans_unavailable_relay_sites_across_actual_chain():
    m, pos = fixture()
    m['insts'].append(Inst(name='wall', master='opaque', x=0, y=0, w=900, h=30, kind='block'))
    f = export_model(m, pos)
    r = check_facts(f)
    assert r['counts']['hops_over'] == 0
    assert r['counts']['wires_no_site'] == 1


def test_worst_corresponding_bit_is_exported_not_group_centroid():
    m, pos = fixture()
    def bits(i, p, width):
        x, y = pos(i, p)
        return [(x + (200 if i == 'b' and k == 7 else 0), y) for k in range(width)]
    pos.bits = bits
    f = export_model(m, pos)
    assert not f['centroid_only_segments']
    assert f['wires'][0]['segments'][-1]['worst_net_bit'] == 7
    # The paired edge really exists; no mixing an arbitrary source and sink bit.
    assert f['wires'][0]['pts'][-1] == [650, 5.]


def test_actual_two_stage_reset_landing_is_separately_described():
    m, pos = fixture()
    m['insts'].append(Inst(name='rstcap', master='qfd_rst_rep_p8', x=60, y=10, w=10, h=10, kind='reset_rep'))
    m['buses'].append(('rstcap_ck', 'clock_trunk', 1, [('pll', 'cb'), ('rstcap', 'ck')]))
    m['buses'].append(('rst_x', 'reset', 1, [('a', 'q'), ('rstcap', 'd')]))
    f = export_model(m, pos)
    assert f['reset_landings'][0]['landing'] == 'rstcap'
    assert f['reset_landings'][0]['kind'] == 'two_stage_reset_synchronizer'
    assert not [c for c in f['crossings'] if c['id'] == 'rst_x']


def test_generator_strict_bit_geometry_preserves_orientation_and_slice_identity():
    # Exercise the real helper without importing the whole die generator graph.
    import ast
    import re
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / 'qwen_rom_fulldie_b3r2.py'
    fn = next(n for n in ast.parse(src.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_pin_pos')
    scope = dict(re=re)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'), scope)
    master = Inst(order=['q'])
    v = Inst(masters=lambda m, k: {'block': master},
             port_widths=lambda m, k: {('block', 'q'): 4},
             pin_rects=lambda *a: [(f'q[{k}]', 'M4', (k*10, 0, k*10+2, 2)) for k in range(4)])
    i = Inst(name='p', master='block', x=100, y=50, w=40, h=10, cx=120, cy=55, orient='MY')
    model = dict(insts=[i])
    pos = scope['_pin_pos'](v, model, strict=True)
    assert pos.bits('p', 'q[3:2]', 2) == [(119, 51), (109, 51)]
    assert pos.bits('p', 'q[2:3]', 2) == [(109, 51), (119, 51)]
    assert pos('p', 'q') == (124, 51)
    with pytest.raises(ValueError, match='no pin geometry'):
        pos('p', 'missing')
    legacy = scope['_pin_pos'](v, model)
    assert legacy('p', 'q[3:2]') == (120, 55)  # original planning behavior


def test_reserved_relay_keepout_is_not_claimed_as_cell_row():
    m, pos = fixture()
    m['relay_keepouts'] = [dict(rect=[50., 0., 80., 30.])]
    assert not any(a < 60 < c and b < 15 < d for a,b,c,d in channels(m))


def test_real_vector_clock_alias_resolves_related_pin_without_guessing():
    m, pos = fixture()
    m['buses'][0][3].append(('b', 'face_ck6'))
    m['port_join'] = dict(block=dict(face_ck6=('face_ck', [6]), fdi_rx_ck0=('fdi_rx_ck', [0])))
    m['dv_cluster_clocks'] = dict(master='block', related_pins=dict(q=['ck']*8, d=['face_ck[6]']*8))
    m['buses'].append(('direct', 'data', 8, [('a', 'q'), ('b', 'd')]))
    f = export_model(m, pos)
    assert not [c for c in f['crossings'] if c['id'] == 'direct']
    assert not any(k.startswith('UNDRIVEN:b/face_ck') for k in f['regions'])


def test_actual_reset_q_copy_ports_are_traced_across_branches():
    from qwen_split.gen_safety_facts import relay_chains
    by = {n: Inst(kind='reset_rep' if n.startswith('r') else 'block') for n in ('a','r0','r1','b','c')}
    def w(n, si, sp, di, dp, x0, x1):
        return dict(id=n,src=[si,sp],dst=[di,dp],pts=[[x0,5],[x1,5]],kind='reset',bits=1)
    ws = [w('a','a','q','r0','d',0,200),w('b','r0','q0','r1','d',210,400),
          w('c','r1','q0','b','d',410,600),w('d','r1','q1','c','d',410,650)]
    chains=relay_chains(ws,by)
    assert len(chains)==2 and all(len(c['segments'])==3 for c in chains)
    f=dict(regions={},crossings=[],channels=[[0,50,1000,100]],wires=chains)
    r=check_facts(f)
    assert r['counts']['hops_over']==0 and r['counts']['wires_no_site']==2


def test_package_reset_synchronizer_is_not_a_clocked_data_capture():
    m, pos = fixture()
    m['insts'].append(Inst(name='rstsync', master='qfd_rstsync', x=60, y=10, w=10, h=10, kind='block'))
    m['buses'].append(('rstsync_ck', 'clock_trunk', 1, [('pll', 'cb'), ('rstsync', 'ck')]))
    m['buses'].append(('package_rst', 'reset', 1, [('a', 'q'), ('rstsync', 'arst_n')]))
    f = export_model(m, pos)
    assert not [c for c in f['crossings'] if c['id'] == 'package_rst']
    assert f['reset_landings'][-1]['kind'] == 'package_reset_synchronizer'
    m['insts'][-1].master = 'raw_reset_flop'
    assert [c for c in export_model(m, pos)['crossings'] if c['id'] == 'package_rst']
