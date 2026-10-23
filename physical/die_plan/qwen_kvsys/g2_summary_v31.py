#!/usr/bin/env python3
"""KV-P2: collect G2 probe results (die + partition FT probes) into one record.  python3 g2_summary_v31.py G2DIR... > g2_v31_report.json"""
import json, sys
from pathlib import Path
out = {}
for root in sys.argv[1:]:
    for d in sorted(Path(root).glob('*/probe.json')):
        p = json.load(open(d)); g = d.parent / 'grt.json'
        ex = (d.parent / 'probe.exit').read_text().strip() if (d.parent / 'probe.exit').exists() else 'missing'
        r = dict(exit=ex, **{k: v for k, v in p.items() if not isinstance(v, (list, dict))})
        if g.exists():
            L = json.load(open(g))['layers']
            r['overflow'] = sum(v.get('overflow', 0) for v in L.values())
            r['max_usage_pct'] = max(v.get('usage_pct', 0) for v in L.values())
        out[d.parent.name] = r
json.dump(dict(probes=out, all_exit0=all(v['exit'] == 'EXIT 0' for v in out.values()),
               overflow_total=sum(v.get('overflow', 0) for v in out.values())), sys.stdout, indent=1)
