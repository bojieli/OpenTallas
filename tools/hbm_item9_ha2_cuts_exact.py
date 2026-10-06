#!/usr/bin/env python3
"""Minimum changed-source full16 adapter, exact fixed FP32 tree/BF16 oracle."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
o=a.out;assert o.is_absolute() and not o.exists();o.mkdir(parents=True)
vals=np.array([0x3f808000,0xbf800000,0x3f818000,0x33800000,0x4b000000,0xcb000000,0x3eaaaaab,0xbeaaaaab],dtype=np.uint32)
words=[]
for pf in (64,384):
 out=[]
 for f in range(pf//8):
  u=vals[(np.arange(8)[:,None]+f+np.arange(16)[None,:])%8]
  u[0,:]=np.uint32(0x3f800000)+((f+np.arange(16,dtype=np.uint32))<<16)
  level=u.view(np.float32)
  while len(level)>1:level=np.add(level[::2],level[1::2],dtype=np.float32)
  assert np.isfinite(level).all()
  bits=level.reshape(-1).view(np.uint32)
  packed=((bits.astype(np.uint64)+0x7fff+((bits>>16)&1))>>16)&0xffff
  out.append(list(map(int,packed)))
 for f in range(0,len(out),2):
  lane16=out[f]+out[f+1]
  words.append(sum(v<<(16*i) for i,v in enumerate(lane16)))
assert len(words)==28
(o/'gold.hex').write_text(''.join(f'{w:0128x}\n' for w in words))
files=['rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv',
 'rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv','rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_runtime.sv',
 'rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_item9_cuts.sv','rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_adapter_item9_cuts.sv',
 'results/rtl/hbm_item9_closure_20261005/tb_item9_ha2_cuts_fullshape.sv']
cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb_item9_ha2_cuts_fullshape','-Mdir',str(o/'obj'),*files]
with (o/'build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
with (o/'run.log').open('w') as log:subprocess.run([str(o/'obj/Vtb_item9_ha2_cuts_fullshape'),'+gold='+str(o/'gold.hex')],stdout=log,stderr=subprocess.STDOUT,check=True)
s=(o/'run.log').read_text();assert 'PASS changedHA2 CUTS1 LANES16 PF384' in s,s
assert 'DESTINATION PASS no slot write' in s
phases=re.findall(r'PHASE PASS pf=(\d+) results=(\d+).*?first_latency_cycles=(\d+)',s)
assert phases==[('64','4','23'),('384','24','23')],phases
(o/'result.json').write_text(json.dumps(dict(verdict='PASS_CHANGED_HA2_FULL16_GOLDEN',shape=dict(NC=8,LANES=16,PFMAX=384,NPT=8,INJ=2,LAT=7,SLOTREG=1,CUTS=1),packed_words=28,BF16_scalar_results=896,first_latency_cycles=23,new_cycles=0,arithmetic_oracle='host float32 fixed pairwise tree then original RNE BF16 packing',source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},host_oracle_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),contextual_SS_FF=False,adopted=False),indent=2)+'\n')
