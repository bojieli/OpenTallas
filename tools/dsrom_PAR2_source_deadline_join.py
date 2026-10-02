#!/usr/bin/env python3
"""Actual relative PP1 edges and exact offered-prefix inequalities, no fake CE."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_PAR2_source_deadline_join_20261002'

def main_callback(event):
    """Consumes observed preedge source issue/address; never invents acceptance."""
    if event.get('source_issue') is not True or event.get('PP')!=1:raise ValueError('actual PP1 source issue required')
    n=event.get('accepted_gclk_edge')
    if type(n) is not int or n<0:raise ValueError('actual accepted gated edge required')
    if event.get('lane_valid') is not True:raise ValueError('source metadata lane predicate required')
    if not event.get('source_event_receipt') or not event.get('identity'):raise ValueError('source accepted event/owner identity required')
    return dict(identity=event['identity'],source_event_receipt=event['source_event_receipt'],
        main_accepted_gclk_edge=n,raw_capture_gclk_edge=n+2,original_lane_consumption_gclk_edge=n+3,
        two_main_terminals_required=True,absolute_stream_mapping_required=True,
        callback_is_relative_source_semantics_not_measured_child_acceptance=True)

def prefix_lead(distinct,deadline_edge,II,terminal_latency):
    if any(type(v) is not int for v in (distinct,deadline_edge,II,terminal_latency)) or distinct<1 or deadline_edge<0 or II<1 or terminal_latency<1:raise ValueError('positive finite service')
    # Reads start -P, -P+II,...; last terminal must be <=deadline_edge.
    return max(0,(distinct-1)*II+terminal_latency-deadline_edge)

def exposed(callback,sidecar_visible,main_clean_visible):
    if type(sidecar_visible) is not int or type(main_clean_visible) is not int:raise ValueError('authenticated visible edges required')
    # Registered terminal visibility is post-NBA. The original lane samples
    # preedge values, so a same-edge registered terminal is too late.
    return max(0,max(sidecar_visible,main_clean_visible)+1-callback['original_lane_consumption_gclk_edge'])

def build():
    s=(OUT/'inputs/element.sv').read_text();p=json.loads((OUT/'inputs/parity_profile.json').read_text());t=json.loads((OUT/'inputs/clean_terminal.json').read_text())
    for clause in ['wire issue = w_run && f_cnt != 0 && !hazard && !pp_block','i1_v <= issue; i2x_v <= i1_v;','i3_v <= i2x_v;','if (i2x_v && !i2x_bk) cap0 <= rd0;','if (i2x_v && i2x_bk) cap1 <= rd1;','assign i2_v = i3_v;','.ce_in(issue && !a_ctr[0])','.ce_in(issue && a_ctr[0])','.v(i2_v && i2_t[2])','.v(i2_v && i2_t[1])']:
        if clause not in s:raise ValueError('PP1 source changed '+clause)
    cases=[]
    for case in p['representative_cases']:
        groups=case.get('parent_offered_cadence',{}).get('groups',[])
        if not groups:continue
        # No claim these groups are accepted/consumer clocks.
        W=max(max(g['source_offered_indices']) for g in groups)+1
        N=max(x['unique_rows'] for x in case['exact_leaf_distinct_rows'])
        cases.append(dict(alias=case['alias'],distinct_words_per_busy_leaf=N,offered_positions=W,
            ideal_II1_latency1_prefix_lead=prefix_lead(N,W,1,1),
            full_phase_inequality=f'P >= max(0,({N}-1)*I_leaf + L_terminal - {W})',
            first_group=dict(words=groups[0]['max_sameleaf_distinct_rows'],window=groups[0]['offered_interval_words'],
                ideal_II1_latency1_prefix_lead=prefix_lead(groups[0]['max_sameleaf_distinct_rows'],groups[0]['offered_interval_words'],1,1)),
            existing_leaf_capture_slots=1,existing_global_raw_slots=412,existing_global_main_paired_slots=128,
            one_credit_held_service_inequality='I_leaf >= max(port_II, accepted_to_safe_leaf_release); if output has no reserved capture, add its backpressure. No clean II1 inferred.',
            lead_time_is_not_cache_word_capacity=True,
            resident_cache_requires_perword_firstready_lastconsumer_intervals=True,
            no_absolute_accepted_edges_or_deadlines_inferred=True))
    measure=json.loads((OUT/'inputs/clean_checker_measurement.json').read_text())
    if measure['status']!='MEASURED_CHECKER_ONLY_CONTEXT_OPEN':raise ValueError('checker measurement scope')
    if hashlib.sha256((OUT/'inputs/checker_cone.sv').read_bytes()).hexdigest()!=measure['model']['cone_sha256']:raise ValueError('checker source changed')
    period=1000/1.2;q=743.9627002;u=60
    detector_cost=[]
    for K,replicas in [(256,412),(272,256)]:
        r=measure['results'][str(K)]
        detector_cost.append(dict(K=K,replicas=replicas,SS_clean_delay_ps=r['ss']['clean_max_delay_ps'],FF_min_ps=r['ff']['min_delay_ps'],mapped_area_per_cone_um2=r['mapped_area_um2'],replicated_cell_area_mm2=replicas*r['mapped_area_um2']/1e6,capture_fed_residual_for_FF_CLKQ_wire_setup_skew_ps=period-u-r['ss']['clean_max_delay_ps'],source_has_no_registers=r['state_bits']==0))
    return dict(schema='opentallas.dsrom.PAR2.source-relative-deadline.v1',
        source_commits=dict(parity='5fc7ff1a6361aa4ac99088aa36bfdf625879f6fc',clean='aefd04ba9e22992718d1e3612343c0dbe2a720cd'),
        input_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((OUT/'inputs').iterdir()) if x.is_file()},
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        callback_contract=dict(accepted_input='Observed source_issue at posedge gclk with PP1 and actual source metadata lane-valid; parent-supplied source receipt and full owner identity.',
            accepted_relative_edge=0,raw_capture_relative_edge=2,first_irreversible_lane_sample_relative_edge=3,
            source_has_no_ECC_qualification_gate=True,adapter_must_block_untested_lane_consume=True,
            registered_terminal_visibility_is_post_NBA=True,
            current_no_added_cycle_gate='Both matched K272 terminals and paired K256/gather authorization post-NBA visible no later than n+2 for sampling at n+3; otherwise hold/aligned-retime/reprice. A separately proved preedge combinational terminal may use its actual stable-before-edge receipt. No implicit replay.',
            parent_cfg_input_root_extractor_untouched=True),
        detector_timing_window=dict(target_period_ps=period,setup_uncertainty_ps=u,hold_uncertainty_ps=25,
            rawmacro_SS_CLKQ_ps=q,
            direct_macro_to_original_lane_detector_budget_before_wire_setup_skew_ps=3*period-q-u,
            capture_fed_detector_budget_before_FF_CLKQ_wire_setup_skew_ps=period-u,
            checker_measurement_source_commit=measure['source_commit'],detector_mapped_delay_not_supplied=False,
            keep_provisional_service_cycles=2,keep_provisional_held_II=2,registered_capture_and_hold_closed=False,not_a_pipeline_or_registered_hold_proof=True,
            formula='Direct: Qmacro+Ddetect+wire+Tsetup+relative_skew+60 <=3T. Captured: Qcapture+Ddetect+wire+Tsetup+relative_skew+60 <=T.'),
        exact_offered_prefix_cases=cases,
        source_seat_accounting=dict(paired_raw_bits=548,additional_inline512_already_in5fc=True,
            adapter_10202_FF_and843776_comparebit_debit_retained=True,no_double_charge_body_or_inlinebits=True,
            standalone_nonce_exception_overlay_is_counterfactual_until_disjoint_instance_map=True),
        normal_cost='Actual positive raw/main detection, capture, gather and owner fence; no fullcorrector on clean path.',
        exception_cost='Hold original credit/codeword/identity through actual correction or fault; source4raw/3main optimistic held bounds remain rare only. No probability0 or II1 from ceil.',
        measured_detector_costs=detector_cost,
        detector_operation_counts=t['detector_price'],
        detector_area_ledger=dict(retained_fullcorrector_floor_mm2=.7996465152+.5279219712,additional_isolated_checkers_cell_mm2=sum(x['replicated_cell_area_mm2'] for x in detector_cost),
            isolated_capture_status_bits_extra=measure['model']['own_extra_state_beyond_Maxwell_exception_hold_bits'],
            mapped_checkers_do_not_recharge_fullcorrector_or_replace_inherited_area_floor=True,
            prior_Maxwell_fullcorrector_copy_as_detector_proxy_is_superseded_not_additive=True,
            adapter5fc_and_Maxwell_state_overlays_require_disjoint_union_before_combining=True),
        no_token_loss_proven=False,actual_absolute_source_event_calendar=False,physical_GO=False,new_RTL=False,new_jobs=0)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args()
    if x.output.exists():raise ValueError('fresh artifact required')
    x.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
