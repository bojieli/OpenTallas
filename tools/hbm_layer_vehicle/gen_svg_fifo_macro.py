#!/usr/bin/env python3
"""Generate only the proposed SVG FIFO's aligned true dual-clock SRAM."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/mem_compiler'))
import sram_gen as S
from build_aligned_v2 import patched, aligned_outline, aligned_write_lef, finish
sp = S.SramSpec('ot_sram_1r1w2c_8x285_m1',8,285,1,1,'1r1w2c')
v1 = S.compile_macro(sp)
out = ROOT/'physical/asap7_memory_macros_v2'
with patched(S, macro_outline=aligned_outline, write_lef=aligned_write_lef,
             GENERATOR_VERSION=S.GENERATOR_VERSION+'+aligned-v2'):
    S.compile_macro(sp,out)
a=v1['area']
finish(out,sp.name,v1,(a['macro_width_um'],a['macro_height_um']),
       {'kind':'sram','spec':v1['spec'],'lane':'HBM-SMB-KITS'})
print('SVG_FIFO_MACRO aligned-v2 PASS 8x285 true dual clocks')
