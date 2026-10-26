#!/usr/bin/env python3
"""Derive the actual native half-launch paths from the emitted die and plan.
This checks post-boot start timing, not reset closure: the caller must wait for
max_release and install every run descriptor before broadcasting launch_v.
"""
import argparse,json,re
from pathlib import Path
import b2_top as T

def check(die_path,plan_path,cmap_path):
    d=T.Die(die_path,[]);p=json.loads(Path(plan_path).read_text());cm=json.loads(Path(cmap_path).read_text())
    ps={x['id']:x for x in p['ports']};lanes={}
    for l in p['lanes']:
        a,b=ps[l['ports'][0]],ps[l['ports'][-1]]
        lanes.setdefault((a['src']['part'],b['dst']['part'],a['kind']),[]).append((l['id'],p['latency']['lanes'][l['id']]['cycles']))
    def part(n):
        assert n in cm['parts'],f'{n}: concrete partition mapping required'
        return cm['parts'][n]
    def route(a,b,kind):
        A,B=part(a),part(b)
        if A==B:return dict(cycles=0,lanes=[])
        ls=lanes.get((A,B,kind)) or lanes.get((A,B,'data' if kind=='ctl' else 'ctl'))
        assert ls,f'no {a}->{b} {kind} lane'
        return dict(cycles=max(x[1] for x in ls),lanes=[x[0] for x in ls])
    def source(n,p):
        segs=d.resolve(T.parse_expr(d.insts[n]['conns'][p],d.widths))
        assert len(segs)==1,(n,p,segs)
        s,_=segs[0];assert s[0]=='n' and s[1] in d.driver,(n,p,s)
        return d.driver[s[1]]
    paths=[]
    for target,rport in [('cp_svg_NW0','run_v'),('cp_svg_NW4','run1_v')]:
        assert d.insts[target]['master']=='ot_static_run_target',target
        assert source('hb_router_ids',rport)==(target,'run_v')
        leaf,lp=source(target,'launch_v');assert lp=='b_launch_v' and d.insts[leaf]['master']=='ot_hbm_host_cfg_leaf2',(leaf,lp)
        anchor,ap=source(leaf,'launch_v');assert (anchor,ap)==('host_cp_ingress','launch_v'),(anchor,ap)
        legs=[route(anchor,leaf,'ctl'),dict(cycles=2,rtl='ot_hbm_host_cfg_leaf CFG_LAT'),route(leaf,target,'ctl'),
              dict(cycles=2,rtl='ot_static_run_target launch_v->run_v'),route(target,'hb_router_ids','data')]
        paths.append(dict(target=target,leaf=leaf,anchor=anchor+'.'+ap,legs=legs,arrival=sum(x['cycles'] for x in legs)))
    end=max(x['arrival'] for x in paths)
    for x in paths:x['required_root_deskew']=end-x['arrival']
    return dict(verdict='PASS' if all(x['required_root_deskew']==0 for x in paths) else 'FAIL',
                arrival=end,paths=paths,reset_gate='NOT EVALUATED; wait max_release and descriptor installation before launch',
                compiler_rule='One ingress launch broadcasts to all armed ot_static_run_target instances. Both half run identities must arrive together; same-layer pair coalesces into one cohort.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--die',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--census-map',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    r=check(a.die,a.plan,a.census_map);Path(a.out).write_text(json.dumps(r,indent=1));print('B2_START_ALIGNMENT',r['verdict'],'arrival',r['arrival'],'pads',[x['required_root_deskew'] for x in r['paths']]);return int(r['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
