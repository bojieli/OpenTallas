#!/usr/bin/env python3
"""Select real logical head0; never replicate canonical operation descriptors."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--h16',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
for rows in [128,640]:
 src=a.h16/f't{rows}_h16';dst=a.out/f't{rows}_h1';dst.mkdir(parents=True,exist_ok=True)
 for name in ['arithmetic.hex','io.hex','aux.hex','config.txt']:shutil.copyfile(src/name,dst/name)
 for name,n in [('raw_sc_sectors',rows//8),('raw_pv_sectors',64),('expected_mb',1),('expected_se',1),('expected_eb',rows),('expected_den',1),('expected_norm',512)]:
  (dst/f'{name}.hex').write_text('\n'.join((src/f'{name}.hex').read_text().split()[:n])+'\n')
 first=int((src/'sink_sectors.hex').read_text().split()[0],16)&0xffffffff
 (dst/'sink_sectors.hex').write_text(f'{first:064x}\n')
 for name,dest in [('expected_scaled_sc','expected_scaled'),('expected_e','expected_e')]:shutil.copyfile(a.oracle/f't{rows}_h00'/f'{name}.hex',dst/f'{dest}.hex')
 model=json.loads((src/'model.json').read_text());model.update(heads=1,canonical_frozen_G25_logical_heads=1,extra_scaled_SC_temporary_allocation_bound=False,physical_qualified=False,native_whole_kernel_qualified=False);(dst/'model.json').write_text(json.dumps(model,indent=2)+'\n')
