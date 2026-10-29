#!/usr/bin/env python3
"""Reprice KV origins in their real GLUE frame using retained conservative data hulls."""
import json,sys,time
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r/'source'))
import count_align_plan as C
import count_align_bind as B
b=json.load(open(r/'inputs/ca_mixed_replan.json'))
rows=[]
for p,v in b['ports'].items():
    mid=.5*(v['d_lo_ps']+v['d_hi_ps'])
    rows.append(dict(port=p,src=v['src_part'],dst=v['dst_part'],src_part=v['src_part'],dst_part=v['dst_part'],
        d_ps=mid,p_dn_ps=mid-v['d_lo_ps']+.050001,p_up_ps=v['d_hi_ps']-mid+.050001,
        unshared_sta_ps=(v['wander_ps']+.050001)/.05))
ctx=C.clock_contexts(str(r/'inputs/proof'),str(r/'inputs/event/plan_sites_astk.json'),['TT','FF'],
    'spice_edge','table','shared',str(r/'inputs/proof/droop_regions.json'),202.5,'inv')
native=C.native_start_clocks(rows,ctx)
if len(sys.argv)>3 and sys.argv[3]=='declared-origin-CK':
    import copy,gen_phys as GP,schema as S
    P=S.Plan(json.load(open(r/'inputs/event/plan_sites_astk.json')))
    offsets={}
    for part,pin in list(native.items()):
        contract=GP.insertion_binding(P,P.parts[part]['type'])
        ck=pin+'__origin_CK'
        offsets[part]=dict(clock=ck,entry_clock=pin,contract=contract,qualification='DECLARED planning only; actual origin and raw-reset-export FF CK required')
        for c,q in ctx.items():
            a=copy.deepcopy(q['taps'][pin]);a['port']=ck;a['entry_clock']=pin;a['origin_insertion_binding']=contract
            mean=contract['tt' if c=='TT' else 'ff'];tol=contract['tol']
            for k,v in [('late_ps',mean+tol),('early_ps',mean-tol),('fall_late_ps',mean+tol),('fall_early_ps',mean-tol)]:
                if k in a:a[k]+=v
            q['taps'][ck]=a
        native[part]=ck
    (r/'declared_origin_CK.json').write_text(json.dumps(offsets,indent=1))
print('CONTEXT',len(native),'native clocks',flush=True)
root,edges,info=C.clock_start_edges(rows,ctx,max_hop_um=float(sys.argv[2]) if len(sys.argv)>2 else 390.,capture_taps=native,launch_taps=native,
    retime_up=True,retime_max=128,root_region='hub_C',distinct_stage_clocks=True,start_skew=(0,87.5),skew_clean=True)
print('GRAPH',root,len(edges),info,flush=True)
json.dump(dict(root=root,start_edges=edges,info=info),open(r/'native_graph.json','w'),indent=1)
summ,out,regs=C.plan(rows,start_edges=edges,start_root=root,start_skew=(0,87.5),skew_clean=True,max_depth=16)
summ.update(period_ps=833.,aperture_ps=833/8,sync_aperture_ps=26.5,pad=0,start_skew_ps=[0,87.5]);summ.setdefault('start_tree',{}).update(info)
doc=dict(summary=summ,crossings=out,regions=regs,start_edges=edges)
json.dump(doc,open(r/'native_plan.json','w'),indent=1)
print('PLAN',json.dumps(summ),flush=True)
try:
    bind=B.bind(doc,parts={p:(v['src_part'],v['dst_part']) for p,v in b['ports'].items()})
    json.dump(bind,open(r/'native_bind.json','w'),indent=1)
    print('BIND',len(bind['parts']),len(bind['regions']),flush=True)
except Exception as e:
    print('BIND_ERROR',repr(e),flush=True)
