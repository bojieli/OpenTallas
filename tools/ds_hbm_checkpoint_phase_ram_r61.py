"""Source lifetime pricing; never replaces the frozen R58 runtime guard.
Writer streams SectorBacking and ndarray payloads; metadata uses only JSON
schema builtins. No live RSS used to lower a bound; no allocator-return credit.
"""
import json,sys,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/ds_hbm_checkpoint_execution_r58_20261003/model.json'


def phase_model(base,homes):
    c=base['RAM']['components'];cp=base['checkpoint']['components']
    metadata=base['checkpoint_new_bytes']-cp['resident_sector_payload_bytes']-cp['cached_array_payload_bytes']
    if metadata<=0:raise ValueError('complete positive metadata bound required')
    # CPython tagged Writer tree: dict/list/tuple/set are encoded with explicit
    # nonempty type tag. Scalar U64/float/bool/null/string nodes and container
    # tables fit64B per serialized JSON byte. No array/sector bytes in this tree.
    tree_heap=64*metadata
    serial=tree_heap+2*metadata+cp['cached_array_payload_bytes']+c['canonical_identity_and_lineage_workspace_bytes']+1048576
    rows=[];count=0
    for i,h in enumerate(homes):
        born=h.get('birth_pc',h.get('binding',{}).get('PC'))
        if born not in (8,9):continue
        ranks=h['rank_group'];kind=h['home']['class']
        if kind=='RF':
            if h['word_count']>128*h['home']['vectors']:raise ValueError('actual RF word bound')
            sectors=2*len(ranks)*((h['word_count']*4+31)//32)
        elif kind=='HBM_NATIVE_STATE':sectors=len(ranks)*((h['binding']['bytes']+31)//32)
        else:raise ValueError('unknown future port class')
        rows.append(dict(home_index=i,birth_PC=born,kind=kind,sector_upper=sectors));count+=sectors
    tail=dict(all_PC8_9_new_sector_objects=count*base['RAM']['interpreter']['sector_entry_bytes'],
      all_cached_array_payload_bytes=cp['cached_array_payload_bytes'],
      all_immutable_input_mapped_pages_bytes=base['RAM']['initial_and_auxiliary_mapped_file_bytes'],
      primitive_CPU_live_and_transient_bytes=c['native_primitive_CPU_live_and_transient_bytes'],
      full_observation_metadata_bytes=cp['four_complete_observation_metadata_copies_bytes'],
      helper_fixed_metadata_IO_bytes=cp['helper_fixed_metadata_and_IO_workspace_bytes'])
    existing_guard=max(base['cold_and_restore_new_RAM_bytes'],base['serialization_workspace_RAM_bytes'])
    required=existing_guard+serial+sum(tail.values())
    candidate=existing_guard-c['serialization_workspace_bytes']+serial
    return dict(schema='DS_CHECKPOINT_SOURCE_PHASE_RAM_R61',existing_R58_guard_bytes=existing_guard,
      checkpoint_metadata_serialized_upper_bytes=metadata,metadata_heap_multiplier=64,
      metadata_python_tree_heap_upper_bytes=tree_heap,serialization_only_increment_bytes=serial,
      cold_restore_candidate_with_all_other_components_retained_bytes=candidate,
      old_serialization_coexistence_overcharge_removed_bytes=c['serialization_workspace_bytes']-serial,
      preserved_original_components=c,future_PC8_9_home_rows=rows,future_PC8_9_sector_upper=count,
      remaining_before_guard_components=tail,
      held_R58_resume_MemAvailable_required_bytes=required,
      whole_producer_release_credit_bytes=0,allocator_return_credit_bytes=0,
      source_RSS_lowering_credit_bytes=0,existing_guard_changed=False,
      future_cold_candidate_adopted=False,source_ram_caps=False)


def verify_sources(pins):
    for name,want in pins.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want:raise ValueError('source drift: '+name)


def load_homes(path):return json.loads(gzip.decompress(Path(path).read_bytes()))
