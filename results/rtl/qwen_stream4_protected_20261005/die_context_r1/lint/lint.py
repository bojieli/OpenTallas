import json,os,subprocess,time,shutil
from pathlib import Path
p=Path('/srv/opentallas-scratch2/jobs/codex-qwen-interface-context-66cac15e3')
os.chdir(p)
def capacity(label):
 def cpu():
  a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(a),a[3]+a[4]
 a=cpu();time.sleep(2);b=cpu()
 idle=(b[1]-a[1])/(b[0]-a[0])*os.cpu_count()
 mem=dict((s.split(':')[0],int(s.split()[1])) for s in Path('/proc/meminfo').read_text().splitlines())['MemAvailable']/2**20
 disk=shutil.disk_usage(p).free/2**30;load=os.getloadavg()[0]
 x=dict(label=label,UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),load=load,idle_cpus=idle,MemAvailable_GiB=mem,disk_free_GiB=disk,need_GiB=16,need_CPUs=2,need_disk_GiB=2,fit=load<128 and idle>=2 and mem>=116 and disk>=2)
 with (p/'capacity.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
 return x['fit']
if not capacity('pre_guard'):raise SystemExit(75)
if os.environ.get('GUARDED')!='1':
 e=dict(os.environ,GUARDED='1')
 os.execve('/srv/opentallas-scratch/admit.sh',['/srv/opentallas-scratch/admit.sh','16','--','python3',str(p/'lint.py')],e)
if not capacity('actual_exec'):raise SystemExit(75)
s=p/'src';base=['verilator','--lint-only','--top-module','ot_qwen_s4_interface_context','-DSYNTHESIS','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-y',str(s/'rtl/hdc/kv'),'-y',str(s/'rtl/lib'),'-y',str(s/'rtl/model_ready_hbm_r14'),str(s/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'),str(s/'rtl/hdc/kv/ot_qwen_s4_interface_context.sv')]
res=[]
for protected in [0,1]:
 cmd=base+['-GPROTECTED='+str(protected)]
 (p/('command_'+str(protected)+'.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 with (p/('lint_'+str(protected)+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 (p/('lint_'+str(protected)+'.exit')).write_text(str(rc)+'\n');res.append(rc)
 if rc:break
(p/'supervisor.exit').write_text(str(max(res))+'\n')
