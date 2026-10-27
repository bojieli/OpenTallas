#!/usr/bin/env python3
"""Continue Claude's MU size probe with R13 direction+multicast and face-affine replication.
Diagnostic plan arithmetic only, no native RTL or physical closure claim.
Usage: mu_r13_probe.py <self-contained-root> <height> <hubtype>
"""
import json,sys,collections,pathlib,os
root=pathlib.Path(sys.argv[1]); height=sys.argv[2]; hub=sys.argv[3]
sys.path.insert(0,str(root/'tools'))
import hbm_r13_mcast as M, hbm_r11_delta as R11, hbm_r10_delta as R10, hbm_r9_delta as R9
P=json.load(open(root/'plan/die_plan.json'))
bybus={frozenset(b['name'] for b in P['partition_types'][tn]['buses']):M.bus_faces(P,part)
       for part,tn in [('NW_hub','q_hub_nw'),('NE_hub','q_hub_ne')]}
dirs=json.load(open(root/'port_dirs.json'))
def resolve(t,bi,conns=None,log=print):
    return M.resolve_lanes_mcast(t,bi,conns,log,dirs,False,bybus[frozenset(b['name'] for b in t['buses'])])
R10.resolve_lanes=resolve
original=R9.plan_quadrants
def quadrant(t,S,*args,**kwargs):
    for n,s in enumerate(t['internal_stations']):
        s['_r13_bits'],s['_r13_id']=s['bits'],n
    Q=original(t,S,*args,**kwargs)
    for s in t['internal_stations']:
        s.pop('_r13_bits',None);s.pop('_r13_id',None)
    M.face_affine(Q,t['outline_um'][0])
    # Same affinity iteration as the current single-user planS2.
    M.affinity(Q,t,1)
    for x in Q['stations']:
        x[0].pop('_r13_bits',None);x[0].pop('_r13_id',None)
    return Q
R9.plan_quadrants=quadrant
src=(root/'mu_probe_claude.py').read_text()
src=src.replace('hubs = [("NW_hub", "q_hub_nw"), ("NE_hub", "q_hub_ne")]',
 'hubs = [("NW_hub", "q_hub_nw")]' if hub=='q_hub_nw' else 'hubs = [("NE_hub", "q_hub_ne")]')
bound='3957.12' if hub=='q_hub_nw' else '3002.4'
sys.argv=[str(root/'mu_probe_claude.py'),str(root/'tools'),str(root/'plan'),'all',height,bound]
exec(compile(src,str(root/'mu_probe_claude.py'),'exec'),{'__name__':'__main__'})
