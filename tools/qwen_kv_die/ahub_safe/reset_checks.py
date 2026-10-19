#!/usr/bin/env python3
import subprocess
from pathlib import Path
b=Path('..').resolve();out=b/'native_bench0_final'
for phase in (1,256,700,1350,1700):
 p=out/f'reset_{phase}.log'
 with p.open('w')as f:r=subprocess.run([str(out/'obj_m0/Vtb_qkd_ahub_static_dw_safe'),f'+reset_phase={phase}'],stdout=f,stderr=subprocess.STDOUT)
 s=p.read_text();assert r.returncode==0 and 'AHUB_DW PASS' in s and 'AHUB_DW FAIL' not in s,(phase,r.returncode,s)
 print('\n'.join(x for x in s.splitlines()if x.startswith(('AHUB_NATIVE_RESET','AHUB_DW PASS'))),flush=True)
print('AHUB_NATIVE_OCCUPIED_RESET_PASS phases=5 global_hold=80 global_drain=80 production_POR_qualified=false')
