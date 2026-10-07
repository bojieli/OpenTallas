#!/usr/bin/env python3
"""Explicit opt-in successor source list. Example:
python3 tools/hbm_su_div64.py campaign --ddiv 64 --quick --only random --scratch /tmp/div64 --out /tmp/div64.json
Uses unchanged c12 default parameters unless --ddiv 64 is explicitly supplied.
"""
import hbm_su_c12 as C

def install():
    for key, values in list(C.SWAP.items()):
        if any(x in key for x in ('vec_lane.sv', 'vec_side.sv', 'v41x_sfu.sv')):
            C.SWAP[key] = ['rtl/hbm_accel/su/div64_candidate/' + p.split('/')[-1] for p in values]
    additions = ['rtl/hdc/v41/ot_hdc_fdiv64.sv', 'rtl/hdc/ot_hdc_cg.sv']
    C.C12_UNITS.extend(additions)
    C.C12_UNITS_DPI.extend(additions)

if __name__ == '__main__':
    install()
    raise SystemExit(C.main())
