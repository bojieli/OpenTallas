#!/usr/bin/env python3
"""Minimum changed-source W2 gateway/caller/sector gates, no numerical engine rebuild."""
import argparse,hashlib,json,subprocess,tarfile,time
from pathlib import Path
from hbm_w2_parent_context import SOURCES
ROOT=Path(__file__).resolve().parents[1]
TB='rtl/test/hbm_accel/integrated_20261005/'
GOLD='results/rtl/hubble_native_connected_w2_20261005/runtime_r1_PASS/case/expected_rows.hex'
FIXTURE='results/rtl/hbm_w2_sector_adapter_20261005/comb_default_r1_PASS/fixture.tar.gz'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out):
 out.mkdir(exist_ok=False,parents=True)
 pins={p:sha(ROOT/p) for p in SOURCES+[TB+'tb_hbm_integrated_w2_publication_nash.sv',TB+'tb_hbm_w2_protected_caller.sv',TB+'tb_hbm_w2_protected_sector_min.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',GOLD,FIXTURE]}
 (out/'source.json').write_text(json.dumps(pins,indent=2)+'\n')
 (out/'private_alloc.svh').write_text("localparam integer RAM_BYTES=8192;\nlocalparam [31:0] BASE_A=32'd4096,LIMIT_A=32'd4160,BASE_B=32'd4224,LIMIT_B=32'd4288;\n")
 # Read only four named flat emitted-source/oracle files, no alternate image.
 with tarfile.open(ROOT/FIXTURE) as tar:
  for name in ['memory_addresses.hex','memory.hex','maps.hex','expected.hex']:
   (out/name).write_bytes(tar.extractfile('fixture_subset/'+name).read())
 stages=[]
 def step(name,cmd,expected=0,marker=None):
  start=time.monotonic()
  with (out/(name+'.log')).open('w') as log:
   p=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  detail=dict(name=name,command=cmd,returncode=p.returncode,elapsed_s=time.monotonic()-start)
  stages.append(detail);(out/(name+'.exit')).write_text(str(p.returncode)+'\n')
  ok=(p.returncode==expected if expected==0 else p.returncode!=0)
  if marker:ok=ok and marker in (out/(name+'.log')).read_text()
  if not ok:raise RuntimeError('actual gate failed: '+name)
 try:
  names=[('caller','tb_hbm_w2_protected_caller'),('sector','tb_hbm_w2_protected_sector_min'),('publication','tb_hbm_integrated_w2_publication_nash')]
  for kind,top in names:
   cmd=['iverilog','-g2012','-I'+str(out),'-s',top,'-o',str(out/(kind+'.vvp'))]
   if kind=='publication':cmd += ['-P'+top+'.PROTECTED_TRANSACTION_PIPELINE=1','-P'+top+'.PROTECTED_PARENT_BOUNDARY=1']
   step(kind+'_compile',cmd+[str(ROOT/p) for p in SOURCES+(['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv'] if kind=='publication' else [])]+[str(ROOT/(TB+top+'.sv'))])
  caller=['vvp',str(out/'caller.vvp'),'+GOLD='+str(ROOT/GOLD)]
  for name,flag,marker in [('clean',None,'PASS_PROTECTED_CALLER_CANONICAL'),('CE','CALLER_CE','PASS_CALLER_CE_REPAIR'),('DUE','CALLER_DUE','PASS_CALLER_DUE_ACCEPTED_IDENTITY_RETAINED')]:
   step('caller_'+name,caller+(['+'+flag] if flag else []),marker=marker)
  sector=['vvp',str(out/'sector.vvp'),'+DIR='+str(out),'+NWORDS=3268','+NCASES=2','+OUT_BASE=71bd800','+OUT_LIMIT=71bd880']
  for name,flag,marker in [('clean',None,'PASS'),('CE','SECTOR_CE','PASS_SECTOR_CE_REPAIR'),('DUE','SECTOR_DUE','PASS_SECTOR_DUE_ACCEPTED_OWNER_DEBT_RETAINED')]:
   step('sector_'+name,sector+(['+'+flag] if flag else []),marker=marker)
  publication=['vvp',str(out/'publication.vvp')]
  for name,flag,rc,marker in [('clean',None,0,'PASS W2_PUBLICATION_SHARED_CPEND_CPL'),('gateway_CE','CORRECT_GATEWAY_CE',0,'PASS_GATEWAY_CE_REPAIR'),('gateway_DUE','CORRUPT_GATEWAY_CONTROL',1,'PASS_GATEWAY_DUE_ACCEPTED_DEBT_RETAINED'),('CDC_memory_CE','CORRECT_CDC_MEMORY_CE',0,'PASS_CDC_MEMORY_CE_REPAIR'),('CDC_memory_DUE','CORRUPT_CDC_MEMORY_DUE',1,'PASS_CDC_MEMORY_DUE_ACCEPTED_DEBT_RETAINED')]:
   step('publication_'+name,publication+(['+'+flag] if flag else []),expected=rc,marker=marker)
  verdict='PASS_MINIMUM_PROTECTED_PARENT_COMPONENTS'
 except Exception as e:
  verdict='FAIL_PRESERVED';error=str(e)
 else:error=None
 stable=all(sha(ROOT/p)==h for p,h in pins.items())
 if not stable:verdict='FAIL_SOURCE_CHANGED'
 result=dict(verdict=verdict,error=error,source_stable=stable,stages=stages,
  scope='Existing four-row32word literal publication/shared-owner/CP-END-CPL gate plus canonical actual caller four rows and two actual source sector frames; protection/transport only. No native arithmetic replay or full-token claim.',
  source_default_off=True,new_extracted_context_warm_qualified=False,physical_qualified=False)
 if verdict.startswith('PASS'):
  import re
  log=(out/'publication_clean.log').read_text()
  result['release_cycle']=int(re.search(r'ACTUAL_SHARED_RELEASE cycle=(\d+)',log)[1])
  result['fourrow_direct_component_release']=196
  result['observed_delta_including_asynchronous_context']=result['release_cycle']-196
  result['delta_is_not_gateway_only']=True
 result['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.suffix!='.vvp'}
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 return 0 if verdict.startswith('PASS') else 1
def run_joined(out):
 """Run only the minimum joined warm mechanism, without component replays."""
 out.mkdir(exist_ok=False,parents=True)
 top='tb_hbm_w2_protected_parent_min'
 paths=SOURCES+[TB+top+'.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',GOLD,FIXTURE]
 pins={p:sha(ROOT/p) for p in paths}
 (out/'source.json').write_text(json.dumps(pins,indent=2)+'\n')
 with tarfile.open(ROOT/FIXTURE) as tar:
  for name in ['memory_addresses.hex','memory.hex','maps.hex','expected.hex']:
   (out/name).write_bytes(tar.extractfile('fixture_subset/'+name).read())
 # CP and testbench are explicit; never pull in numerical arithmetic engines.
 compile_cmd=['iverilog','-g2012','-s',top,'-o',str(out/'parent.vvp')]+[str(ROOT/p) for p in SOURCES+[TB+top+'.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv']]
 commands=[('compile',compile_cmd),('runtime',['vvp',str(out/'parent.vvp'),'+DIR='+str(out),'+GOLD='+str(ROOT/GOLD)])]
 result=dict(verdict='FAIL_PRESERVED',commands=commands,physical_qualified=False,full_native_R2_replayed=False)
 for name,cmd in commands:
  with (out/(name+'.log')).open('w') as log:
   rc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
  (out/(name+'.exit')).write_text(str(rc)+'\n');result[name+'_exit']=rc
  if rc:break
 else:
  if 'PASS_PROTECTED_PARENT_WARM' in (out/'runtime.log').read_text():result['verdict']='PASS_MINIMUM_CONNECTED_PROTECTED_PARENT_WARM'
 result['source_stable']=all(sha(ROOT/p)==h for p,h in pins.items())
 if not result['source_stable']:result['verdict']='FAIL_SOURCE_CHANGED'
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['verdict'].startswith('PASS') else 1
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('output',type=Path);a.add_argument('--joined-only',action='store_true');args=a.parse_args();raise SystemExit((run_joined if args.joined_only else run)(args.output.resolve()))
