#!/usr/bin/env python3
"""One-stream all-reduce stage images for the Qwen3-8B ROM TP runtime (opt-in, default-off).

The pinned stage images split every 4,096-element all-reduce into two serialized
128-word descriptor segments (tools/hdc_qwen_fullshape_program*.py
split_collectives, AR_WORDS = 128): segment A = [layer instructions .., END]
over vector-memory words [v, v+128), then segment B = [END] over [v+128, v+256).
Each segment pays the collective's full fill/drain (2 x link LAT + fold), so an
all-reduce costs ~991 cycles at LAT 339 instead of ~620 as one stream.

This tool derives the one-stream image from a pinned image WITHOUT touching it:
each such pair becomes one all-reduce descriptor of 256 words (the 8-bit count
encodes 256 as 0; decoded only by rtl/rom/ot_qwen_tp_seq_w12.sv with
ENABLE_AR256=1) and segment B's lone END word is dropped; later program bases
are rebased.  Instructions are otherwise byte-identical, so the per-lane
rank-ordered fold ((p0+p1)+p2)+p3 and every other operation are unchanged
(the all-reduce is lane-wise; the split only partitioned the words).

The transform equals the generator's own AR_WORDS=256 output
(`--self-check` proves it on the W12 profile generator, with post-TP scales).
Large payload files are symlinked to the pinned image (read-only).

  qwen_rom_ar256_stage_images.py --stages PINNED_STAGES --out DIR [--only L0,L1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

K_END, K_AR = 0, 1
LINK = ("crom.hex", "matrix_int8.hex", "matrix_scale_bf16.hex")


def dec(d: int) -> dict:
    return {"kind": d & 3, "vw": (d >> 2) & 0xFF, "nw": (d >> 10) & 0xFF, "base": (d >> 32) & 0xFFFF,
            "rest": d & ~((0xFFFF << 32) | 0x3FFFF)}


def merge(words: list[str], desc: list[int]) -> tuple[list[str], list[int], int]:
    """Merge each (AR v,128 | AR v+128,128 over one END word) pair; returns (words, desc, merged)."""
    segs = []
    for i, d in enumerate(desc):
        end = dec(desc[i + 1])["base"] if i + 1 < len(desc) else len(words)
        segs.append([d, words[dec(d)["base"]:end]])
    out, i, merged = [], 0, 0
    while i < len(segs):
        a = dec(segs[i][0])
        if (i + 1 < len(segs) and a["kind"] == K_AR and a["nw"] == 128):
            b = dec(segs[i + 1][0])
            if not (b["kind"] == K_AR and b["nw"] == 128 and b["vw"] == a["vw"] + 128
                    and len(segs[i + 1][1]) == 1 and segs[i + 1][1][0] == segs[i][1][-1]
                    and a["rest"] == b["rest"]):
                raise SystemExit(f"segment {i}: 128-word all-reduce without its END-only continuation")
            out.append([segs[i][0] & ~(0xFF << 10), segs[i][1]])     # nw 256 encodes as 0
            merged += 1
            i += 2
            continue
        if a["kind"] == K_AR and a["nw"] == 128:
            raise SystemExit(f"segment {i}: unpaired 128-word all-reduce")
        out.append(segs[i])
        i += 1
    nwords, ndesc = [], []
    for d, ws in out:
        ndesc.append((d & ~(0xFFFF << 32)) | (len(nwords) << 32))
        nwords.extend(ws)
    return nwords, ndesc, merged


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def self_check() -> dict:
    """The transform of the generator's AR_WORDS=128 program equals its AR_WORDS=256 program."""
    os.environ.setdefault("QWEN_O4_GROUPS", "6144")
    os.environ.setdefault("QWEN_O4_TP", "4")
    import hdc_qwen_fullshape_program_w12 as FP
    res = {}
    for die in range(FP.TP):
        for scales in (None, [70000, 74096]):
            FP.AR_WORDS = 128
            a = FP.profile(die, post_scale_bases=scales)
            FP.AR_WORDS = 256
            b = FP.profile(die, post_scale_bases=scales)
            FP.AR_WORDS = 128
            w, d, n = merge(a["program_hex"], [int(x, 16) for x in a["descriptor_hex"]])
            ok = w == b["program_hex"] and [f"{x:016x}" for x in d] == b["descriptor_hex"]
            res[f"die{die}_scales{int(scales is not None)}"] = {"equal": ok, "merged": n,
                                                                "words": [len(a["program_hex"]), len(w)]}
            if not ok:
                raise SystemExit(f"self-check failed: die {die} scales {scales}")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only", default="", help="comma list of stage names to keep (default all)")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    report = {"schema": "opentallas.qwen-rom-ar256-stage-images.v1", "tool_sha256": sha(Path(__file__))}
    if args.self_check:
        report["self_check"] = self_check()
    if args.stages:
        keep = set(filter(None, args.only.split(",")))
        lines, stages = [], []
        for line in args.stages.read_text().splitlines():
            if not line.strip():
                continue
            name, *dirs, kv = line.split()
            if keep and name not in keep:
                continue
            nd = []
            for k, src in enumerate(map(Path, dirs)):
                dst = args.out / f"{name}-d{k}"
                dst.mkdir(parents=True, exist_ok=False)
                words = (src / "program.hex").read_text().split()
                desc = [int(x, 16) for x in (src / "segments.hex").read_text().split()]
                nw, ndsc, merged = merge(words, desc)
                (dst / "program.hex").write_text("".join(x + "\n" for x in nw))
                (dst / "segments.hex").write_text("".join(f"{x:016x}\n" for x in ndsc))
                for f in LINK:
                    os.symlink((src / f).resolve(), dst / f)
                stages.append({"stage": name, "die": k, "source_dir": str(src),
                               "source_program_sha256": sha(src / "program.hex"),
                               "source_segments_sha256": sha(src / "segments.hex"),
                               "program_sha256": sha(dst / "program.hex"),
                               "segments_sha256": sha(dst / "segments.hex"),
                               "words": [len(words), len(nw)], "segments": [len(desc), len(ndsc)],
                               "allreduces_merged": merged})
                nd.append(str(dst))
            lines.append(" ".join([name, *nd, kv]))
        (args.out / "stages.txt").write_text("".join(x + "\n" for x in lines))
        report["stages"] = stages
        (args.out / "ar256_images.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "stages"}, indent=1))


if __name__ == "__main__":
    main()
