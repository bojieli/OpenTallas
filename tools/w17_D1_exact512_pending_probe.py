"""One unchanged executable final-point capture; no compilation or prefix expansion."""
import fcntl,hashlib,json,os,resource,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/w17_D1_exact512_pending_probe_20261002'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(out):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    plan=json.loads((BASE/'plan.json').read_text())
    assert not (Path(plan['cwd'])/'prog.hex').exists()
    for kind in ('binary','header','GDB'):
        assert sha(plan[kind]['path'])==plan[kind]['SHA256']
    assert sha(BASE/'capture.gdb')==plan['script_SHA256']
    for path,want in plan['source_authority_SHA256'].items():assert sha(ROOT/path)==want
    for lim in (resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE):assert resource.getrlimit(lim)==(-1,-1)
    avail=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    assert avail>=144*2**30 and shutil.disk_usage('/tmp').free>=16*2**30
    assert 8 in os.sched_getaffinity(0)
    lease=open('/tmp/w17-D1-exact512-pending-probe.lock','w');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.sched_setaffinity(0,{8});out.mkdir(exist_ok=False)
    inputs={str(BASE/'plan.json'):sha(BASE/'plan.json'),str(BASE/'capture.gdb'):sha(BASE/'capture.gdb')}
    for kind in ('binary','header','GDB'):inputs[plan[kind]['path']]=plan[kind]['SHA256']
    rec=dict(status='RUNNING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),supervisor_PID=os.getpid(),actual_argv=plan['actual_argv'],cwd=plan['cwd'],available_memory=avail,capacity_reservation_bytes=144*2**30,imposed_limits=[],input_hashes=inputs,fulltoken=False,first_return_deadline=None,authorization='USER_EXPLICIT_REVERSIBLE_SOURCE_BOUND_DIAGNOSTIC_THIS_TURN')
    def save():(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();t=time.monotonic()
    with (out/'gdb.log').open('xb') as log:
        proc=subprocess.Popen([plan['GDB']['path'],'-batch','-nx','-x',str(BASE/'capture.gdb'),'-ex','run','-ex','printf "D1_INFERIOR_EXIT code=%d\\n", $_exitcode'],cwd=plan['cwd'],stdout=log,stderr=subprocess.STDOUT)
        rec['GDB_PID']=proc.pid;save();print(json.dumps(rec),flush=True);code=proc.wait()
    rec.update(status='TERMINAL_PENDING_OFFLINE_REVIEW',GDB_exit=code,wall_s=time.monotonic()-t,log_SHA256=sha(out/'gdb.log'),input_postchecks={p:sha(p)==s for p,s in inputs.items()},default_prog_still_absent=not (Path(plan['cwd'])/'prog.hex').exists());save()
if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
