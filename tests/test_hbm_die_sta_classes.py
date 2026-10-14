"""tools/hbm_die_sta_classes.py: view kinds from the STA case bind map, causes, coverage (hbmdie 10-13)."""
import gzip
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lib(p, name):
    p.write_text(f'library ({name}) {{\n}}\n')


def _case(tmp):
    plan, case = tmp / 'plan', tmp / 'case'
    plan.mkdir()
    case.mkdir()
    insts = [['a', 'hfd_svc_SE_s6', 'svc', 0, 0, 10, 10, 'R0'], ['b', 'hfd_stn_r3', 'waypoint', 300, 0, 10, 10, 'R0'],
             ['c', 'hfd_su', 'su', 900, 0, 10, 10, 'R0'], ['d', 'hfd_stn_q64', 'waypoint', 1200, 0, 10, 10, 'R0'],
             ['e', 'hfd_stn_r4', 'waypoint', 600, 0, 10, 10, 'R0'], ['r', 'hfd_rrl', 'waypoint', 0, 50, 5, 5, 'R0']]
    hops = [['bus0', 'hub', 64, 'a', 't_x', 'b', 'a', 290.0], ['bus1', 'hub', 64, 'b', 'b', 'e', 'a', 290.0],
            ['bus2', 'hub', 64, 'e', 'b', 'c', 'f_x', 620.0], ['bus3', 'hub', 64, 'c', 't_y', 'd', 'a', 280.0],
            ['rst0', 'reset_tree', 1, 'r', 'q', 'a', 'rst_n', 100.0]]
    json.dump(dict(insts=insts, hops=hops), gzip.open(plan / 'plan.json.gz', 'wt'))
    # the generator's own table knows no real master: every row would read placeholder without the bind map
    (plan / 'clock_delivery.json').write_text(json.dumps(dict(tiles={i[1]: dict(view='placeholder') for i in insts})))
    for c in ('ss', 'ff'):
        _lib(case / f'hfd_svc_SE_s6_{c}.lib', f'hfd_svc_SE_s6_{c}')
        _lib(case / f'hfd_stn_r3_{c}.lib', f'hfd_stn_r3_{c}')
        _lib(case / f'hfd_stn_r4_{c}.lib', f'hfd_stn_r4_{c}')
        _lib(case / f'hfd_su_{c}.lib', f'hfd_su_ph_{c}')
        _lib(case / f'hfd_rly_{c}.lib', f'hfd_rly_{c}')
    (case / 'manifest.json').write_text('{}')
    (case / 'relays.json').write_text(json.dumps(dict(
        chains=[dict(bus='bus2', src='e', dst='c', regs=['rl1_bus2_f'], hops_um=[310.0, 310.0])],
        instance_metadata={'rl1_bus2_f': dict(master='hfd_rly_1', bits=64, original_bus='bus2')})))
    (case / 'relay_clock_context.json').write_text(json.dumps(dict(sinks={
        'a/ck': dict(instance='a', entry_ps=dict(tt=100.0, ff=80.0), internal_ps=dict(tt=50.0, ff=40.0)),
        'b/ck': dict(instance='b', entry_ps=dict(tt=0.0, ff=0.0), internal_ps=dict(tt=50.0, ff=40.0))})))
    (case / 'paths_tt.txt').write_text(
        'a/t_x[3] b/a[3] -0.050\n'          # launch flop 100 ps later than capture: passes without the phase
        'b/b[1] e/a[1] -0.010\n'            # station view -> station view
        'e/b[0] rl1_bus2_f/d[0] -0.020\n'   # station view -> STA wire stage
        'rl1_bus2_f/q[0] c/f_x[0] -0.030\n'  # wire stage -> placeholder lib
        'r/q a/rst_n -0.005\n'
        'a/t_x[4] zz/q[0] 0.010\n')
    return plan, case


def _run(tmp, *extra):
    plan, case = _case(tmp)
    out = tmp / 'o.json'
    subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_sta_classes.py'), str(plan), str(case / 'paths_tt.txt'),
                    '--out', str(out), '--md', str(tmp / 'o.md'), *extra], check=True, capture_output=True)
    return json.loads(out.read_text()), case


def test_bind_map_kinds_and_causes(tmp_path):
    r, case = _run(tmp_path, '--case', str(tmp_path / 'case'))
    rep = r['reports']['paths_tt.txt']
    by = {(c['cause'], c['views']): c for c in rep['classes']}
    assert ('clock_phase', 'real->real_station') in by and by[('clock_phase', 'real->real_station')]['clock_phase_ps'] == 100.0
    assert ('relay_chain', 'real_station->real_station') in by
    assert ('relay_chain', 'real_station->sta_relay') in by and by[('relay_chain', 'real_station->sta_relay')]['len_max_um'] == 310.0
    assert ('placeholder_lib', 'sta_relay->placeholder_lib') in by
    assert rep['by_cause']['reset_net']['violators'] == 1
    assert rep['by_cause']['no_plan_hop']['endpoints'] == 1 and rep['by_cause']['no_plan_hop']['violators'] == 0
    assert rep['by_cause']['placeholder_lib']['violators'] == 1         # ONE row, not every row
    cov = r['coverage']
    assert cov['plan_hops']['both_ends_timed']['hops'] == 3 and cov['plan_hops']['one_end_timed']['hops'] == 2
    assert cov['untimed_masters'][0]['master'] == 'hfd_stn_qN'
    assert 'Coverage' in (tmp_path / 'o.md').read_text()


def test_generator_table_over_counts_placeholders(tmp_path):
    """the defect the bind map fixes: with the generator's table every timed end reads placeholder"""
    r, _ = _run(tmp_path)
    rep = r['reports']['paths_tt.txt']
    assert rep['by_cause']['placeholder_lib']['violators'] == 2      # 1 with the bind map
