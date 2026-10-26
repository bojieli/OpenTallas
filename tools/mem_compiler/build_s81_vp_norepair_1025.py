#!/usr/bin/env python3
"""Generate the real aligned r0c0 SRAM used by S81 VP (COORD 2026-10-25 21:21).

No spare storage or external repair pins. Existing r2c2 and fixed nr views are
immutable; this is a distinct physical master requiring fresh affected kits.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sram_gen,build_aligned_v2 as aligned

def build(root):
 root=Path(root);out=root/'physical/asap7_memory_macros_v2';name='ot_sram_1r1w_512x128_m4_r0c0'
 spec=sram_gen.SramSpec(name,512,128,4,1,'1r1w',0,0)
 with aligned.patched(sram_gen,macro_outline=aligned.aligned_outline,write_lef=aligned.aligned_write_lef,GENERATOR_VERSION=sram_gen.GENERATOR_VERSION+'+aligned-v2'):
  sheet=sram_gen.compile_macro(spec,out)
 a=sheet['area'];aligned.finish(out,name,None,(a['macro_width_um'],a['macro_height_um']),{'kind':'sram','spec':sheet['spec']})
 return out/name
if __name__=='__main__':print(build(Path(__file__).resolve().parents[2]))
