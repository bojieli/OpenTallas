"""Source-enforced R68 physical admission floor. No provider or numeric launch."""
import argparse,ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_r68_physical_admission_20261003'

def checked_inputs():
    d=OUT/'inputs';receipt=json.loads((d/'snapshot_receipt.json').read_bytes())
    for name,wanted in receipt['snapshot_file_SHA256'].items():
        if hashlib.sha256((d/name).read_bytes()).hexdigest()!=wanted:raise ValueError('source snapshot pin '+name)
    return d,receipt

def page_proof_ast():
    d,_=checked_inputs();tree=ast.parse((d/'ds_hbm_pc01_controller_r68.py').read_text())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='page_proof')
    predicates=[ast.unparse(n.test) for n in ast.walk(f) if isinstance(n,ast.If)]
    for expected in ["proof['allocator_page_upper_bytes'] < price['required_RAM_bytes']", "proof['physical_new_page_union_upper_bytes'] < touched"]:
        if expected not in predicates:raise ValueError('R68 source admission predicate changed')
    return f

def certificate_floor(*,component_bytes,host_available_bytes,reserved_bytes,filecache_upper=None,kernel_upper=None):
    for n in (component_bytes,host_available_bytes,reserved_bytes):
        if type(n)is not int or n<0:raise ValueError('nonnegative bytes')
    # This is only a necessary floor; unknown source costs cannot certify PASS.
    remaining=host_available_bytes-reserved_bytes
    if remaining<component_bytes:
        return dict(status='PROVED_CAPACITY_REFUSAL_AT_ENROLLED_SNAPSHOT',component_floor_bytes=component_bytes,
                    additional_cost_allowance_bytes=remaining-component_bytes,admission=False)
    for n in (filecache_upper,kernel_upper):
        if n is not None and (type(n)is not int or n<0):raise ValueError('source costs')
    return dict(status='SOURCE_PAGE_CLOSURE_AND_FRESH_PHYSICAL_LEASE_REQUIRED',component_floor_bytes=component_bytes,
                additional_cost_allowance_bytes=remaining-component_bytes,admission=False)

def model():
    d,r=checked_inputs();f=page_proof_ast()
    v=json.loads((d/'model.json').read_bytes());p=json.loads((d/'physical_backing.json').read_bytes())
    host=p['paired_capture']['host'];A=host['MemAvailable_bytes'];ram=host['largest_mapping_extents'][0]
    cap=ram['Size_bytes']-ram['Rss_bytes']+ram['Shared_Clean_bytes']+ram['Shared_Dirty_bytes']
    return dict(schema='DS_R68_ACTUAL_SOURCE_PHYSICAL_ADMISSION_REVIEW_V1',status='NO_POSITIVE_PAGE_CERTIFICATE',
      source_snapshot_sha256=r['source_path_SHA256'],mutable_worktree_snapshotted_without_changes=True,
      R68_component_model_SHA256=hashlib.sha256((d/'model.json').read_bytes()).hexdigest(),
      source_page_proof_function_sha256=hashlib.sha256(ast.unparse(f).encode()).hexdigest(),
      full_native_PCs=v['full_native_PCs'],full_homes=v['full_homes'],old_R64_R67_guards_unchanged=v['old_R64_and_R67_unchanged'],
      actual_flow=['dual full constructors in one preflight process','PC0 execute/seal/exit','fresh PC1 restore/execute/seal/exit','third process cold restore and actual-state compare'],
      checkpoints=2,runtime_journals=3,additional_constructor_journals=2,
      source_component_RAM=dict(constructor=v['required_constructor_RAM_bytes'],runtime=v['required_smoke_RAM_bytes']),
      source_disk=dict(total=v['required_disk_bytes'],two_checkpoint_payloads=v['checkpoint_bytes'],
        PC0journal=v['PC0_journal_capacity_bytes'],PC1journal=v['PC1_journal_capacity_bytes'],
        verifier_and_constructor_bootstraps=v['extra_journal_bootstrap_bytes'],
        graph_metadata=v['generated_graph_and_metadata_bytes'],diagnostics=v['diagnostics_disk_bytes']),
      physical_snapshot=dict(source='3c58e9b271c6c54b7485c8ab639c4658d5ed62cb',time_utc=host['time_utc'],
        available_bytes=A,RAM_only_shared_and_absent_ceiling=cap,historical_not_launch_lease=True),
      stage_results={s:certificate_floor(component_bytes=v[s+'_projection']['required_RAM_bytes'],host_available_bytes=A,reserved_bytes=0) for s in ('constructor','runtime')},
      source_guard_derivation=['R68 requires allocator_page_upper >= stage required_RAM_bytes.',
        'R68 requires physical_new_page_union_upper >= allocator_page_upper + additional filecache upper + kernel upper.',
        'R68 requires physical MemAvailable - protected reserve >= physical_new_page_union_upper.',
        'Therefore physical capacity must be at least the component RAM even with all additional costs zero. Runtime floor exceeds this historical capacity: no certificate can satisfy these unchanged source inequalities.',
        'R68 enroll calls page_proof for both constructor and runtime; constructor-only headroom does not enroll runtime.'],
      COW_overlap=dict(baseline_to_actual_allocations_proved=False,guest_and_host_sum=False,
        whole_shared_exposure_added=False,source_component_is_page_bound=False,
        chain_bound='min(complete cumulative distinct touched host-granule upper, initial shared+absent RAM ceiling) + host nonRAM and protected peer growth',
        process_exit_is_host_release=False,process_max_RSS_is_chain_upper=False,
        readonly_and_checkpoint_pagecache_credit=0),
      missing_certificate_fields=dict(allocator_rounding_retention_upper=None,host_COW_THP_granule_policy=None,
        source_checkpoint_journal_filecache_union_upper=None,page_tables_kernel_growth_upper=None,
        actual_guest_to_physical_parent_membership=None,fresh_peer_growth_reservation=None),
      next_dependency='Kepler frozen source successor + Chandra fresh physical capacity/membership/peer lease. At this snapshot runtime needs at least11314636048 more physical bytes BEFORE any extra costs, or separately reviewed source-preserving reduction. No invented page certificate.',
      actual_numeric_or_constructor_launches=0,resource_admission=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);ap.add_argument('--verify',type=Path);a=ap.parse_args();v=model()
    if a.output:a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
    if a.verify:
        if json.loads(a.verify.read_text())!=v:raise ValueError('source replay mismatch')
        print('PASS_R68_SOURCE_FLOOR_REFUSAL_REPLAY_NO_ADMISSION')
