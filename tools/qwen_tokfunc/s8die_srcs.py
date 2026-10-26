#!/usr/bin/env python3
"""TOK-QW 10-24: the BOUND compute-die slice row for tb_qfd_dv2 (FACE 3, rtl/test/qwen_dv/s8die/qfd_dv_slice_die.sv).

physical/die_plan/qwen_compute/bind/bound_r8 substitutes qfd_dv_slice2 by qfd_dv_s8_flat and the chain ends by
qfd_dv_s8_ce_w5 / _l9h / _e5 (asbuilt_tie.json substitute / substitute_parent).  This lists the s8 sources the bound slices
need = rtl/test/qwen_dv/s5/run_s8.sh COMMON + tools/qwen_dv/gen_slice8_lp_spec.CHILD_SOURCES + the flat / chain-end
variants, their station-safe / station-math-g / k79 sc netlists + the wrapper; and the Verilator flags of the s8 kits
(run_s8.sh VF defines + the bound asbuilt define OT_QFD_UP4_CK_ENTRIES) + -GFACE=3.
dv_bench2 (DV2_S8DIE=1) puts S8_FILES FIRST in SRCS2: Verilator keeps the first declaration of a duplicated module, so the
bound s8 children / station / SRAM models win over the predecessor copies SRCS2 also names.

    python3 tools/qwen_tokfunc/s8die_srcs.py ROOT      -> prints S8_FLAGS (for DV_LOWER_VFLAGS)
"""
import re, sys
from pathlib import Path

S8_FLAGS = ['-GFACE=3', '+define+OT_STATION_REGIONAL', '+define+OT_S5_HARD', '+define+OT_S6_SIM', '+define+OT_S8_SIM',
            '+define+OT_QFD_UP4_CK_ENTRIES', '-Wno-WIDTHCONCAT']
EXTRA = ['rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv', 'rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv',
         'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_safe.sv', 'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv',
         'rtl/qwen_dv/s5/qfd_dv_s5_sc2_ce_leaf.sv', 'rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_up0.sv',
         'rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_dn0.sv', 'rtl/test/qwen_dv/s8die/qfd_dv_slice_die.sv']


def s8_files(root):
    root = Path(root)
    common = re.search(r'COMMON="([^"]*)"', (root / 'rtl/test/qwen_dv/s5/run_s8.sh').read_text()).group(1).split()
    sys.path.insert(0, str(root / 'tools/qwen_dv'))
    import gen_slice8_lp_spec as G
    out = []
    for f in common + list(G.CHILD_SOURCES) + EXTRA:
        if f not in out:
            if not (root / f).is_file():
                raise SystemExit(f'S8DIE: missing {f}')
            out.append(f)
    return out


if __name__ == '__main__':
    s8_files(sys.argv[1])
    print(' '.join(S8_FLAGS))
