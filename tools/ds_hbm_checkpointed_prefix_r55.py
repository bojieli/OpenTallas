"""Prepared fresh PC0..10 execution with actual quiescent PC9 checkpoint.

No numerical launch without exact reviewed source/storage plan. No CPU, wall,
address-space or file-size limits; no witness/reference restore. All originals
remain immutable. A fresh prefix is necessary because R45 payload was not saved.
"""
import argparse
import copy
import subprocess
import gzip
import hashlib
import importlib
import json
import os
import resource
import time
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,D,peer
from ds_hbm_connected_prepare_r37 import load,sha
from ds_hbm_storage_home_binding_r41 import bind_storage,create_bound_provider
from ds_hbm_source_prefix_r45 import driver_class
from ds_hbm_prefix_observed_outputs_r42 import Observed
from ds_hbm_pc10_engine_r44 import Witness
import ds_hbm_additive_endpoint_join_r54 as join


def source_gate(plan,*,available_bytes):
    if plan.get('schema')!='DS_PC0_10_ACTUAL_CHECKPOINT_LAUNCH_PLAN_R55':
        raise ValueError('exact reviewed launch-plan schema required')
    if plan.get('status')!='PASS_SOURCE_AND_STORAGE_REVIEW' or plan.get('stop')!=10 or plan.get('checkpoint_boundary')!=9:
        raise ValueError('complete PC0..10 source/storage review required')
    if plan.get('helper_module')!='ds_producer_checkpoint_resume_v3':
        raise ValueError('explicit enrolled compact V3 checkpoint helper required')
    pins=plan.get('source_sha256',{})
    required=['tools/ds_hbm_checkpointed_prefix_r55.py','tools/ds_hbm_additive_endpoint_join_r54.py',
              'tools/h3_complete_native_calendar_successor_r1.py','tools/ds_producer_checkpoint_resume_v3.py',
              'tools/h3_complete_native_calendar.py','tools/ds_producer_checkpoint_resume.py']
    if any(p not in pins for p in required):raise ValueError('complete runner/calendar/helper/original source list required')
    for path,wanted in pins.items():
        target=(ROOT/path).resolve()
        if not target.is_relative_to(ROOT.resolve()) or sha(target)!=wanted:
            raise ValueError('exact reviewed source pin mismatch: '+path)
    proof=plan.get('storage_proof',{})
    if set(proof)!={'path','sha256'}:raise ValueError('source-sized storage proof artifact required')
    target=(ROOT/proof['path']).resolve()
    if not target.is_relative_to(ROOT.resolve()) or sha(target)!=proof['sha256']:
        raise ValueError('exact storage proof artifact required')
    projection=json.loads(target.read_bytes())
    costs={key:projection.get(key) for key in ('journal_new_bytes','checkpoint_new_bytes','other_new_bytes')}
    if any(type(v)is not int or v<=0 for v in costs.values()):
        raise ValueError('positive complete journal/checkpoint/metadata projection required')
    required_bytes=sum(costs.values())
    if projection.get('projection_complete') is not True or projection.get('source_sha256')!=pins:
        raise ValueError('storage proof must compose exact reviewed source list')
    if type(available_bytes)is not int or available_bytes<required_bytes:
        raise ValueError('fresh aggregate journal/checkpoint/metadata disk headroom insufficient')
    phases={key:projection.get(key) for key in ('producer_journal_new_bytes','continuation_journal_new_bytes',
                                              'cold_and_restore_new_RAM_bytes','producer_new_RAM_bytes',
                                              'serialization_workspace_RAM_bytes')}
    if any(type(v)is not int or v<=0 for v in phases.values()):
        raise ValueError('source-priced distinct producer/continuation journals and coexistence RAM required')
    if phases['producer_journal_new_bytes']+phases['continuation_journal_new_bytes']!=costs['journal_new_bytes']:
        raise ValueError('aggregate journal proof must charge both phase dictionaries/indexes exactly once')
    return dict(costs,**phases,required_new_bytes=required_bytes,available_bytes=available_bytes,
                headroom_bytes=available_bytes-required_bytes,capacity_reservation_acquired=False)


def enrolled_helper(plan):
    helper=importlib.import_module(plan['helper_module'])
    path=ROOT/'tools'/('ds_producer_checkpoint_resume_v3.py')
    if Path(helper.__file__).resolve()!=path.resolve() or sha(path)!=plan['source_sha256'][str(path.relative_to(ROOT))]:
        raise ValueError('exact compact checkpoint runtime origin required')
    for name in ('scope_role_proof','project_checkpoint','capture_quiescent','journal_inventory',
                 'plan_run_scope_transition','verify_checkpoint','restore_quiescent','execute_remaining'):
        if not callable(getattr(helper,name,None)):raise ValueError('checkpoint API absent: '+name)
    return helper


def install_source_modules():
    # Import exact pinned peer modules BEFORE replacing their evidence aliases.
    import sys
    import hbm_bound_event_journal_r30 as journal
    import h3_ds_checkpoint_provider_r30
    import h4_hbm_w19_pc10_endpoints
    import ds_hbm_prefix_observed_outputs_r42
    OriginalDiskEvents=journal.DiskEvents
    OriginalBudget=journal.JournalBudget
    OriginalProvider=join.OriginalSectorProvider
    peer('h4_c0_ds_source_views');peer('h4_c0_provider_movement')
    prefix=driver_class()
    classes=(OriginalDiskEvents,OriginalBudget,OriginalProvider)
    modules=[]
    for module in list(sys.modules.values()):
        if module is None or module is join or getattr(module,'__name__','')=='ds_hbm_current_calendar_adapter_r50':continue
        filename=getattr(module,'__file__',None)
        if not filename or not Path(filename).resolve().is_relative_to(ROOT.resolve()):continue
        if any(isinstance(value,type) and value in classes for value in vars(module).values()):modules.append(module)
    receipt=join.install(modules)
    return prefix,receipt



def charged_projection(helper, projection, source_contract, *, checkpoint_upper):
    """Match V3 capture's complete source-contract charge before payload write."""
    priced=copy.deepcopy(projection)
    extra=len(helper.canonical(source_contract))
    priced['source_contract_bytes']=extra
    priced['metadata_bytes_upper']+=extra
    priced['filesystem_reservation_bytes']+=extra
    if priced['filesystem_reservation_bytes']>checkpoint_upper:
        raise ValueError('actual producer checkpoint plus source contract exceeds reviewed envelope')
    return priced


def memory_admission(*, available_bytes, serialization_workspace_bytes,
                     cold_and_restore_new_bytes, retained_producer=True):
    # MemAvailable already excludes the resident producer. Keep that producer
    # read-only until the new engine finishes so journal handles are never closed
    # or committed after sealing. The reviewed incremental envelope must include
    # the cold constructor AND restored arrays/sector dictionaries simultaneously.
    for value in (available_bytes,serialization_workspace_bytes,cold_and_restore_new_bytes):
        if type(value)is not int or value<=0:raise ValueError('positive measured/projected RAM bytes required')
    required=max(serialization_workspace_bytes,cold_and_restore_new_bytes)
    if available_bytes<required:raise ValueError('actual RAM headroom insufficient for retained producer and cold restore')
    return dict(available_bytes=available_bytes,incremental_peak_bytes=required,
                headroom_bytes=available_bytes-required,producer_retained=retained_producer,
                producer_resident_already_excluded_from_available=retained_producer,process_memory_cap=False)


def available_memory():
    fields=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(fields['MemAvailable'].split()[0])*1024


def restore_cold(helper, *, checkpoint, source_contract, checkpoint_receipt,
                 provider, engine, witness, next_pc):
    transition=helper.plan_run_scope_transition(checkpoint,source_contract=source_contract,
        checkpoint_receipt=checkpoint_receipt,provider=provider,engine=engine,next_pc=next_pc)
    verified=helper.verify_checkpoint(checkpoint,source_contract=source_contract,next_pc=next_pc,
        constructor_contract=dict(identity=helper.identity(helper.unwrap(provider),engine),
            checkpoint_receipt=checkpoint_receipt,run_scope_transition=transition,
            run_scope=helper.run_scope(helper.unwrap(provider))))
    restored=helper.restore_quiescent(verified,engine,provider,witness)
    return verified,restored


def verify_sealed(helper, verified):
    helper.verify_journal_inventory(json.loads(
        (Path(verified['checkpoint_dir'])/'state.json').read_bytes())['historical_journal_inventory'])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():raise ValueError('fresh absolute output; no retry/fallback')
    plan=json.loads(args.plan.read_bytes())
    stat=os.statvfs(args.out.parent)
    admitted=source_gate(plan,available_bytes=stat.f_bavail*stat.f_frsize)
    helper=enrolled_helper(plan)
    prelaunch_RAM=memory_admission(available_bytes=available_memory(),
        serialization_workspace_bytes=admitted['producer_new_RAM_bytes']+admitted['serialization_workspace_RAM_bytes'],
        cold_and_restore_new_bytes=admitted['producer_new_RAM_bytes']+admitted['cold_and_restore_new_RAM_bytes'],
        retained_producer=False)
    args.out.mkdir()
    record=dict(status='INITIALIZING',pid=os.getpid(),start_ns=time.time_ns(),source_plan_sha256=sha(args.plan),
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),storage=admitted,
                prefix_stop=10,checkpoint_boundary=9,full_token_GO=False,hardware_qualified=False,
                prelaunch_RAM_admission=prelaunch_RAM)
    provider=None
    producer_sealed=False
    def save():
        (args.out/'receipt.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    save()
    try:
        nativepath=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
        dispatchpath=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz'
        original=load(nativepath);dispatch=load(dispatchpath)
        homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes']
        manifest=load(D/'inputs/prefix_input_manifest.json.gz')
        if sha(nativepath)!=manifest['native_program_sha256'] or sha(dispatchpath)!=manifest['source_dispatch_sha256']:
            raise ValueError('exact original native/dispatch artifacts')
        native,homes,directory,binding=bind_storage(original,homes,manifest)
        for name,value in [('bound_native',native),('bound_homes',homes)]:
            (args.out/(name+'.json.gz')).write_bytes(gzip.compress(json.dumps(value,sort_keys=True).encode(),mtime=0))
        (args.out/'storage_home_binding.json').write_text(json.dumps(binding,sort_keys=True)+'\n')
        manifest.update(prefix_inputs_bound=True,prefix_GO=True,prefix_stop=10,
            provider_module='tools/ds_hbm_storage_home_binding_r41.py',
            provider_module_sha256=sha(ROOT/'tools/ds_hbm_storage_home_binding_r41.py'),
            journal_root=str(args.out/'actual-prefix-journal'),journal_capacity_bytes=admitted['producer_journal_new_bytes'])
        prefix,install_receipt=install_source_modules()
        record['compact_install']=install_receipt;save()
        _,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(hard,hard))
        def construct(scope_manifest):
            declared=copy.deepcopy(scope_manifest)
            p=create_bound_provider(scope_manifest,native,dispatch,homes,10)
            if declared!=scope_manifest:raise ValueError('constructor mutated source declaration')
            w=Witness(p,original,ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json')
            o=Observed(p,w)
            e=join.engine_class(prefix,finite_pc10=True,retire_unconsumed=True)(native,dispatch,o,
                scope_manifest['checkpoint_revision'],scope_manifest['generation'],homes,
                native_artifact_path=args.out/'bound_native.json.gz',dispatch_artifact_path=dispatchpath,
                original_native_artifact_path=nativepath)
            if helper.shared_factory(p,e) is not e.groups.shared:
                raise ValueError('exact enrolled shared factory required')
            return p,w,o,e
        provider,witness,observed,engine=construct(manifest)
        role=helper.scope_role_proof(provider,engine)
        (args.out/'actual_manifest.json.gz').write_bytes(gzip.compress(json.dumps(manifest,sort_keys=True).encode(),mtime=0))
        (args.out/'initialization_provenance.json').write_text(json.dumps(witness.initialization_provenance,sort_keys=True)+'\n')
        record.update(role_proof=role,expected_outputs=len(witness.expected),retired_PCs=[],native_PCs_executed=0)
        if args.preflight_only:
            cold_manifest=copy.deepcopy(manifest)
            cold_manifest.update(journal_root=str(args.out/'actual-continuation-journal'),
                                 journal_capacity_bytes=admitted['continuation_journal_new_bytes'])
            cp,cw,co,ce=construct(cold_manifest)
            if helper.data_identity(helper.identity(provider,engine))!=helper.data_identity(helper.identity(cp,ce)):
                raise ValueError('cold constructor changed exact data/program/resource identity')
            if helper.scope_role_proof(cp,ce)!=role:raise ValueError('cold source role differs')
            for p in (provider,cp):
                if any(path.stat().st_size>6 for path in p.journal_budget.root.glob('*.events')):
                    raise ValueError('constructor preflight generated actual execution events')
            if engine.retired or ce.retired or witness.seen or cw.seen:
                raise ValueError('constructor preflight executed arithmetic or restore')
            record.update(status='PASS_ACTUAL_PRODUCER_AND_COLD_ADDITIVE_CONSTRUCTORS',
                          actual_restore_executed=False,native_PCs_executed=0,
                          cold_data_identity_exact=True,cold_role_proof=helper.scope_role_proof(cp,ce))
            save();return
        record['status']='RUNNING_FRESH_ACTUAL_SOURCE_PREFIX_WITH_PC9_CHECKPOINT';save()
        for op in native['instructions'][:10]:
            engine.execute_operation(op)
            record.update(retired_PCs=sorted(engine.retired),native_PCs_executed=len(engine.retired),
                          observed_outputs=len(witness.seen),aggregate_reserved_bytes=provider.journal_budget.used)
            save()
        checkpoint=args.out/'actual-PC9-producer-checkpoint'
        source_contract=dict(identity=helper.identity(provider,engine),runner_source_sha256=sha(__file__),
                             source_plan_sha256=sha(args.plan))
        projection=helper.project_checkpoint(engine,observed,witness,boundary_pc=9,destination=checkpoint)
        priced=charged_projection(helper,projection,source_contract,checkpoint_upper=admitted['checkpoint_new_bytes'])
        stat=os.statvfs(args.out)
        disk=helper.join_storage_projection(priced,
            continuation_new_bytes=admitted['continuation_journal_new_bytes'],
            other_new_bytes=admitted['other_new_bytes'],available_bytes=stat.f_bavail*stat.f_frsize)
        if disk['status']!='PASS_STORAGE_PROJECTION':raise ValueError('actual capture/continuation disk headroom insufficient')
        ram=memory_admission(available_bytes=available_memory(),
            serialization_workspace_bytes=priced['serialization_workspace_envelope_bytes']+len(helper.canonical(source_contract)),
            cold_and_restore_new_bytes=admitted['cold_and_restore_new_RAM_bytes'])
        record.update(actual_capture_disk_admission=disk,actual_capture_RAM_admission=ram,
                      actual_charged_checkpoint_projection=priced);save()
        receipt=helper.capture_quiescent(engine,observed,witness,boundary_pc=9,destination=checkpoint,
                                         source_contract=source_contract)
        producer_sealed=True
        record.update(actual_PC9_checkpoint_receipt=receipt,status='ACTUAL_PRODUCER_SEALED_COLD_RESTORE_PENDING');save()
        # Preserve the old live object graph read-only, including journal handles.
        # No finally commit/close on that graph after capture: historical bytes,
        # index and dictionary must stay immutable through cold continuation.
        new_manifest=copy.deepcopy(manifest)
        new_manifest.update(journal_root=str(args.out/'actual-continuation-journal'),
                            journal_capacity_bytes=admitted['continuation_journal_new_bytes'])
        stat=os.statvfs(args.out)
        remaining=admitted['continuation_journal_new_bytes']+admitted['other_new_bytes']
        if stat.f_bavail*stat.f_frsize<remaining:
            raise ValueError('fresh continuation dictionary/index/metadata disk headroom insufficient')
        record['cold_constructor_RAM_admission']=memory_admission(available_bytes=available_memory(),
            serialization_workspace_bytes=admitted['serialization_workspace_RAM_bytes'],
            cold_and_restore_new_bytes=admitted['cold_and_restore_new_RAM_bytes'])
        # Capture completed before this sample: checkpoint bytes are already used
        # disk. Retain the reviewed serialization workspace as an overcharge,
        # rather than assuming Python immediately releases allocator arenas.
        save()
        cold_provider,cold_witness,cold_observed,cold_engine=construct(new_manifest)
        verified,restored=restore_cold(helper,checkpoint=checkpoint,source_contract=source_contract,
            checkpoint_receipt=receipt,provider=cold_observed,engine=cold_engine,witness=cold_witness,next_pc=10)
        record.update(actual_restore_receipt=restored,status='ACTUAL_COLD_RESTORE_COMPLETE_PC10_PENDING');save()
        helper.execute_remaining(cold_engine,stop_after=10)
        verify_sealed(helper,verified)
        record.update(comparison=cold_witness.finish(),status='PASS_ACTUAL_CHECKPOINTED_PC0_10_BYTE_EXACT',
                      retired_PCs=sorted(cold_engine.retired),native_PCs_executed=len(cold_engine.retired),
                      observed_outputs=len(cold_witness.seen),
                      continuation_journal_inventory=helper.journal_inventory(cold_provider,cold_engine,cold_witness,hashes=True),
                      sealed_producer_journal_verified_immutable=True,full_token_exact_qualified=False)
    except BaseException as exc:
        record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));save();raise
    finally:
        if provider is not None and not producer_sealed:provider.journal_budget.db.commit()
        record.update(end_ns=time.time_ns(),max_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save()


if __name__=='__main__':main()
