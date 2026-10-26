#!/usr/bin/env python3
"""S81-HEAD (10-24): re-skew the HD-TILE ROM images to another adder latency.

The bundle ROM image stores the systolic chain skew: physical word p lane j holds logical word (p - SK*(j mod 8)) mod
8192 (tools/dsrom_1m_head.py skewed_image), SK = 1 + popcount(CUT) + SPLIT9.  The 10-21 images
(results/rtl/s81_head_tile_1021/img) were written at CUT 0x17b (SK 8); the closed element views are CUT 0x1ff + SPLIT9
(SK 11).  This decodes each viamap (tools/w10_validation/rtl_v41_rom_array.viamap, depth 4096, 2 banks = even / odd
physical words), un-skews at --from, re-skews at --to and writes the same file names.  Self-check: --from == --to
reproduces every file byte-for-byte (run with --check).  x streams (xa / xb) are copied unchanged (the x skew is in RTL).

    python3 tools/s81_head/hd_reskew_images.py SRC_DIR OUT_DIR --from 8 --to 11 [--check]
"""
import argparse
import shutil
from pathlib import Path

import numpy as np

NW, DEPTH = 8192, 4096


def decode(path):
    """viamap hex -> words[adr] as 16 lanes of 16 bits (adr 0..4095)."""
    rows = [int(l, 16) for l in path.read_text().split()]
    out = np.zeros((DEPTH, 16), dtype=np.uint32)
    for r, v in enumerate(rows):
        if not v:
            continue
        for s in range(8):
            w = 0
            b = 0
            vv = v >> s
            while vv:
                if vv & 1:
                    w |= 1 << b
                vv >>= 8
                b += 1
            assert w >> 256 == 0, (path, r, s)
            for j in range(16):
                out[8 * r + s, j] = (w >> (16 * j)) & 0xFFFF
    return out


def encode(words, path):
    rows = [0] * (DEPTH // 8)
    for a in range(DEPTH):
        w = 0
        for j in range(16):
            w |= int(words[a, j]) << (16 * j)
        r, s = divmod(a, 8)
        v = rows[r]
        b = 0
        while w:
            if w & 1:
                v |= 1 << (b * 8 + s)
            w >>= 1
            b += 1
        rows[r] = v
    path.write_text("".join(f"{v:0548x}\n" for v in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--from", dest="sk_from", type=int, required=True)
    ap.add_argument("--to", dest="sk_to", type=int, required=True)
    ap.add_argument("--check", action="store_true", help="also verify decode/encode round trip at --from")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    p = np.arange(NW)[:, None]
    j = np.broadcast_to(np.arange(16)[None, :], (NW, 16))
    insts = sorted({f.name[:-len("_0.viamap.hex")] for f in a.src.glob("*_0.viamap.hex")})
    for inst in insts:
        img = np.zeros((NW, 16), dtype=np.uint32)
        for bk in (0, 1):
            img[bk::2] = decode(a.src / f"{inst}_{bk}.viamap.hex")
        L = np.zeros_like(img)
        L[(p - a.sk_from * (j % 8)) % NW, j] = img          # un-skew
        new = L[(p - a.sk_to * (j % 8)) % NW, j]             # re-skew
        for bk in (0, 1):
            dst = a.out / f"{inst}_{bk}.viamap.hex"
            encode(new[bk::2], dst)
            if a.check and a.sk_from == a.sk_to:
                assert dst.read_bytes() == (a.src / dst.name).read_bytes(), dst
        print(inst, "ok")
    for f in a.src.iterdir():
        if not f.name.endswith(".viamap.hex"):
            shutil.copy2(f, a.out / f.name)


if __name__ == "__main__":
    main()
