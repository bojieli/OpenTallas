"""Separate source-priced PC01 child. Original full constructors/execute retained.
Only actual source state can cross an atomic boundary. No numerical launch here
without the independent remote physical page admission in the R68 controller.
"""
import argparse,json,os,resource,time,traceback
from pathlib import Path
import ds_hbm_atomic_checkpoint_r67 as atomic
from ds_hbm_per_pc_r67 import constructors,verify_actual_restore
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True)
    ap.add_argument('--pc',type=int);ap.add_argument('--verify-only',action='store_true');ap.add_argument('--constructor-only',action='store_true')
    args=ap.parse_args()
    from ds_hbm_pc01_controller_r68 import validate
    plan,model,admission=validate(args.plan,stage='constructor' if args.constructor_only else 'runtime',pc=args.pc,verify_only=args.verify_only)
    if not args.constructor_only and args.pc is None:raise ValueError('exact PC required')
    import ds_hbm_registered_loader_r57 as loader
    import ds_hbm_checkpointed_prefix_r63 as R
    import ds_producer_checkpoint_resume_v3 as helper
    loader.install()
    _,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE,(hard,hard)) # Same R63 descriptor enrollment.
    out=Path(plan['output_root'])/('constructors' if args.constructor_only else (('verify' if args.verify_only else 'PC')+str(args.pc)))
    out.mkdir()
    record=dict(status='INITIALIZING',pid=os.getpid(),source_plan_sha256=atomic.sha(args.plan),PC=args.pc,
        verify_only=args.verify_only,start_ns=time.time_ns(),native_PCs_executed=0,hardware_qualified=False)
    def save():
        tmp=out/'receipt.pending';tmp.write_bytes(atomic.canonical(record));os.replace(tmp,out/'receipt.json')
    save()
    try:
        journal_cap=model['other_process_journal_capacity_bytes'] if args.constructor_only or args.verify_only else model['PC'+str(args.pc)+'_journal_capacity_bytes']
        p,w,o,e,manifest,install=constructors(dict(journal_root=str(out/'journal'),journal_capacity_bytes=journal_cap),out)
        if len(e.native['instructions'])!=2213 or len(p.homes)!=290730:raise ValueError('complete native/homes required')
        record['scope_role_proof']=helper.scope_role_proof(p,e);record['compact_install']=install
        if args.constructor_only:
            cold=out/'cold';cold.mkdir()
            cp,cw,co,ce,cm,ci=constructors(dict(journal_root=str(cold/'journal'),journal_capacity_bytes=journal_cap),cold)
            role=helper.scope_role_proof(cp,ce)
            if helper.data_identity(helper.identity(p,e))!=helper.data_identity(helper.identity(cp,ce)) or role!=record['scope_role_proof']:
                raise ValueError('complete cold constructor data/role changed')
            if e.retired or ce.retired or w.seen or cw.seen:raise ValueError('constructors executed arithmetic')
            for holder in (p,cp):
                if any(path.stat().st_size>6 for path in holder.journal_budget.root.glob('*.events')):raise ValueError('constructor emitted numeric events')
            record.update(status='PASS_ACTUAL_PC01_DUAL_FULLSOURCE_CONSTRUCTORS',actual_restore_executed=False,cold_data_identity_exact=True,full_native_PCs=2213,full_homes=290730)
            record['source_contract']=dict(identity=helper.identity(p,e),runner_source_sha256=atomic.sha(Path(__file__)),source_plan_sha256=atomic.sha(args.plan))
            save();return
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
        priced=R.charged_projection(helper,projection,contract,checkpoint_upper=model['per_checkpoint_capacity_bytes'])
        if priced['filesystem_reservation_bytes']>model['per_checkpoint_capacity_bytes']:raise ValueError('actual checkpoint exceeds exact envelope')
        record['actual_checkpoint_projection']=priced
        record['capture_RAM_admission']=R.memory_admission(available_bytes=R.available_memory(),
            serialization_workspace_bytes=max(model['inherited_workspace_bytes'],priced['serialization_workspace_envelope_bytes']),
            cold_and_restore_new_bytes=model['inherited_workspace_bytes'])
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
