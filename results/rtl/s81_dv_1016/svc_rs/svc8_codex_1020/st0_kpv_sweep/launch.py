import concurrent.futures,hashlib,json,shlex,subprocess
from pathlib import Path
S=Path('/srv/opentallas-scratch/claude/s81-svc5-1019')
B=S/'svc6/out_solp0/base_d0s0_pe0_ot_svc_land_sram_ot_svc_att_sram_ot_svc_att_pinreg_ot_svc_attw_lp_ot_attn_hgrp_hard'
W=S/'svc6/src_solp0'
O=S/'svc6/codex_st0_kpv';O.mkdir(exist_ok=True)
line=next(x for x in (B/'obj_m40000/Vtb_dsdv_svc_rs__verFiles.dat').read_text().splitlines() if x.startswith('C '))
args=shlex.split(json.loads(line[2:]))
assert '-GST=0' in args and '-DOT_SVC_ATTW_LP' in args and '-DOT_SVC_ATT_PINREG' in args
assert args[args.index('-Mdir')+1]==str(B/'obj_m40000')
(O/'original_top_command.json').write_text(json.dumps(args,indent=2)+'\n')
inputs=[B/'obj_m40000/Vtb_dsdv_svc_rs__verFiles.dat']
for t in args:
 p=Path(t);p=p if p.is_absolute() else W/p
 if p.suffix in ('.sv','.a') and p.is_file():inputs.append(p)
(O/'reused_inputs.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\n' for p in inputs))
VL=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
subprocess.run([str(VL),'--version'],check=True)
def build(k):
 d=O/f'obj_kpv{k}';a=list(args);a[a.index('-Mdir')+1]=str(d);a[a.index('-j')+1]='4';a.append(f'-GKPV={k}')
 (O/f'command_k{k}.json').write_text(json.dumps([str(VL),*a],indent=2)+'\n')
 with (O/f'build_k{k}.log').open('w') as f:r=subprocess.run([str(VL),*a],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(k,r.returncode)
 return k
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for k in pool.map(build,[64,66,68,70]):print('ST0_KPV_BUILT',k,flush=True)
def run(ks):
 k,s=ks;p=O/f'run_k{k}_tail46_s{s}.log'
 with p.open('w') as f:r=subprocess.run([str(O/f'obj_kpv{k}/Vtb_dsdv_svc_rs'),f'+dir={S}/vec/tail46',f'+seed={s}'],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 lines=[x for x in p.read_text().splitlines() if x.startswith(('SVCRS die=','SVCRS_SO '))]
 print('ST0_KPV',k,s,'RC',r.returncode,*lines,sep='\n',flush=True)
 assert len(lines)==2,(k,s,'missing verdict')
 return dict(kpv=k,seed=s,rc=r.returncode,verdicts=lines)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(run,[(k,s) for k in [64,66,68,70] for s in [1,2]]))
(O/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print('ST0_KPV_SWEEP_COMPLETE',flush=True)
