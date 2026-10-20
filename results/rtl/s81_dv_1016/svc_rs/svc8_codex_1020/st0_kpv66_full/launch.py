import concurrent.futures,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/s81-svc5-1019/svc6/codex_st0_kpv')
S=R.parents[1];W=R.parent/'src_solp0';O=R/'kpv66_full';O.mkdir(exist_ok=True)
assert not (O/'summary.json').exists(), 'Preserve completed result'
exe=R/'obj_kpv66/Vtb_dsdv_svc_rs';vf=R/'obj_kpv66/Vtb_dsdv_svc_rs__verFiles.dat'
cmd=json.loads((R/'command_k66.json').read_text());line=next(x for x in vf.read_text().splitlines()if x.startswith('C '));actual=shlex.split(json.loads(line[2:]))
assert actual==cmd[1:]
assert all(v in actual for v in ['-GDIE=0','-GST=0','-GSRAM_MACRO=0','-GMAXCYC=40000','-GKPV=66','-DOT_SVC_ATTW_LP','-DOT_SVC_ATT_PINREG','-DOT_ATTN_HGRP_HARD'])
identity={'historical_executable_sha256':'not recorded at original sweep; no claim based on mtime','existing_binary':{},'verified_inputs':[],'missing_archives':[],'cases':['full1m','short300','skew1m'],'seeds':[1,2]}
for line in (R/'reused_inputs.sha256').read_text().splitlines():
 digest,name=line.split('  ',1);p=Path(name)
 if not p.exists():
  assert p.suffix=='.a',name
  identity['missing_archives'].append({'path':name,'original_expected_sha256':digest})
  continue
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==digest,(name,h,digest)
 identity['verified_inputs'].append({'path':name,'sha256':h,'bytes':p.stat().st_size})
sha=hashlib.sha256(exe.read_bytes()).hexdigest();shutil.copyfile(exe,O/'sim');(O/'sim').chmod(0o755)
assert hashlib.sha256((O/'sim').read_bytes()).hexdigest()==sha
identity['existing_binary']={'original_path':str(exe),'frozen_path':str(O/'sim'),'sha256':sha,'bytes':exe.stat().st_size,'generated_command_sha256':hashlib.sha256(vf.read_bytes()).hexdigest(),'matches_recorded_KPV66_command':True}
identity['vectors']=[]
for case in identity['cases']:
 for p in sorted((S/'vec'/case).rglob('*')):
  if p.is_file():identity['vectors'].append({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'source_identity.json').write_text(json.dumps(identity,indent=2)+'\n');shutil.copyfile(vf,O/vf.name);shutil.copyfile(R/'command_k66.json',O/'command_k66.json')
print('SVC8_ST0_KPV66_FROZEN',sha, 'source_command_vectors_verified',len(identity['vectors']),flush=True)
def run(case_seed):
 case,seed=case_seed;log=O/f'{case}_s{seed}.log'
 with log.open('w')as f:r=subprocess.run([str(O/'sim'),f'+dir={S}/vec/{case}',f'+seed={seed}'],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 lines=[x for x in log.read_text().splitlines()if x.startswith(('SVCRS die=','SVCRS_SO '))]
 row={'case':case,'kpv':66,'seed':seed,'rc':r.returncode,'verdicts':lines}
 print(json.dumps(row),flush=True);assert len(lines)==2,(case,seed,lines)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:rows=list(pool.map(run,[(c,s)for c in identity['cases']for s in [1,2]]))
(O/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert hashlib.sha256((O/'sim').read_bytes()).hexdigest()==sha
print('SVC8_ST0_KPV66_FULL_COMPLETE',flush=True)
