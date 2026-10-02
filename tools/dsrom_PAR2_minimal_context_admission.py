#!/usr/bin/env python3
"""Minimal positive model for independent existing decoder characterization.
Does not edit RTL/uarch, launch tools, or adopt provisional timing or floorplans.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_PAR2_minimal_context_admission_20261002'

def positions(k):
    out=[];n=1
    while len(out)<k:
        if n&(n-1):out.append(n)
        n+=1
    return out

def decoder(k,replicas,allowance):
    r=9;n=k+r+1;p=positions(k);cover=[sum(bool(x&(1<<b)) for x in p) for b in range(r)]
    return dict(K=k,R=r,N=n,replicas_per_shard1_die=replicas,
        input_bits=n,output_bits=k+2,packing='cw={overall,check[8:0],data[K-1:0]}',
        covered_bits=cover,syndrome_XOR2_nodes=sum(cover),overall_XOR2_nodes=n-1,
        correction_comparators=k,comparator_width=9,correction_XOR_bits=k,
        source_is_combinational=True,
        assigned_stream_latency_cycles=2,assigned_II_cycles=1,
        latency_and_II_status='POSITIVE_MODEL_BUDGET_NOT_MEASURED_OR_RETIMER_IMPLEMENTED',
        area_existing_construction_allowance_mm2=allowance,
        area_per_replica_construction_um2=allowance*1e6/replicas,
        characterize_existing_cone_admitted=True,new_RTL_or_hardening_admitted=False,
        own_minimum_characterization_gate='Freeze existing module SHA/K/N/R; all output and corrected/uncorrectable cones active; source SS/FF libraries and60ps/25ps uncertainty; report delay, area, fanout and chosen output loads. No parent calendar needed.',
        own_minimum_hardening_gate='Measured cone delay and actual pipeline cuts/capture FF validate the assigned positive latency/II, enabled valid/header alignment and SS setup/FF hold in declared slot. Refuse until these own interfaces exist.',
        other_projects_are_not_characterization_gates=True)

def build():
    c=json.loads((OUT/'inputs/context.json').read_text());p=json.loads((OUT/'inputs/physical.json').read_text())
    b=(OUT/'inputs/decoder.sv').read_bytes()
    if hashlib.sha256(b).hexdigest()!=c['source_decoder']['sha256']:raise ValueError('decoder source changed')
    area=p['area'];named=area['named_logic_allowance_mm2']
    dec=[decoder(256,412,named['sidecar_leaf_SECDED256_check10']),decoder(272,256,named['main_pair_SECDED272_check10'])]
    for d in dec:
        src=c['source_decoder']['replica_cones'][str(d['K'])]
        if d['syndrome_XOR2_nodes']!=src['independent_syndrome_XOR2_nodes'] or d['covered_bits']!=src['covered_data_bits_per_check']:raise ValueError('source cone demand mismatch')
    distance=c['routing_incidence']['pin_to_consumer_frame_center_max_Manhattan_um']
    # Explicit retained uarch wire-fit counterfactual; actual per-edge route owner
    # replaces this with lengths, pins and track cuts, not a new rate assumption.
    wire_fit=json.loads((OUT/'inputs/wire_fit.json').read_text())
    period=1000/1.2;wire_per_um=wire_fit['WIRE_PS_PER_UM'];flop_setup_skew=wire_fit['WIRE_OVERHEAD_PS'];uncertainty=60
    endpoint_stages=max(1,math.ceil(distance*wire_per_um/(period-uncertainty-flop_setup_skew)))
    state=[dict(block='enabled_raw_capture',replicas=412,bits=274+58,cycles=2,II=1),
           dict(block='protected_sidecar_decode_output',replicas=412,bits=256+2+58,cycles=2,II=1),
           dict(block='gather_reply_capture',replicas=128,bits=16+58,cycles=endpoint_stages,II=1),
           dict(block='main_codeword_assembly',replicas=256,bits=282+58,cycles=1,II=1),
           dict(block='main_corrected_output',replicas=256,bits=272+2+58,cycles=2,II=1)]
    total_bits=sum(s['replicas']*s['bits']*s['cycles'] for s in state)
    overlay=total_bits*area['FF50_proxy_mm2_per_bit']
    paths=dict(raw_capture=2,sidecar_decode=2,gather_reply=endpoint_stages,main_assembly=1,main_decode=2)
    first=sum(paths.values());leaf_debt=paths['raw_capture']+paths['sidecar_decode']+paths['gather_reply']
    # Holds one leaf read debt through protected-word delivery. No earlier credit
    # release or overlap credit; real provider may separately bind transfer slots.
    batch64=64*leaf_debt+paths['main_assembly']+paths['main_decode']
    return dict(schema='opentallas.dsrom.PAR2.minimal-positive-context.v1',
        candidate=c['candidate'],source_pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((OUT/'inputs').iterdir())},
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        target=dict(stream_GHz=1.2,serial_GHz=.9,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
        decoder_entries=dec,
        capture_header_entries=state,
        capture_header_bit_contract=dict(stage=6,rank=2,shard=1,phase=10,opseq=13,era=1,provider_index=7,MB=1,parity=1,physical_row=12,corrected_uncorrectable=2,word_kind=1,valid=1,total=58,
            external_owner_nonce_and_full_generation_retained_by_existing24_ledger=True,
            no_second_native_owner_ledger=True),
        capture_own_gate='Accepted CE/address identity latched at actual macro launch; macro output holds when idle, valid/header cannot advance without accepted read. Enable/control, FFsetup/hold and pin collar measured independently of full-token calendar.',
        endpoint_entry=dict(replica_reply_lanes=128,data_bits_per_lane=16,peak_data_bits_per_stream_cycle=2048,
            proposed_header_bits_per_lane=58,full_reply_bits_per_stream_cycle=128*(16+58),
            representative_cut_with_proposed_headers_bits=33*(16+58),
            routing_track_capacity_measured=False,
            own_minimum_characterization_gate='Freeze retained endpoint coordinates and each declared data/header lane; characterize loaded paths and directional cuts. Report OBS/PG exclusions and FF/clock cost; bandwidth is not inferred from bus width.',
            own_minimum_hardening_gate='Accepted-transfer queue/credit and header alignment, actual endpoints/directional available tracks, slot/CTS/SSFF and measured pipeline/II bound before full tile.',
            private_leaf_address_enable_bits=412*13,leaf_raw_return_bits=412*274,
            representative_cut_bits=c['routing_incidence']['representative_vertical_reply_cut_peak']['reply_bits_if_fully_parallel'],
            max_source_pin_to_consumer_center_Manhattan_um=distance,
            modeled_reply_pipeline_cycles=endpoint_stages,
            wire_fit_ps_per_um=wire_per_um,per_segment_flop_setup_skew_ps=flop_setup_skew,
            estimated_stage_count_is_conservative_policy_not_routed_lower_bound=True,
            actual_per_call_endpoint_pins_lengths_tracks_and_link_resources_required_for_tile=True),
        area=dict(current_physical_construction_screen_mm2=area['with_existing_clearances_screen_mm2'],
            existing_decoder_arbitration_capture_allowance_not_removed=True,
            prospective_fullwidth_reference_register_bits=total_bits,each_positive_stage_fullwidth_charged=True,
            no_containment_overlay_FF50_mm2=overlay,
            conservative_screen_with_all_pipeline_overlay_mm2=area['with_existing_clearances_screen_mm2']+overlay,
            remaining_for_extra_clock_control_PG_or_endpoint_exclusions_mm2=858-area['with_existing_clearances_screen_mm2']-overlay,
            overlay_is_conservative_may_double_charge_existing240400_state_until_disjoint_map=True,
            new_macro_instances=0,physical_fit_proven=False),
        composed_latency=dict(per_dependency_path_cycles=paths,first_good_parity_to_arithmetic_cycle_budget=first,
            one_leaf_read_debt_credit=1,leaf_debt_held_cycles_budget=leaf_debt,
            source_first128seat_batch_conflict_rounds=64,
            serialized64round_budget_cycles=batch64,
            status='EXPLICIT_POSITIVE_PROVISIONAL_NO_MEASURED_SOURCE_ACCEPTANCE_OR_DEADLINE',
            no_first_batch64_vs_wholephase400_conflation=True,
            actual_Nash_request_profile_replaces_counterfactual_rounds_and_credit_release=True,
            original_source_deadline_unbound=True,no_token_loss_proven=False),
        source_stream_join_contract=dict(offered_word_bits=48,offered_cadence_cycles=8,
            config_source_last_capture_edge=26,config_source_safe_GO_edge=27,
            completion='rows_left == 0 && !sm_run && !ld_run',
            offered_indices_are_not_accepted_cycles=True,
            current_parent_generator='/tmp/opentallas-dsrom-source-stream-events-20261002/tools/dsrom_source_stream_events.py',
            pending_parent_frozen_event_record=True,
            no_acceptance_or_prefetch_overlap_credit_from_static_offered_words=True),
        independent_work=dict(Archimedes='Characterize existing completeK256/K272cones now at pinned source/SSFF/declaredloads; update these entries with measured cost. No wait for full-token calendars.',
            Nash='Actual accepted local-parity request/profile, ordered capture and owner terminal/generation; no allocator or ownership redesign.',
            Epicurus='Actual LAT8 mainword/control arrival and finite batch cadence.',
            parent='Actual cfg/activation/root accepted edges, source-call deadlines and exposed dependence.'),
        own_fulltile_or_die_PR_gates=['Native CE/address/ready/backpressure or prelaunch credit admission for nonstallable field',
            'Exact mainword272 plus2inline/8sidecar check order adapter and authenticated good/corrected/poison terminal',
            'Accepted cfg72/ECC input fence, activation beats, root108 capture and ordered retire',
            'Source-matched decoder/capture/header placement, per-edge endpoint lanes/cuts/OBS/PG/CTS and clock domains',
            'Measured SSsetup/FFhold and latency/II for complete connected local path'],
        fulltoken_calibration_is_rate_gate_not_existing_decoder_characterization_gate=True,
        existing_decoder_characterization_admitted=True,fulltile_or_die_PR_admitted=False,
        new_RTL_or_remote_job_launched=False,old_failed_TC_and_S58_records_unchanged=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh evidence path required')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
