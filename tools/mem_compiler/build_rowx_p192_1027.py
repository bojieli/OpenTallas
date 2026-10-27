#!/usr/bin/env python3
"""ROWX LC 32x512 SRAM, identical ports/one-cycle read with 0.192um face pitch.

Uses the already-adopted QW p192 pin-lead timing model; preserves mask_gran32
and distinct read/write faces of the original. Original views are immutable.
"""
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import sram_gen as S
import asap7
import build_qw_p192_1019 as Q
NAME='ot_sram_1r1w_32x512_m1_p192_mir'
def outline(cw,ch,pins,faces=None):
    w,h,info=Q.BASE_OUTLINE(cw,ch,pins,faces=faces)
    hn=math.ceil((round(h*1000)-24)/48)*48+24
    info.update(mirror_height_added_um=round(hn/1000-h,3),height_rule_nm='H=24mod48: M4centres stay12mod48 underR180')
    return w,hn/1000,info

def main():
    asap7.METAL['pin_pitch_um']=.192
    S.macro_outline=outline;S.timing_model=Q.pin_access_timing
    root=Path(__file__).resolve().parents[2]
    out=root/'physical/asap7_memory_macros'
    d=S.compile_macro(S.SramSpec(NAME,32,512,1,1,'1r1w',0,0,mask_gran=32,pin_faces='rw'),out)
    d['pin_access_contract']=dict(pitch_um=.192,max_density_per_um=1/.192,
      immutable_original='ot_sram_1r1w_32x512_m1',generator='tools/mem_compiler/build_rowx_p192_1027.py',
      timing='Existing QW p192 M4 pin-lead RC model; one-cycle read unchanged; parent route qualifies access')
    (out/NAME/(NAME+'.json')).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(NAME,d['area']['macro_width_um'],d['area']['macro_height_um'],d['timing']['tt']['clk_to_q_ps'])
if __name__=='__main__':main()
