"""One bounded directed actual-root gate, preserving logs and rejected mutant.

No timeout or resource cap. This is not fulltop elaboration or token execution.
"""
import hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent


def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 for lim in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):
  resource.setrlimit(lim,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 source=[D/'rank_boundary_tb.sv',D/'ot_gpu_qwen_rank_boundary.sv',ROOT/'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_sector_authority.sv']
 pin=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
 before=pin();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True)
 if dirty:raise RuntimeError('source tree not clean')
 launch=dict(source_HEAD=head,source_sha256=before,pid=os.getpid(),meminfo=Path('/proc/meminfo').read_text(),
  disk_free_bytes=__import__('shutil').disk_usage(out).free,cpu_affinity=sorted(os.sched_getaffinity(0)),
  limits={str(l):list(resource.getrlimit(l)) for l in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE)},
  scope='actual rank-boundary+sector-root4transactions; fixture callers, no W2/backend/CDC/token/physical',started=time.time())
 (out/'launch.json').write_text(json.dumps(launch,indent=2)+'\n')
 cases=[]
 for name,enabled,mutant in [('enabled',1,False),('defaultoff',0,False),('wrong_rank_accept_mutant',1,True)]:
  guard=source[1]
  if mutant:
   raw=guard.read_text();old='grant_live && reverse_rank==grant_identity[136]'
   if raw.count(old)!=1:raise RuntimeError('mutation target drift')
   guard=out/'wrong_rank_accept_mutant.sv';guard.write_text(raw.replace(old,'grant_live'))
  binary=out/(name+'.vvp')
  cmd=['iverilog','-g2012','-s','rank_boundary_tb','-P',f'rank_boundary_tb.TB_ENABLE={enabled}',
       '-o',str(binary),str(source[0]),str(guard),str(source[2])]
  with (out/(name+'.compile.log')).open('w') as f:
   compile_status=subprocess.call(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  if compile_status:cases.append(dict(name=name,command=cmd,compile_exit=compile_status,pass_=False));break
  with (out/(name+'.run.log')).open('w') as f:
   status=subprocess.call(['vvp',str(binary)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  log=(out/(name+'.run.log')).read_text()
  ok=(status!=0 and 'WRONG_RANK' in log) if mutant else status==0 and ('PASS_DEFAULT_OFF' if not enabled else 'PASS_RANKED_ACTUAL_ROOT') in log
  cases.append(dict(name=name,command=cmd,compile_exit=compile_status,run_exit=status,pass_=ok))
 after=pin();result=dict(verdict='PASS_DIRECTED_RANK_BOUNDARY' if len(cases)==3 and all(c['pass_'] for c in cases) and before==after else 'FAIL',
  cases=cases,source_HEAD=head,source_sha256=before,post_source_sha256=after,ended=time.time(),
  token=False,physical=False,CDC=False,W2_datapath=False,scope=launch['scope'])
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
 return 0 if result['verdict'].startswith('PASS') else 1

if __name__=='__main__':sys.exit(main(sys.argv[1]))
