"""Finite R70 provider/provenance schema allocation bounds, metadata only.

No provider constructor, checkpoint payload, numerical execution, parser pricing,
cache release or RAM admission. Shadows are allocation certificates, never
checkpoint or execution inputs. Full future native/home identity is mandatory.
"""
import argparse,collections,gzip,hashlib,json,math,sys
from dataclasses import dataclass
from pathlib import Path
import ds_checkpoint_typed_allocation_bounds as peer
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_checkpoint_provider_closure_bounds_r70_20261003'
INPUT_MANIFEST_SHA='878a4f99869f8154af4f50be9ee1223bdf8259db26ca38a89bdc2df1500e9f1c'
U=(1<<64)-1
@dataclass(frozen=True)
class Leaf:
    encoded:dict

def require(v,msg):
    if not v:raise ValueError(msg)

def read(path):
    raw=path.read_bytes();return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def typed(v):
    if type(v)is Leaf:return v.encoded
    if type(v)is dict:return {'dict':[[typed(k),typed(x)] for k,x in v.items()]}
    if type(v)in (tuple,list,set):return {type(v).__name__:[typed(x) for x in v]}
    if v is None or type(v)in (str,int,float,bool):return v
    raise ValueError('unpriced shadow leaf')

def count(v):
    j=peer.JsonCounts(peer.layout());j.walk(v)
    r=j.result();r['canonical_byte_upper']=len(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
    return r

def array(shape,dtype='<f4'):
    return Leaf({'array':[U,U,dtype,shape,False]})

def source_schemas(root=D):
    root=Path(root)
    require(hashlib.sha256((root/'input_sha256.json').read_bytes()).hexdigest()==INPUT_MANIFEST_SHA,'exact input manifest')
    pins=read(root/'input_sha256.json')
    for name,wanted in pins.items():require(hashlib.sha256((root/'inputs'/name).read_bytes()).hexdigest()==wanted,'source input changed '+name)
    native=read(root/'inputs/PC01_slice.json.gz');manifest=read(root/'inputs/source_manifest.json.gz')
    plan=read(root/'inputs/source_enrollment.json');staging=read(root/'inputs/staging_map.json')
    require((native['full_native_count'],native['full_home_count'])==(2213,290730),'complete production identity')
    ops=native['instructions'];require([o['family'] for o in ops]==['hc_mixes','hc_pre_norm'],'exact PC01 family chain')
    source_keys=[(r['version'],r['rank']) for r in manifest['initial_versions']]
    require(len(source_keys)==len(set(source_keys))==3840,'all future source-image keys')
    # Two checkpoint-derived initial arrays are not source_images; V3 saves
    # them as actual arrays. Shapes from original constructor source, all96ranks.
    published={(manifest['checkpoint_initial_embedding']['version'],r):array([4,5120]) for r in range(96)}
    published.update({(manifest['checkpoint_initial_embedding']['initial_pre_version'],r):array([4]) for r in range(96)})
    locations={};seen=[];max_indices=0;array_bytes=96*(4*5120+4)*4
    for op in ops:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            require(not owned['buffer_programs'],'no collective program before PC2')
            t=native['templates'][owned['template']];nodes={n['dst']:n for n in t['code']}
            rank=owned['rank']
            for w in op['writes']:
                result=w['native_result_binding']['result'];shape=nodes[t['outputs'][result]]['shape']
                ix=[i for i in w['home_indices'] if rank in native['homes'][str(i)]['rank_group']]
                require(ix,'each publication actual RF home')
                max_indices=max(max_indices,len(ix));key=(w['version'],rank)
                published[key]=array(shape);array_bytes+=math.prod(shape)*4
                locations[key]=dict(indices=ix,shape=tuple(shape),dtype=Leaf({'dtype':'<f4'}),pc=op['pc'])
                seen.append([op['pc'],w['version'],rank,1,'data'])
    require(len(locations)==576 and len(seen)==576,'all source-required publications')
    # No releases credited: all source births through1 are included.
    paths=[r['persistent_destination'] for r in staging['files']]+[r['logical_path'] for r in staging['files']]
    path_chars=max(map(len,paths+[plan['output_root'],staging['persistent_root']]))
    # Actual MRO source table is bounded by the entire enrolled file table.
    pins={k:'f'*64 for k in plan['source_sha256']}
    identity={k:'f'*64 for k in ('manifest_sha256','journal_backend_sha256','manifest_data_sha256','native_sha256','homes_sha256','last_use_sha256','dispatch_sha256','allocations_sha256','helper_sha256','retention_policy_sha256','immutable_inputs_sha256')}
    identity.update(revision=manifest['checkpoint_revision'],generation=1,source_sha256=pins,shared_sources_sha256={'bounded_native':'f'*64,'arithmetic_helpers':'f'*64})
    # A one-string maximum path charges unicode4; actual prospective root/path
    # enrollment must fit this explicit source-derived bound before capture.
    longest='x'*path_chars
    costs=dict(admission=2,forward_CDC=4,read_service=64,write_service=80,owner_lookup=12,held_accept=1,write_visibility=4,consume=2,reverse_CDC=4,reverse_grant=4,retire=2)
    ports={}
    for rank in range(96):
        ports[rank]=dict(extents={('DeepSeek',rank):[dict(base=0,bytes=16<<20)]},tags=4,qd=64,write_cap=4,read_ticks=64,write_ticks=80,reverse_ticks=4,costs=costs,
          cost_scope='Positive provisional abstract software ticks; no real DRAM timing or clock claim',accept_sequence=U,
          backing=Leaf({'sector_backing':dict(table=[['DeepSeek',rank]],offset=U,count=U,record_bytes=46)}),
          generations=[U]*4,now=U,order=U,allocation_identity={'address_class':'RF','rank':rank},
          compact_lifecycle=dict(generations={i:U for i in range(4)},last_tick=U,tag_capacity=U,write_capacity=U))
    empty_fields=('backing','query_visible','routes','route_consumers','engram_owners','field_locations')
    provider=dict(published=published,locations=locations,seq=U,fullgraph_source_sha='f'*64,fullgraph_source_failed=False)
    provider.update({k:{} for k in empty_fields})
    extra=dict(history=dict(visible={},sequence=0),group_completed=set(),shared={},
               unconsumed_retired={(o['pc'],w['version']) for o in ops for w in o['writes']})
    snapshot=dict(provider=provider,ports={'rf':ports,'state':{}},immutable_published_keys=source_keys,source_image_keys=source_keys,retired={0,1},extra=extra)
    # One scratch owner per rank-binding/program: exact driver calls one
    # scratch_memory per owned native program, even exceptional operators.
    scratch=sum(len(o['rank_bindings']) for o in ops);streams=96+scratch+5
    # paired events/index files plus dictionary/event DB and restore receipt.
    files=2*streams+3
    history=dict(root=longest,files=[dict(path=longest,bytes=U,stamp=[U]*5,sha256='f'*64) for _ in range(files)],total_bytes=U,hashes_complete=True,physical_qualified=False)
    summary=dict(path=longest,journal_id=U,events=U,event_counts={k:U for k in ('request_accept','write_residence_reserved','software_owned_issue','software_service_phases_reserved','software_backing_visible','software_read_capture','consumer_accept','reverse_credit_accept','validated_reverse_grant','DS_r41_complete_observed_output')},framed_event_SHA256='f'*64,event_bytes=U,index_bytes=U,aggregate_reserved_bytes=U,aggregate_cap_bytes=U,in_memory_event_list=False,live_lifecycle_tags=0,fault=None,hardware_qualified=False)
    bindings=manifest['view_bindings'];resolved=[];verified={}
    for key,rec in bindings.items():
        path=rec['path'];runtime=path if Path(path).is_absolute() else str(Path(staging['persistent_root'])/path)
        require(len(runtime)<=path_chars,'enrolled provenance path bound exceeded')
        if not Path(path).is_absolute():
            resolved.append(dict(key=key,declared_path=path,runtime_path=runtime,sha256=rec['sha256']))
            verified[runtime]=rec['sha256']
    provenance=dict(status='PASS_EXACT_R33_INITIALIZATION_PROVENANCE',declared_input_content_sha256='f'*64,runtime_input_content_sha256='f'*64,source_owned_path_resolutions=len(resolved),verified_unique_coefficient_files=verified,resolved_bindings=resolved,all_other_source_fields_exact=True,hardware_qualified=False)
    scope=dict(prefix_stop=10,journal_root=longest,journal_capacity_bytes=U)
    role=dict(schema='SOURCE_JOURNAL_EVIDENCE_ROLE_V1',source_sha256={'h3_ds_checkpoint_provider_r30.py':'f'*64,'hbm_bound_event_journal_r30.py':'f'*64},compact_runtime_source_sha256={'h3_complete_native_calendar_successor_r1.py':'f'*64,'ds_hbm_additive_endpoint_join_r54.py':'f'*64},native_ports_unchanged=True,capacity_role='SQLite metadata admission guard; not tags/queues/backing extent',stop_role='external execution bound; no use in provider/engine data classes')
    shards={'model-'+str(i).zfill(5)+'-of-00048.safetensors':dict(path=longest,stamp=[U]*5,header_sha256='f'*64) for i in range(1,49)}
    inventory=dict(retired_PCs=[0,1],produced_locations=576,produced_and_initial_cached_array_bytes=array_bytes,raw_sectors=738048,raw_sector_payload_bytes=738048*32,future_source_windows=3840,retained_shared_homes=0,external_source_inputs={'unique_source_files':len(staging['files']),'source_file_bytes':U},metadata_bytes='priced exactly by serialized closure before publication',same_home_restore=True,hardware_qualified=False)
    contract=dict(identity=identity,runner_source_sha256='f'*64,original_runner_source_sha256='f'*64,source_plan_sha256='f'*64,checkpoint_selection=dict(schema='DS_STREAMED_SAVE_SELECTION_R69',original_V3_sha256='f'*64,stream_helper_sha256='f'*64,boundary_helper_sha256='f'*64,projection='original_V3_project_checkpoint',save='source_exact_streamed_two_pass',publication='original_R67_publish',restore='original_V3_verify_and_restore'))
    projection={k:U for k in ('payload_bytes','serialized_arrays','typed_state_metadata_bytes','metadata_python_tree_bytes','metadata_serialization_peak_envelope_bytes','maximum_array_contiguity_temporary_bytes','serialization_workspace_envelope_bytes','raw_sector_record_bytes','metadata_bytes_upper','filesystem_reservation_bytes','available_disk_bytes','old_journal_bytes')}
    projection.update(inventory);projection['old_journal_inventory']=history;projection['source_contract_bytes']=U
    projection['continuation_journal_bytes']='runner positive reviewed projection required separately; no zero default'
    actual=dict(seen=sorted(seen),initialization_provenance=provenance,observation_journal=summary,source_contract=contract,boundary_pc=1,projection=projection,producer_seal={'schema':'DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3','state_sha256':'f'*64,'payload_sha256':'f'*64},run_scope=scope,scope_role_proof=role)
    closure=dict(schema='DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3',identity=identity,inventory=inventory,state=typed(snapshot),run_scope=scope,scope_role_proof=role,historical_journal_inventory=history,opened_checkpoint_shards=shards,payload_sha256='f'*64,payload_bytes=U)
    return dict(snapshot=snapshot,closure=closure,actual_observations=actual,source_manifest=manifest,
      identity=identity,provenance=provenance,journal_inventory=history,scope_role=role,
      provenance_working_view_bindings=bindings,provenance_declared_input_fields={k:manifest[k] for k in ('checkpoint_path','checkpoint_revision','checkpoint_index_sha256','checkpoint_initial_embedding','initial_versions','view_bindings','history_images','history_source_receipt','query_field_homes')}),dict(
        publication_upper=576,published_array_occurrences_upper=len(published),published_array_copy_bytes_upper=array_bytes,
        source_image_key_upper=3840,RF_ports=96,RF_generations_per_port=4,scratch_stream_upper=scratch,
        all_stream_upper=streams,journal_files_upper=files,path_char_upper=path_chars,source_pin_entries_upper=len(pins),
        immutable_input_unique_paths=len({x['path'] for x in manifest['initial_versions']}|{x['path'] for x in bindings.values()}|{x['path'] for x in manifest['history_images']}),
        immutable_input_records=len(manifest['initial_versions']),auxiliary_binding_records=len(bindings),history_input_records=len(manifest['history_images']),
        max_home_indices_per_publication=max_indices,control_integer_upper=U,shard_record_upper=48)


def decoded_metadata_count(value):
    """Original read_tree object forms, excluding array/sector content already
    retained by the source RAM model. No alias discount for keys or controls.
    """
    import numpy as np
    L=peer.layout();kinds=collections.Counter();total=0
    def walk(v):
        nonlocal total
        if type(v)is Leaf:
            kind,items=next(iter(v.encoded.items()));kinds[kind]+=1
            if kind=='array':total+=peer.array_header(len(items[3]))+sys.getsizeof(np.dtype(items[2]))
            elif kind=='dtype':total+=sys.getsizeof(np.dtype(items))
            elif kind=='sector_backing':total+=sys.getsizeof({})+16
            else:raise ValueError('unknown decoded leaf')
            return
        k=type(v).__name__;kinds[k]+=1
        if type(v)is dict:
            total+=peer.dict_bytes(len(v),L)
            for key,item in v.items():walk(key);walk(item)
        elif type(v)in (list,tuple,set):
            total+=(peer.list_bytes(len(v),L) if type(v)is list else L['tuple_header']+8*len(v) if type(v)is tuple else L['set_header']+len(v)*L['set_single_entry'])
            for item in v:walk(item)
        elif type(v)is str:total+=L['unicode4_header']+4*len(v)
        elif v is None or type(v)in (int,bool,float):total+=sys.getsizeof(v)
        else:raise ValueError('unpriced decoded value')
    walk(value)
    # Every restored RF port has the original15 saved fields plus transient
    # live/queue/events/calendar/resident/faults and allocation_identity.
    # Price the source class instance and its full vars table, separately from
    # decoded control containers above. Existing events/backing content stays
    # in the retained source components; no new data FIFO is fabricated.
    class HeaderOnly:pass
    class_header=sys.getsizeof(HeaderOnly())
    port_variable_slots=15+6
    # RF SizedEvents wrapper has one source pointer; installed RF dictionary
    # and four quiescent transient fields are distinct from decoded saved ports.
    sized_events=class_header+peer.dict_bytes(1,L)
    quiescent_fields=L['dict_header']+3*L['list_header']+sys.getsizeof(0)
    port_headers=96*(class_header+peer.dict_bytes(port_variable_slots,L)+sized_events+quiescent_fields)+peer.dict_bytes(96,L)
    return dict(source_object_kind_occurrences=dict(kinds),decoded_nonpayload_heap_upper_bytes=total,
        restored_RF_port_instance_and_vars_upper_bytes=port_headers,restored_RF_port_variable_slots_upper=port_variable_slots,
        decoded_plus_restored_port_headers_upper_bytes=total+port_headers,
        ndarray_sector_payload_added=False,alias_discount_bytes=0,physical_admission=False,
        journal_file_buffers_SQLite_and_allocator_not_in_this_component=True)

def model(root=D):
    values,extents=source_schemas(root)
    rows={k:count(typed(v) if k=='snapshot' else v) for k,v in values.items()}
    for name in ('snapshot','closure'):rows[name]['nullable_integer_slots_upper']=96*2
    resource=read(Path(root)/'inputs/PC01_resource_model.json')
    requests=sum(row['sector_requests_upper'] for row in resource['operator_prices'])
    require(requests*128<U,'finite source prefix counters fit u64')
    return dict(schema='R70_PROVIDER_CLOSURE_NODE_ALLOCATION_BOUND',R70_commit='1dc062fd01d549c5ce611df13bf5cc007e2af0ac',
      full_native_PCs=2213,full_future_homes=290730,allocation_shapes=extents,node_profiles=rows,
      counter_source_proof={'PC01_source_sector_requests_upper':requests,'source_ticks_per_serial_transaction_upper':128,'serial_prefix_tick_upper':requests*128,'metadata_counter_price_upper':U,'no_wall_clock_or_idle_timer':True},
      decoded_state_metadata=decoded_metadata_count(values['snapshot']),
      CPython_layout=peer.layout(),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((Path(root)/'inputs').glob('*'))},
      provider_metadata_and_provenance_object_bounds_complete=True,
      raw_sector_and_array_payload_added_to_node_heap=False,all_possible_births_retained_no_release_discount=True,
      metadata_shadows_are_not_checkpoint_or_runtime_inputs=True,
      parser_scanner_serialization_overlap_owned_by_Kepler=True,physical_admission=False,actual_constructor_runs=0,actual_payload_reads=0,
      required_enrollment=['exact source hashes','enrolled runtime/provenance paths no longer than source path bound','all counters <= finite u64 source prefix bound; actual current values remain source-owned','actual nodes and bytes fit each selected profile','96port/576publication/3840sourcekey schema'],
      composition='Use node_profiles.closure and actual_observations for decoded object heap; snapshot is a separate projection graph, source_manifest belongs to retained constructor identity. Do not add all profiles as simultaneously live or charge payload again.')


def r71_profiles(root=D):
    """Exactly the source-retained roots requested by Kepler's R71 composer.
    Arrays remain binary payload; no production parser or provider is replaced.
    """
    g,e=source_schemas(root);actual=g['actual_observations'];seal=actual['producer_seal']
    receipt=dict(producer_seal=seal,actual_observations_sha256='f'*64)
    publication=dict(schema='DS_ACTUAL_ATOMIC_CHECKPOINT_R67',boundary_pc=1,producer_pid=U,
        destination='x'*e['path_char_upper'],files={name:dict(bytes=U,sha256='f'*64) for name in
        ('payload.bin','state.json','COMPLETE.json','actual_observations.json','RUNNER_COMPLETE.json')},
        producer_receipt=receipt,requires_fresh_process_restore=True)
    transition=dict(schema='DS_EXPLICIT_RUN_SCOPE_TRANSITION_V1',old_identity=g['identity'],new_identity=g['identity'],
        old_run_scope=actual['run_scope'],new_run_scope=actual['run_scope'],next_pc=2,
        checkpoint_receipt=receipt,role_proof=g['scope_role'],seal_sha256='f'*64)
    roots=dict(typed_state=typed(g['snapshot']),state_closure=g['closure'],actual_observations=actual,
        source_contract=actual['source_contract'],projection=actual['projection'],
        atomic_publication=publication,runner_receipt=receipt,producer_seal=seal,
        caller_actual=actual,verified_actual=actual,fresh_actual=actual,run_scope_transition=transition)
    def depth(v):
        if type(v)is dict:return 1+max((depth(x) for x in v.values()),default=0)
        if type(v)in (list,tuple):return 1+max((depth(x) for x in v),default=0)
        return 0
    out={}
    for name,value in roots.items():
        c=count(value)
        out[name]=dict(schema='DS_JSON_CARDINALITY_R71',encoded_bytes=c['canonical_byte_upper'],nodes=c['nodes'],
            kinds=c['kinds'],list_items=c['list_items'],dict_entries=c['dict_entries'],
            max_decoded_string_chars=c['max_decoded_string_chars'],max_integer_chars=c['max_integer_chars'],
            unique_key_upper=len(c['JSON_dictionary_key_names']),max_list_len=c['max_list_len'],max_dict_len=c['max_dict_len'],
            max_depth=depth(value),unshared_python_object_heap_upper_bytes=c['unshared_python_object_heap_upper_bytes'],
            ensure_ascii=True,no_custom_hooks=True,finite_source_upper=True)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--generate',type=Path);ap.add_argument('--verify',action='store_true');ap.add_argument('--r71-profiles',type=Path);a=ap.parse_args();r=model()
    if a.r71_profiles:a.r71_profiles.write_text(json.dumps(r71_profiles(),indent=2,sort_keys=True)+'\n')
    if a.generate:a.generate.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    if a.verify:require(r==read(D/'model.json'),'exact node bound replay')
    print(json.dumps({'extents':r['allocation_shapes'],'object_bytes':{k:v['unshared_python_object_heap_upper_bytes'] for k,v in r['node_profiles'].items()}},sort_keys=True))


def verify_enrolled_metadata(name,value,record):
    """Allocation-shape guard only; numerical/ownership checks stay original.
    Never used to accept checkpoint identities or relax V3 quiescence/seals.
    """
    require(name in record['node_profiles'],'enrolled profile')
    require(not record['physical_admission'],'component cannot confer admission')
    got=count(value);limit=record['node_profiles'][name]
    for field in ('nodes','list_items','dict_entries','decoded_unicode_characters','max_decoded_string_chars','max_integer_chars','max_list_len','max_dict_len','unshared_python_object_heap_upper_bytes','canonical_byte_upper'):
        require(got[field]<=limit[field],'allocation exceeds '+field)
    for kind,n in got['kinds'].items():
        capacity=limit['kinds'].get(kind,0)+(limit.get('nullable_integer_slots_upper',0) if kind=='none' else 0)
        require(n<=capacity,'unknown/excess node kind')
    require(set(got['JSON_dictionary_key_names'])<=set(limit['JSON_dictionary_key_names']),'unpriced schema key')
    return dict(allocation_profile=name,source_object_bounds_fit=True,physical_admission=False,identity_accepted=False)


if __name__=='__main__':main()
