#!/usr/bin/env python3
"""TOK-FUNC2-S81-LX (10-21): ROM images + x streams + goldens for the WHOLE S81 head die (TOK.DS.LAYER.5 bound run).

The head die (S81-HEAD, H4 bind dv_die: 253 x ot_s81hd_tile on 26 spine segments) holds one TP4 rank of the released
DeepSeek-V4.1 head.weight: tile INSTANCE <name> covers rows rowbase + row0 .. + 127 (row0 = the die.v strap).  For every
tile this writes the skewed ROM images exactly as tools/s81_head/hd_tile_images.py / tools/dsrom_1m_head.py cmd_bundle
(P a0..a3 / P b, _0/_1 banks), then xa.hex / xb.hex (golden final-norm x of the 1M-context token) and golden.json:
  local   argmax over the rows this die's tiles hold (rank 0: 0 .. 32383; the last tile's 64 rows past the rank
          boundary are rank 1's real rows -- the strap layout of H4), lowest id on ties
  peers   argmax of ranks 1..3 (modelled: the other three head dies of the TP4 group are off this die)
  token   global argmax over all 129,280 logits (must equal the merged token of the die)

    python3 head_die_images.py --src <source root with tools/> --tiles tiles.txt --out OUT [--jobs N]
tiles.txt: "<INSTANCE> <row0> <ten>" per line (extracted from die.v).  Env DSROM_1M_SNAP / DSROM_1M_HEAD_REF as
tools/dsrom_1m_head.py.
"""
import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

H = None


def init(src):
    global H
    sys.path.insert(0, str(Path(src) / "tools"))
    import dsrom_1m_head as h  # noqa: E402
    h.setup_gate()
    H = h


def one(args):
    src, out, inst, r0 = args
    if H is None:
        init(src)
    ck = H.Ckpt(H.SNAP)
    m = H.gate.Mat(ck, "head", "bf16", H.BUNDLE_ROWS, H.K, r0=r0)
    u = np.asarray(m.u16, dtype=np.uint64)
    for q in range(4):
        H.write_macro(H.skewed_image(u[32 * q:32 * q + 32, :4096].reshape(H.NW, 16)), Path(out), f"{inst}a{q}")
    perm = np.array([32 * (n % 4) + n // 4 for n in range(H.BUNDLE_ROWS)])
    H.write_macro(H.skewed_image(u[perm, 4096:].reshape(H.NW, 16)), Path(out), f"{inst}b")
    return inst


def argmax_low(lg, base):
    b = int(np.argmax(lg))          # numpy argmax = first (lowest id) maximum; no NaN in the golden logits
    return base + b, lg[b]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--gold-only", action="store_true")
    a = ap.parse_args()
    init(a.src)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tiles = [ln.split() for ln in Path(a.tiles).read_text().split("\n") if ln.strip()]
    base = a.rank * H.ROWS_RANK
    xf, logits = H.golden_x()
    bits = lambda v: f"{int(H.G.bits(np.asarray([v], dtype=np.float32))[0]):08x}"
    held = sorted({base + int(r0) + k for _, r0, ten in tiles if ten.endswith("1") for k in range(H.BUNDLE_ROWS)})
    lo, hi = held[0], held[-1] + 1
    assert held == list(range(lo, hi)), "tile rows are not one contiguous range"
    lrow, lval = argmax_low(logits[lo:hi], lo)
    peers = []
    for r in range(4):
        if r == a.rank:
            continue
        prow, pval = argmax_low(logits[r * H.ROWS_RANK:(r + 1) * H.ROWS_RANK], r * H.ROWS_RANK)
        peers.append(dict(rank=r, row=prow, bits=bits(pval)))
    grow, gval = argmax_low(logits, 0)
    gold = dict(schema="opentallas.tokfunc_s81.head_die_gold.v1", rank=a.rank, rowbase=base, rows_held=[lo, hi],
                tiles=len(tiles), local=dict(row=lrow, bits=bits(lval)), peers=peers,
                token=dict(row=grow, bits=bits(gval)), golden_token_expected=H.GOLD_TOKEN,
                snap=str(H.SNAP), ref=str(H.REF))
    assert grow == H.GOLD_TOKEN, (grow, H.GOLD_TOKEN)
    x16 = (H.G.bits(xf).astype(np.uint32) >> 16).astype(np.uint64)

    def slices(xx, n):
        return "".join("".join(f"{int(v):04x}" for v in xx[16 * i:16 * i + 16][::-1]) + "\n" for i in range(n))
    (out / "xa.hex").write_text(slices(x16[:4096], 256))
    (out / "xb.hex").write_text(slices(x16[4096:], 64))
    # the 80 XB ring beats: beat g = K 64g .. 64g + 63 (64 BF16, lane k at [16k +: 16]), one hex line of 1024 b each
    (out / "xb_beats.hex").write_text("".join("".join(f"{int(v):04x}" for v in x16[64 * g:64 * g + 64][::-1]) + "\n"
                                              for g in range(80)))
    (out / "golden.json").write_text(json.dumps(gold, indent=1) + "\n")
    print(json.dumps(gold))
    if a.gold_only:
        return
    work = [(a.src, str(out), inst, base + int(r0)) for inst, r0, ten in tiles]
    with mp.Pool(a.jobs) as p:
        for i, inst in enumerate(p.imap_unordered(one, work)):
            if i % 25 == 0:
                print(f"images {i + 1}/{len(work)} {inst}", flush=True)
    (out / "IMAGES_DONE").write_text(f"{len(work)}\n")


if __name__ == "__main__":
    main()
