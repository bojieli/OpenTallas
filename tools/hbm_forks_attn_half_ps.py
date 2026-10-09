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
    print('written', lo)


if __name__ == '__main__':
    main()
