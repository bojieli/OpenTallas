#!/usr/bin/env python3
"""Minimum productionD512 KV bank+native VM bridge exactness vehicle.
Uses existing SU golden normalization/RoPE/actquant, no arithmetic replacement.
Run only on the fleet, pinned Verilator from hc_gate. This is not a physical gate.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import su_gate as S
import hc_gate as H
import dsrom_su_norm as NM
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(1021512)
x=rng.standard_normal(512).astype(np.float32);x=H.f32(H.u32(x)&np.uint32(0xffff0000))
w=rng.uniform(.25,1.75,512).astype(np.float32);w=H.f32(H.u32(w)&np.uint32(0xffff0000))
ang=rng.uniform(-2,2,32);co=np.cos(ang).astype(np.float32);si=np.sin(ang).astype(np.float32);eps=np.float32(1e-6)
_,ro=NM.golden_row('kv',x,np.zeros(4,np.float32),w,eps,(co,si))
q=S.aq(ro);tmp=S.Run(S.SHAPES['full']);codes,exps=tmp.aq_rows(q,512)
expected=codes[0]+[exps[0]]+[H.pack(b[2],16) for b in q]
assert len(expected)==25
(a.out/'expected.mem').write_text(''.join(f'{int(v):0128x}\n' for v in expected))
def vm_image(kind):
 vm=[0]*1024
 def put(base,rows):
  for i,row in enumerate(rows):
   for quarter in range(4):vm[base+4*i+quarter]=(int(row)>>(128*quarter))&((1<<128)-1)
 desc=168|(int(H.u32([eps])[0])<<96)
 if kind==7:put(672,[desc]);put(676,S.rows_of(w))
 else:put(672,[desc]+S.rows_of(np.concatenate([co,si])));put(692,S.rows_of(x))
 return vm
for kind,name in [(7,'gain_vm'),(1,'kv_vm')]:
 (a.out/(name+'.mem')).write_text(''.join(f'{v:032x}\n' for v in vm_image(kind)))
extra=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_bank.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_leaf.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v']
tb='rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_kv_leaf.sv'
src=list(dict.fromkeys(H.FP['rtl']+S.RTL+S.HIER+extra))
pins={s:H.sha(ROOT/s) for s in src+[tb]}
obj=a.out/'obj';cmd=[H.VERILATOR,'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81sl_kv_leaf','-Mdir',str(obj),'-j','8',*[str(ROOT/s) for s in src+[tb]],'-CFLAGS','-O1']
b=subprocess.run(cmd,capture_output=True,text=True);(a.out/'build.log').write_text(b.stdout+b.stderr)
if b.returncode:raise RuntimeError('build failed '+str(a.out/'build.log'))
r=subprocess.run([str(obj/'Vtb_s81sl_kv_leaf')],cwd=a.out,capture_output=True,text=True);(a.out/'run.log').write_text(r.stdout+r.stderr)
ok=r.returncode==0 and 'KV_LEAF PASS' in r.stdout
n=subprocess.run([str(obj/'Vtb_s81sl_kv_leaf'),'+MUT_DROP_EXP'],cwd=a.out,capture_output=True,text=True);(a.out/'negative_exp_write.log').write_text(n.stdout+n.stderr)
negative_ok=n.returncode!=0 and 'KV_LEAF FAIL' in (n.stdout+n.stderr)
ok=ok and negative_ok
address_ok=True
for flag in ('BAD_ALIGN','BAD_BOUND'):
 z=subprocess.run([str(obj/'Vtb_s81sl_kv_leaf'),'+'+flag],cwd=a.out,capture_output=True,text=True)
 (a.out/(flag.lower()+'.log')).write_text(z.stdout+z.stderr)
 address_ok=address_ok and z.returncode==0 and 'KV_BAD_ADDRESS REJECTED' in z.stdout
ok=ok and address_ok
assert pins=={s:H.sha(ROOT/s) for s in src+[tb]},'source changed'
(a.out/'result.json').write_text(json.dumps(dict(status='PASS' if ok else 'FAIL',production_dim=512,fp='RTL',negative_exp_write_rejected=negative_ok,address_guards_rejected=address_ok,source_sha256=pins,argv=cmd),indent=2)+'\n')
print(r.stdout,flush=True);sys.exit(int(not ok))
