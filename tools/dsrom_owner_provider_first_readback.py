#!/usr/bin/env python3
"""Readback of completed provider-first journals; never rerun matrix packing.

The original300s allocation/checker timeout remains a failure. Exact set-based
membership changes verification complexity, not the source contract or geometry.
"""
import argparse, collections, gzip, hashlib, json, math
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V
import dsrom_owner_provider_first as P

ROOT=Path(__file__).resolve().parents[1]


def reconstruct_pools(records,providers):
    pools=[C.Pool(3375,724) for _ in range(58)]
    spans=collections.defaultdict(list)
    for p in providers:
        s=p['stage'];pool=pools[s]
        if p['kind']=='ECC_FP4_SIDECAR':
            if p['pairs']!=pool.ecc_pairs:raise ValueError('ECC reservation changed')
            pool.ecc_bits=p['bits']
        elif p['kind'] in ('HE','CROM'):
            for q in p['pairs']:
                if q not in pool.fill or q in pool.raw or q in pool.bf:raise ValueError('illegal immutable provider site')
                pool.raw.add(q);pool.fill[q]=8192
        else:raise ValueError('unknown provider class')
    for m in records:
        if m['stage'] is None:continue
        pool=pools[m['stage']];pool.phases+=1
        for si,q,first,n,stride,start,w in m['plans']:
            if q in pool.raw:raise ValueError('matrix aliases immutable provider')
            pool.fill[q]=max(pool.fill[q],start+n*w)
    return pools


def control_debit(phases,np=4096):
    phw=max(1,(phases-1).bit_length());words=25*(1<<phw)
    # A physical4096x274 allocation screen, not a source-proven config macro.
    # Protect each48-bit sourceword with7SECDED bits; four55-bit words fit.
    packed=274//(48+C.secded_bits(48));leaves=math.ceil(math.ceil(words/packed)/4096)
    return {'phase_count':phases,'required_PHW':phw,'source_PHW6_fits':phases<=64,
        'compiled_cfg_source_data_bits':np*words*48,'compiled_cfg_SECDED_extra_bits_if_protected':np*words*C.secded_bits(48),
        'phase_key_table_bits':32*(1<<phw),'cfg_source_words_per_pair':words,'cfg_load_cycles_per_phase':27,
        'source_PHW6_compiled_cfg_source_data_bits':np*25*64*48,
        'conditional_fixed4096_cfg_screen':{'physical_word_bits':274,'protected_cfg_word_bits':55,
            'packed_cfg_words_per_macro_word':packed,'leaves_per_compiled_pair':leaves,
            'macro_body_area_all_compiled_pairs_mm2':leaves*np*7881.3648/1e6,
            'separate_from_4_weight_macros':True,'packing_mux_and_ports_not_implemented':True,
            'included_in_original_pair_frame_not_proven':True,'area_not_free_or_double_debited':True},
        'config_macro_abstract_or_area_fit_qualified':False}


def summarize(pools,records,providers,decls,headers):
    demanded=collections.Counter();placed=collections.Counter();counts=collections.Counter();placed_counts=collections.Counter()
    for m in records:
        words=P.matrix_words(m);demanded[m['format']]+=words;counts[m['format']]+=1
        if m['stage'] is not None:placed[m['format']]+=words;placed_counts[m['format']]+=1
    stats=[]
    for s,p in enumerate(pools):
        cap=3375*2*8192;matrix=sum(v for q,v in p.fill.items() if q not in p.raw)*2
        raw=len(p.raw)*2*8192;unused=cap-matrix-raw
        if unused<0 or p.ecc_bits>len(p.ecc_pairs)*4*4096*256:raise ValueError('finite capacity violation')
        stats.append({'stage':s,'compiled_NP':4096,'NBF':724,'active_pairs':3375,'compiled_padding_sites':721,
            'compiled_physical_weight_macros':16384,'active_physical_word_capacity':cap,'matrix_physical_words':matrix,
            'immutable_raw_reserved_physical_words':raw,'unused_active_physical_words':unused,
            'free_logical_words_by_root_region':{r:sum(8192-p.fill[q] for q in p.byreg[(r,'q')] if q not in p.raw) for r in range(128)},
            'BF_free_logical_words':sum(8192-p.fill[q] for q in p.bf),'control':control_debit(p.phases)})
    covered=set().union(*(d[4] for d in decls));covered|={'embed.weight','head.weight','norm.weight'}
    if {n for n in headers if n.startswith('layers.')} -covered:raise ValueError('active tensor omission')
    encoded_total=sum(demanded.values());reserved=sum(s['immutable_raw_reserved_physical_words'] for s in stats)
    unused=sum(s['unused_active_physical_words'] for s in stats);capacity=58*3375*2*8192
    holes=sum(s['matrix_physical_words'] for s in stats)-sum(placed.values())
    if capacity!=sum(placed.values())+holes+reserved+unused:raise ValueError('word capacity not conserved')
    summary={'declared_matrix_count':sum(counts.values()),'placed_matrix_count':sum(placed_counts.values()),
        'declared_by_format':counts,'placed_by_format':placed_counts,
        'routed_expert_matrix_count':sum(m['expert'] is not None for m in records),
        'encoded_physical_words_per_rank_by_format':demanded,'placed_encoded_physical_words_per_rank_by_format':placed,
        'declared_encoded_physical_words_per_rank':encoded_total,'placed_encoded_physical_words_per_rank':sum(placed.values()),
        'unallocated_encoded_physical_words_per_rank':encoded_total-sum(placed.values()),
        'alignment_hole_words_per_rank':holes,'immutable_raw_reserved_physical_words_per_rank':reserved,
        'unused_active_physical_words_per_rank':unused,'active_physical_word_capacity_all58_per_rank':capacity,
        'rank_replicas':4,'active_header_tensor_count':len(covered),
        'active_header_native_storage_bytes_once':sum(headers[n]['source_storage_bytes'] for n in covered),
        'native_header_bytes_not_equal_to_padded_converted_replicated_ROM_bytes':True}
    return stats,summary


def verify(journal,out):
    journal=journal.resolve();out=out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    headers=C.load_headers(P.INPUTS/'tensor_headers.jsonl.gz')
    decls=[C.declarations(headers,L) for L in range(40)]
    records=list(C.readrows(journal/'assignments.jsonl.gz'));providers=list(C.readrows(journal/'provider_assignment.jsonl.gz'))
    before=list(C.readrows(journal/'immutable_provider_preallocation.jsonl.gz'))
    after=[p for p in providers if p['kind'] in ('HE','CROM')]
    if before!=after:raise ValueError('immutable providers changed after packing')
    pools=reconstruct_pools(records,providers);field=pools[0].compiled_field()
    # Same exact finite membership predicates as prior verifier, with hash sets.
    fast_field=dict(field);fast_field['weight_active_site_IDs']=set(field['weight_active_site_IDs'])
    fast_field['BF_DUAL_site_IDs']=set(field['BF_DUAL_site_IDs'])
    gate=P.verify_records(records,providers,decls,fast_field)
    stats,totals=summarize(pools,records,providers,decls,headers)
    demand=json.loads(gzip.decompress((P.INPUTS/'full_product_demand.json.gz').read_bytes()))
    field.update(compiled_physical_weight_macros=16384,compiled_q_sites=3372,compiled_BF_dual_sites=724,
        source_envelope_area_mm2=(3372*64825.596+724*142971.9984)/1e6,
        return_declared_bits=69771008,conditional_return_FF50pct_mm2=69771008*.37908/.5/1e6,
        RNE_WAKE_and_dualcompute_hardened_context_qualified=False)
    missing=[{'layer':m['layer'],'alias':m['alias']} for m in records if m['stage'] is None]
    readonly_homes={p['layer']:p['stage'] for p in providers if p['kind']=='HE'}
    cross_home=collections.Counter()
    for m in records:
        if m['stage'] is not None and m['stage']!=readonly_homes[m['layer']]:cross_home[m['layer']]+=1
    needed_sourcebits=sum(s['control']['compiled_cfg_source_data_bits'] for s in stats)
    report={'schema':'opentallas.fullmodel.owner.provider-first-readback.v1','candidate':P.CANDIDATE,'prior_FAIL_commit':P.PRIOR,
        'capacity_verdict':'PASS_SYMBOLIC_STORAGE_PLACEMENT' if not missing else 'FAIL_CANDIDATE_PLACEMENT',
        'original_execution_verdict':'FAIL_RESOURCE_TIMEOUT_DURING_VERIFICATION',
        'readback_calibration_gate':gate,'all40_all384_placed':not missing and totals['routed_expert_matrix_count']==40*384*3,
        'missing_matrices':missing,'conservation':totals,'compiled_field':field,'stage_stats':stats,
        'provider_homes':readonly_homes,'matrix_stages_differing_from_provider_home_counts_by_layer':cross_home,
        'used_matrix_stage_IDs':sorted({m['stage'] for m in records if m['stage'] is not None}),
        'all58_stages_remain_hardware_charged':True,
        'control_source_PHW6_verdict':'PASS' if all(s['control']['source_PHW6_fits'] for s in stats) else 'FAIL_REQUIRED_CONTROL_STORAGE_WIDTH_AND_FANOUT_BINDING',
        'total_compiled_cfg_source_data_bits_per_TP_rank':needed_sourcebits,
        'conditional_cfg_fixed4096_macro_body_area_sum_per_TP_rank_mm2':sum(s['control']['conditional_fixed4096_cfg_screen']['macro_body_area_all_compiled_pairs_mm2'] for s in stats),
        'dedicated_providers':V.dedicated_providers(headers),'source_pins':V.source_receipts(),
        'descriptor_bridge_instruction_count':sum(n['kind']=='instruction' for n in demand['nodes']),
        'descriptor_bridge_runtime_action_count':sum(n['kind']=='runtime_action' for n in demand['nodes']),
        'descriptor_provider_ABI_and_finite_causal_calendar_binding_complete':False,
        'remaining_binding_limits':['PHW/config storage and its actual macro/pin/decoder/fanout area debit, preserving27-cycle loader contract unless priced otherwise.',
            'HE/CROM consumers need native field274 provider adapters and explicit local/remote delivery; home rule itself grants no port or latency.',
            'Mandatory ECC sidecar decode and its source provenance/clock/ports are unqualified.',
            'q-on-BF is source-supported but actual dualcompute/RNE/WAKE hardened abstract remains unqualified.',
            'All4778 descriptor node/rank lifetimes/calendars, head compute and dedicated table ports remain to bind.'],
        'next_gate':'Same candidate: compose actual descriptor/rank provider routes and finite calendars, including configuration provider storage; storage PASS alone is not admission.',
        'minimum_stage_count_proved':False,'new_partition_selected':False,'whole_token_cycles':None,
        'originals_unchanged':True,'matrix_packing_reruns':0,'checkpoint_payload_reads':0,'RTL_builds_PR_or_sims':0,
        'physical_area_fit_qualified':False,'physical_admission':False,'full_token_admission':False,
        'compiler_sha256':C.sha(Path(__file__).read_bytes()),'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in
            [journal/'assignments.jsonl.gz',journal/'provider_assignment.jsonl.gz',journal/'compiler_source.py',
             journal/'immutable_provider_preallocation.jsonl.gz',journal/'terminal.json',P.INPUTS/'tensor_headers.jsonl.gz',P.INPUTS/'full_product_demand.json.gz']}}
    (out/'model.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'capacity':report['capacity_verdict'],'declared':totals['declared_matrix_count'],
        'placed':totals['placed_matrix_count'],'minimum_stage_proof':False,'PHW6':report['control_source_PHW6_verdict']}),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--journal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    verify(a.journal,a.out)
