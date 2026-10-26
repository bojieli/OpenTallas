#!/usr/bin/env python3
"""Compile genuine 64x512 no-spare/no-repair SRAM; no existing view is changed."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sram_gen,build_aligned_v2 as aligned

def build(root):
 out=Path(root)/'physical/asap7_memory_macros_v2';name='ot_sram_1r1w_64x512_m1_r0c0'
 spec=sram_gen.SramSpec(name,64,512,1,1,'1r1w',0,0)
 with aligned.patched(sram_gen,macro_outline=aligned.aligned_outline,write_lef=aligned.aligned_write_lef,GENERATOR_VERSION=sram_gen.GENERATOR_VERSION+'+aligned-v2'):
  sheet=sram_gen.compile_macro(spec,out)
 a=sheet['area'];aligned.finish(out,name,None,(a['macro_width_um'],a['macro_height_um']),{'kind':'sram','spec':sheet['spec']})
 return out/name
if __name__=='__main__':print(build(Path(__file__).resolve().parents[2]))
