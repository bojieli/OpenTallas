#!/usr/bin/env python3
"""MR-5 deep order at the SHIPPED shape: the production TP-4 compressor's ring-8 instructions, ISA-executed.

The production full-shape compiler (tools/w11_dsrom_full_tp_program.py FullLayerBuilder) emits, for each ratio-2
KV source layer (2, 8, 14), the compressor record ring: a 1,024-element (kv | gate) record per position in RING8
(8 records, chunk-interleaved so the core's DYN25 = (pos mod 8) * 4 is the record offset), the odd position's
partner copy PREV <- record (pos - 1), and the pair pooling ops reading PREV | CPROJ.  This tool executes exactly
those emitted SU instructions -- encoded to the FULL 2048-bit word and decoded back -- with the full-shape DYN table
(tools/v41_fullshape_isa.full_dyn = ot_hdc_core_v41x.sv FULL_SHAPE with ROLLBACK_RING_DYN = 1) and the full-shape
SU semantics (v41_fullshape_isa.Rank.su), on one rank's vector memory (2^19 elements, written-ness tracked).  The two
projection all-gathers are the only non-SU producers: the harness writes each position's CPROJ (kv | gate, FP32)
where the gathers land.

Schedules (the MR-5 probe's, tools/mtp_rollback_isa_probe.py): CLEAN = positions 0..N-1; DEEP = 0..c-1, c with a
corrupted record (the rejected draft), S squashed successors c+1..c+S, then c..N-1 re-issued.  PASS: at every odd
position of the re-issued run the pooled pair (POOL, BF16) and its sum of squares (SS) equal the CLEAN run bit for
bit, CLEAN equals the golden pooling (hdc_golden_v41.Model.compressor arithmetic) bit for bit, and no read touches
an unwritten element.  The ring-2 build (the legacy two-record allocation, DYN18) is the negative control.

    python3 tools/mtp_ring8_fullshape_isa.py --output results/rtl/mtp_lead_20261009/ring8_fullshape/record.json
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_dsrom_full_tp_program as F  # noqa: E402
import v41_fullshape_isa as FI  # noqa: E402
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

I = F.I
HD = F.R.SHIPPED["hd"]
VM = 1 << 19


class Rank(FI.Rank):
    """v41_fullshape_isa.Rank without the die images: vector memory, written-ness and the DYN table only."""

    def __init__(self):  # noqa: D107  (the parent loads images; nothing here needs them)
        self.vm = np.zeros(VM, dtype=np.float32)
        self.ok = np.zeros(VM, dtype=bool)
        self.unwritten = []
        self.stores = None
        self.dyn = None


def compressor_ops(L, entries):
    """The scheduled layer-L program's compressor SU / COLL words up to the pooled pair, round-tripped through
    the FULL encoding."""
    F.RING_ENTRIES = entries
    b = F.FullLayerBuilder(L)
    prog = b.build_layer()
    v = b.V
    ops = [f for f in prog if f["_tag"].startswith(f"L{L}.compressor") and f["unit"] in (I.UNIT_SU, I.UNIT_COLL)]
    last = max(i for i, f in enumerate(ops) if f["unit"] == I.UNIT_SU and f.get("red") and
               f.get("r_base") == v["SS"] and v["POOL"] <= f.get("o_base", -1) < v["POOL"] + HD)
    ops = ops[:last + 1]
    dec, words = [], []
    for f in ops:
        clean = {k: x for k, x in f.items() if not k.startswith("_")}
        w = I.encode(full_shape=True, **clean)
        words.append(format(w, "0512x"))
        g = I.decode(w, full_shape=True)
        g["_tag"] = f["_tag"]
        dec.append(g)
    return b, dec, hashlib.sha256("".join(words).encode()).hexdigest()


def record(pos, tok):
    rng = np.random.default_rng(1_000_003 * pos + 7919 * tok + 17)
    kv = (rng.standard_normal(HD)).astype(np.float32)
    sc = (rng.standard_normal(HD) * 3).astype(np.float32)
    return kv, sc


def golden_pool(r0, r1):
    """hdc_golden_v41.Model.compressor, ratio 2, up to (and including) to_bf16(pooled); plus its sum of squares."""
    kvs, scs = np.stack([r0[0], r1[0]]), np.stack([r0[1], r1[1]])
    m = np.max(scs, axis=0)
    e = V.exp(V.add(scs, V.neg(m)))
    p = V.div(e, V.seqsum(list(e))[None, :])
    pooled = G.to_bf16(V.seqsum([V.mul(kvs[i], p[i]) for i in range(2)]))
    return pooled


def run(b, ops, jobs):
    rk = Rank()
    v = b.V
    out = {}
    for pos, tok in jobs:
        rk.dyn = FI.full_dyn(pos)
        kv, sc = record(pos, tok)
        for f in ops:
            if f["unit"] == I.UNIT_COLL:
                rk.write(f["coll_dst"], kv if f["_tag"].endswith("kv_projection_gather") else sc)
                continue
            if f["pred"] == I.PRED_ODD and not pos & 1:
                continue
            assert f["pred"] in (I.PRED_ALWAYS, I.PRED_ODD), f["_tag"]
            rk.su(f, 0, [])
        if pos & 1:     # the last occurrence of a position wins (the re-issued run)
            out[pos] = (G.bits(rk.vm[v["POOL"]:v["POOL"] + HD]).copy(), int(G.bits(rk.vm[v["SS"]:v["SS"] + 1])[0]))
    return out, rk


def case(b, ops, osha, L, entries, c, S, N):
    clean = [(p, 0) for p in range(N)]
    deep = clean[:c] + [(c, 1)] + clean[c + 1:c + 1 + S] + clean[c:]
    co, crk = run(b, ops, clean)
    do, drk = run(b, ops, deep)
    golden = all(np.array_equal(co[p][0], G.bits(golden_pool(record(p - 1, 0), record(p, 0)))) for p in co)
    mism = [p for p in range(c, N) if p & 1 and (not np.array_equal(co[p][0], do[p][0]) or co[p][1] != do[p][1])]
    unw = len(crk.unwritten) + len(drk.unwritten)
    return dict(layer=L, ring_entries=entries, corrected=c, successors=S, positions=N, ops_sha256=osha,
                clean_equals_golden=bool(golden), mismatching_positions=mism, unwritten_reads=unw,
                passed=bool(golden and not mism and not unw))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--positions", type=int, default=24)
    a = ap.parse_args()
    F.G.set_arith("chunk8")
    F.G.set_fuse("")
    old_lanes, old_entries = I.SU_LANES, F.RING_ENTRIES
    I.SU_LANES = 8              # build_program's setting
    rows, opsinfo = [], {}
    try:
        for L in (2, 8, 14):
            for entries in (8, 2):
                b, ops, osha = compressor_ops(L, entries)
                opsinfo[f"L{L}_ring{entries}"] = dict(words=len(ops), sha256=osha,
                                                      tags=[f["_tag"] for f in ops if f["unit"] == I.UNIT_SU])
                for c in (3, 4, 9, 10):
                    for S in range(1, 8):
                        r = case(b, ops, osha, L, entries, c, S, a.positions)
                        rows.append(r)
                        print(L, entries, c, S, "PASS" if r["passed"] else "FAIL", r["mismatching_positions"][:4],
                              flush=True)
    finally:
        I.SU_LANES, F.RING_ENTRIES = old_lanes, old_entries
    r8 = [r for r in rows if r["ring_entries"] == 8]
    r2 = [r for r in rows if r["ring_entries"] == 2]
    contract = [r for r in r8 if r["successors"] <= 6]
    res = dict(schema="opentallas.mtp-ring8-fullshape-isa.v1",
               shape="deepseek-v4.1-flash SHIPPED, TP 4, hd 512 (one rank's compressor; the record is replicated)",
               compiler="tools/w11_dsrom_full_tp_program.py FullLayerBuilder (production TP-4 full-shape emitter)",
               semantics="v41_fullshape_isa.Rank.su + full_dyn (ot_hdc_core_v41x FULL_SHAPE, ROLLBACK_RING_DYN 1)",
               ring8_contract="corrected position c re-issued after S <= 6 squashed successors (7 positions in "
                              "flight); at S = 7 an odd c's partner record c - 1 = c + 7 (mod 8) is overwritten",
               ring8_contract_cases=len(contract), ring8_contract_pass=all(r["passed"] for r in contract),
               ring8_s7=[dict(layer=r["layer"], corrected=r["corrected"], passed=r["passed"]) for r in r8
                         if r["successors"] == 7],
               ring2_cases=len(r2), ring2_failed=sum(not r["passed"] for r in r2),
               ring2_odd_corrected_all_fail=all(not r["passed"] for r in r2 if r["corrected"] & 1),
               clean_equals_golden_all=all(r["clean_equals_golden"] for r in rows),
               programs=opsinfo, rows=rows)
    res["pass"] = bool(res["ring8_contract_pass"] and res["ring2_odd_corrected_all_fail"]
                       and res["clean_equals_golden_all"])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(res, indent=1) + "\n")
    print("pass" if res["pass"] else "FAIL", {k: x for k, x in res.items() if k not in ("rows", "programs")})
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
