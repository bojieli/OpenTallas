"""Immutable source/input capture and lowering preflight; no simulator execution."""
import pathlib, hashlib, json, shutil, sys, os, datetime
R=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWLAYER')
W=R/'staging_replay_1019'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if len(sys.argv)>1 and sys.argv[1]=='capture':
 W.mkdir(exist_ok=False)
 (W/'original').mkdir()
 manifest={}
 for p in sorted((R/'src').rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:
   manifest[str(p.relative_to(R/'src'))]=sha(p)
 (W/'source_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
 shutil.copytree(R/'src',W/'src',ignore=shutil.ignore_patterns('__pycache__'),copy_function=shutil.copy2)
 for p in [R/'run.sh',R/'nu1.log',R/'nu4.log',*R.glob('nu*/runs/*/bench.out')]:
  q=W/'original'/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 records=[]
 for nu in [1,4]:
  p=R/f'nu{nu}/obj_n12/Vtb'; records.append(dict(nu=nu,path=str(p),sha256=sha(p),bytes=p.stat().st_size))
 (W/'executables.json').write_text(json.dumps(records,indent=2)+'\n')
 (W/'fixtures.json').write_text(json.dumps({str(p):sha(p) for p in sorted((R/'fx_qk').glob('*.npz'))},indent=2)+'\n')
 print('CAPTURE complete; original files unchanged');sys.exit()
SRC=W/'src'; sys.path.insert(0,str(SRC/'rtl/test/qwen_dv'));sys.path.insert(0,str(SRC/'tools/qwen_layerbench'))
os.environ.update(QWEN_O4_TP='8',QWEN_O4_GROUPS='3072',HDC_SU_WIDTH='64',HDC_KV_FMT='fp8',OT_GOLD_ROOT=str(SRC),PYTHONDONTWRITEBYTECODE='1')
reads=set()
def audit(event,args):
 if event=='open' and isinstance(args[0],str):
  p=pathlib.Path(args[0]);
  if p.is_file() and (p.is_relative_to(SRC) or p.is_relative_to(R/'fx_qk')):reads.add(str(p))
sys.addaudithook(audit)
import numpy as np
import dv_lower_vec_bench as B
cases=[]
for nu in [1,4]:
 for layer in [0,1]:
  for mode,suffix in [('resid','resid1'),('silu','silu'),('qk','qk')]:cases.append(dict(nu=nu,name=f'L{layer}_{suffix}',mode=mode,fixture=str(R/f'fx_qk/L{layer}_{suffix}_tp8.npz'),mutant=None))
 cases.append(dict(nu=nu,name='L0_resid2',mode='resid',fixture=str(R/'fx_qk/L0_resid2_tp8.npz'),mutant=None))
 for mode,suffix,mut in [('resid','resid1','arwin'),('silu','silu','nor'),('qk','qk','ropesign')]:cases.append(dict(nu=nu,name=f'MUT_L0_{suffix}_{mut}',mode=mode,fixture=str(R/f'fx_qk/L0_{suffix}_tp8.npz'),mutant=mut))
for c in cases:
 rng=np.random.default_rng(1); consts=B.consts_for(rng)
 with np.load(c['fixture']) as z:
  for k in ('ps1','ps2','q_norm','k_norm'):
   if k in z:consts[k]=z[k].astype(B.F)
  if 'pos' in z:consts['pos']=int(z['pos'])
 lw=B.V.lower_vec(c['mode'],c['mutant'],ages=None,consts=consts,ar_order='row')
 c.update(preflight='PASS',commands=len(lw['commands']),collisions=len(lw['collisions']))
 print('PREFLIGHT',c['nu'],c['name'],'PASS',flush=True)
(W/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
(W/'runtime_reads_preflight.json').write_text(json.dumps({p:sha(pathlib.Path(p)) for p in sorted(reads)},indent=2)+'\n')
print('ALL 20 PREFLIGHT PASS; no RTL run')
