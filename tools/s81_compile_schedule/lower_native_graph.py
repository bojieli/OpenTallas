#!/usr/bin/env python3
"""Lower actual S81 operator names to their owned native fused operations.

This is a structural graph rewrite, never numerical execution. Source programs
are the released 59-stage operator graphs. Native issue timing still requires
owner-measured endpoint/service contracts; priced durations are not inherited.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SU_SOURCE = 'rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_h.sv'
HC_SOURCE = 'rtl/dsrom_sys/s81_suhc/ot_s81_hc_core.sv'
HCP_SOURCE = 'rtl/dsrom_sys/s81_hcx/dsfd_sp_hcx_projection.sv'
HCT_SOURCE = 'rtl/dsrom_sys/s81_hcx/ot_s81_hcx_post_native.sv'
GLOBAL_GRAPH='results/arch/token_path_20261008/ds_rom.json'
# Exactly the actual fused SU chains, not a heuristic based on graph adjacency.
ALIASES = {
 'attn.quant':'attn.hc_pre', 'ffn.norm.scale':'ffn.hc_pre', 'ffn.quant':'ffn.hc_pre',
 'attn.q_norm.sumsq':'attn.q_quant','attn.kv_norm.sumsq':'attn.kv_rope_qdq',
 'attn.max':'attn.exp','attn.den':'attn.exp','attn.sink':'attn.exp',
 'ffn.shared_quant':'ffn.shared_swiglu','ffn.swiglu':'ffn.quant2','ffn.route_w':'ffn.quant2',
 'attn.cmp.norm.sumsq':'attn.cmp.row_qdq','attn.cmp.norm.rsqrt':'attn.cmp.row_qdq',
 'attn.cmp.norm.scale':'attn.cmp.row_qdq',
 'attn.cmp.k_norm.sumsq':'attn.cmp.k_rope_qdq','attn.cmp.k_norm.rsqrt':'attn.cmp.k_rope_qdq',
 'attn.cmp.k_norm.scale':'attn.cmp.k_rope_qdq',
 **{f'{block}.hc.{name}':f'{block}.hc.fn' for block in ('attn','ffn') for name in ('sumsq','rsqrt')},
 **{f'{block}.hc.pre_post':f'{block}.hc.sinkhorn' for block in ('attn','ffn')},
}
KINDS = {'attn.q_quant':('QN',0),'attn.kv_rope_qdq':('KV',1),'attn.z_quant':('QB',2),
         'ffn.shared_swiglu':('SW',3),'ffn.quant2':('SW',3),'attn.exp':('SE',4),
         'attn.normalize':('SO',5),'ffn.softplus_sqrt':('RA',8),'ffn.bias':('RB',9),
         'attn.q_rope':('QR',10),'ffn.weights':('RW',11),'attn.cmp.row_qdq':('CN',12),
         'attn.cmp.k_rope_qdq':('IK',13),'attn.cmp.pool':('CP',14)}


def layer_tail(ident):
    match=re.fullmatch(r'(L\d+)\.(.+)',ident)
    return match.groups() if match else (None, ident)


def representative(ident):
    layer,tail=layer_tail(ident)
    return layer+'.'+ALIASES.get(tail,tail) if layer else ident


def endpoint(ident):
    layer,tail=layer_tail(ident)
    if layer and tail in KINDS:
        kind,opcode=KINDS[tail]
        return dict(engine='su',port=1,endpoint='dsfd_sp_su_h',kind=kind,opcode=opcode,
                    source=SU_SOURCE,owner='s_su_missing_ops' if opcode>=12 else 's_func')
    if layer and tail in ('attn.hc.fn','ffn.hc.fn'):
        return dict(engine='hcx',port=11,endpoint='dsfd_sp_hcx_projection',kind='HCP',
                    source=HCP_SOURCE,owner='s_hc_home',semantic='normalized HC projection includes exact H sumsq and rsqrt')
    if layer and tail in ('attn.hc.sinkhorn','ffn.hc.sinkhorn'):
        return dict(engine='hcx',port=11,endpoint='ot_s81_hcx_post_native',kind='HC_TAIL',
                    source=HCT_SOURCE,owner='s_hc_home',semantic='existing HBM op2 pre/post and Sinkhorn')
    if layer and tail in ('attn.hc_pre','ffn.hc_pre','attn.hc_post','ffn.hc_post'):
        return dict(engine='hc',port=2,endpoint='ot_s81_hc_core',kind='NORM' if tail.endswith('_pre') else 'POST',
                    source=HC_SOURCE,owner='s_func')
    return None


def lower(programs, root=ROOT):
    """Keep every raw operation in coverage; alias only named native fusions.

    A complete global graph is required because native chains can span stage
    group boundaries. Cross-stage edge labels remain explicit integration
    requirements; no scalar 'ext' time invents their native data producers.
    """
    raw={}
    for program in programs:
        local={o['op']:o['id'] for o in program['ops']}
        for op in program['ops']:
            if op['id'] in raw:
                raise ValueError('duplicate source operation '+op['id'])
            raw[op['id']]=dict(op,stage=program['stage'],pred_ids=[local[p] for p in op['preds']])
    # Stage programs retain only local predecessor indexes. Recover the real
    # cross-stage dependencies from their source graph, bridging zero-cycle
    # fused markers without dropping the producer's identity.
    graph_path=root/GLOBAL_GRAPH
    external=[]
    external_edges=[]
    if graph_path.exists():
        graph=json.loads(graph_path.read_text())
        allnodes={n['id']:n for n in graph['nodes']}
        incoming={}
        for edge in graph['edges']:
            incoming.setdefault(edge['dst'],set()).add(edge['src'])
        def ancestors(ident,active,consumer):
            if ident in raw:
                return {ident}
            if ident in active:
                raise ValueError('source graph zero-cycle dependency cycle '+ident)
            node=allnodes.get(ident)
            if node is None or node['cycles']>0:
                external.append(ident)
                external_edges.append(dict(producer=ident,consumer=consumer))
                return set()
            result=set()
            for parent in incoming.get(ident,()):
                result |= ancestors(parent,active|{ident},consumer)
            return result
        for ident,op in raw.items():
            parents=set(op['pred_ids'])
            for parent in incoming.get(ident,()):
                parents |= ancestors(parent,set(),ident)
            op['pred_ids']=sorted(parents)
    aliases={ident:representative(ident) for ident in raw}
    missing=[(a,b) for a,b in aliases.items() if b not in raw]
    if missing:
        raise ValueError('native fusion target missing: '+str(missing))
    members={}
    for ident,rep in aliases.items():
        members.setdefault(rep,[]).append(ident)
    jobs={}
    for rep,source_ids in members.items():
        source=raw[rep]
        native=endpoint(rep)
        preds=sorted({aliases[p] for ident in source_ids for p in raw[ident]['pred_ids'] if aliases[p]!=rep})
        job=dict(id=rep,source_ids=source_ids,source_stages=sorted({raw[i]['stage'] for i in source_ids}),
                 preds=preds,native_binding=native,duration_cycles=None,
                 fixed_service_contract=None,dispatch_eligible=False)
        layer,tail=layer_tail(rep)
        if layer and tail=='attn.a_allgather':
            job['required_transport']=dict(mode=1,records_per_rank=28,total_output_rows=112,
                                           arg24=(1<<16)|28,
                                           payload='320 WQ_A FP32 and128 WKV FP32 words perrank',
                                           required_owner='S81 native collective integration',
                                           historical_fixture_records_per_rank=12,
                                           historical_fixture_timing_usable=False)
        if native:
            path=root/native['source']
            job['source_evidence']=[dict(path=native['source'],sha256=hashlib.sha256(path.read_bytes()).hexdigest())] if path.exists() else []
            # CN/IK/CP are not admitted merely because a wrapper source exists.
            job['requires_opcode_body_proof']=native.get('opcode',0)>=12
        jobs[rep]=job
    # Projection yields six values per rank: actual TP4 all-gather is mandatory
    # before the existing coefficient tail's 24-element input.
    inserted=[]
    for ident in list(jobs):
        layer,tail=layer_tail(ident)
        if not layer or tail not in ('attn.hc.fn','ffn.hc.fn'):
            continue
        block=tail.split('.')[0]
        gather=f'{layer}.{block}.hc.raw_allgather'
        jobs[gather]=dict(id=gather,source_ids=[],source_stages=jobs[ident]['source_stages'],preds=[ident],
                          native_binding=None,duration_cycles=None,fixed_service_contract=None,
                          dispatch_eligible=False,required_owner='s_gather',
                          required='TP4 ordered six FP32 values/rank -> 24 FP32, actual capture to VM')
        tailjob=f'{layer}.{block}.hc.sinkhorn'
        jobs[tailjob]['preds']=sorted(set(jobs[tailjob]['preds'])|{gather})
        inserted.append(gather)
        if block=='ffn':
            store=f'{layer}.attn.hc.h_store_for_hcx'
            jobs[store]=dict(id=store,source_ids=[],source_stages=jobs[ident]['source_stages'],
                            preds=[f'{layer}.attn.hc_post'],
                            native_binding=dict(engine='hc',port=2,endpoint='ot_s81_hc_core',kind='H_STORE',
                                                opcode=1,base_row=0,source=HC_SOURCE,owner='s_func'),
                            duration_cycles=None,fixed_service_contract=None,dispatch_eligible=False,
                            required='export actual updated HC private H before FFN projection reads VM')
            jobs[ident]['preds']=sorted(set(jobs[ident]['preds'])|{store})
            inserted.append(store)
    # Indexer field projection is not query packet preparation. Native QI
    # performs128-dimensional RoPE/FP4 plus weight scaling before SVC scoring.
    for ident in list(jobs):
        layer,tail=layer_tail(ident)
        if layer and tail=='attn.idx.q':
            query=f'{layer}.attn.idx.query_prepare'
            jobs[query]=dict(id=query,source_ids=[],source_stages=jobs[ident]['source_stages'],
                             preds=[ident,f'{layer}.attn.a_proj'],native_binding=None,
                             duration_cycles=None,fixed_service_contract=None,dispatch_eligible=False,
                             required_owner='s_su_missing_ops',proposed_opcode=15,
                             required='native D128 RoPE64/FP4UE8M0, projected weight scaling, actual SVC type4 frame; no512padding')
            jobs[f'{layer}.attn.idx.score']['preds']=sorted(set(jobs[f'{layer}.attn.idx.score']['preds'])|{query})
            inserted.append(query)
    # Prove the fusions retain a DAG rather than relying on original start order.
    ordered,active,seen=[],set(),set()
    def visit(ident):
        if ident in active:
            raise ValueError('native fusion dependency cycle '+ident)
        if ident in seen:
            return
        if ident not in jobs:
            raise ValueError('dangling native producer '+ident)
        active.add(ident)
        for pred in jobs[ident]['preds']:
            visit(pred)
        active.remove(ident);seen.add(ident);ordered.append(ident)
    for ident in jobs:
        visit(ident)
    unowned=[j['id'] for j in jobs.values() if not j['native_binding']]
    return dict(schema='opentallas.s81.native-graph-lowering.v1',status='NATIVE_CALENDAR_INCOMPLETE',
                raw_operations=len(raw),native_jobs=len(jobs),fused_operations=len(raw)-len(members),
                input_program_sha256={p['stage']:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest() for p in programs},
                aliases=aliases,inserted_jobs=inserted,jobs=[jobs[i] for i in ordered],
                global_dependency_graph_evidence=dict(path=GLOBAL_GRAPH,sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest()) if graph_path.exists() else None,
                unresolved_external_producers=sorted(set(external)),
                external_producer_edges=sorted({(e['producer'],e['consumer']) for e in external_edges}),
                unowned_endpoint_jobs=unowned,dispatch_eligible=False,qualified=False,
                note='Source structural lowering only; native producer allocation, fixed service and timing still required.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--programs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args()
    programs=[json.loads(p.read_text()) for p in sorted(a.programs.glob('S[0-9][0-9][0-9].json'))]
    result=lower(programs)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(f"{result['raw_operations']} raw -> {result['native_jobs']} native jobs; {result['fused_operations']} named fusions, {len(result['unowned_endpoint_jobs'])} endpoints still unbound")


if __name__=='__main__':
    main()
