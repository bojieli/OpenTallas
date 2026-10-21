#!/usr/bin/env python3
"""Opt-in real 4x32 1R1W SRAM for GRP delay backend coupons; no default changes.

--write-face (KV-GRP8 10-20): LEF pin FACES by port class instead of the compiler's half/half split of the flat pin
list.  The default split put clk/r_*/rd_out[31:0] AND wd_in[12:0] on the W face, wd_in[31:13] + w_mask on the E face,
so every ring macro's write word arrived on BOTH faces: in the s7 grp floorplans (4-macro abutted MY stacks) the
wd_in[12:0] nets wrapped round the stack ends and the incremental GRT boxed them (GRT-0183 on ring-B wd_in[3] in all
four s7 gates, again after the fresh-process resume).  --write-face keeps the SAME outline, pitch, pin count per face
(52 / 51), Liberty, behaviour and blackbox views; only pin positions move:
  W face (master): clk, r_ce_in, r_addr_in, rd_out[31:0], w_mask_in[15:0]      (read port: faces the ring exits under MY)
  E face (master): w_ce_in, w_addr_in, wd_in[31:0], w_mask_in[31:16]           (write port: faces the incoming word under MY)
"""
import argparse
import hashlib
import json
from pathlib import Path
import asap7
import sram_gen as S
import build_coll_safe_pins_1019 as P

NAME='ot_sram_1r1w_4x32_m1_p192_grp_rsp'


class _Slice:
    """LEF-only view of a slice of a bus pin (direction/kind/bits as views.Pin)."""
    def __init__(self, pin, idx):
        self.name, self.width, self.direction, self.kind, self.related = pin.name, len(idx), pin.direction, pin.kind, pin.related
        self._bits = [f"{pin.name}[{i}]" for i in idx]

    def bits(self):
        return self._bits


def write_face_lef(base):
    def lef(name, w, h, pins, props):
        by = {p.name: p for p in pins}
        assert set(by) == {'clk', 'r_ce_in', 'r_addr_in', 'rd_out', 'w_ce_in', 'w_addr_in', 'wd_in', 'w_mask_in'}, sorted(by)
        b = by['wd_in'].width
        west = [by['clk'], by['r_ce_in'], by['r_addr_in'], by['rd_out'], _Slice(by['w_mask_in'], range(b // 2))]
        east = [by['w_ce_in'], by['w_addr_in'], by['wd_in'], _Slice(by['w_mask_in'], range(b // 2, b))]
        nw, ne = (sum(len(p.bits()) for p in x) for x in (west, east))
        # views.write_lef puts the first ceil(n/2) flat bits on the W edge, the rest on the E edge
        assert nw == -(-(nw + ne) // 2), (nw, ne)
        return base(name, w, h, west + east, props)
    return lef


def main():
    ap=argparse.ArgumentParser(__doc__);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--write-face',action='store_true',help='read port W face / write port E face (KV-GRP8)');a=ap.parse_args()
    asap7.METAL['pin_pitch_um']=0.192
    S.timing_model=P.pin_access_timing
    S.macro_outline=P.mirror_outline
    if a.write_face:
        S.write_lef=write_face_lef(S.write_lef)
    sheet=S.compile_macro(S.SramSpec(NAME,4,32,1,1,'1r1w',0,0),a.out)
    sheet['grp_delay_contract']={'logical_capacity':'32 banks x 4words x32bits =4096bits; all payload in actual SRAM','operation':'single sameclock 1R1W, registered read, read-before-write on same address','source_pinning':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(S.__file__),Path(P.__file__),Path(asap7.__file__),Path(S.__file__).with_name('behav.py'),Path(S.__file__).with_name('views.py'),Path(S.__file__).with_name('asap7_calibration.json'),asap7.BITCELL_JSON,asap7.TECH_JSON]},'pin_access':'0.192um contacts; mirror-safe vertical outline; calibrated actual longest pin lead RC included via existing compiler helper','qualification':'views only, no route/phase/behavior PASS claimed; timed/functional/SAT coupon required'}
    if a.write_face:
        sheet['grp_delay_contract']['pin_faces']=('KV-GRP8 --write-face: master W = clk,r_ce_in,r_addr_in,rd_out[31:0],w_mask_in[15:0]; '
                                                  'master E = w_ce_in,w_addr_in,wd_in[31:0],w_mask_in[31:16]; outline/pitch/Liberty/behaviour unchanged')
    p=a.out/NAME/(NAME+'.json');p.write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'name':NAME,'area':sheet['area'],'timing':sheet['timing']},indent=2))
if __name__=='__main__':main()
