#!/usr/bin/env python3
"""PVFIN: port-density-safe32x128 SRAM abstract, calibrated existing p192 recipe.

Preserves original macro bytes, behavioral storage, ports, read edge and cycle
latency. Prices the stretched pin face using existing M4 lead RC/cap/energy
model from build_qw_p192_1019. A route is still required for qualification.
"""
import json
from pathlib import Path
import build_qw_p192_1019 as B
NAME='ot_sram_1r1w_32x128_m1_p192_pvfin'
B.MACROS=[(NAME,32,128,1,0,0,'ot_sram_1r1w_32x128_m1')]
if __name__=='__main__':
 B.main()
 p=B.ROOT/'physical/asap7_memory_macros'/NAME/(NAME+'.json')
 d=json.loads(p.read_text())
 d['pin_access_contract']['generator']='tools/mem_compiler/build_pvfin_p192_1020.py'
 d['pin_access_contract']['timing_recipe']='tools/mem_compiler/build_qw_p192_1019.py'
 p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
