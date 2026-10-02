#!/usr/bin/env python3
"""Default-off clean-terminal proposal with finite held correction, no RTL jobs."""
import argparse,functools,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_PAR2_clean_terminal_20261002'

@functools.lru_cache(maxsize=2)
def masks(k):
    p=[];i=3
    while len(p)<k:
        if i&(i-1):p.append(i)
        i+=1
    return [sum(1<<j for j,x in enumerate(p) if x&(1<<b)) for b in range(9)],p

def check_word(cw,k):
    ms,_=masks(k);d=cw&((1<<k)-1)
    syn=sum((((d&m).bit_count()&1)^((cw>>(k+b))&1))<<b for b,m in enumerate(ms))
    overall=cw.bit_count()&1
    return syn,overall,syn==0 and overall==0

def encode(d,k):
    ms,_=masks(k);w=d|sum(( (d&m).bit_count()&1)<<(k+b) for b,m in enumerate(ms))
    return w|((w.bit_count()&1)<<(k+9))

def source_decoder(cw,k):
    syn,overall,_=check_word(cw,k);_,p=masks(k);fix=sum((syn==x)<<j for j,x in enumerate(p))
    pow2=(syn&(syn-1))==0;hit=bool(fix)
    return (cw&((1<<k)-1))^(fix if overall else 0),bool(overall and (pow2 or hit)),bool((not overall and syn!=0) or (overall and not pow2 and not hit))

def build():
    r=json.loads((OUT/'inputs/decoder_characterization.json').read_text());c=json.loads((OUT/'inputs/context.json').read_text())
    if r['status']!='CHARACTERIZED_COMBINATIONAL_ONLY' or r['FF_registered_hold_closed']:raise ValueError('wrong qualification scope')
    if hashlib.sha256((OUT/'inputs/decoder.sv').read_bytes()).hexdigest()!=r['model']['decoder_source_sha256']:raise ValueError('decoder source mismatch')
    period=1000/1.2;unc=60;clkq=743.9627002;dec=[]
    for k,rep in [(256,412),(272,256)]:
        v=r['results'][str(k)];arrival=max(v['ss']['data_arrival_ps']);ms,_=masks(k)
        dec.append(dict(K=k,N=k+10,replicas=rep,clean_predicate='syn==0 && overall==0',
            source_data_on_clean='cw[K-1:0], identical to original corrected data and good flags',
            detector_only_output_bits=11,detector_only_outputs='syn[8:0],overall,clean',
            raw_data_bits_held_in_parallel=k,
            detector_only_characterization_admitted=True,correction_fix_comparators_off_normal_terminal_path=True,
            syndrome_XOR2_nodes=sum(m.bit_count() for m in ms),overall_XOR2_nodes=k+9,
            balanced_reduction_depth_is_structural_not_measured=True,
            clean_detector_service_cycles_provisional=2,clean_detector_II_held_provisional=2,
            detector_mapped_delay_unmeasured=True,existing_full_corrector_arrival_ps=arrival,
            full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq=math.ceil((arrival+unc)/period),
            full_corrector_lower_bound_is_NOT_proven_pipeline=True,existing_combinational_state_bits=0,
            measured_corrector_cell_area_mm2=rep*v['area_um2']/1e6,
            detector_area_no_subtraction_credit=True,registered_hold_closed=False))
    spec=importlib.util.spec_from_file_location('finite',OUT/'inputs/finite_calendar_source.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    p=json.loads((OUT/'inputs/provisional_parameters.json').read_text())
    p.update(delivery_cycles=c['endpoint_entry']['modeled_reply_pipeline_cycles'],raw_decode_cycles=2,decoder_II=2,weight_ECC_cycles=2)
    witness=json.loads((OUT/'inputs/witness_word_rows.json').read_text())
    counts=[len(v) for v in witness['unique_rows_by_pidx_MB_parity'].values()]
    clean=mod.calendar(counts,p)
    error=dict(p,raw_decode_cycles=dec[0]['full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq'],decoder_II=dec[0]['full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq'],weight_ECC_cycles=dec[1]['full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq'])
    repair=mod.calendar(counts,error)
    # Preserve old conservative reference-stage charge; add nonce and inline
    # storage, plus distinct exception holds until actual disjoint lifetime proven.
    units=sum(x['replicas']*x['cycles'] for x in c['capture_header_entries'])
    nonce_bits=16*units;inline_bits=128*4;exception_bits=412*(266+74)+256*(282+74)
    detector_proxy=sum(d['measured_corrector_cell_area_mm2'] for d in dec)
    coeff=c['area']['no_containment_overlay_FF50_mm2']/c['area']['prospective_fullwidth_reference_register_bits']
    return dict(schema='opentallas.dsrom.PAR2.clean-terminal.v1',candidate=c['candidate'],
        input_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((OUT/'inputs').iterdir()) if x.is_file()},
        decoder_source_sha256=r['model']['decoder_source_sha256'],generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        finite_calendar_source_sha256=hashlib.sha256((OUT/'inputs/finite_calendar_source.py').read_bytes()).hexdigest(),
        decoder_entries=dec,raw_macro_SS_CLKQ_ps=clkq,target_period_ps=period,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        direct_rawmacro_plus_fullK256_held_lower_bound_intervals=math.ceil((clkq+dec[0]['existing_full_corrector_arrival_ps']+unc)/period),
        macro_arrival_combination='Conservative use of full reported decoder arrival; source20ps is transition not assumed removable arrival. Actual launch arrival/slew/capture setup/wire/skew still required.',
        encoding_contract=dict(default_off=True,current_physical_FP4_encoder_placement_proven=False,
            main='data272 + inline check[1:0] + sidecar check[8:2],overall =282 systematic bits',
            sidecar='sourceK256 protected256+check9+overall=266; physical274word unused8not free parity',
            synthetic_oracle_only=True,paired_two274_raw_capture_bits=548,previous544_omits_inline_bits=4),
        normal_flow='Accept exact read identity -> hold raw codeword/data -> parallel syndrome/overall check -> authenticated CLEAN terminal -> gather checked sidecar bits -> main check -> only then irreversible arithmetic consume.',
        exception_flow='Nonclean word keeps input/debt stable. Source full corrector runs on held codeword; good corrected terminal replaces staged data/parity before dependent main check. Poison faults before consume. No timer as a decoder terminal.',
        buffer_and_fence=dict(readnonce_bits=16,old_proposed_header_bits=58,new_header_bits=74,
            gather_data_bits=16,gather_full_packet_bits=90,independent_lanes_proposed=128,full_reply_demand_bits=11520,
            read_credit_per_leaf=1,response_slots_proposed=128,gather_slots_proposed=128,
            release_credit_only_after_authenticated_delivery=True,
            wrap_requires_all_accepted_reads_correction_capture_delivery_debts_drained=True,
            source24_external_owner_lease_generation_nonce_reused=True,new_native_owner_ledger=False,
            stale_duplicate_mismatch_cannot_qualify=True,actual_readnonce16_echo_RTL_unimplemented=True),
        area=dict(prior_screen_mm2=c['area']['conservative_screen_with_all_pipeline_overlay_mm2'],
            no_decoder_allowance_floor_reduction=True,extra_nonce_reference_bits=nonce_bits,extra_inline_bits=inline_bits,
            separate_exception_hold_reference_bits=exception_bits,no_capture_reuse_credit=True,
            added_FF50_policy_mm2=(nonce_bits+inline_bits+exception_bits)*coeff,
            extra_clean_detector_full_corrector_cell_proxy_mm2=detector_proxy,
            detector_proxy_is_conservative_duplicate_logic_not_measured_clean_cone=True,
            screen_mm2=c['area']['conservative_screen_with_all_pipeline_overlay_mm2']+(nonce_bits+inline_bits+exception_bits)*coeff+detector_proxy,
            FF50_is_policy_not_mapped_clockPG_or_fit=True),
        finite_witness=dict(source=witness,clean_parameters=p,clean_schedule=clean,
            all_words_repair_counterfactual_parameters=error,all_words_repair_counterfactual_schedule=repair,
            selected_EIDs_not_runtime_bound=True,original_consumer_deadline_unbound=True,
            error_probability_not_assumed_zero=True,exception_stalls='sum of exposed authenticated correction/poison/drain costs on actual critical dependencies; requires error events, no invented frequency',
            held_multicycle_service_NOT_pipelined_II=True),
        admission=dict(existing_detector_cone_characterization=True,
            own_gate='Exact syndrome/overall complete loaded clean terminal cones + raw macro launch/capture and retained data; measure detector delay before selecting normal cycles/II. Input stable until terminal; FFhold and source encoder/accepted identity/deadline remain required.',
            fulltile_PR=False,normal_latency_calibrated=False,no_token_loss=False,new_RTL=False,new_job=False),
        old_fullcorrector_failures_and_provisional_profiles_preserved=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);p=a.parse_args()
    if p.output.exists():raise ValueError('new evidence required')
    p.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
