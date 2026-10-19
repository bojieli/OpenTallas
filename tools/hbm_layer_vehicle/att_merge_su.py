#!/usr/bin/env python3
"""HBM-ATTGAP (10-19): the ON-DIE cross-SM ATT.PV merge -- SU lane-store pairwise tree -- benched on the real N512 SU.

Gap (VEH-ATT 10-19): the PV nodes of the 10 attention SMs (DS T640, d4g W2 split) were merged in Python; no on-die unit
owned the merge.  The golden (tools/hgi_sim/lib.py att_pv = csum8 over positions: chunk sums of 8, then a +0-padded
pairwise tree over next_pow2(chunks)) makes the merge a PLAIN FP32 pairwise sum of the SM (sub-run) nodes in position
order padded with +0 to next_pow2(chunks) / (chunks a node).  No log-sum-exp rescale exists in this golden: attend.max
(global max over all T scores) precedes attend.exp_sum / attend.bf16_p, so every SM accumulates the same globally-scaled
BF16 p (attend.den / attend.norm divide after the merge).  The +0 pads are executed as real adds (add(-0, +0) = +0).

OWNER (d4g lowering): the SU.  Quarter q runs its quadrant's subtree (the SM nodes its smw writer put in its VM banks;
d4g W2 places SM j in quadrant j // 4, so with sub-runs of 32 rows the 20 nodes split 8 / 8 / 4 + 4 pads / 8 pads =
aligned subtrees of the golden 32-pad tree) as ONE SU programme of chained VOP adds through the lane store (class AD_C:
O = A + C, su_arith_compile OPS 'AD_C'), then the four quadrant partials cross on the COLL ring all-gather
(ot_hgi_coll_ring_ag, C1 class, word-preserving) and each quarter finishes the top levels for its 128 positions (fused
into the attend.norm SU programme).  No new RTL: the SU VOP add and the ring all-gather exist and are bench-proven.

THIS BENCH (minimum component: the arithmetic and its order on the real lanes): rtl/.../static_su/arithmetic/
tb_su_static_arithmetic (ot_hbm_su_static_arithmetic, 512 lanes, real pinned store banks; MLAT/ALAT/LEAF of the die's
LAT4/LEAF1 lanes) plays the whole tree in place in the lane store: the nodes (the RTL PV nodes of att_images.py unit,
<out>.nodes.npz, position l on lane l) are seeded in rows 256.., level k is one 64-issue op (issue v: A = row 256+2v,
C = row 256+2v+1 -> O = row 256+v, the tb's output-row law), every output word of every level is checked against the
independent NumPy golden (hdc_golden add, canonical +0) and the generator asserts that the final row equals the fixture
PV O bit for bit.  Negative controls: the tb's ADDR / PHASE / DATA mutants (must FAIL) and ORDER (a valid-looking
non-golden pairing at level 1 -- (j, j + pad/2) -- against the golden expectation; the generator first asserts that its
result differs from the fixture).  Issues v >= the level's pair count compute deterministic filler (modelled exactly).

    att_merge_su.py vectors --nodes L2_pos.nodes.npz --out DIR [--order]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "hbm_static"))
sys.path.insert(0, str(ROOT / "tools"))
from su_arith_compile import pack, physical_word  # noqa: E402
from hdc_golden import add  # noqa: E402

ROWS, LANES, ISSUES, CYC, OROW = 512, 512, 64, 176, 256


def control_images(pairs):
    """per op: pairs[v] = (rowA, rowC) for v < 64 -> 176 control lines (su_arith_compile baseline layout, AD_C)."""
    terms = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) for k in range(7))
    ctl = dict(no=1, ni=8192, ls=7, lvw=7, dst=1, co_dst=1, ca_ad=2,
               cp_imm1=0x3fa00000, cm_imm1=0x3fa00000, ce_imm1=0x3fa00000,
               ca_imm2=0x3ec00000, cs_imm2=0x3ec00000, cx_imm3=0x3f400000)
    out = []
    for cycle in range(CYC):
        v = max(0, min(ISSUES - 1, cycle - 8))
        ra, rc = pairs[v]
        rows = (ra, 0, rc, 0, OROW + v)          # roles A B C D O (B, D unused by AD_C)
        line = 0
        for q in range(4):
            f = dict(ctl, ld=int(cycle == 0), ld_c=terms, emit=int(8 <= cycle < 8 + ISSUES), i_v=v * 128,
                     vb=sum(physical_word(q, rows[s]) << (s * 24) for s in range(5)))
            line |= pack(f) << (q * 1742)
        out.append(line)
    return out


def tree_ops(pad, order_mut=False):
    """pairwise levels over rows OROW..OROW+pad-1, in place: level k pairs (2v, 2v+1) -> v.  order_mut: level 1 pairs
    (v, v + pad/2) instead (a different, non-golden tree)."""
    ops, n = [], pad
    while n > 1:
        half = n // 2
        pairs = []
        for v in range(ISSUES):
            if order_mut and n == pad and v < half:
                pairs.append((OROW + v, OROW + v + half))
            else:
                pairs.append((OROW + 2 * v, OROW + 2 * v + 1))
        ops.append(pairs)
        n = half
    return ops


def run_model(store, ops):
    """exact store model of the tb: every issue of an op reads the pre-op store (all reads precede the op's first
    write-back: read at issue <= 8+v, write at FIRST_OUTPUT+v >= 31+v), writes row OROW+v."""
    gold = []
    for pairs in ops:
        out = np.zeros((ISSUES, LANES), np.uint32)
        for v, (ra, rc) in enumerate(pairs):
            out[v] = add(store[ra].view(np.float32), store[rc].view(np.float32)).view(np.uint32)
        store[OROW:OROW + ISSUES] = out
        gold.append(out.ravel())
    return gold


def cmd_vectors(a):
    z = np.load(a.nodes)
    nodes, pad, fx = z["nodes"].astype(np.uint32), int(z["pad"]), z["fixture_pv"].astype(np.uint32)
    assert nodes.shape[1] == LANES and len(nodes) <= pad <= 128, (nodes.shape, pad)
    # seed: nodes on rows 256.., +0 pads to the golden pad, deterministic finite filler elsewhere (read only by
    # filler issues, modelled exactly)
    lane = np.arange(LANES, dtype=np.float32)
    seed = np.stack([((lane % 29) - 14) * np.float32(0.0625) + np.float32(r % 61) * np.float32(0.015625)
                     for r in range(ROWS)]).astype(np.float32).view(np.uint32)
    seed[OROW:OROW + pad] = 0
    seed[OROW:OROW + len(nodes)] = nodes
    ops = tree_ops(pad, a.order)
    gold_ops = tree_ops(pad, False)
    st = seed.copy()
    gold = run_model(st, gold_ops)
    final = st[OROW]
    if not np.array_equal(final, fx):
        raise SystemExit(f"golden tree of the RTL nodes != fixture PV ({int(np.sum(final != fx))} words)")
    if a.order:
        sm = seed.copy()
        run_model(sm, ops)
        bad = int(np.sum(sm[OROW] != fx))
        if bad == 0:
            raise SystemExit("ORDER mutant gives the fixture PV on this data: not a witness")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "seed.mem").write_text("\n".join(f"{x:08x}" for x in seed.ravel()) + "\n")
    (out / "gold.mem").write_text("\n".join(f"{x:08x}" for x in np.concatenate(gold)) + "\n")
    lines = [w for pairs in ops for w in control_images(pairs)]
    (out / "control.mem").write_text("\n".join(f"{x:01742x}" for x in lines) + "\n")
    doc = dict(schema="opentallas.hbm_att_merge_su.v1", lane="HBM-ATTGAP", nodes=int(len(nodes)), pad=pad,
               levels=len(ops), ops=["AD_C level %d" % (k + 1) for k in range(len(ops))], order_mutant=bool(a.order),
               nodes_npz=str(a.nodes), nodes_sha256=hashlib.sha256(Path(a.nodes).read_bytes()).hexdigest(),
               final_equals_fixture_pv=True, order_mutant_final_mismatch_words=(bad if a.order else 0),
               golden="hdc_golden add (NumPy FP32 RNE, canonical +0) over the tb's in-place store schedule",
               nops=len(ops))
    (out / "programme.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("vectors")
    p.add_argument("--nodes", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--order", action="store_true", help="ORDER negative control (non-golden level-1 pairing)")
    a = ap.parse_args(argv)
    return cmd_vectors(a)


if __name__ == "__main__":
    sys.exit(main())
