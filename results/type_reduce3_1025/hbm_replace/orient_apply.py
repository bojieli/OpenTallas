#!/usr/bin/env python3
"""TYPE-REDUCE-3 10-25: try the orientation-only merge (one template table + whole-instance orient, no move) for the
held HBM groups that replace_probe.py finds at 0 pins > 405 um, then G0C (check.py --completeness) per group.
Writes a PROBE plan B2n/die_plan.tr3probe_<tag>.json + B2n/cores_tr3probe/*.json (deleted after each run unless
--keep).  Run from the repo root:  python3 orient_apply.py OUTDIR [group ...]"""
import json, os, shutil, subprocess, sys
P = 'physical/die_plan/hbm_arch/B2n'
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
probe = json.load(open('results/type_reduce3_1025/hbm_replace/replace_probe.json'))
TOFF = {('u_xl_Q_aqlo', 'MX'): (0.0, 0.096)}   # MX of a 108 um core: M6 (0.064) half pitch off; 0.096 = 0 mod M4 0.048, 0.032 mod M6
want = sys.argv[2:] or [g for g, v in probe.items() if v['pins_over_405'] == 0]
def run(tag, groups):
    plan = json.load(open(f'{P}/die_plan.json'))
    T = plan['partition_types']
    os.makedirs(f'{P}/cores_tr3probe', exist_ok=True)
    for g in groups:
        v = probe[g]; m = g.split('|')[0]
        tt, ti = v['template'].split('/')
        src = next(hc for hc in T[tt]['hard_cores'] if hc['inst'] == ti)
        assert src.get('orient', 'R0') == 'R0'
        rel = f'cores_tr3probe/{m}__{g.split("|")[1]}.json'
        shutil.copy(f'{P}/{src["pins_file"]}', f'{P}/{rel}')
        for r in v['rows']:
            hc = next(h for h in T[r['type']]['hard_cores'] if h['inst'] == r['inst'])
            assert hc.get('orient', 'R0') == 'R0' and r['shift_um'] == [0, 0]
            hc['pins_file'] = rel; hc['track_offset_um'] = list(src.get('track_offset_um', [0.0, 0.0]))
            for i, d in enumerate(TOFF.get((r['inst'], r['orient']), (0.0, 0.0))): hc['track_offset_um'][i] += d
            if r['orient'] != 'R0': hc['orient'] = r['orient']
    pf = f'{P}/die_plan.tr3probe.json'
    json.dump(plan, open(pf, 'w'), indent=0)
    od = f'{OUT}/{tag}'
    r = subprocess.run(['python3', 'tools/die_plan/check.py', pf, '--completeness', '--out', od],
                       capture_output=True, text=True)
    os.remove(pf); shutil.rmtree(f'{P}/cores_tr3probe')
    rep = json.load(open(f'{od}/g0_report.json'))
    fs = {(x.get('level') or x.get('severity'), x.get('check'), x.get('msg') or x.get('message')) for x in rep['findings']}
    return dict(verdict=rep['verdict'], errors=rep['errors'], warnings=rep['warnings']), fs
base_last, base = run('base', [])
print('BASE', base_last)
res = dict(base=base_last, groups={})
for g in want:
    last, fs = run(g.split('|')[0], [g])
    new = sorted(map(list, fs - base)); gone = sorted(map(list, base - fs))
    res['groups'][g] = dict(g0c=last, new_findings=new, gone_findings=gone)
    print(g, '->', last, 'new', len(new), 'gone', len(gone))
    for x in new[:6]: print('    +', x)
json.dump(res, open(f'{OUT}/orient_apply.json', 'w'), indent=1)
