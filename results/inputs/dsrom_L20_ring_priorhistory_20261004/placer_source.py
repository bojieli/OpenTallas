#!/usr/bin/env python3
"""W11: place a region's index keys into the quarter-per-stack RING layout (the die's IDX_RING = 1 key map).

Input: a region's keys in the legacy relative 68-B super-block layout (tools/hdc_images_v41x.py ikhbm_image,
tools/v41_die_l0_images.py key_superblocks): key t (b = t // 1024, tt = t % 1024) has its 128 E2M1 codes in
sectors (17 b + 1 + tt // 64) * 128 + 2 (tt % 64) and + 1, its 4 UE8M0 scale bytes in 32-bit field tt % 8 of
sector 17 b * 128 + tt // 8.

Output: per stack q, the sectors of the ring state of count n (the keys present before the step):
  Qs = 8 floor(n / 32); key t on stack q = 0 (t < Qs), 1 (< 2 Qs), 2 (< 3 Qs), else 3;
  ring slot sl = t mod C, C = RSB * 1024 + RTAIL;
  codes at (KB + 17 (sl // 1024) + 1 + (sl % 1024) // 64) * 128 + 2 (sl % 64) (+ 1),
  scale in field sl % 8 of sector (KB + 17 (sl // 1024)) * 128 + (sl % 1024) // 8,
where KB is the region's base block: user_base_sectors / 128 + r * UBLK (UBLK = 17 RSB + 1 + ceil(RTAIL / 64)),
r = (region KV word - cfg_ik_base) >> 7.  This is the placement the die ring gates check the die's own writer
against (rtl/test/tb_chip_v41x_die_ring_mu.sv ring_image; results/rtl/w11_die_idx_ring_mu_gate.json carries
keys written by the die in one step and compared with this placement at the next).

CLI: w11_idx_ring_place.py <ikhbm_region.hex> <out_dir> [--n N] [--kb KB] [--rsb 64] [--rtail 32]
writes <out_dir>/ikring_s<q>.hex ("<sector hex> <256-bit hex>" lines, the runtime wrapper's sparse format).
"""
from __future__ import annotations

import argparse
from pathlib import Path


def geometry(rsb: int = 64, rtail: int = 32) -> tuple[int, int]:
    c = rsb * 1024 + rtail
    ublk = rsb * 17 + ((1 + (rtail + 63) // 64) if rtail else 0)
    return c, ublk


def keys_of(img: dict[int, int]) -> dict[int, tuple[int, int]]:
    """{t: (codes 512-bit, scale 32-bit)} of the keys in a legacy relative image (a key with zero codes and
    scale is absent, as the benches count it)."""
    keys: dict[int, list[int]] = {}
    for s, w in img.items():
        b, o = divmod(s, 17 * 128)
        blk, j = divmod(o, 128)
        if blk == 0:                                  # scale block: sector j holds keys 8 j .. 8 j + 7
            for f in range(8):
                v = (w >> (32 * f)) & 0xFFFFFFFF
                if v:
                    keys.setdefault(b * 1024 + 8 * j + f, [0, 0])[1] = v
        else:
            t = b * 1024 + (blk - 1) * 64 + j // 2
            if w:
                k = keys.setdefault(t, [0, 0])
                k[0] |= w << (256 * (j % 2))
    return {t: (c, sc) for t, (c, sc) in keys.items()}


def place(img: dict[int, int], n: int | None = None, kb: int = 0, rsb: int = 64,
          rtail: int = 32) -> dict[int, dict[int, int]]:
    c, _ = geometry(rsb, rtail)
    keys = keys_of(img)
    if n is None:
        n = max(keys) + 1 if keys else 0
    assert all(t < n for t in keys), "a key beyond the count"
    qs = (n // 32) * 8
    assert qs <= c and n - 3 * qs <= c, f"count {n} exceeds the ring ({c} slots a stack)"
    out: dict[int, dict[int, int]] = {0: {}, 1: {}, 2: {}, 3: {}}
    for t, (codes, sc) in keys.items():
        q = 0 if t < qs else 1 if t < 2 * qs else 2 if t < 3 * qs else 3
        sl = t % c
        cs = (kb + 17 * (sl // 1024) + 1 + (sl % 1024) // 64) * 128 + 2 * (sl % 64)
        ss = (kb + 17 * (sl // 1024)) * 128 + (sl % 1024) // 8
        m = out[q]
        if codes:
            m[cs] = codes & ((1 << 256) - 1)
            m[cs + 1] = codes >> 256
        if sc:
            m[ss] = m.get(ss, 0) | (sc << (32 * (sl % 8)))
    return out


def read_sparse(p: Path) -> dict[int, int]:
    img = {}
    for line in p.read_text().split("\n"):
        if line.strip():
            a, w = line.split()
            img[int(a, 16)] = img.get(int(a, 16), 0) | int(w, 16)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--n", type=int, default=None, help="keys present (default: highest key + 1)")
    ap.add_argument("--kb", type=int, default=0, help="region base block")
    ap.add_argument("--rsb", type=int, default=64)
    ap.add_argument("--rtail", type=int, default=32)
    a = ap.parse_args()
    st = place(read_sparse(a.image), a.n, a.kb, a.rsb, a.rtail)
    a.out.mkdir(parents=True, exist_ok=True)
    for q, m in st.items():
        (a.out / f"ikring_s{q}.hex").write_text("".join(f"{s:x} {w:064x}\n" for s, w in sorted(m.items())))
    print({q: len(m) for q, m in st.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
