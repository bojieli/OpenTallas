#!/usr/bin/env python3
"""Read-only diagnostic of the old D4 measured slacks; emits no binding/K values."""
import collections, hashlib, json, math
from pathlib import Path
p = Path(__file__).resolve().parent
d = json.loads((p / 'rS_land_plan.json').read_text())
T = d['T_ps']; hist = collections.Counter(); changed = []; complete = []; missing = []
for r in d['links']:
    if r.get('E') is None or set(r.get('h0', {})) != {'tt', 'ff'} or set(r.get('s1', {})) != {'tt', 'ff'}:
        missing.append(r['bid']); continue
    need = max(1, math.ceil(r['E'] - min(r['h0'].values()) / T))
    hist[need] += 1
    complete.append(dict(bid=r['bid'], min_raw_depth=need, E=r['E'], E_gen=r['E_gen']))
    if r['E'] != r['E_gen']: changed.append(r['bid'])
roots = collections.Counter(); reach = []
for line in (p / 'rS_long_wires.rpt').read_text().splitlines():
    row = line.split()
    if len(row) >= 5 and row[1] == 'manhtn' and float(row[2]) > 405:
        roots[row[0].split('/')[0]] += 1
        reach.append(dict(driver=row[0], manhattan_um=float(row[2])))
out = dict(schema='opentallas.qw.d4_phase_diagnostic.v1', qualified=False,
    source='compute6f78e3de2 tools562357708 rS', input_sha256={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['rS_land_plan.json','rS_long_wires.rpt']},
    warning='Old D4 measured-slack counterfactual only. New D8 RTL/K mod16/reset release/first-use/macro ages are unproved. No K or binding emitted. Raw zero-slack depth is not reserved signoff.',
    complete_TTFF=len(complete), missing_TTFF=missing, original_D4_window_fail=d['summary']['window_fail'],
    raw_depth_hist=dict(sorted(hist.items())), E_changed=changed,
    raw_depth_over8=[r for r in complete if r['min_raw_depth']>8],
    reach_report_rows_over405=len(reach), reach_by_driver_root=roots.most_common(),
    reach_note='Driver report rows, not unique physical nets or routed path proof; includes skipped clock nets. Original repeater check reports544over425,max590.5.',
    lanes=complete, reach_top20=reach[:20])
(p/'diagnostic.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps({k:out[k] for k in ['complete_TTFF','raw_depth_hist','reach_report_rows_over405']}))
