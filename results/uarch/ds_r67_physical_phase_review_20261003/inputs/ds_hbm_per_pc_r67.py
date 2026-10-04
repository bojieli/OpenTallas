"""Actual one-PC child and fresh-process state verifier; default-off, remote only.
All arithmetic executes inherited NativeExecution. Checksums/golden are never
execution or restore inputs. Original constructor, calendar and V3 guards stay.
"""
import argparse,copy,gzip,json,os,resource,subprocess,sys,time,traceback
from pathlib import Path
import ds_hbm_atomic_checkpoint_r67 as atomic

ROOT=Path(__file__).resolve().parents[1]


def exact_saved_tree(helper,encoded,current,payload):
    """Compare saved actual bytes with restored actual state without a new FIFO.
    Does not use expected numerical outputs. At most two1MiB byte chunks for
    array comparisons; port records are one46-byte actual sector at a time.
    """
    import numpy as np
    if not isinstance(encoded,dict):
        if type(encoded)is not type(current) or encoded!=current:raise ValueError('restored scalar identity mismatch')
        return
    if len(encoded)!=1:raise ValueError('typed saved tree required')
    kind,value=next(iter(encoded.items()))
    if kind=='sector_backing':
        if type(current)is not helper.SectorBacking or len(current.values)!=value['count']:
            raise ValueError('restored actual sector count mismatch')
        for i,((target,rank,sector),actual) in enumerate(current.values.items()):
            idx,saved_sector,mask,raw=helper.SECTOR_RECORD.unpack_from(payload,value['offset']+i*value['record_bytes'])
            if value['table'][idx]!=[target,rank] or saved_sector!=sector:
                raise ValueError('restored actual sector address mismatch')
            if len(actual)!=32 or any(actual[j]!=(raw[j] if mask>>j&1 else None) for j in range(32)):
                raise ValueError('restored actual sector bytes/validity mismatch')
        return
    if kind=='array':
        offset,n,dtype,shape,writeable=value
        if not isinstance(current,np.ndarray) or current.dtype.str!=dtype or list(current.shape)!=shape or current.nbytes!=n or bool(current.flags.writeable)!=writeable:
            raise ValueError('restored actual array type/shape mismatch')
        raw=memoryview(np.ascontiguousarray(current)).cast('B')
        for start in range(0,n,1048576):
            if bytes(raw[start:start+1048576])!=bytes(payload[offset+start:offset+min(start+1048576,n)]):
                raise ValueError('restored actual array bytes mismatch')
        return
    if kind=='dtype':
        if not isinstance(current,np.dtype) or current.str!=value:raise ValueError('restored dtype mismatch')
        return
    if kind=='bytes':
        offset,n,mutable=value
        if type(current)is not (bytearray if mutable else bytes) or current!=bytes(payload[offset:offset+n]):raise ValueError('restored bytes mismatch')
        return
    if kind=='dict':
        if type(current)is not dict or len(current)!=len(value):raise ValueError('restored dictionary ownership mismatch')
        for key,item in value:
            decoded=helper.read_tree(key,b'')
            if decoded not in current:raise ValueError('restored dictionary key mismatch')
            exact_saved_tree(helper,item,current[decoded],payload)
        return
    if kind=='set':
        if type(current)is not set or helper.read_tree(encoded,b'')!=current:raise ValueError('restored set mismatch')
        return
    typ={'tuple':tuple,'list':list}.get(kind)
    if typ is None or type(current)is not typ or len(current)!=len(value):raise ValueError('restored container mismatch')
    for item,actual in zip(value,current):exact_saved_tree(helper,item,actual,payload)


def verify_actual_restore(helper,checkpoint,provider,engine):
    import numpy as np
    root=Path(checkpoint);closure=json.loads((root/'state.json').read_bytes())
    p=helper.quiescent(provider,engine)
    helper.validate_backing(p)
    n=(root/'payload.bin').stat().st_size
    payload=np.memmap(root/'payload.bin',dtype=np.uint8,mode='r') if n else b''
    exact_saved_tree(helper,closure['state'],helper.snapshot_state(p,engine),payload)
    return dict(actual_payload_exact=True,live_debts=0,all_owners_drained=True,
        raw_RF_state_shared_bytes_and_masks_compared=True,ownership_versions_generations_counters_compared=True,
        retired_PCs=sorted(engine.retired),payload_bytes=n,comparison_uses_actual_checkpoint_only=True)


def constructors(scope_manifest,out):
    # Literal R63 constructor sequence, including original artifact equality,
    # regenerated home-only binding and all40 group templates. No MRO exemption.
    import ds_hbm_checkpointed_prefix_r63 as R
    from ds_hbm_connected_prepare_r37 import load,sha
    from h3_ds_connected_provider_r37 import D
    from ds_hbm_storage_home_binding_r41 import bind_storage,create_bound_provider
    from ds_hbm_pc10_engine_r44 import Witness
    from ds_hbm_prefix_observed_outputs_r42 import Observed
    nativepath=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
    dispatchpath=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz'
    original=load(nativepath);dispatch=load(dispatchpath)
    homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes']
    manifest=load(D/'inputs/prefix_input_manifest.json.gz')
    if sha(nativepath)!=manifest['native_program_sha256'] or sha(dispatchpath)!=manifest['source_dispatch_sha256']:
        raise ValueError('exact original native/dispatch artifacts')
    native,homes,directory,binding=bind_storage(original,homes,manifest)
    for name,value in [('bound_native',native),('bound_homes',homes)]:
        (out/(name+'.json.gz')).write_bytes(gzip.compress(json.dumps(value,sort_keys=True).encode(),mtime=0))
    manifest.update(prefix_inputs_bound=True,prefix_GO=True,prefix_stop=10,
        provider_module='tools/ds_hbm_storage_home_binding_r41.py',
        provider_module_sha256=sha(ROOT/'tools/ds_hbm_storage_home_binding_r41.py'),
        journal_root=scope_manifest['journal_root'],journal_capacity_bytes=scope_manifest['journal_capacity_bytes'])
    prefix,install=R.install_source_modules()
    declared=copy.deepcopy(manifest)
    p=create_bound_provider(manifest,native,dispatch,homes,10)
    if declared!=manifest:raise ValueError('constructor mutated source declaration')
    w=Witness(p,original,ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json')
    o=Observed(p,w)
    e=R.join.engine_class(prefix,finite_pc10=True,retire_unconsumed=True)(native,dispatch,o,
        manifest['checkpoint_revision'],manifest['generation'],homes,
        native_artifact_path=out/'bound_native.json.gz',dispatch_artifact_path=dispatchpath,
        original_native_artifact_path=nativepath)
    return p,w,o,e,manifest,install


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True)
    ap.add_argument('--pc',type=int,required=True);ap.add_argument('--verify-only',action='store_true')
    args=ap.parse_args()
    from ds_hbm_remote_controller_r67 import validate_child
    plan=validate_child(args.plan,args.pc,args.verify_only)
    import ds_hbm_registered_loader_r57 as loader
    import ds_hbm_checkpointed_prefix_r63 as R
    import ds_producer_checkpoint_resume_v3 as helper
    loader.install()
    _,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE,(hard,hard)) # Same R63 descriptor enrollment.
    out=Path(plan['output_root'])/(('verify' if args.verify_only else 'PC')+str(args.pc))
    out.mkdir()
    record=dict(status='INITIALIZING',pid=os.getpid(),source_plan_sha256=atomic.sha(args.plan),PC=args.pc,
        verify_only=args.verify_only,start_ns=time.time_ns(),native_PCs_executed=0,hardware_qualified=False)
    def save():
        tmp=out/'receipt.pending';tmp.write_bytes(atomic.canonical(record));os.replace(tmp,out/'receipt.json')
    save()
    try:
        p,w,o,e,manifest,install=constructors(dict(journal_root=str(out/'journal'),journal_capacity_bytes=plan['per_process_journal_capacity_bytes']),out)
        record['scope_role_proof']=helper.scope_role_proof(p,e);record['compact_install']=install
        checkpoint_pc=args.pc if args.verify_only else args.pc-1
        if checkpoint_pc>=0:
            previous=Path(plan['output_root'])/('checkpoint-PC'+str(checkpoint_pc))
            publication=json.loads((previous/'ATOMIC_COMPLETE.json').read_bytes())
            atomic.require_fresh_restore(publication)
            actual=json.loads((previous/'actual_observations.json').read_bytes())
            verified,restored=R.restore_cold(helper,checkpoint=previous,source_contract=actual['source_contract'],
                checkpoint_receipt=publication['producer_receipt'],provider=o,engine=e,witness=w,next_pc=checkpoint_pc+1)
            record['actual_restore_receipt']=restored
            record['actual_restore_exactness']=verify_actual_restore(helper,previous,o,e)
            record['restored_from_actual_producer_pid']=publication['producer_pid'];save()
        if args.verify_only:
            record.update(status='PASS_ACTUAL_COLD_PROCESS_RESTORE',retired_PCs=sorted(e.retired));save();return
        if e.retired!=set(range(args.pc)):raise ValueError('one exact next PC required')
        op=e.native['instructions'][args.pc]
        if op['pc']!=args.pc:raise ValueError('exact source PC identity')
        e.execute_operation(op) # Inherited source arithmetic; never a golden callback.
        record.update(native_PCs_executed=1,retired_PCs=sorted(e.retired),observed_outputs=len(w.seen));save()
        destination=Path(plan['output_root'])/('checkpoint-PC'+str(args.pc))
        contract=dict(identity=helper.identity(p,e),runner_source_sha256=atomic.sha(Path(__file__)),
            original_runner_source_sha256=atomic.sha(ROOT/'tools/ds_hbm_checkpointed_prefix_r55.py'),source_plan_sha256=atomic.sha(args.plan))
        projection=helper.project_checkpoint(e,o,w,boundary_pc=args.pc,destination=destination)
        priced=R.charged_projection(helper,projection,contract,checkpoint_upper=plan['per_checkpoint_capacity_bytes'])
        if priced['filesystem_reservation_bytes']>plan['per_checkpoint_capacity_bytes']:raise ValueError('actual checkpoint exceeds exact envelope')
        record['actual_checkpoint_projection']=priced
        record['capture_RAM_admission']=R.memory_admission(available_bytes=R.available_memory(),
            serialization_workspace_bytes=max(plan['capture_workspace_RAM_bytes'],priced['serialization_workspace_envelope_bytes']),
            cold_and_restore_new_bytes=plan['capture_workspace_RAM_bytes'])
        save()
        result=atomic.capture_atomic(helper,e,o,w,boundary_pc=args.pc,destination=destination,source_contract=contract,enabled=True)
        record.update(status='PASS_ACTUAL_ONE_PC_ATOMIC_CHECKPOINT',checkpoint=result,
            producer_journal_sealed=True,continuation_on_this_process_forbidden=True);save()
        # No execute, flush, commit or close on old provider graph after sealing.
        # Controller verifies journal bytes once this process has exited.
    except BaseException as exc:
        record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc());save();raise
    finally:
        record['end_ns']=time.time_ns();save()

if __name__=='__main__':main()
