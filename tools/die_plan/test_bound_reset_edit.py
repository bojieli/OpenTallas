"""bound_reset_edit: plain relay + pad-station re-sites on a bound reset kit (SERDES-KITWIN-1111 follow-up)."""
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import bound_reset_contract as BRC
import bound_reset_edit as E
import gen_phys as G
import gen_rtl
import reset_tree as R


def tree(lockup=True):
    rl = [dict(name='u_rrl_0', d='rst_root_n', q='rst_rl_0', xy=[17.28, 17.28], depth=1, tap=0, kind='tap'),
          dict(name='u_rrl_1', d='rst_rl_0', q='rst_rl_1', xy=[17.28, 380.0], depth=2, tap=1, kind='tap'),
          dict(name='u_rrl_2', d='rst_rl_1', q='rst_rl_2', xy=[17.28, 200.0], depth=3, tap=1, kind='pad'),
          dict(name='u_rrl_3', d='rst_rl_2', q='rst_n_t1', xy=[17.28, 380.0], depth=4, tap=1, kind='pad'),
          dict(name='u_rrl_4', d='rst_rl_0', q='rst_rl_4', xy=[300.0, 17.28], depth=2, tap=0, kind='tap'),
          dict(name='u_rrl_5', d='rst_rl_4', q='rst_rl_5', xy=[300.0, 17.28], depth=3, tap=0, kind='pad'),
          dict(name='u_rrl_6', d='rst_rl_5', q='rst_n_t0', xy=[300.0, 17.28], depth=4, tap=0, kind='pad')]
    t = dict(type='t', entry='relayed', sync_stages=2, root=[8.64, 8.64], start=False, relays=rl, taps=['clk', 'clk_t1'],
             own_depth=4, depth=4, n_tree=3, n_pad=4, max_hop_um=362.72, reach_um=405, outs=[], core_resets=[],
             relay_driver=False)
    if lockup:
        t['relay_lockup'] = 'negedge'
    return t


def make_kit(tmp_path):
    t = tree()
    text = ('module top(input clk, arst_n);\n bound u_bound(.clk(clk), .arst_n(arst_n));\nendmodule\n'
            'module bound(input clk, arst_n);\n' + '\n'.join(R.rtl_lines(t)) + '\nendmodule\n' + gen_rtl.CELLS
            + getattr(gen_rtl, 'LOCKUP_CELLS', ''))
    kit = tmp_path / 'kit'
    (kit / 'rtl').mkdir(parents=True)
    f = kit / 'rtl' / 'bound.sv'
    f.write_text(text)
    p = SimpleNamespace(types={'t': dict(module='top', outline_um=[1000, 1000],
                                         clock=dict(landing_contract=dict(collector_tree=t)))})
    c = G.install_bound_native_reset(p, 't', [f])
    src = BRC.emitted(f, 't', t)
    for x in ('bound.reset_tree.json', 'bound.reset_tree.tcl'):
        (kit / 'rtl' / x).unlink()
    BRC.stage(kit / 'rtl', src, c)
    return kit


def review(tmp_path):
    img = tmp_path / 'r.png'
    img.write_bytes(b'png')
    return dict(verdict='PASS', image=str(img), findings=['viewed'])


def snap(kit):
    return {p.name: p.read_bytes() for p in (kit / 'rtl').iterdir()}


def test_default_touches_nothing(tmp_path):
    kit = make_kit(tmp_path)
    a = snap(kit)
    rep = E.edit(kit)
    assert snap(kit) == a and rep['plain'] is False and not rep['station']


def test_plain_swaps_only_the_relay_cells_and_matches_the_generator(tmp_path):
    kit = make_kit(tmp_path)
    assert 'ot_dp_rrelay_nl u_rrl_1 ' in (kit / 'rtl/bound.sv').read_text()
    rep = E.edit(kit, plain=True)
    new = (kit / 'rtl/bound.sv').read_text()
    rec = json.loads((kit / 'rtl/bound_reset.json').read_text())
    assert not re.search(r'ot_dp_rrelay_nl u_rrl', new) and rep['depth_map_unchanged']
    assert 'relay_lockup' not in rec['tree'] and rec['tree_sha256'] == BRC.digest(rec['tree'])
    want = {re.sub(r'\s+', ' ', x.strip()) for x in R.rtl_lines(rec['tree']) if 'u_rrl_' in x}
    have = {re.sub(r'\s+', ' ', x.strip()) for x in new.split('\n') if re.search(r'\bot_dp_rrelay\s+u_rrl_', x)}
    assert want == have
    assert rec['verified_cell_classes'] == ['ot_dp_rrelay']


def test_station_moves_a_pad_to_the_hop_midpoint_and_keeps_graph_and_depths(tmp_path):
    kit = make_kit(tmp_path)
    a = json.loads((kit / 'rtl/bound_reset.json').read_text())
    tcl0 = (kit / 'rtl/reset_tree.tcl').read_text()
    rtl0 = (kit / 'rtl/bound.sv').read_bytes()
    rep = E.edit(kit, station=[('u_rrl_1', 'u_rrl_2')], review=review(tmp_path))
    rec = json.loads((kit / 'rtl/bound_reset.json').read_text())
    assert rep['sites'] == {'u_rrl_2': [17.28, 290.0]}            # midpoint of (17.28, 380) and (17.28, 200)
    assert rec['placement_sites'] == rep['sites'] and rec['placement_review']['verdict'] == 'PASS'
    assert E.depth_map(rec['tree']) == E.depth_map(a['tree']) and rec['tree'] == a['tree']
    assert (kit / 'rtl/bound.sv').read_bytes() == rtl0            # sites only: the RTL is not touched
    d = [x for x in zip(tcl0.split('\n'), (kit / 'rtl/reset_tree.tcl').read_text().split('\n')) if x[0] != x[1]]
    assert len(d) == 1 and 'rst_rl_2' in d[0][1] and '290.000' in d[0][1]
    assert rec['placement_tcl_sha256'] == __import__('hashlib').sha256((kit / 'rtl/reset_tree.tcl').read_bytes()).hexdigest()


def test_station_refuses_tap_relays_unfed_pairs_and_missing_review(tmp_path):
    kit = make_kit(tmp_path)
    a = snap(kit)
    with pytest.raises(SystemExit, match='PAD relays'):
        E.edit(kit, station=[('u_rrl_0', 'u_rrl_1')], review=review(tmp_path))
    with pytest.raises(SystemExit, match='not fed by'):
        E.edit(kit, station=[('u_rrl_5', 'u_rrl_2')], review=review(tmp_path))
    with pytest.raises(SystemExit, match='PASS review'):
        E.edit(kit, station=[('u_rrl_1', 'u_rrl_2')], review=dict(verdict='FAIL', image='x', findings=['a']))
    with pytest.raises(SystemExit, match='PASS review'):
        E.edit(kit, station=[('u_rrl_1', 'u_rrl_2')], review=None)
    assert snap(kit) == a                                         # every refusal leaves the kit untouched


def test_station_reach_is_enforced(tmp_path):
    kit = make_kit(tmp_path)
    rec = json.loads((kit / 'rtl/bound_reset.json').read_text())
    rec['tree']['reach_um'] = 100
    rec['tree_sha256'] = BRC.digest(rec['tree'])
    (kit / 'rtl/bound_reset.json').write_text(json.dumps(rec))
    with pytest.raises(SystemExit, match='beyond the reach'):
        E.edit(kit, station=[('u_rrl_1', 'u_rrl_2')], review=review(tmp_path))


def test_depth_map_counts_relays_from_the_root():
    t = tree()
    assert E.depth_map(t) == {'rst_rl_0': 1, 'rst_rl_1': 2, 'rst_rl_2': 3, 'rst_n_t1': 4, 'rst_rl_4': 2, 'rst_rl_5': 3,
                              'rst_n_t0': 4}
