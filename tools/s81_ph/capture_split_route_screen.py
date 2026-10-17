#!/usr/bin/env python3
"""Obstacle-aware bundle screen of all actual capture internal bit paths.

This is a candidate planning bound, not routed timing or congestion proof.
Each bundle follows a shortest orthogonal path around all opaque child boxes;
per-bit endpoint offsets give a conservative length bound on that same trunk.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from s81 import hub_router as HR


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('geometry',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();geo=json.loads(a.geometry.read_text());children=geo['children'];groups=defaultdict(list)
    def endpoint(pin):
        name,p=pin.rsplit('/',1);c=children[name];point=c['pins'][p]['xy_um'];x,y=c['at_um'];w,h=c['outline_um']
        face=min(('W','E','S','N'),key=lambda f:{'W':abs(point[0]-x),'E':abs(point[0]-x-w),'S':abs(point[1]-y),'N':abs(point[1]-y-h)}[f])
        projected=[x if face=='W' else x+w if face=='E' else point[0],y if face=='S' else y+h if face=='N' else point[1]]
        return name,p.split('[')[0],face,point,projected
    for p in geo['internal_paths']:
        src,dst=endpoint(p['driver']),endpoint(p['sink'])
        groups[(src[0],src[1],src[2],dst[0],dst[1],dst[2])].append((p,src,dst))
    boxes=[(n,*c['at_um'],*c['outline_um']) for n,c in children.items()]
    die=(0,0,*geo['outline_um']);routes=[];unrouted=0;over500=0;worst=0;bit_um=0
    # _hanan_once uses 4*PITCH only as a turn cost. Zero selects minimum wire
    # length here; no raster router or physical process rule is changed.
    HR.PITCH=0
    for key,bits in sorted(groups.items()):
        src=[sum(b[1][4][i] for b in bits)/len(bits) for i in range(2)]
        dst=[sum(b[2][4][i] for b in bits)/len(bits) for i in range(2)]
        path=HR._hanan_once(src,key[2],dst,key[5],boxes,die,2.16)
        record=dict(source=key[:3],sink=key[3:],bits=len(bits),path=path)
        if path is None:
            unrouted+=len(bits);record['unrouted_bits']=len(bits)
        else:
            L=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(path,path[1:]));bounds=[]
            for p,s,d in bits:
                bound=L+sum(abs(s[3][i]-src[i])+abs(d[3][i]-dst[i]) for i in range(2))
                bounds.append(round(bound,3))
            record.update(trunk_um=round(L,3),max_bit_length_bound_um=max(bounds),over500=sum(v>500 for v in bounds))
            worst=max(worst,max(bounds));over500+=record['over500'];bit_um+=sum(bounds)
        routes.append(record)
        print('BUNDLE',key,len(bits),record.get('max_bit_length_bound_um','UNROUTED'),flush=True)
    out=dict(schema='opentallas.s81.capture_split_obstacle_screen.v1',adopted=False,physical_qualified=False,
             note='All child bodies opaque. New pins are proposed; 2.16um planning clearance. Trunk+endpoint offset is conservative, not individual detailed routes. Actual track/PG/cut capacity, clock delivery, source binding and TT/FF/DRC remain required.',
             geometry=str(a.geometry),summary=dict(actual_internal_bit_paths=len(geo['internal_paths']),bundles=len(routes),
                 unrouted_bits=unrouted,bit_bounds_over500=over500,max_bit_length_bound_um=worst,
                 total_bit_mm_bound=round(bit_um/1000,3)),routes=routes)
    a.out.write_text(json.dumps(out,indent=2)+'\n');print('CAPTURE_OBSTACLE_SCREEN',json.dumps(out['summary']),flush=True)


if __name__=='__main__':main()
