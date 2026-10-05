import json,os,hashlib,subprocess,time,shutil
from pathlib import Path
pin=Path('/home/ubuntu/w19-complete-functional-pin-066');root=Path(__file__).resolve().parent
mem={l.split()[0].rstrip(':'):int(l.split()[1])*1024 for l in open('/proc/meminfo')}
avail=mem['MemAvailable'];free=shutil.disk_usage(pin).free
assert avail>=128*2**30 and free>=2*2**30 and os.getloadavg()[0]<os.cpu_count(), 'fresh resource admission refused'
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=pin,text=True).strip()
assert sha.startswith('066dad009') and not subprocess.check_output(['git','status','--porcelain'],cwd=pin,text=True)
admission={'schema':'opentallas.deepseek.complete.software-job-admission.v1','source_commit':sha,'worktree':str(pin),
 'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'memory_available_bytes':avail,'disk_free_bytes':free,
 'cpu_count':os.cpu_count(),'loadavg':os.getloadavg(),'OMP_OPENBLAS_threads':1,'nice':15,
 'decoded_initialKV_bytes_estimate':6710886400,'decoded_six_experts_plus_shared_layer_cache_estimate_bytes':2300000000,
 'private_heap_reserve_bytes':24*2**30,'RSS_guard_bytes_including_readonly_checkpoint_mmap_pages':96*2**30,
 'output_disk_reserve_bytes':2*2**30,'checkpoint_payload_copies':False,'jobs':'fullL0compare53ops thenfull40+head2213ops sequential',
 'ordinary_GPU_lowering_complete':False,'DUT_executed':False,'physical_backend_bound':False,
 'sparse_checkout_intake':'no-checkout add then sparse set required read-tree --reset -u HEAD to populate; no full checkout created'}
(root/'admission.json').write_text(json.dumps(admission,indent=2)+'\n')
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'};results=[]
for name,stop in [('full-L0',53),('full-40-head',None)]:
 out=root/name
 assert not out.exists(), 'refuse evidence overwrite'
 cmd=['nice','-n','15','python3','tools/deepseek_hbm_complete_executor.py','--out',str(out),'--compare-reference']
 if stop:cmd+=['--stop-after',str(stop)]
 with (root/(name+'.log')).open('w') as log:
  p=subprocess.Popen(cmd,cwd=pin,env=env,stdout=log,stderr=subprocess.STDOUT)
  peak=0;guard=None
  while p.poll() is None:
   try:
    rss=next(int(l.split()[1])*1024 for l in Path(f'/proc/{p.pid}/status').read_text().splitlines() if l.startswith('VmRSS:'));peak=max(peak,rss)
    if rss>96*2**30:guard='RSS resource guard';p.terminate()
   except (FileNotFoundError,StopIteration):pass
   (root/'progress.json').write_text(json.dumps({'active':name,'pid':p.pid,'source_commit':sha,'peakRSS_bytes':peak,'finished':results})+'\n')
   time.sleep(2)
  rc=p.wait()
 result={'job':name,'pid':p.pid,'exit_code':rc,'peakRSS_bytes':peak,'guard':guard,'output':str(out/'execution.json')};results.append(result)
 if rc:break
(root/'queue-result.json').write_text(json.dumps({'admission':admission,'jobs':results,'verdict':'PASS' if len(results)==2 and all(r['exit_code']==0 for r in results) else 'FAIL'},indent=2)+'\n')
print(json.dumps(results),flush=True)
