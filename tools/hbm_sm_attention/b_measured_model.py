#!/usr/bin/env python3
"""DS-V4.1-Flash 1M-context token rate with attention on the SM engines, from the MEASURED SM attention bench
(H-SM-ATT 2026-10-15).  Replaces the first-order SM cost of att_vs_sm_model.py (H-ATTQ) with the per-record cycles of
tools/hbm_sm_attention/sm_attn_bench.py (RTL, exact full shape) and states every non-measured term as MODEL.

Per attention record (batch 1, serial with the matvecs: ATT idle_true_dep dominates, so record time adds to the token):
  B = fa + comp (+ PV: publish + cross-SM merge)
  fa      = hbm.first_access + SM.overhead (measured constants of tools/hgi_sim timing: 104 + 155); prefetch variant drops
            the 104 (KV rows are known from the window ring / IDX top-k before q is ready)
  comp    = the busiest SM's measured span (first KV line -> last result) of its ops in the record:
            QK T640: qk8 (4 window rows) + qk4 (16 compressed rows), measured as two serial ops (conservative)
            PV T640: one aligned run of 4 chunks (32 tokens) on 20 SMs;  T128: QK 4 rows, PV 1 chunk on 16 SMs
  publish = MODEL: 512 FP32 PV node words leave the SM at 8 words / cycle (64 cycles)
  merge   = MODEL: pairwise cross-SM node merge on SU (fixed-slot 4-quadrant reduce-scatter, H-ELEM-B/H-COLL):
            sum over levels of (adds x 512 / 512 lanes + 16 depth/overhead), pads skipped (add(x, +0) = x exactly)
A at its immutable price (147.144 / 339.144 per record) and A's source-feasible bound are the references.
Extra KV writes of the adopted floorplan (stack-local KV): +3 compressed-row and +3 window-row DMA.STOREs per layer per
token (posted, 30 cycles each on DMA, which has slack: DMA busy 40,284 of 565,569) -- reported as DMA busy added and as a
critical-path upper bound if every store serialised.
"""
import argparse
import json
import math

DS_TOK = 565569.1
A_PRICE = {128: 147.144, 640: 339.144}
LAYERS = {128: 2, 640: 38}
FA, FIRST = 104 + 155, 104
CLK = 1.2e9


def merge_cycles(nodes):
    lv, n, c = 0, nodes, 0
    while n > 1:
        adds = n // 2
        c += math.ceil(adds * 512 / 512) + 16
        n = math.ceil(n / 2)
        lv += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds640")
    ap.add_argument("ds128")
    ap.add_argument("--out")
    a = ap.parse_args()
    d640, d128 = json.load(open(a.ds640)), json.load(open(a.ds128))

    def span(d, prefix):
        return max(o["cycles"]["span"] for o in d["ops"] if o["name"].startswith(prefix))

    comp = {640: dict(qk=span(d640, "qk8") + span(d640, "qk4"), pv=span(d640, "pv")),
            128: dict(qk=span(d128, "qk8"), pv=span(d128, "pv"))}
    nodes = {640: sum(1 for o in d640["ops"] if o["kind"] == "pv"), 128: sum(1 for o in d128["ops"] if o["kind"] == "pv")}
    PUB = 64
    out = dict(measured_comp=comp, pv_nodes=nodes, model_terms=dict(fa=FA, first_access=FIRST, publish=PUB,
               merge={T: merge_cycles(nodes[T]) for T in nodes}))
    for pf in (False, True):
        delta = 0.0
        rec = {}
        for T in (128, 640):
            fa = FA - (FIRST if pf else 0)
            qk = fa + comp[T]["qk"]
            pv = fa + comp[T]["pv"] + PUB + merge_cycles(nodes[T])
            rec[T] = dict(qk=qk, pv=pv, a_price=A_PRICE[T])
            delta += LAYERS[T] * (qk + pv - 2 * A_PRICE[T])
        tok = DS_TOK + delta
        out["prefetch" if pf else "exposed"] = dict(per_record=rec, delta_cycles=round(delta, 1), token_cycles=round(tok, 1),
                                                     tok_s=round(CLK / tok, 1), vs_A_price=round(DS_TOK / tok - 1, 4),
                                                     vs_A_feasible=round(581299 / tok - 1, 4))
    kvw = 6 * 40 * 30
    out["extra_kv_writes"] = dict(stores_per_token=6 * 40, dma_busy_added=kvw,
                                  critical_path_upper_bound_tok_s=round(CLK / (out["exposed"]["token_cycles"] + kvw), 1))
    s = json.dumps(out, indent=1)
    print(s)
    if a.out:
        open(a.out, "w").write(s)


if __name__ == "__main__":
    main()
