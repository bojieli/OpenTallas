#!/usr/bin/env python3
"""TOK-HBM-3 plan event d44x = d44t + R8 bus latency groups for split register words whose lanes d44t de-aligned.

d44t (DIE-HBM-59 FT S0 re-site) gives L168/L168m +2 stations (8 -> 10) while L14/L167 (L14m/L167m) stay 8. The bind's
as-built landing groups (bus_groups.json, COORD R8) show all three lanes land in ONE sink register
hcb_NW1.u_c.$procdff$71842 (NE: hcb_NE1) at the same as-built stage, so the d44t bound word would arrive split over two
cycles. Fix = one R8 'bus' latency_group per side; Plan.lane_pads() pads L14/L167 to the slowest member (10).
Usage: tools/hbm_b2/r8_word_groups_event.py <d44t die_plan.json[.gz]> <out die_plan.json>  then: python3 tools/die_plan/gen.py latency <out die_plan.json> --inplace --out <dir>."""
import gzip, json, sys
src, dst = sys.argv[1:3]
raw = json.loads((gzip.open(src, 'rt') if src.endswith('.gz') else open(src)).read())
GROUPS = [
    dict(name='L168_word', kind='bus', lanes=['L14', 'L167', 'L168'], source='NW_b000 -> NW_b001 hcb_NW1.u_c.$procdff$71842',
         note='TOK-HBM-3 d44x: one as-built register word over 3 lanes (bind bus_groups landing, same as-built stage); d44t L168 +2'),
    dict(name='L168m_word', kind='bus', lanes=['L14m', 'L167m', 'L168m'], source='NE_b000 -> NE_b001 hcb_NE1.u_c.$procdff$71842',
         note='TOK-HBM-3 d44x: mirror of L168_word'),
]
have = {g['name'] for g in raw.get('latency_groups', [])}
for g in GROUPS:
    if g['name'] in have: raise SystemExit(f"group {g['name']} already present")
    for l in g['lanes']:
        if l not in {x['id'] for x in raw['lanes']}:
            raise SystemExit(f'unknown lane {l}')
raw.setdefault('latency_groups', []).extend(GROUPS)
raw['note'] = 'TOK-HBM-3 d44x = d44t + R8 bus groups L168_word/L168m_word | ' + raw.get('note', '')
open(dst, 'w').write(json.dumps(raw, indent=1) + '\n')
print('added', [g['name'] for g in GROUPS])
