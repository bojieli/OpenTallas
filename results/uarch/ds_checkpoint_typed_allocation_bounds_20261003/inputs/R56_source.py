"""PC9 source-addressed checkpoint and two-journal host resource composition.
No payload execution. No hardware memory/area credit, transport rate or clock.
Every byte refers to newly allocated host files/RAM; already existing inputs
and terminal historical journals stay in used space. Originals stay pinned.
"""
import argparse,copy,gzip,json,math,os,sys
from hbm_bound_event_journal_r30 import CompactSectors
from pathlib import Path
import ds_hbm_checkpoint_storage_r55 as old
import ds_hbm_pc10_projection_r46 as journal
import ds_hbm_source_prefix_r45 as prefix
import ds_producer_checkpoint_resume_v3 as helper
from h3_ds_connected_provider_r37 import ROOT,D
from ds_hbm_connected_prepare_r37 import load,sha

OUT=ROOT/'results/uarch/ds_hbm_dual_resources_r56_20261003'

def merge(intervals):
    answer=[]
    for a,b in sorted(intervals):
        if type(a)is not int or type(b)is not int or a<0 or b<=a:raise ValueError('positive source address interval')
        if answer and a<=answer[-1][1]:answer[-1][1]=max(answer[-1][1],b)
        else:answer.append([a,b])
    return answer


def source_sector_homes(native,homes,manifest):
    """Price reserved RF vectors in both copies and all immutable state homes.
    Retired contents persist in backing: union ALL writes, not just live versions.
    All initial state homes charged even if not read in this prefix. Shared
    provider is lazy and first created by PC10, after the PC9 checkpoint.
    """
    if [o['family'] for o in native['instructions'][:11]]!=old.FAMILIES:raise ValueError('exact prefix required')
    rf={};state={};selected=[]
    for i,h in enumerate(homes):
        if 'birth_pc' in h:born=h['birth_pc']
        elif h['home']['class']=='HBM_NATIVE_STATE':born=h['binding']['PC']
        else:raise ValueError('source home birth identity absent')
        if born>9:continue
        selected.append(i)
        for rank in h['rank_group']:
            if h['home']['class']=='RF':
                sm=h['SM'];vectors=h['home']['vectors'];slot=h['home']['slot_first']
                if not 0<=sm<32 or not 0<=slot<512 or slot+vectors>512:raise ValueError('RF source slot bound')
                for replica in (0,1):
                    a=(sm*2+replica)*512*128*4+slot*512
                    rf.setdefault(rank,[]).append([a,a+vectors*512])
            elif h['home']['class']=='HBM_NATIVE_STATE':
                b=h['binding'];state.setdefault(rank,[]).append([b['base'],b['base']+b['reservation_bytes']])
            else:raise ValueError('unsupported native source home class')
    for image in manifest['initial_versions']:
        if 'home' not in image:continue
        h=image['home'];state.setdefault(image['rank'],[]).append([h['base'],h['base']+h['reservation_bytes']])
    rows=[]
    for kind,table in [('rf',rf),('state',state)]:
        for rank,spans in sorted(table.items()):
            rounded=[[a//32,(b+31)//32] for a,b in spans]
            rows.append(dict(kind=kind,rank=rank,sector_ranges=merge(rounded)))
    count=sum(b-a for r in rows for a,b in r['sector_ranges'])
    return dict(boundary_pc=9,selected_source_home_count=len(selected),rows=rows,
                resident_sector_upper=count,ports_upper=len(rows),shared_ports_at_boundary=0,
                released_raw_contents_retained=True,initial_state_extents_all_charged=True,
                hardware_capacity_unchanged=True)


def heap(value):
    return helper.deep_metadata_bytes(value)


def ram_model(native,homes,manifest,sector_model,checkpoint_model,legacy):
    """Explicit CPython allocation schema for coexistence, no process limits.
    Charge every sector as a partial32-element list AND dict/key ownership;
    full bytearrays cost less. All32 pointer slots are priced. CPython byte atoms are source-proven
    cached immutable objects and charged as a full256-entry table per port,
    with a runtime refusal if that representation differs.
    A singleton dict charges its entire allocation per entry, overpricing all
    larger tables. Saved/restored arrays, mmap payload, immutable mapped pages,
    constructor identity/canonical JSON/lineage copies all charged separately.
    """
    if sys.implementation.name!='cpython':raise ValueError('priced CPython allocation layout required')
    rawbytes=bytes(range(256))
    if any(rawbytes[i] is not int(str(i)) for i in range(256)):
        raise ValueError('source-byte cached atoms require repricing on this interpreter')
    partial=CompactSectors({('DeepSeek',95,old.U):[None]*32})
    singleton=sys.getsizeof(partial)+sys.getsizeof(vars(partial))
    key=sys.getsizeof(('DeepSeek',95,old.U))+sys.getsizeof('DeepSeek')+2*sys.getsizeof(old.U)
    value=sys.getsizeof([None]*32)
    per_sector=singleton+key+value
    # Largest copied port dictionary in apply_port_state coexists temporarily.
    sectors=sector_model['resident_sector_upper']
    largest_port=max(sum(b-a for a,b in r['sector_ranges']) for r in sector_model['rows'])
    raw=sectors*per_sector
    manifest_heap=heap(manifest);program_heap=heap(native);homes_heap=heap(homes)
    # Enumerated source allocation slots, each bounded by the complete source
    # graph. They do not assume object sharing across constructor/lineage paths.
    slots=[
      'R55 runner original native','R55 runner bound native','R55 bound homes and original homes',
      'R41 bind_storage copied native','R41 bind_storage restored native','R41 expanded and original homes',
      'R43 validate_lineage original native','R43 validate_lineage original homes',
      'R43 validate_lineage expected native','R43 validate_lineage expected homes',
      'R43 validate_lineage decoded bound native','GroupOperandTiles native/parents/templates',
      'TokenDriver allocations and source ownership','ProductionPC10 exact regenerated directory',
      'Witness expected dictionary and initialization provenance','checkpoint typed closure/source inventory',
      'cold constructor corresponding lineage and group-plan retained graphs',
      'V3 restore saved metadata tree','V3 restore verified/source/role manifests',
      'runner active metadata and import/source snapshots']
    graph=program_heap+homes_heap+manifest_heap
    constructors=len(slots)*graph
    # Canonical serializations have2 simultaneous operands in equality tests;
    # encode bytes + unicode for both, plus gzip input/output/intermediate.
    json_bytes=len(helper.canonical(native))+len(helper.canonical(homes))+len(helper.canonical(manifest))
    canonical_workspace=2*(sys.getsizeof(helper.canonical(native))+sys.getsizeof(helper.canonical(homes))+sys.getsizeof(helper.canonical(manifest)))+2*json_bytes
    initial_file_bytes=sum(Path(v['path']).stat().st_size for v in manifest['initial_versions'])
    # Constructor auxiliary arrays are lazy. Charge every declared explicit
    # source image too, even those first used after PC10. No checkpoint shards
    # preloaded: source LockedCheckpoint copies selected tensor rows only.
    auxiliary_paths={v['path'] for v in manifest.get('view_bindings',{}).values() if isinstance(v,dict) and 'path' in v}
    auxiliary_file_bytes=sum((ROOT/p).stat().st_size if not Path(p).is_absolute() else Path(p).stat().st_size for p in auxiliary_paths)
    mapped=initial_file_bytes+auxiliary_file_bytes
    arrays=checkpoint_model['components']['cached_array_payload_bytes']
    components=dict(source_byte_atom_tables=(192+192+96*32)*sum(sys.getsizeof(i) for i in range(256)),
      all_retained_producer_partial_sector_objects=raw,
      cold_restored_partial_sector_objects=raw,
      restore_port_dictionary_copy=largest_port*singleton,
      producer_cached_source_array_bytes=arrays,cold_restored_cached_array_bytes=arrays,
      immutable_inputs_mapped_twice_bytes=2*mapped,
      exact_source_metadata_allocation_slots_bytes=constructors,
      canonical_identity_and_lineage_workspace_bytes=canonical_workspace,
      checkpoint_mmap_resident_bytes=checkpoint_model['checkpoint_new_bytes'],
      native_primitive_CPU_live_and_transient_bytes=legacy['CPU_native_workspace_upper_bytes'],
      serialization_workspace_bytes=checkpoint_model['checkpoint_new_bytes']+constructors+canonical_workspace)
    # Duplicate shared PC10 backing charged separately from checkpoint state.
    # Each of3072 real shared providers may fill its charged64KiB aperture.
    shared=96*32*(65536//32)*per_sector
    components['PC10_all_shared_sector_objects']=shared
    peak=sum(components.values())
    # R55 requires a producer + max(serialization,cold_restore) decomposition.
    # Allocate all non-raw components to cold/serialization conservatively;
    # producer raw is included separately. Their sum exactly equalspeak.
    producer=raw+arrays
    rest=peak-producer
    return dict(components=components,coexistence_RAM_peak_bytes=peak,
        producer_new_RAM_bytes=producer,cold_and_restore_new_RAM_bytes=rest,
        serialization_workspace_RAM_bytes=rest,
        interpreter=dict(implementation=sys.implementation.name,version=sys.version,sector_entry_bytes=per_sector,
                         singleton_dict_bytes=singleton,key_bytes=key,partial_value_bytes=value),
        metadata_source_graph_bytes=graph,metadata_allocation_slots=slots,
        initial_and_auxiliary_mapped_file_bytes=mapped,all_shared_apertures_charged=True,
        no_RSS_measurement_used_as_upper_bound=True,process_RAM_cap=False)


def model(native,homes,manifest,*,output_root):
    output_root=Path(output_root)
    original=old.model(native,homes,manifest,output_root=output_root)
    sectors=source_sector_homes(native,homes,manifest)
    refined=copy.deepcopy(original)
    refined['components']['resident_sector_payload_bytes']=sectors['resident_sector_upper']*helper.SECTOR_RECORD.size
    refined['checkpoint_new_bytes']=sum(refined['components'].values())
    refined['resident_sector_upper']=sectors['resident_sector_upper']
    # Retain ALL old non-sector metadata and array overcharges, including3072
    # shared-port metadata rows not created atPC9. No payload/identity omitted.
    refined['old_checkpoint_new_bytes']=original['checkpoint_new_bytes']
    refined['hardware_capacity_credit']=0
    legacy=prefix.model(native,homes,10)
    producer=prefix.model(native,homes,9)
    retained=load(ROOT/'results/uarch/ds_hbm_current_calendar_join_r50_20261002/model.json')
    # Exact R46 non-sector sizes retained. Source paths differ in length:
    # reserve the full longer path on each repeated source-read receipt/call.
    root_extra=max(0,len(str(output_root/'actual-continuation-journal/events.sqlite'))-len(retained['output_root']+'/actual-prefix-journal/events.sqlite'))
    path_extra=8*root_extra*(49152+96*512+928*96)
    compact=None
    # Compact shared proof is pinned in published successor receipts. This
    # model retains that source-bound transaction/dictionary/index cost.
    published=ROOT/'results/uarch/h3_complete_native_calendar_20261002/c0_program_shared64_r1/R46_source_pins.json'
    if not published.exists():raise ValueError('published exact compact source schema required')
    import h3_complete_native_calendar_successor_r1 as calendar
    import ds_hbm_pc10_journal_model_r44 as shared
    required=['tools/ds_hbm_pc10_projection_r46.py','tools/ds_hbm_pc10_journal_model_r44.py',
              'tools/h4_hbm_w19_pc10_endpoints.py','tools/hbm_provider_microvm_r21.py']
    regenerated=calendar.project_r46_compact_shared_journal(retained,shared.model(),
        {p:(ROOT/p).read_bytes() for p in required})
    compact=regenerated['compact_shared_component_bytes']
    if regenerated['complete_disk_reservation_bytes']!=819950818992:
        raise ValueError('source-matched published compact projection changed')
    if legacy['journal_capacity_bytes']!=retained['components']['inherited_RF_state_sector_bound']:
        raise ValueError('retained conservative RF request envelope changed')
    c=retained['components'];restore_headers=sectors['ports_upper']*8192
    # Selected finite PC10 does not execute generic complete-parts LOAD. Its
    # source uses512 acquisitions per rank, each128 words; exact16 aligned
    # 32B sectors per acquisition, plus BOTH mirror writes and readback. Prove
    # every span and home against the unchanged source plan and addresses.
    plan=journal.peer('h4_c0_ds_tiled_continuation').GroupOperandTiles()
    exact=journal.exact_PC10_RF_requests(plan,homes)
    legacy_PC10=next(o['software_sector_request_conservative_bound'] for o in legacy['ops'] if o['PC']==10)
    if exact['total']!=1081344 or legacy_PC10!=7667712:
        raise ValueError('exact selected PC10 RF/source request count changed')
    removed_generic=(legacy_PC10-exact['total'])*8*8*(legacy['event_serialization_envelope_bytes']+64)
    # Keep this failed/inadequate generic-host projection as a separate record.
    # No source runtime or physical port is modified by choosing the proven
    # host-log count. Prefix0..9 request/event envelopes remain unchanged.
    producer_capacity=(producer['journal_capacity_bytes']+c['inherited_1568_output_comparisons']+
      c['explicit_PC0_9_source_read_receipt_journals']+c['explicit_PC0_9_numeric_call_records']+
      c['unconsumed_retirement_records']+path_extra)
    continuation_capacity=(legacy['journal_capacity_bytes']-producer['journal_capacity_bytes']-removed_generic+131072+
      c['additional_PC10_96_output_comparisons']+c['additional_PC10_49152_source_read_receipts']+
      c['additional_PC10_96_full_group_call_records']+compact+c['unconsumed_retirement_records']+
      restore_headers+4*8192+path_extra)
    # Other host artifacts: regenerated bound_native/homes, both manifests,
    # identity/storage receipts and runner receipt completeJSON copies. Price
    # uncompressed originals (gzip bounded <=input+framing separately charged).
    other=2*(len(helper.canonical(native))+len(helper.canonical(homes)))+6*len(helper.canonical(manifest))+refined['components']['six_source_identity_and_contract_copies_bytes']+65536
    ram=ram_model(native,homes,manifest,sectors,refined,legacy)
    return dict(schema='DS_HBM_PC9_CAPTURE_DUAL_JOURNAL_RESOURCES_R56',
      checkpoint=refined,source_sector_homes=sectors,RAM=ram,
      producer_journal_new_bytes=producer_capacity,continuation_journal_new_bytes=continuation_capacity,
      journal_new_bytes=producer_capacity+continuation_capacity,
      checkpoint_new_bytes=refined['checkpoint_new_bytes'],other_new_bytes=other,
      producer_new_RAM_bytes=ram['producer_new_RAM_bytes'],cold_and_restore_new_RAM_bytes=ram['cold_and_restore_new_RAM_bytes'],
      serialization_workspace_RAM_bytes=ram['serialization_workspace_RAM_bytes'],
      journal_derivation=dict(legacy_RF_state_bound=legacy['journal_capacity_bytes'],producer_RF_state_bound=producer['journal_capacity_bytes'],
        additional_continuation_dictionary_bootstrap_bytes=131072,restored_port_event_index_headers_bytes=restore_headers,
        fresh_control_stream_headers_bytes=4*8192,compact_shared_full_source_bound_bytes=compact,
        per_phase_path_length_extra_bytes=path_extra,retirement_records_charged_to_both_phases=True,
        source_addressed_PC10_RF_counts=exact,unselected_generic_PC10_RF_requests=legacy_PC10,
        unselected_generic_request_overcharge_removed_host_bytes=removed_generic,
        RF_prefix_request_counts_and_event_envelope_unchanged=True,
        physical_RF_second_return_capacity_traffic_and_costs_unchanged=True,
        new_journal_dictionary_index_accounted=True),
      projection_complete=True,actual_numerical_execution=False,hardware_qualified=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args();n,h,m=journal.source_inputs();v=model(n,h,m,output_root=args.output_root)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ('producer_journal_new_bytes','continuation_journal_new_bytes','checkpoint_new_bytes','other_new_bytes')}))
    print('coexistence_RAM_peak_bytes',v['RAM']['coexistence_RAM_peak_bytes'])
