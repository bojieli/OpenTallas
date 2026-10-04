#!/usr/bin/env python3
"""Asynchronous-collective stage images for the Qwen3-8B ROM TP runtime (opt-in, default-off).

Dataflow level 5 (collective fusion, AGENTS.md), two independent transforms of
a stage image that leave the pinned image untouched:

--fuse  (level 1+5) the post-all-reduce epilogue in ONE stream-unit op.  The
        pinned program scales the rank-folded o/down sum and adds the residual
        as two ops (tools/hdc_qwen_fullshape_program_w12.py insert_post_tp_scales,
        then the residual op of tools/hdc_program.build_program):
            S: T1 = fl(T1 x s)              MC_C, s = constant ROM
            R: X  = fl(X + T1), r = sum X^2 AD_C (+ the reducer)
        F replaces the pair: the multiply stage (MA_AB, b = s from the constant
        ROM) then the add stage (AD_C, c = X) of the same element pipeline, with
        R's reducer and destination, so X' = fl(fl(T1 x s) + X): the golden's two
        roundings, no FMA (tools/qwen_fused_epilogue_gate.py proves it on the
        production unit).  T1 then keeps the unscaled sum; the tool checks that
        nothing reads T1 before the engine rewrites it.
--cut   (level 5) a cut-through all-reduce: descriptor bit 20, decoded only by
        rtl/rom/ot_qwen_tp_seq_async_w12.sv with ASYNC_COLL = 1 (the segment's
        words are sent as the matrix engine writes them).  The tool sets the bit
        only where the program contract holds: the segment ends [.., ME, END]
        with END's barrier; that ME op writes every element of the region
        exactly once; no other ME op of the segment writes into it; and any
        stream-unit write into it is followed by a barrier before that ME op.

The per-word rank-order fold ((p0+p1)+p2)+p3, the word tags and every other
instruction are unchanged.  Program bases are rebased after a fused pair.

  qwen_rom_async_coll.py --stages STAGES --out DIR [--only L0,L1] [--fuse] [--cut] [--self-check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("QWEN_O4_GROUPS", "6144")
os.environ.setdefault("QWEN_O4_TP", "4")
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402

K_END, K_AR = 0, 1
CUT_BIT = 20
LINK = ("crom.hex", "matrix_int8.hex", "matrix_scale_bf16.hex")
W, IL = I.W_LANES, I.INTERLEAVE
GROUPS = int(os.environ["QWEN_O4_GROUPS"])
TMAX = 8192
T1, X = 0, 4096                     # vm_map() of tools/hdc_qwen_fullshape_program_w12.py
H = 4096


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dec_desc(d: int) -> dict:
    return {"kind": d & 3, "vw": (d >> 2) & 0xFF, "nw": ((d >> 10) & 0xFF) or (256 if d & 3 == K_AR else 0),
            "base": (d >> 32) & 0xFFFF}


def split_segments(words: list[str], desc: list[int]) -> list[list[dict]]:
    segs = []
    for i, d in enumerate(desc):
        end = dec_desc(desc[i + 1])["base"] if i + 1 < len(desc) else len(words)
        segs.append([QI.decode_instruction(int(x, 16)) for x in words[dec_desc(d)["base"]:end]])
    return segs


def join_segments(segs: list[list[dict]], desc: list[int]) -> tuple[list[str], list[int]]:
    words, nd = [], []
    for d, ins in zip(desc, segs):
        nd.append((d & ~(0xFFFF << 32)) | (len(words) << 32))
        words.extend(f"{QI.encode_instruction(f):0256x}" for f in ins)
    return words, nd


def nz(f: dict, keys) -> bool:
    return all(f[k] == 0 for k in keys)


# ---- level 1+5: the fused epilogue -----------------------------------------------------------------------
def is_scale(f):
    return (f["unit"] == I.UNIT_SU and f["su_nout"] == 1 and f["su_nin"] == H and f["a_src"] == 0
            and f["a_base"] == T1 and f["a_si"] == 1 and f["c_src"] == I.SRC_ALT and f["c_si"] == 1
            and f["mc"] == I.MC_C and f["dst"] == I.DST_VM and f["d_base"] == T1 and f["d_si"] == 1
            and nz(f, ("chase", "chase_n", "wait_me", "wait_su", "chase_rows", "su_d_nin", "a_so", "a_d", "b_src",
                       "b_base", "b_so", "b_si", "b_d", "c_so", "c_d", "ma", "mb", "ad", "sfu", "md", "d_so", "d_d",
                       "red", "r_base", "r_so", "red_sq", "imm1", "imm2")))


def is_residual(f):
    return (f["unit"] == I.UNIT_SU and f["su_nout"] == 1 and f["su_nin"] == H and f["a_src"] == 0
            and f["a_base"] == X and f["a_si"] == 1 and f["c_src"] == I.SRC_VM and f["c_base"] == T1
            and f["c_si"] == 1 and f["ad"] == I.AD_C and f["dst"] == I.DST_VM and f["d_base"] == X
            and f["d_si"] == 1
            and nz(f, ("chase", "chase_n", "wait_me", "chase_rows", "su_d_nin", "a_so", "a_d", "b_src", "b_base",
                       "b_so", "b_si", "b_d", "c_so", "c_d", "ma", "mb", "sfu", "mc", "md", "d_so", "d_d",
                       "imm1", "imm2")))


def fused(s: dict, r: dict) -> dict:
    f = dict(r)
    f.update(barrier=s["barrier"] | r["barrier"], wait_su=s["wait_su"] | r["wait_su"],
             a_base=T1, a_si=1, ma=I.MA_AB, b_src=I.SRC_ALT, b_base=s["c_base"], b_si=1,
             c_src=I.SRC_VM, c_base=X, c_si=1, ad=I.AD_C)
    return f


def reads_t1(f: dict) -> bool:
    """Does the op use (hdc_program.Machine semantics) a VM operand whose stream starts inside T1?"""
    if f["unit"] == I.UNIT_SU:
        used = {"a": f["a_src"] == 0,
                "b": f["b_src"] == I.SRC_VM and (f["ma"] == I.MA_AB or f["md"] == I.MD_B or f["ad"] == I.AD_NEGB),
                "c": f["c_src"] == I.SRC_VM and (f["mb"] != I.MB_OFF or f["ad"] == I.AD_C or f["mc"] == I.MC_C)}
        return any(u and f[f"{s}_base"] < T1 + H for s, u in used.items())
    if f["unit"] == I.UNIT_ME:
        return f["me_xbase"] < T1 + H
    return False


def fuse_epilogues(segs: list[list[dict]]) -> tuple[list[list[dict]], int]:
    out, n = [], 0
    for ins in segs:
        new, i = [], 0
        while i < len(ins):
            if i + 1 < len(ins) and is_scale(ins[i]) and is_residual(ins[i + 1]):
                new.append(fused(ins[i], ins[i + 1]))
                n += 1
                i += 2
            else:
                if is_scale(ins[i]):
                    raise SystemExit("post-TP scale op without its residual op")
                new.append(ins[i])
                i += 1
        out.append(new)
    # T1 keeps the unscaled sum: nothing may read T1 before the engine rewrites it (whole stage, in order)
    flat = [f for ins in out for f in ins]
    for k, f in enumerate(flat):
        if f["unit"] == I.UNIT_SU and f["ma"] == I.MA_AB and f["b_src"] == I.SRC_ALT and f["a_base"] == T1 \
                and f["c_base"] == X and f["d_base"] == X:
            for g in flat[k + 1:]:
                if g["unit"] == I.UNIT_ME and g["me_oen"] and g["me_obase"] == T1 // W:
                    break
                if reads_t1(g):
                    raise SystemExit("an op reads T1 after a fused epilogue")
    return out, n


# ---- level 5: the cut-through contract -------------------------------------------------------------------
def me_writes(f: dict, strict: bool = False) -> dict:
    """{word: lane mask} the ME op writes (tools/hdc_program.Machine.me addressing; KV rounds at full context)."""
    if not f["me_oen"]:
        return {}
    if f["me_d_obase"]:
        raise SystemExit("ME op with a position-dependent output base in a cut-through segment")
    split = f["me_split"]
    per_round = GROUPS >> split
    tiles = f["me_tiles"]
    if f["me_d_tiles"] == I.DYN_TTILES:
        tiles = f["me_tiles"] + (TMAX - 1) // (W * per_round) + 1
    elif f["me_d_tiles"]:
        raise SystemExit("unexpected dynamic tile count")
    n = f["me_nout"] + (TMAX if f["me_d_nout"] else 0)      # DYN_T = pos + 1 <= TMAX
    r, q, j, l = (a.reshape(-1) for a in np.meshgrid(np.arange(tiles), np.arange(per_round), np.arange(IL),
                                                     np.arange(W), indexing="ij"))
    t = r * per_round + q
    keep = ((t * IL + j) * W + l < n) if f["me_mmode"] == 0 else (t * W + l < n)
    word = (f["me_obase"] + t * f["me_ots"] + j * f["me_ojs"])[keep]
    out: dict = {}
    for w, ln in zip(word.tolist(), l[keep].tolist()):
        m = out.get(w, 0)
        if strict and (m >> ln) & 1:
            raise SystemExit("ME op writes one element twice")
        out[w] = m | (1 << ln)
    return out


def su_writes_region(f: dict, lo: int, hi: int) -> bool:
    """Element range check of a stream-unit op's VM destination and reducer slots against [lo, hi)."""
    if f["unit"] != I.UNIT_SU:
        return False
    n_out, n_in = f["su_nout"], f["su_nin"]
    if f["dst"] == I.DST_VM:
        span = [f["d_base"] + o * f["d_so"] + i * f["d_si"] for o in (0, n_out - 1) for i in (0, max(n_in - 1, 0))]
        if f["d_d"] or (min(span) < hi and max(span) >= lo):
            return True
    if f["red"]:
        rs = [f["r_base"], f["r_base"] + (n_out - 1) * f["r_so"]]
        if min(rs) < hi and max(rs) >= lo:
            return True
    return False


def cut_ok(ins: list[dict], vw: int, nw: int) -> str | None:
    """None if the cut-through contract holds for this all-reduce segment, else the reason."""
    if len(ins) < 2 or ins[-1]["unit"] != I.UNIT_END or not ins[-1]["barrier"]:
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
        if su_writes_region(f, lo, hi) and not any(g["barrier"] for g in ins[k + 1:-2]):
            return f"stream op {k} writes the region without a barrier before the last ME op"
    return None


def transform(words: list[str], desc: list[int], fuse: bool, cut: bool) -> tuple[list[str], list[int], dict]:
    segs = split_segments(words, desc)
    info = {"fused": 0, "cut": 0, "not_cut": []}
    if fuse:
        segs, info["fused"] = fuse_epilogues(segs)
    nd = list(desc)
    if cut:
        for i, (d, ins) in enumerate(zip(desc, segs)):
            dd = dec_desc(d)
            if dd["kind"] != K_AR:
                continue
            why = cut_ok(ins, dd["vw"], dd["nw"])
            if why is None:
                nd[i] = d | (1 << CUT_BIT)
                info["cut"] += 1
            else:
                info["not_cut"].append({"segment": i, "reason": why})
    w, nd = join_segments(segs, nd)
    return w, nd, info


# ---- ISA-golden equivalence of the actual fused words ------------------------------------------------------
def isa_equivalence(words: list[str], desc: list[int], rng) -> dict:
    """Execute every (S, R) pair of the image and its fused op in hdc_program.Machine.su on random and
    adversarial data; X and the reducer slot must be bit-identical."""
    segs = split_segments(words, desc)
    pairs = [(ins[i], ins[i + 1]) for ins in segs for i in range(len(ins) - 1)
             if is_scale(ins[i]) and is_residual(ins[i + 1])]
    res = []
    for s, r in pairs:
        f = fused(s, r)
        for trial in range(4):
            m = object.__new__(P.Machine)
            hi = max(s["c_base"], r["r_base"]) + H + 16
            vm = np.zeros(max(hi, 1 << 15), dtype=np.float32)
            vm[T1:T1 + H] = rng.uniform(-3000, 3000, H).astype(np.float32)
            vm[X:X + H] = rng.normal(0, 2, H).astype(np.float32)
            crom = np.zeros((s["c_base"] + H, 2), dtype=np.float32)
            crom[s["c_base"]:, 0] = (rng.uniform(0.5, 2, H) * 2.0 ** rng.integers(-14, -4, H)).astype(np.float32)
            if trial:                                  # cancellations, signed zeros, subnormals
                idx = rng.choice(H, 600, replace=False)
                a, b = idx[:200], idx[200:400]
                vm[X + a] = -(vm[T1 + a] * crom[s["c_base"] + a, 0])
                vm[T1 + b] = np.float32(-0.0) if trial == 1 else np.float32(1e-41)
                vm[X + idx[400:]] = np.float32(-0.0)
            m.vm, m.crom, m.kv = vm.copy(), crom, np.zeros(1, dtype=np.float32)
            dyn = [0] * 8
            m.su(s, dyn)
            m.su(r, dyn)
            a_vm = m.vm
            m2 = object.__new__(P.Machine)
            m2.vm, m2.crom, m2.kv = vm.copy(), crom, np.zeros(1, dtype=np.float32)
            m2.su(f, dyn)
            ok_x = bool((G.bits(a_vm[X:X + H]) == G.bits(m2.vm[X:X + H])).all())
            ok_r = bool(G.bits(np.float32(a_vm[r["r_base"]])) == G.bits(np.float32(m2.vm[r["r_base"]])))
            res.append({"scale_base": s["c_base"], "trial": trial, "x_equal": ok_x, "r_equal": ok_r})
    return {"pairs": len(pairs), "trials": res, "all_equal": all(x["x_equal"] and x["r_equal"] for x in res)}


def self_check() -> dict:
    """On the W12 profile generator (post-TP scales, AR_WORDS 256): the fuse finds one pair per all-reduce, the
    cut contract holds on every all-reduce segment, the descriptor round trip is exact, and the fused words
    are ISA-equivalent to the pairs."""
    import hdc_qwen_fullshape_program_w12 as FP
    FP.AR_WORDS = 256
    out = {}
    for die in range(FP.TP):
        a = FP.profile(die, post_scale_bases=[70000, 74096])
        desc = [int(x, 16) for x in a["descriptor_hex"]]
        nar = sum(dec_desc(d)["kind"] == K_AR for d in desc)
        w, d, info = transform(a["program_hex"], desc, True, True)
        w0, d0, _ = transform(a["program_hex"], desc, False, False)
        eq = isa_equivalence(a["program_hex"], desc, np.random.default_rng(die))
        ok = (info["fused"] == nar and info["cut"] == nar and w0 == a["program_hex"] and d0 == desc
              and len(w) == len(a["program_hex"]) - nar and eq["all_equal"])
        out[f"die{die}"] = {"allreduces": nar, "fused": info["fused"], "cut": info["cut"], "not_cut": info["not_cut"],
                            "identity_round_trip": w0 == a["program_hex"] and d0 == desc,
                            "words": [len(a["program_hex"]), len(w)], "isa_equivalence": eq["all_equal"], "ok": ok}
        if not ok:
            raise SystemExit(f"self-check failed: die {die}: {out[f'die{die}']}")
    FP.AR_WORDS = 128
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only", default="", help="comma list of stage names to keep (default all)")
    ap.add_argument("--fuse", action="store_true")
    ap.add_argument("--cut", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    report = {"schema": "opentallas.qwen-rom-async-coll-stage-images.v1", "tool_sha256": sha(Path(__file__)),
              "fuse": args.fuse, "cut": args.cut}
    if args.self_check:
        report["self_check"] = self_check()
    if args.stages:
        keep = set(filter(None, args.only.split(",")))
        lines, stages = [], []
        rng = np.random.default_rng(20261003)
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
                nw, ndsc, info = transform(words, desc, args.fuse, args.cut)
                if any(dec_desc(d)["kind"] == K_AR and (d >> 10) & 0xFF != 0 for d in desc):
                    raise SystemExit(f"{src}: expects one-stream (256-word) all-reduce images")
                (dst / "program.hex").write_text("".join(x + "\n" for x in nw))
                (dst / "segments.hex").write_text("".join(f"{x:016x}\n" for x in ndsc))
                for f in LINK:
                    os.symlink((src / f).resolve(), dst / f)
                eq = isa_equivalence(words, desc, rng) if args.fuse else None
                if eq is not None and not eq["all_equal"]:
                    raise SystemExit(f"{src}: fused op not ISA-equivalent")
                stages.append({"stage": name, "die": k, "source_dir": str(src),
                               "source_program_sha256": sha(src / "program.hex"),
                               "source_segments_sha256": sha(src / "segments.hex"),
                               "program_sha256": sha(dst / "program.hex"),
                               "segments_sha256": sha(dst / "segments.hex"),
                               "words": [len(words), len(nw)], "segments": len(desc),
                               "fused": info["fused"], "cut": info["cut"], "not_cut": info["not_cut"],
                               "isa_equivalence_pairs": eq["pairs"] if eq else 0})
                nd.append(str(dst))
            lines.append(" ".join([name, *nd, kv]))
        (args.out / "stages.txt").write_text("".join(x + "\n" for x in lines))
        report["stages"] = stages
        (args.out / "async_coll_images.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "stages"}, indent=1))


if __name__ == "__main__":
    main()
