#!/usr/bin/env python3
"""COLL.TOPK_MERGE prices (hgi-1010/k, 2026-10-10): the hardware merge sink (ot_hgi_coll_ep TKM = 1) against the G20
idiom fallback (gathers + IDX.MERGE), on the G25 DS program's 9 records a token.  The cheaper EXACT form is the default.

HARDWARE (one record): every rank multicasts pf = ceil(n / 8) flits of 8 {value, id} pairs on the gather bypass; the
merge sink filters each pair against tau (the running k-th key), inserts survivors 4 a cycle into the systolic array,
then drains, id-sorts (odd-even transposition, ceil(nout / 4) rounds) and shifts out O / R.
    price = gather(G n 8 B)  [the TU gather model the walk already charges: endpoint 108.6 + 23.75 a flit a rank,
                              one 377.6 ns crossing, 0.15 us striping tail]
          + tail(nout)       [sink: drain + id sort + shift-out, measured on tb_hgi_coll_tkm at production shape:
                              TAIL_FIX + TAIL_PER_CELL x ceil(nout / 4)]
IDIOM (G20 lowering, spec 6.7 text): IDX.TOPK (k = n) orders each rank's list by the key + an indexed read of the ids
by the returned positions; two exact COLL.ALL_GATHERs (values, ids); IDX.MERGE key 0 (first k); an SU op writes -id as
FP32; IDX.TOPK (k, order 0) over -id; an indexed read of the winners into O (and R).  Unit rates: IDX.TOPK = the
measured ot_hgi_idx_topk service (3.16 cycles an input element on the VM fast path, tb_hgi_idx_tput n 384) + one emit
a cycle; ALL_GATHER = the TU gather model x 0.716 (qualified PIPE ratio, hgi_unit_tput coll); IDX.MERGE measured
(tb_hgi_idx_merge: G 96 n 512 k 512 1,301 cycles, k 2,048 3,407); SU / indexed reads ~ n / 16 + 40 a record.
The idiom is INFEASIBLE when the two gathered G n arrays do not fit the 262,144-word VM (the L20 candidate merge:
2 x 96 x 1,366 = 262,272 words).

    python3 -m hgi_sim.topk_merge_price [--json OUT]        (from tools/)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

VM_WORDS = 1 << 18
# sink tail fit (tb_hgi_coll_tkm, filled from the production-shape bench; see results/rtl/hgi_coll_tkm_20261010)
TAIL_FIX = 60.0
TAIL_PER_CELL = 3.0
IDX_TOPK_PER_IN = 1213.0 / 384          # tb_hgi_idx_tput: n 384 k 6 service 1,213 cycles (VM fast path bound)
IDX_MERGE_MEAS = {(96, 512, 512): 1301.0, (96, 512, 2048): 3407.0}
ALL_GATHER_RATIO = 0.716


def gather(nbytes, G):
    from hgi_sim.perf import coll_cycles
    return coll_cycles("ALL_GATHER", nbytes, G)[0]


def hw_price(G, n, k):
    nout = min(k, G * n)
    g = gather(G * n * 8, G)
    t = TAIL_FIX + TAIL_PER_CELL * math.ceil(nout / 4)
    return dict(form="hw", gather=round(g, 1), tail=round(t, 1), total=round(g + t, 1))


def idx_topk(n, k):
    return n * IDX_TOPK_PER_IN + k


def idx_merge(G, n, k):
    if (G, n, k) in IDX_MERGE_MEAS:
        return IDX_MERGE_MEAS[(G, n, k)]
    return 1.2 * k + 8 * math.log2(max(G, 2)) + 60          # ~1 output a cycle + tree + VM (fit of the measured cases)


def small(n):
    return n / 16 + 40


def idiom_price(G, n, k, has_r):
    nout = min(k, G * n)
    words = 2 * G * n
    terms = dict(local_sort=idx_topk(n, n), local_ids=small(n),
                 gathers=2 * ALL_GATHER_RATIO * gather(G * n * 4, G),
                 merge=idx_merge(G, n, k), neg_id=small(nout), id_sort=idx_topk(nout, nout),
                 winners=small(nout) * (2 if has_r else 1))
    tot = sum(terms.values())
    return dict(form="idiom", feasible=words <= VM_WORDS, vm_words=words, terms={a: round(b, 1) for a, b in terms.items()},
                total=round(tot, 1))


def ds_records():
    """the G25 DS program's TOPK_MERGE records (layer, G, n, k, has_r, current price)"""
    from hgi_sim import ds_native_timing as DT
    root = TOOLS.parent
    d, recs = DT.load(root / "results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json")
    cf = DT.NativeCost(d["ops"], recs, row_gather={})
    out = []
    for r in recs:
        if r.unit == "COLL" and r.op == "TOPK_MERGE":
            out.append(dict(layer=r.layer, tag=r.tag, G=96, n=r.desc["A"].n, k=r.imm_a, has_r="R" in r.desc,
                            price_now=round(cf(r, None, 0)[0], 1)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    rows = []
    for x in ds_records():
        h = hw_price(x["G"], x["n"], x["k"])
        i = idiom_price(x["G"], x["n"], x["k"], x["has_r"])
        best = "hw" if (not i["feasible"] or h["total"] <= i["total"]) else "idiom"
        rows.append(dict(**x, hw=h, idiom=i, default=best))
    tot = dict(price_now=round(sum(r["price_now"] for r in rows), 1), hw=round(sum(r["hw"]["total"] for r in rows), 1),
               idiom_feasible_records=sum(r["idiom"]["feasible"] for r in rows),
               idiom=round(sum(r["idiom"]["total"] for r in rows), 1))
    res = dict(schema="opentallas.topk_merge_price.v1", records=rows, per_token=tot,
               model=__doc__.split("\n\n")[1].strip())
    print(json.dumps(dict(per_token=tot, per_record=[(r["layer"], r["tag"], r["price_now"], r["hw"]["total"],
                                                       r["idiom"]["total"], r["idiom"]["feasible"], r["default"])
                                                      for r in rows]), indent=1))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
