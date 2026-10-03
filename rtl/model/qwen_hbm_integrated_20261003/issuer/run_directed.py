"""Small new actual-issuer component gate. Caller events are directed fixtures.

One leaf; no canonical engine/token/physical or installed ownership claim.
"""
import hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent

def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 for r in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):resource.setrlimit(r,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 sources=[D/'issuer_tb.sv',D/'ot_gpu_qwen_full_issuer.sv',ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv']
 pins=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
 before=pins();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True):raise RuntimeError('dirty source')
 launch=dict(pid=os.getpid(),source_HEAD=head,source_sha256=before,started=time.time(),meminfo=Path('/proc/meminfo').read_text(),
  free_disk=__import__('shutil').disk_usage(out).free,scope='single actual issuer leaf, fixture callers only',
  limits={str(r):list(resource.getrlimit(r)) for r in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE)})
 (out/'launch.json').write_text(json.dumps(launch,indent=2)+'\n');cases=[]
 for name,enabled in [('enabled',1),('defaultoff',0)]:
  binary=out/(name+'.vvp');cmd=['iverilog','-g2012','-s','issuer_tb','-P',f'issuer_tb.TB_ENABLE={enabled}','-o',str(binary),*map(str,sources)]
  with (out/(name+'.compile.log')).open('w') as f:ce=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  if ce:cases.append(dict(name=name,compile_exit=ce,pass_=False));break
  with (out/(name+'.run.log')).open('w') as f:rc=subprocess.call(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  log=(out/(name+'.run.log')).read_text();ok=rc==0 and ('PASS_FULL_ISSUER_' if enabled else 'PASS_DEFAULT_OFF_FULL_ISSUER') in log
  cases.append(dict(name=name,command=cmd,compile_exit=ce,run_exit=rc,pass_=ok))
 result=dict(verdict='PASS_DIRECTED_FULL_ISSUER_LEAF' if len(cases)==2 and all(c['pass_'] for c in cases) and pins()==before else 'FAIL',cases=cases,
   source_HEAD=head,source_sha256=before,post_source_sha256=pins(),ended=time.time(),installed_bindings=False,token=False,physical=False)
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if result['verdict'].startswith('PASS') else 1
if __name__=='__main__':sys.exit(main(sys.argv[1]))
