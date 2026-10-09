#!/usr/bin/env python3
"""hbm-forks (2026-10-09, RQ-HF-4): pin plans of the half tiles with the PS entry ports.

Copies physical/hbm_attn_tile_r/half/<master>/ to physical/hbm_attn_tile_r/half_ps/<master>/ and adds, to hfd_attn_half_lo
only, the PS row port `ks` (1,102 in: 3 forwarded clocks + the 1,099-b row line) and the static strap `ldk` (1 in) on the
S face, M5, at the k bank's pitch (0.192 um), in the free span east of ci (k 518.9-721.6, ci 733.9-1050.5 um).
The legacy records are untouched.   python3 tools/hbm_forks_attn_half_ps.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, DST = ROOT / 'physical/hbm_attn_tile_r/half', ROOT / 'physical/hbm_attn_tile_r/half_ps'
X0, PITCH = 1062.0, 0.192


def main():
    for m in ('hfd_attn_half_lo', 'hfd_attn_half_hi'):
        d = DST / m
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(SRC / m, d)
    lo = DST / 'hfd_attn_half_lo'
    r = json.loads((lo / 'ports.json').read_text())
    x1 = round(X0 + 1101 * PITCH, 3)
    r['ports']['ks'] = dict(bits=1102, direction='input', layer='M5', x=[X0, x1], y=[0.096, 0.096])
    r['ports']['ldk'] = dict(bits=1, direction='input', layer='M5', x=[round(x1 + 2.016, 3)] * 2, y=[0.096, 0.096])
    r['note_hbm_forks'] = 'ks / ldk added by tools/hbm_forks_attn_half_ps.py (RQ-HF-4 entry points)'
    (lo / 'ports.json').write_text(json.dumps(r, indent=1) + '\n')
    lines = [f'place_pin -pin_name {{ks[{i}]}} -layer M5 -location {{{X0 + i * PITCH:.4f} 0.0960}} -pin_size {{0.0240 0.1920}}'
             for i in range(1102)]
    lines.append(f'place_pin -pin_name {{ldk[0]}} -layer M5 -location {{{x1 + 2.016:.4f} 0.0960}} -pin_size {{0.0240 0.1920}}')
    with open(lo / 'io_place.tcl', 'a') as f:
        f.write('# hbm-forks RQ-HF-4: PS entry row port + strap\n' + '\n'.join(lines) + '\n')
    mp = lo / 'macro_placement.tcl'
    add = '# hbm-forks RQ-HF-4: the PS entry row port ks lands in two SN pin banks under its pins (x 1062.0-1273.4, S face)\n'
    for c, x in ((0, 1056.096), (1, 1163.616)):
        add += (f'place_macro -macro_name {{u_pks.gn.g_s\\[0\\].g_c\\[{c}\\].g_sn.u_b}} -location {{{x:.3f} 0.024}} '
                '-orientation R0 -exact\n')
    # stage 0's third bank and stages 1-4 (5 stages x 3 banks: 1,102 b > 2 x 544), slots chosen free of every macro
    for s_, x, y0 in ((1, 570.36, 94.488), (2, 799.7, 308.712), (3, 955.22, 542.984), (4, 799.7, 735.912)):
        for c in range(2):     # bank 2 (bits 1,088-1,101: the forwarded clocks, unused past the pin) is swept
            add += (f'place_macro -macro_name {{u_pks.gn.g_s\\[{s_}\\].g_c\\[{c}\\].g_sn.u_b}} '
                    f'-location {{{x:.3f} {y0 + 13.968 * c:.3f}}} -orientation R0 -exact\n')
    anchor = 'foreach ot_i [[ord::get_db_block] getInsts] {'      # before the FIRM freeze of every placed block
    txt = mp.read_text()
    mp.write_text(txt.replace(anchor, add + anchor, 1).replace('banks=69"', 'banks=79"'))
    print('written', lo)


if __name__ == '__main__':
    main()
