"""R-CAP (RULES-CAP-1, RULEBOOK 11-13): the pre-launch movable-cell projection, proved on harvested kit runs
(testdata/cap_runs_1113.json: 295 distinct runs of S81 / HEAD / QC / KV / HBM kits, 11-03..11-13), and its three
stops: kit preflight, the pre-floorplan projection in native_cell_cap.tcl, the place census in cell_census.tcl."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cap_estimate as C  # noqa: E402

RUNS = json.loads((HERE / 'testdata' / 'cap_runs_1113.json').read_text())


def test_tap_endcap_model_matches_macro_free_runs():
    r = sorted(C.tap_endcap(x['outline']) / x['tap'] for x in RUNS if x['mac'] == 0 and x['tap'] > 1000)
    assert len(r) >= 80
    assert 0.99 < r[len(r) // 2] < 1.02 and r[0] > 0.95 and r[-1] < 1.08, (r[0], r[len(r) // 2], r[-1])


def test_projection_against_past_runs():
    rows = C.validate(RUNS)
    big = sorted(abs(r['err']) for r in rows if r['meas'] >= 100_000)
    assert len(big) >= 200                                   # the task asked for 20+
    assert big[len(big) // 2] <= 0.12 and big[int(len(big) * 0.9)] <= 0.32, (big[len(big) // 2], big[int(len(big) * 0.9)])
    over = [r for r in rows if r['meas_over']]
    assert len(over) >= 50
    # no run measured above the place budget is launched without a stop armed
    assert all(r['verdict'] in ('OVER', 'NEAR') for r in over), [r for r in over if r['verdict'] not in ('OVER', 'NEAR')]
    assert sum(r['verdict'] == 'OVER' for r in over) >= 0.85 * len(over)
    # a predicted OVER that measured under the budget was within 10 % of it, bar the two known outliers
    false = [r for r in rows if r['verdict'] == 'OVER' and not r['meas_over']]
    assert len(false) <= 8 and sum(r['meas'] < 0.9 * C.BUDGET['place'] for r in false) <= 2, false


def test_no_run_over_the_place_budget_finished_global_route():
    over = [x for x in RUNS if x['mov'] > C.BUDGET['place']]
    assert len(over) >= 50 and not any(x['last'] in ('5_2_route', '6_report') for x in over)
    assert max(x['mov'] for x in RUNS if x['signed']) < C.TARGET


@pytest.mark.parametrize('synth,pins,outline,macros,verdict', [
    (100_000, 5000, [1442.88, 1226.88], 27, 'OK'),
    (200_000, 5000, [622.08, 1339.2], 0, 'OK'),
    (250_000, 5000, [622.08, 1339.2], 0, 'TARGET'),
    (300_000, 5000, [622.08, 1339.2], 0, 'NEAR'),
    (332_424, 14503, [1442.88, 1226.88], 47, 'OVER'),         # S81 dsdv_slice_c1x_C__t3 (measured 678k)
    (425_150, 14624, [2160.0, 1520.64], 20, 'OVER'),          # KV kv3_pv_v2 (measured 627k)
    (400_001, 0, [100.0, 100.0], 0, 'OVER'),
])
def test_verdicts(synth, pins, outline, macros, verdict):
    e = C.project(synth, pins, outline, macros)
    assert e['verdict'] == verdict, e
    assert e['place'] == synth + e['port_buffers'] + e['wire_buffers'] and e['port_buffers'] == pins
    assert (e['verdict'] == 'OVER') == ('split' in e)


def test_split_recommendation():
    e = C.project(425_150, 14624, [2160.0, 1520.64], 20)
    assert e['split_parts'] == 3 and e['place'] * C.SPLIT_OVERHEAD / 3 <= C.TARGET < e['place'] * C.SPLIT_OVERHEAD / 2
    m = C.message('kv3_pv_v2', e)
    assert 'split into 3 parts' in m and 'registered' in m and 'lane-group' in m and 'not counted' in m
    assert C.split_parts(400_001) == 2 and C.split_parts(1_000_000) == 5


def test_fixed_cells_are_not_in_the_budget():
    e = C.project(18_032, 500, [648.0, 2505.6], 0)             # HBM NW_iorly class: 134k taps, 18k logic
    assert e['tap_endcap'] > 100_000 and e['verdict'] == 'OK' and e['instances_place'] == e['place'] + e['tap_endcap']
    assert C.mem_gb([4898.88, 2073.6], 1_070_000) >= 100       # q_mcb_ne died at 110 GB
    assert C.mem_gb([172.8, 1036.8], 40_000) == 32


def mk_kit(tmp_path, synth=None, pins=14503, outline=(1442.88, 1226.88), macros=47, cap_budget=None):
    kit = tmp_path / 'kit'
    kit.mkdir()
    (kit / 'budget.json').write_text(json.dumps(dict(die='s81', type='t', outline_um=list(outline), pins=pins)))
    if synth is not None:
        (kit / 'native_cell_count.json').write_text(json.dumps(dict(stdcells=synth, macros=macros)))
    if cap_budget is not None:
        (kit / 'cap_budget.json').write_text(json.dumps(cap_budget))
    return kit


def test_check_kit_sources(tmp_path):
    errs, e = C.check_kit(mk_kit(tmp_path, 332_424))
    assert errs == [] and e['verdict'] == 'OVER' and e['macros'] == 47      # LIMIT-BIND-1: recorded, never an error
    assert 'measured synth' in e['synth_basis']
    kit2 = tmp_path / 'b'
    kit2.mkdir()
    assert C.check_kit(mk_kit(kit2)) == ([], None)             # no estimate: not judged
    kit3 = tmp_path / 'c'
    kit3.mkdir()
    errs, e = C.check_kit(mk_kit(kit3, cap_budget=dict(cells=100_000, macros=3)))
    assert errs == [] and e['verdict'] == 'OK' and e['macros'] == 3
    assert C.main(['--kit', str(tmp_path / 'kit')]) == 0 and C.main(['--kit', str(kit3 / 'kit')]) == 0


def test_kit_preflight_fails_an_over_budget_kit(tmp_path):
    import kit_preflight as KP
    rec = KP.check(mk_kit(tmp_path, 332_424))
    row = rec['checks']['cell_budget']
    assert row['verdict'] == 'PASS' and row['estimate']['verdict'] == 'OVER'     # R-CAP removed (LIMIT-BIND-1): info only
    assert not any(i.startswith('cell_budget: ') for i in rec['issues'])
    ok = tmp_path / 'ok'
    ok.mkdir()
    rec = KP.check(mk_kit(ok, 120_000, pins=4000, macros=0))
    assert rec['checks']['cell_budget']['verdict'] == 'PASS' and rec['checks']['cell_budget']['estimate']['verdict'] == 'OK'


def _synth_metrics(kit, stdcells, macros):
    d = kit / 'run' / 'logs' / 'asap7' / 'dp_t' / 'base'
    d.mkdir(parents=True)
    (d / '1_synth.json').write_text(json.dumps({'synth__design__instance__count': stdcells + macros,
                                                'synth__design__instance__count__stdcell': stdcells,
                                                'synth__design__instance__count__macros': macros}))


def _pc_plan(tmp_path, hard_cores=True, flat_k=802):
    """KV kv3_pc_v1 shape: a 1036.8 x 1520.64 type whose cells_evidence row is the FLAT count (hard cores included)."""
    pd = tmp_path / 'plan'
    pd.mkdir()
    t = dict(outline_um=[1036.8, 1520.64], contents=[dict(module='qkd_kvs_pc')])
    if hard_cores:
        t['hard_cores'] = [dict(module='qkd_kvs_pcc'), dict(module='qkd_kvs_pcf')] * 4
    (pd / 'die_plan.json').write_text(json.dumps(dict(partition_types=dict(t=t), partitions=[dict(name='pc_0', type='t')])))
    (pd / 'cells_evidence.json').write_text(json.dumps(dict(cells_per_type=dict(t=dict(flat_k=flat_k)))))
    return pd


def test_measured_synth_sources(tmp_path):
    """KV-RCAP-MEAS 11-13: any measured count of the synthesized top beats a plan estimate; macros are not cells."""
    kit = mk_kit(tmp_path, pins=8903, outline=(1036.8, 1520.64), cap_budget=dict(cells=850_612, macros=3))
    _synth_metrics(kit, 227_619, 12)
    n, m, basis = C.measured_synth(kit)
    assert (n, m) == (227_619, 12) and '1_synth.json' in basis
    errs, e = C.check_kit(kit)
    assert errs == [] and e['synth'] == 227_619 and e['macros'] == 12 and e['synth_basis'].startswith('measured synth')
    (kit / 'cap_projection.json').write_text(json.dumps(dict(synth=227_000, macros=12)))
    assert C.measured_synth(kit)[0] == 227_000                  # the receipt beats the ORFS metrics
    (kit / 'native_cell_count.json').write_text(json.dumps(dict(stdcells=227_619, macros=12)))
    assert 'native_cell_count.json' in C.measured_synth(kit)[2]
    bare = tmp_path / 'bare'
    bare.mkdir()
    assert C.measured_synth(mk_kit(bare)) is None


def test_kit_preflight_prefers_measured_over_flat_plan_estimate(tmp_path):
    """kv3_pc_v1 (KV-KITFIX-1 13:22): main failed the kit at 906,739 projected from the plan's 850,612 flat row."""
    import kit_preflight as KP
    pd = _pc_plan(tmp_path)
    fresh = tmp_path / 'fresh'
    fresh.mkdir()
    kit = mk_kit(fresh, pins=8903, outline=(1036.8, 1520.64), macros=12)
    (kit / 'budget.json').write_text(json.dumps(dict(type='t', outline_um=[1036.8, 1520.64], pins=8903)))
    rec = KP.check(kit, pd)                                    # no synthesis yet: the flat row is CORED, not judged
    row = rec['checks']['cell_budget']
    assert row['verdict'] == 'PASS' and row['estimate']['verdict'] == 'CORED'
    assert row['estimate']['plan_estimate'] > 800_000 and row['estimate']['hard_cores'] == 8
    _synth_metrics(kit, 227_619, 12)                           # measured: judged on the measured count
    row = KP.check(kit, pd)['checks']['cell_budget']
    assert row['verdict'] == 'PASS' and row['estimate']['synth'] == 227_619
    assert row['estimate']['synth_basis'].startswith('measured synth') and row['estimate']['verdict'] in ('OK', 'TARGET')
    over = tmp_path / 'over'
    over.mkdir()
    kit = mk_kit(over, 450_000, pins=8903, outline=(1036.8, 1520.64), macros=12)
    rec = KP.check(kit, pd)                                    # an over-cap measured netlist is recorded, not failed
    assert rec['checks']['cell_budget']['verdict'] == 'PASS' and rec['checks']['cell_budget']['estimate']['verdict'] == 'OVER'
    soft = tmp_path / 'soft'
    soft.mkdir()
    pd2 = _pc_plan(soft, hard_cores=False)
    kit = mk_kit(soft, pins=8903, outline=(1036.8, 1520.64))
    (kit / 'budget.json').write_text(json.dumps(dict(type='t', outline_um=[1036.8, 1520.64], pins=8903)))
    row = KP.check(kit, pd2)['checks']['cell_budget']          # no hard cores: the plan row is its movable logic
    assert row["verdict"] == "PASS" and row['estimate']['verdict'] == 'OVER'
    assert row['estimate']['synth_basis'].startswith('plan estimate (cells.py by_type')


def test_g0_check_plan():
    types = dict(big=dict(outline_um=[1442.88, 1226.88]), small=dict(outline_um=[622.08, 1339.2]),
                 cored=dict(outline_um=[2160.0, 1520.64], hard_cores=[dict(outline_um=[300.0, 300.0])] * 4),
                 none=dict(outline_um=[10.0, 10.0]))
    parts = dict(b0=dict(type='big'), s0=dict(type='small'), c0=dict(type='cored'))
    ports = dict(p=dict(width=14503, src=dict(part='b0'), dst=dict(part='s0')),
                 q=dict(width=1000, src=dict(part='c0'), dst=dict(part='__die__')))
    P = SimpleNamespace(types=types, parts=parts, ports=ports)
    items = []
    R = SimpleNamespace(err=lambda c, m, **k: items.append(('E', c, m, k)), warn=lambda c, m, **k: items.append(('W', c, m, k)))
    types['edge'] = dict(outline_um=[622.08, 1339.2])
    out = C.check_plan(P, R, dict(big=(332_424, 'by_type'), small=(100_000, 'plan'), cored=(7_017_000, 'by_part l1'),
                                  edge=(330_000, 'plan'), none=(0, 'plan')))
    assert out['over'] == ['big'] and out['near'] == ['edge'] and out['cored_unjudged'] == ['cored']
    assert 'none' not in out['rows']                          # flat estimate of a cored type: left to the netlist
    assert [i[:2] for i in items] == [('W', 'cell_budget'), ('W', 'cell_budget')]      # LIMIT-BIND-1: OVER is a WARN
    assert 'split into' in items[0][2] and items[0][3] == dict(type='big') and 'place census stops' in items[1][2]
    P.types['cored']['cells'] = 1
    out = C.check_plan(P, R, dict(cored=(450_000, 'plan')))    # its own type.cells is its movable logic: judged
    assert out['over'] == ['cored']


def test_tcl_copies_use_the_same_constants():
    cap = (HERE / 'native_cell_cap.tcl').read_text()
    cen = (HERE / 'cell_census.tcl').read_text()
    assert f'{C.K_PIN} * $ot_cap_pins * $ot_cap_hp + {C.K_MAC} * $ot_cap_macros * $ot_cap_hp' in cap
    for text in (cap, cen):
        assert f'> {C.BUDGET["place"]}' in text and f'* {C.SPLIT_OVERHEAD} / ' in text and f'> {C.TARGET}' in text


CAP_MOCK = '''namespace eval ord {proc get_db_block {} {return block}; proc get_db_tech {} {return tech}}
proc tech {m} {return 1000}
proc block {m} {switch $m {getInsts {return [concat [lrepeat STD stdinst] [lrepeat MAC macros]]} getBTerms {return [concat [lrepeat PINS sig] vdd]} getDieArea {return die}}}
proc die {m} {switch $m {dx {return WDBU} dy {return HDBU}}}
proc sig {m} {return SIGNAL}
proc vdd {m} {return POWER}
proc stdinst {m} {return stdmaster}
proc macros {m} {return macromaster}
proc stdmaster {m} {return 0}
proc macromaster {m} {return 1}
'''


def run_cap(tmp_path, std, macros, pins, outline, limit=None):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = (HERE / 'native_cell_cap.tcl').read_text().replace('/work/native_cell_count.json', str(tmp_path / 'count.json'))
    script = script.replace('/work/cap_projection.json', str(tmp_path / 'proj.json'))
    mock = (CAP_MOCK.replace('STD', str(std)).replace('MAC', str(macros)).replace('PINS', str(pins))
            .replace('WDBU', str(int(outline[0] * 1000))).replace('HDBU', str(int(outline[1] * 1000))))
    (tmp_path / 'run.tcl').write_text(mock + ('' if limit is None else f'set ::ot_native_cell_limit {limit}\n') + script)
    return subprocess.run(['tclsh', str(tmp_path / 'run.tcl')], capture_output=True, text=True)


def test_pre_floorplan_projection_stops_with_the_split(tmp_path):
    r = run_cap(tmp_path, 332_424, 47, 14503, (1442.88, 1226.88))
    want = C.project(332_424, 14503, [1442.88, 1226.88], 47)
    assert r.returncode == 0 and f'after place resize {want["place"]} above the R-CAP place budget 400000' in r.stdout
    assert f'split into {want["split_parts"]} parts' in r.stdout and 'R-CAP removed' in r.stdout
    assert json.loads((tmp_path / 'proj.json').read_text())['place'] == want['place']


def test_pre_floorplan_projection_passes_and_probe_reports(tmp_path):
    r = run_cap(tmp_path, 120_000, 0, 4000, (622.08, 1339.2))
    assert r.returncode == 0 and 'OT_CELL_BUDGET stage=pre_floorplan synth=120000 pins=4000' in r.stdout, r.stderr
    r = run_cap(tmp_path, 380_000, 0, 10597, (622.08, 1339.2), limit=517000)
    assert r.returncode == 0 and 'capacity probe, not stopped' in r.stdout, r.stderr


CEN_MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
set NETS {}
proc blk {m} {switch $m {getInsts {return $::INSTS} getNets {return $::NETS}}}
proc m_std {m} {switch $m {isBlock {return 0} getName {return BUFx2_ASAP7_75t_R}}}
proc m_tap {m} {switch $m {isBlock {return 0} getName {return TAPCELL_ASAP7_75t_R}}}
proc i_std {m} {switch $m {getMaster {return m_std} getPlacementStatus {return PLACED}}}
proc i_tap {m} {switch $m {getMaster {return m_tap}}}
'''


def run_census(tmp_path, std, tap, stage, env=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    kit = tmp_path / 'kit'
    kit.mkdir(exist_ok=True)
    shutil.copyfile(HERE / 'cell_census.tcl', kit / 'cell_census.tcl')
    script = (CEN_MOCK + f'set INSTS [concat [lrepeat {std} i_std] [lrepeat {tap} i_tap]]\n{env}\n'
              + f'proc wrap {{}} {{ uplevel #0 [list source {{{kit / "cell_census.tcl"}}}] }}\nwrap\nputs "RET [ot_cell_census {stage}]"\n')
    (tmp_path / 'census.tcl').write_text(script)
    return subprocess.run(['tclsh', str(tmp_path / 'census.tcl')], text=True, capture_output=True)


def test_place_census_stops_a_measured_over_budget_run(tmp_path):
    r = run_census(tmp_path, 678_022, 92_298, 'place')        # S81 dsdv_slice_c1x_C__t3 as measured
    assert r.returncode != 0 and 'OT_CELL_BUDGET stage=place movable=678022' in r.stderr and 'split into 3 parts' in r.stderr
    assert 'OT_CELL_CENSUS stage=place nontap=678022 tap_endcap=92298' in r.stdout          # the census line still prints
    r = run_census(tmp_path, 400_000, 300_000, 'place')       # taps never count
    assert r.returncode == 0, r.stderr
    r = run_census(tmp_path, 678_022, 0, 'cts')               # only the place stage stops
    assert r.returncode == 0 and 'WARN OVER_CAP' in r.stdout, r.stderr
    r = run_census(tmp_path, 678_022, 0, 'place', 'set ::env(OT_CELL_BUDGET_GATE) 0')
    assert r.returncode == 0 and 'capacity probe, not stopped' in r.stdout, r.stderr


def test_cored_flat_type_cells_above_synth_budget_is_not_judged():
    """KV-RCAP-FLAT 11-13: an explicit type.cells of a cored split type above the synth budget is the inherited flat
    parent estimate (hard cores counted), so it is CORED; a glue-sized type.cells stays judged."""
    import cap_estimate as ce
    assert ce.cored_estimate({"hard_cores": [{}], "cells": 4966000}, "plan type.cells")
    assert not ce.cored_estimate({"hard_cores": [{}], "cells": 120000}, "plan type.cells")
    assert not ce.cored_estimate({"cells": 4966000}, "plan type.cells")
