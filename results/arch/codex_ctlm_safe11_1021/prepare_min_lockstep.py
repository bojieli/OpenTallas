#!/usr/bin/env python3
"""Assemble exact safe11 landing differential; both sides use h16yb native hard leaf.
This proves transport composition; existing head3135 control proof proves the leaf.
No old h16c/LPF head is a numerical/control reference.
"""
from pathlib import Path
import subprocess,sys
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
def blob(rev,path):return subprocess.check_output(['git','show',rev+':'+path])
def put(path,data):
 p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
files=blob('HEAD','results/rtl/qw_tlprod_1020/bench10.f').decode().splitlines(); kept=[]
for f in files:
 if f=='rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv':continue
 if f.startswith('rtl/qwen_dv/lp9d_np/'):f=f.replace('lp9d_np','lp9e_h16y')
 if f=='tb_np10.sv':source='results/rtl/qw_tlprod_1020/'+f
 elif f.startswith('calr/'):source='results/rtl/qw_calr_1020/ctlm9c/'+f.split('/')[-1]
 else:source=f
 data=blob('HEAD',source)
 if f=='rtl/qwen_dv/qfd_tt_ctlm_dv_lpf.sv':
  data=data.replace(b'ot_qfd_tt_ctlm_static_hr #(.STAGE_ME((STAGE_ME != 0) ? 1 : 0)) u_hr',b'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r u_hr').replace(b', .ck_pm0(ck), .ck_pm1(ck)',b'')
 put(f,data);kept.append(f)
for f in ['results/rtl/qw_head_safe32_1020/h16y/net_ifg2/native32_1r_param.v','results/rtl/qw_head_safe32_1020/h16y/net_ifg2/native32_helpers.sv']:
 put(f,blob('4d8fedfd8',f));kept.append(f)
f='physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v';put(f,blob('HEAD',f));kept.append(f)
# Exact immutable calendar images and simulation ROM models used by the existing minimal producer bench.
for base in ['results/rtl/qw_tlprod_1020/images','results/rtl/qw_calr_1020/ctlm9c']:
 names=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD',base],text=True).splitlines()
 for p in names:
  if '/images/' in p:
   dst=p.split('/images/',1)[1]
  elif p.endswith('.hex'):
   dst='calr/'+p.rsplit('/',1)[1]
  else:continue
  put(dst,blob('HEAD',p))
(out/'safe11.f').write_text('\n'.join(kept)+'\n')
print('SAFE11_MIN_SOURCE_READY',len(kept))
