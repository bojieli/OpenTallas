"""Plan direct metal delivery from an actual mesh to declared partition entries.

Long entries are returned as pending staged branches. No centre, pin layer, cell
or station is invented. The result is a planning delta, not a timing receipt.
"""
import argparse
import json
from pathlib import Path


def direct_delivery(P, mesh, reach_um=450.):
    hs=[(float(s['y']),float(s['x0']),float(s['x1'])) for s in mesh['M8']]
    vs=[(float(s['x']),float(s['y0']),float(s['y1'])) for s in mesh['M9']]
    taps=[];pending=[]
    for part in sorted(P.parts):
        ck=P.ptype(part).get('clock',{})
        if 'tap_um' not in ck or 'layer' not in ck:
            raise ValueError(f'{part} has no declared clock terminal coordinate/layer')
        x,y=P.to_die(part,ck['tap_um']);candidates=[]
        for yy,x0,x1 in hs:
            if x0-1e-6<=x<=x1+1e-6:candidates.append((abs(y-yy),'M8',x,yy))
        for xx,y0,y1 in vs:
            if y0-1e-6<=y<=y1+1e-6:candidates.append((abs(x-xx),'M9',xx,y))
        if not candidates:raise ValueError(f'{part} cannot project to any mesh strap')
        length,layer,fx,fy=min(candidates)
        record=dict(part=part,xy=[x,y],terminal_layer=ck['layer'],source='declared_partition_entry',
                    mesh_anchor=[layer,fx,fy],wire_um=round(length,6))
        (taps if length<=reach_um+1e-6 else pending).append(record)
    return dict(schema='opentallas.qc_direct_entry_delivery.v1',taps=taps,pending_staged_branches=pending,
                reach_um=reach_um,partitions=len(P.parts),complete=not pending,
                scope='declared entry coordinates and layers; direct metal only; pending branches require actual reserved buffers; no local tree or timing qualification')


def main():
    import schema
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan');ap.add_argument('spec');ap.add_argument('out');a=ap.parse_args()
    p=schema.Plan(schema.load(a.plan),Path(a.plan))
    spec=json.loads(Path(a.spec).read_text())
    result=direct_delivery(p,spec['mesh'])
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('taps','pending_staged_branches')}))
    print(f'direct={len(result["taps"])} pending={len(result["pending_staged_branches"])}')


if __name__=='__main__':main()
