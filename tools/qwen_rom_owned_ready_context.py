#!/usr/bin/env python3
"""Additive, default-off owned readiness producer sizing; no RTL admission.

Snapshot channels are a concrete proposed implementation, not instantiated
source hardware. Existing tile and failed construction receipts are immutable.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_local_parent_composition as P
R=P.R
OUT=Path('results/uarch/qwen_rom_owned_ready_context_20261002')
PEER='33385b882'
INV='INVx1_ASAP7_75t_R'
PERIOD={'stream':1000/1.2,'serial':1000/.9,'service':1000.}


def accept_snapshot(request_sequence, snapshot_sequence, acknowledged, released,
                    predicate, crossed_fifo_empty, causal_debt_empty):
    values=(acknowledged,released,predicate,crossed_fifo_empty,causal_debt_empty)
    if any(type(v) is not bool for v in values):
        raise ValueError('binary actual producer predicates required')
    if any(type(v) is not int or not 0<=v<2**32 for v in
           (request_sequence,snapshot_sequence)):
        raise ValueError('source irs_serial aperture')
    return request_sequence==snapshot_sequence and all(values)


def allocation():
    rows=[]
    def add(name,domain,width,purpose):
        for bit in range(width):
            rows.append(dict(instance=name+'['+str(bit)+']',domain=domain,
                             cell=R.ASR,restoring_cell=INV,purpose=purpose))
    channels=[]
    for name,domain in [('stack'+str(i),'service') for i in range(4)]+[
            ('serial','serial'),('stream','stream')]:
        # Conservative common CDC implementation even for the stream-local
        #channel; no stages are optimized away or silently credited.
        local={'release_sync':2,'request_sync':2,'return_ack_sync':2,
               'snapshot_ack':1,'frozen_sequence_and_ready':33}
        dest={'ack_sync':2,'sample_sequence_and_ready':33,
              'sample_valid':1,'committed':1}
        for field,width in local.items():add(name+'.'+field,domain,width,'local frozen snapshot')
        for field,width in dest.items():add(name+'.'+field,'stream',width,'acknowledged stream sample')
        channels.append(dict(name=name,source_domain=domain,source_FFs=sum(local.values()),
                             stream_FFs=sum(dest.values()),snapshot_bits=33))
    add('request_sequence','stream',32,'source identity_t.irs_serial; no wrap with debt')
    add('request_toggle','stream',1,'one outstanding snapshot transaction')
    add('joined_ready','stream',1,'preedge readiness; cannot launch on sampling edge')
    add('held_instruction','stream',379,'all24 DYN-adjusted instruction fields')
    add('held_vector','stream',128,'actual tile x128')
    add('held_identity','stream',192,'full source identity_t including irs_serial')
    add('held_PC','stream',5,'source32-PC aperture')
    add('held_valid','stream',1,'request owned through IREG acceptance/explicit abort')
    return rows,channels


def buffer_price(corner,fanout,length):
    _,lib,caps=R.library(corner)
    cap=fanout*caps[(R.ASR,'CLK')]['cap_fF']+.165790*length
    result={'cap_fF':cap,'length_um':length,'fanout':fanout}
    for t in ('rise','fall'):
        result[t+'_delay_ps']=R.envelope(lib[R.BUF],'cell_'+t,cap,5,80)
        result[t+'_slew_ps']=R.envelope(lib[R.BUF],t+'_transition',cap,5,80)
    result['within_320ps_slew']=max(result[t+'_slew_ps'][1] for t in ('rise','fall'))<=320
    return result


def price():
    rows,channels=allocation()
    counts={d:sum(r['domain']==d for r in rows) for d in PERIOD}
    # Dedicated candidate hub reservation. These are distinct abstract row
    #sites, not a claim of legal placement among macro OBS/PG access.
    for i,r in enumerate(rows):r['candidate_site_um']=[(i%64+.5), (i//64+.5)]
    trees={d:R.tree_count(n,8) for d,n in counts.items()}
    buffers=2*sum(t['buffers'] for t in trees.values())
    cell_area=len(rows)*(.37908+.04374)+buffers*.10206
    loads={c:{d:{p:counts[d]*R.library(c)[2][(R.ASR,p)]['cap_fF']
                  for p in ('CLK','RESETN')} for d in PERIOD} for c in ('ss','ff')}
    numeric={c:buffer_price(c,8,16) for c in ('ss','ff')}
    # Corresponding direct wire cap and reset capacitance separately; do not
    #substitute CLK capacitance for RESETN in the reset collector.
    reset_numeric={}
    for c in ('ss','ff'):
        _,lib,caps=R.library(c)
        cap=8*caps[(R.ASR,'RESETN')]['cap_fF']+.165790*16
        reset_numeric[c]=dict(cap_fF=cap,delay_ps={t:R.envelope(lib[R.BUF],'cell_'+t,cap,5,80) for t in ('rise','fall')},
            slew_ps={t:R.envelope(lib[R.BUF],t+'_transition',cap,5,80) for t in ('rise','fall')})
    ff={}
    for c in ('ss','ff'):
        _,lib,caps=R.library(c)
        # QN requires a real restoring INV; no free logical Q on this cell.
        qcap=caps[(INV,'A')]['cap_fF']+2*.165790
        ff[c]={t:R.envelope(lib[R.ASR],'cell_'+t,qcap,5,80,related='CLK') for t in ('rise','fall')}
    result=dict(schema='qwen-owned-ready-context-r1',status='BLOCKED_SOURCE_EXPORT_AND_PHYSICAL_ADMISSION',
        selected_explicitly=True,default_enabled=False,parent_reset_provider_instantiated=False,
        source_map_admission=False,startup_admitted=False,PnR=False,additional_maps=0,numerical_runs=0,
        selected_map_sha256=R.obj(P.OUT/'model-r1.json')['selected_map_sha256'],
        immutable_local_parent_model_sha256=R.sha(P.OUT/'model-r1.json'),
        peer_commit=PEER,channels=channels,source_allocated_not_mapped_FFs=len(rows),
        readiness_clock_reset_counts_per_rank=counts,readiness_pin_loads_fF=loads,
        tile_successor_counts_unchanged=dict(clock=102352,reset=56683),
        domain_period_ps=PERIOD,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        collector_trees=trees,clock_plus_reset_buffers=buffers,
        FF_plus_restoring_INV_plus_collector_area_um2=cell_area,
        TP4_replicas=4,TP4_additional_cell_area_mm2=4*cell_area/1e6,
        proposed_hub_slot_um=[64,64],hub_slot_fit_conditional=cell_area<4096,
        predicate_logic_and_causal_export_cost_complete=False,
        fixed_service_predicate_input_bits_per_stack=452,
        fixed_predicate_bits_scope='416 queue occupancy + ingress1 + write residence12 + grant1 + live_tags16 + owner_state2 + owner_held1 + route_held1 + enabled1 + fault1',
        existing_FIFO_control_FFs_per_FIFO=26,existing_FIFO_data_FFs='2*WIDTH',
        existing_bridge_FIFO_count=2,existing_bridge_route_FFs='WIDTH+7',
        actual_selected_parent_bridge_instance_count=None,
        existing_service_macro_clocks_per_rank=384,existing_tail_macro_clocks_per_rank=128,
        service_macro_clocks_rank_once=512,KV_cold_calendar_selected_production=False,
        finite_leaf_clock_load_price=numeric,finite_leaf_reset_load_price=reset_numeric,
        finite_leaf_wire_scope='16um TOTAL output wire per8-sink leaf; upper collectors and domain entry routes are not timed by this leaf calculation.',
        complete_readiness_collector_timing_proven=False,
        snapshot_FF_QN_clkq_ps=ff,
        protocol=[
          'Quarantine old owners/debt; inhibit admissions in every source domain; no readiness from live_tags alone.',
          'Issue one source identity.irs_serial snapshot transaction; sequence cannot wrap while any owner, return or debt survives.',
          'Each local release uses its own two FFs; stream release does not release serial/service.',
          'Two local request synchronizers precede a local registered snapshot of sequence plus readiness; predicate includes queues, owner/grant/route, FIFO crossed pointers, causal ledger and tail binding.',
          'Freeze all33 snapshot bits while ACK crosses two stream FFs; wait one additional stream guard edge before registered sample, compare all32 sequence bits.',
          'Join acknowledged samples on the following stream edge; preedge joined_ready enables the next edge only.',
          'Hold full379-bit instruction, x128,192-bit identity and PC through actual IREG consume at launch+1; return ACK crosses two local FFs before snapshot storage reuse.',
          'After startup, use descriptor kv_ok and actual write-drain/window readiness per issue; do not repeat startup drain per instruction.',
          'Any reset or debt reappearance invalidates readiness and requires explicit abort/quarantine; do not silently re-epoch held requests.'],
        clean_two_stage_startup_demand_ps={d:5*p+7*PERIOD['stream'] for d,p in PERIOD.items()},
        latency_scope='Worst edge phase within nominal clean two-stage transfer; no bound on metastability or outstanding drain. Predicate evaluation/source routes and reset recovery/removal remain additional unqualified demands.',
        steady_added_staging_cycles=1,steady_latency_price_ps=PERIOD['stream'],
        steady_stage_scope='Owned parent launch register once per issue, actual IREG already present; no numerical/rate gain claim.',
        readiness_control_corridor_reserved_tracks_demand=6*4+6*33,
        corridor_scope='24 request/ACK/return/valid plus198 held snapshot bits; local hub reservation only, no fit credit against tile64clock/64reset or1048fill.',
        selected_tile_corridor_um=96.768,selected_tile_cell_ceiling_um2=125000,
        PG='Hub rails and clock/reset source collectors require legal PG/pin access and IR/EM; no tile PG timing transfer.',
        actual_source_ready_arrivals_ps=None,actual_release_ack_domain_phases_ps=None,
        field1536_cell_area_plus_one_rank_readiness_lower_bound_mm2=R.obj(P.OUT/'model-r1.json')['field']['tile_cell_plus_field_clock_buffer_area_mm2']+cell_area/1e6,
        whole_parent_cost_complete=False,
        remaining_prerequisites=[
          'Implement enabled source-local predicate exports and causal-debt/assembly bookkeeping; their actual widths and logic cost are not supplied by the software receipt.',
          'Bind actual parent bridge instances/WIDTH/domains and FIFO/route state to the coherent source snapshot; source primitive is not a selected-instance inventory.',
          'Allocate legal hub sites, full per-domain collector routes and PG; extract snapshot data and ACK skew with bundled-data setup60/hold25 and stability through return ACK.',
          'Join actual source root arrivals/local phases, reset pulse/recovery/removal and registered launch timing; existing50..99ps input demand is not a producer timing measurement.',
          'Preserve frozen local reset49SS/77FF failures and387clock/410reset collector crossings; solve before contextual build.',
          'Prove actual instantiated parent provider and binary held379/x128 launch, then one context map for successor realization; no external idealization.'])
    return result,rows


def generate():
    result,rows=price()
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    review=dict(verdict='NO_CONTEXT_BUILD_ADMISSION',local_construction_commit='8df5971a3',
        physical_model_join_sha256=result['immutable_local_parent_model_sha256'],
        Russell_commit=PEER,Euclid_source_contract=json.loads((root/'inputs/ampere_dependency_r1.json').read_text())['euclid_commit'],
        priced_candidate=dict(FFs=result['source_allocated_not_mapped_FFs'],
            domain_FFs=result['readiness_clock_reset_counts_per_rank'],
            collectors=result['clock_plus_reset_buffers'],
            cell_area_lower_bound_um2=result['FF_plus_restoring_INV_plus_collector_area_um2']),
        next_concrete_closure_step='Bind six local snapshot exports to enabled actual stack/owner, serial, KV tail and FIFO state; implement causal-debt counters at allocation/return/ACK events and price the resulting predicate graph before provider RTL.',
        physical_unknowns=result['remaining_prerequisites'],
        frozen_failures_preserved=True,source_owned_provider_connected=False,
        one_context_map_only_after_model_and_source_admission=True)
    for name,obj in [('model-r1.json',result),('register-allocation-r1.json',rows),('admission-review-r1.json',review)]:
        (root/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    pins={str(p):R.sha(p) for p in [Path(__file__).relative_to(R.ROOT),
        Path('tools/uarch_model_qwen_owned_ready.py'),Path('tests/test_qwen_rom_owned_ready_context.py'),
        P.OUT/'model-r1.json',P.OUT/'admission-review-r1.json']}
    for p in sorted((root/'inputs').rglob('*')):
        if p.is_file():pins[str(p.relative_to(R.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (root/'sourcepins-r1.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n')
    artifacts={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.glob('*.json')) if p.name!='artifact-sha256-r1.json'}
    (root/'artifact-sha256-r1.json').write_text(json.dumps(artifacts,indent=2,sort_keys=True)+'\n')
    return result


if __name__=='__main__':print(json.dumps(generate(),indent=2))
