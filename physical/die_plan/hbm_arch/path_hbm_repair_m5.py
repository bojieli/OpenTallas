#!/usr/bin/env python3
"""Rebuild HBM FT/internal station + reset geometry on an M5-ceiling plan (path_hbm_m5_ceiling.py).

Same flow as path_hbm_repair.py (b2o internal stations, hbm_bit_stations actual-bit FT stations, b2n reset
wavefront, lane latency table from schema.Plan), with ONE difference that follows from the M5 core ceiling:
hbm_bit_stations runs ft_sites in strict per-bit mode with core-avoiding LEGS (avoid_core_routes=True), the rule
for M7-walled cores (a wide FT bundle could not cross a core whose OBS covers M6/M7). With every hard core of the
selected types at obs_max <= M5, the FT layers M6 (H) and M7 (V) are free over the cores, so FT legs may cross a
core; station CELLS still stay off every core + 8.64-um halo (RowAllocator blocked boxes, targets outside cores)
and every bit hop stays <= ft_station_max_um. Bits are ribbon-ordered (bit_order) so a bus stays parallel.
The script refuses to run when any selected type has a hard core above M5.
"""
import argparse, copy, importlib, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'tools' / 'die_plan'), str(HERE)]
import schema as S

OK_OBS = {'M1', 'M2', 'M3', 'M4', 'M5'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--helper', type=Path, required=True, help='dir with b2o.py, b2n.py, hbm_bit_stations.py')
    ap.add_argument('--types', required=True); a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    sys.path.insert(0, str(a.helper.resolve()))
    B = importlib.import_module('b2o'); BN = importlib.import_module('b2n'); HBS = importlib.import_module('hbm_bit_stations')
    FS = HBS.shared.ft_sites
    p = json.loads((a.src / 'die_plan.json').read_text()); old = copy.deepcopy(p); types = a.types.split(',')
    high = {tn: [c['inst'] for c in p['partition_types'][tn].get('hard_cores', []) if c.get('obs_max', 'M7') not in OK_OBS]
            for tn in types}
    high = {k: v for k, v in high.items() if v}
    if high: raise SystemExit(f'hard cores above M5 in selected types (legs may not cross them): {high}')

    def place_over_m5(raw, allocator_cls, types=None, reach_um=405., margin=.98, max_radius_um=40., avoid_core_routes=False, bit_order=False):
        for tn in (types or []):
            bad = [c['inst'] for c in raw['partition_types'][tn].get('hard_cores', []) if c.get('obs_max', 'M7') not in OK_OBS]
            if bad: raise ValueError(f'{tn}: cores above M5 {bad[:3]}')
        return FS._place_strict(raw, allocator_cls, types=types, reach_um=reach_um, margin=margin,
                                max_radius_um=max_radius_um, avoid_core_routes=False, bit_order=True)
    HBS.shared.ft_sites.place = place_over_m5
    shutil.copytree(a.src, a.out)
    report = {'not_release_ready': True, 'types': types, 'mode': 'M5-ceiling: FT legs over cores on M6/M7, station cells off cores',
              'unproven_face_budgets': {}, 'clock_pending': True}; log = []
    for tn, t in p['partition_types'].items():
        if isinstance(t.get('face_pins_per_um'), dict): report['unproven_face_budgets'][tn] = t.pop('face_pins_per_um')
    print('REBUILD_INTERNAL', ','.join(types), flush=True)
    report['internal_unroutable'] = B.internal_stations(p, a.out, types, log)
    print('REBUILD_ACTUAL_FT', flush=True)
    try: report['ft_repair'] = HBS.repair(p, log=lambda m: print(m, flush=True), only_types=types)
    except HBS.RepairFailure as e: report['ft_repair'] = e.report
    print('REBUILD_RESET', flush=True); BN.reset_wavefront(p, log)
    before = S.Plan(old, a.src / 'die_plan.json'); after = S.Plan(p, a.out / 'die_plan.json')
    p['latency']['lanes'] = {lid: after.lane_latency(lid) for lid in after.lanes}
    report['lane_cycle_delta'] = {lid: p['latency']['lanes'][lid]['cycles'] - before.lane_latency(lid)['cycles'] for lid in after.lanes
                                  if p['latency']['lanes'][lid]['cycles'] != before.lane_latency(lid)['cycles']}
    report['log'] = log
    (a.out / 'die_plan.json').write_text(json.dumps(p, indent=1) + '\n')
    (a.out / 'repair_report.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
    print('REPAIR_COMPLETE', json.dumps({'internal_unroutable': report['internal_unroutable'], 'ft_failures': report['ft_repair'].get('type_failures'),
                                         'lane_delta': report['lane_cycle_delta']}), flush=True)
    return int(bool(report['internal_unroutable']) or report['ft_repair'].get('verdict') == 'FAIL')


if __name__ == '__main__': raise SystemExit(main())
