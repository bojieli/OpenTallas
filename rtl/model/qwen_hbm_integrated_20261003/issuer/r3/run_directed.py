"""Only the new actual coded issuer receiver, with fixture producers/allocator.

Preserves one fresh output directory per run; no wall/CPU/AS/FSIZE limits.
No fulltop compilation, canonical arithmetic, allocator or physical claim.
"""
import hashlib,json,os,resource,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];D=Path(__file__).resolve().parent
SOURCES=[D/'issuer_tb.sv',D/'ot_gpu_qwen_full_issuer_r3.sv',D.parent/'ot_gpu_qwen_full_issuer.sv',ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv']
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 for lim in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):resource.setrlimit(lim,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 pre=hashes();launch=dict(pid=os.getpid(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=pre,started=time.time(),meminfo=Path('/proc/meminfo').read_text(),disk_free=shutil.disk_usage(out).free,limits={str(l):resource.getrlimit(l) for l in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE)},scope='new issuer leaf ONLY; allocator/engine event fixtures')
 (out/'launch.json').write_text(json.dumps(launch,indent=2)+'\n');cases=[]
 for name,enabled in [('enabled',1),('defaultoff',0)]:
  cmd=['iverilog','-g2012','-s','issuer_r3_tb','-P',f'issuer_r3_tb.TB_ENABLE={enabled}','-o',str(out/(name+'.vvp')),*map(str,SOURCES)]
  with (out/(name+'.compile.log')).open('w') as f:ce=subprocess.call(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  rc=None
  if not ce:
   with (out/(name+'.run.log')).open('w') as f:rc=subprocess.call(['vvp',str(out/(name+'.vvp'))],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  log=(out/(name+'.run.log')).read_text() if rc is not None else ''
  marker='PASS_TYPED_EMPTY_INITIAL_SEPARATE_ROOT_GROUP_RECEIVER' if enabled else 'PASS_DEFAULT_OFF_TYPED_ISSUER'
  cases.append(dict(name=name,command=cmd,compile_exit=ce,run_exit=rc,pass_=rc==0 and marker in log))
  if not cases[-1]['pass_']:break
 terminal=dict(verdict='PASS_TYPED_ISSUER_RECEIVER' if len(cases)==2 and all(c['pass_'] for c in cases) and pre==hashes() else 'FAIL',source_sha256=pre,post_source_sha256=hashes(),cases=cases,elapsed_s=time.time()-launch['started'],whole1737=False,allocator_component=False,physical=False,peakRSS_measured=False)
 (out/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n');print(terminal['verdict']);return 0 if terminal['verdict'].startswith('PASS') else 1
if __name__=='__main__':sys.exit(main(sys.argv[1]))
