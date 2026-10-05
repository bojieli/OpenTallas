import datetime,fcntl,json,os,subprocess,sys,time
from pathlib import Path
WT=Path('/home/ubuntu/ds-recovery-negative-successor-20261002')
D=Path('/tmp/DS-recovery-negative-successor-capacity-20261002-r1')
Q=Path('/tmp/claude-1000/queue/DS-recovery-successor-local-reservation-20261002-r1')
RUN=Path('/tmp/DS-recovery-negative-successor-execution-20261002-r1')
PLAN=WT/'results/uarch/DS_recovery_negative_successor_20261002/preflight/plan.json'
sys.path.insert(0,str(WT/'tools'))
import DS_recovery_negative_successor as r
Q.mkdir(exist_ok=False)
r.write(D/'supervisor_identity.json',{'PID':os.getpid(),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip(),'supervisor_sha256':r.sha(__file__),'state':'WAITING_FOR_OWNER_RELEASE_OF_SHARED_ADMISSION_LOCK','no_job_started':True})
with Path('/tmp/opentallas-local-memory-heavy-admission.lock').open('a+') as shared:
    fcntl.flock(shared,fcntl.LOCK_EX)
    with (Q/'reservation.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        # Respect canonical current receipts, including explicit correction.
        existing=[]
        for p in sorted(Path('/tmp/claude-1000/queue').glob('*/cpu-reservation.receipt.json')):
            correction=p.parent/'cpu-reservation.corrected.receipt.json'
            actual=correction if correction.exists() else p
            v=r.read(actual)
            if v.get('reservation_active'):
                existing.append({'path':str(actual),'sha256':r.sha(actual),'CPUs':v.get('reserved_cpus',[]),'state':v.get('state')})
        conflicting=[v for v in existing if set(v['CPUs']) & {6,7}]
        if conflicting:
            r.write(D/'reservation_refusal.json',{'conflicts':conflicting,'no_execution':True})
            raise SystemExit(1)
        context=r.host_context(D)
        context['UTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        context['D1_terminal']=subprocess.check_output(['systemctl','--user','show','w17-D1-disjoint-local-20261002-r1.service','-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True)
        context['active_reservations']=existing
        context['service_properties']=subprocess.check_output(['systemctl','--user','show','DS-recovery-negative-successor-20261002-r1.service','-p','MemoryMax','-p','MemorySwapMax','-p','RuntimeMaxUSec','-p','LimitCPU','-p','LimitFSIZE','-p','LimitAS','-p','CPUQuotaPerSecUSec','-p','CPUAffinity','-p','ControlGroup'],text=True)
        r.write(D/'live_context_at_admission.json',context)
        lease={'schema':'DS-recovery-successor-disjoint-capacity.v1','PID':os.getpid(),'UTC':context['UTC'],'source_commit':'68e0a801d9d852e337453fc9ef87b1b9b47b69bd','plan_sha256':r.sha(PLAN),'reserved_cpus':[6,7],'reservation_active':True,'memory_reservation_bytes':16*2**30,'disk_reservation_bytes':16*2**30,'shared_admission_lock':shared.name,'reservation_lock':lock.name,'active_reservations':existing,'D1_CPUs_preserved':list(range(8,32)),'broadmask_TP96_contention':'Existing broadmask simulator retains affinity; CPU reservation is disjoint from peer assigned CPU sets, not exclusive scheduler isolation.','resource_limits':'No runtime/file/CPU-time/address-space/memory quota','release_condition':'Exact pinned successor terminal, child drained; no expiry or automatic restart.'}
        r.write(Q/'cpu-reservation.receipt.json',lease)
        r.write(D/'reservation.json',lease)
        inv=r.read(D/'historical_inventory.json')
        review=r.read(PLAN.parent/'review_template.json')
        review.update(status='MODEL_RESOURCE_CONTEXT_REVIEWED',reserved_CPUs=[6,7],active_job_CPUs=sorted(set([0,1]+list(range(8,32))+[x for v in existing for x in v['CPUs']])),reserved_memory_bytes=16*2**30,reserved_disk_bytes=16*2**30,measured_memory_peak_bytes=max(v['memory_peak_bytes'] for v in inv['measurements']),measured_output_peak_bytes=inv['five_retained_phase_bytes_estimate'],inventory_evidence=[{'path':str(D/'historical_inventory.json'),'sha256':r.sha(D/'historical_inventory.json')},{'path':str(D/'live_context_at_admission.json'),'sha256':r.sha(D/'live_context_at_admission.json')}],reservation_evidence=[{'path':str(D/'reservation.json'),'sha256':r.sha(D/'reservation.json')}],reviewer='Codex source-model/inventory review under parent authorization; shared Hubble/D1 admission lock acquired after owner release',fresh_admission_UTC=context['UTC'],reservation_not_cap=True)
        review_path=Path('/tmp/DS-recovery-negative-successor-reviewed-capacity.json')
        r.write(review_path,review)
        r.validate_review(review_path,PLAN,D)
        r.write(D/'review_validated.json',{'UTC':context['UTC'],'review_sha256':r.sha(review_path),'plan_sha256':r.sha(PLAN),'source_commit':lease['source_commit'],'source_plan_unchanged':True,'launch_authorized':True})
        command=['/usr/bin/python3',str(WT/'tools/DS_recovery_negative_successor.py'),'execute','--plan',str(PLAN),'--review',str(review_path),'--out',str(RUN)]
        with (D/'runner_stdout.log').open('x') as stdout:
            child=subprocess.Popen(command,cwd=WT,stdout=stdout,stderr=subprocess.STDOUT)
            r.write(D/'runner_identity.json',{'pid':child.pid,'command':command,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()})
            with (D/'service_samples.jsonl').open('x') as samples:
                while child.poll() is None:
                    cg=next(line.split('::',1)[1].strip() for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
                    path=Path('/sys/fs/cgroup')/cg.lstrip('/')
                    row=r.capacity_sample(D)
                    row['UTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    for k in ['memory.current','memory.peak','memory.events','cpu.stat','pids.current']:
                        row[k]=(path/k).read_text().strip()
                    row['output_files']=sum(1 for p in RUN.rglob('*') if p.is_file()) if RUN.exists() else 0
                    row['output_bytes']=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()) if RUN.exists() else 0
                    samples.write(json.dumps(row)+'\n');samples.flush()
                    time.sleep(5)
            code=child.wait()
        r.write(D/'terminal.json',{'returncode':code,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'record_sha256':r.sha(RUN/'record.json') if (RUN/'record.json').exists() else None,'runner_stdout_sha256':r.sha(D/'runner_stdout.log'),'completed_objects_preserved':True})
        r.write(Q/'released.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':code,'reservation_released':True,'no_retries':True})
raise SystemExit(code)
