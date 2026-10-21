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
    assert len(facts['wires']) == 3
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
    assert len(doc['wires']) == 3
