"""Matched nominal tap arrivals cannot hide uncommon early/late damage."""
import argparse
import json
from pathlib import Path
import pytest
import die_clock as D
import schema as S


def test_equal_nominal_arrivals_still_have_uncommon_damage():
    r=D.pair_clock_damage(1000,890,1000,890,0.17)
    assert r['max_damage_ps']==pytest.approx(109.83)
    assert r['cppr_credit_ps']==pytest.approx(0.17)


def test_shared_prefix_credit_only_and_missing_credit_conservative():
    assert D.pair_clock_damage(1000,890,1000,890,110)['max_damage_ps']==0
    assert D.pair_clock_damage(1000,890,1000,890)['max_damage_ps']==110
    assert D.pair_clock_damage(1000,890,1000,890,500)['cppr_credit_ps']==110


def test_actual_qc_common_root_range_matches_sta_hold_credit():
    r=D.pair_clock_damage(6254.66561,6147.60742,6257.99561,6150.94,20.51448-20.34690)
    assert r['hold_damage_ps']==pytest.approx(110.22061)


def test_node_reader_keeps_early_column_and_legacy_api(tmp_path):
    f=tmp_path/'arr.txt'
    f.write_text('N n0 20.51448 20.34690\nT p 1000 890 20\n')
    assert D.read_node_ranges(f)['n0']==(20.51448,20.34690)
    assert len(D.read_arr(f))==4
    assert D.read_arr(f)[3]['n0']==20.51448


def test_report_gates_damage_while_retaining_nominal_info(tmp_path):
    plan=Path(__file__).parent/'examples/s81_pair/s81_pair_plan.json'
    raw=json.loads(plan.read_text())
    actual_plan=tmp_path/'plan.json';actual_plan.write_text(json.dumps(raw))
    T,tree=D.build(S.Plan(raw),leaf_um=1000,rep_um=450,keep=[])
    (tmp_path/'tree.json').write_text(json.dumps(tree))
    rows=[f"T {t['port']} 1000 890 20\n" for t in tree['taps']]
    rows += [f'N {n} 20.51448 20.34690\n' for n in T.cells]
    for corner in ('TT','FF'):
        (tmp_path/f'arr_{corner}.txt').write_text(''.join(rows))
    D.cmd_report(argparse.Namespace(plan=str(actual_plan),dir=str(tmp_path)))
    report=json.loads((tmp_path/'clock_report.json').read_text())
    for corner in ('TT','FF'):
        assert report['verdict'][corner]['gate']=='FAIL'
        assert report['corners'][corner]['seam']['nominal_max_abs_ps']==0
        assert report['corners'][corner]['seam']['gate_max_ps']>100


def test_damage_does_not_round_a_failure_down_to_eighty():
    assert D.pair_clock_damage(1000,919.999999,1000,919.999999)['max_damage_ps']>80
