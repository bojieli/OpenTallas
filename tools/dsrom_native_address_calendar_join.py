#!/usr/bin/env python3
"""Consume authoritative native address compiler receipts in retained calendar/model.

No address re-emitter, allocator, arithmetic callback or hardware execution.
"""
import argparse,collections,copy,gzip,hashlib,json
from pathlib import Path
import dsrom_phase_calendar_binding as C

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_full_product_binding_20261002'
INPUT=BASE/'inputs/native_address_d660'
MANIFEST_SHA='a93c363857a802cfa241a8a18932a8c6cfc94e90bdd054b0738e61fc836d03fb'
PRIOR_SHA='634c98a8ab64ecf4fd590b96ad9d1c5b2b7f17770b5b6ca3da0c72cd29a0be29'

def load():
    raw=(INPUT/'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('native input manifest changed')
    data={};receipts=json.loads(raw)
    for p in receipts:
        b=(INPUT/p['snapshot']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=p['sha256']:raise ValueError('native compiler snapshot changed')
        if p['snapshot'].endswith('.jsonl.gz'):data[p['snapshot']]=[json.loads(x) for x in gzip.decompress(b).splitlines()]
        elif p['snapshot'].endswith('.json'):data[p['snapshot']]=json.loads(b)
        else:data[p['snapshot']]=b.decode()
    raw=(BASE/'provider_first_composed-r4.json.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PRIOR_SHA:raise ValueError('retained phase/calendar baseline changed')
    data['prior']=json.loads(gzip.decompress(raw));data['receipts']=receipts
    return data

def join(x):
    result=copy.deepcopy(x['prior']);model=x['model.json'];bindings=x['node_bindings.jsonl.gz']
    source=''.join(x['ot_v41_rom_adapt.sv'].split())
    if 'if(!hit)fault<=1\'b1;' not in source or 'st<=S_GO;' not in source:raise ValueError('source fault/control path changed; re-audit entry gating')
    if model['candidate']!=result['candidate'] or model['native_instructions']!=4778:raise ValueError('same candidate native instruction census')
    bynode={b['node']:b for b in bindings}
    if len(bynode)!=4887 or set(bynode)!=set(result['templates']):raise ValueError('all native/nonweight node IDs required')
    counts=collections.Counter(b['classification'] for b in bindings)
    if dict(counts)!=model['classification'] or counts['WEIGHT_PHASE']!=1149 or counts['UNBOUND_DEDICATED_HEAD']!=1:raise ValueError('weight/nonweight/head class coverage')
    words={p['node']:p for p in x['patched_weight_words.jsonl.gz']}
    oldrecipes={p['node_id']:p for p in result['descriptor_address_and_native_admission']['patch_recipes']}
    if set(words)!=set(oldrecipes):raise ValueError('all authoritative patched weight words required')
    native_faults={n['node']:n['failures'] for n in model['native_admission_failures']}
    prior_faults=result['descriptor_address_and_native_admission']['layer_ME_m_ok_failures']+result['descriptor_address_and_native_admission']['head_ME_m_ok_failures']
    if set(native_faults)!={p['node_id'] for p in prior_faults}:raise ValueError('native failures changed or dropped')
    address_by_ordinal={p['matrix_journal_ordinal']:p for p in x['physical_address_boundaries.jsonl.gz']}
    if set(address_by_ordinal)!=set(range(46509)):raise ValueError('all source physical-address ordinals required')
    choice_matches=0;seen_ordinals=set();words_checked=0;runtime=0
    for node,t in result['templates'].items():
        b=bynode[node]
        if b['classification']!='NOT_WEIGHT_PHASE' and b['source_node_semantic_sha256']!=t['node_sha256']:raise ValueError('retained demand semantic hash changed')
        if b['classification']=='WEIGHT_PHASE':
            recipe=oldrecipes[node]
            changes={k:v['new'] for k,v in b['address_patches'].items()}
            if changes!=recipe['changes'] or any(b['address_patches'][k]['old']!=recipe['original_fields'][k] for k in changes):raise ValueError('authoritative patch disagrees with retained phase audit')
            if int(words[node]['word_hex'],16)!=int(recipe['optin_native_ISA_word_hex'],16):raise ValueError('native patched ISA word mismatch')
            words_checked+=1
            if t['owner']['kind']=='runtime_expert_field':
                expected=result['phase_selector_tables'][t['cfg']['phase_selector_table']];runtime+=1
                if b['selector_VM_element_address']!=t['owner']['source_EID_VM_address'] or b['selector_slot'] is None:raise ValueError('actual indexed VM read path changed')
                if [p['expert'] for p in b['phase_choices']]!=list(range(384)):raise ValueError('all384 runtime alternatives in actual EID order required')
            else:
                expected=[t['cfg']['exact_phase']]
                if b['selector_slot'] is not None:raise ValueError('dense descriptor acquired runtime selector')
            if len(expected)!=len(b['phase_choices']):raise ValueError('phase choice coverage')
            for p,q in zip(expected,b['phase_choices']):
                if any(q[k]!=p[k] for k in ('stage','phase','source_key_word','matrix_journal_ordinal')):raise ValueError('compiler/phase directory identity mismatch')
                a=address_by_ordinal[q['matrix_journal_ordinal']]
                if (a['stage'],a['phase'],a['layer'],a['alias'])!=(q['stage'],q['phase'],b['layer'],q['alias']):raise ValueError('code/scale/ECC address provider belongs to different phase')
                seen_ordinals.add(q['matrix_journal_ordinal']);choice_matches+=1
            t['authoritative_native_address_binding']={'node':node,'input_snapshot':'node_bindings.jsonl.gz',
                'kind':b['kind'],'selector_VM_element_address':b['selector_VM_element_address'],'selector_slot':b['selector_slot'],
                'address_patches':b['address_patches'],'consumer_X_FP32_VM_elements':b['consumer_X_FP32_VM_elements'],
                'consumer_output_base_elements':b['consumer_output_base_elements'],'output_format':b['output_format'],
                'physical_address_lookup':'physical_address_boundaries.jsonl.gz by exact matrix_journal_ordinal; full API remains owned by d66047e51',
                'actual_stage_dispatch_implemented':False,'native_admission_failures':b['native_admission_failures']}
        else:
            t['authoritative_native_classification']=b['classification']
            if b['classification']=='UNBOUND_DEDICATED_HEAD':t['dedicated_head_provider_unbound']=True
    if seen_ordinals!=set(range(46509)):raise ValueError('full model phase coverage lost')
    # Consume producer outputs; no re-encoding or reconstruction of any address.
    result['descriptor_address_and_native_admission']={
        'authoritative_commit':'d66047e514a280b53be6d8a181d9930d9bc6d052','model':model,
        'previous_partial_recipe_compiler_superseded_for_future_joins':True,
        'patched_weight_word_snapshot':'patched_weight_words.jsonl.gz','node_bindings_snapshot':'node_bindings.jsonl.gz',
        'physical_address_snapshot':'physical_address_boundaries.jsonl.gz',
        'all_native_descriptors_admitted':False}
    result['native_address_join_census']={'native_instructions':4778,'weight_descriptors':1150,'layer_weights_bound':1149,
        'QE':1010,'ME':140,'nonweight_and_runtime_nodes':3737,'head_unbound':1,'unique_physical_phase_ordinals':len(seen_ordinals),
        'actual_runtime_indexed_calls':runtime,'existing_words_validated_without_encoder':words_checked,'phase_choice_matches':choice_matches}
    result['native_entry_control_gate']={'source_bad_EID_guard_present':False,
        'fault_does_not_suppress_S_LOOK_to_S_GO':True,'source_inspection_only_no_measured_fault_execution':True,
        'must_reject_before_any_cfg_or_field_side_effect':['EID outside0..383','native predicate failure','missing or mismatched phase key','stale/reset generation','cfg poison/missing good word/act fence'],
        'required_source_receipts':['entry_refusal_before_GO','generation_lease_and_fault_drain','actual_selected_EID_VM_read','provider_word_delivery_and_consumer_visibility'],
        'software_API_checked_is_not_native_refusal_qualification':True,
        'extra_control_area_and_latency_not_inferred_free':True}
    result['schema']='opentallas.dsrom.native-address-calendar-budget-join.v1'
    result['input_native_receipts']=x['receipts'];result['prior_record_sha256']=PRIOR_SHA
    result['address_compiler_or_allocator_rerun']=False
    result['unresolved_costs']+=['Native entry refusal/kill and generation drain, with missing key and bad EID gating before S_GO',
        'Dedicated head provider/shape/address and argmax/native rounding implementation']
    result['schedule_costs_complete']=False;result['build_admitted']=False
    return result

def price(joined,bindings,resources,rendezvous):
    """Native-calendar refusal/lease constraints augment existing finite solver."""
    if set(bindings)!={e['id'] for e in joined['events']}:raise ValueError('all finite native endpoint profiles required')
    faults={f['node'] for f in joined['descriptor_address_and_native_admission']['model']['native_admission_failures']}
    for e in joined['events']:
        t=joined['templates'][e['template']];b=bindings[e['id']]
        if e['template'] in faults and not b.get('native_admission_repair_receipts'):raise ValueError('native rounding/mode/argmax repair unbound')
        if t.get('dedicated_head_provider_unbound') and not b.get('dedicated_head_provider_receipts'):raise ValueError('dedicated head provider cannot inherit layer phase')
        if t['kind']=='field_adapter':
            for key in ('entry_refusal_before_GO_receipts','generation_lease_and_fault_drain_receipts','code_scale_ECC_delivery_receipts','root_and_consumer_visibility_receipts'):
                if not b.get(key):raise ValueError('native field endpoint constraint unbound: '+key)
            a=t['authoritative_native_address_binding']
            if a['selector_slot'] is not None:
                if not b.get('actual_selected_EID_VM_read_receipts') or b.get('selector_VM_element_address')!=a['selector_VM_element_address']:raise ValueError('actual source indexed VM acceptance path unbound')
    return C.price(joined,bindings,resources,rendezvous)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    x=join(load());x['compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    data=(json.dumps(x,sort_keys=True,indent=2)+'\n').encode();a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.suffix=='.gz':data=gzip.compress(data,mtime=0)
    with a.out.open('xb') as f:f.write(data)
    print(json.dumps({'census':x['native_address_join_census'],'fit_mm2':x['whole_area_ledger_mm2']['conservative_no_containment_credit_die_total'],'full_token_or_build_admitted':False},sort_keys=True))
if __name__=='__main__':main()
