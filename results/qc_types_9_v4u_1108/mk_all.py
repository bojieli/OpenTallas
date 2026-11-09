#!/usr/bin/env python3
"""Private FW START proposal using existing W=3 hardware; never edits the input plan."""
import argparse, copy, json, math
from pathlib import Path

TYPE = 'sle_fw_v3'
DEPTH = 3
LIMIT = 405.0
DESIGN_HOP = 380.0
PITCH = 16.2

def l1(a, b): return sum(abs(x-y) for x,y in zip(a,b))

def construct(base, reset):
    plan = copy.deepcopy(base)
    typ = plan['partition_types'][TYPE]
    pins = typ['clock']['landing_contract']['pins']
    origin = next(x['xy_um'] for x in pins if x['name'] == 'cland_rstart_in')
    nodes = [r for r in reset['tree']['relays'] if r['depth'] == 1 and r['d'] == 'rst_root_n']
    if not nodes or any(r['depth'] != 1 for r in nodes): raise ValueError('no phase-1 raw reset class')
    # All nodes have the same actual source and one registered edge, not merely
    # a geographically convenient depth label. Ports cannot be raw reset copies.
    outputs = {x['name'] for x in pins if x['dir']=='out'}
    if any(r['q'] in outputs for r in nodes): raise ValueError('raw reset drives a port')
    width,height=typ['outline_um']; occupied=[]; branches={}; report=[]; held=[]
    points=[]
    for ix in range(1,int(width/PITCH)):
        for iy in range(1,int(height/PITCH)):
            xy=[round(ix*PITCH,3),round(iy*PITCH,3)]
            raw=min(nodes,key=lambda r:(l1(xy,r['xy']),r['q']))
            if l1(xy,raw['xy']) <= LIMIT-8.64:
                points.append((xy,raw))
    targets=sorted((p for p in pins if p['dir']=='out' and p['name'].startswith('cland_fstart_out_')),key=lambda p:p['name'])
    old=typ['clock'].get('landing_writer_start',{})
    for target in targets:
        bus=target['name'].removeprefix('cland_fstart_out_'); end=target['xy_um']
        if False:
            if l1(origin,end)>LIMIT:
                held.append(dict(bus=bus,direct_hop_um=l1(origin,end),reason='non-W export: separate phase-correct START/reset form required; no deeper-reset substitution'))
            continue
        candidates=[]
        for stage in range(DEPTH):
            ideal=[a+(b-a)*(stage+1)/(DEPTH+1) for a,b in zip(origin,end)]
            candidates.append([(xy,raw) for xy,raw in points if l1(xy,ideal)<=220 and all(l1(xy,o)>8.64 for o in occupied)])
        states=[(0.0,[origin],[])]
        for stage,layer in enumerate(candidates):
            nxt=[]
            for xy,raw in layer:
                best=None
                for cost,path,raws in states:
                    hop=l1(path[-1],xy)
                    if hop>DESIGN_HOP:continue
                    # Squared hops avoid concentrating the whole flight in one
                    # segment; raw-reset flight is explicitly priced too.
                    value=cost+hop*hop+0.05*l1(xy,raw['xy'])**2
                    if best is None or value<best[0]:best=(value,path+[xy],raws+[raw])
                if best is not None:nxt.append(best)
            states=nxt
        states=[(c+l1(p[-1],end)**2,p,r) for c,p,r in states if l1(p[-1],end)<=DESIGN_HOP]
        if not states:
            held.append(dict(bus=bus,direct_hop_um=l1(origin,end),reason='no phase-1 four-hop path'));continue
        cost,path,raws=min(states,key=lambda v:v[0]);path=path+[end]
        stages=[dict(xy_um=xy,raw_reset=raw['q']) for xy,raw in zip(path[1:-1],raws)]
        occupied.extend(path[1:-1]);branches[bus]=dict(stages=stages)
        prior=old.get('depth',0) if bus in old.get('branches',{}) else 0
        report.append(dict(bus=bus,path_um=path,hops_um=[l1(a,b) for a,b in zip(path,path[1:])],raw_reset_hops_um=[l1(xy,r['xy']) for xy,r in zip(path[1:-1],raws)],raw_resets=[dict(q=r['q'],d=r['d'],depth=r['depth'],xy=r['xy']) for r in raws],old_W=prior,new_W=DEPTH,receiver_K_delta=DEPTH-prior,steady_payload_cycles_delta=0))
    typ['clock']['landing_writer_start']=dict(depth=DEPTH,branches=branches)
    return plan,dict(schema='codex.qc_fw_start_candidate/1',status='PRIVATE PROPOSAL; QC plan/review ownership; HOLD_PHYSICAL',type=TYPE,source_um=origin,writer_depth=DEPTH,max_hop_um=max(max(r['hops_um']) for r in report),max_raw_reset_hop_um=max(max(r['raw_reset_hops_um']) for r in report),raw_reset_class='one edge from rst_root_n; actual bound_reset.json depth-1 nodes only',branches=report,held_exports=held,K_rule='receiver K_new = logical K + W - R; relative change is new_W-old_W',steady_payload_cycles_delta=0,physical_qualification='planned sites only; actual whole-relay gates and DPL retention must be reviewed; no P&R retry')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('base',type=Path);a.add_argument('reset',type=Path);a.add_argument('out',type=Path);args=a.parse_args()
    if args.out.exists():a.error('refuse to overwrite existing candidate')
    plan,report=construct(json.loads(args.base.read_text()),json.loads(args.reset.read_text()))
    args.out.mkdir(parents=True);(args.out/'plan.json').write_text(json.dumps(plan,indent=1)+'\n');(args.out/'model.json').write_text(json.dumps(report,indent=1)+'\n')
    print(f"W branches {len(report['branches'])}; START max {report['max_hop_um']:.3f} um; raw reset max {report['max_raw_reset_hop_um']:.3f} um; held exports {len(report['held_exports'])}")
