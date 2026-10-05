#!/usr/bin/env python3
"""Same S58 candidate, immutable providers reserved before any matrix packing.

The previous compiler/FAIL remains byte-identical. Provider homes are a declared
symbolic placement policy, not an existing remote HE/CROM delivery interface.
No source RTL, image payload, physical implementation or stage sweep is invoked.
"""
from __future__ import annotations
import argparse, collections, datetime, json, math, sys
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V

ROOT=Path(__file__).resolve().parents[1]
INPUTS=V.BASE/'inputs'
PRIOR='24d509c135d4b9fa13a9bad504aad8a6cf69fc7a'
CANDIDATE='DS4096-TP4-S58-PAIR1'


def provider_home(layer,stages=58,layers=40):
    """One ordered immutable provider bundle per home, spread over the fixed die set."""
    if not 0<=layer<layers or stages<layers:raise ValueError('provider home geometry')
    return layer*stages//layers


def reserve_providers(pools,declarations):
    providers=[];homes={}
    for L,(_,constants,he,_,_) in enumerate(declarations):
        stage=provider_home(L,len(pools),len(declarations));homes[L]=stage
        pool=pools[stage]
        hw=sum(x['rows']*math.ceil(x['K']/64) for x in he)
        word=0;hd=[]
        for x in he:
            words=x['rows']*math.ceil(x['K']/64)
            hd.append({**x,'native_bank_word_base':word,'native_bank_words':words});word+=words
        if hw:providers.append({'stage':stage,'layer':L,'kind':'HE','declarations':hd,
            **pool.raw_bankset([x['alias'] for x in he],hw),
            'provider_home_policy':'floor(layer*58/40), independent of later matrix placement',
            'native_HE_to_field_274_adapter_and_transport_qualified':False})
        elements=0;cd=[]
        for c in constants:
            cd.append({**c,'native_FP32_element_base':elements});elements+=c['elements']
        if elements:providers.append({'stage':stage,'layer':L,'kind':'CROM','declarations':cd,
            **pool.raw_bankset([c['alias'] for c in constants],math.ceil(elements/8),1),
            'native_CROM_to_field_274_adapter_and_transport_qualified':False})
    return providers,homes


def provider_tensor_address(provider,alias,row,col=0):
    d=next(x for x in provider['declarations'] if x['alias']==alias)
    if provider['kind']=='HE':
        if not (0<=row<d['rows'] and 0<=col<d['K']):raise ValueError('HE tensor coordinate')
        q,bank=divmod(col,8);beat,lane=divmod(q,8)
        word=d['native_bank_word_base']+row*math.ceil(d['K']/64)+beat;bit=lane*32
    elif provider['kind']=='CROM':
        if col!=0 or not 0<=row<d['elements']:raise ValueError('CROM local flat coordinate')
        index=d['native_FP32_element_base']+row;bank=0;word=index//8;bit=(index%8)*32
    else:raise ValueError('not an immutable HE/CROM provider')
    return dict(C.provider_word_address(provider,bank,word,bit,32),stage=provider['stage'],
                layer=provider['layer'],tensor=d['tensor'],native_bank=bank,native_word=word,
                transport_ABI_qualified=False)


def matrix_words(m):
    """Encoded physical weight words, including source-defined padding and copied scales."""
    return ((m['rows']+1)//2)*2*sum(C.S.seg_words(m['format'],e,n) for e,n in C.ordered_segments(m['format'],m['K']))


def verify_records(records,providers,decls,field):
    wanted={(m['layer'],m['alias']):m for g,*_ in decls for ms in g.values() for m in ms}
    got={(m['layer'],m['alias']):m for m in records}
    if len(got)!=len(records) or set(got)!=set(wanted):raise ValueError('matrix declaration omission/duplicate')
    for key,m in got.items():
        d=wanted[key]
        for k in ('rows','K','format','tensor','rank_slices','expert','source_scale_tensor'):
            if m[k]!=d[k]:raise ValueError('source declaration mismatch '+str(key)+':'+k)
        if m['stage'] is None:continue
        C.check_matrix(m)
        actual=sum(n*w*2 for si,p,first,n,stride,start,w in m['plans'])
        if actual!=matrix_words(m):raise ValueError('encoded words not conserved')
        for si,p,*_ in m['plans']:
            if p not in field['weight_active_site_IDs']:raise ValueError('inactive weight site')
            if m['format']=='bf16' and p not in field['BF_DUAL_site_IDs']:raise ValueError('BF on q-only site')
    homes={}
    for p in providers:
        if p['kind'] not in ('HE','CROM'):continue
        key=(p['layer'],p['kind'])
        if key in homes:raise ValueError('duplicate provider')
        homes[key]=p
    if set(homes)!={(L,k) for L in range(40) for k in ('HE','CROM')}:raise ValueError('immutable provider omitted')
    return C.check_global_overlap(records,providers)


def compile_candidate(headers,candidate,out):
    counts=candidate['single_candidate_counts']
    if candidate['candidate_id']!=CANDIDATE or (counts['stages'],counts['TP'],counts['complete_pairs_per_die'],
            counts['BF_pairs_per_die_reservation'])!=(58,4,3375,724):raise ValueError('different shared candidate')
    out.mkdir(parents=True,exist_ok=False)
    (out/'compiler_source.py').write_bytes(Path(__file__).read_bytes())
    declarations=[C.declarations(headers,L) for L in range(40)]
    pools=[C.Pool(3375,724) for _ in range(58)]
    providers,homes=reserve_providers(pools,declarations)
    immutable_snapshot={(p['layer'],p['kind']):(p['stage'],tuple(p['pairs'])) for p in providers}
    # All immutable HE/CROM/ECC pair IDs exist before the first matrix trial.
    C.gzrows(out/'immutable_provider_preallocation.jsonl.gz',providers)
    (out/'preallocation.json').write_text(json.dumps({'schema':'opentallas.owner.provider-first.preallocation.v1',
        'candidate':CANDIDATE,'matrix_trials_so_far':0,'all40_HE_CROM_reserved':True,
        'HE_CROM_complete_pairs':sum(len(p['pairs']) for p in providers),
        'ECC_reserved_complete_pairs':sum(len(p.ecc_pairs) for p in pools),
        'provider_homes':homes,'ECC_site_IDs_by_stage':[p.ecc_pairs for p in pools]},indent=2)+'\n')
    stage=0;failures=[];records=[];covered=set();demand_words=collections.Counter();placed_words=collections.Counter()
    for L,(groups,cs,he,tables,names) in enumerate(declarations):
        covered.update(names)
        allocation_groups=[(m['alias'],[m]) for m in groups[None]]
        allocation_groups +=[(e,ms) for e,ms in groups.items() if e is not None]
        for group,ms in allocation_groups:
            for m in ms:demand_words[m['format']]+=matrix_words(m)
            while True:
                trial=pools[stage].clone();planned=[]
                try:
                    for m in ms:
                        x=trial.matrix(m);x.update(stage=stage,compiled_NP=4096,key=C.key_for(L,m['alias']),
                                                 immutable_provider_home=homes[L])
                        C.check_matrix(x);planned.append(x)
                except C.CapacityError as e:
                    if stage+1<58:stage+=1;continue
                    failures.append({'layer':L,'group':group,'stage':stage,'error':str(e),
                                     'unallocated_aliases':[m['alias'] for m in ms]})
                    records.extend({**m,'stage':None,'plans':[],'allocation_failure':str(e)} for m in ms)
                    break
                pools[stage]=trial;records.extend(planned)
                for m in planned:placed_words[m['format']]+=matrix_words(m)
                break
        print(f'layer={L} last_matrix_stage={stage} failed_groups={len(failures)}',flush=True)
    C.gzrows(out/'assignments.jsonl.gz',records)
    for s,pool in enumerate(pools):providers.append({'stage':s,'kind':'ECC_FP4_SIDECAR','pairs':pool.ecc_pairs,
        'bits':pool.ecc_bits,'protected_data_capacity_bits':len(pool.ecc_pairs)*4*4096*256,
        'read_bits_per_active_pair_cycle':16,'current_source_decoder_available':False})
    if immutable_snapshot!={(p['layer'],p['kind']):(p['stage'],tuple(p['pairs'])) for p in providers if p['kind'] in ('HE','CROM')}:
        raise ValueError('immutable provider moved after matrix packing')
    C.gzrows(out/'provider_assignment.jsonl.gz',providers)
    field=pools[0].compiled_field();overlap=verify_records(records,providers,declarations,field)
    stats=[];used_stages={m['stage'] for m in records if m['stage'] is not None}
    for s,p in enumerate(pools):
        phw=max(1,(p.phases-1).bit_length());capacity=3375*2*8192
        used_weight=sum(v for pair,v in p.fill.items() if pair not in p.raw)*2
        reserved_raw=len(p.raw)*2*8192;unused=capacity-used_weight-reserved_raw
        if unused<0 or p.ecc_bits>len(p.ecc_pairs)*4*4096*256:raise ValueError('finite capacity debit violated')
        free_by_region={r:sum(8192-p.fill[q] for q in p.byreg[(r,'q')] if q not in p.raw) for r in range(128)}
        stats.append({'stage':s,'compiled_NP':4096,'NBF':724,'weight_active_pairs':3375,'padding_sites':721,
            'compiled_physical_macros':16384,'physical_compiled_gross_bits':4096*4*4096*274,
            'active_physical_word_capacity':capacity,'matrix_physical_words':used_weight,
            'immutable_raw_reserved_physical_words':reserved_raw,'unused_active_physical_words':unused,
            'free_logical_words_by_root_region':free_by_region,'BF_free_logical_words':sum(8192-p.fill[q] for q in p.bf),
            'phase_count':p.phases,'required_PHW':phw,'source_PHW6_fits':p.phases<=64,
            'compiled_cfg_source_data_bits':4096*25*48*(1<<phw),
            'compiled_cfg_SECDED_extra_bits_if_protected':4096*25*C.secded_bits(48)*(1<<phw),
            'phase_key_table_bits':32*(1<<phw),'config_load_cycles_per_phase':27,
            'config_mask_ROM_abstract_ports_and_area_qualified':False})
    global_names={'embed.weight','head.weight','norm.weight'};covered.update(global_names)
    if {n for n in headers if n.startswith('layers.')} -covered:raise ValueError('active tensor omitted')
    count=collections.Counter(m['format'] for m in records);placed=collections.Counter(m['format'] for m in records if m['stage'] is not None)
    conservation={'declared_matrix_count':len(records),'placed_matrix_count':sum(placed.values()),
        'declared_by_format':count,'placed_by_format':placed,'all40_all384_expert_matrix_count':sum(m['expert'] is not None for m in records),
        'encoded_matrix_physical_words_per_rank':demand_words,'placed_encoded_matrix_physical_words_per_rank':placed_words,
        'unallocated_encoded_matrix_physical_words_per_rank':demand_words-placed_words,
        'matrix_words_per_rank_declared_total':sum(demand_words.values()),
        'matrix_words_per_rank_placed_total':sum(placed_words.values()),
        'active_word_capacity_all58_per_rank':58*3375*2*8192,
        'raw_reserved_word_capacity_all58_per_rank':sum(s['immutable_raw_reserved_physical_words'] for s in stats),
        'unused_active_word_capacity_all58_per_rank':sum(s['unused_active_physical_words'] for s in stats),
        'active_header_tensor_count':len(covered),'active_header_native_storage_bytes_once':sum(headers[n]['source_storage_bytes'] for n in covered),
        'rank_storage_replicas':4,'native_header_bytes_not_equivalent_to_padded_converted_replicated_ROM_bytes':True}
    field.update(compiled_physical_macros=16384,compiled_q_sites=3372,compiled_BF_dual_sites=724,
        source_envelope_area_mm2=(3372*64825.596+724*142971.9984)/1e6,
        return_declared_bits=69771008,conditional_return_FF50pct_mm2=69771008*.37908/.5/1e6,
        dualcompute_area_and_RNE_WAKE_context_qualified=False)
    report={'schema':'opentallas.fullmodel.owner.provider-first.v1','candidate':CANDIDATE,'prior_FAIL_commit':PRIOR,
        'capacity_verdict':'PASS_SYMBOLIC_STORAGE_PLACEMENT' if not failures else 'FAIL_CANDIDATE_PLACEMENT',
        'all_matrix_declarations_placed':not failures,'allocation_failures':failures,'compiled_field':field,
        'provider_homes':homes,'used_matrix_stages':sorted(used_stages),'conservation':conservation,
        'stage_stats':stats,'full_allocation_rowtree_root_overlap_gate':overlap,
        'source_pins':V.source_receipts(),'immutable_provider_preallocation_sha256':C.sha((out/'immutable_provider_preallocation.jsonl.gz').read_bytes()),
        'provider_class_and_delivery_binding_limits':['HE/CROM native consumer adapters/ports remain unbound; immutable provider homes can differ from matrix homes.',
            'ECC decode/read sidecar paths have no qualified source implementation.',
            'PHW6 cannot represent fullmodel ownership phases; config ROM storage/fanout/area debit is separate and mandatory.',
            '4778 descriptor-node/rank causal calendars and remote provider delivery have not been composed.',
            'Dedicated Engram tables and head/embed storage preserve complete data; their ports/head compute remain unqualified.'],
        'dedicated_providers':V.dedicated_providers(headers),'minimum_partition_proved':False,
        'golden_order':'Unchanged source row pairs and ordered K subtrees; complete operator/expert triple stage groups monotonically placed. Runtime selection/reduction order never sorted by provider home.',
        'healthy_phase_config_load_cycles':27,'stream_clock_target_GHz':1.2,'serial_chain_clock_target_GHz':0.9,
        'clock_or_latency_measurement_credit':False,'whole_token_cycles':None,
        'payload_bytes_read':0,'new_RTL_builds_PR_or_sims':0,'physical_admission':False,'full_token_admission':False,
        'compiler_sha256':C.sha(Path(__file__).read_bytes()),'dependency_compiler_sha256':C.sha((ROOT/'tools/dsrom_full_owner_compiler.py').read_bytes()),
        'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in
            [INPUTS/'tensor_headers.jsonl.gz',INPUTS/'header_capture.json',INPUTS/'full_product_demand.json.gz']}}
    (out/'model.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'capacity':report['capacity_verdict'],'declared':len(records),'placed':sum(placed.values()),
                      'failed_groups':len(failures),'used_matrix_stages':len(used_stages)}),flush=True)
    return report


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--candidate',type=Path,required=True);args=a.parse_args()
    compile_candidate(C.load_headers(INPUTS/'tensor_headers.jsonl.gz'),json.loads(args.candidate.read_text()),args.out.resolve())
