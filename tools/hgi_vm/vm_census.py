#!/usr/bin/env python3
"""VM traffic census of HGI-1 token programs (hgi-1010/f, VM architecture).

For every record: DMA.LOAD -> VM (HBM source bytes by source fmt, VM FP32 words written), and every other unit's VM
operand words (read: A B C D I; written: O R).  n_sel / DYN counts are resolved with --ctx (POS1 = ctx).  Qwen is built
from the compiler (program(), LOOP counts expanded); DS from an hgi_e2e export's ds_program.json (hex records).
"""
import argparse, json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from hgi_sim.records import decode_one, MDesc  # noqa: E402

ESZ = {"FP32": 4, "U32": 4, "BF16": 2, "FP8E4M3": 1, "INT8": 1, "UE8M0": 1, "FP4E2M1": 0.5}
READS, WRITES = ("A", "B", "C", "D", "I"), ("O", "R")


def elems(d: MDesc, ctx):
    n = d.n
    if d.n_sel:
        n = ctx if d.n_sel != 63 else d.n or 1
    return n * max(d.m, 1)


def census(recs_with_count, ctx):
    dma = collections.defaultdict(lambda: dict(n=0, hbm_B=0, vm_words=0, max_hbm_B=0, misaligned_n=0,
                                               misaligned_hbm_B=0))
    unit = collections.defaultdict(lambda: dict(rd_words=0, wr_words=0))
    big = []
    for r, cnt in recs_with_count:
        if r.unit == "DMA" and r.op == "LOAD" and r.desc.get("O") is not None and r.desc["O"].space == "VM":
            a, o = r.desc["A"], r.desc["O"]
            e = elems(a, ctx)
            k = a.fmt
            dma[k]["n"] += cnt
            dma[k]["hbm_B"] += cnt * e * ESZ[a.fmt]
            dma[k]["vm_words"] += cnt * e
            dma[k]["max_hbm_B"] = max(dma[k]["max_hbm_B"], e * ESZ[a.fmt])
            # VM-512 full-rate rule: each raw sector's expansion stays in one tile -> O base (and O row stride when
            # m > 1) a multiple of 8 * e words, e = 4 / esz (FP32 8, BF16 16, FP8 / INT8 32 words)
            al = int(8 * 4 / ESZ[a.fmt])
            if o.base % al or (max(o.m, 1) > 1 and o.stride % al):
                dma[k]["misaligned_n"] += cnt
                dma[k]["misaligned_hbm_B"] += cnt * e * ESZ[a.fmt]
            big.append((e * ESZ[a.fmt], a.fmt, r.tag, cnt))
            continue
        u = f"{r.unit}.{r.op}"
        for k, d in r.desc.items():
            if d.space != "VM":
                continue
            w = elems(d, ctx) * cnt
            unit[u]["rd_words" if k in READS else "wr_words"] += w
    big.sort(reverse=True)
    return dict(dma_load_to_vm=dma, units=unit, largest_loads=[dict(hbm_B=b, fmt=f, tag=t, count=c) for b, f, t, c in big[:12]])


def qwen(ctx):
    from hgi_sim import qwen_compiler as QC
    cfg = json.load(open(ROOT / "compiler/models/qwen3-8b/config.json"))
    g = QC.Geometry(cfg, ctx)
    md = QC.qwen_params(cfg)
    recs = QC.program(g, md, g.L)
    out, mult = [], 1
    for r in recs:
        if r.unit == "CTL" and r.op == "LOOP":
            mult = r.param & 0xFFFF; continue
        if r.unit == "CTL" and r.op == "ENDLOOP":
            mult = 1; continue
        out.append((r, mult))
    return out


def ds(path):
    p = json.load(open(path))
    out = []
    for lay in p["layers"]:
        for rr in lay["records"]:
            r, _ = decode_one(bytes.fromhex(rr["hex"]), 0)
            r.tag = rr.get("tag", "")
            out.append((r, 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["qwen", "ds"])
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--program", help="ds: ds_program.json")
    a = ap.parse_args()
    recs = qwen(a.ctx) if a.model == "qwen" else ds(a.program)
    print(json.dumps(census(recs, a.ctx), indent=1, default=dict))


if __name__ == "__main__":
    main()
