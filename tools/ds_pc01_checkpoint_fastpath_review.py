"""Source-priced PC0->actual checkpoint->coldPC1 proposal and host backing audit.

Metadata-only. Does not import a provider/runner, mmap weights, reclaim cache,
copy data, lower R64 guards, change run scope or launch arithmetic. Full-program
identity remains mandatory in any future additive implementation.
"""
import argparse
import ast
import collections
import copy
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_pc01_checkpoint_fastpath_review_20261003'


def load(p):
    raw=p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok,why):
    if not ok:raise ValueError(why)


def union(spans):
    out=[]
    for a,b in sorted(spans):
        require(type(a)is int and type(b)is int and 0<=a<b,'source sector span')
        if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out


def compact_primitives(base):
    path=base/'sources/tools/h3_complete_native_calendar_successor_r1.py'
    tree=ast.parse(path.read_bytes())
    names={'compact_uint','CompactDiskEvents','compact_source_frame_upper'}
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    require({n.name for n in nodes}==names,'exact compact source functions')
    # Compile ONLY encoding/sizing functions. No constructor is invoked.
    ns=dict(re=re,json=json,hashlib=hashlib,Counter=collections.Counter,Path=Path)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns['compact_source_frame_upper']


def compact_charge(frame, event):
    f=frame(event)
    dictionary=sum(8*(len(canonical(x))+64) for x in (f['descriptor'],f['metadata']) if x is not None)
    return dict(frame=f, dictionary_bytes=dictionary,
                event_bytes=f['frame_bytes_upper']+16, # charge sparse index on EVERY record
                complete_new_descriptor_charge_bytes=dictionary+f['frame_bytes_upper']+16)


def operator_prices(data,frame):
    homes=data['homes'];rows=[]
    for op in data['instructions']:
        require(op['pc'] in (0,1),'only reviewed PC0..1 slice')
        require(sorted(r['rank'] for r in op['rank_bindings'])==list(range(96)), 'full96 rank coverage')
        req=0;published=0;cached_bytes=0;native_calls=0;control_cost=0;spans=collections.defaultdict(list)
        versions=collections.Counter();max_individual_array=0
        for own in op['rank_bindings']:
            if own.get('empty_owned_extent'):continue
            require(not own.get('buffer_programs'),'reviewed early operators have no collective buffer loop')
            rank=own['rank'];t=data['templates'][own['template']];native_calls+=1
            for name,p in t['providers'].items():
                b=op['provider_bindings'][own['template']][name]
                if b['kind'] in ('versioned_operand','explicit_auxiliary_provider'):
                    words=math.prod(p['shape'])*(2 if p['dtype']=='I64' else 1)
                    req+=(words+7)//8+32
            record=dict(PC=op['pc'],rank=rank,template=own['template'],source_native_stages=len(t['code']),
                        native_mode='unchanged_source_Machine_live_range_CPU_SSA',
                        native_opcode_counts=dict(collections.Counter(n['op'] for n in t['code'])),
                        published_versions=[w['version'] for w in op['writes']],full_token_exact_qualified=False,physical_qualified=False)
            control_cost+=compact_charge(frame,dict(event='C0_actual_native_numeric_call',record=record))['complete_new_descriptor_charge_bytes']
            code={n['dst']:n for n in t['code']}
            for w in op['writes']:
                ix=[i for i in w['home_indices'] if rank in homes[str(i)]['rank_group']]
                total_bytes=0
                for i in ix:
                    h=homes[str(i)];count=h['word_count'];require(h['home']['class']=='RF','no early native-state writer')
                    require(count<=128*h['home']['vectors'],'RF home capacity')
                    req+=3*((count+7)//8)+2*(count%8!=0);total_bytes+=4*count
                    for replica in (0,1):
                        first=(2*h['SM']+replica)*262144+h['home']['slot_first']*512
                        spans[rank].append([first//32,(first+count*4+31)//32])
                field=w['native_result_binding']['result'];shape=code[t['outputs'][field]]['shape']
                require(math.prod(shape)*4==total_bytes,'source F32 output/home extent')
                cached_bytes+=total_bytes;versions[w['version']]+=total_bytes
                max_individual_array=max(max_individual_array,total_bytes);published+=1
                event=dict(event='DS_r41_complete_observed_output',identity=dict(PC=op['pc'],rank=rank,generation=1,
                    version=w['version'],home_indices=ix),field='data',shape=shape,dtype='<f4',payload_sha256='f'*64,
                    original_reference_home_indices=ix,allocated_home_records=[homes[str(i)] for i in ix],
                    byte_exact=True,reference_sha256='f'*64,hardware_qualified=False)
                control_cost+=compact_charge(frame,event)['complete_new_descriptor_charge_bytes']
                # Overcharge possible global unconsumed retirement once/rank/write.
                event=dict(event='source_unconsumed_output_retired',PC=op['pc'],version=w['version'],generation=1,
                           producer_all_rank_reverse_retirement_complete=True,source_or_manifest_consumer_references=0,hardware_qualified=False)
                control_cost+=compact_charge(frame,event)['complete_new_descriptor_charge_bytes']
        rows.append(dict(PC=op['pc'],family=op['family'],native_calls=native_calls,publication_records=published,
            sector_requests_upper=req,control_journal_upper_bytes=control_cost,
            produced_cached_bytes_without_release_discount=cached_bytes,per_version_cached_bytes=dict(versions),
            largest_individual_output_bytes=max_individual_array,
            RF_written_sector_spans={str(r):union(s) for r,s in spans.items()}))
    return rows


def host_delta(*,allocation,unbacked,shared_resident):
    for v in (allocation,unbacked,shared_resident):require(type(v)is int and v>=0,'nonnegative physical bytes')
    # New private guest pages can COW the WHOLE touched shared page, not merely
    # the old proportional PSS share. Reclaim credit requires observed host
    # backing release and cannot exceed this modeled positive delta.
    gross=min(allocation,unbacked+shared_resident)
    return gross


def model(base=D/'inputs'):
    base=Path(base)
    for p,h in load(base/'input_sha256.json').items():require(sha(base/p)==h,'input changed: '+p)
    data=load(base/'PC01_metadata_slice.json.gz');require(data['full_native_count']==2213 and data['full_home_count']==290730,'full source origin')
    require([o['family'] for o in data['instructions']]==['hc_mixes','hc_pre_norm'],'actual early family chain')
    frame=compact_primitives(base);rows=operator_prices(data,frame)
    schema=load(base/'journal_schema_envelope_r2.json');frames=[];descriptors={}
    for name,v in schema['schemas'].items():
        e=copy.deepcopy(v['schema_template']);e['allocation_identity']={'address_class':'RF','rank':95}
        # Source R54 wrapper can checksum normal admission and write visibility.
        e['payload_sha256']='f'*64
        f=frame(e);frames.append(dict(event=name,**f));descriptors[canonical(f['descriptor'])]=f['descriptor']
    max_frame=max(f['frame_bytes_upper'] for f in frames)
    # Metadata is constant per RF rank; descriptor scalar fields are extracted
    # losslessly, checksum bytes stay in frames, source fixed costs stay in schema.
    metadata=[{'address_class':'RF','rank':r} for r in range(96)]
    dictionary=131072+sum(8*(len(canonical(d))+64) for d in list(descriptors.values())+metadata)
    streams=96+5;file_reserve=streams*8192;restore_scope_file=65536
    per=[]
    for r in rows:
        req=r['sector_requests_upper'];events=8*req
        sector_bytes=events*(max_frame+16) # EVERY event pays sparse index, no compression ratio
        # Keep the source's preacceptance buffer guard and per-rank operator allowance.
        guard=96*65536
        r.update(sector_events_upper=events,source_compact_sector_journal_upper_bytes=sector_bytes)
        per.append(dict(PC=r['PC'],sector_events=sector_bytes,control_records=r['control_journal_upper_bytes'],
                        descriptor_and_owner_dictionary=dictionary,event_index_padding=file_reserve,
                        preacceptance_reservation=guard,bootstrap_scope_receipt=restore_scope_file))
    journals=[sum(p.values())-p['PC'] for p in per]
    old=load(base/'preflight_model.json');ram=old['RAM']['coexistence_RAM_peak_bytes']
    # Conservative FIRST gate intentionally retains full reviewed RAM. A second
    # source-accounted streaming-phase option is proposed below, never admitted.
    checkpoint_upper=old['checkpoint_new_bytes']
    other=old['other_new_bytes']
    # Existing latest+previous actual payloads stay used; third staging copy is
    # the only new data. Same-filesystem directory rename adds NO payload copy.
    capture_phase_new=checkpoint_upper
    rotation_existing=2*checkpoint_upper
    disk_new=sum(journals)+capture_phase_new+other
    placement=load(base/'source_placement_inventory.json')
    host=load(base/'remote_metadata.json');physical=load(base/'physical_capacity_cc4d.json');cache=load(base/'cache_inventory_de930.json');observed=load(base/'R58_terminal_receipt.json')
    q=physical['QEMU_residency_snapshot'];G=q['configured_memory_bytes'];rss=q['RSS_bytes'];pss=q['PSS_bytes']
    # SharedClean missing from retained smaps: bound ALL non-PSS RSS as shared
    # is not enough. The full RSS bound covers SharedClean until fresh inventory.
    shared_known=q['shared_dirty_bytes'];shared_clean=None
    unbacked=max(0,G-rss)
    current_known_delta=host_delta(allocation=ram,unbacked=unbacked,shared_resident=shared_known)
    conservative_delta=host_delta(allocation=ram,unbacked=unbacked,shared_resident=rss)
    for name,h in [('PVE1',host['PVE1']),('agidock128',host['agidock128'])]:
        h['new_source_and_run_disk_bytes']=placement['selected_shard_bytes']+placement['source_input_bytes']+disk_new
        h['run_and_selected_source_disk_margin_bytes']=h['disk_free_bytes']-h['new_source_and_run_disk_bytes']
        h['full_released_source_and_run_disk_bytes']=placement['all_released_shard_bytes']+placement['source_input_bytes']+disk_new
        h['full_source_disk_margin_bytes']=h['disk_free_bytes']-h['full_released_source_and_run_disk_bytes']
        h['guest_RAM_margin_unchanged_R64_bytes']=h['MemAvailable_bytes']-ram
        h['resource_admission']=False
    metadata_only=sum(v for k,v in old['checkpoint']['components'].items()
                      if k not in ('resident_sector_payload_bytes','cached_array_payload_bytes'))
    encoded_heap_multiplier=64
    # This is a proposed schema-specific builtin-heap allowance, NOT allocator
    # highwater/OS headroom proof; actual V3 exact project remains mandatory.
    capture_workspace=encoded_heap_multiplier*metadata_only+2*metadata_only+old['checkpoint']['components']['cached_array_payload_bytes']+1048576
    replacement=old['RAM']['components']['serialization_workspace_bytes']
    priced_ram=dict(old['RAM']['components']);priced_ram['serialization_workspace_bytes']=capture_workspace
    # Remove NO state here: retain both producer+restored old raw upper bounds,
    # PC10 shared overcharge, all graph/image/diagnostic costs. Thus this option
    # still exceeds a small PC0-1 physical shape but remains source conservative.
    prospective_RAM=sum(priced_ram.values())
    # Entire sector contents ever written through PC1 persist, even released
    # versions. Initial readonly NPY views are not boxed state port writes.
    spans=collections.defaultdict(list)
    for row in rows:
        for rank,ranges in row['RF_written_sector_spans'].items():spans[rank].extend(ranges)
    merged={rank:union(ranges) for rank,ranges in spans.items()}
    source_sectors=sum(b-a for ranges in merged.values() for a,b in ranges)
    per_sector=old['RAM']['interpreter']['sector_entry_bytes']
    largest_port=max(sum(b-a for a,b in ranges) for ranges in merged.values())
    source_ram=dict(old['RAM']['components'])
    source_ram['all_retained_producer_partial_sector_objects']=source_sectors*per_sector
    source_ram['cold_restored_partial_sector_objects']=source_sectors*per_sector
    source_ram['PC10_all_shared_sector_objects']=0 # source lazy __call__ unreachable before PC10
    source_ram['restore_port_dictionary_copy']=largest_port*old['RAM']['interpreter']['singleton_dict_bytes']
    raw_scoped_peak=sum(source_ram.values())
    streaming_ram=dict(source_ram);streaming_ram['serialization_workspace_bytes']=capture_workspace
    streaming_peak=sum(streaming_ram.values())
    preflight_ram={k:v for k,v in old['RAM']['components'].items()
        if k not in ('all_retained_producer_partial_sector_objects','cold_restored_partial_sector_objects',
                     'PC10_all_shared_sector_objects','restore_port_dictionary_copy','serialization_workspace_bytes',
                     'checkpoint_mmap_resident_bytes')}
    # Retain cached-array overcharges, two constructor mappings, all20 graphs,
    # complete diagnostics and native transient allowance even in no-op preflight.
    constructor_only_peak=sum(preflight_ram.values())
    return dict(schema='DS_PC01_ACTUAL_CHECKPOINT_FASTPATH_RESOURCE_REVIEW_V1',status='MODEL_ONLY_NO_ADMISSION',
        implementation_go=False,old_R64_guard_unchanged=True,actual_constructor_runs=0,numeric_runs=0,
        memory_object_lifetimes=dict(
            released_weight_files='External unchanged disk bytes; V3 saves only opened-shard identity/header/stamp, not weight payload copies.',
            immutable_initial_images='3840 per-owner wrappers point at40 immutable source paths; readonly file pages are shared kernel backing, not3840 independent file payloads. R64 mapped allowance retained.',
            parameter_access='NativeExecution loops rank-by-rank; PC0/1 provider reads selected checkpoint tensors into actual arrays, source run_buffer releases views each rank. No full-checkpoint preload.',
            initial_embedding='One selected BF16 row widenedF32 and repeated4planes, assigned96 readonly keys. Writer has no ndarray memo: saved payload must charge96 logical serialized copies; cold restore copies96 arrays.',
            produced_arrays='Each actual publication retains its source version/rank array until unchanged full-program last_use; no early source retirement discount.',
            raw_sectors='Union of every actually written source sector throughPC1, including2RF replicas. Raw contents remain even when version visibility is released.',
            snapshot='SectorBacking aliases live raw dictionary duringcapture; 46B records stream. Typed metadata tree and JSON coexist; no full payload BytesIO.',
            cold_restore='Payload is mmap-read, arrays copy, sector values decode; saved dictionaries and new port dictionary tables coexist but point atsame restored key/value objects.',
            process_boundary='R66 separate producer/cold processes can remove producer object coexistence onlyafter actual atomic seal, processgone and historicaljournal revalidation. Primary model doesnot take that credit.'),
        intended_gate=dict(full_native_PCs=2213,full_homes=290730,capture_boundary=0,cold_next_PC=1,
            final_native_PC=1,expected_PC0_publications=384,expected_PC1_publications=192,
            source_arithmetic_or_operand_versions_changed=False,expected_bytes_as_restore_payload=False),
        source_compact_frame_proof=dict(frames=frames,max_frame_bytes=max_frame,events_per_request=8,
            dictionary_static_RF_rank_records=96,sparse_index_charged_every_event=True,
            encoding='existing exact u64-varint lossless descriptor/metadata/checksum stream; no measured compression ratio',
            no_event_drop=True,source_schema_closure_requires_review=True),
        operator_prices=rows,journal_components=per,journal_phase_bytes=journals,
        disk=dict(fresh_producer_and_cold_journals=sum(journals),new_checkpoint_upper=checkpoint_upper,
            retained_R64_other_artifacts_and_diagnostics=other,total_fresh_run_bytes=disk_new,
            existing_latest_plus_previous_checkpoint_bytes=rotation_existing,
            staging_plus_latest_plus_previous_checkpoint_peak=rotation_existing+capture_phase_new,
            disk_new_with_two_retained_future_payload_snapshots=disk_new+rotation_existing,
            current_actual_PC9_checkpoint_exists=False,
            atomic_partial_must_be_preserved_on_failure=True,
            same_filesystem_atomic_rename_payload_copy_bytes=0,released_weights_embedded_in_checkpoint_bytes=0,
            full_released_weights_bytes=placement['all_released_shard_bytes'],selected_PC01_shards_bytes=placement['selected_shard_bytes'],
            source_existing_or_new_copy_must_be_per_filesystem=True,retained_historical_journals_never_pruned=True,
            failed_staging_not_deleted=True,weights_source_transfer_verified=False),
        RAM=dict(primary_proposal_retain_reviewed_RAM_bytes=ram,
            serialization_phase_R64_overcharge_bytes=replacement,
            proposed_typed_metadata_builtin_heap_multiplier=encoded_heap_multiplier,
            proposed_metadata_only_upper_bytes=metadata_only,
            proposed_streamed_capture_workspace_bytes=capture_workspace,
            prospective_replacement_total_bytes=prospective_RAM,
            prospective_replacement_admitted=False,
            source_PC01_sector_union=source_sectors,source_PC01_port_count=len(merged),
            source_PC01_partial_sector_object_bytes_per_constructor=source_sectors*per_sector,
            source_PC01_saved_dictionary_copy_bytes=largest_port*old['RAM']['interpreter']['singleton_dict_bytes'],
            source_PC01_all_initial_images_and_full_future_program_retained=True,
            source_scoped_existing_workspace_RAM_bytes=raw_scoped_peak,
            proposed_streamed_source_scoped_RAM_bytes=streaming_peak,
            actual_dual_constructor_only_source_component_bytes=constructor_only_peak,
            source_scoped_components=source_ram,proposed_streamed_source_scoped_components=streaming_ram,
            constructor_only_source_components=preflight_ram,
            raw_source_state_removed=False,actual_capture_project_required=True,
            later_PC2_to2212_future_homes_not_boxed_before_their_producers=True,
            two_live_constructor_graphs_retained_in_primary_proposal=True,
            sequential_fresh_process_option='R66 producer exit after atomic seal then cold process; no checkpoint/source journal deletion; exact old snapshot data persists; source implementation review needed',
            readonly_weight_pool_option='same dev/inode/stamp+header+payload/source identity; readonly maps and per-owner visibility/leases retained, separate owner wrappers; file-page alias proof only, no raw-state sharing',
            allocator_SQLite_peak_unknown=True,
            measured_R58_one_producer_PC0_9_peak_bytes=observed['max_rss_KiB']*1024,
            measured_R58_dual_constructor_capture_restore=False,
            measured_RSS_not_used_as_launch_upper_bound=True),
        prospective_hosts=host,
        physical_parent=dict(retained_source='cc4d800ac8c031449c56bea2c3c643c0a4a1320d',guest_roof_bytes=G,
            qemu_RSS_bytes=rss,qemu_PSS_bytes=pss,observed_shared_dirty_bytes=shared_known,
            shared_clean_bytes=shared_clean,unbacked_roof_minimum_bytes=unbacked,
            full_known_shared_COW_plus_unbacked_delta_bytes=current_known_delta,
            conservative_missing_shared_clean_delta_bytes=conservative_delta,
            physical_MemAvailable_bytes=physical['fresh_physical_parent']['host_MemAvailable_bytes'],
            PSS_difference_not_full_COW_cost=True,guest_plus_host_not_summed=True,
            retirement_owner_confirmations=[],scoped_fadvise_executed=False,host_reclaim_credit_bytes=0,
            cache_inventory_source='de9301e6472fde5633f1b3b7ed293ac4fdbf39be',
            W6_cache_candidate_resident_bytes=cache['W6_candidate_guest_resident_bytes'],
            owner_confirmed_retired_clean_files=cache['owner_confirmed_retired_clean_weight_files_identified'],
            cache_cleanliness_verified=cache['clean_dirty_page_state_verified'],
            cache_NFS_TCP2049=cache['configured_NFS']['transport_probe']['TCP2049'],
            current_known_no_credit_COW_deficit_bytes=max(0,current_known_delta-physical['fresh_physical_parent']['host_MemAvailable_bytes']),
            worst_missing_SharedClean_no_credit_deficit_bytes=max(0,conservative_delta-physical['fresh_physical_parent']['host_MemAvailable_bytes']),
            prospective_streaming_peer_growth_margin_bytes=physical['fresh_physical_parent']['host_MemAvailable_bytes']-streaming_peak,
            observed_guest_cache_eviction_alone_is_host_credit=False,
            guest_balloon_or_virtio_mem_observed=False,physical_reporting_or_discard_mechanism_verified=False,
            prospective_PC01_scoped_workspace_host_delta_upper=host_delta(allocation=raw_scoped_peak,unbacked=unbacked,shared_resident=rss),
            prospective_PC01_streamed_workspace_host_delta_upper=host_delta(allocation=streaming_peak,unbacked=unbacked,shared_resident=rss),
            constructor_only_host_delta_upper=host_delta(allocation=constructor_only_peak,unbacked=unbacked,shared_resident=rss),
            peer_job_growth_and_host_exclusive_lease_bytes=None,
            physical_admission=False),
        mandatory_source_changes=['New defaultoff launcher binds capture0/next1/reachablePC0..1, existing guards fixed9/10 cannot take JSON-only edit.',
            'Keep complete native/homes/dispatch/last_use source, same generation, original constructor and default arithmetic.',
            'Explicit owner-only run_scope transition and source-role enrollment; compare exactly retired subset, never weaken per-publication witness.',
            'Retain V3 quiescence/complete backing/typed codec/source contract/historical journal checks.',
            'Use existing compact source logger/schema identity; verify all reachable event variants and cost bounds before GO.',
            'R66 atomic capturefsync same-filesystem staging rename, immutable external receipt; distinct coldPID and sealed historical inventory verification.',
            'On .226 enroll output under existing persistent /home/ubuntu filesystem; reject tmpfs for disk-reserved output.',
            'Owner confirms retired cache candidates; fresh host+QEMU physical ownership proof and reservation before any fadvise or launch.'],
        retention_contract=['No current deletion or cache action.',
            'Only future full payload snapshots can rotate after newer coldrestore validates and all old mmap/read/owner leases retire.',
            'Keep latest+previous payloads plus new staging until seal; archive unique pass/failure records. Failed staging remains.',
            'Historical journals remain immutable at their original exact paths/stamps; payload retention does not grant journal pruning.',
            'Released model source files remain external readonly providers and are never replaced by witness bytes.'],
        gaps=['Full SharedClean/PrivateDirty/QEMU RAM-only residency and physical membership of .226 not yet enrolled.',
            'NFS2049 reported unreachable; existing mount capacity/permission is not admission.',
            'No source-confirmed retired file list or host reclaim mechanism/measurement; Cached is not a reclaim credit.',
            'Typed metadata multiplier proposal is not an allocator/SQLite highwater proof; prospective RAM is NOT launch guard.',
            'Remote source shard transfer/hash closure and all full-token future provider paths absent; only local metadata sizes known.',
            'PC0..1 is a mandatory actual full-shape checkpoint component gate; trained full2213 token remains unfinished.'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,default=D/'inputs');p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    raw=canonical(model(a.inputs))+b'\n'
    if a.verify:require(a.verify.read_bytes()==raw,'review replay differs')
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(raw)
    print('PASS_SOURCE_RESOURCE_REVIEW_NO_LAUNCH')

if __name__=='__main__':main()
