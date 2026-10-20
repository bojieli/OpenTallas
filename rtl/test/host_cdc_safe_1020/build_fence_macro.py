#!/usr/bin/env python3
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import build_qw_p192_1019 as P
S=P.S;S.timing_model=P.pin_access_timing;S.macro_outline=P.mirror_outline
P.asap7.METAL['pin_pitch_um']=0.192
name='ot_sram_1r1w_32x64_m1_p192_mir'
d=S.compile_macro(S.SramSpec(name,32,64,1,1,'1r1w',0,0),ROOT/'physical/asap7_memory_macros')
print(name,d['area'])
