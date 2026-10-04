#!/usr/bin/env python3
"""SU-only native archive builder. Invoke through EPYC atomic admit; no runtime."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 model=json.loads((ROOT/'results/uarch/dsrom_sun256_native_prefix_20261004/model.json').read_text())
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise RuntimeError('source must be pinned clean')
 for path,sha in model['source_sha256'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise RuntimeError('source mismatch '+path)
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 obj=a.out/'obj';params=model['parameters']
 cmd=[str(tool),'--cc','--top-module','ot_hdc_v41x_su_adapt','--prefix','VDsromSu256','--Mdir',str(obj),'--output-split','20000','--output-split-cfuncs','200','-Wno-fatal','-CFLAGS','-O0']+[f'-G{k}={v}' for k,v in params.items()]+[str(ROOT/x) for x in model['rtl_closure']]
 receipt={'scope':'native SUN256 SU leaf archive only; no runtime/HE/corearray/provider or clock admission','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'supervisor_pid':os.getpid(),'verilator_sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'verilator_version':subprocess.check_output([str(tool),'--version'],text=True).strip(),'parameters':params,'limits':'no running time/memory/AS/file caps; EPYC atomic admission reservation32GiB/sharedreserve150GiB','commands':[cmd],'stages':[]}
 t=time.monotonic();rc=1
 try:
  with (a.out/'frontend.log').open('w') as log:
   proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT);receipt['frontend_pid']=proc.pid;(a.out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n');rc=proc.wait()
  receipt['stages'].append({'name':'frontend','exit':rc,'wall_seconds':time.monotonic()-t})
  if rc==0:
   cmd2=['make','-C',str(obj),'-f','VDsromSu256.mk','-j16','OPT_FAST=-O0','OPT_SLOW=-O0','VDsromSu256__ALL.a'];receipt['commands'].append(cmd2)
   t2=time.monotonic()
   with (a.out/'compile.log').open('w') as log:
    proc=subprocess.Popen(cmd2,stdout=log,stderr=subprocess.STDOUT);receipt['compile_make_pid']=proc.pid;(a.out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n');rc=proc.wait()
   receipt['stages'].append({'name':'archive','exit':rc,'wall_seconds':time.monotonic()-t2})
   if rc==0:
    files=[obj/'VDsromSu256__ALL.a',obj/'VDsromSu256.h',obj/'VDsromSu256__verFiles.dat',obj/'VDsromSu256.mk',obj/'VDsromSu256_classes.mk']
    receipt['artifacts']={str(p.relative_to(a.out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
  receipt['verdict']='PASS_NATIVE_SU_ARCHIVE_ONLY' if rc==0 else 'FAIL_PRESERVED_NO_RETRY'
 finally:
  receipt['terminal_exit']=rc;(a.out/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return rc
if __name__=='__main__':raise SystemExit(main())
