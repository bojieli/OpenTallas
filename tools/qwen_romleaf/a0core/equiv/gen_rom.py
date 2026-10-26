#!/usr/bin/env python3
"""Write the 10 via-map images qtile_t<T>_b<b>_c<c>.viamap.hex (512 rows x 2128 bits) that ot_rom_4096x266_m8 loads
under +OT_ROM_DIR for a tile bound with ROM_TILE=T.  Pattern = the old native bench
(rtl/test/tb_qwen_romleaf_parent_nk_native.sv): arr[row][bit] = ((row*17 + bit*13 + col*31 + bank*7) % 29) < 14.
usage: gen_rom.py OUTDIR TILE"""
import os
import sys

out, tile = sys.argv[1], int(sys.argv[2])
os.makedirs(out, exist_ok=True)
for b in range(5):
    for c in range(2):
        with open(f"{out}/qtile_t{tile}_b{b}_c{c}.viamap.hex", "w") as f:
            for row in range(512):
                v = 0
                for bit in range(2128):
                    if ((row * 17 + bit * 13 + c * 31 + b * 7) % 29) < 14:
                        v |= 1 << bit
                f.write(format(v, "0532x") + "\n")
print(f"gen_rom.py: 10 images for tile {tile} in {out}")
