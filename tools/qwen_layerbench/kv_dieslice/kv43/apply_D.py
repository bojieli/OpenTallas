#!/usr/bin/env python3
"""KV boot D diagnostic successor: retain all PHY lane flops, clock them on their endpoint HBM domain.
Only the ten HBM PHY face lanes per PC partition are changed. The native binder uses per-port domains.
No register stages, data expressions or epoch expressions are altered. Call on a NEW staged tree, never a live build.
"""
import argparse, json, re
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('staged');a=ap.parse_args()
r=Path(a.staged)/'src'/'bind__rtl'; rows=[]
for p in sorted(r.glob('kv3_pc*_part*.sv')):
    s=p.read_text(); changed=[]; out=[]
    for line in s.splitlines(keepends=True):
        if re.search(r'\bot_dp_(?:st|dly)\b',line) and re.search(r'\bu_(?:bin_i_phy_\w+(?:fhN|rhN|piN)(?:_d\d+)?|bout_o_kvpc_\w+pc__po(?:_d\d+)?)\s*\(',line):
            if '.clk(clk)' not in line: raise SystemExit(f'Unexpected already changed clock: {p}: {line}')
            changed.append(re.search(r'\bu_\w+',line).group())
            line=line.replace('.clk(clk)', '.clk(clk_clk_hbm)')
        out.append(line)
    if changed:
        if len(changed)!=10 or 'input  wire clk_clk_hbm' not in s: raise SystemExit(f'Unexpected PHY lane layout {p}: {len(changed)}')
        p.write_text(''.join(out));rows.append(dict(file=p.name,instances=changed))
if len(rows)!=24: raise SystemExit(f'Expected 24 PC partition types, got {len(rows)}')
(Path(a.staged)/'fixD.json').write_text(json.dumps(dict(scope='HBM PHY face registers only',types=rows,added_stages=0,domain='HBM'),indent=2)+'\n')
print(f'D applied: {len(rows)} PC types, {sum(len(x["instances"]) for x in rows)} PHY clock pins core -> HBM; 0 added register stages')
