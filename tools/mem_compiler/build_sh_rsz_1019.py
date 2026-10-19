#!/usr/bin/env python3
"""S81-SHLK s10 (2026-10-19): right-sized dual-clock SRAM masters for the dsdv_sh_lk host FIFOs.

The sr9 kit used three 16x546 masters (176.9 x 81 um, 825 contacts a face) for 514- / 289- / 289-bit FIFOs; native
32x64 banks (16 of them) cannot be stacked (17.304-um height is off the 0.27-um row grid, so no abutment) and a
16-slot 43.2-lattice grid with 20-um channels costs ~60k um2.  This builds, with the UNCHANGED compiler and the
aligned-v2 wrapper (as build_banked_2c_1019.py), the two right-sized masters the FIFOs need:
    ot_sram_1r1w2c_16x257_m1   (the 514-bit host receive FIFO = two of them)
    ot_sram_1r1w2c_16x289_m1   (the 289-bit request FIFO and the 8-deep svc FIFO, address zero-extended)
Calibrated analytical abstracts (see each JSON claim_boundary); no transistor layout / macro SPICE.
    python3 tools/mem_compiler/build_sh_rsz_1019.py
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/mem_compiler'))
import sram_gen as S  # noqa: E402
from build_aligned_v2 import patched, aligned_outline, aligned_write_lef  # noqa: E402


def main():
    out = ROOT / 'physical/asap7_memory_macros_v2'
    rec = []
    for words, bits in ((16, 257), (16, 289)):
        name = f'ot_sram_1r1w2c_{words}x{bits}_m1'
        spec = S.SramSpec(name, words, bits, 1, 1, '1r1w2c')
        with patched(S, macro_outline=aligned_outline, write_lef=aligned_write_lef):
            sheet = S.compile_macro(spec, out)
        a = sheet['area']
        contacts = sum(p.width for p in S.pins_for(spec))
        rec.append({'master': name, 'words': words, 'bits': bits, 'width_um': a['macro_width_um'],
                    'height_um': a['macro_height_um'], 'area_um2': a['macro_area_um2'], 'contacts': contacts,
                    'contacts_per_um_face': round(contacts / 2 / a['macro_height_um'], 3),
                    'clk_to_q_ps_tt': sheet['timing']['tt']['clk_to_q_ps']})
    dst = ROOT / 'results/arch/s81_shlk_s10_1019/rsz_macros.json'
    dst.write_text(json.dumps({'schema': 'opentallas.s81shlk.rsz_macros.1019', 'masters': rec}, indent=1) + '\n')
    for r in rec:
        print('RSZ', r)


if __name__ == '__main__':
    main()
