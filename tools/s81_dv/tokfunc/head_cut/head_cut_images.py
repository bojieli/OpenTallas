#!/usr/bin/env python3
"""RTLGAP2-HEADTB (10-21): ROM images of every head-die tile for the CUT-A runs, with the element skew of the BOUND tile.

Same images as tools/s81_head/hd_tile_images.py (the tile bench) for every die tile: instance prefix INSTANCE (die.v
strap), rows rowbase + row0 .. + 127 of the released DeepSeek-V4.1 head.weight, skewed with SK = the element adder latency
of ot_s81hd_bundle as bound (NC 1 -> ot_hdc_fp32_add_lat_fan32 LAT 7 -> SK 7).  tokfunc2-s81-lx head_die_images.py wrote
its images with the dsrom_1m_head default SK (1 + popcount(CUT 0x17b) = 8): on the NC 1 bundle every formed logit of every
tile was wrong (CUT-A 0/128), so those images are not used.  Also writes xa.hex / xb.hex / xb_beats.hex / golden.json
(copied from --golden-dir, the reference stays the same) and IMAGES_DONE.

    python3 head_cut_images.py --src SRC --tiles tiles.txt --golden-dir LXIMG --out OUT [--sk 7] [--jobs N]
Env DSROM_1M_SNAP / DSROM_1M_HEAD_REF as tools/dsrom_1m_head.py.
"""
import argparse
import multiprocessing as mp
import shutil
import sys
from pathlib import Path

import numpy as np

H = None
SK = 7


def init(src, sk):
    global H
    sys.path.insert(0, str(Path(src) / "tools"))
    import dsrom_1m_head as h  # noqa: E402
    h.setup_gate()
    h.SK = sk
    H = h


def one(args):
    src, sk, out, inst, r0 = args
    if H is None:
        init(src, sk)
    ck = H.Ckpt(H.SNAP)
    m = H.gate.Mat(ck, "head", "bf16", H.BUNDLE_ROWS, H.K, r0=r0)
    u = np.asarray(m.u16, dtype=np.uint64)
    for q in range(4):
        H.write_macro(H.skewed_image(u[32 * q:32 * q + 32, :4096].reshape(H.NW, 16)), Path(out), f"{inst}a{q}")
    perm = np.array([32 * (n % 4) + n // 4 for n in range(H.BUNDLE_ROWS)])
    H.write_macro(H.skewed_image(u[perm, 4096:].reshape(H.NW, 16)), Path(out), f"{inst}b")
    return inst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--golden-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rowbase", type=int, default=0)
    ap.add_argument("--sk", type=int, default=7)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for f in ("xa.hex", "xb.hex", "xb_beats.hex", "golden.json"):
        shutil.copy(Path(a.golden_dir) / f, out / f)
    tiles = [ln.split() for ln in Path(a.tiles).read_text().split("\n") if ln.strip()]
    work = [(a.src, a.sk, str(out), inst, a.rowbase + int(r0)) for inst, r0, _ in tiles]
    with mp.Pool(a.jobs) as p:
        for i, inst in enumerate(p.imap_unordered(one, work)):
            if i % 25 == 0:
                print(f"images {i + 1}/{len(work)} {inst}", flush=True)
    (out / "IMAGES_DONE").write_text(f"{len(work)} sk {a.sk}\n")


if __name__ == "__main__":
    main()
