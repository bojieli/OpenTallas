"""R69 phase composition: explicit positive source bounds, never guessed credit."""
import hashlib
import json
from pathlib import Path

MODEL_SHA = 'ae5e031ebbf51413095a5ae6aeee02958ea653ecedcd26ffe38860f12dafcfda'
FIELDS = ('project_snapshot_encoded_tree_upper_bytes',
          'project_canonical_and_measure_walk_upper_bytes',
          'save_snapshot_stream_frames_upper_bytes',
          'save_leaf_and_array_temporary_upper_bytes',
          'identity_contract_and_journal_metadata_upper_bytes',
          'atomic_json_parse_upper_bytes', 'cold_json_parse_upper_bytes',
          'restore_verifier_json_and_compare_upper_bytes',
          'retained_allocator_and_cumulative_COW_upper_bytes',
          'new_runner_source_and_diagnostics_upper_bytes')

def source_ledger(root):
    root = Path(root)
    original = root / 'results/uarch/ds_hbm_pc01_r68_20261003/model.json'
    if hashlib.sha256(original.read_bytes()).hexdigest() != MODEL_SHA:
        raise ValueError('exact frozen915 model required')
    m = json.loads(original.read_bytes())
    allowance = m['inherited_workspace_bytes']
    audit = json.loads((root / 'results/uarch/ds_checkpoint_streamed_state_20261003/allocation_phase_audit.json').read_text())
    if sum(audit['allowance_formula'].values()) != allowance:
        raise ValueError('serialization allowance decomposition mismatch')
    base = m['required_smoke_RAM_bytes'] - allowance
    if base != audit['candidate_base_excluding_inherited_allowance_bytes']:
        raise ValueError('source retained-base mismatch')
    return dict(schema='R69_CHECKPOINT_PHASE_LEDGER', full_native_PCs=2213,
        full_homes=290730, full_future_lifetimes_retained=True,
        original_R68_guard_RAM_bytes=m['required_smoke_RAM_bytes'],
        original_R68_constructor_RAM_bytes=m['required_constructor_RAM_bytes'],
        original_R68_disk_envelope_bytes=m['required_disk_bytes'],
        inherited_allowance_bytes=allowance, allowance_decomposition=audit['allowance_formula'],
        retained_candidate_base_bytes=base, retained_base_is_complete_peak=False,
        retained_base_components={k:v for k,v in m['inherited_RAM_components'].items() if k != 'serialization_workspace_bytes'},
        no_payload_mmap_or_restore_object_credit=True,
        save_selection='parent647d3cec5 ds_checkpoint_streamed_state_r2.py only',
        phase_allocations={
            'project_checkpoint':'Original V3 measure_state remains: encoded container tree + canonical string/bytes + deep_metadata traversal seen set + array temporary. No streaming projection credit.',
            'save':'Snapshot wrappers alias producer objects; R2 bounded frames and original leaf writer including sector tables and noncontiguous array temporary. Two passes/hash checks; no full encoded container tree or whole closure canonical buffer.',
            'atomic_publish':'Original R67 verify_payload reads full state JSON and actual observations; decoded objects/input bytes/text coexist before sibling rename. Rename adds no second payload copy.',
            'cold_restore':'Original full constructor, V3 verify+read_tree, closure JSON parsing; original restored arrays/sectors and CompactSectors table copy remain charged in retained base.',
            'restore_exactness':'Original verify_actual_restore parses JSON and creates saved tree/readonly mmap while comparing actual state; positive parser/compare increment required.',
            'physical_backing':'Object lifetime maxima do not prove page reuse/release; retained allocator, cumulative COW/filecache/kernel and peer leases must be independently bounded.'},
        required_positive_phase_fields=list(FIELDS), phase_bounds=None,
        required_runtime_RAM_bytes=None, physical_admission=False,
        constructor_or_numeric_jobs=0,
        note='No original guard, source/helper identity, or runtime plan is lowered by this ledger.')

def compose(ledger, proof):
    if proof.get('complete_source_phase_bounds') is not True:
        raise ValueError('reviewed complete source phase bounds required')
    if any(type(proof.get(k)) is not int or proof[k] <= 0 for k in FIELDS):
        raise ValueError('all phase increments must be explicit positive source bounds')
    common = proof['identity_contract_and_journal_metadata_upper_bytes']
    peaks = dict(
        project=proof['project_snapshot_encoded_tree_upper_bytes'] + proof['project_canonical_and_measure_walk_upper_bytes'] + common,
        save=proof['save_snapshot_stream_frames_upper_bytes'] + proof['save_leaf_and_array_temporary_upper_bytes'] + common,
        atomic=proof['atomic_json_parse_upper_bytes'] + common,
        cold=proof['cold_json_parse_upper_bytes'] + common,
        restored_verify=proof['restore_verifier_json_and_compare_upper_bytes'] + common)
    extra = proof['retained_allocator_and_cumulative_COW_upper_bytes'] + proof['new_runner_source_and_diagnostics_upper_bytes']
    return dict(phase_increment_peaks=peaks,
        required_runtime_RAM_bytes=ledger['retained_candidate_base_bytes'] + max(peaks.values()) + extra,
        constructor_RAM_floor_bytes=ledger['original_R68_constructor_RAM_bytes'],
        physical_admission=False, host_page_and_peer_reserve_still_required=True,
        composed_as_maximum_of_live_phases_not_serial_sum=True)

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path)
    a=p.parse_args();result=source_ledger(a.root)
    if a.verify and result != json.loads(a.verify.read_text()):raise ValueError('phase ledger replay differs')
    if a.out:a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'retained_candidate_base_bytes':result['retained_candidate_base_bytes'],'physical_admission':False}))
