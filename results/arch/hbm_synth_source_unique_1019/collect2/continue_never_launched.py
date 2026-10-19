import concurrent.futures, datetime, fcntl, json, os, pathlib, shlex, subprocess
A = pathlib.Path(__file__).resolve().parent
lock = (A/'collect2.controller.lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
M = json.loads((A/'failed_only_resume.stable.json').read_text())
I = json.loads((A/'inventory_collect2.json').read_text())
existing = {name for h in I.values() for name in h['data']['rows']}
rows = [x for x in M['failed_only'] if x['cell'] not in existing and x['cell'] not in ['ot_hgi_sfu_core_split3','ot_hbm_su_static_pgslice_lg__pv0']]
assert len(rows) == 9
R = '/srv/opentallas-scratch/claude/hd4g/gen2e2/failed_resume_1019'
S = '/srv/opentallas-scratch/claude/hd4g/gen2e2/src_6f783d0a1'
(A/'collect2.execution_manifest.json').write_text(json.dumps({'controller_pid':os.getpid(),'never_launched':rows,'preserved_existing':sorted(existing),'snapshot':'6f783d0a1','source_audit':'input_audit_collect2.json','no_S3_GEN_GO':True},indent=2)+'\n')
def run(x):
    cell,m,w,mem,bb,env = x['row']
    rowlock=(A/(cell+'.collect2.lock')).open('x')
    fcntl.flock(rowlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    extra=x['failure']['rounds'][0]['extra']; out=R+'/'+cell
    cmd='set -e; cd '+shlex.quote(S)+'; test ! -e '+shlex.quote(out)+'; '+shlex.join(['env','MEMG='+mem,'HIER=1','EXTRA='+','.join(extra),'WTOP='+w]+shlex.split(env)+['bash',R+'/synth_master.sh','.',out,cell,m,'-',bb,'--prefer','v16w/prefer_'+cell+'.txt'])+'; '+shlex.join(['env','MEMG='+mem,'bash','tools/hbm_die_v15/synth_etm.sh','.',out,cell])
    args=['/home/ubuntu/bin/ot-run','--mem',mem,'--threads','4','--dir',R+'/collect2_admitted','--priority','die','--','bash','-c',cmd]
    (A/(cell+'.collect2.execution.json')).write_text(json.dumps({'args':args,'pid':os.getpid(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
    with (A/(cell+'.collect2.client.log')).open('x') as f:
        p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT)
        (A/(cell+'.collect2.client.pid')).write_text(str(p.pid)+'\n')
        rc=p.wait()
    rec={'cell':cell,'client_rc':rc,'output':out,'status':'EXECUTION_COMPLETED_NEEDS_HASH_PORT_ETM_REVIEW' if rc==0 else 'FAIL_PRESERVED'}
    (A/(cell+'.collect2.receipt.json')).write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for result in ex.map(run,rows): pass
