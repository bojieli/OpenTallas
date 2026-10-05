#!/usr/bin/env python3
"""C0 analytical control sizing from immutable H3/H1 sources. No RTL admission."""
import ast,collections,gzip,hashlib,json,math,pathlib,subprocess
from uarch_model import DFF_UM2, GPU_LOGIC_UTIL
NATIVE='fd7220c1e55397dec90222e1f99a8bd95ae02e03'
AUDIT='e844837ed6dcaa669761e7e394c5b93b61255e75'
DEWEY='6e28f1a8b48ea0182aed59a09d65540a1b0b96b3'
DEWEY_INTERFACE='results/uarch/h3_complete_native_calendar_20261002/h4_actual_config_e844/C0_Sagan_interface.json'
H1='992c14a70f812028f9de5e46eb79d5688db9482b'
QPATH='results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz'
DPATH='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/h4_c0_bridge_model_20261002'
def bits(n):return max(1,(max(1,n)-1).bit_length())
def pinned(path,pin=NATIVE):return subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
def load(path):return json.loads(gzip.decompress(pinned(path)))
def sources():
    q=load(QPATH);d=load(DPATH);r=load(d['residence_archive']);return q,d,r

def residence(homes):
    events=collections.defaultdict(lambda:collections.Counter());max_slot=0;max_byte=0;classes=collections.Counter();versions=set();unique=set()
    for h in homes:
        versions.add(h['version']);cl=h.get('home',{}).get('class','control');classes[cl]+=1
        ranks=h.get('rank_group',[h.get('rank',0)]);sm=h.get('SM',0)
        start=max(0,h['birth_pc']);end=h.get('retire_pc',max(h.get('consumers',[start]) or [start]))
        if end is None:end=max(h.get('consumers',[start]) or [start])
        for rank in ranks:
            domain=(rank,sm);identity=(domain,h['version'])
            if identity in unique:raise ValueError('duplicate home identity requires explicit merge '+str(identity))
            unique.add(identity);events[domain][start]+=1;events[domain][end+1]-=1
        if cl=='RF':max_slot=max(max_slot,h['home']['slot_first']+h['home']['vectors'])
        elif cl=='spill':max_byte=max(max_byte,h['home'].get('byte_offset',0)+h['home'].get('bytes',0))
    peaks=[]
    for (rank,sm),ev in events.items():
        live=peak=0;at=0
        for pc,delta in sorted(ev.items()):
            live+=delta
            if live>peak:peak=live;at=pc
        peaks.append({'rank':rank,'SM':sm,'max_live_versions':peak,'peak_PC':at})
    return {'home_records':sum(classes.values()),'home_classes':dict(classes),'version_count':len(versions),'expanded_home_identities':len(unique),'max_RF_slot_end_exclusive':max_slot,'max_local_spill_byte_end':max_byte,'max_live_versions_per_SM':max(x['max_live_versions'] for x in peaks),'peaks':sorted(peaks,key=lambda x:(x['rank'],x['SM']))}

def control_model(q,d,r):
    dewey=json.loads(pinned(DEWEY_INTERFACE,DEWEY))
    forward=load('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz')
    audit=json.loads(gzip.decompress(pinned('results/uarch/h4_native_rtl_binding_audit_20261002/family_bindings.json.gz',AUDIT)))
    model={};rank_programs={}
    for name,ops,homes in [('Qwen',q['operations'],[h for v in q['operands'] for h in v['homes']]),('DeepSeek',d['instructions'],r['homes'])]:
        rr=residence(homes);versions=sorted(set(h['version'] for h in homes)|{v if isinstance(v,str) else v['version'] for op in ops for side in ('reads','writes') for v in op[side]});families=sorted({x.get('opcode',x.get('family')) for x in ops});rank_count=2 if name=='Qwen' else 96
        max_reads=max(len(x['reads']) for x in ops);max_writes=max(len(x['writes']) for x in ops);max_deps=max(len(x['dependencies']) for x in ops)
        codes=list(q['microcode'].values()) if name=='Qwen' else [t['code'] for t in d['templates'].values()]
        max_steps=max(len(c) for c in codes);code_steps=sum(len(c) for c in codes)
        max_shape=max((math.prod(ins.get('shape',[]) or [1]) for c in codes for ins in c),default=1)
        if name=='Qwen':max_shape=max(sum(v['elements_per_rank']) for v in q['operands'])
        max_commands=max((sum(x['calendar_export']['physical_primitives']['native_primitive_commands'].values()) for x in ops),default=1) if name=='Qwen' else max_shape*max_steps
        fields={'opcode':6,'PC':bits(len(ops)),'family':bits(len(families)),'template':bits(len(codes)),'microstep':bits(max_steps),'logical_scalar_index':bits(max_shape),'RF_src_a':9,'RF_src_b':9,'RF_dst':9,'active_lanes':8,'version':bits(len(versions)),'rank':bits(rank_count),'SM':5,'generation':64,'fragment_sequence':bits(max_commands+1)}
        fields.update(source_version_a=fields['version'],source_version_b=fields['version'],source_version_predicate=fields['version'],source_generation_a=64,source_generation_b=64,source_generation_predicate=64,RF_predicate=9)
        raw=sum(fields.values());minimum_word_bits=math.ceil(raw/64)*64;word_bits=512
        if raw>512:raise ValueError('explicit command identities exceed Dewey512-bit envelope')
        consumer_counts=collections.Counter(v if isinstance(v,str) else v['version'] for op in ops for v in op['reads'])
        # Source-derived maximum resident homes; proposed fixed64-bit address/identity entry.
        entry_fields={'version':fields['version'],'class':2,'RF_base':9,'span_vectors':10,'byte_address':max(10,bits(rr['max_local_spill_byte_end']+1)),'visible':1,'producer_done':1,'mirrored_ACK':2,'consumers_remaining':bits(max(consumer_counts.values(),default=0)+1),'reverse_grant':1,'generation':64}
        entry_bits=sum(entry_fields.values());minimum_slots=1<<bits(rr['max_live_versions_per_SM']);slots=dewey['finite_per_SM']['scoreboard_entries'];entry_bits=max(200,entry_bits)
        # one accepted command, one response and one64B command-fetch window; no outstanding tag reuse.
        temporary_tag_bits=32*(fields['microstep']+1+1+32+8)
        per_sm_bits=slots*entry_bits+temporary_tag_bits+2*word_bits+512+6*32+64+8+16+9+2+10+64+128+64
        rank_dep_bits=len(ops)+32+fields['PC']+64+256+1
        dictionary_bits=code_steps*word_bits
        descriptor_bits=fields['family']+fields['template']+fields['PC']+(max_reads+max_writes)*fields['version']+max_deps*fields['PC']+64
        descriptor_bytes=math.ceil(descriptor_bits/64)*8
        flop_area=per_sm_bits*DFF_UM2
        mux_bits=slots*(entry_bits+fields['version'])+2*word_bits
        compare_area=slots*fields['version']*0.2
        logic_um2=flop_area+mux_bits*0.2+compare_area+512
        footprint=logic_um2/GPU_LOGIC_UTIL/1e6
        # Physical data ports already exist. C0 adds control only; no cross-SM4096-bit mux.
        control_tracks=2*word_bits+sum([9,9,9,1,1,1,1,1])+64+32
        local_channel=int(64*4/0.08)
        rank_fanout_tracks=word_bits+32+32
        model[name]={'PCs':len(ops),'families':len(families),'ranks':rank_count,'SMs_per_rank':32,'residence':rr,'encoding':{'declared_version_count':len(versions),'versions_without_resident_home':sorted(set(versions)-{h['version'] for h in homes}),'fields_bits':fields,'minimum_command_bits':raw,'aligned_command_bits':word_bits,'minimum_aligned_command_bits':minimum_word_bits,'minimum_source_entries':minimum_slots,'adopted_interface_command_bits':512,'PC_descriptor_bytes_upper':descriptor_bytes,'max_reads':max_reads,'max_writes':max_writes,'max_PC_dependencies':max_deps,'native_code_templates':len(codes),'maximum_SSA_steps':max_steps,'static_code_steps':code_steps,'maximum_logical_shape_elements':max_shape,'command_count_field_upper':max_commands,'dictionary_bytes':math.ceil(dictionary_bits/8),'descriptor_table_bytes':len(ops)*descriptor_bytes,'dictionary_policy':'existing immutable control provider, streamed64B fetch; shared per rank, not32copies on die','literal_pool':'Exact attrs/immediates and shape/provider metadata remain external typed immutable blobs; NOT included in fixed-word dictionary estimate; raw-source upper bound separately recorded'},'scoreboard':{'entry_fields_bits':entry_fields,'entry_aligned_bits':entry_bits,'proposed_entries_per_SM':slots,'maximum_source_live_versions':rr['max_live_versions_per_SM'],'outstanding_RF_transactions':1,'outstanding_scratch_transactions':1,'command_fetch_window_bytes':64,'loop_counter_registers':6,'loop_counter_bits_each':32,'loop_counter_scope':'PROPOSED envelope; procedural nested helpers must emit continuations; not a proven sufficient whole-program hardware loop stack','full_token_generation_bits':64,'H1_fence_epoch_bits':8,'epoch_adapter':'64-bit generation retained outside H1;8-bit fence epochs reused only after all owned ACKs/returns/reverse grants drained; reset invalidates session','RF_temporary_slots':32,'temporary_tag_bits':temporary_tag_bits,'temporary_tag_scope':'32 RF workspace slots; source SSA identity, valid/ready,32-bit compiler continuation/refcount field,8-bit drained epoch. Refcount overflow requires external continuation, never wraps.','storage_bits_per_SM':per_sm_bits,'rank_dependency_bits':rank_dep_bits,'program_source_digest_bits_per_rank':256,'program_context_selector_bits':1,'command_program_hash_policy':'Trusted pinned256-bit source digest retained per rank; each source_PC context references it. Not transmitted as an extra unpriced512-bit-word field.','publication':'visible only after completed+both mirror ACKs; ownership held through consumer completion and reverse grant'},'cost':{'compute_MACs_per_cycle':0,'control_issue_proposed_per_SM_per_cycle':1,'ports_bytes_per_transaction':{'command_fetch':64,'metadata_fetch':64,'RF_read_A':512,'RF_read_B':512,'RF_write_each_mirror':512,'scratch':64},'command_fetch_peak_Bpc_per_rank':32*64,'command_fetch_peak_scope':'Analytical simultaneous issue ceiling, not sustainable HBM/controller bandwidth; positive existing provider/route service charges still required.','physical_arithmetic_credit':0,'RF_third_operand_policy':'SELECT/SCATTER/control operands require an extra serialized RF read and predicate capture; no third RF port inferred.','RF_transaction_II':'C_RF_R_accept+C_RF_R_response+7ALU+C_RF_W_accept+C_mirrored_ACK+C_done_accept; positive measured/provisional edge costs required','front_control_cycles_per_command_provisional':22,'C0_costs_Dewey_positive_provisional_ticks':{'C0_fetch':2,'C0_decode':2,'C0_home_scoreboard':12,'C0_accept':2,'C0_complete':2,'C0_reverse_retire':2},'front_control_events':['decode','home lookup+dependency gate','local RF arbitration','issued/completed bookkeeping'],'command_fetch_64B_beats':math.ceil(word_bits/512),'scratch_64B_beats_per_128lane_vector':8,'source_Q128B_shared_to_H1_64B_multiplier':2,'serial_front_overhead_cycles_full_program':'22*N_executed_commands + C_extra_fetch64*N_extra_command_beats + C_desc64*N_descriptor_beats; native/provider/RF costs added once by Dewey, not duplicated','tokens_per_second':None,'latency_scope':'CONTROL MODEL ONLY, actual full-program ordered dynamic command expansion pending; per-family counted model estimates do not qualify hardware'},'area':{'DFF_area_um2_per_bit':DFF_UM2,'mux_area_um2_per_bit_ASSUMED':0.2,'lookup_mux_bit_equivalents':mux_bits,'register_area_um2':flop_area,'compare_area_um2_ASSUMED':compare_area,'control_area_um2_ASSUMED':512,'logic_um2_per_SM':logic_um2,'placement_utilization_ASSUMED':GPU_LOGIC_UTIL,'footprint_mm2_per_SM':footprint,'replicas_per_rank':32,'footprint_mm2_32SM':32*footprint,'rank_dependency_flop_mm2':rank_dep_bits*DFF_UM2/GPU_LOGIC_UTIL/1e6,'existing_RF_scratch_area_recharged':False,'slot_fit':'UNQUALIFIED: reserve incremental footprint in SMslot; no contextual macro/SSFF evidence'},'routing':{'new_control_tracks_local':control_tracks,'local_channel_tracks_ASSUMED':local_channel,'local_channel_basis':'existing model assumption64um channel,4existing signal layers,0.08um pitch','fits_ASSUMED_incremental_control_channel':control_tracks<=local_channel,'combined_existing_payload_plus_C0_tracks_if_shared_channel':8192+8192+512+1024+control_tracks,'fits_ASSUMED_single_combined_channel':(8192+8192+512+1024+control_tracks)<=local_channel,'combined_channels_required_ASSUMED':math.ceil((8192+8192+512+1024+control_tracks)/local_channel),'rank_broadcast_wires':rank_fanout_tracks,'replica_fanout':32,'local_demux':'lookup entries finite, one accepted RF owner; no new wide data crossbar','command_boundary_bits':512,'command_32SM_fanout_bits':32*512,'metadata_boundary_bits':512,'RF_existing_read_bits':8192,'RF_existing_write_bits':4096,'scratch_existing_bits':512,'hub_routing_layer_check':'PENDING; no added layers authorized'}}
        # Family costs from existing producers; never fill missing hardware with CPU implementation.
        families_out=[]
        for fam in families:
            a=next(x for x in audit if x['model']==name and x['family']==fam)
            families_out.append({'family':fam,'PCs':a['PCs'],'required_primitives':a['required_primitives'],'missing_hardware_gates':a['remaining_work'],'C0_decode_source_present':True,'hardware_admitted':False,'CPU_primitive_execution_is_RTL':False})
        model[name]['family_gates']=families_out
        if name=='Qwen':
            command_counts=collections.Counter()
            for op in ops:command_counts[op['opcode']]+=sum(op['calendar_export']['physical_primitives']['native_primitive_commands'].values())
            model[name]['cost']['source_counted_commands_by_family']=dict(command_counts)
            model[name]['cost']['source_counted_commands']=sum(command_counts.values())
            model[name]['cost']['C0_counted_positive_provisional_ticks']=22*sum(command_counts.values())
            model[name]['cost']['count_scope']='Committed full-context primitive export; source ordered dynamic trace and actual32SM scheduling remain separate.'
        else:
            lower=upper=0
            by_family=collections.defaultdict(lambda:{'command_lower':0,'command_upper':0})
            for op,dispatch in zip(ops,forward['PC_dispatch']):
                assert op['pc']==dispatch['pc']
                lo=sum((n+127)//128 for n in dispatch['baseline_once_scalars'].values());hi=sum(dispatch['baseline_once_scalars'].values())
                lower+=lo;upper+=hi;by_family[op['family']]['command_lower']+=lo;by_family[op['family']]['command_upper']+=hi
            model[name]['cost']['source_command_bounds_by_family']=dict(by_family)
            model[name]['cost']['source_command_bounds']={'lower':lower,'upper':upper}
            model[name]['cost']['C0_positive_provisional_tick_bounds']={'lower':22*lower,'upper':22*upper}
            model[name]['cost']['count_scope']='Bounds only from existing once-materialized scalar counts: ceil(opcode scalars/128) <= commands <= scalar evaluations. NOT actual streaming mask/provider trace or timing; selected continuation contracts remain unchanged.'
        if name=='DeepSeek':
            model[name]['compiler_workspace_binding']={'source':'results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz','rank_cap_bytes':forward['workspace']['rank_cap_bytes'],'provider_AW':forward['workspace']['provider_AW'],'base':forward['workspace']['base'],'physically_certified':False,'template_execution_paths':dict(collections.Counter(t['execution_path'] for t in forward['templates'].values())),'state_not_in_resident_version_table':'SSA temporaries/continuations reuse existing bounded compiler frame allocator; actual aligned disjoint32MiB/rank lease REQUIRED before running; no AW27 wraps or RF enlargement','hardware_gate':'Streaming paths need explicit ordered128lane continuation emitter; logical template shapes cannot issue directly.'}
        else:
            model[name]['compiler_workspace_binding']={'source':QPATH,'RF_temporary_vectors':32,'scratch_reserved_bytes':17408,'spill_bytes':33554432,'hardware_gate':'Procedural TiledMachine command trace supplies actual ordered leaf calls; static invocation histograms do not establish order or finite loop state.'}
        rank_programs[name]={'versions':versions,'family_ids':{f:i for i,f in enumerate(families)}}
    return {'schema':'opentallas.h4.C0.control_model.v1','enabled_default':False,'RTL_allowed':False,'native_commit':NATIVE,'H1_RTL_commit':H1,'unified_model_basis':'tools/uarch_model.py: DFF_UM2/GPU_LOGIC_UTIL and gpu_payload_transport_model routing/mux assumption; immutable fd722 source','scope':'No provider implementation, no numeric engine, no connected-token qualification','programs':model},rank_programs

def hbm_native_c0_bridge_model(enabled=False):
    """Additive opt-in C0 sizing API; the pinned unified model is unchanged."""
    if not enabled:
        return dict(schema="opentallas.h4.C0.control_model.v1", enabled_default=False,
                    RTL_allowed=False, status="OFF")
    qwen, deepseek, residence = sources()
    model, _ = control_model(qwen, deepseek, residence)
    return model


def main():
    q,d,r=sources();m,_=control_model(q,d,r);OUT.mkdir(exist_ok=True,parents=True)
    # raw source size bounds include attrs/literal/provider metadata deliberately excluded from fixed words.
    pins={}
    for p,pin in [(QPATH,NATIVE),(DPATH,NATIVE),(d['residence_archive'],NATIVE),('tools/uarch_model.py',NATIVE),('rtl/gpu/ot_gpu_full_sm_service.sv',H1),('rtl/gpu/ot_gpu_rf_service.sv',H1),('rtl/gpu/ot_gpu_scratch_service.sv',H1)]:
        b=pinned(p,pin);pins[pin+':'+p]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
        if p in (QPATH,DPATH):m['programs']['Qwen' if p==QPATH else 'DeepSeek']['encoding']['raw_program_JSON_bytes_upper_including_metadata']=len(gzip.decompress(b))
    b=pinned('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz');pins[NATIVE+':results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz']={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
    b=pinned('results/uarch/h4_native_rtl_binding_audit_20261002/family_bindings.json.gz',AUDIT);pins[AUDIT+':results/uarch/h4_native_rtl_binding_audit_20261002/family_bindings.json.gz']={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
    m['source_pins']=pins
    for path in (DEWEY_INTERFACE,'tools/h3_complete_native_calendar.py'):
        b=pinned(path,DEWEY);m['source_pins'][DEWEY+':'+path]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
    m['Dewey_interface_commit']=DEWEY
    m['Dewey_interface_path']=DEWEY_INTERFACE
    m['minimum_table_scope']='8/16 entries bound source resident versions only; interface512 adopted to cover compiler temporary/continuation/provider command identities until full dynamic occupancy is proved.'
    (OUT/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({n:{'PCs':p['PCs'],'families':p['families'],'command_bits':p['encoding']['aligned_command_bits'],'live_versions':p['scoreboard']['maximum_source_live_versions'],'scoreboard_entries':p['scoreboard']['proposed_entries_per_SM'],'control_mm2_32SM':p['area']['footprint_mm2_32SM'],'local_control_tracks':p['routing']['new_control_tracks_local']} for n,p in m['programs'].items()},sort_keys=True))
if __name__=='__main__':main()
