#!/usr/bin/env python3
"""Read-only HBM r19b/r19c integration audit; no jobs or closure credit."""
import hashlib
import json
import subprocess
from pathlib import Path
import hbm_die_views as V
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/hbm_accel_die_views_20261006/coordinator_r19c'


def rates(base, delta):
    return dict(baseline_us=base, added_us=delta, latency_us=base + delta,
                latency_increase_pct=100 * delta / base,
                throughput_decrease_pct=100 * delta / (base + delta))


def main():
    V.L.VARIANT = ''
    V._MODEL.clear()
    base = V.model()[0]
    bp = V.H.manhattan_paths(base)
    V.L.VARIANT = 'r19c'
    V._MODEL.clear()
    m, _, masters, _ = V.model()
    cp = V.H.manhattan_paths(m)
    stations = lambda x: sorted((i.name, i.master, i.x, i.y) for i in x['insts'] if i.kind == 'waypoint')
    vm = []
    for i in m['insts']:
        if i.master in V.H.VM_CENTRE:
            ck = masters[i.master].ports['ck']
            vm.append(dict(master=i.master, origin_um=[i.x,i.y], size_um=[i.w,i.h], clock_pin=ck,
                           M7_global_on_track=round((i.x + ck[2]) * 1000) % 64 == 16))
    idx = json.loads((OUT / 'index.json').read_text())
    split = json.loads((ROOT / 'physical/hbm_accel_die_views/index_q/split_stages.json').read_text())
    stages = split['added_cycles']
    add_cycles = (stages['keys'] - 10) * 8 + (max(stages['rows'].values()) - 4) * 40
    inputs = ['tools/hbm_accel_die_fp.py', 'tools/hbm_die_views.py', 'tools/hbm_die_views_recompose.py',
              'tools/hbm_die_coordinator_audit.py', 'physical/hbm_accel_die_views/index_q/split_stages.json',
              'results/rtl/hbm_accel_die_views_20261006/recompose_r19b_r13wire__cp_in_su.json',
              'results/rtl/budgets_20261006/inputs/calibrations.json',
              'physical/hbm_accel_die_views/insertion_override.json']
    files = [ROOT / f for f in inputs]
    files += sorted((OUT / 'zeno_9797836f2').glob('*.json'))
    files += [OUT / 'index.json', OUT / 'budgets/summary.json', OUT / 'die_model_hbm.json.gz']
    record = dict(schema='opentallas.hbm_die_coordinator.r19c.v1',
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        adopted='r19b', candidate='r19c', adopted_changed=False, new_jobs_launched=0,
        physical_closed=False, functional_closed=False, measured_clock_plan=False,
        vm=vm, station_identities_unchanged=stations(base)==stations(m),
        path_stage_changes={p:dict(old=bp[p]['stages_430'],candidate=cp[p]['stages_430'])
                            for p in bp if bp[p]['stages_430']!=cp[p]['stages_430']},
        VM_write_alignment=dict(SW=cp['hub_su_SW_vm']['stages_430'], NW=cp['hub_su_NW_vm']['stages_430'],
            equal=False, status='BLOCKED: equal external cycle count and atomic producer/CDC binding required; internal wrapper depth 5/5 is insufficient'),
        index_counts=idx['counts'], pin_mismatches={n:v['check']['problems'] for n,v in idx['masters'].items()
            if v.get('check',{}).get('verdict')=='MISMATCH'},
        cmdproc_n=dict(pin_match=idx['masters']['hfd_cmdproc_n']['check']['verdict'],
                       receipt=idx['masters']['hfd_cmdproc_n']['receipt'], functional_closed=False),
        serial_clock_budget=dict(domains=['hfd_su','hfd_sfu','hfd_hc'], period_ps=1000/0.9,
            sheet_global_route_ps=770, sheet_global_signoff_ps=833.333, entry_arrivals_measured=False,
            status='BLOCKED: per-domain sheet/parent SDC consistency and measured clock entry required'),
        historical_total=rates(537.376,22.17),
        pending_index=dict(cycles=add_cycles, frequency_GHz=1.2, added_us=add_cycles/1200,
                           physical_adopted=False, common_baseline=rates(537.376,22.17+add_cycles/1200)),
        pending_costs=[dict(item='SU reducer SAFE',cycles_per_reduction=4, frequency_GHz=0.9,
                            us_per_reduction=4/900,occurrences=None,adopted=False),
                      dict(item='HA2 edge',cycles_per_occurrence=1,occurrences=None,frequency_GHz=None,adopted=False),
                      dict(item='mcast r6 extra tap',cycles_bound=571,frequency_GHz=1.2,
                           us_bound=571/1200,adopted=False,note='Check event overlap before summing'),
                      dict(item='VM alignment / real publication path',cycles=None,adopted=False),
                      dict(item='SM 3x3 grid',credit_us=None,adopted=False,owner='Boyle')],
        budget_limit='Zero infeasible analytical ports uses historical calibration/nominal targets, not new VM measurements. 160 direction-resolution failures remain. No signoff or launch admission.',
        open_reservations=['hfd_su_red and hfd_su_full have only clock/reset in the die graph; Avicenna must supply real port binding including reducer S input/N result faces.'])
    (OUT / 'audit.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['station_identities_unchanged','path_stage_changes','index_counts','historical_total','pending_index']}))


if __name__ == '__main__':
    main()
