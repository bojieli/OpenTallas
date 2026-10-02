#!/usr/bin/env python3
"""Single GO-authorized observation; fail closed before compile on cap mismatch."""
import os,sys,time,json,pathlib,subprocess,signal,hashlib
OUT=pathlib.Path('/home/ubuntu/qwen-provider-observation-r4-20261002')
REPO=pathlib.Path('/home/ubuntu/OpenTallas-qwen-provider-observation-r4')
UNIT='qwen-provider-r4-20261002.service'
start=time.monotonic()
def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def caps():
    cg=pathlib.Path('/sys/fs/cgroup'+pathlib.Path('/proc/self/cgroup').read_text().strip().split('::')[1])
    names=['memory.max','memory.swap.max','memory.current','memory.peak','memory.events','cpu.max','cpu.stat','cpuset.cpus','cpuset.cpus.effective','cgroup.events']
    return dict(cgroup=str(cg),affinity=sorted(os.sched_getaffinity(0)),files={n:(cg/n).read_text() for n in names if (cg/n).exists()},monotonic=time.monotonic(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
c=caps()
c['systemd_properties']=subprocess.check_output(['systemctl','show',UNIT,'-p','RuntimeMaxUSec','-p','KillMode','-p','KillSignal','-p','TimeoutStopUSec','-p','MemoryMax','-p','MemorySwapMax','-p','AllowedCPUs','-p','CPUAffinity','-p','CPUQuotaPerSecUSec'],text=True)
save('caps_before.json',c)
assert c['affinity']==[31]
assert c['files']['cpuset.cpus.effective'].strip()=='31'
assert c['files']['memory.max'].strip()=='4294967296'
assert c['files']['memory.swap.max'].strip()=='0'
assert c['files']['cpu.max'].split()[0]==c['files']['cpu.max'].split()[1]
for property_line in ['RuntimeMaxUSec=2min 30s','KillMode=control-group','KillSignal=9','TimeoutStopUSec=0','MemoryMax=4294967296','MemorySwapMax=0']:
    assert property_line in c['systemd_properties'],property_line
assert subprocess.check_output(['git','status','--porcelain'],cwd=REPO)==b''
go=json.loads((OUT/'parent_GO.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==go['prepared_owner_commit']
for n,s in go['prepared_files_sha256'].items():assert sha(OUT/'source'/n)==s
save('cap_verification.json',dict(status='PASS_BEFORE_COMPILE',caps=c,limits=go['limits'],worktree_clean=True))
records=[]
def run(command,limit,logname):
    began=time.monotonic()
    with (OUT/logname).open('wb') as log:
        p=subprocess.Popen(command,cwd=REPO,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        timed_out=False
        try:code=p.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out=True
            os.killpg(p.pid,signal.SIGKILL)
            code=p.wait()
    result=dict(command=command,pid=p.pid,exit_code=code,timed_out=timed_out,limit_seconds=limit,elapsed_seconds=time.monotonic()-began,log=logname,log_sha256=sha(OUT/logname))
    records.append(result);save('run_receipt.json',dict(records=records,whole_elapsed_seconds=time.monotonic()-start,no_retries=True))
    return result
source=OUT/'source'
cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_actual_controller','-Mdir',str(OUT/'obj'),'-I'+str(source),str(source/'controller_observed.sv'),str(source/'tb_actual_controller.sv')]
save('compiler_version.json',dict(verilator=subprocess.check_output(['verilator','--version'],text=True),compiler=subprocess.check_output(['g++','--version'],text=True)))
r=run(cmd,120,'compile.log')
if r['exit_code']==0:
    binary=OUT/'obj/Vtb_actual_controller'
    save('binary_receipt.json',dict(path=str(binary),sha256=sha(binary),bytes=binary.stat().st_size,compiler_success=True))
    sim_start=time.monotonic()
    for case in [0,1,2]:
        remaining=30-(time.monotonic()-sim_start)
        if remaining<=0:
            save('sim_budget_exhausted.json',dict(next_case=case,aggregate_sim_seconds=time.monotonic()-sim_start));break
        run([str(binary),f'+CASE={case}',f'+QHP_JOURNAL={OUT}/case{case}.tsv',f'+QHP_CLIENT_JOURNAL={OUT}/case{case}_client.tsv'],remaining,f'case{case}.log')
    save('simulation_aggregate.json',dict(elapsed_seconds=time.monotonic()-sim_start,limit_seconds=30))
else:
    save('binary_receipt.json',dict(compiler_success=False,binary_present=(OUT/'obj/Vtb_actual_controller').exists(),cases_not_run='Single compilation failed; no retry/change/fallback'))
save('caps_after.json',caps())
save('termination.json',dict(status='COMPILE_FAILED_NO_RETRY' if r['exit_code'] else 'SINGLE_COMPILE_CASE_ATTEMPTS_COMPLETE',whole_elapsed_seconds=time.monotonic()-start,hardware_qualification=False,WRdone_generated=False))
