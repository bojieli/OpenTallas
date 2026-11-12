"""CLAND-WSTART-1 respace: same depth, core- and band-clear sites, every hop <= 405, landing_place relocates none."""
import copy
import json
import wstart_respace as R


def vehicle():
    return {'outline_um': [1200.0, 2500.0],
            'hard_cores': [{'origin_um': [86.0, 69.0], 'outline_um': [458.0, 1158.0]},
                           {'origin_um': [86.0, 1305.0], 'outline_um': [458.0, 1157.0]}],
            'clock': {'landing_contract': {
                          'bands': {'w': {'rect_um': [19.4, 300.0, 71.3, 400.0]}},
                          'pins': [{'name': 'cland_fstart_out_y_o', 'dir': 'out', 'xy_um': [2.1, 2490.0]}]},
                      'landing_reader_start': {'origin_rect_um': [247.0, 61.5, 264.3, 78.8], 'branches': {}},
                      'landing_writer_start': {'depth': 7, 'branches': {'y_o': {'stages': [
                          {'xy_um': [224.3 - 31.7 * i, 369.9 + 304.3 * i], 'raw_reset': f'rst_rl_{i}'} for i in range(7)]}}}}}


def test_respaced_chain_is_clear_same_depth_and_short():
    P = {'partition_types': {'T': vehicle()}}
    rows = R.plan_rows(P, ['T'])
    assert len(rows) == 1 and rows[0]['ok'], rows
    r = rows[0]
    assert r['old_max_hop'] > R.LIMIT and r['new_max_hop'] <= R.LIMIT and r['relocated'] == 0
    assert [s['raw_reset'] for s in r['stages']] == [f'rst_rl_{i}' for i in range(7)]
    t = P['partition_types']['T']
    for s in r['stages']:
        assert not R._inside(s['xy_um'], R._cores(t)) and not R._inside(s['xy_um'], R._bands(t), grow=2.16)


def test_apply_replaces_only_listed_branches_and_keeps_depth(tmp_path):
    P = {'partition_types': {'T': vehicle(), 'U': vehicle()}}
    base = tmp_path / 'p.json'; base.write_text(json.dumps(P))
    delta = tmp_path / 'd.json'; out = tmp_path / 'o.json'
    assert R.main(['delta', str(base), str(delta), 'T']) == 0
    assert R.main(['apply', str(base), str(delta), str(out)]) == 0
    Q = json.loads(out.read_text())
    assert Q['partition_types']['U'] == P['partition_types']['U']
    assert len(Q['partition_types']['T']['clock']['landing_writer_start']['branches']['y_o']['stages']) == 7
    assert R.plan_rows(Q, ['T']) == []          # nothing left over the limit
    bad = json.loads(delta.read_text()); bad['types']['T']['y_o'] = bad['types']['T']['y_o'][:-1]
    delta.write_text(json.dumps(bad))
    import pytest
    with pytest.raises(SystemExit, match='depth changed'):
        R.main(['apply', str(base), str(delta), str(out)])
