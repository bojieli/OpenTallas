"""Additive PC0-1 component price. No provider constructors or numeric execution.
The source component bound is separate from physical page/allocator admission.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_hbm_pc01_r68_20261003'
DEPLOY_ROOT=Path('/tmp/kepler-ds-pc01-r68-mainbase-20261003')
NEW=('tools/ds_hbm_pc01_price_r68.py','tools/ds_hbm_pc01_controller_r68.py','tools/ds_hbm_pc01_child_r68.py')

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def model():
    import ds_pc01_checkpoint_fastpath_review as peer
    import ds_hbm_remote_price_r67 as old
    import ds_hbm_dual_resources_r56 as base
    snapshot=ROOT/'results/uarch/ds_pc01_checkpoint_fastpath_review_20261003/model.json'
    review=peer.model()
    if snapshot.read_bytes()!=peer.canonical(review)+b'\n':raise ValueError('exact Peirce component replay required')
    n,h,m=base.journal.source_inputs()
    if len(n['instructions'])!=2213 or len(h)!=290730:raise ValueError('complete future program/home identity required')
    pins,compiled=old.all_helpers()
    baseline=ROOT/'results/uarch/ds_hbm_checkpoint_readiness_r64_20261003/preflight_plan.json'
    required=json.loads(baseline.read_bytes())['source_sha256']
    for path,wanted in required.items():
        if sha(ROOT/path)!=wanted:raise ValueError('unchanged required runtime/metadata pin: '+path)
        pins[path]=wanted
    for path in NEW:
        raw=(ROOT/path).read_bytes();compile(raw,path,'exec');pins[path]=hashlib.sha256(raw).hexdigest()
        if path not in compiled:compiled.append(path)
    pins[str(snapshot.relative_to(ROOT))]=sha(snapshot)
    source_bytes=sum((ROOT/p).stat().st_size for p in NEW)+sum((ROOT/p).stat().st_size for p in ('tools/ds_hbm_atomic_checkpoint_r67.py','tools/ds_hbm_per_pc_r67.py'))
    graph_bytes=sum(len(canonical(v)) for v in (n,h,m))
    pin_bytes=len(canonical(pins))
    # Retain old lineage/diagnostics and both graph RAM even though children do
    # not coexist. Pay five newly generated graph artifacts (2 preflight+3run).
    metadata_disk=5*(2*graph_bytes+20*pin_bytes)
    diagnostics_disk=5*2*6*(source_bytes+graph_bytes+pin_bytes)
    extra_RAM=20*pin_bytes+10*(source_bytes+graph_bytes)+2*1048576
    # Two actual snapshots. At any boundary there is at most previous+staging;
    # there is no deletion/rotation credit, and both final snapshots persist.
    checkpoint_upper=review['disk']['new_checkpoint_upper']+6*pin_bytes
    journals=review['journal_phase_bytes']
    # Fresh verifier/preflight dictionaries and sparse streams, no numeric
    # events in these three constructors. Charge full per-rank guards anyway.
    boot=sum(v for k,v in review['journal_components'][0].items() if k not in ('PC','sector_events','control_records'))
    extra_boot=3*boot
    disk=sum(journals)+extra_boot+2*checkpoint_upper+review['disk']['retained_R64_other_artifacts_and_diagnostics']+metadata_disk+diagnostics_disk
    smoke_RAM=review['RAM']['source_scoped_existing_workspace_RAM_bytes']+extra_RAM+2*(checkpoint_upper-review['disk']['new_checkpoint_upper'])
    preflight_RAM=review['RAM']['actual_dual_constructor_only_source_component_bytes']+extra_RAM
    def projection(ram,stage):return dict(projection_complete=True,required_RAM_bytes=ram,required_disk_bytes=disk,
        stage=stage,source_component_only=True,physical_page_admission=False,physical_parent_aggregate_required=True,
        allocator_page_filecache_kernel_and_peer_growth_proof_required=True,hardware_qualified=False)
    paths={}
    for r in list(m['initial_versions'])+list(m.get('view_bindings',{}).values()):
        if not isinstance(r,dict) or 'path' not in r:continue
        p=Path(r['path']);local=p if p.is_absolute() else ROOT/p
        deployed=p if p.is_absolute() else DEPLOY_ROOT/p
        paths[str(deployed)]=dict(bytes=local.stat().st_size,sha256=r['sha256'])
    return dict(immutable_input_index=dict(paths=paths,checkpoint_path=m['checkpoint_path'],no_oracle_substitution=True),schema='DS_FULL_SOURCE_PC01_COMPONENT_R68',full_native_PCs=2213,full_homes=290730,
        source_sha256=pins,compiled_python_helpers=sorted(compiled),static_all_helpers_complete=True,
        Peirce_commit='1f7f14f5185170b25dac060baa213c54c88fff89',Peirce_model_sha256=sha(snapshot),
        runtime_projection=projection(smoke_RAM,'actual_PC0_1_capture_restore'),constructor_projection=projection(preflight_RAM,'dual_constructor_only'),
        required_disk_bytes=disk,required_smoke_RAM_bytes=smoke_RAM,required_constructor_RAM_bytes=preflight_RAM,
        inherited_workspace_bytes=review['RAM']['serialization_phase_R64_overcharge_bytes'],
        inherited_RAM_components=review['RAM']['source_scoped_components'],extra_RAM_bytes=extra_RAM,
        per_checkpoint_capacity_bytes=checkpoint_upper,retained_checkpoint_count=2,atomic_payload_rename_copy_bytes=0,
        checkpoint_bytes=2*checkpoint_upper,PC0_journal_capacity_bytes=journals[0],PC1_journal_capacity_bytes=journals[1],
        other_process_journal_capacity_bytes=boot,extra_journal_bootstrap_bytes=extra_boot,
        preserved_other_disk_bytes=review['disk']['retained_R64_other_artifacts_and_diagnostics'],
        generated_graph_and_metadata_bytes=metadata_disk,diagnostics_disk_bytes=diagnostics_disk,
        full_future_lifetimes_retained=True,old_R64_and_R67_unchanged=True,unproved_streamed_workspace_used=False,
        source_existing_required=True,absent_transfer_not_admitted=True,guest_plus_host_sum=False,COW_extra_double_charge=False,
        physical_write_set_COW_proof=None,numerical_runs=0)

def generate():
    v=model();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'model.json').write_bytes(canonical(v)+b'\n')
    old=ROOT/'results/uarch/ds_hbm_remote_controller_r67_20261003/ot-pve1_plan.template.json'
    interpreter=json.loads(old.read_bytes())['interpreter']
    output='/home/ubuntu/ds-hbm-pc01-r68-run-20261003'
    index=OUT/'immutable_input_index.json'
    index.write_bytes(canonical(v['immutable_input_index'])+b'\n')
    common=dict(schema='DS_FULL_SOURCE_PC01_PLAN_R68',source_root=str(DEPLOY_ROOT),component_model=str(DEPLOY_ROOT/'results/uarch/ds_hbm_pc01_r68_20261003/model.json'),component_model_sha256=sha(OUT/'model.json'),
        source_sha256=v['source_sha256'],static_all_helpers_complete=True,interpreter=interpreter,
        output_root=output,resolved_output_root=output,full_native_PCs=2213,full_homes=290730,terminal_PC=1,
        immutable_input_index=str(DEPLOY_ROOT/'results/uarch/ds_hbm_pc01_r68_20261003/immutable_input_index.json'),
        immutable_input_index_sha256=sha(index),
        constructor_parent_proof='/home/ubuntu/ds-hbm-pc01-r68-enrollment/constructor_parent.json',
        runtime_parent_proof='/home/ubuntu/ds-hbm-pc01-r68-enrollment/runtime_parent.json',enrolled=False,actual_smoke=False,numerical_GO=False)
    for alias in ('ot-pve1','ot-agidock128'):(OUT/(alias+'_plan.template.json')).write_bytes(canonical(dict(common,host_alias=alias))+b'\n')
    print(json.dumps({k:v[k] for k in ('required_disk_bytes','required_smoke_RAM_bytes','required_constructor_RAM_bytes','checkpoint_bytes')},indent=2))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--verify',type=Path);args=ap.parse_args()
    if args.verify:
        if args.verify.read_bytes()!=canonical(model())+b'\n':raise ValueError('cold source component replay differs')
        print('PASS_EXACT_PC01_COMPONENT_REPLAY_NO_CONSTRUCTORS')
    else:generate()
