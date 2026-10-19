"""tools/die_hold_budget.py: OpenSTA full_clock_expanded FF min dumps (ideal latency, propagated tree, ETM macros)."""
import re
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


def test_zero_ideal_clocks_are_diagnostic():
    # no die clock model at all (cluster --cts none): every network delay is ideal 0 -> links DIAGNOSTIC, not PASS
    t = re.sub(r'(?m)^\s*-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?(\s+clock network delay \(ideal\))', r'   0.0    0.0\1',
               (HERE / 'etm_ff.rpt').read_text())
    r = D.classify(D.parse(t))
    assert r['counts']['ideal_clock_links'] == r['coverage']['links'] == 3
    assert r['verdict'] in ('DIAGNOSTIC', 'FAIL')
    r2 = D.classify(D.parse((HERE / 'etm_ff.rpt').read_text()))
    assert r2['counts']['ideal_clock_links'] == 0      # ideal clocks carrying plan latencies stay judged


DEEP = """Startpoint: n59 (rising edge-triggered flip-flop clocked by stream)
Endpoint: d2d (rising edge-triggered flip-flop clocked by stream__early)
Path Group: stream__early
Path Type: min

 Delay   Time   Description
-------------------------------------------------------
   0.0    0.0   clock stream (rise edge)
   0.0    0.0   clock source latency
   0.0    0.0 ^ n59/ck[0] (shallow_tile)
  48.4   48.4 ^ n59/q[0] (shallow_tile)
  63.2  111.6 ^ d2d/d[0] (deep_tile)
        111.6   data arrival time

   0.0    0.0   clock stream__early (rise edge)
{LAT} {LAT}   clock source latency
   0.0 {LAT} ^ d2d/ck (deep_tile)
  25.0 -317.7   inter-clock uncertainty
   0.0 -317.7   clock reconvergence pessimism
 258.5  -59.2   library hold time
        -59.2   data required time
-------------------------------------------------------
        -59.2   data required time
       -111.6   data arrival time
-------------------------------------------------------
        170.8   slack (MET)
"""


def test_declared_insertion_judges_skew_at_child_flops(tmp_path):
    """Q-DIE13: a deep tile tapped early by its measured insertion matches its neighbour at the flops"""
    ins = {'deep_tile': {'ck': 342.7}, 'shallow_tile': {'ck[0]': 0.0}}
    tapped = D.parse(DEEP.replace('{LAT}', '-342.7'))
    assert tapped[0]['src_lat_launch'] == 0.0 and tapped[0]['src_lat_capture'] == -342.7
    assert D.classify(tapped)['counts']['skew_fail_links'] == 1              # judged at the pins: 343 > 80
    r = D.classify(tapped, insertion=ins)
    assert r['counts']['skew_fail_links'] == 0 and r['counts']['tap_mismatch_links'] == 0 and r['verdict'] == 'PASS'
    assert r['params']['skew_at'].startswith('child flops')
    # the same tile NOT tapped early: boundary delta 0, but its flops see the full 343 ps -> still a skew FAIL
    flat = D.parse(DEEP.replace('{LAT}', '   0.0'))
    r = D.classify(flat, insertion=ins)
    assert r['counts']['skew_fail_links'] == 1 and r['counts']['tap_mismatch_links'] == 1 and r['verdict'] == 'FAIL'
    # CLI: insertion_ps from views.json at the ff corner
    v = tmp_path / 'views.json'
    v.write_text(json.dumps({'real': {'deep_tile': {}, 'shallow_tile': {}}, 'hard_macro': {}, 'assumed': [],
                             'insertion_ps': {'deep_tile': {'tt': {'ck': 420.7}, 'ff': {'ck': 342.7}}}}))
    rp = tmp_path / 'r.rpt'; rp.write_text(DEEP.replace('{LAT}', '-342.7'))
    out = tmp_path / 'o.json'
    D.main(['classify', '--report', str(rp), '--out', str(out), '--qwen-views', str(v)])
    assert json.loads(out.read_text())['verdict'] == 'PASS'


def test_tap_mismatch_fails_even_when_pair_skew_cancels():
    # Two equally mistapped tiles have zero pair skew; that cannot validate the
    # declaration that the physical clock taps compensate their measured insertion.
    p = _path('a', 'b', 'deep', 'deep', 20.0, delta=0.0)
    p.update(src_lat_launch=-300.0, src_lat_capture=-300.0,
             start_clock_pin='a/ck', end_clock_pin='b/ck')
    r = D.classify([p], insertion={'deep': {'ck': 342.7}})
    assert r['counts']['skew_fail_links'] == 0
    assert r['counts']['tap_mismatch_links'] == 1
    assert r['verdict'] == 'FAIL'
    p.update(src_lat_launch=-342.7, src_lat_capture=-342.7)
    assert D.classify([p], insertion={'deep': {'ck': 342.7}})['verdict'] == 'PASS'
