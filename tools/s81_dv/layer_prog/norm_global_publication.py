#!/usr/bin/env python3
"""Predict actual-source publication occupancy, without issuing a production job.

Inputs are component-relative XG-pin fragment dates and complete current word /
fragment boundary routes. Every upstream native partial epoch remains held.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path


def compose(publication,routes,vpaths,include_resource_slots=False):
    sha=publication['source_top_sha256']
    if routes['source_top_sha256']!=sha or vpaths['source_top_sha256']!=sha:
        raise ValueError('same source publication and transport required')
    pos={f'u_s_{c}{t}':(c,t)for c in range(8)for t in 'SN'}
    line={}
    for p in routes['ring']:
        if p['input']not in ('ri_e','ri_w')or p['status']!='PASS_DIRECT_NX':continue
        if p['active_bits']!=1045:raise ValueError('all header/BF payload bits must be source traced')
        source=p['source_slice'];side='e'if p['output']=='ro_e'else'w'
        c,t=pos[source];dc,dt=pos[p['slice']]
        if t!=dt or dc!=c+(1 if side=='e'else-1):raise ValueError('actual horizontal publication route differs')
        line[source,side]=(p['slice'],p['edges'])
    if len(line)!=28:raise ValueError('all28 actual horizontal word links required')
    vp={p['source_slice']:p for p in vpaths['complete_V_paths']}
    if set(vp)!=set(pos)or any(p['full_source_V_edges']is None for p in vp.values()):
        raise ValueError('all16 measured candidate V path sums required')
    out=defaultdict(list);local=defaultdict(list);gather=defaultdict(list);head=defaultdict(list)
    def deliver(sl,edge,src,kind):
        gather[sl].append(dict(edge=edge,source=src,kind=kind))
        if sl=='u_s_0N'and src['family']=='bf16'and src['header_index']&128:head[edge].append(src)
    def walk(sl,side,edge,hops,src):
        while hops:
            out[sl,side,edge].append(src)
            dst,age=line[sl,side];edge+=age+2
            deliver(dst,edge,src,'line_'+side)
            sl=dst;hops-=1
    for e in publication['events']:
        if e['fragment']!=0:continue
        sl=e['slice'];c,t=pos[sl];src={k:e[k]for k in ('slice','sid','leaf','global_beat','header_index','family','candidate_k')}
        # XG xf pin event -> xf input register -> own fragment collector ->
        # line output is6edges. Paired actual rstop proof gives V_ASM=V+2.
        own=e['relative_XG_input_edge']+6
        for node,edge,kind in [(sl,own,'own'),(vp[sl]['destination_slice'],own+vp[sl]['full_source_V_edges']+2,'V_assembled')]:
            local[node,edge].append(src);deliver(node,edge,src,kind)
            if 7-c:walk(node,'e',edge,7-c,src)
            if c:walk(node,'w',edge,c,src)
    conflicts=[dict(kind='line_output',slice=sl,side=side,edge=edge,sources=v)for(sl,side,edge),v in sorted(out.items())if len(v)>1]
    conflicts += [dict(kind='own_or_V_assembled',slice=sl,edge=edge,sources=v)for(sl,edge),v in sorted(local.items())if len(v)>1]
    conflicts += [dict(kind='HEAD_egress',slice='u_s_0N',edge=edge,sources=v)for edge,v in sorted(head.items())if len(v)>1]
    expected=len([e for e in publication['events']if e['fragment']==0])
    if any(len(x)!=expected for x in gather.values()):raise ValueError('predicted allgather ownership/count differs')
    result=dict(schema='opentallas.s81.norm_global_publication_prediction.v1',
        status='PREDICTED_SOURCE_OCCUPANCY_CONFLICTS'if conflicts else'PREDICTED_SOURCE_OCCUPANCY_CLEAR',
        source_top_sha256=sha,consumer=publication['consumer'],conflicts=conflicts,
        predicted_gather=gather,predicted_HEAD_egress=[dict(edge=e,sources=v)for e,v in sorted(head.items())],
        local_source_pin_to_own_line_edges=6,line_stop_edges=2,V_assembly_after_own_line_extra_edges=2,
        latest_relative_gather_edge=max(x['edge']for v in gather.values()for x in v),
        conditional_on_aligned_native_partial_component=True,
        upstream_per_leaf_native_producer_dates=None,input_arrival_leases=None,
        candidate_configuration_adopted=False,actual16stop_gate=False,
        physical_phase_qualified=False,HOST_START_authority=False,full_token=False)
    if include_resource_slots:
        result['resource_slots']=[('line',sl,side,edge)for(sl,side,edge)in out]+[('g0',sl,'',edge)for(sl,edge)in local]+[('head','u_s_0N','',edge)for edge in head]
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('publication','routes','vpaths','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh prediction output required')
    r=compose(*[json.loads(getattr(a,n).read_text())for n in ('publication','routes','vpaths')]);a.out.write_text(json.dumps(r,indent=1)+'\n');print(r['status'],'conflicts',len(r['conflicts']),'latest',r['latest_relative_gather_edge'])
