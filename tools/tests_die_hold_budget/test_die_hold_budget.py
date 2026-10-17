"""tools/die_hold_budget.py: OpenSTA full_clock_expanded FF min dumps (ideal latency, propagated tree, ETM macros)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import die_hold_budget as D  # noqa: E402


def _p(name):
    return D.parse((HERE / name).read_text())


def test_ideal_latency_layout():
    a = {(p['start'], p['end']): p for p in _p('ideal_ff.rpt')}
    r = a[('a', 'c')]
    assert (r['L'], r['Cap'], r['delta']) == (40.0, 130.0, 90.0)     # uncertainty printed above the clock pin
    assert (r['launch_min'], r['wire'], r['hold'], r['U']) == (29.3, 14.0, 8.7, 25.0)
    assert r['slack'] == -80.4


def test_propagated_layout():
    a = {(p['start'], p['end']): p for p in _p('propagated_ff.rpt')}
    r = a[('a', 'c')]
    assert (r['L'], r['Cap'], r['delta'], r['launch_min'], r['wire']) == (20.8, 9.8, -11.0, 30.7, 14.1)
    assert r['start_clock_pin'] == 'a/CLK' and r['end_clock_pin'] == 'c/CLK'
    # the reconstructed hold equation equals the reported slack
    assert abs(r['L'] + r['launch_min'] + r['wire'] - (r['Cap'] + r['U'] + r['crpr'] + r['hold']) - r['slack']) < 0.11


def test_etm_launch_min_from_bound_view_and_classes():
    paths = _p('etm_ff.rpt')
    a = {(p['start'], p['end']): p for p in paths}
    assert a[('u_a', 'u_b')]['launch_min'] == 55.0          # ETM clk->out min (fall 55 < rise 60), no placeholder
    assert a[('u_r', 'u_c')]['launch_min'] == 30.0
    rec = D.classify(paths, {}, paths_cap=100, design='t')
    lk = {(x['sender'], x['receiver']): x for v in rec['worst_links'].values() for x in v}
    assert lk[('u_a', 'u_b')]['fix'] == 'SKEW_GT80'           # delta 100 > 80: clock fix, never a hold pad
    assert rec['counts']['skew_fail_links'] == 1 and rec['verdict'] == 'FAIL'
    assert rec['counts']['by_fix'] == {'PASS': 2, 'SKEW_GT80': 1}
    assert rec['link_classes']['tile_etm->tile_etm']['max_abs_delta'] == 100.0


def _path(s, e, sm, em, slack, delta=20.0, U=25.0):
    return dict(start=s, end=e, start_kind='reg', end_kind='reg', start_master=sm, end_master=em, slack=slack,
                delta=delta, launch_min=30.0, wire=5.0, hold=10.0, U=U, crpr=0.0)


def test_fix_classes_relay_holdcell_diagnostic():
    ps = [_path('t1', 't2', 'tileA', 'tileB', -12.0), _path('t1', 't2', 'tileA', 'tileB', -3.0),
          _path('t3', 'r1', 'tileA', 'hbfd_rly_48_WE', -7.0), _path('p1', 't4', 'interimX', 'tileB', -9.0),
          _path('t5', 't6', 'tileA', 'tileB', 4.0)]
    rec = D.classify(ps, {'diagnostic': ['interimX']}, paths_cap=None)
    assert rec['counts']['by_fix'] == {'DIAGNOSTIC_PLACEHOLDER': 1, 'DIE_NET_HOLD_CELL': 1, 'PASS': 1, 'RELAY_STATION': 1}
    hc = rec['worst_links']['DIE_NET_HOLD_CELL'][0]
    assert hc['bits'] == 2 and hc['demand_ps'] == 12.0
    assert rec['placeholder_senders'] == ['interimX']
    assert rec['verdict'] == 'FAIL'


def test_verdicts_u_truncation_diagnostic():
    ok = [_path('t1', 't2', 'tileA', 'tileB', 4.0)]
    assert D.classify(ok)['verdict'] == 'PASS'
    assert D.classify(ok, paths_cap=1)['verdict'] == 'DIAGNOSTIC'                        # dump may be truncated
    assert D.classify(ok, {'diagnostic': ['tileB']})['verdict'] == 'DIAGNOSTIC'          # placeholder receiver
    assert D.classify(ok, {'diagnostic_all': 'ideal clocks'})['verdict'] == 'DIAGNOSTIC'
    low_u = [_path('t1', 't2', 'tileA', 'tileB', 4.0, U=10.0)]
    r = D.classify(low_u)
    assert r['verdict'] == 'FAIL' and r['counts']['paths_with_U_below_25'] == 1           # U relaxed: refused
    r = D.classify([_path('t1', 't2', 'tileA', 'tileB', 4.0, U=31.0)])
    assert r['verdict'] == 'PASS' and r['counts']['paths_with_U_above_25'] == 1           # clock-OCV pair: reported


def test_qwen_views(tmp_path):
    v = tmp_path / 'views.json'
    v.write_text(json.dumps({'real': {'tile_etm': {}}, 'hard_macro': {}, 'assumed': ['dsfd_rly_66_SW']}))
    out = tmp_path / 'o.json'
    D.main(['classify', '--report', str(HERE / 'etm_ff.rpt'), '--out', str(out), '--qwen-views', str(v)])
    r = json.loads(out.read_text())
    assert r['counts']['diagnostic_links'] == 2 and r['verdict'] == 'FAIL'                 # skew FAIL still wins


def test_cli(tmp_path):
    m = tmp_path / 'm.json'
    m.write_text(json.dumps({'diagnostic': []}))
    out = tmp_path / 'o.json'
    assert D.main(['classify', '--report', str(HERE / 'etm_ff.rpt'), '--out', str(out), '--masters', str(m),
                   '--paths-cap', '100', '--design', 'unit']) == 0
    assert json.loads(out.read_text())['coverage']['links'] == 3


def test_tcl_dump_line():
    assert D.tcl_dump('/run/hold_links_ff.rpt', 1000) == (
        'report_checks -path_delay min -group_path_count 1000 -endpoint_path_count 1 -format full_clock_expanded '
        '-digits 1 > /run/hold_links_ff.rpt')


def test_qwen_clock_tcl_hold_budget():
    sys.path.insert(0, str(HERE.parent / 'qwen_tp8'))
    sys.path.insert(0, str(HERE.parent))
    from qwen_tp8 import die_sta_libs as Q
    doms = {'stream': [('a/ck', 'A', 'ck'), ('b/ck', 'B', 'ck')]}
    leaves = {'A': {'tt': {'ck': 100}}, 'B': {'tt': {'ck': 301}}}
    legacy = Q.clock_tcl(doms, leaves, 'tt')
    assert legacy == Q.clock_tcl(doms, leaves, 'tt', hold_budget='tile')       # default byte-identical
    assert '-hold 100.000000' in legacy and '-hold 25.000000' not in legacy
    die = Q.clock_tcl(doms, leaves, 'tt', hold_budget='die')
    assert '-hold 100.000000' not in die and die.count('-hold 25.000000') == 4
    assert '-setup 210.000000' in die                                           # setup unchanged
