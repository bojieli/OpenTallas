#!/usr/bin/env python3
"""Cut-through (asynchronous collective) images for the Qwen ROM system top's reduced TP-4 dies.

tools/qwen_rom_async_coll.py (claude/qwen-async-collective-20261003) sets descriptor bit 20 on the full-shape W12
images; this tool applies the same program contract to the reduced tools/hdc_program.py --tp images that the system
top runs (it imports nothing from the full-shape tools, whose import would switch tools/hdc_golden.py to the
full-shape configuration).  A segment's all-reduce is cut through only when:
  * the segment ends [.., ME, END] and END carries a barrier;
  * that ME op writes every element of the region [vw, vw + nw) words exactly once;
  * no other ME op of the segment writes into the region;
  * any stream-unit write into the region is followed by a barrier before that ME op.
Instruction words, programs and every other file are copied unchanged; only desc_d*.hex gains bit 20.

    HDC_SU_WIDTH=1 python3 tools/qwen_rom_sys_async_images.py --img IMG --out IMG_ASYNC
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("HDC_SU_WIDTH", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402

CUT_BIT = 20
W, IL = I.W_LANES, I.INTERLEAVE


def me_writes(f: dict, strict: bool = False) -> dict:
    """{word: lane mask} the ME op writes (hdc_program.Machine.me addressing, KV rounds at full context)."""
    g = lambda k: f.get(k, 0)  # noqa: E731
    if not g("me_oen"):
        return {}
    if g("me_d_obase"):
        raise SystemExit("ME op with a position-dependent output base")
    per_round = P.GR >> g("me_split")
    tiles = g("me_tiles")
    if g("me_d_tiles") == getattr(I, "DYN_TTILES", -1):
        tiles = g("me_tiles") + (P.TMAX - 1) // (W * per_round) + 1
    elif g("me_d_tiles"):
        raise SystemExit("unexpected dynamic tile count")
    n = g("me_nout") + (P.TMAX if g("me_d_nout") else 0)
    r, q, j, l = (a.reshape(-1) for a in np.meshgrid(np.arange(tiles), np.arange(per_round), np.arange(IL),
                                                     np.arange(W), indexing="ij"))
    t = r * per_round + q
    keep = ((t * IL + j) * W + l < n) if g("me_mmode") == 0 else (t * W + l < n)
    word = (g("me_obase") + t * g("me_ots") + j * g("me_ojs"))[keep]
    out: dict = {}
    for w, ln in zip(word.tolist(), l[keep].tolist()):
        m = out.get(w, 0)
        if strict and (m >> ln) & 1:
            raise SystemExit("ME op writes one element twice")
        out[w] = m | (1 << ln)
    return out


def su_writes_region(f: dict, lo: int, hi: int) -> bool:
    g = lambda k: f.get(k, 0)  # noqa: E731
    if f["unit"] != I.UNIT_SU:
        return False
    n_out, n_in = max(g("su_nout"), 1), g("su_nin")
    if g("dst") == I.DST_VM:
        span = [g("d_base") + o * g("d_so") + i * g("d_si") for o in (0, n_out - 1) for i in (0, max(n_in - 1, 0))]
        if g("d_d") or (min(span) < hi and max(span) >= lo):
            return True
    if g("red"):
        rs = [g("r_base"), g("r_base") + (n_out - 1) * g("r_so")]
        if min(rs) < hi and max(rs) >= lo:
            return True
    return False


def cut_ok(ins: list, vw: int, nw: int):
    if len(ins) < 2 or ins[-1]["unit"] != I.UNIT_END or not ins[-1].get("barrier"):
        return "segment does not end in a barrier END"
    last = ins[-2]
    if last["unit"] != I.UNIT_ME:
        return "the op before END is not a matrix-engine op"
    region = set(range(vw, vw + nw))
    lw = me_writes(last, strict=True)
    if any(lw.get(w, 0) != 0xFFFF for w in region):
        return "the last ME op does not write every region element"
    lo, hi = vw * W, (vw + nw) * W
    for k, f in enumerate(ins[:-2]):
        if f["unit"] == I.UNIT_ME and region & set(me_writes(f)):
            return f"ME op {k} also writes the region"
        if su_writes_region(f, lo, hi) and not any(x.get("barrier") for x in ins[k + 1:-2]):
            return f"stream op {k} writes the region without a barrier before the last ME op"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--img", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    model = G.Model(P.GR, 4)
    lays = P.tp_layouts(model, 4)
    a.out.mkdir(parents=True, exist_ok=True)
    for f in a.img.iterdir():
        if f.is_file():
            shutil.copy2(f, a.out / f.name)
    report = {}
    for d, lay in enumerate(lays):
        prog = P.build_program(lay)
        words, desc = P.encode_segments(prog)
        orig = [int(x, 16) for x in (a.img / f"desc_d{d}.hex").read_text().split()]
        if orig != desc:
            raise SystemExit(f"die {d}: rebuilt descriptors differ from {a.img}/desc_d{d}.hex")
        nd, info = list(desc), []
        for i, (ins, (kind, vw, nw, row0)) in enumerate(P.segments(prog)):
            if kind != 1:
                continue
            why = cut_ok(ins, vw, nw)
            if why is None:
                nd[i] |= 1 << CUT_BIT
            info.append(dict(segment=i, vw=vw, nw=nw, cut=why is None, reason=why))
        (a.out / f"desc_d{d}.hex").write_text("".join(f"{x:016x}\n" for x in nd))
        report[f"die{d}"] = info
    (a.out / "async_images.json").write_text(json.dumps(report, indent=1) + "\n")
    cut = sum(x["cut"] for v in report.values() for x in v)
    total = sum(len(v) for v in report.values())
    print(f"cut-through all-reduces: {cut} of {total}")
    for k, v in report.items():
        for x in v:
            if not x["cut"]:
                print(k, x)


if __name__ == "__main__":
    main()
