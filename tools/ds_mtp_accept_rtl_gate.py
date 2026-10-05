"""One clean-source functional accept component compile; fullwidth directed gate."""
import argparse,gzip,hashlib,json,os,subprocess,time
from pathlib import Path
import ds_mtp_accept_rtl_preparation as P
ROOT=P.ROOT
VERILATOR=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
def cpus():
 r={}
 for s in Path('/proc/stat').read_text().splitlines():
  a=s.split()
  if a and a[0].startswith('cpu') and a[0][3:].isdigit():
   vals=list(map(int,a[1:]));r[int(a[0][3:])]=(sum(vals),vals[3]+vals[4])
 return r

def run(out):
 # Immutable output allocation; no retries into an existing artifact directory.
 out.mkdir(parents=True,exist_ok=False)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
 if dirty:raise RuntimeError('refuse compile from dirty source tree')
 assert json.loads((P.OUT/'preparation.json').read_text())==P.model()
 before=cpus();time.sleep(.5);after=cpus();affinity=sorted(os.sched_getaffinity(0))
 idle={c:(after[c][1]-before[c][1])/max(1,after[c][0]-before[c][0]) for c in affinity}
 cpu=max(idle,key=idle.get)
 capacity={'available_RAM_kB':int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:'))),
 'free_disk_bytes':os.statvfs(out).f_bavail*os.statvfs(out).f_frsize,'measured_CPU_idle_fraction':idle[cpu],
 'selected_affinity':[cpu],'inventory':'one Icarus component compile, sequential fixture processes, no C++ or P&R','arbitrary_limits':None}
 (out/'headroom.json').write_text(json.dumps(capacity,indent=2)+'\n')
 if capacity['available_RAM_kB']<1024*1024 or capacity['free_disk_bytes']<128*1024*1024 or idle[cpu]<=0:raise RuntimeError('measured headroom insufficient for small component inventory')
 def command(cmd,name):
  t=time.monotonic()
  with (out/(name+'.log')).open('w')as f:
   p=subprocess.run(['taskset','-c',str(cpu),*map(str,cmd)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  return {'command':list(map(str,cmd)),'rc':p.returncode,'seconds':time.monotonic()-t,'log':name+'.log'}
 lint=command([VERILATOR,'--lint-only','--timing','--timescale','1ns/1ps','--top-module','tb',*P.SOURCES],'lint')
 if lint['rc']!=0:raise RuntimeError('lint failed; immutable log retained')
 binary=out/'sim.vvp'
 compile=command(['iverilog','-g2012','-s','tb','-o',binary,*P.SOURCES],'compile')
 if compile['rc']!=0:raise RuntimeError('compile failed; immutable log retained')
 cases=[]
 for c in [-1,*range(42)]:
  r=command(['vvp',binary,'+case='+str(c)],'case_'+str(c));r['case']=c
  text=(out/r['log']).read_text()
  r['pass']=r['rc']==0 and ('COMPONENT_PASS' if c==-1 else '_PASS')in text and 'GATE_FAIL'not in text
  cases.append(r)
  (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  if not r['pass']:break
 # Deliberately truncate a fullwidth token: checker must reject actual behavior,
 # not merely a compilation error. Same fixture/source oracle, separate mutant.
 original=(ROOT/P.SOURCES[2]).read_text()
 mutant=out/'mutant_truncate.sv';mutant.write_text(original.replace('n[SQ][28+:21]=tokx_tok;','n[SQ][28+:21]={5\'b0,tokx_tok[15:0]};'))
 mutant_binary=out/'mutant.vvp';mutant_sources=[str(mutant)if p==P.SOURCES[2]else p for p in P.SOURCES]
 mutant_compile=command(['iverilog','-g2012','-s','tb','-o',mutant_binary,*mutant_sources],'mutant_compile')
 mutant_run=command(['vvp',mutant_binary,'+case=-1'],'mutant_runtime')if mutant_compile['rc']==0 else None
 mutant_text=(out/'mutant_runtime.log').read_text()if mutant_run else ''
 detected=bool(mutant_run and mutant_run['rc']!=0 and 'GATE_FAIL'in mutant_text and 'literal source golden every active21-bit slot'in mutant_text)
 record={'source_commit':head,'source_hashes':P.model()['source_hashes'],'capacity':capacity,'lint':lint,'compile':compile,'cases':cases,
 'mutant_compile':mutant_compile,'mutant_run':mutant_run,'mutant_detected_by_behavior':detected,
 'pass':len(cases)==43 and all(c['pass']for c in cases)and detected,
 'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
 'scope':'component protected functional only; external truthfully fenced coldreset/origin/fences, no actual native caller/drafter/provider, no SSFF/P&R/rate',
 'extra_stage':0,'actual_MTP_acceptance_or_PHY':False}
 (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 for name in ['sim.vvp','mutant.vvp']:
  p=out/name
  if p.exists():
   with gzip.GzipFile(str(p)+'.gz','wb',mtime=0)as f:f.write(p.read_bytes())
 print(json.dumps({'pass':record['pass'],'cases':len(cases),'source_commit':head,'out':str(out)}))
 return record

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=run(a.out)
 if not r['pass']:raise SystemExit(1)
if __name__=='__main__':main()
