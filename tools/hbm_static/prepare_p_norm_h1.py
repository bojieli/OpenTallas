#!/usr/bin/env python3
"""Select real logical head0; never replicate canonical operation descriptors."""
import argparse,json,shutil
from make_p_producer_calendar import compile_head
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--h16',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sfu-tools',type=Path,required=True);a=p.parse_args()
for rows in [128,640]:
 src=a.h16/f't{rows}_h16';dst=a.out/f't{rows}_h1';dst.mkdir(parents=True,exist_ok=True)
 compile_head(rows,0,a.sfu_tools,dst,normalize=True,scaled_in_e=True)
 for name,n in [('raw_sc_sectors',rows//8),('raw_pv_sectors',64),('expected_mb',1),('expected_se',1),('expected_eb',rows),('expected_den',1),('expected_norm',512)]:
  (dst/f'{name}.hex').write_text('\n'.join((src/f'{name}.hex').read_text().split()[:n])+'\n')
 first=int((src/'sink_sectors.hex').read_text().split()[0],16)&0xffffffff
 (dst/'sink_sectors.hex').write_text(f'{first:064x}\n')
 for name,dest in [('expected_scaled_sc','expected_scaled'),('expected_e','expected_e')]:shutil.copyfile(a.oracle/f't{rows}_h00'/f'{name}.hex',dst/f'{dest}.hex')
 model=json.loads((src/'model.json').read_text());model.update(heads=1,canonical_frozen_G25_logical_heads=1,extra_scaled_SC_temporary_allocation_bound=True,scaled_SC_lease='future_E_before_raw_E_generation',physical_qualified=False,native_whole_kernel_qualified=False);(dst/'model.json').write_text(json.dumps(model,indent=2)+'\n')

mut=a.out/'mutant_live_SC_lease';shutil.copytree(a.out/'t640_h1',mut,dirs_exist_ok=True)
compile_head(640,0,a.sfu_tools,mut,normalize=True,wrong_lease_sc=True)
