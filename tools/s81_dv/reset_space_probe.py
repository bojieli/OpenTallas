#!/usr/bin/env python3
"""Geometry-only candidate probe, using actual failed case LEF sizes and landing hints.

No timing/clock/RTL/cycle qualification. Old reset topology is deliberately not
claimed to fit after movement; every actual reset edge still needs rederivation.
"""
import argparse,json,copy,hashlib
from pathlib import Path
import dv_rvcase as R
import dv_diecase as C


def probe(plan,old,hints,saved):
    W,H=plan['facts']['die_um'];placer=R.Placer(W,H)
    blocks={b['name']:b for b in plan['blocks']};sizes=saved['sizes'];loc={};links={}
    for b in plan['blocks']:
        loc['u_'+b['name']]=[b['x'],b['y'],b['w'],b['h']]
        placer.add((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
    for l in plan['links']:
        nm=l['i'].replace('-','_');a,b=l['e'];links[nm]=dict(hops=l['h'],bits=l['b'],src=plan['blocks'][a[0]]['name'],dst=plan['blocks'][b[0]]['name'],dxy=b[2:4])
        for k,(x,y) in enumerate(l['sp']):
            direction=C.station_dir(l['h'],x,y);master=f"dsfd_dvrlyh_{l['b']}_{direction}"
            w,h=sizes[master];loc[f'st_{nm}_{k}']=[x-w/2,y-h/2,w,h];placer.add((x-w/2,y-h/2,x+w/2,y+h/2))
    for i,r in sorted((r['inst'],r) for r in hints['landings']):
        l=links[r['link']];b=blocks[r['dst']];x,y=l['dxy'];face=R.face_of(b,x,y)
        w,h=sizes[r['master']]
        if face in 'SN':
            xx=x-w/2;yy=b['y']-h-2 if face=='S' else b['y']+b['h']+2;pref=[(1,0),(-1,0),(0,-1 if face=='S' else 1)]
        else:
            xx=b['x']-w-2 if face=='W' else b['x']+b['w']+2;yy=y-h/2;pref=[(0,1),(0,-1),(-1 if face=='W' else 1,0)]
        px,py,d=placer.put(xx,yy,w,h,prefer=pref);loc[i]=[px,py,w,h]
    R.reserve_lanes(placer,links)
    seed=dict(plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),sizes=sizes,
        locations=copy.deepcopy(loc),obstructions=list(set(tuple(x) for v in placer.buck.values() for x in v)))
    result=dict(scope='SIGNAL_GRID_GEOMETRY_ONLY_PG_AND_RESET_TOPOLOGY_NOT_QUALIFIED',origin_grid_um=[.048,.048,0,0],seed=seed,reset_locations={},failures=[],max_move_um=0)
    # This gives only a candidate request point. Obstructions always come from actual new geometry.
    old_bottom=min(b['y'] for b in old['blocks'] if b['kind']=='frame' and b['name'].endswith('02'))
    old_street0=old_bottom-380
    old_bottom1=min(b['y'] for b in old['blocks'] if b['kind']=='frame' and b['name'].endswith('12'))
    old_street1=old_bottom1-380
    new_frames={b['name']:b for b in plan['blocks'] if b['kind']=='frame'}
    old_frames={b['name']:b for b in old['blocks'] if b['kind']=='frame'}
    dx=new_frames['f_0L00']['x']-old_frames['f_0L00']['x']
    result['reset_request_translation_x_um']=dx
    for p in hints['reset_place']:
        x,y=p['xy'];x+=dx;shift=0 if y<1650 else 24 if y<old_street0 else 39 if y<old_bottom else 54
        w,h=sizes[p['master']]
        try:
            px,py,d=placer.put(x-w/2,y+shift-h/2,w,h,step=4,rmax=405,max_distance=405,exact_edges=True,origin_grid=(.048,.048,0,0))
            result['reset_locations'][p['inst']]=[px,py,w,h];result['max_move_um']=max(result['max_move_um'],d)
        except ValueError as e:
            result['failures'].append(dict(inst=p['inst'],point=[x,y+shift],error=str(e)));break
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--old-plan',required=True);p.add_argument('--hints',required=True);p.add_argument('--saved',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    load=lambda x:json.loads(Path(x).read_text())
    r=probe(load(a.plan),load(a.old_plan),load(a.hints),load(a.saved));Path(a.out).write_text(json.dumps(r))
    print(json.dumps({k:v for k,v in r.items() if k not in ('seed','reset_locations')}));print('placed',len(r['reset_locations']));raise SystemExit(1 if r['failures'] else 0)
