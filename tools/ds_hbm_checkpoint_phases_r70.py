"""Additive all-port table lifetime gate; frozen R69 remains byte-identical."""
import json
import hashlib
from pathlib import Path
import ds_hbm_checkpoint_phases_r69 as original
import ds_checkpoint_typed_allocation_bounds as peer

SCHEMA = 'R70_ALL_PORT_COLD_COPY_PROOF'
PEER_SOURCE_SHA='0213cc14c65d86f69f61dd6066813b1b41234a86436af495bd22fa4eea570f19'
PEER_MODEL_SHA='9797b3fa6123d991c780a25db6d2664c65841cf7bc9a842f7f5bdabe74e49e48'

def source_ledger(root):
    root = Path(root)
    result = original.source_ledger(root)
    pc01 = json.loads((root / 'results/uarch/ds_pc01_checkpoint_fastpath_review_20261003/model.json').read_text())['RAM']
    profile = json.loads((root / 'results/uarch/ds_hbm_checkpoint_readiness_r64_20261003/preflight_model.json').read_text())['RAM']['interpreter']
    entries = pc01['source_PC01_sector_union']
    ports = pc01['source_PC01_port_count']
    table_unit = profile['singleton_dict_bytes']
    retained = result['retained_base_components']['restore_port_dictionary_copy']
    if (entries, ports, table_unit, retained) != (738048, 96, 352, 2706176):
        raise ValueError('source PC01 table/interpreter ledger changed; reprice explicitly')
    peer_root=root/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003'
    if hashlib.sha256(Path(peer.__file__).read_bytes()).hexdigest()!=PEER_SOURCE_SHA or hashlib.sha256((peer_root/'model.json').read_bytes()).hexdigest()!=PEER_MODEL_SHA:
        raise ValueError('pinned Peirce972 source/model required')
    profile=peer.frozen_r69_restore_correction(peer_root)
    if profile!=json.loads((peer_root/'model.json').read_bytes())['restore_correction']:
        raise ValueError('fresh Peirce972 correction differs from frozen profile')
    if (profile['restored_sector_upper'],profile['restored_port_upper'],
        profile['existing_singleton_table_allowance'],profile['old_largest_only_allowance_bytes'])!=(entries,ports,table_unit,retained):
        raise ValueError('exact Peirce972 all-port profile required')
    gross = profile['all_table_copies_upper_bytes']
    header = profile['all_empty_table_headers_upper_bytes']//ports
    result.update(schema='R70_ALL_PORT_CHECKPOINT_PHASE_LEDGER',
        parent_schema='R69_CHECKPOINT_PHASE_LEDGER',
        restore_table_accounting=dict(restored_sector_entries_upper=entries,
            restored_nonempty_ports_upper=ports, table_only_unit_upper_bytes=table_unit,
            per_port_header_upper_bytes=header,
            conservative_all_port_table_upper_bytes=gross,
            original_largest_only_bytes_already_retained=retained,
            mandatory_extra_copy_upper_bytes=gross-retained,
            source_profile_commit='972c35b3970c58b3a5ef1958c4c403a280b645c2',
            source_profile_sha256=PEER_MODEL_SHA,
            raw_keys_values_arrays_charged_again=False,
            source='V3 restore saved=read_tree; saved ports remain live while every apply_port_state creates CompactSectors table; shared ports repeat same path.'),
        required_restore_proof_schema=SCHEMA,
        required_restore_proof_fields=['restore_dictionary_tables_complete',
            'restored_sector_entry_upper', 'restored_port_count_upper',
            'restore_all_port_table_extra_upper_bytes'])
    result['phase_allocations']['cold_restore'] += (
        ' Largest-only copy is insufficient: all saved old tables and all new CompactSectors tables coexist. '
        'Explicit extra table-only bound is mandatory; raw keys/values remain shared and are not recharged.')
    result['required_positive_phase_fields'] += ['restore_all_port_table_extra_upper_bytes']
    return result

def compose(ledger, proof):
    if proof.get('restore_proof_schema') != SCHEMA or proof.get('restore_dictionary_tables_complete') is not True:
        raise ValueError('complete all-port table lifetime source proof required')
    table = ledger['restore_table_accounting']
    entries, ports, extra = (proof.get(k) for k in
        ('restored_sector_entry_upper', 'restored_port_count_upper', 'restore_all_port_table_extra_upper_bytes'))
    if any(type(v) is not int or v <= 0 for v in (entries, ports, extra)):
        raise ValueError('positive explicit all-port counts/copy bound required')
    if entries < table['restored_sector_entries_upper'] or ports < table['restored_nonempty_ports_upper']:
        raise ValueError('all restored ports and entries must be covered')
    required_extra = (entries * table['table_only_unit_upper_bytes']
        + ports * table['per_port_header_upper_bytes']
        - table['original_largest_only_bytes_already_retained'])
    if extra < required_extra:
        raise ValueError('largest-only or insufficient aggregate table copy bound')
    adapted = dict(proof)
    old_cold = adapted.get('cold_json_parse_upper_bytes')
    if type(old_cold) is not int or old_cold <= 0:
        raise ValueError('positive original cold JSON parse bound still required')
    adapted['cold_json_parse_upper_bytes'] = old_cold + extra
    result = original.compose(ledger, adapted)
    result.update(restore_table_only_extra_bytes=extra,
                  old_largest_only_bytes_not_charged_twice=True,
                  original_cold_JSON_parse_bytes=old_cold,
                  all_port_copy_added_to_cold_live_phase_only=True)
    return result

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path)
    a=p.parse_args();r=source_ledger(a.root)
    if a.verify and r!=json.loads(a.verify.read_text()):raise ValueError('all-port phase replay differs')
    if a.out:a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(r['restore_table_accounting'],sort_keys=True))
