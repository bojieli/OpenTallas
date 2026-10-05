#!/usr/bin/env python3
"""Exclusive detached current L0; wait existing bridge gate and resource lease, never duplicate it."""
import argparse,pathlib,json,subprocess,os,sys,time,fcntl,hashlib,shutil,re
ROOT=pathlib.Path(__file__).resolve().parents[1];QUEUE=pathlib.Path('/tmp/claude-1000/queue')
WORK=pathlib.Path('/home/ubuntu/w17-current-L0-fastpp-20261001-r4')
BRIDGE_RESULT=QUEUE/'w17jobs/w10_field_r1.json'
MODEL=ROOT/'results/rtl/w17_current_fastpp_connection_20261001/prebuild_model.json'
SNAP=pathlib.Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')
import w17_current_fastpp_die_rt_cli_v4 as DRIVER

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(name,r):p=WORK/name;p.write_text(json.dumps(r,indent=2)+'\n')
def note(state,**kw):
 r=dict(time=time.time(),pid=os.getpid(),state=state,**kw);save('state.json',r)
 with open(QUEUE/'W17.manifest','a') as f:f.write('\n# W17 currentL0 '+state+' PID'+str(os.getpid())+' '+json.dumps(kw)+'\n')
def qualified():
 if not BRIDGE_RESULT.exists():return False
 r=json.loads(BRIDGE_RESULT.read_text());assert r['status']=='pass' and r['source_stable'] and r['negative_control_rejected'] and r['golden_mismatch']==0 and r['unexpected_writes']==0
 assert all(x['rejected'] for x in r['pp_mapping_mutants']) and r['binding']['FAST']==1 and r['binding']['PP']==1 and r['binding']['FRONT_PAR']==0
 binding=json.loads((ROOT/'results/rtl/w17_current_fastpp_connection_20261001/live_bridge_source_binding.json').read_text())
 for p in binding['files']:assert r['source_sha256'][p['path']]==p['live_gate_sha256'] and sha(ROOT/p['path'])==p['current_sha256']
 return True
def measured_jobs(mem,load,cores):
 # Bound each extra compiler at 8GiB beyond pinned jobs2/80GiB host envelope.
 # Choose for NEW stage only; never resize an existing make.
 cpu_slots=max(0,int(.6*cores-load))
 ram_slots=2+max(0,int((mem-80*2**30)/(8*2**30)))
 jobs=max(2,min(8,cpu_slots,ram_slots))
 return jobs,80+max(0,jobs-2)*8
def admission():
 mem=int(re.search(r'MemAvailable:\s+(\d+)',pathlib.Path('/proc/meminfo').read_text()).group(1))*1024
 disk=shutil.disk_usage('/home').free;load=os.getloadavg()[0];cores=len(os.sched_getaffinity(0))
 jobs,floor=measured_jobs(mem,load,cores)
 return dict(mem_GiB=mem/2**30,disk_GiB=disk/2**30,load1=load,affinity=cores,compiler_jobs=jobs,memory_floor_GiB=floor,pass_admission=mem>=floor*2**30 and disk>=80*2**30 and load+jobs<=.6*cores)
def cleanpins():
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'source tree dirty'
 return {str(p.relative_to(ROOT)):sha(p) for p in DRIVER.all_sources()+[MODEL,ROOT/'tools/w17_current_fastpp_die_field.py',ROOT/'tools/v41_die_images_w17w10.py',ROOT/'tools/w17_current_fastpp_die_rt.py',ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py',ROOT/'results/rtl/w17_L0_cli_recovery_20261001/reuse.json',pathlib.Path(__file__)]}
def execute(cmd,stage,base):
 assert cleanpins()==base
 # CPU+RAM+disk preflight inside the held existing lease before EACH heavy stage.
 while True:
  assert qualified();a=admission()
  if a['pass_admission']:break
  note('WAIT_CPU_RAM_DISK_IN_LEASE',stage=stage,admission=a);time.sleep(30)
 cmd=list(cmd)
 if '--jobs' in cmd:cmd[cmd.index('--jobs')+1]=str(a['compiler_jobs'])
 note('RUN_STAGE',stage=stage,command=[str(x) for x in cmd],admission=a)
 with open(WORK/(stage+'.log'),'xb') as log:p=subprocess.run([str(x) for x in cmd],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 assert p.returncode==0,('stage failed',stage,p.returncode)
def admitted():
 owner=json.loads((WORK/'launch.json').read_text());pins=owner['source_sha256'];assert cleanpins()==pins and qualified()
 a=admission()
 if not a['pass_admission']:note('REQUEUE_RESOURCE_RACE',admission=a);return 75
 note('ADMITTED',admission=a,lease='orfs_gate slots1/2 only floor80GiB')
 # No golden current-token KV injection: preexisting context only; DUT writer owns rowpos.
 # Regenerate field ROM/stream/config for FASTPP; hardlink only immutable startup fixtures.
 receipt=json.loads((ROOT/'results/rtl/w17_L0_cli_recovery_20261001/reuse.json').read_text())
 images=pathlib.Path(receipt['images'])
 for rel,digest in receipt['image_sha256'].items():assert sha(images/rel)==digest,('image changed',rel)
 save('reused_image_pins.json',receipt)
 build=WORK/'build';build.mkdir()
 # Existing current ATT source differs from historical archive: no reuse across changed pins.
 execute([sys.executable,ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py','attn','--work',build,'--jobs','2','--fast','1','--pp','1'],'build_attention',pins)
 for rank in range(4):execute([sys.executable,ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py','build','--work',build,'--jobs','2','--only',f'die{rank}','--fast','1','--pp','1'],f'build_rank{rank}',pins)
 execute([sys.executable,ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py','build','--work',build,'--jobs','2','--only','pq,pb,retn,root','--fast','1','--pp','1'],'build_field_PHW6',pins)
 execute([sys.executable,ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py','link','--work',build,'--fast','1','--pp','1'],'link',pins)
 # Current L0 only: conservative diagnostic WD, never substitute PC advance for DONE/full VM.
 os.environ['RT_WATCHDOG']='100000';os.environ['RT_SKIP']='0'
 execute([sys.executable,ROOT/'tools/w17_current_fastpp_die_rt_cli_v4.py','run','--work',build,'--images',images,'--out',WORK/'L0_output','--threads','8','--max-cycles','400000','--fast','1','--pp','1'],'connected_L0',pins)
 result=json.loads((WORK/'L0_output/result.json').read_text());good=result['returncode']==0 and len(result['done'])==4 and all(x['actual_words']==x['words']==524288 and x['pass_exact'] for x in result['check'].values())
 save('terminal.json',dict(verdict='PASS_CURRENT_L0_VM_EXACT' if good else 'FAIL_CURRENT_L0',scope='L0 only, not all40+head',source_commit=owner['source_commit'],source_stable=cleanpins()==pins,raw_result=str(WORK/'L0_output/result.json'),next_dependency='current indexedL20; then connectedall40+head under16f2c7c21',adopt=False));note('TERMINAL',pass_L0=good)
 return 0 if good else 1
def supervise():
 WORK.mkdir(exist_ok=False)
 lock=open(QUEUE/'W17.current-L0.owner.lock','a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 pins=cleanpins();r=dict(pid=os.getpid(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source=str(ROOT),source_sha256=pins,model=str(MODEL),work=str(WORK),scope='current connected L0 full existingprofile128regions/PHW6, not full40token',prerequisite_bridge_pid=532447,prerequisite_result=str(BRIDGE_RESULT),resource_lease='existing /tmp/claude-1000/orfs_gate.sh slots1/2; floor80GiB +freshCPU/load<.6affinity anddisk80GiB insidelease',no_duplicate=True)
 save('launch.json',r);(QUEUE/'W17.current-L0-owner.json').write_text(json.dumps(r,indent=2)+'\n');note('WAIT_EXISTING_BRIDGE_PASS',source_commit=r['source_commit'])
 while not qualified():time.sleep(30)
 while True:
  cmd=['/tmp/claude-1000/orfs_gate.sh',sys.executable,__file__,'--admitted']
  note('WAIT_EXISTING_RESOURCE_LEASE');rc=subprocess.call(cmd,env=dict(os.environ,OT_GATE_SLOTS='2',OT_GATE_MIN_GB='80'),cwd=ROOT)
  if rc!=75:return rc
  time.sleep(30)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--admitted',action='store_true');args=ap.parse_args()
 try:sys.exit(admitted() if args.admitted else supervise())
 except Exception as e:
  if WORK.exists():save('failure.json',dict(verdict='FAILED_PREREQUISITE_OR_STAGE',error=repr(e),scope='currentL0 only; noPASS/adoption',time=time.time()));note('FAILED',error=repr(e))
  raise
