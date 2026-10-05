"""R67 source lifetimes and physical backing model; no constructors/launches."""
import argparse,ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_r67_physical_phase_review_20261003'

def require(v,msg):
    if not v:raise ValueError(msg)

def page_evolution(baseline,phases,granule=4096):
    """Complete finite guest-to-host granule identity witness, not aggregate RSS.
    phases: reads/writes. Private backing persists even when process exits.
    Absent read allocates private backing; shared write allocates one private
    replacement; repeated same identity does not COW again. Alias and generation
    normalization must precede this function. Old pinned backing is independent
    identity and included in baseline/new allocation inventory.
    """
    require(type(granule)is int and granule>0,'positive granule')
    require(all(v in ('private','shared','absent') for v in baseline.values()),'backing kinds')
    state=dict(baseline);growth=0;rows=[]
    for phase in phases:
        reads=set(phase['reads']);writes=set(phase['writes']);touch=reads|writes
        require(touch<=state.keys(),'complete enrolled backing identities')
        new={g for g in touch if state[g]=='absent' or (g in writes and state[g]=='shared')}
        for g in new:state[g]='private'
        growth+=len(new)*granule
        rows.append(dict(new_backing_bytes=len(new)*granule,cumulative_backing_bytes=growth))
    return rows

def exposure(*,roof,resident,shared_clean,shared_dirty):
    for v in (roof,resident,shared_clean,shared_dirty):require(type(v)is int and v>=0,'nonnegative bytes')
    require(resident<=roof and shared_clean+shared_dirty<=resident,'RAM-only mapping accounting')
    return roof-resident+shared_clean+shared_dirty

def bounded_delta(*,cumulative_complete_touch_bytes,ram_exposure_bytes,kernel_growth,peer_growth):
    for v in (cumulative_complete_touch_bytes,ram_exposure_bytes,kernel_growth,peer_growth):
        require(type(v)is int and v>=0,'complete source/page/growth upper bounds required')
    return min(cumulative_complete_touch_bytes,ram_exposure_bytes)+kernel_growth+peer_growth

def load_inputs():
    d=OUT/'inputs';pins=json.loads((d/'input_sha256.json').read_text())
    for name,h in pins.items():require(hashlib.sha256((d/name).read_bytes()).hexdigest()==h,'source pin '+name)
    return d

def verify_calls(d):
    tree=ast.parse((d/'ds_hbm_remote_controller_r67.py').read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    smoke=next(n for n in ast.walk(main) if isinstance(n,ast.If) and ast.unparse(n.test)=='args.smoke')
    calls=[ast.unparse(n.value) for n in smoke.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='child']
    require(calls==['child(args.plan, plan, 0)','child(args.plan, plan, 1)','child(args.plan, plan, 1, verify_only=True)'],'exact three-child source order')
    child=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='child')
    require(any(isinstance(n,ast.Call) and ast.unparse(n.func)=='process.wait' for n in ast.walk(child)),'source child terminal join')
    return calls

def model():
    d=load_inputs();calls=verify_calls(d)
    old=json.loads((d/'PC01_model.json').read_text());phy=json.loads((d/'physical_backing.json').read_text())
    host=phy['paired_capture']['host'];ram=host['largest_mapping_extents'][0]
    cap=exposure(roof=ram['Size_bytes'],resident=ram['Rss_bytes'],shared_clean=ram['Shared_Clean_bytes'],shared_dirty=ram['Shared_Dirty_bytes'])
    r=old['RAM'];ctor=r['actual_dual_constructor_only_source_component_bytes'];cold=r['source_scoped_existing_workspace_RAM_bytes']
    raw=old['disk'];check=raw['fresh_producer_and_cold_journals'] if 'fresh_producer_and_cold_journals' in raw else None
    return dict(schema='DS_R67_PC01_PHASE_PHYSICAL_BACKING_REVIEW_V1',status='SOURCE_LIFETIME_COMPLETE_PAGE_BOUND_MISSING_NO_ADMISSION',
      R67_commit='e606f6ef34dd67e72f97904f75b9714b8889329b',old_R64_guards_unchanged=True,launches=0,
      source_child_order=calls,source_child_processes_simultaneously_live=1,
      full_native_PCs=2213,full_homes=290730,actual_PC0_PC1_only_component_smoke=True,full_token_scope_reduced=False,
      checkpoints_retained=2,journals_created=3,third_process_executes_arithmetic=False,
      phase_contracts=[
        dict(phase='PC0',operations=[0],constructor_full_scope=True,restore=False,capture_PC=0),
        dict(phase='PC1',operations=[1],constructor_full_scope=True,restore_PC=0,capture_PC=1),
        dict(phase='verify1',operations=[],constructor_full_scope=True,restore_PC=1,exact_actual_byte_verification=True)],
      source_component_prices=dict(dual_constructor_bytes=ctor,PC01_existing_workspace_bytes=cold,
        streamed_workspace_proposal_bytes=r['proposed_streamed_source_scoped_RAM_bytes'],
        individual_prices_are_not_allocator_page_upper_bounds=True,
        cumulative_constructor_component_sum_three_children=3*ctor,
        retained_conservative_source_component_sum_PC0_PC1_verify1=3*cold,
        sequential_lifetime_discount_applied=False),
      baseline_physical=dict(source='3c58e9b271c6c54b7485c8ab639c4658d5ed62cb',
        measured_utc=host['time_utc'],host_available_bytes=host['MemAvailable_bytes'],
        RAM_roof_bytes=ram['Size_bytes'],RAM_resident_bytes=ram['Rss_bytes'],
        RAM_shared_dirty_bytes=ram['Shared_Dirty_bytes'],RAM_shared_clean_bytes=ram['Shared_Clean_bytes'],
        RAM_private_dirty_bytes=ram['Private_Dirty_bytes'],RAM_AnonHugePages_bytes=ram['AnonHugePages_bytes'],
        RAM_unbacked_bytes=ram['Size_bytes']-ram['Rss_bytes'],RAM_only_new_backing_exposure_upper_bytes=cap,
        exposure_is_alternative_not_additional=True,
        exposure_minus_host_available_bytes=cap-host['MemAvailable_bytes'],
        dual_constructor_nominal_margin_before_page_cache_kernel_peer_bytes=host['MemAvailable_bytes']-ctor,
        existing_workspace_nominal_margin_before_page_cache_kernel_peer_bytes=host['MemAvailable_bytes']-cold,
        guest_and_host_capacity_never_added=True,cache_eviction_credit_bytes=0,
        guest_exit_proves_host_backing_release=False,baseline_to_source_private_reuse_proof=False,
        bound_inputs_are_historical_not_launch_lease=True),
      physical_derivation=['One guest backing granule is absent OR shared OR private at the enrolled baseline, never both absent and shared.',
        'Absent read/write allocates at most one backing granule; shared write COW allocates at most one; both turn that identity private.',
        'Subsequent touches of the same private identity add no backing; later phases touching different baseline-shared identities can grow backing even after earlier process exit.',
        'Thus main-RAM incremental peak <= min(complete cumulative unique touched-granule upper, baseline RAMSharedClean+RAMSharedDirty+RAMSize-RAMRSS). Never add the two.',
        'Host growth outside the RAM mapping and protected peer unsharing/reservations are separate. No pages/PSS/cache release credited.'],
      page_bound_blockers=['Exact CPython/glibc allocation lifetime/arena-retention and granule rounding must bind source object components.',
        'Host COW/THP allocation granule policy must be enrolled: sparse 4KiB guest touch is not automatically 4KiB host allocation.',
        'All three journals, two checkpoint payloads, source file reads and state JSON verification create guest file-cache/kernel touches across phases.',
        'R67 verifier restore_cold -> verify_actual_restore takes another closure/snapshot and payload memmap; two1MiB compare chunks do not bound the whole source graph.',
        'Kepler source-priced PC01 successor plan is required; old R67 admission still demands original R64 constructor receipt and full resource guard.',
        'Fresh physical host/QEMU snapshot and explicit protected-peer growth lease are absent; .226 physical-host independence not assumed.'],
      source_persistence=['Retain checkpoint-PC0 and checkpoint-PC1 plus PC0,PC1,verify1 journals. No journal/payload pruning.',
        'R67 wait provides process nonoverlap, not guest allocator same-PFN reuse or QEMU host backing release.',
        'Input same-content hashes do not prove same backing pages; no readonly alias discount taken.',
        'Full future source program/homes/last_use and ownership versions persist in each cold constructor. Expected outputs used only as oracle.'],
      resource_admission=False,Kepler_owns_PC01_source_successor=True,Chandra_owns_fresh_physical_fleet_lease=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);ap.add_argument('--verify',type=Path);a=ap.parse_args();v=model()
    if a.output:a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
    if a.verify:require(json.loads(a.verify.read_text())==v,'exact replay');print('PASS_SOURCE_R67_PHASE_REPLAY_NO_ADMISSION')
