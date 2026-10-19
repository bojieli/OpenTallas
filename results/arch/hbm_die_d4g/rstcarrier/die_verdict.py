#!/usr/bin/env python3
"""L2H-GEN2D-RST 10-19: classify a finished d4g GEN case S8 (case/run.sh: GRT + STA TT/FF + die clock dump + neighbour
skew gate + hold budget) into one JSON verdict for H.GRT / H.STA / H.CLK / H.RST.  Reads only files already written by the
run; stand-ins (SYNTH views) are counted and labelled, never treated as closure.
    die_verdict.py CASE_DIR OUT.json"""
import json, re, sys
from pathlib import Path
case, out = Path(sys.argv[1]), Path(sys.argv[2])
o = case / 'out'
v = dict(case=str(case), run_exit=(o / 'run.exit').read_text().strip() if (o / 'run.exit').exists() else None)
log = (o / 'run.log').read_text(errors='replace') if (o / 'run.log').exists() else ''
v['ot_done'] = 'OT_DONE' in log
ov = re.findall(r'^\s*Total\s+\d+\s+\d+\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', log, re.M)
m = re.findall(r'(?:Total overflow|overflow)[^\n]*?(\d+)\s*$', log, re.M | re.I)
v['grt_total_overflow'] = int(ov[-1][1]) if ov else (int(m[-1]) if m else None)
v['grt_overflow_lines'] = [l.strip()[:200] for l in log.splitlines() if 'overflow' in l.lower()][-6:]
for c, k in (('tt', 'max'), ('ff', 'min')):
    p = o / f'paths_{c}_{k}.txt'
    if not p.exists():
        v[f'{c}_{k}'] = None
        continue
    worst, neg, n, tns = None, 0, 0, 0.0
    for line in p.open():
        f = line.split()
        if len(f) < 3:
            continue
        try:
            s = float(f[2])
        except ValueError:
            continue
        n += 1
        worst = s if worst is None else min(worst, s)
        if s < 0:
            neg += 1; tns += s
    v[f'{c}_{k}'] = dict(endpoints=n, worst_ps=worst, negative=neg, tns_ps=round(tns, 1))
try:
    g = json.loads((o / 'neighbour_skew_gate.json').read_text())
    v['neighbour_skew'] = {k: g[k] for k in g if not isinstance(g[k], (list, dict))} or g
except Exception as e:
    v['neighbour_skew'] = f'missing ({e.__class__.__name__})'
try:
    hb = json.loads((o / 'hold_budget.json').read_text())
    v['hold_budget'] = {k: hb[k] for k in hb if not isinstance(hb[k], (list, dict))}
except Exception as e:
    v['hold_budget'] = f'missing ({e.__class__.__name__})'
try:
    man = json.loads((case / 'manifest.json').read_text())
    rg = man.get('reset_reach_gate') or {}
    v['reset_reach_gate'] = {k: rg.get(k) for k in ('reach_gate', 'por_direct_sinks', 'forest_sinks', 'relay_row_sinks', 'errors', 'kinds')}
    kinds = {}
    for x in (man.get('views') or {}).values() if isinstance(man.get('views'), dict) else []:
        k = str(x.get('kind', '?')).split(' ')[0] if isinstance(x, dict) else str(x).split(' ')[0]
        kinds[k] = kinds.get(k, 0) + 1
    v['view_kinds'] = kinds or man.get('kinds_count')
    v['placement_problems'] = len(man.get('placement_problems') or [])
except Exception as e:
    v['manifest'] = f'missing ({e.__class__.__name__})'
v['labels'] = 'SYNTH views are LABELLED STAND-INS (D5): a pass with stand-ins never counts as closure'
tt, ff = v.get('tt_max') or {}, v.get('ff_min') or {}
v['verdict'] = dict(
    H_GRT='PASS' if v['grt_total_overflow'] == 0 else ('FAIL' if v['grt_total_overflow'] else 'UNKNOWN'),
    H_STA_TT='PASS' if tt.get('negative') == 0 and tt.get('endpoints') else ('FAIL' if tt.get('negative') else 'UNKNOWN'),
    H_STA_FF='PASS' if ff.get('negative') == 0 and ff.get('endpoints') else ('FAIL' if ff.get('negative') else 'UNKNOWN'),
    H_RST=(v.get('reset_reach_gate') or {}).get('reach_gate'))
out.write_text(json.dumps(v, indent=1, default=str) + '\n')
print('DIE_VERDICT', json.dumps(v['verdict']), 'overflow', v['grt_total_overflow'], 'tt', tt.get('worst_ps'), 'ff', ff.get('worst_ps'))
