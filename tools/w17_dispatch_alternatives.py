#!/usr/bin/env python3
"""Price expert link widths and local template/cache proposals on actual owners.

This calendar is a partial feasibility comparison, never accepted performance.
It preserves the e61 baseline and requires full consumer/PHY/collective costs.
"""
import argparse, ast, json, math
from decimal import Decimal as D
from pathlib import Path
import w17_integer_expert_residency as R
from w17_conservative_geometry_search import GEOMETRY,descriptor_cost,product_geometry

BASELINE=('e61a5a1ee89497562fdf5aa9e82b85d346cd2b57','results/quality/w16_w17_geometry_search_20261001/search.json')
FLOORPLAN=(GEOMETRY[0],'results/floorplan/v41_pack_refit_w10_interim.json')
TEMPLATE_REPLAY=('a1aef63e8','results/rtl/w17_connected_token_preparation_20261001/compact_cfg_template_replay.json')
REQUEST=5120*16
RETURN=1280*16
FRAME_BITS=256

def worst_selection(stages,cost,k=6):
    """Exact stage-capacity DP; six distinct expert IDs, not six invented owners."""
    dp={0:(0,[])}
    for stage,count,distance in stages:
        nxt={}
        for used,(score,trace) in dp.items():
            for take in range(min(count,k-used)+1):
                value=score+(cost(distance,take) if take else 0)
                if used+take not in nxt or value>nxt[used+take][0]:
                    nxt[used+take]=(value,trace+([(stage,take,distance)] if take else []))
        dp=nxt
    if k not in dp:raise ValueError('not enough distinct resident experts')
    return dp[k]

def ceildiv(a,b):return (a+b-1)//b

def build():
    source={name:R.blob(p) for name,p in [('baseline',BASELINE),('floorplan',FLOORPLAN),('geometry',GEOMETRY),('template_replay',TEMPLATE_REPLAY)]}
    base=json.loads(source['baseline']);old=next(x for x in base['candidates'] if x['q_pairs']==1024)
    fp=json.loads(source['floorplan']);geo=fp['geometry']
    env={}
    selected=[]
    for n in ast.parse(source['geometry']).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('WIRE_PS_PER_UM_LOADED','WIRE_OVERHEAD_PS','UNCERTAINTY_PS','CDC_W18') for t in n.targets):selected.append(n)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<pinned link parameters>','exec'),env)
    # Conservative full-outline Manhattan on-die envelope at every stage hop.
    # Off-die PHY/link service is separate and must be bound before admission.
    distance_um=D(str(geo['die_w_um']))+D(str(geo['die_h_um']))
    segment=(D(2500)/3-D(str(env['UNCERTAINTY_PS']))-D(str(env['WIRE_OVERHEAD_PS'])))/D(str(env['WIRE_PS_PER_UM_LOADED']))
    route_cycles=math.ceil(distance_um/segment)
    cdc=env['CDC_W18'];activation_cdc_ticks=cdc['slow_to_fast_fast_cycles']*3
    result_cdc_ticks=cdc['fast_to_slow_slow_cycles']*4
    reverse_cdc_ticks=activation_cdc_ticks+result_cdc_ticks
    manifest=R.inputs();templates,strides=R.templates(manifest,1024)
    owners,stages,cap=R.assignments(manifest,templates,strides)
    assert cap==85 and len(stages)==181 and old['template_sha256']==R.sha(json.dumps(templates,sort_keys=True,separators=(',',':')).encode())
    layer_stages=[]
    for layer in range(40):
        counts={}
        for o in owners:
            if o['layer']==layer:counts[o['stage']]=counts.get(o['stage'],0)+1
        anchor=min(counts)
        layer_stages.append([(s,n,s-anchor+1) for s,n in sorted(counts.items())])
    spine=next(x for x in fp['channels']['channels'] if x['channel']=='spine_0')
    capacity=spine['tracks'];existing=spine['demand_wires']
    corridor_area=D(str(geo['spine_h_um']))*D(str(geo['die_w_um']))/D(1000000)
    rows=[]
    for width in (256,512,1024,2048):
        for policy in ('compact_per_expert_activation','compact_stage_activation_reuse','central_expanded_config'):
            reuse=policy=='compact_stage_activation_reuse'
            central=policy=='central_expanded_config'
            costs=[];traces=[]
            for layer,residents in enumerate(layer_stages):
                def cost(d,k):
                    groups=1 if reuse else k
                    request=groups*REQUEST+k*FRAME_BITS
                    if central:request+=k*3*1024*25*48
                    ret=k*(RETURN+FRAME_BITS)
                    # Every request/return is store-and-forward. Reuse sends one
                    # bounded batch per destination, so it also pays whole-batch
                    # serialization before the first invocation; no cut-through.
                    serial=ceildiv(request,width)+ceildiv(ret,width)
                    route=2*route_cycles*groups
                    cdc_ticks=groups*activation_cdc_ticks+k*result_cdc_ticks+groups*reverse_cdc_ticks
                    # Rootowner lookup and stage-local slot validation each
                    # have a proposed two-fast-cycle registered read.
                    owner_ticks=k*4*3
                    return d*(serial+route)*3+cdc_ticks+owner_ticks
                value,trace=worst_selection(residents,cost)
                costs.append(value);traces.append(dict(layer=layer,selected_stage_counts=trace,partial_transport_ticks=value))
            new_tracks=2*(width+64) # separate directions,64 control/credit each
            total_tracks=existing+new_tracks
            corridors=ceildiv(total_tracks,capacity);additional=corridors-1
            # Full-packet landing; lease retains activation until last expert
            # actually consumes it and the ordered return completes.
            max_request=REQUEST+(6 if reuse else 1)*FRAME_BITS
            if central:max_request+=3*1024*25*48
            landing_bits=2*(max_request+RETURN+FRAME_BITS)
            pipeline_bits=2*(width+64)*route_cycles
            # Stage-local immutable128x16 slot->layer/expert/valid owner table.
            slot_table_bits=128*16
            slot_mux_bits=127*16
            owner_area=(D(slot_table_bits)*D('.2916')+D(slot_mux_bits+15)*D('.2'))/D('.5')/D(1000000)
            storage_area=D(landing_bits+pipeline_bits)*D('.2916')/D('.5')/D(1000000)
            # Two-input relay/local-source selection plus landing-buffer read.
            mux_bits=2*(width+64)+max_request-width
            mux_area=D(mux_bits)*D('.2')/D('.5')/D(1000000)
            # Slot/family/go10-bit registered binary broadcast; existing leaf
            # slot registers are already in e61 descriptor area, count once.
            fanout_bits=10*(1024-1)
            fanout_area=D(fanout_bits)*D('.2916')/D('.5')/D(1000000)+D(fanout_bits)*D('.23328')/D('.5')/D(1000000)
            extra=corridor_area*additional+owner_area+storage_area+mux_area+fanout_area
            rows.append(dict(link_bits_per_rank_source_cycle=width,TP4_separate_replicas=4,
                aggregate_bits_per_source_cycle=width*4,policy=policy,
                source_order_worst_six_distinct_expert_partial_transport_ticks=sum(costs),
                partial_transport_us=str(D(sum(costs))/D(3600)),
                cfg_and_stream_partial_ticks=40*6*329*3,
                transport_plus_cfg_and_stream_partial_us=str(D(sum(costs)+40*6*329*3)/D(3600)),
                layer_worst_selections=traces,
                tracks=dict(existing=existing,added_both_directions=new_tracks,total=total_tracks,
                    capacity_per_corridor=capacity,corridors_required=corridors,
                    additional_corridors=additional,single_existing_corridor_fits=total_tracks<=capacity),
                area=dict(additional_corridor_mm2=str(corridor_area*additional),
                    local_owner_table_mm2=str(owner_area),landing_and_route_registers_mm2=str(storage_area),
                    relay_and_buffer_read_mux_mm2=str(mux_area),local_descriptor_fanout_mm2=str(fanout_area),
                    additional_screen_mm2_per_stage_rank=str(extra),
                    residual_field_after_candidate_additions_mm2=str(D(old['fixed_product_field_remainder_after_q_cfg_BF1024_mm2'])-extra)),
                local_owner=dict(slot_table_bits=slot_table_bits,entries=128,entry_bits=16,
                    fields={'valid':1,'layer':6,'expert':9},table_lookup_cycles_candidate=2,
                    root_lookup_cycles_candidate=2,root_table_replicas=160,
                    expert_stage_slot_table_replicas=724),
                local_template_expansion=dict(required=not central,cfg_cycles_per_family=35,
                    cfg_plus_stream_partial_cycles_per_expert=329,
                    templates_already_counted_in_baseline_area=True),
                credits=dict(landing_slots_per_direction=2,maximum_active_activation_leases_per_stage=1,
                    buffered_job_descriptors_per_activation=6 if reuse else 1,
                    landing_bits=landing_bits,route_pipeline_bits=pipeline_bits,
                    release='After actual descriptor validation, all selected expert reads, ordered consumer completion and reverse credit/CDC; partial transport ticks never substitute for finaldone.'),
                exactness='Proposal: same selected expert IDs in ascending order, same weights/activation bytes and local template word order. Requires q1024-specific dynamicbase replay and full producer/collective gates.',
                physical_admission=False,adopt=False))
    return dict(schema='opentallas.w17.dispatch-alternatives.v1',
        baseline_preserved=dict(commit=BASELINE[0],expert_dispatch_serialization_us=440,
            interpretation='Critical feasibility finding; not accepted performance, connected timing or a full-token rate.'),
        source_pins={name:dict(commit=p[0],path=p[1],sha256=R.sha(source[name])) for name,p in [('baseline',BASELINE),('floorplan',FLOORPLAN),('geometry',GEOMETRY),('template_replay',TEMPLATE_REPLAY)]},
        geometry_scope=fp['claim_boundary'],
        route_model=dict(full_outline_manhattan_um=str(distance_um),wire_ps_per_um=env['WIRE_PS_PER_UM_LOADED'],
            uncertainty_ps=env['UNCERTAINTY_PS'],registered_route_cycles_per_hop=route_cycles,
            source_route_clock_hypothesis_Hz=1200000000,source_model_not_current_physical_qualification=True,
            PHY_and_package_service_requires_separate_bound=True),
        CDC_model=dict(fast_to_slow_ticks=result_cdc_ticks,slow_to_fast_ticks=activation_cdc_ticks,
            reverse_credit_ticks=reverse_cdc_ticks,source=cdc['src']),
        frame_proposal=dict(bits=FRAME_BITS,fields_bits={'global_key':17,'weight_FP32':32,'epoch':32,
            'position':21,'ordinal':3,'stage':8,'slot':7,'family':2,'valid':1,'length':17,
            'opcode':8,'source_rank':2,'destination_rank':2,'flags':8},qualified=False),
        candidates=rows,
        full_model_dependencies=['Physical homes and actual word codecs for all active nonexpert matrices/constants and Engram',
            'BF legal spatial fit and current q/clock/power qualification',
            'Actual link PHY service, credits, corridor connectivity and alignment',
            'Actual activation quantization, SU/SFU and per-expert TP intermediate/output collectives',
            'Ordered consumer/finaldone calendar and context/epoch reuse validation',
            'Correct CKV visibility/prelease and persistent full-program state'],
        accepted_performance=False,whole_token_cycles_qualified=False,
        engine_RTL_build_ready=False,physical_admission=False,headline_rate=None,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2)+'\n')
