#!/usr/bin/env python3
"""Current a969 MTP physical-owner reply; preserves r1 as history.
No source, engine or physical launch changes. Unreserved requests fail closed.
"""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/ds_mtp_serial_spine_context_r2_20261003'


def checked():
    rows=json.loads((BASE/'inputs/origins.json').read_text())
    for r in rows:
        p=BASE/'inputs'/r['copy']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('Pinned source drift: '+r['copy'])
    return rows


def tree(sinks):
    out=[];level=0
    while sinks>1:
        out.append([dict(name=f'L{level}_B{i}',first=8*i,stop=min(8*i+8,sinks)) for i in range(math.ceil(sinks/8))])
        sinks=len(out[-1]);level+=1
    return out


def build():
    pins=checked();read=lambda n:(BASE/'inputs'/n).read_text()
    e=json.loads(read('enrollment.json'));p=json.loads(read('cell_prices.json'))['facts']
    prior=json.loads(read('prior_r1_reply.json'));parent=json.loads(read('split_parent_model.json'))
    core,xu=read('core.sv'),read('xu_adapt.sv')
    for s,a in [(core,'xu_bf16 <= (`F(XU_D_N) != 0)'),(xu,'X_SEL != 0 && i_bf16'),(xu,'.IW(16)'),(core,'TOPK = FULL_SHAPE ? 512 : 16')]:
        if a not in s: raise ValueError('Actual scalar branch changed: '+a)
    if read('tile.sv').count(') u_core (')!=1 or read('die.sv').count(') u_tile (')!=1:
        raise ValueError('Actual source core replica census changed')
    comp=e['kernel_composition'];sinks=comp['new_protected'];levels=tree(sinks)
    nodes=sum(map(len,levels));asr=p['DFFASRHQNx1_ASAP7_75t_R'];hq=p['DFFHQNx1_ASAP7_75t_R'];buf=p['BUFx4_ASAP7_75t_R']
    width,height=128,191.70;gross=comp['gross_50pct_mm2']
    scalar=e['scalar_repair'];delta=scalar['raw_FF_width_delta']
    cdc=[]
    for name in ['XU_fast_subtree_completion','ME_attention_index_completion']:
        f=next(x for x in parent['prospective_edges'] if x['name']==name)
        r=next(x for x in parent['prospective_edges'] if x['name']==name+'_reverse_receipt')
        # Native shared FIFO W,DEPTH4,HOLD2: mem+shadow8W +26control FF.
        cdc.append(dict(name=name,W=f['packet_bits'],reverse_W=r['packet_bits'],DEPTH=4,HOLD=2,
            full_state_bits=8*(f['packet_bits']+r['packet_bits'])+52,
            source_namespace='This concrete private core; accepted-command origin retained by corrected102raw caller',
            source_domain='stream1.2GHz proposed subtree',destination_domain='serial0.9GHz core and leaf',
            source_selected_but_not_installed=True,
            extra_TOKX_AMAX_FIFO_count=0,
            source_pin='inputs/shared_fifo.sv: ot_ratio_cdc_fifo',
            area_charge='Named completion/reverse bridge replacement, no independent new leaf FIFO and no old placeholder removal credit until instance containment is matched'))
    bits=sum(x['full_state_bits'] for x in cdc)
    return dict(schema='DS_MTP_SERIAL_SPINE_PHYSICAL_REPLY_R2',source_pins=pins,
        authoritative_enrollment='a9691644a',mandatory_correctness=True,one_percent_performance_filter_applies=False,
        supersedes=dict(prior_request='128x184.14um/1944protected/73callerraw',prior_reply_commit='69c556aae',history='inputs/prior_r1_reply.json; unchanged prior records'),
        kernel=dict(NSLOT=8,NW=21,leaf_raw=614,caller_raw=102,total_raw=716,
            caller_protected_words=4,total_protected_words=28,protected_FF_sinks=sinks,
            raw_state_delta=29,protected_state_delta=72,
            replacement='102raw/4protected caller records replaces73raw/3records, leaf614raw retained once',
            default_enable=False,source_NSLOT_default=e['actual_runtime']['core_default_NSLOT'],
            source_installed=False,MACs_per_cycle=0),
        scalar_source=dict(branch=e['source_selected_producer'],K=512,VW=32,ORDER=1,old_IW=16,new_IW=21,
            raw_before=scalar['raw_before'],raw_after=scalar['raw_after'],width_FF_delta=delta,
            width_only_body_um2=scalar['width_only_body_um2'],width_only_50pct_mm2=scalar['width_only_50pct_mm2'],
            width_only_cell_counts=scalar['width_only_cell_counts'],
            price_scope='Use owner complete width-only construction0.03135116988, not Arch earlierFF-only0.002242404mm2. Full mutable selector protection and loaded stage costs remain additional.',
            extra_selector_replicas=0,prospective_added_edges=0,zero_added_edges_measured=False,
            source_input_bytes_per_edge=4,source_writeback_bytes_per_edge=4,
            source_last_input_to_result_edges=1026,
            input_clock='Actual retained source singleclk; selected split subtree is prospective1.2GHz and requires connected CDC',
            clamp_or_BF16_substitution=False,
            full21_index_before_32bit_writeback=True),
        requested_slot=dict(name='MTP_ACCEPT_SERIAL_SPINE_PER_ACTUAL_CORE',width_um=width,height_um=height,
            body_um2=comp['gross_cell_body_um2'],gross50pct_mm2=gross,rectangle_mm2=width*height/1e6,
            spare_geometric_um2=width*height-gross*1e6,
            actual_reserved_rectangle=None,fit_qualified=False,
            scalar_width_only_added_separate_mm2=scalar['width_only_50pct_mm2'],
            leaf_plus_scalar_width_only_gross50pct_mm2=gross+scalar['width_only_50pct_mm2'],
            credits_for_old_state_or_slot_embedding=0,
            corridor_or_macro_frame_borrowing=False,
            physical_reply='NOT_RESERVED: new kernel request and mandatory scalar provider debit require named disjoint selected-home instance containment; sourcekernel enrollment not a physical allocation'),
        replica_census=dict(one_kernel_per_actual_enrolled_core=1,actual_cores_per_source_die_wrapper=1,
            hierarchy='die.u_tile.u_core; scalar u_xu.u_sel remains one originalK512 provider',
            enrolled_successor_instances=0,
            N_TP_is_link_replication_not_core_count=True,
            PAR2_physical_binding='Maxwell assigns one source core namespace and resolves which selected shard hosts it; no implicit second core, rankfleet or perstage replication',
            actual_fleet_count_unproven=True),
        local_clock_reset=dict(GHz=0.9,period_ps=1000/0.9,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            protected_sinks=sinks,
            SS_CLK_pin_fF=sinks*asr['SS']['pins']['CLK']['cap_fF'],FF_CLK_pin_fF=sinks*asr['FF']['pins']['CLK']['cap_fF'],
            CLK_levels=levels,RESETN_levels=levels,buffer_counts=[len(x) for x in levels],
            buffers_per_tree=nodes,total_clock_reset_buffers=2*nodes,
            difference_to_old558_buffers=2*nodes-558,
            contained_in_owner_body=True,add_clock_tree_charge_again=0,
            FF_CLK_eight_sink_fF=8*asr['FF']['pins']['CLK']['cap_fF'],
            FF_RESETN_eight_sink_fF=8*asr['FF']['pins']['RESETN']['cap_fF'],
            root_A_SS_fF=buf['SS']['pins']['A']['cap_fF'],root_A_FF_fF=buf['FF']['pins']['A']['cap_fF'],
            scalar_added_CLK_SS_fF=delta*hq['SS']['pins']['CLK']['cap_fF'],
            scalar_added_CLK_FF_fF=delta*hq['FF']['pins']['CLK']['cap_fF'],
            SETN='Inactive perrecord local ties; literal tie PG/native pin union mandatory, not a global asserted reset',
            load_scope='Kernel2016sinks plus scalar7690width sinks plus selected bridge sinks; existing completeK512 clock never removed or reclassified as only2016sinks',
            native_slew_route_skew_not_yet_bound=True,equal_depth_skew_credit=False,loaded_SSFF=False,
            root_reset_release='Stop new admission, preserve accepted holders until positive allcopies provider/result/forward/return/reverse/stamp fence; synchronously release domains. FIFO reset cancels, never certifies retirement.'),
        signal_channels=dict(leaf_signals=636,producer_cut_instances=2,producer_signals_each=52,
            producer_fields=dict(token=21,original_lease=25,slot=3,valid=1,ready=1,begin_finish_discriminator=1),
            leaf_floor_um_at48nm=30.528,each_producer_floor_um_at48nm=2.496,
            if_all_share_one_cut_signals=740,if_all_share_one_cut_floor_um_at48nm=35.52,
            sum_not_selected_single_corridor=True,
            independent_boundary_names=['serial_core_leaf','XU_origin_terminal_holder','ME_origin_terminal_holder'],
            producer_holder_occupancy_each=1,leaf_nominal_TOKX_AMAX_II_edges=2,
            no_full_selector_II2_claim=True,
            leaf_bytes_per_edge=json.loads(read('prior_r1_reply.json'))['channels']['bytes_per_edge'],
            source_scalar_read_write_bytes_per_edge=4,
            legal_tracks_after_PG_via_clock=None,PG_or_corridor_free_capacity_credit=0),
        prospective_CDC=dict(edges=cdc,state_bits=bits,state_cell_floor_mm2=bits*hq['SS']['area_um2']/1e6,
            eight_sink_buffer_floor_mm2=math.ceil(bits/8)*buf['SS']['area_um2']/1e6,
            held52signals_are_origin_and_finish_cuts_not_automatic_FIFO=True,
            phase_or_multicycle_exceptions=False,
            command_origin='Accepted producer command captures actual pos/gen/slot before launch; bridgeepoch/txn must match on return, no latest c_slot relabel',
            nominal_latency_not_stalled_bound=True,
            no_shared_FIFO_RTL_edits=True,hardware_closure=False),
        latency=dict(protected_accept_min_edges=3,delta_from_old_min_edges=2,delta_ns=2/0.9,
            producer_finish_to_first_leaf_query_min_edges=1,
            actual_scalar_scan_and_tail_and_fence_and_CDC_separate=True,
            full_token_or_MTP_rate_claim=None,
            additional_checked_pipeline_or_capture_edge='Must add actual record/codecs/clock/area/latency in model before newRTL; no free edge or clockrelaxation'),
        exact_next_dependencies=[
            dict(owner='Russell01a0fd4d',action='Freeze currentNSLOT8/NW21 defaultoff kernel + protected origin holder source and fullK512 scalar width/protection realization, with actual begin/finish/stamp mapping'),
            dict(owner='Maxwell',action='Return one selected actual core home/shard identifier and disjoint128x191.70 rectangle plus scalar0.03135116988width-only debit; actualfleet replica census and oldmatched containment required'),
            dict(owner='Archimedes+Maxwell',action='Join these2016+7690 and bridge native sink pins to retained fullparentCLK/reset tree, rail/via exclusions and separate636/52/52channel routes'),
            dict(owner='Claude',action='Match fullcompletion/reverse bridge packet ports and related-clock reset/epoch cancellation to truthful ownerdrain; sharedFIFO ownership unchanged'),
            dict(owner='Dewey/Popper',action='Supply actual positive allcopies fence/parallelME lane identity and finite reuse/delivery contract; localtake is not KVrelease')],
        four_target_applicability=dict(DS_ROM='Current source mandatorywidth repair plus proposed privateleafslot',DS_HBM='Samekernel only actualcaller enrollment; no assumed32SM orrankcount',Qwen_ROM='No DS MTP caller/clock/area transfer',Qwen_HBM='No DS source topology transfer'),
        admission=dict(source_model_reply_ready=True,slot_reserved=False,new_RTL_or_build_authorized_here=False,physical_G0=False,whole_MTP=False),
        physical_launch_policy='AllNEWphysical launches tools/run_abi3_physical_aligned_guarded.py --macro-track-gate with ot_mts::place/assert and strictactualinstancecensus; existingpinsjobs unchanged',
        original_sources_unchanged=True,new_jobs=0,global_Z3_unchanged=True,no_new_PVE2_PVE3_jobs=True)

if __name__=='__main__':
    p=BASE/'model.json';p.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n');print(p)
