#!/usr/bin/env python3
"""One S58 compiled array/return/config budget; proposals remain unqualified."""
import argparse,hashlib,json,math,subprocess
from fractions import Fraction as F
from pathlib import Path
import dsrom_full_product_binding as B
import dsrom_resident_site_binding as R

def proposed_SECDED_mapping():
    parity=[1<<i for i in range(8)]
    return {'codeword_bits':249,'Hamming_parity_physical_bits':[x-1 for x in parity],
            'overall_parity_physical_bit':248,'payload_physical_bits':[i-1 for i in range(1,249) if i not in parity],
            'unused_physical_bits':list(range(249,274)),
            'mapping_is_proposal_not_source_implementation':True}

def config(np,phw,nseg=8):
    words=(3*nseg+1)*(1<<phw);bundles=(np+4)//5
    # Broadcast cfg_ph/ld_k are identical across pairs. Five48bit pair
    # words share240bits at one address; PP2cycle timing retains1word/cycle.
    depthchunks=math.ceil(math.ceil(words/2)/4096);macros=bundles*2*depthchunks
    return {'compiled_pairs':np,'PHW':phw,'CW':3*nseg+1,'words_per_pair':words,
        'declared_bits_all_compiled_pairs':np*words*48,'pairs_per_bundle':5,'bundles':bundles,
        'proposed_word_SECDED_mapping':proposed_SECDED_mapping(),'independent_pair_outputs':'lane payload bits48*(pair%5)..48*(pair%5+1), after SECDED payload extraction; uniform phase/index does not merge pair content or pair gating',
        'useful_bits_per_bundle_word':240,'config_SECDED_required_bits':9,
        'PP_parity_banks_per_depthchunk':2,'depthchunks_per_parity':depthchunks,'physical4096x274_macros':macros,
        'gross_macro_bits':macros*4096*274,'macro_body_mm2':float(F(macros)*F('7881.3648')/10**6),
        'physical_address_recipe':{'bundle':'pair//5','lane':'pair%5','logical_index':'phase*25+cfg_word','parity':'logical_index&1','depthchunk':'(logical_index>>1)//4096','row':'(logical_index>>1)%4096','physical_leaf':'bundle*(2*depthchunks)+2*depthchunk+parity','payload_bits_before_SECDED':'[48*lane,48*(lane+1))'},
        'proposal_only':True,'same_depth_and_master':True,'full_macro_or_cfg_timing_admission':False,
        'source_loader_cycle_model':{'cfg_words_per_phase':25,'existing_combinational_cm_last_accept_after_cfg_go_cycles':26,
            'PP_macro2cycle_plus_consumer_register_last_accept_cycles':28,'additional_cycles_per_actual_cfg_event':2,
            'cycle_credit_qualified':False,'required_proof':['two-cycle macro read valid matches broadcast cfg_word index','each independent48bit output lane matches original per-pair cm contents','per-pair enable/gating and held data during backpressure','240payload+9SECDED exact bit map and decoder latency','final cfg word visible before matrix issue and consumer busy fence'],
            'conditions':'noECCadditionalcycles priced yet; no busy/return-drain overlap credit; actual broadcast controller/endpoint calendar must bind everycfg event'},
        'excluded_positive_costs':['mask-ROM collar and48bit lane decode','depthchunk+PP bank mux/control/capture','PHW10 dispatch key decoder and fanout','ECC encoder/decode/BIST fault propagation','halo/pin/corridor/PDN/CTS/hold exclusions'],
        'baseline_overlap_credit':0,'why_no_old_cfg_subtraction':'Pair wrapper cm is outside u_e element; no mapped instance ledger proves an existing cfg provider inside q/BF catalogue frame. Do not subtract PHW6 bits merely because source declared them.'}

def frozen(commit,path):
    raw=subprocess.check_output(['git','show',commit+':'+path],cwd=B.ROOT)
    return json.loads(raw),{'commit':subprocess.check_output(['git','rev-parse',commit],cwd=B.ROOT).decode().strip(),'path':path,'sha256':hashlib.sha256(raw).hexdigest()}

def build(model_path=None):
    if model_path is None:
        model,model_receipt=frozen('24d509c13','results/uarch/dsrom_fixed4096_owner_compiler_20261002/attempt8/model.json')
    else:
        raw=model_path.read_bytes();model=json.loads(raw);model_receipt={'path':str(model_path),'sha256':hashlib.sha256(raw).hexdigest(),'draft_snapshot':True}
    arch,arch_receipt=frozen('c1037db16','results/uarch/dsrom_cfg_phase_capacity_20261002/model.json')
    shared,shared_receipt=frozen('c1b460ae','results/uarch/dsrom_shared_complete_pair_candidate_r20_20261002/shared_candidate.json')
    corrected,corrected_receipt=frozen('c9b4730bd','results/uarch/dsrom_service_hub_arch_handoff_20261002/inventory_service_join.json')
    retained_path='results/uarch/dsrom_current4096_field_receipts_20261002/receipt-r4.json'
    retained_raw=(B.ROOT/retained_path).read_bytes()
    retained_receipt={'commit':'63f9fe2d6a7c9ada57c8cbfb0cf365b3ef349c24','path':retained_path,'sha256':hashlib.sha256(retained_raw).hexdigest()}
    retained=json.loads(retained_raw)['current_service_capacity_negative']
    if retained['service_join_source']!=corrected_receipt['commit']:raise ValueError('corrected service receipt currency')
    np=4096;nbf=724
    if model['candidate_id']!=B.CANDIDATE or any(s['compiled_NP']!=np for s in model['stage_stats']):raise ValueError('one shared compiled candidate')
    stats=model['stage_stats'];phw=max(s['required_PHW'] for s in stats)
    path='physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.json'
    blob=subprocess.check_output(['git','show',B.PIN+':'+path],cwd=B.ROOT);master=json.loads(blob)
    if abs(master['area']['macro_area_um2']-7881.3648)>1e-7:raise ValueError('macro area source currency')
    frame=F(np-nbf)*R.Q_FRAME+F(nbf)*R.BF_FRAME
    ret=B.return_dimensions({'compiled_NP':np,'R':128,'NBF':nbf,'RD':64,'ROOTD':128,'RST':1})
    cfg=config(np,phw)
    actual_cfg=arch['storage_cases']['compiled_declared']
    if actual_cfg['cfg_bits']!=cfg['declared_bits_all_compiled_pairs']:raise ValueError('compiled configuration bits mismatch')
    cfg['alternate_prospective_shared_owner_provider']=actual_cfg
    cfg['selected_budget_provider']='Archimedes source-equivalent4096x72 per-pair depth mapping plus local mux; Maxwell five-pair packing remains separate unadopted proposal'
    cfg_cost=F(str(actual_cfg['ROM_plus_word_mux_screen_mm2']))
    rne=F(str(retained['RNE_separate_construction_mm2']));wake=(F(np-nbf)*F('27.00216')+F(nbf)*F('2128.58296'))/10**6
    inherited_field_allowance=F(str(retained['corrected_field_available_mm2']));inherited_debit=F(858)-inherited_field_allowance
    priced=frame/10**6+F(str(ret['conservative_FF_50pct_um2']))/10**6+cfg_cost+rne+wake
    perstage=[{'stage':s['stage'],'phase_count':s['phase_count'],'required_PHW':s['required_PHW'],
        'full_compiled_cfg':config(np,s['required_PHW']),
        'active_only_cfg_bits_from_owner':s['pair_cfg_bits_if_required_PHW']} for s in stats]
    return {'schema':'opentallas.dsrom.one-S58-compiled-whole-budget.v1','candidate':B.CANDIDATE,'stage_count':58,'TP':4,
        'input_receipts':[model_receipt,arch_receipt,shared_receipt,corrected_receipt,retained_receipt,
                         {'commit':B.PIN,'path':path,'sha256':hashlib.sha256(blob).hexdigest()}],
        'physical_array':{'compiled_NP':np,'NBF':nbf,'source_BF_predicate':'pair=floor(i*NP/NBF),i0..NBF-1',
            'physical_q_frames':np-nbf,'physical_BF_frames':nbf,'catalog_full_compiled_frame_mm2':float(frame/10**6),
            'main4096_macros_per_die':4*np,'active3375_not_physical_declaration':True,'dualcompute_abstract_bound':False},
        'return':ret,'configuration_provider':cfg,'per_stage_config_requirements':perstage,
        'same_template_maxPHW_proposal':True,'reticle_mm':[26,33],
        'exact_once_area_ledger_mm2':{'reticle':858,'inherited_service_routes_clockPG_debit':float(inherited_debit),
            'already_inside_inherited_named_service_proxy_do_not_add_again':shared['area_and_service_reserve']['source_named_service_proxy_mm2'],
            'full_compiled_q_BF_catalog_frames':float(frame/10**6),'declared_return_FF50_proxy':ret['conservative_FF_50pct_um2']/1e6,
            'config_prospective_body_plus_local_mux':float(cfg_cost),'RNE_BF724_upper_proxy':float(rne),'WAKE_full_compiled_upper_proxy':float(wake),
            'composed_priced_field_terms':float(priced),'remaining_against_corrected_inherited_field_allowance':float(inherited_field_allowance-priced),
            'earlier_unidentified_native_residual_proxy_47_208':{'mm2':47.208013178655904,'not_silently_removed':True,'excluded_from_named_component_sum_until_containment_reconciled':'No provider identity proves disjointness from new cfg/ECC/raw/dispatch/control terms; conservative counterfactual adding it is recorded separately.'},
            'counterfactual_unknown_native_residual_disjoint_total':float(priced+F('47.208013178655904')),
            'conservative_no_containment_credit_die_total':float(inherited_debit+priced+F('47.208013178655904')),
            'conservative_no_containment_credit_reticle_margin':float(inherited_field_allowance-priced-F('47.208013178655904')),
            'actual_fixed_service_rectangles':corrected['service']['rectangles'],
            'service_clock_PG_actual_shapes_bound':corrected['service']['actual_clock_PG_shapes_bound'],
            'unpriced_nonzero_terms':['qFP4 separateECC provider/decoder','actualHE/CROM/shared dispatch provider','cfgmux/capture/PHW fanout decode area and routes','currentRNEWAKE dualcompute outline growth','service macro halo/pins/clockPG/hold costs not proven by inherited debit'],
            'fit_verdict':'NOT_QUALIFIED_mix_of_source_macro_body_and_conservative_frame_return_RNE_WAKE_proxies_not_minimum_or_impossibility'},
        'critical_path_latency':{'reference41_candidate58_added_stage_boundaries':17,
            'old_conditional_hop_delta_us':6.238,'old_conditional_field_reuse_and_head_delta_us':22.864,
            'old_390_061_us_not_current_calibration':True,
            'actual_cfg_delta_formula':'sum_over_nonoverlapped_actualcfg_events(2cycles + ECCdecodecycles + source_lease/drain/CDC stalls), 1.2GHz modelonly; storage phasecount is not token eventcount',
            'source_cfg_after_last_GO_busy':'retain source consumer drain; no ideal overlap between q/BF phases or shared ports',
            'no_actual_whole_token_cycles':True},
        'allocator_observed_failure_count':len(model['allocation_failures']),'allocator_first_failure':model['allocation_failures'][0] if model['allocation_failures'] else None,'source_PHW6_verdict':model['current_source_PHW6_verdict'],
        'conditional_S58_original_FAIL_preserved':True,'new_count_selected':False,'RTL_PR':False,'full_token_or_physical_admission':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();x=build(a.model);a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
