"""Default-off remote full-source PC0-1 smoke; separate from R64/R67 guards."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import ds_hbm_remote_controller_r67 as remote
import ds_hbm_atomic_checkpoint_r67 as atomic
ROOT=Path(__file__).resolve().parents[1]


def scope(plan):
    if (plan.get('schema'),plan.get('full_native_PCs'),plan.get('full_homes'),plan.get('terminal_PC'))!=('DS_FULL_SOURCE_PC01_PLAN_R68',2213,290730,1):
        raise ValueError('exact separate full-source PC01 scope required')
    p=Path(plan['component_model'])
    if atomic.sha(p)!=plan['component_model_sha256']:raise ValueError('exact source component envelope required')
    model=json.loads(p.read_bytes())
    if model['source_sha256']!=plan['source_sha256'] or model['full_native_PCs']!=2213 or model['full_homes']!=290730:
        raise ValueError('component/source fullfuture identity mismatch')
    if (plan.get('output_root'),plan.get('resolved_output_root'))!=('/home/ubuntu/ds-hbm-pc01-r68-run-20261003',)*2:raise ValueError('exact source-priced persistent output required')
    remote.verify_sources(plan)
    return model


def verify_inputs(plan):
    path=Path(plan['immutable_input_index'])
    if atomic.sha(path)!=plan['immutable_input_index_sha256']:raise ValueError('exact immutable input index required')
    index=json.loads(path.read_bytes())
    for name,r in index['paths'].items():
        p=Path(name)
        if not p.is_file() or p.stat().st_size!=r['bytes'] or atomic.sha(p)!=r['sha256']:
            raise ValueError('actual source input absent or changed: '+name)
    if not Path(index['checkpoint_path']).is_dir():raise ValueError('actual released checkpoint absent')
    return index


def page_proof(plan,model,stage):
    key='constructor' if stage=='constructor' else 'runtime'
    price=model[key+'_projection']
    proof_path=Path(plan[key+'_parent_proof']);proof=json.loads(proof_path.read_bytes())
    # No guest+host sums, RSS/PSS discounts or independent extra sharedDirty
    # debit. Newly touched page union is one physical allocation/COW exposure.
    if proof.get('actual_output_root')!=plan['resolved_output_root'] or proof.get('physical_membership_verified') is not True:
        raise ValueError('exact output and physical guest membership required')
    if proof.get('write_set_source_model_sha256')!=plan['component_model_sha256'] or proof.get('write_set_COW_overlap_reviewed') is not True:
        raise ValueError('source write-set/COW-overlap proof required')
    mounts=[]
    for line in Path('/proc/mounts').read_text().splitlines():
        row=line.split()
        if len(row)>2 and Path(plan['resolved_output_root']).is_relative_to(row[1]):mounts.append((len(row[1]),row[2]))
    if not mounts or max(mounts)[1] in ('tmpfs','ramfs'):raise ValueError('persistent filesystem required; tmpfs not disk admission')
    fields=('allocator_page_upper_bytes','filecache_page_upper_bytes','page_tables_and_kernel_upper_bytes','guest_extra_page_upper_bytes','physical_new_page_union_upper_bytes')
    if any(type(proof.get(k))is not int or proof[k]<0 for k in fields):raise ValueError('positive complete physical page inventory required')
    if proof['allocator_page_upper_bytes']<price['required_RAM_bytes']:raise ValueError('source component cannot be lowered by page proof')
    touched=proof['allocator_page_upper_bytes']+proof['filecache_page_upper_bytes']+proof['page_tables_and_kernel_upper_bytes']
    if proof['physical_new_page_union_upper_bytes']<touched:raise ValueError('unproved touched-page exclusion or COW overlap credit')
    reserve=proof.get('other_owned_reservations_and_live_growth_bytes')
    if type(reserve)is not int or reserve<0 or proof.get('MemAvailable_bytes',0)-reserve<proof['physical_new_page_union_upper_bytes']:
        raise ValueError('physical touched-page aggregate admission fails')
    adapted=dict(plan,resource_projection=price,physical_parent_admission=str(proof_path))
    admission=remote.fresh_admission(adapted)
    if admission['available_RAM_bytes']<price['required_RAM_bytes']+proof['guest_extra_page_upper_bytes']:
        raise ValueError('guest allocator/kernel/filecache aggregate fails')
    admission.update(physical_new_page_union_upper_bytes=proof['physical_new_page_union_upper_bytes'],COW_counted_once=True)
    return admission


def validate(plan_path,*,stage,pc=None,verify_only=False):
    plan=json.loads(Path(plan_path).read_bytes())
    if plan.get('enrolled')is not True:raise ValueError('explicit remote source/page enrollment required')
    if stage not in ('constructor','runtime'):raise ValueError('exact priced stage required')
    if pc is not None and (type(pc)is not int or pc not in (0,1) or (verify_only and pc!=1)):
        raise ValueError('only actual PC0,PC1 and third-process PC1 restore')
    if sys.version!=plan['interpreter']['version'] or sys.implementation.name!=plan['interpreter']['implementation']:
        raise ValueError('exact source-priced interpreter required')
    raw=bytes(range(256))
    if any(raw[i]is not int(str(i)) for i in range(256)):raise ValueError('source byte-atom identity differs')
    if plan.get('source_root')!=str(ROOT):raise ValueError('exact enrolled deployed source root required')
    model=scope(plan);verify_inputs(plan);admission=page_proof(plan,model,stage)
    if stage=='runtime':
        receipt=json.loads((Path(plan['output_root'])/'constructors'/'receipt.json').read_bytes())
        if receipt.get('status')!='PASS_ACTUAL_PC01_DUAL_FULLSOURCE_CONSTRUCTORS' or receipt.get('source_plan_sha256')!=atomic.sha(plan_path):
            raise ValueError('actual same-plan complete dual constructors required')
        if receipt.get('native_PCs_executed')!=0 or receipt.get('actual_restore_executed')is not False or receipt.get('cold_data_identity_exact')is not True:
            raise ValueError('constructor scope/identity proof differs')
    return plan,model,admission


def run_child(path,mode):
    plan,model,admission=validate(path,stage='constructor' if mode=='constructors' else 'runtime')
    root=Path(plan['output_root'])
    if mode=='constructors':
        if root.exists():raise ValueError('fresh constructor output required; no retry')
        root.mkdir();atomic.durable_json(root/'admission.json',admission)
    label=mode
    argv=[sys.executable,str(ROOT/'tools/ds_hbm_pc01_child_r68.py'),'--plan',str(path)]
    if mode=='constructors':argv.append('--constructor-only')
    else:
        argv+=['--pc','0' if mode=='PC0' else '1']
        if mode=='verify1':argv.append('--verify-only')
    with (root/(label+'.log')).open('xb') as log:
        child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        atomic.durable_json(root/(label+'.handle.json'),dict(pid=child.pid,argv=argv,start_ns=time.time_ns(),source_plan_sha256=atomic.sha(path)))
        code=child.wait() # no runtime/CPU/affinity/AS/FSIZE limits
    receipt=json.loads((root/label/'receipt.json').read_bytes())
    expected={'constructors':'PASS_ACTUAL_PC01_DUAL_FULLSOURCE_CONSTRUCTORS','PC0':'PASS_ACTUAL_ONE_PC_ATOMIC_CHECKPOINT','PC1':'PASS_ACTUAL_ONE_PC_ATOMIC_CHECKPOINT','verify1':'PASS_ACTUAL_COLD_PROCESS_RESTORE'}[mode]
    if code or receipt.get('status')!=expected:raise ValueError('actual child failure preserved: '+label)
    if mode!='constructors':remote.verify_sealed_checkpoints(plan,0 if mode=='PC0' else 1)
    return receipt


def finish_smoke(a,b,v,source_sha):
    exact=v['actual_restore_exactness']
    if len({a['pid'],b['pid'],v['pid']})!=3:raise ValueError('three actual fresh process identities required')
    if a['retired_PCs']!=[0] or b['retired_PCs']!=[0,1] or exact['retired_PCs']!=[0,1] or exact['actual_payload_exact']is not True:
        raise ValueError('complete actual PC01 payload/retirement required')
    if exact.get('live_debts')!=0 or exact.get('all_owners_drained')is not True:raise ValueError('actual restored owners/credit debts must be drained')
    if a['observed_outputs']!=384 or b['observed_outputs']!=576:raise ValueError('all source PC01 publications required')
    if b['restored_from_actual_producer_pid']!=a['pid'] or v['restored_from_actual_producer_pid']!=b['pid']:
        raise ValueError('actual producer->cold->third process lineage required')
    return dict(exact,status='PASS_ACTUAL_PC0_1_ATOMIC_CHECKPOINT_COLD_PROCESS_RESTORE',
        source_plan_sha256=source_sha,producer_PC0_pid=a['pid'],producer_PC1_pid=b['pid'],verifier_pid=v['pid'],
        full_native_PCs=2213,full_homes=290730,observed_outputs=576,both_checkpoint_payloads_retained=True,
        sealed_journals_reverified_after_process_exit=True,full_token_GO=False,hardware_qualified=False)


def enroll(template,destination):
    plan=json.loads(Path(template).read_bytes())
    if plan.get('enrolled')is not False or Path(destination).exists():raise ValueError('fresh disabled template and fresh enrollment required')
    if plan.get('source_root')!=str(ROOT):raise ValueError('exact enrolled deployed source root required')
    model=scope(plan);verify_inputs(plan)
    page_proof(plan,model,'constructor');page_proof(plan,model,'runtime')
    plan['enrolled']=True
    atomic.durable_json(destination,plan)
    return plan


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--constructor-preflight',action='store_true');g.add_argument('--smoke',action='store_true');g.add_argument('--enroll',type=Path)
    args=p.parse_args()
    if args.enroll:enroll(args.enroll,args.plan);return
    if args.constructor_preflight:run_child(args.plan,'constructors');return
    a=run_child(args.plan,'PC0');b=run_child(args.plan,'PC1');v=run_child(args.plan,'verify1')
    plan=json.loads(args.plan.read_bytes())
    atomic.durable_json(Path(plan['output_root'])/'smoke_receipt.json',finish_smoke(a,b,v,atomic.sha(args.plan)))

if __name__=='__main__':main()
