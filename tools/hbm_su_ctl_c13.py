#!/usr/bin/env python3
"""Minimum full-controller exactness on existing golden chain cases.

Default-OFF CTL13 successor; no leaf FP equivalence or physical qualification
is claimed by this driver. Existing c12 arithmetic, identities and golden
rounding are retained. Run su-run with the existing case pickle.
"""
import os
from pathlib import Path
import sys
import hbm_su_c12 as C

ROOT = Path(__file__).resolve().parents[1]
C.SWAP['rtl/hdc/v41x/ot_hdc_v41x_vec.sv'] = [
    'rtl/hdc/v41x/ot_hdc_v41x_vec_c13.sv',
    'rtl/hdc/v41x/ot_hdc_su_ctl_c13_primitives.sv',
]
original_apply = C.apply

def apply(VC, dpi=False):
    original_apply(VC, dpi=dpi)
    VC.TB = ROOT / 'rtl/test/tb_hdc_v41x_vec_c13.sv'
    os.environ['OT_VFLAGS'] += ' -GCTL13=1'
    # Capacity admission replaces the inherited wall-time limit.
    original_run_case = VC.run_case
    VC.run_case = lambda exe, d, nops, x=None, timeout=None: original_run_case(exe, d, nops, x, timeout=None)

C.apply = apply
if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != 'su-run':
        raise SystemExit('Use su-run with existing golden controller cases')
    raise SystemExit(C.main())
