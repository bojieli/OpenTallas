#!/usr/bin/env python3
"""One actual changed384/K6 gate; no old gate replay or local build fallback."""
import argparse,json,resource,subprocess,sys
from pathlib import Path
import hbm_router_pipeline_gate_20261006 as B
ROOT=Path(__file__).resolve().parents[1]
P='physical/hbm_die_abstracts_20261006/compute/'
FILES=[P+'router_pipeline_r1/pinned/ot_gpu_router_topk.sv',P+'router_pipeline_r1/pinned/ot_gpu_router_topk_f.sv',P+'router_pipeline_r2/ot_hbm_router_topk_successor.sv',P+'router_pipeline_r2/tb_router_successor.sv']
MODEL='results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r2/before_rtl.json'
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--admitted',action='store_true');q=a.parse_args()
 if not Path('/srv/opentallas-scratch/admit.sh').is_file():a.error('remote unchanged admission guard required')
 out=q.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'gate.json').exists() or (out/'compile.log').exists():a.error('retainedattempt exists; no replay/overwrite')
 if not B.capacity(out,'post_admission' if q.admitted else 'pre_admission')['cpu_fit']:return 75
 if not q.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','2','--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 r=dict(source_sha256={p:B.sha(ROOT/p) for p in FILES},model_sha256=B.sha(ROOT/MODEL),declared_ram_gib=2,workers=1,parent_qualified=False,fixtures=B.vectors(out),runs={})
 cmd=['iverilog','-g2012','-s','tb_router_successor','-o',str(out/'router.vvp'),*[str(ROOT/p) for p in FILES]]
 with (out/'compile.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 r.update(compile_returncode=rc,compile_command=cmd)
 if not rc:
  r['binary_sha256']=B.sha(out/'router.vvp')
  for name,args,marker in [('exact',[],'ROUTER_SUCCESSOR_REAL384_K6_PASS'),('negative_bank',['+NEG_BANK'],'GOLDEN_BANK_FAIL'),('negative_held_reset',['+NEG_RESET'],'HELD_RESET_GHOST')]:
   with (out/(name+'.log')).open('w') as f:rc=subprocess.call(['vvp',str(out/'router.vvp'),'+DIR='+str(out),*args],stdout=f,stderr=subprocess.STDOUT)
   log=(out/(name+'.log')).read_text();ok=(rc==0 if name=='exact' else rc!=0) and marker in log
   r['runs'][name]=dict(returncode=rc,expected_marker=marker,expected_outcome_observed=ok)
   if not ok:break
 r['peak_child_rss_KiB']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
 r['post_capacity']=B.capacity(out,'terminal')
 r['passed']=r['compile_returncode']==0 and len(r['runs'])==3 and all(x['expected_outcome_observed'] for x in r['runs'].values())
 r['status']='PASS_CHANGED_ROUTER_SUCCESSOR_MINIMUM' if r['passed'] else 'FAIL_RETAINED'
 (out/'gate.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return 0 if r['passed'] else 1
if __name__=='__main__':sys.exit(main())
