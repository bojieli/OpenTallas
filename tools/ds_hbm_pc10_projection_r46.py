"""Complete source-matched PC0..10 software journal projection, no execution.

Synthetic hash/integer maxima below are RECORD-SIZE schemas only. They contain
no operands and never enter any provider/VM. Timing and hardware remain open.
"""
import gzip,hashlib,json
from collections import Counter
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,peer
from ds_hbm_source_prefix_r43 import model as inherited_model
from ds_hbm_storage_home_binding_r41 import bind_storage
from ds_hbm_prefix_observed_outputs_r42 import comparison_journal_cost
from ds_hbm_unconsumed_retirement_r45 import retirement_plan
from ds_hbm_pc10_journal_model_r44 import model as shared_model
from ds_hbm_pc10_engine_r44 import PC10_REFERENCE,PC10_REFERENCE_SHA

U=(1<<64)-1;HASH='f'*64
DEFAULT_OUTPUT=Path('/tmp/kepler-ds-r46-PC0-10-execution-20261002')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def reserve(v):return 8*(len(canonical(v))+64)


def source_inputs():
    D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs'
    def load(p):return json.loads(gzip.decompress(p.read_bytes()))
    original=load(ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz')
    manifest=load(D/'prefix_input_manifest.json.gz')
    native,homes,_,proof=bind_storage(original,load(D/'actual_DeepSeek_homes.json.gz')['homes'],manifest)
    if proof['effective_native_content_sha256']!='9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d':
        raise ValueError('complete exact bound source required')
    return native,homes,manifest


def source_receipt_schema(plan,rank,span,journal_path):
    parent=plan.parents[10];tid=parent['new_template'];node=plan.templates[tid]['code'][1+2*span['contributor']]
    reference=dict(template=tid,code_index=1+2*span['contributor'],opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],
                   operand='src:0',value='v0',logical_byte_offset=span['LOAD_flat_word_first']*4,payload_bytes=512)
    receipt=dict(event='C0_software_source_read_receipt',version=span['source_version'],rank=span['source_rank'],generation=1,
        field=None,producer_PC=9,journal_path=str(journal_path),journal_id=U,start=U,end=U,event_digest=HASH,
        accepted_sectors=16,source_words=128,payload_sha256=HASH,
        source_content_sha256='9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d',
        software_reverse_drained=True,hardware_qualified=False)
    proof=dict(schema='H4_DS_ACTUAL_OPERAND_JOURNAL_ADMISSION_V1',source_reference=reference,source_SSA_bytes=262144,
        owner=dict(PC=9,rank=span['source_rank'],SM=span['local_word_first']//256%32,generation=1,
                   version=span['source_version'],lease=f'group:10:{rank}:1:{span["source_version"]}'),
        logical_byte_address=U,physical_byte_address=U,physical_translation_bound=True,payload_bytes=512,
        sector32_transactions=16,scratch64_transactions=8,
        phase_counts={k:16 for k in ('request_accept','software_owned_issue','software_service_phases_reserved','software_read_capture',
                                     'consumer_accept','reverse_credit_accept','validated_reverse_grant')},
        peak_live_provider_tags=1,matching_reverse_drained=True,journal_sha256=HASH,additional_provider_RF_C0_I64_charge=0,
        cost_replacement=None,actual_lease_acquisition_and_release_journal=None,installed_home_directory_source_pin=None,
        whole_program_movement_complete=False,hardware_admitted=False,consumer_PC=10,consumer_rank=rank,
        translation_scope='explicit provider software backing namespace; not installed hardware',dispatch_binding_checked=True)
    return receipt,proof


def call_schema(plan,homes,rank,journal_path):
    parent=plan.parents[10];tid=parent['new_template'];writer=parent['writes'][0]
    indices=[i for i in writer['home_indices'] if rank in homes[i]['rank_group']]
    identity=dict(PC=10,rank=rank,generation=1,version=writer['version'],home_indices=indices)
    source=[];outputs=[];bridge_reservation=0
    for group in range(8):
        for first in range(0,1024,128):
            tile=plan.tile(10,rank,group,first)
            for span in tile['source_spans']:
                receipt,proof=source_receipt_schema(plan,rank,span,journal_path)
                bridge_reservation+=reserve(receipt)
                source.append(dict(receipt,source_operand_proof=proof))
            outputs.append(dict(version=writer['version'],rank=rank,generation=1,first=tile['output_flat_word_first'],bytes=512,
                payload_sha256=HASH,pending_obligations=0,
                state='actual_published' if tile['tile_ordinal']==63 else 'unpublished_charged_staging'))
    fragment=dict(target='DeepSeek',rank=rank,epoch=1,pc=10,serial=U,sector=U)
    publication=dict(identity=identity,payload_sha256={'data':HASH},
        events=[dict(event=e,identity=identity,sequence=U,source_fragment_identity=fragment,source_tag=U,source_tag_generation=U,source_tick=U)
                for e in ('software_backing_visible','consumer_accept','validated_reverse_grant')],pending_obligations=0,physical_qualified=False)
    journal=dict(journal_id=U,start=U,end=U,sector_transactions=U,actual_RF_mirrors=2,required_write_sectors=U,
        all_required_mirror_sectors_reverse_drained=True)
    ops=sorted({n['op'] for n in plan.templates[tid]['code']})
    import hbm_provider_microvm_r21 as sector
    defaults=sector.SectorProvider({})
    result=dict(schema='H4_DS_EXECUTED_GROUP128_JOURNAL_KERNEL_V1',PC=10,rank=rank,generation=1,
        source_native_sha256=plan.inventory['source_native_sha256'],source_dispatch_sha256=plan.inventory['source_dispatch_sha256'],
        tiles_executed=64,source_spans=512,output_spans=64,shared_capacity_per_SM=65536,reserved_shared_bytes=8704,
        peak_RF_vectors=32,executed_primitive_scalars={k:U for k in ops},executed_steps={k:U for k in ops},
        actual_shared_movements={k:U for k in ('sector32','scratch64','write512','read512')},
        actual_movement_proof_chain_sha256=HASH,output_sha256=HASH,output_span_receipts=outputs,
        explicit_provisional_sector_parameters=dict(phase_costs=dict(defaults.costs),read_ticks=defaults.read_ticks,write_ticks=defaults.write_ticks,tag_capacity=1),
        actual_serial_sector_service_software_ticks=U,scratch64_endpoint_cost=None,primitive_endpoint_costs=None,
        actual_RF_mirror_journal=journal,physical_address_translation=None,native_C0_provider_RF_I64_cost_added=0,
        full_program_executed=False,production_unknown_shared_calls=193316,whole_token_latency=None,hardware_admitted=False,
        actual_source_receipts=source,actual_publication=publication,actual_result_journal=journal,
        source_global_view_released=True,source_version_retired=False,unpublished_output_staging_bytes=32768,
        total_operand_and_staging_bound_bytes=41472,actual_provider_writer=True,
        production_payload_provenance='caller-retained producer backing; qualification belongs to full driver/input receipts',
        production_calls_closed=0,publication=publication,
        original_native_artifact_sha256=plan.inventory['source_native_sha256'],
        native_artifact_sha256='1bca266785a062b9396f6704116982b5944a1f915b8acdad945000b3d7ba612d',
        hardware_qualified=False,physical_primitive_port_calendar_bound=False)
    return dict(event='C0_actual_native_group_call',record=result),bridge_reservation


def exact_PC10_RF_requests(plan,homes):
    parent=plan.parents[10];producer=parent['provider_bindings'][parent['new_template']]['parts']['version']
    reads=0;writes=0;readback=0
    source_homes={r:[h for h in homes if h['version']==producer and r in h['rank_group']] for r in range(64)}
    for group in range(8):
        for first in range(0,1024,128):
            for span in plan.tile(10,0,group,first)['source_spans']:
                sm=first//256%32;selected=[h for h in source_homes[span['source_rank']] if h['SM']==sm]
                if len(selected)!=1:raise ValueError('exact contiguous source RF home required')
                h=selected[0]
                if h['partition']!='chunk32_block256' or h['word_count']!=256 or h['home']['class']!='RF':raise ValueError('selected PC9 RF packing changed')
                byte=sm*2*262144+h['home']['slot_first']*512+(first%256)*4
                if byte%32 or byte+512>16777216:raise ValueError('selected source RF span alignment/bounds')
                if first%256+128>h['word_count']:raise ValueError('selected source span exceeds home')
                reads+=len({(byte+4*j)//32 for j in range(128)})
    for rank in range(96):
        ix=[i for i in parent['writes'][0]['home_indices'] if rank in homes[i]['rank_group']]
        if len(ix)!=32 or {homes[i]['SM'] for i in ix}!=set(range(32)):raise ValueError('complete32SM output mapping required')
        for i in ix:
            h=homes[i]
            if h['home']['class']!='RF' or h['word_count']!=256 or h['home']['vectors']!=2:raise ValueError('selected output RF packing changed')
            for copy in range(2):
                byte=(h['SM']*2+copy)*262144+h['home']['slot_first']*512
                if byte%32 or byte+1024>16777216:raise ValueError('mirrored RF output extent')
                writes+=len({(byte+4*j)//32 for j in range(256)})
            readback+=h['word_count']//8
    return dict(source_RF_read_sectors=96*reads,mirrored_RF_write_sectors=writes,RF_readback_sectors=readback,
                total=96*reads+writes+readback,source_words_per_span=128,aligned_sectors_per_span=16,
                source_RF_homes_and_W19_chunks_validated=True,physical_RF_second_return_payload_discounted=False)


def prefix_metadata_reservation(native,journal_path):
    # Exact data-free SourceViews call census for this selected prefix: PC4
    # independent buffers, then PC8 q/window reads in <=128-word batches.
    profile=[];bridge=0;numeric=0;numeric_count=0
    for op in native['instructions'][:10]:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            buffers=owned.get('buffer_programs') or [dict(template=owned['template'])]
            for b in buffers:
                template=native['templates'][b['template']]
                selected=op['writes'] if 'write_version' not in b else [w for w in op['writes'] if w['version']==b['write_version']]
                record=dict(PC=op['pc'],rank=owned['rank'],template=b['template'],source_native_stages=len(template['code']),
                    native_mode='unchanged_source_Machine_live_range_CPU_SSA',native_opcode_counts=dict(Counter(n['op'] for n in template['code'])),
                    published_versions=[w['version'] for w in selected],full_token_exact_qualified=False,physical_qualified=False)
                numeric+=reserve(dict(event='C0_actual_native_numeric_call',record=record));numeric_count+=1
                calls=[]
                if op['family']=='all_gather':
                    producer,writer=next((o,w) for o in native['instructions'][:op['pc']] for w in o['writes'] if w['version']==b['read_version'])
                    if not isinstance(writer['producer_extent'],list) or len(writer['producer_extent'])!=96:raise ValueError('selected prefix producer extent changed')
                    calls=[(producer['pc'],b['read_version'],r) for r,(lo,hi) in enumerate(writer['producer_extent']) if hi>lo]
                elif op['family']=='attend':
                    bindings=op['provider_bindings'][b['template']]
                    q=bindings['q_own'];rows=bindings['rows']
                    qwords=1
                    for d in template['providers']['q_own']['shape']:qwords*=d
                    calls.extend([(7,q['version'],owned['rank'])]*((qwords+127)//128))
                    versions=rows['additional_versions']
                    if len(versions)!=2 or op['source_op']['yarn']:raise ValueError('selected prefix window-only source changed')
                    calls.extend([(5,rows['version'],owned['rank'])]*(128*512//128))
                for pc,version,rank in calls:
                    receipt=dict(event='C0_software_source_read_receipt',version=version,rank=rank,generation=1,field=None,producer_PC=pc,
                        journal_path=str(journal_path),journal_id=U,start=U,end=U,event_digest=HASH,accepted_sectors=U,source_words=16384,
                        payload_sha256=HASH,source_content_sha256='9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d',
                        software_reverse_drained=True,hardware_qualified=False)
                    bridge+=reserve(receipt)
                if calls:profile.append(dict(PC=op['pc'],destination_rank=owned['rank'],template=b['template'],source_read_receipt_records=len(calls)))
    return dict(source_read_receipt_records=sum(r['source_read_receipt_records'] for r in profile),
                bridge_receipt_reservation_bytes=bridge,numeric_call_records=numeric_count,numeric_call_reservation_bytes=numeric,
                source_profiles=profile)


def project(native,homes,manifest,*,output_root=DEFAULT_OUTPUT):
    output_root=Path(output_root)
    if not output_root.is_absolute():raise ValueError('actual absolute output root required for record-size projection')
    base=inherited_model(native,homes,10)
    prefix_comparison=comparison_journal_cost(native,homes)['additional_page_index_reservation_bytes']
    plan=peer('h4_c0_ds_tiled_continuation').GroupOperandTiles()
    journal_path=output_root/'actual-prefix-journal/events.sqlite'
    prefix_meta=prefix_metadata_reservation(native,journal_path)
    calls=[];bridge=0
    for rank in range(96):
        record,additional=call_schema(plan,homes,rank,journal_path)
        bridge+=additional
        calls.append(dict(rank=rank,serialized_upper_bytes=len(canonical(record)),page_index_reservation_bytes=reserve(record)))
    raw=PC10_REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PC10_REFERENCE_SHA:raise ValueError('PC10 observer reference pin')
    rows=json.loads(raw)['expectations'];observed=0
    for row in rows:
        event=dict(event='DS_r44_PC10_observed_output',identity={k:row[k] for k in ('PC','rank','generation','version','home_indices')},
            field='data',shape=[8192],dtype='<f4',payload_sha256=HASH,byte_exact=True,reference_sha256=PC10_REFERENCE_SHA,hardware_qualified=False)
        observed+=reserve(event)
    retirement=retirement_plan(native,manifest,homes);retire_events=[]
    for pc,versions in retirement.items():
        if pc>10:continue
        for version in versions:
            retire_events.append(dict(event='source_unconsumed_output_retired',PC=pc,version=version,generation=manifest['generation'],
                producer_all_rank_reverse_retirement_complete=True,source_or_manifest_consumer_references=0,hardware_qualified=False))
    shared=shared_model();components=dict(
        inherited_RF_state_sector_bound=base['journal_capacity_bytes'],
        inherited_1568_output_comparisons=prefix_comparison,
        explicit_PC0_9_source_read_receipt_journals=prefix_meta['bridge_receipt_reservation_bytes'],
        explicit_PC0_9_numeric_call_records=prefix_meta['numeric_call_reservation_bytes'],
        additional_PC10_96_output_comparisons=observed,
        additional_PC10_49152_source_read_receipts=bridge,
        additional_PC10_96_full_group_call_records=sum(c['page_index_reservation_bytes'] for c in calls),
        additional_PC10_shared_sector_journals=shared['shared_only_journal_reservation_bytes'],
        unconsumed_retirement_records=sum(reserve(e) for e in retire_events))
    # Tick/sequence/generation upper strings are finite source-derived bounds:
    # <=18M inherited+1.8M shared requests, <=8 events/request; existing service
    # <=128 ticks/request. Bounds are far below uint64. No uint64 hardware timer.
    rf=exact_PC10_RF_requests(plan,homes)
    legacy=next(o for o in base['ops'] if o['PC']==10)['software_sector_request_conservative_bound']
    envelope=base['event_serialization_envelope_bytes']
    old_sector_reservation=legacy*8*8*(envelope+64)
    exact_sector_reservation=rf['total']*8*8*(envelope+64)
    exact_components=dict(components)
    exact_components['inherited_RF_state_sector_bound']-=old_sector_reservation-exact_sector_reservation
    total_requests=base['sector_requests_conservative_bound']+shared['sector_transactions']
    return dict(schema='DS_PC0_10_COMPLETE_SOFTWARE_JOURNAL_PROJECTION_R46',output_root=str(output_root),
        projection_complete_for_selected_runtime_journals=True,journal_capacity_bytes=sum(components.values()),components=components,
        complete_conservative_inherited_projection_bytes=sum(components.values()),
        source_addressed_candidate_projection_bytes=sum(exact_components.values()),source_addressed_components=exact_components,
        PC10_RF_sector_address_derivation=rf,retained_legacy_PC10_RF_sector_bound=legacy,
        source_addressed_RF_event_reservation_bytes=exact_sector_reservation,
        selected_runtime_projection='conservative inherited projection retained until parent reviews source-addressed refinement',
        integer_schema_upper=U,finite_request_upper=total_requests,finite_sector_tick_upper=total_requests*128,
        actual_numeric_or_provider_requests_executed=0,schema_hashes_are_size_placeholders_not_stimuli=True,
        group_call_records=calls,source_read_receipts=96*512,expected_output_comparisons=1664,
        prefix_metadata=prefix_meta,legacy_generic_metadata_overhead_retained_without_credit=True,
        shared_reserved_bytes=96*32*65536,operand_and_unpublished_output_bound_bytes=41472,
        CPU_native_workspace_upper_bytes=base['CPU_native_workspace_upper_bytes'],
        physical_RF_readpair_response_bytes=96*512*1024,unused_second_RF_payload_charged=True,
        inherited_RF_read_and_write_bounds_not_replaced=True,
        physical_critical_path_edges=None,physical_service_or_macro_fit_admitted=False,
        software_shared_serial_ticks=shared['software_all_serial_sector_ticks'],software_ticks_not_hardware_cycles=True,
        required_runtime_lineage='same provider instance; actual PC0..9 retirement and all64 PC9 witnessed RF publications before PC10',
        runtime_GO=False,PC10_numerical_launch_performed=False,
        prerequisites=['R45 stop9 numerical PASS','fresh complete provider/witness/composed-engine preflight',
                       'parent source review and numerical GO','fresh disk >= projected capacity; retained failures remain'],
        hardware_admitted=False,full_token_GO=False)

if __name__=='__main__':
    n,h,m=source_inputs();print(json.dumps(project(n,h,m),sort_keys=True,indent=2))
