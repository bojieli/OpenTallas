#!/usr/bin/env python3
"""One changed-source full384/K6 gate and two real fault controls. Remote only."""
import argparse,hashlib,json,os,random,resource,struct,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1'
FILES=[BASE+'/pinned/ot_gpu_router_topk.sv',BASE+'/pinned/ot_gpu_router_topk_f.sv',BASE+'/ot_hbm_router_topk_pipeline.sv',BASE+'/tb_router_pipeline.sv']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def capacity(out,phase):
 def sample():
  v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]));return sum(v[:8]),v[3]+v[4]
 t,i=sample();time.sleep(.5);tt,ii=sample();idle=(ii-i)/(tt-t)*os.cpu_count()
 x=dict(phase=phase,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),cpus=os.cpu_count(),load=os.getloadavg()[0],idle_cpus=idle,disk_free_bytes=os.statvfs(out).f_bavail*os.statvfs(out).f_frsize)
 x['cpu_fit']=idle>=1 and x['load']<x['cpus']
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
 return x

def vectors(out):
 rng=random.Random(20261006);req=[];exp=[]
 def fp(w):return struct.unpack('<f',struct.pack('<I',w))[0]
 def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
 for c in range(64):
  if c==0:vals=[bits(float(i)) for i in range(384)]
  elif c==1:vals=[bits(1.)]*384
  elif c==2:vals=[0x80000000 if i%2 else 0 for i in range(384)]
  elif c==3:vals=[bits(-float(i)) for i in range(384)]
  else:vals=[bits(rng.randint(-65536,65536)/128.) for _ in range(384)]
  if c>3:
   for i in range(0,384,31):vals[i]=bits(1.)
  ids=sorted(sorted(range(384),key=lambda i:(-fp(vals[i]),i))[:6])
  exp.append(sum(i<<(9*j) for j,i in enumerate(ids)))
  for b in range(24):req.append(sum(v<<(32*j) for j,v in enumerate(vals[b*16:(b+1)*16])))
 (out/'input.mem').write_text(''.join(f'{v:0128x}\n' for v in req))
 (out/'expected.mem').write_text(''.join(f'{v:014x}\n' for v in exp))
 return dict(seed=20261006,vectors=64,values=24576,independent_golden='FP32 decode then descending numeric value/lowest-index tie, selected IDs ascending',input_sha256=sha(out/'input.mem'),expected_sha256=sha(out/'expected.mem'))

def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--admitted',action='store_true');q=a.parse_args()
 if not Path('/srv/opentallas-scratch/admit.sh').is_file():a.error('remote admission host required; no local gate fallback')
 out=q.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'gate.json').exists():a.error('immutable gate evidence exists; choose a new changed attempt')
 if not capacity(out,'post_admission' if q.admitted else 'pre_admission')['cpu_fit']:return 75
 if not q.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','2','--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 r=dict(source_sha256={p:sha(ROOT/p) for p in FILES},model_sha256=sha(ROOT/'results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1/before_rtl.json'),declared_ram_gib=2,workers=1,parent_qualified=False,fixtures=vectors(out),runs={})
 cmd=['iverilog','-g2012','-s','tb_router_pipeline','-o',str(out/'router.vvp'),*[str(ROOT/p) for p in FILES]]
 with (out/'compile.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 r['compile_returncode']=rc;r['compile_command']=cmd
 if not rc:
  r['binary_sha256']=sha(out/'router.vvp')
  for name,args,marker in [('exact',[],'ROUTER_PIPELINE_REAL384_K6_PASS'),('negative_bank',['+NEG_BANK'],'GOLDEN_BANK_FAIL'),('negative_held_reset',['+NEG_RESET'],'HELD_RESET_GHOST')]:
   with (out/(name+'.log')).open('w') as f:rc=subprocess.call(['vvp',str(out/'router.vvp'),'+DIR='+str(out),*args],stdout=f,stderr=subprocess.STDOUT)
   text=(out/(name+'.log')).read_text();ok=(rc==0 if name=='exact' else rc!=0) and marker in text
   r['runs'][name]=dict(returncode=rc,expected_marker=marker,expected_outcome_observed=ok)
   if not ok:break
 r['peak_child_rss_KiB']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
 r['post_capacity']=capacity(out,'terminal')
 r['passed']=r['compile_returncode']==0 and len(r['runs'])==3 and all(v['expected_outcome_observed'] for v in r['runs'].values())
 r['status']='PASS_CHANGED_ROUTER_MINIMUM_MECHANISM' if r['passed'] else 'FAIL_RETAINED'
 (out/'gate.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return 0 if r['passed'] else 1
if __name__=='__main__':sys.exit(main())
