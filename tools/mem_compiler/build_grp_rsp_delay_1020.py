#!/usr/bin/env python3
"""Opt-in real 4x32 1R1W SRAM for GRP delay backend coupons; no default changes."""
import argparse
import hashlib
import json
from pathlib import Path
import asap7
import sram_gen as S
import build_coll_safe_pins_1019 as P

NAME='ot_sram_1r1w_4x32_m1_p192_grp_rsp'

def main():
    ap=argparse.ArgumentParser(__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    asap7.METAL['pin_pitch_um']=0.192
    S.timing_model=P.pin_access_timing
    S.macro_outline=P.mirror_outline
    sheet=S.compile_macro(S.SramSpec(NAME,4,32,1,1,'1r1w',0,0),a.out)
    sheet['grp_delay_contract']={'logical_capacity':'32 banks x 4words x32bits =4096bits; all payload in actual SRAM','operation':'single sameclock 1R1W, registered read, read-before-write on same address','source_pinning':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(S.__file__),Path(P.__file__),Path(asap7.__file__),Path(S.__file__).with_name('behav.py'),Path(S.__file__).with_name('views.py'),Path(S.__file__).with_name('asap7_calibration.json'),asap7.BITCELL_JSON,asap7.TECH_JSON]},'pin_access':'0.192um contacts; mirror-safe vertical outline; calibrated actual longest pin lead RC included via existing compiler helper','qualification':'views only, no route/phase/behavior PASS claimed; timed/functional/SAT coupon required'}
    p=a.out/NAME/(NAME+'.json');p.write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'name':NAME,'area':sheet['area'],'timing':sheet['timing']},indent=2))
if __name__=='__main__':main()
