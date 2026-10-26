#!/usr/bin/env python3
"""S81-KITS-RTLC ruling (b): const_pins_dropped entries for dsdv_bksel_c (producer) and dsdv_bk_g (consumer)."""
import json, sys
L = sys.argv[1] + "/physical/die_plan/s81/inputs/const_pins_dropped.json"
d = json.load(open(L))
drop = ["vd[0]"] + ["vd[%d]" % i for i in range(357, 502)] + ["vd[513]"]
ren = {"vd[%d]" % i: "vd[%d]" % (i - 1) for i in range(1, 357)}
ren.update({"vd[%d]" % (502 + k): "vd[%d]" % (356 + k) for k in range(11)})
assert len(drop) == 147 and len(ren) == 367
why = ("S81-KITS-RTLC 10-24 coordinator ruling (b) 'drop' (bk_col has no consumer in v4.8): the dsfd_selt_c vd word of "
       "the S81 bk_sel select control is {kind 4 (3/4/5/7), seg_tag 8, 145 x 0, ...}: vd[513] (kind msb) and vd[501:357] "
       "are constant 0 at the producer (raw face_guard: TIELO), and vd[0] (rst copy) has no reader in dsdv_bk_g; "
       "dsdv_bksel_c vd and dsdv_bk_g vd (VD_PK = 1) are packed to vd[366:0] = {vd[512:502], vd[356:1]} at both ends "
       "('rename'); legacy plana / bk_col parents use dsdv_bk_g VD_PK = 0")
for m in ("dsdv_bksel_c", "dsdv_bk_g"):
    assert m not in d["modules"], m
    d["modules"][m] = {"pins": drop, "rename": ren, "why": why}
json.dump(d, open(L, "w"), indent=1)
print("ok")
