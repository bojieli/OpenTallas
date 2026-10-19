from pathlib import Path
import subprocess,json,concurrent.futures
out=Path(__file__).parent/'evidence'
code=r'''
from pathlib import Path
import json,hashlib,subprocess,datetime
base=Path('/srv/opentallas-scratch/claude/ref_gate')
names=['hnx_fused_lane_1019-20261019-113956','hnx_fused_lane_t648_1019-20261019-113956','hnx_hcq_hub_safe_1019-20261019-120816','hnx_hcq_hub_safe_b389_1019-20261019-120816','hnx_idxq_kb2-20261019-114107','hnx_vms_bank_safe2-20261019-080952','hnx_rp3a3_spvm_safe_nf-20261019-115212']
a={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':[]}
for n in names:
 d=base/n
 if not d.is_dir():continue
 r={'path':str(d),'logs':[]}; snap=base/(n+'.source_snapshot.json')
 if snap.exists():r['snapshot_sha256']=hashlib.sha256(snap.read_bytes()).hexdigest();r['source_snapshot']=json.loads(snap.read_text())
 for f in ['cts.log','grt.log','synth.log']:
  p=d/f
  if p.exists():
   b=p.read_bytes();r['logs'].append({'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mtime_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'tail':b[-3000:].decode(errors='replace')})
 a['runs'].append(r)
a['processes']=subprocess.getoutput("ps -eo pid,etime,pcpu,rss,args | grep -E 'openroad|yosys|gate_cts_hnx|gate_grt_hnx' | grep -v grep")
print(json.dumps(a,indent=2))
'''
def run(host):
 p=subprocess.run(['ssh','-o','BatchMode=yes',host,'python3','-'],input=code,text=True,capture_output=True,timeout=80)
 (out/(host+'_actual.json')).write_text(p.stdout if p.returncode==0 else json.dumps({'error':p.stderr,'rc':p.returncode}))
 return host,p.returncode,len(p.stdout)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:
 print(list(e.map(run,['ot-epyc7','ot-agidock128','ot-epyc4'])))
