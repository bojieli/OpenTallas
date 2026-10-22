#!/usr/bin/env python3
"""Opt-in host SRAM p192 abstracts using the established QW pin-access RC recipe.
Retain old macro views. Same32x546 storage, masks, ports, behaviour and clock latency.
"""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import build_qw_p192_1019 as P
S=P.S;S.timing_model=P.pin_access_timing;S.macro_outline=P.mirror_outline
P.asap7.METAL['pin_pitch_um']=0.192
for port in ['1r1w','1r1w2c']:
 orig='ot_sram_'+port+'_32x546_m1';name=orig+'_p192_mir'
 d=S.compile_macro(S.SramSpec(name,32,546,1,1,port,0,0),ROOT/'physical/asap7_memory_macros')
 d['pin_access_contract']=dict(pitch_um=0.192,max_density_per_um=1/0.192,immutable_original=orig,
   generator='rtl/test/host_cdc_safe_1020/build_macros.py',recipe='tools/mem_compiler/build_qw_p192_1019.py',
   timing='Existing QW p192 terminal-to-core lead M4 Elmore + worst output/inv4 RC added to clk->q/setup/slew/min period/caps/energy; original memory functionality unchanged.',
   claim='Calibrated analytical abstract; not transistor layout; consuming parent route still required')
 (ROOT/'physical/asap7_memory_macros'/name/(name+'.json')).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 a=d['area'];print(name,a['macro_width_um'],a['macro_height_um'],a['macro_area_um2'],d['timing']['tt']['clk_to_q_ps'])
