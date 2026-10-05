#!/usr/bin/env python3
"""Exact phase/descriptor join, known costs and explicit finite calendar obligations.

No arithmetic callback, allocator, RTL, payload, hardware or calibrated token credit.
"""
import argparse, collections, copy, gzip, hashlib, json
from fractions import Fraction
from pathlib import Path
import dsrom_full_product_binding as B
import dsrom_provider_first_event_join as E

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_full_product_binding_20261002'
INPUT=BASE/'inputs/provider_first_622'
MANIFEST_SHA='192c73f0cbe0e349812195bcbcb4384412069b8eaf323eeead3fa0b64b2bf373'
PROJECTION_SHA='aa09cb01ae6da0f3a25863fce7153847513236ce05ea6fb9c52873edda70f9e5'
BUDGET_SHA='821b5c4a8bb2f64c8ecdc4b0f508e8f0b8e704393aba7e6e2e2f5e0d91c14e0d'

def load():
    m=(INPUT/'manifest.json').read_bytes()
    if hashlib.sha256(m).hexdigest()!=MANIFEST_SHA:raise ValueError('phase input manifest changed')
    out={}
    for r in json.loads(m):
        b=(INPUT/r['snapshot']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('exact owner/phase snapshot changed')
        if r['snapshot'].endswith('.jsonl.gz'):out[r['snapshot']]=[json.loads(x) for x in gzip.decompress(b).splitlines()]
        elif r['snapshot'].endswith('.json'):out[r['snapshot']]=json.loads(b)
        else:out[r['snapshot']]=b.decode()
    b=(INPUT/'issue_projection.json.gz').read_bytes()
    if hashlib.sha256(b).hexdigest()!=PROJECTION_SHA:raise ValueError('source issue projection changed')
    out['issue']=json.loads(gzip.decompress(b))
    if out['issue']['source_sha256']!=out['cfg_interface.json']['input_sha256']['results/uarch/dsrom_owner_provider_first_20261002/r1/assignments.jsonl.gz']:raise ValueError('source journal projection currency')
    b=(BASE/'compiled_whole_budget-r6.json').read_bytes()
    if hashlib.sha256(b).hexdigest()!=BUDGET_SHA:raise ValueError('old budget history changed')
    out['budget']=json.loads(b)
    return out

def validate_directories(x):
    interface=x['cfg_interface.json'];phases=x['cfg_phase_directory.jsonl.gz'];keys=x['cfg_key_tables.jsonl.gz']
    if (interface['compiled_NP'],interface['NBF'],interface['PHW'],len(phases),len(keys))!=(4096,724,10,46509,58):raise ValueError('full compiled phase census')
    stages={k['stage']:k for k in keys}
    if set(stages)!=set(range(58)) or any(len(k['words'])!=1024 or k['PHW']!=10 for k in keys):raise ValueError('uniform58 PHW10 tables')
    index={};coordinates=set();counts=collections.Counter();issue=x['issue']['records']
    if len(issue)!=len(phases):raise ValueError('all issue costs required')
    for ordinal,(p,c) in enumerate(zip(phases,issue)):
        s=p['stage'];phase=p['phase'];identity=(p['layer'],p['alias'])
        if identity in index or (s,phase) in coordinates or p['matrix_journal_ordinal']!=ordinal:raise ValueError('duplicate or reordered matrix phase')
        if s not in stages or phase!=counts[s] or phase>=1024:raise ValueError('source ordered phase coordinate')
        if stages[s]['words'][phase]!=p['source_key_word'] or not p['source_key_word']>>31:raise ValueError('phase/key table identity')
        if bool((p['source_key_word']>>30)&1)!=(p['format']=='bf16'):raise ValueError('BF flag key mismatch')
        if p['config_logical_word_range']!=[25*phase,25*(phase+1)]:raise ValueError('exact config word address')
        if any(c[k]!=p[k] for k in ['matrix_journal_ordinal','stage','phase','layer','alias','format']):raise ValueError('source issue cost belongs to different phase')
        if not isinstance(c['issue_cycles_LAT8_condition'],int) or c['issue_cycles_LAT8_condition']<1:raise ValueError('positive source issue cost')
        if c['key']!=(p['source_key_word']&((1<<30)-1)):raise ValueError('typed source key identity')
        index[identity]={**p,'issue_cycles_LAT8_condition':c['issue_cycles_LAT8_condition']}
        counts[s]+=1;coordinates.add((s,phase))
    expected={int(k):v for k,v in interface['actual_phase_counts_by_stage'].items()}
    if dict(counts)!=expected:raise ValueError('source phase counts changed')
    for s,k in stages.items():
        if any(k['words'][counts[s]:]):raise ValueError('unused page valid or freed page credit')
    providers={(p['layer'],p['kind']):p for p in x['cfg_provider_directory.jsonl.gz']}
    if len(providers)!=80 or set(providers)!={(l,k) for l in range(40) for k in ('HE','CROM')}:raise ValueError('all immutable provider homes')
    for (l,k),p in providers.items():
        if p['stage']!=l*58//40 or len(p['pairs'])!=(8 if k=='HE' else 1):raise ValueError('immutable provider home or grain changed')
    ecc=x['cfg_ECC_directory.jsonl.gz']
    if {p['stage'] for p in ecc}!=set(range(58)) or len(ecc)!=58 or any(len(p['pairs'])!=103 for p in ecc):raise ValueError('all58 ECC sidecars')
    return index,providers

def he_address(row,col,K=20480,base=0):
    if not 0<=row<24 or not 0<=col<K:raise ValueError('HE source tensor coordinate')
    q,bank=divmod(col,8);word,lane=divmod(q,8)
    return bank,base+row*((K+63)//64)+word,lane

def he_transpose(K=20480):
    if K%512:raise ValueError('aligned native eight-chunk block required')
    # Native lane(c,l): fn[j*3+l,c*(K/8)+k]. No regrouped arithmetic.
    addresses=[set() for _ in range(8)]
    for k in range(64):
        for j in range(8):
            for l in range(3):
                for c in range(8):
                    bank,word,lane=he_address(j*3+l,c*(K//8)+k,K)
                    addresses[bank].add(word)
    reads=[len(a) for a in addresses]
    if reads!=[192]*8:raise ValueError('actual HCP8 bank demand changed')
    bits=2*24*8*64*32
    return dict(native_word_bits=768,packed_bank_word_bits=256,native_k_block=64,
        native_words_per_block=512,source_unique_reads_per_bank_per_block=reads,
        conditional_one_read_per_bank_stream_cycles_per_block=192,
        native_consumer_serial_cycles_per_block=512,
        native_issue_serial_cycles=K,source_tree_serial_cycles=15,blocks_per_projection=K//512,
        complete_projection_packed_bytes=24*K*4,
        pingpong_buffer_bits=bits,pingpong_buffer_bytes=bits//8,
        pingpong_FF50_area_proxy_mm2=float(Fraction(bits)*Fraction('0.2916')/Fraction('0.5')/1000000),
        cold_prefetch_stream_cycles=192,
        sustain_condition='8 independently qualified bank reads/cycle, bounded ECC/capture/transport and destination ownership; next block ready before its512 serial cycles. No native hr_ready port to absorb a missed deadline.',
        no_change_to_golden_order=True,provider_implemented=False,
        source_formula='pack_he_fp32:bank=col%8,word=row*ceil(K/64)+col//64,lane=(col//8)%8; nativecol=c*(K/8)+k,row=j*3+l')

def phase_identity(p):
    return {k:p[k] for k in ('stage','phase','source_key_word','matrix_journal_ordinal','format','rows_per_rank','K_per_rank','issue_cycles_LAT8_condition')}

def compose(demand,x):
    index,providers=validate_directories(x)
    joined=E.join(demand,x['route.json']);families={};dense_cost=0;expert_min=0;expert_max=0
    for t in joined['templates'].values():
        owner=t['owner'];prefix=t['id'].split('.')[0];layer=int(prefix[1:]) if prefix.startswith('L') and prefix[1:].isdigit() else None
        if owner['kind']=='dense_field':
            p=index[(layer,owner['alias'])]
            if owner['stage']!=p['stage'] or owner['format']!=p['format'] or owner['conditional_LAT8_issue_cycles']!=p['issue_cycles_LAT8_condition']:raise ValueError('dense cost/map export mismatch')
            t['cfg']['exact_phase']=phase_identity(p);dense_cost+=p['issue_cycles_LAT8_condition']
        elif owner['kind']=='runtime_expert_field':
            key=f'L{layer}.{owner["part"]}'
            if key not in families:
                families[key]=[phase_identity(index[(layer,f'exp{eid}.{owner["part"]}')]) for eid in range(384)]
            if any(p['stage']!=int(owner['owner_stage_by_EID'][eid]) for eid,p in enumerate(families[key])):raise ValueError('runtime EID route and phase mismatch')
            t['cfg']['phase_selector_table']=key
            t['cfg']['selected_EID_requires_actual_source_trace']=True
        elif owner['kind']=='HE':
            p=providers[(layer,'HE')]
            if owner['alias'] not in p['aliases'] or owner['stage']!=p['stage']:raise ValueError('HE emitted call provider mismatch')
            t['native_provider_reference']={'layer':layer,'kind':'HE','stage':p['stage'],'pairs':p['pairs'],'alias':owner['alias']}
        else:
            # Exported CROM storage is NOT a frontend port/address translation proof.
            t['native_CROM_binding_if_used']={'layer':layer,'requires_native_address_half_translation':True}
    for layer in range(40):
        costs=[sum(families[f'L{layer}.{part}'][eid]['issue_cycles_LAT8_condition'] for part in ('w1','w3','w2')) for eid in range(384)]
        expert_min+=sum(sorted(costs)[:6]);expert_max+=sum(sorted(costs)[-6:])
    iface=x['cfg_interface.json'];budget=copy.deepcopy(x['budget']['exact_once_area_ledger_mm2'])
    provider=iface['prospective_physical_cfg_provider']
    if provider['prospective_macro_instances']!=28672 or provider['expanded_physical_macro_pin_count']!=2523136:raise ValueError('72bit provider expansion changed')
    # c1037 existing prospective mux term retained once, not packed274 substitution.
    if abs(provider['macro_body_mm2']-68.57156984832)>1e-9:raise ValueError('current72bit cfg body changed')
    if abs(budget['config_prospective_body_plus_local_mux']-(provider['macro_body_mm2']+0.61917364224))>1e-9:raise ValueError('config ledger reconciliation')
    he=he_transpose()
    joined['phase_selector_tables']=families
    joined.update(schema='opentallas.dsrom.phase-calendar-budget-join.v1',phase_selector_tables=families,
        cfg_provider=provider, cfg_decoder_and_visibility_contract=iface['cfg_adapter_required_contract'],
        current_storage_placement_verdict='PASS_SYMBOLIC_STORAGE_PLACEMENT',old24d_failure_record_unchanged=True,
        whole_area_ledger_mm2=budget,
        added_HE_transpose_no_containment_counterfactual_mm2=budget['conservative_no_containment_credit_die_total']+he['pingpong_FF50_area_proxy_mm2'],
        added_HE_transpose_counterfactual_scope='Conditional uniform per-die localHE buffer outside retained service debit; actual containment/provider placement unbound. Not architectural minimum or selected implementation.',
        native_HE_adapter_model=he,
        native_admission_predicates=x['cfg_handoff.json']['native_admission_contract'],
        descriptor_address_and_native_admission=descriptor_patches(demand,joined),
        cfg_delivery_contract=x['cfg_handoff.json']['delivery_contract'],
        known_call_costs=dict(scope='All original call-site templates accepted; actual predicates/selected-EID trace must bind before runtime total. Rank sums are not summed as serial TP4 token latency.',
            field_cfg_calls_per_rank=1149,generic_cfg_cycles_per_call=27,generic_cfg_work_cycles_per_rank=31023,
            dense_LAT8_source_issue_cycles_per_rank=dense_cost,
            actual_selected6_expert_LAT8_source_issue_work_min_per_rank=expert_min,
            actual_selected6_expert_LAT8_source_issue_work_max_per_rank=expert_max,
            HE_default_NL3_IL8_native_issue_serial_cycles_per_rank=80*20480,
            HE_cold_block_prefetch_stream_cycles_if_every_projection_cold=80*192,
            HE_default_source_tree_serial_cycles_per_rank=80*15,
            stage_resident_phases_not_token_calls=True,physical_cfg_27cycle_credit=False),
        finite_calendar_equations=equations(joined),
        exact_cfg_instances_all58x4=iface['all58x4rank_macro_instances_if_uniform_provider'],
        exact_cfg_pins_all58x4=iface['all58x4rank_physical_cfg_pins_if_uniform_provider'],
        cfg_bits_all58x4=58*4*4096*25600*48,
        no_274bit_cfg_provider_credit=True,full_token_cycles_evaluated=False,latency_costs_not_zeroed=True,
        unresolved_costs=['actual predicate/selected6EID trace and executable stage-packet/frontend mapping','positive finite native frontend RF/VM/SU/SFU/INT/attention/index costs and shared resources','cfg72 capture/ECC/generation/fault/delivery fence','HE8bank reads/ECC/capture/transpose deadline and transport plus CROM64 translation','field drain/return visibility, root/context/provider ownership and stage crossing','physical placement, decoded key table fanout/mux and SS/FF clock closure'],
        no_new_partition_selected=True)
    return joined

def descriptor_patches(demand,joined):
    patches=[];failed=[];head_failed=[]
    for n in demand['nodes']:
        f=n.get('instruction',{});t=joined['templates'][n['id']]
        if f.get('unit')==1 and not f.get('me_wsrc',0):
            predicates={'m_xks_eq1':f.get('me_xks',0)==1,'m_xcs_eq_m_k':f.get('me_xcs',0)==f.get('me_k',0),
                'm_xjs_eq0':f.get('me_xjs',0)==0,'m_ots_eqIL8':f.get('me_ots',0)==8,
                'm_ojs_eq1':f.get('me_ojs',0)==1,'m_round':bool(f.get('me_round',0)),
                'not_m_amax':not f.get('me_amax',0),'not_m_mmode':not f.get('me_mmode',0)}
            if not all(predicates.values()):
                target=failed if isinstance(n['scope'],int) else head_failed
                target.append({'node_id':n['id'],'failed_predicates':[k for k,v in predicates.items() if not v],
                    'original_fields':{k:v for k,v in f.items() if k.startswith('me_')},
                    'original_word_sha256':n.get('template_word_sha256'),
                    'must_not_force_round_or_change_reduction_order':True})
        if t['kind']!='field_adapter':continue
        patched=copy.deepcopy(f);o=t['owner']
        if o['kind']=='dense_field':
            p=t['cfg']['exact_phase'];field='me_wbase' if f['unit']==1 else 'qe_wbase'
            changes={field:p['source_key_word']&((1<<30)-1)};owner={'stage':p['stage'],'phase':p['phase'],'key_word':p['source_key_word']}
            if bool((p['source_key_word']>>30)&1)!=(f['unit']==1):raise ValueError('native ME/QE mode not exported phase format')
        else:
            table=joined['phase_selector_tables'][t['cfg']['phase_selector_table']]
            base=table[0]['source_key_word']&((1<<30)-1)
            if any((p['source_key_word']&((1<<30)-1))!=base+eid*4096 for eid,p in enumerate(table)):raise ValueError('source expert key/stride is not affine')
            changes={'qe_wbase':base,'qe_istride':4096};owner={'phase_selector_table':t['cfg']['phase_selector_table'],'stage_and_phase_from_actual_selected_EID':True}
        patched.update(changes)
        # Original encoder emits actual ISA words; address proposal only, never a callback.
        word=B.encode_instruction(patched)
        if any(patched[k]!=v for k,v in f.items() if k not in changes):raise ValueError('address recipe modifies arithmetic/order fields')
        K=f['qe_nb']*32 if f['unit']==3 else f['me_k']*(1<<f.get('me_split',0))
        rows=f['qe_nout'] if f['unit']==3 else f['me_nout']
        patches.append({'node_id':n['id'],'source_node_sha256':B.digest(n),'changes':changes,
            'original_fields':{k:f.get(k) for k in changes},'phase_route':owner,
            'optin_native_ISA_word_hex':hex(word),'optin_word_sha256':B.digest(hex(word)),
            'source_opcode_rounding_and_operand_versions_unchanged':True,
            'input_F32_VM_transport_bytes':K*4,'output_F32_VM_transport_bytes':rows*4,
            'native_transport_and_operand_visibility_not_free':True})
    return {'schema':'opentallas.dsrom.descriptor-key-patches.v1','patch_recipes':patches,
        'patches':len(patches),'runtime_expert_stride_patch_count':sum('qe_istride' in p['changes'] for p in patches),
        'layer_ME_m_ok_failures':failed,'head_ME_m_ok_failures':head_failed,
        'all_native_descriptors_admitted':False,'runtime_image_or_stage_packet_emitted':False,
        'immutable_addresses_not_payloads':True,'physical_and_raw_provider_ABIs_unqualified':True}

def equations(joined):
    """Executable max-plus input DAG. Symbols remain positive, never zero defaults."""
    out=[]
    for e in joined['events']:
        t=joined['templates'][e['template']];o=t['owner'];role=t['kind']
        known=[];symbols=[e['id']+'.accept',e['id']+'.provider_II',e['id']+'.native_service_and_visibility']
        if role=='field_adapter':
            known=[{'domain':'streaming','cycles':27,'term':'generic_source_cfg_only'}]
            if o['kind']=='dense_field':known.append({'domain':'streaming','cycles':t['cfg']['exact_phase']['issue_cycles_LAT8_condition'],'term':'conditional_LAT8_field_issue'})
            else:known.append({'domain':'streaming','phase_selector_table':t['cfg']['phase_selector_table'],'term':'conditional_LAT8_field_issue_actual_EID'})
            resource={'kind':'field_cfg_matrix','scope':'rank','stage':o.get('stage'),'actual_EID_owner_selection_required':o['kind']=='runtime_expert_field','release':'complete'}
        elif role=='HE_adapter':
            known=[{'domain':'serial','cycles':20495,'term':'default_NL3_IL8_nativeHE_issue_plus_source_tree'},{'domain':'streaming','cycles':192,'term':'conditional_cold_transpose_prefetch'}]
            resource={'kind':'HE_bank_transpose_native','scope':'rank','stage':o['stage'],'release':'complete'}
        else:resource={'kind':'collective_ingress' if t['source_unit']==6 else 'native_service','scope':'global' if t['source_unit']==6 else 'requires_actual_provider_scope','provider_binding_required':True,'release':'source_lease_contract_required'}
        out.append({'event':e['id'],'required_positive_symbols':symbols,'known_completion_terms':known,
            'start_max_completion_dependencies':e['required_completion_dependencies'],
            'start_previous_acceptance':e['previous_acceptance'], 'resource':resource,
            'acceptance_distinct_from_completion':True,'TP4_peer_rendezvous_required':t['source_unit']==6,
            'complete_equation':'start + sum(known_terms_ns) + native_service_and_visibility_ns; full cost and resource release must bind before evaluate'})
    return out

def price(joined,bindings,resources,rendezvous):
    """Evaluate only complete positive profiles; no default for any native endpoint."""
    expected={e['id'] for e in joined['events']}
    if set(bindings)!=expected:raise ValueError('complete4778 descriptor/native event profile coverage required')
    for e in joined['events']:
        b=bindings[e['id']];t=joined['templates'][e['template']]
        faults=joined.get('descriptor_address_and_native_admission',{}).get('layer_ME_m_ok_failures',[])+joined.get('descriptor_address_and_native_admission',{}).get('head_ME_m_ok_failures',[])
        if any(f['node_id']==e['template'] for f in faults) and not b.get('native_admission_repair_receipts'):
            raise ValueError('original native m_ok refusal requires exact ordered native repair receipt')
        if b.get('latency_evidence_kind') not in ('provisional','source_model','measured') or not b.get('cost_assumption_receipts'):
            raise ValueError('explicit finite positive latency evidence required')
        if not b.get('frontend_or_transport_owner_receipts'):
            raise ValueError('parent/frontend readiness and transport ownership cannot be free')
        extra=Fraction(str(b.get('native_service_and_visibility_ns',0)))
        if extra<=0:raise ValueError('missing native service/capture/visibility cannot be zero')
        period=B.validate_calendar(b['calendar']);minimum=extra
        if t['kind']=='field_adapter':
            if t['owner']['kind']=='runtime_expert_field':
                eid=b.get('selected_EID')
                if not isinstance(eid,int) or isinstance(eid,bool) or not 0<=eid<384:raise ValueError('source selected EID required')
                p=joined['phase_selector_tables'][t['cfg']['phase_selector_table']][eid]
            else:p=t['cfg']['exact_phase']
            expected_phase={k:p[k] for k in ('stage','phase','source_key_word','matrix_journal_ordinal')}
            if b.get('cfg_phase_identity')!=expected_phase or not b.get('cfg_delivery_fence_receipts'):
                raise ValueError('exact exported phase and actual cfg delivery fence required')
            if b.get('owner_stage')!=p['stage']:raise ValueError('actual selected phase owner changed')
            minimum+=Fraction(27+p['issue_cycles_LAT8_condition'])*Fraction(5,6)
        elif t['kind']=='HE_adapter':
            if b.get('native_HE_dimensions')!={'NL':3,'IL':8,'S':8,'K':20480}:
                raise ValueError('default nativeHE profile requires source-exact dimensions')
            if not b.get('HE_adapter_bank_deadline_receipts'):raise ValueError('nonbackpressured HE adapter deadline proof required')
            minimum+=Fraction(20495)*Fraction(10,9)+Fraction(192)*Fraction(5,6)
        if b['calendar']['complete_cycles']*period<minimum:raise ValueError('calendar below cfg/actualphase/native issue and positive endpoint cost')
    return E.price(joined,bindings,resources,rendezvous)

def project_issue(out):
    import subprocess,tempfile
    rev='622dbc897fd5ecb5a5b691e1ae39bea0ad751524'
    source='results/uarch/dsrom_owner_provider_first_20261002/r1/assignments.jsonl.gz'
    with tempfile.TemporaryFile() as f:
        subprocess.run(['git','show',rev+':'+source],stdout=f,cwd=ROOT,check=True)
        f.seek(0);h=hashlib.sha256()
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
        digest=h.hexdigest()
        if digest!='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f':raise ValueError('source journal changed')
        f.seek(0);rows=[];counts=collections.Counter()
        with gzip.GzipFile(fileobj=f) as z:
            for i,line in enumerate(z):
                m=json.loads(line);stage=m['stage'];phase=counts[stage];counts[stage]+=1
                rows.append(dict(matrix_journal_ordinal=i,stage=stage,phase=phase,layer=m['layer'],alias=m['alias'],format=m['format'],key=m['key'],issue_cycles_LAT8_condition=m['issue_cycles_LAT8_condition']))
    r=dict(source_commit=rev,source_path=source,source_sha256=digest,projection='Copies issue_cycles_LAT8_condition; no allocator/readback/repacking/arithmetic execution.',records=rows)
    b=gzip.compress((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    if hashlib.sha256(b).hexdigest()!=PROJECTION_SHA:raise ValueError('cost projection replay mismatch')
    with out.open('xb') as f:f.write(b)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--demand',type=Path,default=BASE/'demand-r7.json.gz');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--project-issue',action='store_true');a=ap.parse_args()
    if a.project_issue:project_issue(a.out);return
    raw=a.demand.read_bytes();d=json.loads(gzip.decompress(raw));x=compose(d,load())
    x['input_demand_sha256']=hashlib.sha256(raw).hexdigest();x['compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['owner_trace_compiler_sha256']=hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest();x['input_manifest_sha256']=MANIFEST_SHA;x['issue_projection_sha256']=PROJECTION_SHA
    b=(json.dumps(x,sort_keys=True,indent=2)+'\n').encode();a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.suffix=='.gz':b=gzip.compress(b,mtime=0)
    with a.out.open('xb') as f:f.write(b)
    print(json.dumps({'census':x['census'],'known_call_costs':x['known_call_costs'],'whole_area':x['whole_area_ledger_mm2']['conservative_no_containment_credit_die_total'],'build_admitted':False},sort_keys=True))
if __name__=='__main__':main()
