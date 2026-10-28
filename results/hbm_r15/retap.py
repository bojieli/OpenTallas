#!/usr/bin/env python3
"""HBM-R15: every partition core clock tap := origin + orient(core clock entry) (apply_clk.to_part rule); fixes the taps the
C16 outline moves left stale (EP x5, q3 edge x2) and the 17 pre-existing C15-lineage mismatches. usage: retap.py PLANDIR"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_clk as A
d = Path(sys.argv[1]); DP = json.loads((d/'die_plan.json').read_text()); CE = json.loads((d/'clock_entries.json').read_text())
rep = []
for tn, t in DP['partition_types'].items():
    taps = {tp['name']: tp for tp in (t.get('clock') or {}).get('taps', []) if tp.get('kind') == 'core'}
    for h in t.get('hard_cores', []) or []:
        k = A.ekey(CE, tn, h['inst']); e = CE[tn][k] if k else None
        tp = taps.get(h['inst']) or (taps.get(e.get('tap')) if e and k == h['inst'] else None)
        if not (e and tp): continue
        new = A.to_part(h, e['xy_um'])
        if max(abs(u-v) for u, v in zip(new, tp['xy'])) > 0.01:
            rep.append([tn, h['inst'], tp['xy'], new]); tp['xy'] = new
(d/'die_plan.json').write_text(json.dumps(DP, indent=1)+'\n')
(d/'retap_report.json').write_text(json.dumps(rep, indent=1)+'\n'); print('retapped', len(rep))
