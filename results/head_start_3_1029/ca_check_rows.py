#!/usr/bin/env python3
"""HEAD-START-2: routed START phase check per capture endpoint (TT setup w/ droop derate + 60 ps unc, FF hold + 25 ps unc,
OpenSTA propagated clock on GRT RC, CPPR on). Endpoint worst setup (TT) and worst hold (FF) are combined; the plan's
count alignment may shift capture by whole cycles J (RTL PAD/count), the capture EDGE is fixed by RTL (EDGE_FALL).
  as-built margin   = max_J min(sTT + J*T, hFF - J*T)          (current RTL edges)
  re-plan margin    = max_k min(sTT + k*T/2, hFF - k*T/2)       (edge re-chosen = --start-prev re-plan)
Crossing = worst-path launch stage != capture stage (either check); intra-stage endpoints must have J=0 slack >= 0.
usage: ca_check.py endpoint_TT endpoint_FF start_overlay.json start_stages.json out.json driven_mapped.json"""
import json,re,sys,collections
T=833.333
ft,ff,ovf,stf,out=sys.argv[1:6]
mapped=sys.argv[6]
def ld(f):
    d={}
    for l in open(f):
        x=l.split();d[x[0]]=dict(smax=float(x[1]),smin=float(x[2]))
    return d
tt,fh=ld(ft),ld(ff)
inv={v:k for k,v in json.load(open(ovf))['cell_names'].items()}
# launch stages = stages of the FFs in the D-pin fan-in cone (netlist walk through combinational cells and BUF chains)
mod=json.load(open(mapped))['modules']['ot_die_start_stages'];drv={}
for cn,c in mod['cells'].items():
    for p,bits in c['connections'].items():
        if c['port_directions'][p]=='output':
            for b in bits:drv[b]=cn
isff=lambda cn:mod['cells'][cn]['type'].startswith(('DFF','SDFF'))
def cone(cn):
    seen=set();ffs=set();stack=[b for p,bits in mod['cells'][cn]['connections'].items() if p=='D' for b in bits]
    while stack:
        b=stack.pop()
        if b in seen or not isinstance(b,int):continue
        seen.add(b);d=drv.get(b)
        if d is None:ffs.add('PORT');continue
        if isff(d):ffs.add(d);continue
        stack+=[x for p,bits in mod['cells'][d]['connections'].items() if mod['cells'][d]['port_directions'][p]=='input' for x in bits]
    return ffs
st={s['id']:s for s in json.load(open(stf))['stages']}
def stage(pin):
    c=pin.split('/')[0]
    if c not in inv:return 'PORT:'+pin
    m=re.search(r'u_st_(\w+?)\.',inv[c]);return m[1] if m else '?'
rows=[]
for n in tt:
    s,h=tt[n]['smax'],fh[n]['smin'];cap=stage(n);L={('PORT' if f=='PORT' else re.search(r'u_st_(\w+?)\.',f)[1]) for f in cone(inv[n.split('/')[0]])};la=lb=','.join(sorted(L-{cap,'PORT'})) or cap
    full=max(((min(s+j*T,h-j*T)),j) for j in range(-12,13))
    half=max(((min(s+k*T/2,h-k*T/2)),k) for k in range(-24,25))
    rows.append(dict(ep=n,cap=cap,launch_setup=la,launch_hold=lb,cross=(la!=cap or lb!=cap),s=s,h=h,asbuilt=full[0],J=full[1],replan=half[0],k=half[1],
                     edge_fall=st.get(cap,{}).get('edge_fall')))
X=[r for r in rows if r['cross']];I=[r for r in rows if not r['cross']]
def summ(R,key):
    v=[r[key] for r in R];return dict(n=len(R),min=round(min(v),2) if v else None,lt0=sum(x<0 for x in v),lt100=sum(x<100 for x in v))
res=dict(schema='head_start_routed_phase/1',period_ps=T,
  basis='OpenSTA propagated clock, GRT50 RC (estimate_parasitics -global_routing), NLDM liberty (no spice clock-cal), CPPR on; TT setup: data cell x1.10 / net x1.05 droop derate + 60 ps unc; FF hold: 25 ps unc; clock AOCV 0.21%/mm NOT applied (UNCHECKED term)',
  intra=dict(n=len(I),setup_lt0=sum(r['s']<0 for r in I),hold_lt0=sum(r['h']<0 for r in I),min_setup=round(min(r['s'] for r in I),2),min_hold=round(min(r['h'] for r in I),2),nonzero_J_needed=sum(r['J']!=0 for r in I)),
  crossing=dict(asbuilt=summ(X,'asbuilt'),replan=summ(X,'replan'),J_hist=dict(sorted(collections.Counter(r['J'] for r in X).items())),
               halfstep_hist=dict(sorted(collections.Counter(r['k'] for r in X).items())),
               fail_asbuilt_capture_stages=len({r['cap'] for r in X if r['asbuilt']<0}),
               fail_asbuilt_edge_fall=dict(collections.Counter(str(r['edge_fall']) for r in X if r['asbuilt']<0))),
  worst_asbuilt=sorted(X,key=lambda r:r['asbuilt'])[:15],worst_replan=sorted(X,key=lambda r:r['replan'])[:15],worst_intra=sorted(I,key=lambda r:min(r['s'],r['h']))[:10])
res["rows"]=rows; json.dump(res,open(out,"w"),indent=0)
print(json.dumps({k:v for k,v in res.items() if not k.startswith('worst')},indent=1))
