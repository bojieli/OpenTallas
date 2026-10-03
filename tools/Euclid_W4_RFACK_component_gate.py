#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,resource,subprocess,os
from Euclid_W4_RFACK_component_price import price
from Euclid_W4_RFACK_identity_contract import RECORD
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sources():
    r=RECORD/'rtl-source-inputs-r4'
    paths=['rtl/gpu_w4_euclid_20261003/ot_gpu_rf_service.sv','rtl/gpu_w4_euclid_20261003/ot_gpu_full_sm_service.sv']
    pin=json.loads((r/'source-pins.json').read_text())
    for p,h in pin.items():
        if hashlib.sha256((r/p).read_bytes()).hexdigest()!=h:raise ValueError('actual source pin '+p)
    rest=[str(r/p) for p in pin if p!='rtl/test/full_sm_service/tb_full_service_exact.sv']
    return [str(ROOT/p) for p in paths]+rest
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();out=pathlib.Path(args.out);out.mkdir(exist_ok=False)
 for limit in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):
  soft,hard=resource.getrlimit(limit)
  if hard!=resource.RLIM_INFINITY:raise ValueError('inherited hard cap')
  resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('clean source freeze required')
 m=price();assert m['latency']['added_local_RF_edges_vs_existing_ACK']==1
 freeze=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 files=sources();test=ROOT/'rtl/test/W4_euclid_20261003';jobs=[]
 for top,extra in [('ot_gpu_rf_service',['-GACK_ID=0']),('ot_gpu_rf_service',['-GACK_ID=1']),('ot_gpu_full_sm_service',['-GENABLE=1','-GACK_ID=0']),('ot_gpu_full_sm_service',['-GENABLE=1','-GACK_ID=1'])]:
  jobs.append((top+'-lint-'+''.join(extra),['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--lint-only','--timing','-Wno-fatal','-Werror-IMPLICIT','-Werror-UNDRIVEN','--top-module',top,*extra,*files],0))
 for name,top in [('tb_W4_RFACK','tb_W4_RFACK'),('tb_W4_full_service','tb_W4_full_service'),('tb_W4_default_original','tb_full_service_exact'),('tb_W4_valid_code_mismatch','tb_W4_valid_code_mismatch')]:
  jobs.append((name+'-compile',['iverilog','-g2012','-s',top,'-o',str(out/name),*files,str(test/(name+'.sv'))],0))
  jobs.append((name+'-run',['vvp',str(out/name)],0))
  if name=='tb_W4_valid_code_mismatch':jobs.append((name+'-wrongslot',['vvp',str(out/name),'+WRONG_SLOT'],0))
 toolpaths=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator_bin','/usr/bin/iverilog','/usr/bin/vvp']
 stat=os.statvfs(out)
 receipt={'tool_pins':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in toolpaths},'sourcefreeze':freeze,'supervisor_PID':os.getpid(),'exclusive_out':str(out),'status':'LIVE','meminfo':pathlib.Path('/proc/meminfo').read_text(),'disk_available_bytes':stat.f_bavail*stat.f_frsize,'limits_unlimited_CPU_AS_FSIZE':True,'source_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files},'jobs':[],'scope':'actual source-selected conditional W4 component; no upstream connector/CDC/physical/rate qualification'}
 (out/'launch.json').write_text(json.dumps(receipt,indent=2)+'\n')
 for name,argv,expected in jobs:
  with open(out/(name+'.log'),'w') as f:
   child=subprocess.Popen(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
   (out/'live-child.json').write_text(json.dumps({'supervisor_PID':os.getpid(),'child_PID':child.pid,'name':name,'argv':argv},indent=2)+'\n')
   rc=child.wait() # no timeouts, no per-process/costly caps
  b=(out/(name+'.log')).read_bytes();receipt['jobs'].append(dict(name=name,argv=argv,rc=rc,log_sha256=hashlib.sha256(b).hexdigest()))
  print(name,rc,flush=True)
  if rc!=expected:
   receipt['status']='FAIL_'+name;break
 else:receipt['status']='PASS_W4_SOURCE_SELECTED_COMPONENT_ONLY_CONNECTOR_UNQUALIFIED'
 receipt['post_source_sha256']={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files}
 assert receipt['post_source_sha256']==receipt['source_sha256']
 (out/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(receipt['status'],flush=True)
