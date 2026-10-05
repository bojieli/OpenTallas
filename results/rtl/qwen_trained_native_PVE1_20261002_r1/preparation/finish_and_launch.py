"""One-shot actual terminal collector, qualification and authorized native launch."""
import json,subprocess,time,sys,hashlib,os
from pathlib import Path
D=Path('/tmp/h1-qwen-trained-native-execution-20261002');A=Path('/home/ubuntu/OpenTallas-hbm-r6-archive');old=Path('/tmp/h1-qwen-pve1-conversion-r2-20261002');host='ot-pve1';job='/home/ubuntu/otjobs/qwen-trained-byte-conversion-pve1-20261002-r2';unit='hbm-qwen-trained-byte-conversion-pve1-20261002-r2.service'
def ssh(cmd,**kw):return subprocess.run(['ssh',host,cmd],check=True,**kw)
try:
 while True:
  state=ssh('systemctl --user show '+unit+' --property=MainPID,ActiveState',text=True,capture_output=True).stdout
  if 'MainPID=0'in state and ('ActiveState=inactive'in state or'ActiveState=failed'in state):break
  time.sleep(20)
 # Archive raw terminal exactly, even a failure; never rerun producer.
 dest=A/'results/rtl/qwen_trained_byte_conversion_PVE1_20261002_r2/terminal';dest.mkdir()
 for file in ['terminal.json','run_start.json','actual_producer.log','memory.jsonl','qualified_page_copy-start.json','qualified_page_copy-end.json','checkpoint_production-start.json','checkpoint_production-end.json','GO.json','GO.commit','launcher.py']:
  subprocess.run(['scp',host+':'+job+'/'+file,str(dest/file)],check=True)
 for file in ['manifest.json','producer_identity.json']:
  subprocess.run(['scp',host+':'+job+'/images/'+file,str(dest/file)],check=True)
 (dest/'journal.txt').write_text(ssh('journalctl --user -u '+unit+' --no-pager -o short-iso-precise',text=True,capture_output=True).stdout)
 (dest/'systemd.txt').write_text(ssh('systemctl --user show '+unit+' --property=MainPID,ActiveState,Result,ExecMainStatus,MemoryPeak,MemoryMax,MemorySwapMax,RuntimeMaxUSec,LimitFSIZE,LimitAS',text=True,capture_output=True).stdout)
 (dest/'source_root.txt').write_text(ssh('git -C /home/ubuntu/OpenTallas-qwen-trained-conversion-pve1-r3 rev-parse HEAD; git -C /home/ubuntu/OpenTallas-qwen-trained-conversion-pve1-r3 status --porcelain',text=True,capture_output=True).stdout)
 hashes={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.iterdir()if p.is_file()};(dest/'raw_sha256.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
 t=json.loads((dest/'terminal.json').read_text());assert t['verdict']=='PASS_COMPLETE_CHECKPOINT_BYTE_PRODUCTION_ONLY',t
 # All pages are independently hashed without mutating producer outputs.
 with(D/'qualified_images.json').open('xb')as f:ssh('/home/ubuntu/.local/qwen-trained-provider-pve1/bin/python -',input=(D/'qualify_images.py').read_text(),text=True,stdout=f)
 (dest/'qualified_images.json').write_bytes((D/'qualified_images.json').read_bytes())
 subprocess.run(['git','add','--',str(dest.relative_to(A))],cwd=A,check=True);subprocess.run(['git','commit','-m','Archive actual complete Qwen checkpoint production r2 and independently qualify every page'],cwd=A,check=True)
 print('CONVERSION_TERMINAL_ARCHIVED',subprocess.check_output(['git','rev-parse','HEAD'],cwd=A,text=True).strip(),flush=True)
 while not(old/'lease_released.json').exists():time.sleep(5)
 log=(D/'lease_keeper.log').open('xb');p=subprocess.Popen([sys.executable,str(D/'lease_keeper.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while not(D/'lease.json').exists():
  if p.poll()is not None:raise RuntimeError('Fresh native fleet lease denied; preserve complete conversion, no automaticretry')
  time.sleep(1)
 subprocess.run([sys.executable,str(D/'launch.py')],check=True)
 state=ssh('systemctl --user show hbm-qwen-trained-native-token-pve1-20261002-r1.service --property=MainPID,ActiveState,MemoryMax,MemorySwapMax,RuntimeMaxUSec,LimitFSIZE,LimitAS',text=True,capture_output=True).stdout
 (D/'actual_service.txt').write_text(state);print(state,flush=True)
except BaseException as e:
 (D/'coordinator_failure.json').write_text(json.dumps(dict(error=repr(e),time=time.time(),no_automatic_retry=True,preserved_producer_outputs=True))+'\n');raise
