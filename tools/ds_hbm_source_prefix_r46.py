"""Prepared opt-in actual PC0..10 runner; numerical execution requires parent GO.
Fresh execution retains actual PC9 backing/leases in the same provider instance.
No resume from digest journals, golden stimuli, affinity or arbitrary caps.
"""
import argparse,copy,gzip,hashlib,json,os,resource,time
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,D
from ds_hbm_source_prefix_r45 import driver_class
from ds_hbm_storage_home_binding_r41 import bind_storage,create_bound_provider as create_prefix_provider
from ds_hbm_prefix_observed_outputs_r42 import Observed
from ds_hbm_pc10_engine_r44 import Witness
from ds_hbm_pc10_composed_engine_r46 import engine_class
from ds_hbm_unconsumed_retirement_r45 import retirement_plan
from ds_hbm_pc10_projection_r46 import project
from ds_hbm_connected_prepare_r37 import load,sha
def main():
    a=argparse.ArgumentParser();a.add_argument('--stop',type=int,choices=(10,),required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--preflight-only',action='store_true');a.add_argument('--retire-unconsumed',action='store_true');a.add_argument('--finite-pc10',action='store_true');args=a.parse_args()
    if not args.finite_pc10 or not args.retire_unconsumed:raise ValueError('explicit default-off PC10 and proven retirement opt-ins required')
    if args.out.exists():raise ValueError('fresh invocation; no retry/fallback')
    args.out.mkdir();record=dict(status='INITIALIZING',pid=os.getpid(),start_ns=time.time_ns(),prefix_stop=args.stop,full_token_GO=False,hardware_qualified=False);provider=None
    def save():(args.out/'receipt.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    save()
    try:
        nativepath=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz';dispatchpath=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz';native=load(nativepath);dispatch=load(dispatchpath);homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes'];manifest=load(D/'inputs/prefix_input_manifest.json.gz')
        if sha(nativepath)!=manifest['native_program_sha256'] or sha(dispatchpath)!=manifest['source_dispatch_sha256']:raise ValueError('exact actual source artifacts')
        original_native=native
        native,homes,directory,binding=bind_storage(native,homes,manifest)
        (args.out/'storage_home_binding.json').write_text(json.dumps(binding,sort_keys=True,indent=2)+'\n')
        (args.out/'bound_native.json.gz').write_bytes(gzip.compress(json.dumps(native,sort_keys=True).encode(),mtime=0))
        (args.out/'bound_homes.json.gz').write_bytes(gzip.compress(json.dumps(homes,sort_keys=True).encode(),mtime=0))
        priced=project(native,homes,manifest,output_root=args.out)
        orphan_plan=retirement_plan(native,manifest,homes)
        manifest.update(prefix_inputs_bound=True,prefix_GO=True,prefix_stop=args.stop,provider_module='tools/ds_hbm_storage_home_binding_r41.py',provider_module_sha256=sha(ROOT/'tools/ds_hbm_storage_home_binding_r41.py'),journal_root=str((args.out/'actual-prefix-journal').resolve()),journal_capacity_bytes=priced['journal_capacity_bytes'])
        free=os.statvfs(args.out).f_bavail*os.statvfs(args.out).f_frsize
        if free<priced['journal_capacity_bytes']:raise ValueError('source matched projection exceeds fresh available disk; no fixed cap substitute')
        (args.out/'model.json').write_text(json.dumps(priced,sort_keys=True,indent=2)+'\n');(args.out/'actual_manifest.json.gz').write_bytes(gzip.compress(json.dumps(manifest,sort_keys=True).encode(),mtime=0))
        soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(hard,hard))
        declared_snapshot=copy.deepcopy(manifest)
        provider=create_prefix_provider(manifest,native,dispatch,homes,args.stop)
        if declared_snapshot!=manifest:raise ValueError('initializer mutated caller declaration')
        witness=Witness(provider,original_native,ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json')
        provenance=witness.initialization_provenance
        (args.out/'initialization_provenance.json').write_text(json.dumps(provenance,sort_keys=True,indent=2)+'\n')
        (args.out/'runtime_internal_manifest.json.gz').write_bytes(gzip.compress(json.dumps(provider.manifest,sort_keys=True).encode(),mtime=0))
        observed=Observed(provider,witness)
        engine=engine_class(driver_class(),finite_pc10=args.finite_pc10,retire_unconsumed=args.retire_unconsumed)(native,dispatch,observed,manifest['checkpoint_revision'],manifest['generation'],homes,native_artifact_path=args.out/'bound_native.json.gz',dispatch_artifact_path=dispatchpath,original_native_artifact_path=nativepath)
        if args.retire_unconsumed:record['unconsumed_output_plan_prefix']={str(pc):v for pc,v in engine.unconsumed_plan.items() if pc<=args.stop}
        (args.out/'engine_native_lineage.json').write_text(json.dumps(engine.groups.lineage,sort_keys=True,indent=2)+'\n')
        if args.preflight_only:
            record.update(status='PASS_ACTUAL_PROVIDER_WITNESS_ENGINE_CONSTRUCTORS',expected_outputs=len(witness.expected),native_PCs_executed=0,journal_event_rows=provider.journal_budget.db.execute('select count(*) from event').fetchone()[0],all_source_inputs_exact=True)
            save();return
        record.update(status='RUNNING_ACTUAL_SOURCE_PREFIX',model=priced,disk_available_bytes=free,manifest_sha256=sha(args.out/'actual_manifest.json.gz'));save();record.update(engine.run(stop_after=args.stop));record['comparison']=witness.finish();record['status']='PASS_SOURCE_NATIVE_PREFIX_BYTE_EXACT'
        record.update(checkpoint_reads=provider.checkpoint.receipts,retained_versions=[dict(version=v,rank=r) for v,r in sorted(provider.locations)],retained_future_source_windows=len(provider.source_images),journal_bytes=provider.journal_budget.path.stat().st_size,aggregate_reserved_bytes=provider.journal_budget.used,full_token_exact_qualified=False,primitive_scratch_transport_qualified=False)
    except Exception as e:record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(e).__name__,reason=str(e));save();raise
    finally:
        if provider is not None:provider.journal_budget.db.commit()
        record.update(end_ns=time.time_ns(),max_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save()
if __name__=='__main__':main()
