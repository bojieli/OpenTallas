#!/usr/bin/env python3
"""Exact one-line W1 source-list successor; actual lint and finite RTL stage."""
import argparse,hashlib,json,os,resource,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD='rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv'
NEW='rtl/model_ready_hbm_w1_euclid_20261003/ot_hbm_causal_command_provider.sv'
BENCH='rtl/test/model_ready_hbm_w1_euclid_20261003/tb_W1_provider.sv'
TOOL=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
RECORD=ROOT/'results/uarch/W1_euclid_provider_hygiene_20261003'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sources():
 return ['rtl/model_ready_hbm_r14/'+n for n in ['ot_hbm_r14_pkg.sv','ot_hbm_r14_pc.sv','ot_hbm_r14_tag_owner.sv']]+[NEW]+[f'physical/asap7_memory_macros/{n}/{n}.v' for n in ['ot_sram_1r1w_64x512_m1_r2c2','ot_sram_1r1w_128x256_m1_r2c2']]
def identity():
 old=(ROOT/OLD).read_bytes();new=(ROOT/NEW).read_bytes()
 model=json.loads((RECORD/'pre-edit-model-identity-r1.json').read_text())
 if sha(ROOT/OLD)!=model['original_provider_sha256']:raise ValueError('pinned original changed')
 if sha(ROOT/'tools/uarch_model.py')!=model['unified_model_sha256']:raise ValueError('model root changed')
 if old.count(b'assign commit_ready=0;')!=1 or new!=old.replace(b'assign commit_ready=0;',b'assign commit_r=0;'):raise ValueError('exact one-line successor only')
 marker=b' end else begin:on';a=old[old.index(marker):];b=new[new.index(marker):]
 if a!=b:raise ValueError('entire enabled branch byte identity')
 return {'original_sha256':sha(ROOT/OLD),'successor_sha256':sha(ROOT/NEW),'enabled_branch_sha256':hashlib.sha256(a).hexdigest(),'normalized_entire_source_identity':True,'enabled_branch_byte_identical':True,'model_delta_cycles_ports_replicas_enabled_area':0}
def run(out):
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean frozen worktree required')
 out.mkdir(exist_ok=False);src=sources();pins={p:sha(ROOT/p) for p in src+[OLD,BENCH,'rtl/test/model_ready_hbm_r14/ot_hbm_r14_backing_fixture.sv','tools/uarch_model.py','tools/W1_euclid_provider_hygiene_gate.py']}
 limits={n:resource.getrlimit(getattr(resource,'RLIMIT_'+n)) for n in ('CPU','AS','FSIZE')}
 if any(hard!=resource.RLIM_INFINITY for soft,hard in limits.values()):raise ValueError('unlimited CPU/AS/FSIZE hard limits required')
 for n in ('CPU','AS','FSIZE'):resource.setrlimit(getattr(resource,'RLIMIT_'+n),(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 r={'status':'STARTED','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'identity':identity(),'source_pins':pins,'tool_sha256':sha(TOOL),'tool_bin_sha256':sha(TOOL.with_name('verilator_bin')),'caps':None,'headroom':{'MemAvailable_line':next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')),'disk_free_B':shutil.disk_usage(out).free,'CPU_affinity':sorted(os.sched_getaffinity(0))},'jobs':[],'no_PR_or_calendar_adoption':True}
 def execute(argv,name):
  start=time.time()
  with (out/(name+'.log')).open('xb') as f:p=subprocess.run(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['jobs'].append({'name':name,'argv':argv,'returncode':p.returncode,'wall_s':time.time()-start,'log_sha256':sha(out/(name+'.log'))})
  if p.returncode:raise ValueError('actual tool failure '+name)
  return (out/(name+'.log')).read_text()
 try:
  for enable in (0,1):
   log=execute([str(TOOL),'--lint-only','--timing','--Wall','-Wno-fatal','-Werror-IMPLICIT','-Werror-UNDRIVEN','--top-module','ot_hbm_causal_command_provider',f'-GENABLE={enable}']+[str(ROOT/p) for p in src],f'ENABLE{enable}-lint')
   if '%Warning-IMPLICIT:' in log or '%Warning-UNDRIVEN:' in log:raise ValueError('no implicit or undriven warnings permitted')
  execute([str(TOOL),'--binary','--timing','--assert','-j','1','--threads','1','-Wno-fatal','-Werror-IMPLICIT','-Werror-UNDRIVEN','--top-module','tb_W1_provider','--Mdir',str(out/'obj')]+[str(ROOT/p) for p in src+['rtl/test/model_ready_hbm_r14/ot_hbm_r14_backing_fixture.sv',BENCH]],'stage-build')
  binary=out/'obj/Vtb_W1_provider';r['binary_sha256']=sha(binary)
  log=execute([str(binary)],'stage-run')
  if 'PASS_W1_TWO_TRANSACTIONS' not in log:raise ValueError('exact finite handshake verdict absent')
  if any(sha(ROOT/p)!=h for p,h in pins.items()):raise ValueError('post-run source changed')
  r['status']='PASS_W1_DEFAULT_OFF_LINT_AND_ENABLED_IDENTITY_FINITE_STAGE'
 except Exception as e:r['status']='FAIL_W1_SUCCESSOR_GATE';r['error']=str(e)
 with (out/'terminal.json').open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 return 0 if r['status'].startswith('PASS_') else 1
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.out.resolve()))
