#!/usr/bin/env python3
"""Physical-owner reply to Russell's full-width MTP accept request.

A requested rectangle is not an allocation. This audit prices the source scalar
branch correction and names local clock sinks and existing prospective CDC
edges without editing the producer or adopting an unplaced geometry.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/ds_mtp_serial_spine_context_20261003'


def inputs():
    rows=json.loads((BASE/'inputs/origins.json').read_text())
    for r in rows:
        p=BASE/'inputs'/r['copy']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('Pinned input drift: '+r['copy'])
    return rows


def scalar_state(K,IW,VW=32):
    """Literal ot_hdc_select registers, including full insertion/pass/emission."""
    if type(K) is not int or K<2 or type(IW) is not int or IW<1:
        raise ValueError('Full selector shape required')
    KW=K.bit_length(); PW=VW+IW+2
    sections=dict(busy=1,input=2+VW+IW+KW,key=PW,
        wave_threshold=2*K,stored=K*PW,pass_entries=(K-1)*PW,
        bank=K*(IW+2),emission_control=KW+6,
        output=IW+3)
    return dict(sections=sections,total=sum(sections.values()))


def tree(sinks,fanout=8):
    """Named prospective buffer groups; no equal-depth skew credit."""
    levels=[]; count=sinks; level=0
    while count>1:
        groups=[]
        for i in range(math.ceil(count/fanout)):
            groups.append(dict(name=f'L{level}_B{i}',first=i*fanout,
                               stop=min((i+1)*fanout,count)))
        levels.append(groups);count=len(groups);level+=1
    return levels


def fifo_state(W,DEPTH=4,HOLD=2):
    aw=(DEPTH-1).bit_length();cw=HOLD.bit_length()
    # mem+shadow, wp/rp+their samples, both states+samples, counters and ok.
    return 2*DEPTH*W+4*(aw+1)+8+2*cw+2


def build():
    rows=inputs();source=lambda name:(BASE/'inputs'/name).read_text()
    a=json.loads(source('accept_model.json'));prices=json.loads(source('cell_prices.json'))['facts']
    xu=source('xu_adapt.sv');core=source('core.sv')
    for text,anchor in [(xu,'.IW(16)'),(xu,'X_SEL != 0 && i_bf16'),(xu,'s_idx[15:0]'),
                        (xu,'vw_data <= {16\'d0, so_idx}'),(core,'xu_bf16 <= (`F(XU_D_N) != 0)'),
                        (core,'TOPK = FULL_SHAPE ? 512 : 16')]:
        if anchor not in text: raise ValueError('Source branch anchor absent: '+anchor)
    if source('tile.sv').count(') u_core (')!=1 or source('die.sv').count(') u_tile (')!=1:
        raise ValueError('Actual die/tile core census changed')
    old,new=scalar_state(512,16),scalar_state(512,21)
    ff=prices['DFFHQNx1_ASAP7_75t_R'];asr=prices['DFFASRHQNx1_ASAP7_75t_R'];buf=prices['BUFx4_ASAP7_75t_R']
    delta=new['total']-old['total'];levels=tree(1944)
    nodes=sum(map(len,levels))
    parent=json.loads(source('split_parent_model.json'))
    names=['XU_fast_subtree_completion','ME_attention_index_completion']
    cdc=[]
    for name in names:
        f=next(e for e in parent['prospective_edges'] if e['name']==name)
        r=next(e for e in parent['prospective_edges'] if e['name']==name+'_reverse_receipt')
        bits=fifo_state(f['packet_bits'])+fifo_state(r['packet_bits'])
        cdc.append(dict(name=name,source_bits=f['source_bits'],packet_bits=f['packet_bits'],
            reverse_packet_bits=r['packet_bits'],shared_component='ot_ratio_cdc_fifo',DEPTH=4,HOLD=2,
            full_state_bits=bits,meaning='Full21bit scalar SELECT index or ME AMAX index with origin; scalar TOPK result must not be labeled BF16',
            source_selection='Prospective same-die related1.2->0.9GHz completion; local TOKX/AMAX held queries consume it at0.9GHz',
            extra_separate_TOKX_FIFO=0,extra_separate_AMAX_FIFO=0,
            charge='Named replacement of prior prospective completion/receipt placeholder, not additional independent path; no area credit until Maxwell containment joins',
            realized_in_parent=False))
    cdc_bits=sum(e['full_state_bits'] for e in cdc)
    area=a['gross_at_50pct_util_mm2'];width,height=128,184.14
    return dict(schema='DS_MTP_SERIAL_SPINE_PHYSICAL_REPLY_R1',source_pins=rows,
      owner_join=dict(Russell='01a0fd4d: full scalar width/provider enrollment + compiler TOPK512',Maxwell='Selected core-to-shard ownership and disjoint slot containment/clock/reset/PG union',Claude='Shared related-clock FIFO; no competing component edits'),
      actual_source=dict(X_SEL1_static_draft_path='S_SEL FP32: XU_D_N absent =>i_bf16false',current_scalar_IW=16,required_scalar_IW=21,NW=21,TOPK=512,
        missing_widened_points=['u_sel.IW and in_idx','so_idx wire','sel_first adapter/core net','vw_data full21bit index zeroextension to32'],
        zeroextension_rule='Extend full21bit result to32; never extend alreadytruncated16. Do not change BF16 discriminator to force unrelated branch.',
        finite_witnesses=[dict(index=i,retained16=i&65535,required21=i) for i in [65535,65536,129279]],
        old_scalar_state=old,new_scalar_state=new,additional_scalar_FF_bits=delta,
        arithmetic='FP32 value ordering, lower-index ties and original insertion/emission order retained',
        full_selector_tail_edges_after_last=1026,full_selector_busy_edges_after_last=1537,
        tail_scope='RetainedK512 source even runtimek1; not leafTOKX/AMAXII2 or measured timing'),
      replicas=dict(per_selected_source_die=1,per_tile=1,per_actual_core=1,
        source_hierarchy='u_tile.u_core.g_accept plus XU scalar provider; N_TP link loops are not core replicas',
        new_enrolled_hardware_instances=0,
        physical_P_AR2_owner='No inferred second core for row-split shard; Maxwell must bind this one namespace to selected physical home',
        fleet_rule='Multiply only actual enrolled core instance census; no96rank/32SM/product stage assumption'),
      request=dict(name='MTP_ACCEPT_SERIAL_SPINE_PER_ACTUAL_CORE',width_um=width,height_um=height,
        gross_cell_body_um2=a['gross_cell_body_um2'],gross_50pct_mm2=area,
        rectangle_mm2=width*height/1e6,unused_geometric_um2=width*height-area*1e6,
        excludes_added_scalar_provider=True,
        actual_reserved_rectangle=None,physical_fit=False,
        requirement='Parent must add disjoint rectangle to selected fixed candidate union, with literal PG/via/clock exclusions; no corridor/site borrowing'),
      scalar_provider_debit=dict(added_FF_bits=delta,
        FF_body_floor_mm2=delta*ff['SS']['area_um2']/1e6,
        at50pct_FF_floor_mm2=2*delta*ff['SS']['area_um2']/1e6,
        FF_clock_pin_SS_fF=delta*ff['SS']['pins']['CLK']['cap_fF'],
        FF_clock_pin_FF_fF=delta*ff['FF']['pins']['CLK']['cap_fF'],
        added_compare_bits=5*512+5*511,
        area_scope='Index-state floor only: wider compare and insertion/pass/sort multiplexers + hold/reset/clock/wires require separate realization. sel_first full21 gross already in caller ledger; no duplicate5-bit charge.',
        matched_existing_scalar_debit=None,existing_slot_containment_proven=False),
      local_clock=dict(GHz=0.9,period_ps=1000/0.9,SS_setup_ps=60,FF_hold_ps=25,
        protected_FF_sinks=1944,clock_pin_SS_fF=1944*asr['SS']['pins']['CLK']['cap_fF'],
        clock_pin_FF_fF=1944*asr['FF']['pins']['CLK']['cap_fF'],
        prospective_CLK_tree=levels,prospective_RESETN_tree=levels,
        buffers_per_tree=nodes,clock_plus_reset_buffers=2*nodes,
        already_in_accept_body=True,new_clock_buffer_area_added_again=0,
        FF_eight_sink_CLK_pin_fF=8*asr['FF']['pins']['CLK']['cap_fF'],
        FF_eight_sink_RESETN_pin_fF=8*asr['FF']['pins']['RESETN']['cap_fF'],
        root_input_load_SS_fF=buf['SS']['pins']['A']['cap_fF'],root_input_load_FF_fF=buf['FF']['pins']['A']['cap_fF'],
        SETN='Inactive constant tied locally; actual tie instance/pin/PG union must be mapped, not another asserted global reset wire',
        reset='Coordinated truthful allcopies drain then local reset release; no cold reset or FIFO flush may erase accepted ownership debt.',
        actual_driver_arrival_wire_skew=None,loaded_SS_FF=False,equal_depth_skew_credit=False),
      channels=dict(signal_union=636,ports=a['ports'],bytes_per_edge=a['port_bytes_per_edge'],
        nominal_TOKX_AMAX_II=2,half_rate_each_max_payload_bytes_s=6.125*0.9e9/2,
        track_pitch_um=0.048,unexcluded_width_floor_um=636*0.048,
        actual_legal_capacity=None,excluded='PG rails, vias, clock/reset crossings, pin escapes and existing field/service routes must subtract literal resources',
        sum_is_not_single_bus_fit=True,admissible_routes=False),
      CDC=dict(edges=cdc,full_state_bits=cdc_bits,
        state_body_floor_mm2=cdc_bits*ff['SS']['area_um2']/1e6,
        clock_buffer_floor_mm2=math.ceil(cdc_bits/8)*buf['SS']['area_um2']/1e6,
        reset_epoch='Source private25bit key plus bridgeepoch32/txn16; reverse acceptance not result consumption or provider release. Flush cancels traffic, cannot certify truthful allcopiesfence.',
        origin='Capture25bit leaf origin at actual producer command acceptance and match bridgeepoch/txn on completion; never relabel returned index with current core slot. Russell owns installed stamp/producer wiring.',
        phase_exceptions=False,component_physical_or_formal_credit=False,
        hierarchy='Retained caller is singleclk; actual related-clock split is prospective source-selected, not proven by singleclock test'),
      latency=dict(accept_protected_min_edges=3,added_min_serial_edges=2,added_min_serial_ns=2/0.9,
        source_scalar_input_and_tail_separate=True,
        blocked_provider_or_fence_maximum_ns=None,whole_MTP_or_AR_gain=None,
        no_unmeasured_protection_cone_fit=True),
      target_applicability=dict(DS_ROM='Actual source width correction and one selected serial-core physical request',DS_HBM='Same private leaf only if actual caller enrolled; GPU SM replication not inferred',Qwen_ROM='No DS MTP topology/area transfer',Qwen_HBM='No DS source caller transfer'),
      remaining_exact_gates=['Russell freeze actual fullIW21 scalar/select/writeback source and enumerate added comparator/mux cells', 'Maxwell select one actual core/shard namespace and allocate this rectangle plus scalar growth in disjoint parent union', 'Bind native pins/rail/via exclusions and retained global root/reset release to these named sinks', 'Loaded complete mutable-protection/query/prefix/capture cones SS60/FF25, stages priced before adding edges', 'Claude completion/reverse FIFO ports + reset cancellation versus owner truthful drain receipt'],
      admission=dict(request_priced_for_review=True,slot_reserved=False,component_RTL_authorized_here=False,physical_G0=False,whole_token=False),
      guarded_physical_policy='EveryNEW physical launch uses tools/run_abi3_physical_aligned_guarded.py --macro-track-gate and ot_mts::place/assert with strict actualinstancecensus; livepinnedjobs unchanged',
      no_new_PVE2_PVE3_jobs=True,no_new_RTL_or_PnR=True)

if __name__=='__main__':
    out=BASE/'model.json';out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n');print(out)
