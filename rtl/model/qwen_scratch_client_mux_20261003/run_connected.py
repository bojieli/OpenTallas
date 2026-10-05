"""ONE actual router + owned client + unchanged SRAM service measurement."""
import json,hashlib,subprocess,sys,os,resource,time,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
W4='results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/'
SOURCES=['rtl/model/qwen_scratch_client_mux_20261003/connected_tb.sv','rtl/model/qwen_scratch_client_mux_20261003/ot_gpu_qwen_scratch_client_mux.sv','rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_shared_router.sv',W4+'ot_gpu_scratch_service.sv',W4+'ot_sram_1r1w_1024x256_m2_r2c2.v','rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv']
def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 for limit in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT):raise RuntimeError('source dirty')
 pins=lambda:{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();before=pins()
 launch=dict(source_HEAD=head,source_sha256=before,pid=os.getpid(),started=time.time(),meminfo=Path('/proc/meminfo').read_text(),disk_free=shutil.disk_usage(out).free,limits={str(l):list(resource.getrlimit(l)) for l in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE)},scope='one actually connected router/ownedclient/64KiB SRAM pair; caller ownership inputs are fixtures; not fullfactory/token/physical')
 (out/'launch.json').write_text(json.dumps(launch,indent=2)+'\n');cases=[]
 for name,enable in [('enabled',1),('defaultoff',0)]:
  cmd=['iverilog','-g2012','-s','scratch_connected_tb','-P',f'scratch_connected_tb.ENABLE_CLIENT={enable}','-o',str(out/(name+'.vvp'))]+[str(ROOT/p) for p in SOURCES]
  with (out/(name+'.compile.log')).open('w') as f:ce=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  rc=None
  if ce==0:
   with (out/(name+'.run.log')).open('w') as f:rc=subprocess.call(['vvp',str(out/(name+'.vvp'))],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  expected='PASS_CONNECTED_ROUTER_OWNED_CLIENT_ACTUAL_64KIB' if enable else 'PASS_DEFAULTOFF_ACTUAL_ROUTER_TWO_SRAMS'
  ok=ce==0 and rc==0 and expected in (out/(name+'.run.log')).read_text()
  cases.append(dict(name=name,compile_exit=ce,run_exit=rc,pass_=ok,command=cmd))
  if not ok:break
 terminal=dict(verdict='PASS_CONNECTED_SCRATCH' if len(cases)==2 and all(c['pass_'] for c in cases) and before==pins() else 'FAIL',source_HEAD=head,source_sha256=before,post_source_sha256=pins(),cases=cases,ended=time.time(),wholefactory=False,token=False,SSFF=False)
 (out/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n');return int(terminal['verdict']=='FAIL')
if __name__=='__main__':sys.exit(main(sys.argv[1]))
