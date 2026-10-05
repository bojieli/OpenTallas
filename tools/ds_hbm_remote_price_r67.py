"""Freeze whole helper inventory and per-PC remote source resource price.
Source-only metadata analysis. No native/provider constructors or arithmetic.
"""
import ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_hbm_remote_controller_r67_20261003'
NEW=('tools/ds_hbm_atomic_checkpoint_r67.py','tools/ds_hbm_per_pc_r67.py',
     'tools/ds_hbm_remote_controller_r67.py','tools/ds_hbm_remote_price_r67.py')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def all_helpers():
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    names=sorted(set(NEW)|{p for p in tracked if (p.startswith('tools/') and p.endswith('.py')) or
        (p.startswith('results/uarch/') and p.endswith(('.py','.py.source')))})
    pins={};compiled=[]
    for p in names:
        file=ROOT/p
        raw=file.read_bytes() if file.exists() else subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
        compile(raw,p,'exec');ast.parse(raw,filename=p)
        pins[p]=hashlib.sha256(raw).hexdigest();compiled.append(p)
    return pins,compiled


def price():
    sys.path.insert(0,str(ROOT/'tools'))
    import ds_hbm_dual_resources_r56 as base
    import ds_producer_checkpoint_resume_v3 as helper
    n,h,m=base.journal.source_inputs()
    baseline=ROOT/'results/uarch/ds_hbm_checkpoint_readiness_r64_20261003/preflight_model.json'
    v=json.loads(baseline.read_bytes())
    # Analytical clone: exactly one cutoff changes9->10; no runtime method is
    # replaced. Same source address/replica/extent formula, recorded AST below.
    import inspect
    tree=ast.parse(inspect.getsource(base.source_sector_homes));changes=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Name) and node.left.id=='born' and ast.unparse(node)=='born > 9':
            node.comparators[0].value=10;changes+=1
    if changes!=1:raise ValueError('one source-owned analytical cutoff required')
    namespace=dict(vars(base));exec(compile(ast.fix_missing_locations(tree),'<R67 analytical cutoff only>','exec'),namespace)
    sectors=namespace['source_sector_homes'](n,h,m)
    # The inherited function's result label is literal9; only this report label
    # becomes10. Source addresses and counts come from the changed cutoff.
    sectors['boundary_pc']=10
    shared_sectors=96*32*(65536//32)
    sector_delta=sectors['resident_sector_upper']-v['source_sector_homes']['resident_sector_upper']
    if sector_delta<0:raise ValueError('no inherited occupancy credit')
    pins,compiled=all_helpers()
    original=json.loads((baseline.parent/'preflight_plan.json').read_bytes())['source_sha256']
    pins.update(original)
    source_bytes=sum(len((ROOT/p).read_bytes()) if (ROOT/p).exists() else len(subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)) for p in pins)
    graph_bytes=sum(len(canonical(x)) for x in (n,h,m))
    source_metadata=len(canonical(pins))
    snapshot=v['checkpoint_new_bytes']+(sector_delta+shared_sectors)*helper.SECTOR_RECORD.size+6*source_metadata
    checkpoints=11*snapshot
    processes=13 # PC0..10 children plus independent PC1 and PC10 verifier.
    bootstrap=processes*((v['checkpoint']['port_upper']+4)*2*8192+131072)
    # All event paths bounded by exact longer final/staging path, includingUUID.
    output='/home/ubuntu/ds-hbm-r67-run-20261003'
    old_output=v['output_root'];extra=max(0,len(output+'/checkpoint-PC10.pending-'+'f'*32)-len(old_output))
    requests=sum(o['software_sector_request_conservative_bound'] for o in base.prefix.model(n,h,10)['ops'])
    path_bytes=8*8*extra*(requests+49152+96*512+928*96)
    copy_metadata=processes*(2*graph_bytes+20*source_metadata)
    # Durable child/controller diagnostics pay source+graph full-text JSON6x;
    # serialization has4-byteunicode + encoded copies in memory. No trace cap.
    diagnostics=processes*2*6*(source_bytes+graph_bytes+source_metadata)
    disk=v['journal_new_bytes']+bootstrap+path_bytes+checkpoints+v['other_new_bytes']+copy_metadata+diagnostics
    sector_unit=v['RAM']['interpreter']['sector_entry_bytes']
    ram_extra=2*sector_delta*sector_unit+shared_sectors*sector_unit+2*(snapshot-v['checkpoint_new_bytes'])+20*source_metadata+10*(source_bytes+graph_bytes)+2*1048576
    ram=v['RAM']['coexistence_RAM_peak_bytes']+ram_extra
    # Preserve the entire dual-constructor/retained producer price even though
    # these children do not overlap. Any source-proven reduction is Peirce's
    # separately reviewed successor; this plan takes zero such credit.
    projection=dict(projection_complete=True,required_disk_bytes=disk,required_RAM_bytes=ram,
        inherited_R64_disk_bytes=sum(v[k] for k in ('journal_new_bytes','checkpoint_new_bytes','other_new_bytes')),
        inherited_R64_RAM_bytes=v['RAM']['coexistence_RAM_peak_bytes'],no_inherited_guard_lowering=True,
        source_snapshot_upper_bytes=snapshot,retained_checkpoint_count=11,process_count=processes,
        exact_PC10_RF_state_sectors=sectors['resident_sector_upper'],additional_PC10_RF_state_sectors=sector_delta,
        PC10_shared_sectors=shared_sectors,all_snapshot_bytes=checkpoints,
        additional_journal_bootstrap_bytes=bootstrap,additional_path_bytes=path_bytes,
        additional_constructor_and_metadata_copies_bytes=copy_metadata,full_diagnostics_disk_bytes=diagnostics,
        additional_RAM_bytes=ram_extra,source_sector_entry_bytes=sector_unit,
        extra_concurrent_array_compare_bytes=2*1048576,atomic_rename_payload_copy_bytes=0,
        old_checkpoint_component_replaced_bytes=v['checkpoint_new_bytes'],
        whole_source_inputs_already_present_required=True,remote_transfer_inventory_cost_pending_if_not_present=True,
        physical_parent_aggregate_required=True,hardware_qualified=False,
        analytical_cutoff_change_only=True,source_model_sha256=sha(ROOT/'tools/ds_hbm_dual_resources_r56.py'))
    common=dict(schema='DS_REMOTE_ACTUAL_PER_PC_CONTROLLER_R67',source_sha256=pins,
        static_all_helpers_complete=True,output_root=output,resolved_output_root=output,
        interpreter=v['RAM']['interpreter'],capture_workspace_RAM_bytes=v['serialization_workspace_RAM_bytes']+ram_extra,
        resource_projection=projection,per_process_journal_capacity_bytes=v['journal_new_bytes']+bootstrap+path_bytes,
        per_checkpoint_capacity_bytes=snapshot,
        actual_dual_constructor_receipt='/home/ubuntu/ds-hbm-r67-enrollment/R64/receipt.json',
        actual_dual_constructor_plan='/home/ubuntu/ds-hbm-r67-enrollment/R64/preflight_plan.json',
        actual_dual_constructor_sha256=None,physical_parent_admission='/home/ubuntu/ds-hbm-r67-enrollment/physical_parent_admission.json',
        enrolled=False,actual_smoke_executed=False,actual_constructor_executed=False,numerical_GO=False,
        enrollment_required=['exact all-helper inventory deployed plus unchanged R64 source/data archive',
          'original absolute immutable input paths mirrored from source input index, or separately reviewed explicit lineage migration',
          'exact priced CPython version/numpy source-byte and dtype representations',
          'actual positive R64 constructor receipt/plan/hash','reviewed fresh physical-parent aggregate and guest/filesystem admission'])
    OUT.mkdir(parents=True,exist_ok=True)
    for alias in ('ot-pve1','ot-agidock128'):
        (OUT/(alias+'_plan.template.json')).write_text(json.dumps(dict(common,host_alias=alias),sort_keys=True,indent=2)+'\n')
    (OUT/'resource_projection.json').write_text(json.dumps(projection,sort_keys=True,indent=2)+'\n')
    (OUT/'static_helpers.json').write_text(json.dumps(dict(source_sha256=pins,compiled_python_helpers=compiled,
        status='PASS_ALL_TRACKED_TOOLS_AND_RETAINED_PYTHON_SOURCE_SNAPSHOTS_COMPILE',runtime_imports_executed=False,
        native_arithmetic_executed=False),sort_keys=True,indent=2)+'\n')
    paths={}
    for r in m['initial_versions']:
        p=Path(r['path']);paths[str(p)]=dict(bytes=p.stat().st_size,sha256=r.get('sha256'))
    for r in m.get('view_bindings',{}).values():
        if isinstance(r,dict) and 'path' in r:
            p=Path(r['path']);p=p if p.is_absolute() else ROOT/p
            paths[str(p)]=dict(bytes=p.stat().st_size,sha256=r.get('sha256'))
    (OUT/'immutable_input_index.json').write_text(json.dumps(dict(paths=paths,checkpoint_path=m['checkpoint_path'],
        note='existing actual source inputs; mirror exactpaths; no oracle substitution; verify all hashes before constructors'),sort_keys=True,indent=2)+'\n')
    print(json.dumps(projection,indent=2))

if __name__=='__main__':price()
