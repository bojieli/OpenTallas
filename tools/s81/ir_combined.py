#!/usr/bin/env python3
"""S81 die IR window: COMBINED supply loss per instance (r5 2026-10-14, IR release gate).

  ir_combined.py <irm work dir> [--json OUT]

The irm window (tools/dsrom_s81_fulldie.py irm) solves VDD and VSS separately (PSM) and its OT_IR_INNER lines report each
rail's worst node.  Their sum (c8p: 13.65 + 23.09 mV spine, 178.66 + 193.85 mV field) adds maxima that sit at different
instances.  The supply a cell sees is VDD(inst) - VSS(inst): this tool joins ir_VDD.rpt and ir_VSS.rpt per instance
terminal on the inner (judged) window and reports the worst combined loss (0.7 V - (VDD - VSS)) against the 35 mV budget,
by instance kind (kinds.json), with the count of instances over budget.  Prints one OT_IR_COMBINED line.
"""
import collections
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
man = json.loads((d / 'manifest.json').read_text())
ix0, iy0, ix1, iy1 = man['inner_local_um']
vdd, budget = man.get('vdd_v', 0.7), man.get('budget_mv', 35.0)
kinds = json.loads((d / 'kinds.json').read_text())
loss = collections.defaultdict(dict)
for net in ('VDD', 'VSS'):
    for ln in (d / f'ir_{net}.rpt').read_text().splitlines()[1:]:
        c = ln.strip().split(',')
        if len(c) < 6:
            continue
        x, y, v = float(c[3]), float(c[4]), float(c[5])
        if not (ix0 <= x <= ix1 and iy0 <= y <= iy1):
            continue
        mv = (vdd - v if net == 'VDD' else v) * 1000.0
        loss[c[0]][net] = max(loss[c[0]].get(net, 0.0), mv)
rows = sorted(((a.get('VDD', 0.0) + a.get('VSS', 0.0), k, a.get('VDD', 0.0), a.get('VSS', 0.0), kinds.get(k, '?'))
               for k, a in loss.items()), reverse=True)
by_kind = {}
for t in rows:
    by_kind.setdefault(t[4], round(t[0], 2))
over = collections.Counter(t[4] for t in rows if t[0] > budget)
worst = rows[0] if rows else (0.0, None, 0.0, 0.0, None)
rec = dict(window=man.get('window'), instances=len(rows), budget_mv=budget, power_w=man.get('power_w'),
           power_w_per_mm2=man.get('power_w_per_mm2'), strap_pitch_um=man.get('strap_pitch_um'), coverage=man.get('coverage'),
           worst_combined_mv=round(worst[0], 2), worst_inst=worst[1], worst_vdd_mv=round(worst[2], 2),
           worst_vss_mv=round(worst[3], 2), worst_kind=worst[4], worst_by_kind=by_kind,
           over_budget=sum(over.values()), over_budget_by_kind=dict(over),
           verdict='PASS' if rows and worst[0] <= budget else 'FAIL')
if '--json' in sys.argv:
    Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(rec, indent=1) + '\n')
print('OT_IR_COMBINED window=%s verdict=%s worst_mv=%.2f (VDD %.2f + VSS %.2f at %s %s) budget_mv=%.0f over=%d power_w=%s'
      % (rec['window'], rec['verdict'], rec['worst_combined_mv'], rec['worst_vdd_mv'], rec['worst_vss_mv'], worst[1], worst[4],
         budget, rec['over_budget'], rec['power_w']))
