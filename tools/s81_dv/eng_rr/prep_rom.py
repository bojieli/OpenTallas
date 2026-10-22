#!/usr/bin/env python3
"""S81-RTLGAP/RG-ENG: bench token-map ROM images (ot_dsrom_engram_token_map, 8 x ot_rom_4096x72_m8 'tmap<g>').
Synthetic compressed-id map cid(tok) = (tok * 7919 + 11) % 99092 (tb_dsdv_eng_rr.cid); word a of bank g holds the 4
ids of tok = g << 14 | a << 2 | lane at bits 17 lane.  Physical via map: word a -> row a / 8, data bit b -> column
8 b + a % 8 (ot_rom_4096x72_m8 phys_col, mux 8); one 576-bit row a line, MSB first ($readmemh).
Usage: prep_rom.py <out dir>"""
import sys
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for g in range(8):
    rows = [0] * 512
    for a in range(4096):
        w = 0
        for lane in range(4):
            tok = (g << 14) | (a << 2) | lane
            w |= ((tok * 7919 + 11) % 99092) << (17 * lane)
        for b in range(72):
            if (w >> b) & 1:
                rows[a // 8] |= 1 << (8 * b + a % 8)
    (out / f'tmap{g}.viamap.hex').write_text(''.join(f'{r:0144x}\n' for r in rows))
