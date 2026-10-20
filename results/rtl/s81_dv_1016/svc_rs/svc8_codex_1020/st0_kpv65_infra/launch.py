import concurrent.futures,hashlib,json,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/s81-svc5-1019/svc6/codex_st0_kpv')
S=R.parents[1]
W=R.parent/'src_solp0'
O=R/'kpv65';O.mkdir(exist_ok=True)
assert not (O/'summary.json').exists(), 'Do not overwrite completed diagnostic'
records=[]
for line in (R/'reused_inputs.sha256').read_text().splitlines():
 digest,name=line.split('  ',1);p=Path(name);actual=hashlib.sha256(p.read_bytes()).hexdigest()
 assert actual==digest, (str(p),actual,digest)
 records.append({'path':str(p),'sha256':actual,'bytes':p.stat().st_size})
(O/'verified_reused_inputs.json').write_text(json.dumps(records,indent=2)+'\n')
a=json.loads((R/'original_top_command.json').read_text())
assert '-GST=0' in a and '-DOT_SVC_ATTW_LP' in a and '-DOT_SVC_ATT_PINREG' in a
assert not any(v.startswith('-GKPV=') for v in a)
a[a.index('-Mdir')+1]=str(O/'obj');a[a.index('-j')+1]='8';a.append('-GKPV=65')
VL='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
(O/'command.json').write_text(json.dumps([VL,*a],indent=2)+'\n')
with (O/'build.log').open('w') as f:r=subprocess.run([VL,*a],cwd=W,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0, r.returncode
print('SVC8_ST0_KPV65_BUILT source_hashes_verified',len(records),flush=True)
def run(seed):
 p=O/f'tail46_s{seed}.log'
 with p.open('w') as f:r=subprocess.run([str(O/'obj/Vtb_dsdv_svc_rs'),f'+dir={S}/vec/tail46',f'+seed={seed}'],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 lines=[x for x in p.read_text().splitlines() if x.startswith(('SVCRS die=','SVCRS_SO '))]
 row={'kpv':65,'seed':seed,'rc':r.returncode,'verdicts':lines}
 print(json.dumps(row),flush=True)
 assert len(lines)==2
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,[1,2]))
(O/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print('SVC8_ST0_KPV65_COMPLETE',flush=True)
