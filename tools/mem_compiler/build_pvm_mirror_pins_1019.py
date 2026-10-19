#!/usr/bin/env python3
"""Separate mirror-compatible PVM SRAM analytical macro; canonical p192 unchanged.
Regenerates complete compiler views. No transistor GDS or escape-route claim.
"""
import json,math
from pathlib import Path
import asap7
import sram_gen as S
from build_pvm_safe_pins_1019 import pin_access_timing
ROOT=Path(__file__).resolve().parents[2]
NAME='ot_sram_1r1w_64x512_m1_r2c2_p192_mir'
BASE_OUTLINE=S.macro_outline

def outline(cw,ch,pins):
    w,h,info=BASE_OUTLINE(cw,ch,pins)
    # A mirrored 12nm-offset M4 centre remains on-track iff H=24mod48nm.
    hn=math.ceil((round(h*1000)-24)/48)*48+24
    h2=hn/1000
    info.update(mirror_height_added_um=round(h2-h,3),height_rule_nm='H=24mod48; same 12nm M4 track residue under R180 at 43.2um lattice',original_row_snapped_height_um=h)
    return w,h2,info

def main():
    asap7.METAL['pin_pitch_um']=0.192
    S.macro_outline=outline
    S.timing_model=pin_access_timing
    sheet=S.compile_macro(S.SramSpec(NAME,64,512,1,1,'1r1w',2,2),ROOT/'physical/asap7_memory_macros')
    sheet['pin_access_contract']={'pitch_um':0.192,'immutable_original':'ot_sram_1r1w_64x512_m1_r2c2_p192','orientation':'Whole real abstract R180; all pins, PG, OBS and calibrated core rotate together','generator':'tools/mem_compiler/build_pvm_mirror_pins_1019.py','timing':'Calibrated core + actual new macroheight-coreheight M4 lead:0.38RC+driverR*C; clktoq/setup/minperiod/cap/energy recomputed','claim':'Analytical LEF/Lib/behavioral abstract; no transistor GDS, no detailed external access or native timing qualification'}
    path=ROOT/'physical/asap7_memory_macros'/NAME/(NAME+'.json')
    path.write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'size':[sheet['area']['macro_width_um'],sheet['area']['macro_height_um']],'area':sheet['area']['macro_area_um2'],'clktoq':{c:t['clk_to_q_ps'] for c,t in sheet['timing'].items()}}))
if __name__=='__main__':main()
