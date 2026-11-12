"""pick.py GEN_DIR: replay cases from the frame's own BF phases: full (the measured vector's phase), tail (last-segment
attn.wo_a), router (last-segment ffn.router), then one extra per further (op, row count) of this frame."""
import json, sys
from pathlib import Path
g = Path(sys.argv[1])
bf = [p for p in json.loads((g / 'bf_phases.json').read_text()) if p['rows'] > 0]
full = json.loads((g / 'vec/meta.json').read_text())['field_phase']
out = [('full', full)]
tail = [p for p in bf if p['op'] == 'attn.wo_a' and p['seg'] == p['nseg'] - 1 and p['phase'] != full]
rtr = [p for p in bf if p['op'] == 'ffn.router' and p['seg'] == p['nseg'] - 1]
out.append(('tail', tail[-1]['phase']))
out.append(('router', rtr[0]['phase']))
by = {p['phase']: p for p in bf}
seen = {(by[k]['op'], by[k]['rows']) for _, k in out}
for p in bf:
    key = (p['op'], p['rows'])
    if key not in seen:
        seen.add(key)
        out.append((('woa' if p['op'] == 'attn.wo_a' else 'router') + str(p['rows']), p['phase']))
for n, k in out:
    print(n, k, by[k]['op'], by[k]['rows'], f"{by[k]['seg']}/{by[k]['nseg']}")
