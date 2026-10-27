#!/usr/bin/env python3
"""Continue Claude's MU size probe with R13 direction+multicast and face-affine replication.
Diagnostic plan arithmetic only, no native RTL or physical closure claim.
Usage: mu_r13_probe.py <self-contained-root> <height> <hubtype>
"""
import json,sys,collections,pathlib,os
root=pathlib.Path(sys.argv[1]); height=sys.argv[2]; hub=sys.argv[3]
sys.path.insert(0,str(root/'tools'))
import hbm_r13_mcast as M, hbm_r11_delta as R11, hbm_r10_delta as R10, hbm_r9_delta as R9
import hub_shelf_dp as DP
_pack=R9.HR.pack_hub

def _buddy_pack(W,H,cores,**kw):
    import re
    by={c["inst"]:c for c in cores};items=[];pairs={};used=set()
    for c in cores:
        m=re.fullmatch(r"u_vmb_Q(\d+)(_mu1)?",c["inst"])
        if not m:continue
        lid=2*int(m.group(1))+(1 if m.group(2) else 0)
        fid=f"u_mu_fused_{lid}"
        assert fid in by,(c["inst"],fid)
        f=by[fid];name=f"__mu_buddy_{lid}"
        a=c["w"]*c["h"];b=f["w"]*f["h"]
        items.append(dict(inst=name,w=c["w"]+8.64+f["w"],h=max(c["h"],f["h"]),
                          ocx=(a*c["ocx"]+b*f["ocx"])/(a+b),ocy=(a*c["ocy"]+b*f["ocy"])/(a+b)))
        pairs[name]=(c,f);used.update((c["inst"],fid))
    items.extend(c for c in cores if c["inst"] not in used)
    assert len(pairs)==8,len(pairs)
    try:pl,info=_pack(W,H,items,**kw)
    except ValueError:
        kw.pop("shelves",None)
        pl,info=DP.pack_hub_dp(W,H,items,**kw)
    out={n:xy for n,xy in pl.items() if n not in pairs}
    for name,(c,f) in pairs.items():
        x,y=pl[name]
        out[c["inst"]]=(x,y)
        out[f["inst"]]=(round(x+c["w"]+8.64,3),y)
    assert set(out)==set(by)
    info["mu_buddies"]=len(pairs)
    info["mu_pair_gap_um"]=8.64
    return out,info
R9.HR.pack_hub=_buddy_pack
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
    kwargs["named_ends"]=True
    Q=original(t,S,*args,**kwargs)
    import re
    banks=sorted(h["inst"] for h in t["hard_cores"] if h["inst"].startswith("u_vmb_"))
    assert len(banks)==16, len(banks)
    assignment={n:i//8 for i,n in enumerate(banks)}
    for h in Q["cores"]:
        n=h["inst"]
        leaf=re.fullmatch(r"u_mu_fused_(\d+)",n)
        node=re.fullmatch(r"u_mu_fused_n[123].*_q([01])(?:_\d+)?",n)
        if leaf:assignment[n]=int(leaf.group(1))//8
        elif node:assignment[n]=int(node.group(1))
    assert sum(n.startswith("u_mu_fused_n") for n in assignment)==14
    for n,k in assignment.items():
        assert n in Q["segof"],n
        Q["segof"][n]=k
    Q["stations"]=[(st,ea,eb,Q["segof"][ea[1]] if ea[0]=="C" else ka,Q["segof"][eb[1]] if eb[0]=="C" else kb)
                   for st,ea,eb,ka,kb in Q["stations"]]
    Q["mu_atomic_groups"]=assignment
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
bound='3957.12'
sys.argv=[str(root/'mu_probe_claude.py'),str(root/'tools'),str(root/'plan'),'all',height,bound]
exec(compile(src,str(root/'mu_probe_claude.py'),'exec'),{'__name__':'__main__'})
