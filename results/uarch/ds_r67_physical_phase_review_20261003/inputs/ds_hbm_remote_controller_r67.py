"""Remote-only actual per-PC subprocess controller. No guessed process caps.
Source/static preparation is local-safe; runtime needs real remote/parent proof.
"""
import argparse,ast,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALIASES={'ot-pve1':('ot-pve1',),'ot-agidock128':('vm-xry57mhfyn','ot-agidock128')}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources(plan):
    for path,wanted in plan['source_sha256'].items():
        p=ROOT/path
        if not p.resolve().is_relative_to(ROOT) or sha(p)!=wanted:raise ValueError('exact enrolled source required: '+path)
        if path.endswith(('.py','.py.source')):compile(p.read_bytes(),str(p),'exec')
    if plan.get('static_all_helpers_complete') is not True:raise ValueError('static ALL-helper inventory required')


def owned_allocated(root):
    total=0
    if root.exists():
        for p in root.rglob('*'):
            if p.is_symlink():raise ValueError('no output symlink capacity credit')
            if p.is_file():total+=p.stat().st_blocks*512
    return total


def fresh_admission(plan):
    alias=plan['host_alias']
    if alias not in ALIASES or socket.gethostname() not in ALIASES[alias]:raise ValueError('enrolled remote host only; no local numerical launch')
    root=Path(plan['output_root'])
    if not root.is_absolute() or str(root.resolve())!=plan['resolved_output_root']:raise ValueError('exact priced persistent output root required')
    price=plan['resource_projection']
    if price.get('projection_complete') is not True:raise ValueError('complete source resource price required')
    proof_path=Path(plan['physical_parent_admission'])
    proof=json.loads(proof_path.read_bytes())
    now=time.time_ns()
    if proof.get('reviewed') is not True or proof.get('guest_alias')!=alias or proof.get('source_projection_sha256')!=hashlib.sha256(canonical(price)).hexdigest():
        raise ValueError('reviewed physical-parent aggregate proof required')
    # Validity interval is supplied by measured host coordination, not a job
    # timeout. Parent must refresh its evidence as active-job ownership changes.
    if not proof['measured_ns']<=now<=proof['valid_until_ns']:raise ValueError('fresh physical-parent ownership/headroom evidence required')
    reserve=proof['other_owned_reservations_and_live_growth_bytes']
    if type(reserve)is not int or reserve<0 or proof['MemAvailable_bytes']-reserve<price['required_RAM_bytes']:
        raise ValueError('physical-parent aggregate RAM admission fails')
    m=dict(x.split(':',1) for x in Path('/proc/meminfo').read_text().splitlines())
    available=int(m['MemAvailable'].split()[0])*1024
    if available<price['required_RAM_bytes']:raise ValueError('guest RAM admission fails')
    if alias=='ot-agidock128' and price['required_RAM_bytes']>proof['fleet_remaining_RAM_budget_bytes']:
        raise ValueError('fleet aggregate RAM budget fails')
    stat=os.statvfs(root.parent)
    already=owned_allocated(root)
    remaining=max(0,price['required_disk_bytes']-already)
    if stat.f_bavail*stat.f_frsize<remaining:raise ValueError('actual output filesystem aggregate disk admission fails')
    return dict(hostname=socket.gethostname(),parent_proof_sha256=sha(proof_path),
        available_RAM_bytes=available,required_RAM_bytes=price['required_RAM_bytes'],
        available_disk_bytes=stat.f_bavail*stat.f_frsize,remaining_new_disk_bytes=remaining,
        already_allocated_owned_output_bytes=already,arbitrary_process_limits=False)


def verify_inputs(plan):
    index_path=Path(plan['immutable_input_index'])
    if sha(index_path)!=plan['immutable_input_index_sha256']:raise ValueError('exact immutable source input index required')
    index=json.loads(index_path.read_bytes())
    for name,record in index['paths'].items():
        p=Path(name)
        if not p.is_file() or p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:
            raise ValueError('actual source input absent or changed: '+name)
    if not Path(index['checkpoint_path']).is_dir():raise ValueError('actual released checkpoint source absent')
    return True


def enroll(template,*,destination,input_index,parent_proof,constructor_receipt,constructor_plan):
    plan=json.loads(Path(template).read_bytes())
    if Path(destination).exists():raise ValueError('fresh enrolled plan required')
    plan.update(immutable_input_index=str(Path(input_index).resolve()),immutable_input_index_sha256=sha(input_index),
        physical_parent_admission=str(Path(parent_proof).resolve()),actual_dual_constructor_receipt=str(Path(constructor_receipt).resolve()),
        actual_dual_constructor_plan=str(Path(constructor_plan).resolve()),actual_dual_constructor_sha256=sha(constructor_receipt))
    verify_sources(plan);verify_inputs(plan);fresh_admission(plan)
    from ds_hbm_checkpoint_execution_r63 import validate_preflight
    receipt=json.loads(Path(constructor_receipt).read_bytes());validate_preflight(receipt)
    if receipt['source_plan_sha256']!=sha(constructor_plan):raise ValueError('constructor lineage differs')
    plan['enrolled']=True
    with Path(destination).open('xb') as f:f.write(canonical(plan));f.flush();os.fsync(f.fileno())
    return plan


def validate_child(path,pc,verify_only):
    plan=json.loads(Path(path).read_bytes())
    if plan.get('enrolled') is not True:raise ValueError('explicit reviewed remote enrollment required')
    if sys.implementation.name!=plan['interpreter']['implementation'] or sys.version!=plan['interpreter']['version']:
        raise ValueError('exact source-priced interpreter required')
    raw=bytes(range(256))
    if any(raw[i] is not int(str(i)) for i in range(256)):raise ValueError('source byte-atom representation differs')
    verify_sources(plan);fresh_admission(plan)
    if type(pc)is not int or not 0<=pc<=10:raise ValueError('prepared exact PC0..10 scope only')
    preflight=json.loads(Path(plan['actual_dual_constructor_receipt']).read_bytes())
    from ds_hbm_checkpoint_execution_r63 import validate_preflight
    validate_preflight(preflight)
    if sha(Path(plan['actual_dual_constructor_receipt']))!=plan['actual_dual_constructor_sha256']:
        raise ValueError('exact actual R64 constructor receipt required')
    if preflight['source_plan_sha256']!=sha(Path(plan['actual_dual_constructor_plan'])):
        raise ValueError('exact constructor plan lineage required')
    if not verify_only and pc>1:
        smoke=json.loads((Path(plan['output_root'])/'smoke_receipt.json').read_bytes())
        if smoke.get('status')!='PASS_ACTUAL_PC0_1_ATOMIC_CHECKPOINT_COLD_PROCESS_RESTORE' or smoke.get('source_plan_sha256')!=sha(path):
            raise ValueError('actual same-source PC0-1 smoke required before long prefix')
    return plan


def verify_sealed_checkpoints(plan,through):
    import ds_producer_checkpoint_resume_v3 as helper
    for pc in range(through+1):
        root=Path(plan['output_root'])/('checkpoint-PC'+str(pc))
        closure=json.loads((root/'state.json').read_bytes())
        helper.verify_journal_inventory(closure['historical_journal_inventory'])
    return True


def child(plan_path,plan,pc,*,verify_only=False):
    fresh_admission(plan)
    argv=[sys.executable,str(ROOT/'tools/ds_hbm_per_pc_r67.py'),'--plan',str(plan_path),'--pc',str(pc)]
    if verify_only:argv.append('--verify-only')
    label=('verify' if verify_only else 'PC')+str(pc)
    log=Path(plan['output_root'])/(label+'.log')
    with log.open('xb') as f:
        process=subprocess.Popen(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        handle=dict(pid=process.pid,argv=argv,source_plan_sha256=sha(plan_path),label=label,start_ns=time.time_ns())
        (Path(plan['output_root'])/'live_child.json').write_bytes(canonical(handle))
        status=process.wait() # No wall/CPU timeout, affinity, AS or FSIZE cap.
    receipt_path=Path(plan['output_root'])/label/'receipt.json'
    receipt=json.loads(receipt_path.read_bytes()) if receipt_path.exists() else {}
    expected='PASS_ACTUAL_COLD_PROCESS_RESTORE' if verify_only else 'PASS_ACTUAL_ONE_PC_ATOMIC_CHECKPOINT'
    if status!=0 or receipt.get('status')!=expected:raise ValueError('actual child failure preserved: '+label)
    verify_sealed_checkpoints(plan,pc)
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--admission-only',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--continue-through-PC10',action='store_true')
    p.add_argument('--enroll',type=Path);p.add_argument('--input-index',type=Path)
    p.add_argument('--parent-proof',type=Path);p.add_argument('--constructor-receipt',type=Path);p.add_argument('--constructor-plan',type=Path)
    args=p.parse_args()
    if args.enroll:
        enroll(args.enroll,destination=args.plan,input_index=args.input_index,parent_proof=args.parent_proof,
            constructor_receipt=args.constructor_receipt,constructor_plan=args.constructor_plan)
        return
    if sum((args.admission_only,args.smoke,args.continue_through_PC10))!=1:raise ValueError('one explicit admission, smoke or continuation mode required')
    plan=json.loads(args.plan.read_bytes());verify_sources(plan);admission=fresh_admission(plan)
    root=Path(plan['output_root'])
    if args.admission_only:
        print(json.dumps(admission,sort_keys=True));return
    if args.smoke:
        if root.exists():raise ValueError('fresh smoke output; no retry or silent resume')
        root.mkdir();(root/'admission.json').write_bytes(canonical(admission))
        a=child(args.plan,plan,0);b=child(args.plan,plan,1);v=child(args.plan,plan,1,verify_only=True)
        exact=v['actual_restore_exactness']
        if exact['retired_PCs']!=[0,1] or not exact['actual_payload_exact']:raise ValueError('actual PC0-1 restore incomplete')
        record=dict(exact,status='PASS_ACTUAL_PC0_1_ATOMIC_CHECKPOINT_COLD_PROCESS_RESTORE',
            producer_pid=b['pid'],restore_pid=v['pid'],PC0_producer_pid=a['pid'],
            sealed_journals_verified_after_producer_exit=True,source_plan_sha256=sha(args.plan),
            observed_outputs=b['observed_outputs'],native_PC0_1_executed=True,hardware_qualified=False)
        (root/'smoke_receipt.json').write_bytes(canonical(record))
    else:
        validate_child(args.plan,2,False)
        # Resume actual PC1 state. No PC0..1 rerun, no golden/witness restore.
        for pc in range(2,11):child(args.plan,plan,pc)
        v=child(args.plan,plan,10,verify_only=True)
        (root/'terminal.json').write_bytes(canonical(dict(status='PASS_ACTUAL_PER_PC_CHECKPOINTED_PC0_10',
            source_plan_sha256=sha(args.plan),actual_restore_exactness=v['actual_restore_exactness'],
            full_token_GO=False,hardware_qualified=False)))

if __name__=='__main__':main()
