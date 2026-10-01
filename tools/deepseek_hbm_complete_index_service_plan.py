"""Unadmitted ordinary-GPU authority/service plan and executed local phase traces.

IKD1 stays byte-identical. External producer/read leases are a proposed service
contract, never source timestamps, host-hash GPU credit or a payload rewrite.
"""
from pathlib import Path
from types import FunctionType,SimpleNamespace
import hashlib,json,gzip
import deepseek_hbm_complete_index_consumer as Consumer
import numpy as np
import deepseek_hbm_complete_index_fused as F
import deepseek_hbm_complete_index_fused_model as FM
import deepseek_hbm_complete_index_blas_model as BM
import deepseek_hbm_complete_index_exceptional as E
X=F.X;B=F.B;ins=X.K.ins
ROOT=Path(__file__).resolve().parents[1]

def authority_program():
    # Descriptor8 words incl mandatory zero padding; external record16 words.
    # Independent expected words originate in protected scheduler/owner context.
    p=[ins('MOV','difference',0)]
    for family,count in [('descriptor',8),('external_lease',16)]:
        for word in range(count):
            p += [ins('LOAD','actual',f'{family}{word}'),ins('LOAD','expected',f'protected_expected_{family}{word}'),
                  ins('XOR','mismatch','actual','expected'),ins('OR','difference','difference','mismatch')]
    for shift in [16,8,4,2,1]:
        p += [{'op':'SHFL','dst':'other','src':['difference'],'offset':shift},ins('OR','difference','difference','other')]
    return p+[{**ins('STORE','authority_difference','difference'),'predicate_stride':32}]

def authority_execute(memory,trace=False):
    p=authority_program();runner=E.TracedSIMT((1,32),memory,kernel='authority_metadata') if trace else X.SIMT((1,32),memory)
    runner.run(p[:1])
    runner.run(p[1:-11],np.arange(32)[None,:]<2)
    runner.run(p[-11:])
    return runner

def plan():
    current=FM.model();fallback,extent=BM.layout(2)
    # One arena, no overlap/alias. Retain exact currentquery across branch.
    # Fallback arena already holds rawquery/weights/provider buffers. Additional
    # cache/guard/authority arenas cannot silently alias its temporary banks.
    extra=[('cached_fullquery_units',16896),('cached_fullquery_scales',512),
        ('query_guard_flags',512),('query_guard_pingpong',128),('key_guard_flags',32),
        ('key_guard_pingpong',128),('authority_record_and_expected',2*24*4*2),
        ('authority_result',128),('ABI_input',128),('ABI_output',256)]
    cursor=extent;regions=[]
    for name,size in extra:
        cursor=(cursor+255)//256*256;regions.append({'name':name,'base':cursor,'bytes':size});cursor+=size
    source=[Path(__file__),Path(F.__file__),Path(FM.__file__),Path(B.__file__),Path(BM.__file__),Path(E.__file__),
            Path(X.__file__),Path(F.C.__file__),Path(X.K.__file__),Path(X.L.__file__),Path(F.C.V.__file__),Path(F.C.G.__file__),Path(Consumer.__file__)]
    phases=[
        {'id':'producer_result','requires':['actual_source_program_op_and_result_id'], 'writes':['payload','decoded_class_flags'], 'service_cycles':None},
        {'id':'payload_WRcommit','requires':['producer_result','controller_actual_WRACK'], 'writes':['protected_payload_visible'], 'service_cycles':None},
        {'id':'IKD1_WRcommit','requires':['payload_WRcommit','controller_actual_descriptor_WRACK'], 'writes':['published_epoch'], 'service_cycles':None},
        {'id':'ACK_reverse_CDC','requires':['IKD1_WRcommit','captured_ACK','common36_bothdie_drain'], 'writes':['owner_lease_ready'], 'service_cycles':None},
        {'id':'lease_acquire','requires':['owner_lease_ready','immutable_provider_record','independent_expected_owner_context'], 'writes':['consumer_read_lease'], 'service_cycles':None},
        {'id':'authority_compare','requires':['lease_acquire','metadata_return_visible'], 'writes':['authority_difference'], 'shared_warp_issues_local2':49,'service_cycles':None},
        {'id':'decoded_query_key_guard','requires':['authority_compare_zero','decoded_bytes_visible'], 'writes':['actual_finite_route'], 'service_cycles':None},
        {'id':'query_prepare','requires':['actual_query_version','query_guard'], 'writes':['cached_fullquery_units','cached_fullquery_scales'], 'shared_issues_per_SM_per_call':913,'service_cycles':None},
        {'id':'finite_path','requires':['actual_finite_route','query_prepare','key_decoder_visible'], 'reads':['cached_fullquery_units','cached_fullquery_scales','keys','key_units','key_exponents','weights'], 'shared_issues_known_local2':945,'service_cycles':None},
        {'id':'exceptional_path','requires':['actual_nonfinite_route','current_query_raw_visible','key_raw_visible'], 'reads':['query','keys','weights'], 'writes':list(fallback), 'kernel_count':36,'service_cycles':None},
        {'id':'ABI_and_output_commit','requires':['selected_path_head_ready','ordinary_ABI_writeback','actual_output_WRACK'], 'writes':['F64_storage_ABI_scores'], 'service_cycles':None},
        {'id':'consumer_done','requires':['every_phase_last_read','every_phase_write_visible','ABI_and_output_commit'], 'writes':['last_consumer_done'], 'service_cycles':None},
        {'id':'credit_return_and_reuse','requires':['consumer_done','reverse_CDC_credit','common36_bothdie_drain'], 'writes':['next_epoch_may_publish'], 'service_cycles':None}]
    # No favorable finite/nonfinite frequency is assumed. State scenarios are
    # distinct branches, not an average/historical token clock.
    return {'schema':'w19 source-composed index service proposal r1','source_pins':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
        'wire':'IKD1 unchanged <4sBBHQ magic/format/flags0/lengthLE16/epochLE64 +16zero pad; fmt1/68B orfmt2/512B',
        'external_record_NOT_wire_extension':['producer_graphop_result_id','source_program_SHA256','owner_rank','global_key_id','physical_base_stack_PC','generation_epoch','actual_decoded_class_flags','payload_WRvisible','descriptor_WRvisible','ACKcaptured_reverseCDC','consumer_leases','phase_firstwrite_lastread','consumer_done','creditreturn'],
        'external_record_word_layout_and_protected_owner_provider_pins':None,
        'authority_program':authority_program(),'authority_masks':'difference initialized all32; descriptor/context loads+compares only2 owned key lanes; SHFL/OR all32; STORE lane0','authority_cost':{'shared_warp_issues_local2':49,'metadata_requested_full_warp_slot_bytes':49*128,'comparisons':24,'metadata_words_read':48,'source_of_expected_words':'independent protected owner/scheduler context, NEVER supplied cache metadata','physical_owner_context_read_and_lease_service_cycles':None,'acceptance_only_if_OR_difference_zero':True},
        'shared_issues_known_SM0_with_49_metadata_issues_each_invocation':current['finite_SM0_shared_issue_count_known_obligations']+1113*49+8*49,
        'does_NOT_price_all_provider_RF_opII_or_authority_routes':True,
        'lifetimes':phases,'fallback_local2_nonalias_regions':fallback,'fallback_arena_bytes':extent,
        'retained_query_authority_extra_regions':regions,'composed_nonalias_extent_bytes':cursor,'capacity_fits_64KiB_only':cursor<=65536,
        'fallback_full64_eager_extent_bytes':BM.layout(64)[1],'fallback_full64_eager_live_bytes':BM.peak_live(64)[1],
        'no_optional_alias_or_timer_release':True,
        'packed_key_reuse_model_only':{'source':'actual same-invocation quantize_pack output; not inversepacking and no fabricated initialState provenance',
            'producer_scope':'finite raw input can produce decoded Inf253; raw nonfinite needs preserved format2 actual decodedbits',
            'guard_rule':'actual producer decodedbit classification, held by same immutable epoch/readlease; tag1 is NOT finite',
            'candidate_key_codes':'twiceE2M1 u(code); source UE8 exponent byte-127. No altered BF16/zero/Inf/NaN rounding',
            'ordinary_mapping_cost_per_term':'SHR/AND to extract nibble, AND magnitude, signed BLT mag4; else AND+IADD+SHR+ISUB+SHL; sign AND/SHR plus conditional ISUB. No native table.',
            'hoisted_key_payload_word_LOADs_per_key':17,'query_unit_and_scale_LOADs_per_key':132,'weight_LOADs_per_key':1,'result_STOREs_per_key':1,
            'shader_shared_issues_local2_candidate':302,'known_ABI_handoff_shared_issues_local2':11,
            'producer_classflag_handoff_and_route_shared_issues_local2_candidate':2,
            'consumer_shared_issues_local2_candidate_excluding_authority_provider':315,
            'producer_quantize_pack_decode_and_flag_stores_charged_once_per_key':None,
            'integer_opcode_RF_shift_branch_ports_cycles':None,'initial_KV_fixture_packed_provenance_coverage':None,
            'wholeprogram_all_keys_packed_claim':False,'adopted':False,'bounded_implementation_authorized_by_this_model':False},
        'actual_timestamps':None,'hardware_admitted':False,'actual_token_rate':None,'wholejoin_owner':'Boyle','RTL_written':False}


def fixture_inputs(kind='ones-r1'):
    if kind=='ones-r1':return np.ones((32,128),np.float32),np.ones((2,128),np.float32),np.ones(32,np.float32)
    if kind!='diverse-r2':raise ValueError('unknown retained fixture')
    rng=np.random.default_rng(20261002)
    lattice=np.array([0,.5,-.5,1,-1,1.5,-1.5,2,-2,3,-3,4,-4,6,-6],np.float32)
    exponents=[-126,-80,-20,-3,0,3,16,32]
    qraw=np.empty((32,128),np.float32);kraw=np.empty((2,128),np.float32)
    for head in range(32):
        for block in range(4):
            terms=rng.choice(lattice,32);terms[(head+block*3)%32]=6
            qraw[head,block*32:(block+1)*32]=(terms.astype(np.float64)*2.**exponents[(head*3+block*5)%8]).astype(np.float32)
    for key in range(2):
        for block in range(4):
            terms=rng.choice(lattice,32);terms[(key*7+block*11)%32]=6
            exponent=[[-7,1,-2,8],[3,-5,4,-1]][key][block]
            kraw[key,block*32:(block+1)*32]=(terms.astype(np.float64)*2.**exponent).astype(np.float32)
    return qraw,kraw,np.linspace(-2.25,3.75,32,dtype=np.float32)

def fixture_decoded(qraw,kraw):
    return np.stack([F.C.V.qdq_fp4_e8m0(row) for row in qraw]),np.stack([F.C.V.qdq_fp4_e8m0(row) for row in kraw])

def traces(fixture='ones-r1'):
    """Execute all current local phases; no global module mutation or source edit."""
    runs=[];counter=iter(range(10000))
    def make(shape,memory,initial=None):
        initial={} if initial is None else initial
        m=E.TracedSIMT(shape,{**memory,**{'external_'+k:v for k,v in initial.items()}},kernel=f'phase{next(counter)}')
        # Explicit seedLOADs expose historical source scale handoff, not free RF.
        if initial:m.run([ins('LOAD',k,'external_'+k) for k in initial])
        runs.append(m);return m
    proxy=SimpleNamespace(**{k:v for k,v in vars(X).items() if not k.startswith('__')});proxy.SIMT=make
    proxy.decode=FunctionType(X.decode.__code__,{**X.decode.__globals__,'SIMT':make})
    proxy.block=FunctionType(X.block.__code__,{**X.block.__globals__,'SIMT':make})
    classify=FunctionType(F.classified.__code__,{**F.classified.__globals__,'X':proxy})
    qraw,kraw,weights=fixture_inputs(fixture);q,keys=fixture_decoded(qraw,kraw)
    initial_q=q.copy();initial_keys=keys.copy()
    with np.errstate(over='ignore',invalid='ignore'):
        finite_expected=Consumer.reference_scores(q,keys[np.arange(5456)%2],weights,np.arange(5456))[:2]
    classify(q);classify(keys)
    query_decoders=[proxy.decode(q[:,b*32:(b+1)*32]) for b in range(4)]
    for _,_,runner in query_decoders:
        runner.run([ins('STORE','scale','e')]);runner.trace[-1]['lowerer_added_scale_STORE_bridge']=True
    # Masked key decoder identical to published finite path,2 real rows only.
    def masked(shape,memory,initial=None):
        m=make(shape,memory,initial);original=m.run
        def run(program,active=None,path=()):
            owned=np.arange(shape[0]*32).reshape(shape)<2
            return original(program,owned if active is None else active&owned,path)
        m.run=run;return m
    decode=FunctionType(X.decode.__code__,{**X.decode.__globals__,'SIMT':masked})
    kd=[decode(keys[:,b*32:(b+1)*32]) for b in range(4)]
    for _,_,runner in kd:
        runner.run([ins('STORE','scale','e')]);runner.trace[-1]['lowerer_added_scale_STORE_bridge']=True
    # Build the exact published shader inputs from these executed decoders.
    memory={'weights':weights[None,:].view(np.uint32)}
    for b in range(4):
        qu,qe,_=query_decoders[b];ku,ke,_=kd[b]
        memory.update({f'q{b}_{j}':qu[:,j][None,:].view(np.uint32) for j in range(32)})
        memory.update({f'k{b}_{j}':ku[:,j,None].view(np.uint32) for j in range(32)})
        memory[f'eq{b}']=qe[None,:].view(np.uint32);memory[f'ek{b}']=ke[:,None].view(np.uint32)
    finite=make((2,32),memory).run(F.program());finite_output=finite.stores['final'][:,0].tolist()
    finite_runs=len(runs)
    def result_event(runner,symbol,lane):
        return next(event['id'] for event in reversed(runner.trace) if event.get('dst')==symbol and event['opcode']=='STORE' and any(lane in v['lanes'] for v in event['active_lanes']))
    for event in finite.trace:
        if event['opcode']!='LOAD':continue
        symbol=event['src'][0];bindings=[]
        if symbol.startswith(('q','k')) and '_' in symbol:
            family=symbol[0];b,j=map(int,symbol[1:].split('_'));producer=(query_decoders if family=='q' else kd)[b][2]
            for mask in event['active_lanes']:
                for lane in mask['lanes']:
                    pl=lane if family=='q' else mask['warp']
                    bindings.append({'consumer_warp':mask['warp'],'consumer_lane':lane,'producer_event':result_event(producer,'unit'+str(j),pl),'producer_warp':0,'producer_lane':pl,'producer_STORE_visibility_cycle':None})
        elif symbol.startswith(('eq','ek')):
            family=symbol[1];b=int(symbol[2:]);producer=(query_decoders if family=='q' else kd)[b][2]
            for mask in event['active_lanes']:
                for lane in mask['lanes']:
                    pl=lane if family=='q' else mask['warp'];ordinal=int(producer.writers['e'][0,pl])
                    bindings.append({'consumer_warp':mask['warp'],'consumer_lane':lane,'producer_event':f'{producer.kernel}:{ordinal}','producer_register':'e','producer_warp':0,'producer_lane':pl,'mandatory_scale_STORE_bridge_event':result_event(producer,'scale',pl),'producer_STORE_visibility_cycle':None})
        event['crossphase_shared_producer_bindings']=bindings
    sanitize=FunctionType(B.sanitize.__code__,{**B.sanitize.__globals__,'X':proxy})
    binary=FunctionType(B.binary.__code__,{**B.binary.__globals__,'X':proxy})
    fallback=FunctionType(B.source_sized_scores.__code__,{**B.source_sized_scores.__globals__,'X':proxy,'sanitize':sanitize,'binary':binary})
    # Only selected source heads/blocks become exceptional in diverse-r2.
    if fixture=='ones-r1':
        raw=np.ones(128,np.float32);raw[0]=np.nan
        with np.errstate(over='ignore',invalid='ignore'):q=np.tile(F.C.V.qdq_fp4_e8m0(raw),(32,1))
        raw[0]=np.inf
        with np.errstate(over='ignore',invalid='ignore'):keys[1]=F.C.V.qdq_fp4_e8m0(raw)
    else:
        fallback_qraw=qraw.copy();fallback_kraw=kraw.copy()
        fallback_qraw[3,32+5]=np.nan;fallback_qraw[17,96+7]=np.inf
        fallback_kraw[1,64+11]=np.inf
        with np.errstate(over='ignore',invalid='ignore'):q,keys=fixture_decoded(fallback_qraw,fallback_kraw)
    fallback_out,_=fallback(q,keys,weights,5456)
    with np.errstate(over='ignore',invalid='ignore'):
        expected=Consumer.reference_scores(q,keys[np.arange(5456)%2],weights,np.arange(5456))[:2]
    if not np.array_equal(fallback_out.astype(np.float64).view(np.uint64),expected.view(np.uint64)):raise AssertionError('traced exceptional path differs from original fullmacro source')
    if not np.array_equal(np.array(finite_output,np.uint32).view(np.float32).astype(np.float64).view(np.uint64),finite_expected.view(np.uint64)):raise AssertionError('finite currentproduced source mismatch')
    proposal=plan();base=lambda n:proposal['fallback_local2_nonalias_regions'][n]['base']
    extra={r['name']:r['base'] for r in proposal['retained_query_authority_extra_regions']}
    def addresses(phase,symbol,warp,lane,store):
        if phase==0:
            return extra['query_guard_flags']+warp*4 if store else base('query')+4*((warp%4*32+lane)*33+warp//4)
        if phase in [1,2]:
            src,dst=('query_guard_flags','query_guard_pingpong') if phase==1 else ('query_guard_pingpong','query_guard_flags')
            return extra[dst]+warp*4 if store else extra[src]+4*(warp*32+lane)
        if phase==3:
            return extra['key_guard_flags']+warp*4 if store else base('keys')+4*((warp//4)*128+(warp%4)*32+lane)
        if phase==4:return extra['key_guard_pingpong']+warp*4 if store else extra['key_guard_flags']+4*lane
        if 5<=phase<=8:
            b=phase-5
            if symbol=='scale':return extra['cached_fullquery_scales']+4*(b*32+lane)
            j=int(symbol[4:] if store else symbol[1:])
            return extra['cached_fullquery_units']+4*((b*32+j)*33+lane) if store else base('query')+4*((b*32+j)*33+lane)
        if 9<=phase<=12:
            b=phase-9
            if symbol=='scale':return base('k_exp')+4*(b*2+lane)
            j=int(symbol[4:] if store else symbol[1:])
            return base('k_units')+4*(b*2*33+lane*33+j) if store else base('keys')+4*(lane*128+b*32+j)
        if phase==13:
            if store:return base('head_reduction')+4*(warp*32+lane)
            if symbol=='weights':return base('weights')+4*lane
            if symbol.startswith('eq'):return extra['cached_fullquery_scales']+4*(int(symbol[2:])*32+lane)
            if symbol.startswith('ek'):return base('k_exp')+4*(int(symbol[2:])*2+warp)
            family=symbol[0];b,j=map(int,symbol[1:].split('_'))
            return extra['cached_fullquery_units']+4*((b*32+j)*33+lane) if family=='q' else base('k_units')+4*(b*2*33+warp*33+j)
        return None
    endpoint_ledger={}
    for phase,runner in enumerate(runs[:finite_runs]):
        for event in runner.trace:
            if event['opcode'] not in ['LOAD','STORE']:continue
            store=event['opcode']=='STORE';symbol=event['dst'] if store else event['src'][0]
            mapped=[]
            for mask in event['active_lanes']:
                for lane in mask['lanes']:
                    addr=addresses(phase,symbol,mask['warp'],lane,store)
                    mapped.append({'warp':mask['warp'],'lane':lane,'address':addr,'bytes':4})
                    key=str(addr);entry=endpoint_ledger.setdefault(key,{'firstwrite':None,'lastread':None,'lastwrite':None})
                    if store:
                        if entry['firstwrite'] is None:entry['firstwrite']=event['id']
                        entry['lastwrite']=event['id']
                    else:entry['lastread']=event['id']
            event['source_mapped_shared_accesses']=mapped
            event['mapping_kind']='proposal byteaddresses, NOT provider placement/timestamps'
    validation=validate_mapped_values(runs[:finite_runs],proposal,initial_q,initial_keys,weights)
    return {'fixture':fixture+' synthetic actualQDQ32queries/2keys; production5456 macro policy, not checkpoint',
        'fixture_source_bits':{'query_raw_F32_bits':qraw.view(np.uint32).tolist(),'key_raw_F32_bits':kraw.view(np.uint32).tolist(),'initial_decoded_query_bits':initial_q.view(np.uint32).tolist(),'initial_decoded_key_bits':initial_keys.view(np.uint32).tolist(),'weights_F32_bits':weights.view(np.uint32).tolist()},
        'fallback_query_nonfinite_head_count':int(np.any(~np.isfinite(q),axis=1).sum()),
        'fallback_query_nonfinite_block_count':int(np.any(~np.isfinite(q.reshape(32,4,32)),axis=2).sum()),
        'fallback_query_finite_block_count':int(np.all(np.isfinite(q.reshape(32,4,32)),axis=2).sum()),
        'mapped_value_validation':validation,
        'finite_compared_original_full5456_F64_ABI':True,
        'finite_firstwrite_lastread_word_endpoints':endpoint_ledger,

        'finite_phase_count':finite_runs,'fallback_phase_count':len(runs)-finite_runs,
        'finite_F32_output_bits':finite_output,'fallback_compared_original_full5456_F64_ABI':True,'fallback_F32_output_bits':fallback_out.view(np.uint32).tolist(),
        'initial_external_scale_LOADs_are_added_obligations':True,
        'phases':[{'kernel':r.kernel,'shape':list(r.shape),'counts':dict(r.counts),'metrics':dict(r.metrics),'events':r.trace,
                   'crossphase_producer_dependency_binding':'finite q/keyunits exact sourceSTORE events and scaleRF producers attached; scaleSTORE bridge/provider mappings remain UNBOUND','shared_physical_address_mapping':None,'hardware_cycles':None} for r in runs],
        'RF_versions':'actual executed laneSSA, not allocated physical RF','provider_events_actual':False}

def validate_mapped_values(runs,proposal,q,keys,weights):
    base=lambda n:proposal['fallback_local2_nonalias_regions'][n]['base']
    initial={base('query')+4*(term*33+head):int(q.view(np.uint32)[head,term]) for head in range(32) for term in range(128)}
    initial.update({base('keys')+4*(row*128+term):int(keys.view(np.uint32)[row,term]) for row in range(2) for term in range(128)})
    initial.update({base('weights')+4*head:int(weights.view(np.uint32)[head]) for head in range(32)})
    written={};loads=stores=external=0
    for runner in runs:
        for event in runner.trace:
            if event['opcode'] not in ['LOAD','STORE']:continue
            groups=event['operand_reads'][0]['values'] if event['opcode']=='LOAD' else event['shared_write_values']
            bits={(group['warp'],lane):value for group in groups for lane,value in zip(group['lanes'],group['bits'])}
            for access in event['source_mapped_shared_accesses']:
                address=access['address'];value=bits[(access['warp'],access['lane'])]
                if event['opcode']=='STORE':written[address]=value;stores+=1
                else:
                    loads+=1
                    if address in written:expected=written[address]
                    else:
                        if address not in initial:raise AssertionError('uninitialized mapped address')
                        expected=initial[address];external+=1
                    if value!=expected:raise AssertionError('mapped LOAD differs from current STORE/fixture bits')
    return {'LOAD_lanes_checked':loads,'STORE_lanes_checked':stores,'initial_external_LOADs_fixture_only_provider_UNBOUND':external,'verdict':'PASS','hardware_provider_bound':False}

if __name__=='__main__':print(json.dumps(plan(),indent=2,sort_keys=True))
