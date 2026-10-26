#!/usr/bin/env python3
"""Separate lateral free space from rectangle legality for a DVM candidate."""
import argparse,hashlib,json
from pathlib import Path

def audit(model,candidate):
    by={i['n']:dict(i) for i in model['insts']}
    by.update({r['after']['n']:r['after'] for r in candidate['moves']})
    rows=[]
    for move in candidate['moves']:
        a=move['after']
        if not a['n'].startswith('h_'):continue
        # Only neighbors with positive common Y interval obstruct the side.
        neighbors=[b for b in by.values() if b['n']!=a['n'] and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+1e-6]
        sides={}
        for side in ('W','E'):
            cand=[(a['x']-b['x']-b['w'],b) for b in neighbors if b['x']+b['w']<=a['x']+1e-6] if side=='W' else [(b['x']-a['x']-a['w'],b) for b in neighbors if b['x']>=a['x']+a['w']-1e-6]
            distance,b=min(cand,key=lambda r:r[0]) if cand else (None,None)
            sides[side]=dict(clearance_um=round(distance,6) if distance is not None else None,neighbor=b['n'] if b else None)
        rows.append(dict(instance=a['n'],sides=sides))
    return dict(schema='opentallas.qwen.dvm-gap-audit.v1',scope='Nonrelay geometry side-clearance only',columns=rows,qualification=False,findings=['Column is placed flush against the west neighboring field tile; the 0.648um remainder is on the east side, not split equally.','No new widened leaf/column physical pin or obstruction view provided; historical 64.8um leaf spec cannot establish access for 72.36um successor.','Existing leaf recipe has macro_halo_um 5.4 for internal macro placement; applicability at this die boundary is not established. This audit neither invents a die halo nor waives one.','Do not count the lateral sliver as a relay-placement corridor. Actual allocator site dimensions, upper-metal crossings, pin escape and cut capacity must be demonstrated.','Abutting outlines are not automatically impossible: registered face pins and permitted upper-metal crossing may work, but require actual views.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('candidate',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    r=audit(json.loads(a.model.read_text()),json.loads(a.candidate.read_text()));r['sha256']={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (a.model,a.candidate)};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['columns'][:2]))
if __name__=='__main__':main()
