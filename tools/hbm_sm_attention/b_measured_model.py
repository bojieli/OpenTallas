#!/usr/bin/env python3
"""DS-V4.1-Flash 1M-context token rate with attention on the SM engines, from the MEASURED SM attention bench
(H-SM-ATT 2026-10-15).  Replaces the first-order SM cost of att_vs_sm_model.py (H-ATTQ) with the per-record cycles of
tools/hbm_sm_attention/sm_attn_bench.py (RTL, exact full shape) and states every non-measured term as MODEL.

Per attention record (batch 1, serial with the matvecs: ATT idle_true_dep dominates, so record time adds to the token):
  B = fa + comp (+ PV: publish + cross-SM merge)
  fa      = hbm.first_access + SM.overhead (measured constants of tools/hgi_sim timing: 104 + 155); prefetch variant drops
            the 104 (KV rows are known from the window ring / IDX top-k before q is ready)
  comp    = the busiest SM's measured span (first KV line -> last result) of its ops in the record:
            QK T640: one op a SM over its 4 window (SM-KV8) + 16 top-k (SM-KV4) rows (older runs: two serial ops)
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


def validate_evidence(d, shape):
    """Only complete positive component records can supply measured model inputs."""
    summary, ops = d.get("summary", {}), d.get("ops", [])
    expected_scores = {"ds128": 128, "ds640": 640, "qwen8192": 65536}[shape]
    if not (summary.get("shape") == shape and summary.get("verdict") == "PASS"
            and summary.get("mut") is None and ops
            and summary.get("ops") == summary.get("passed") == len(ops)
            and summary.get("qk_scores_checked") == expected_scores
            and summary.get("pv_cross_sm_merge_equals_att_pv") is True
            and all(o.get("pass") is True and o.get("rc") == 0 and not o.get("fault")
                    and o.get("mismatches") == 0 and o.get("results") == o.get("expected") for o in ops)):
        raise ValueError(f"{shape}: complete positive exact component evidence required")


def merge_cycles(nodes):
    lv, n, c = 0, nodes, 0
    while n > 1:
        adds = n // 2
        c += math.ceil(adds * 512 / 512) + 16
        n = math.ceil(n / 2)
        lv += 1
    return c


Q_TOK, Q_ATT_LAYER, Q_L = 1258136.0, 4 * 660.1, 36


def qwen_model(d):
    """Qwen3-8B TP4 T8192 on HBM (pathfinding): per die per layer 2 KV heads x (QK, PV), 4 q heads per KV head on 4 SM x
    columns.  Busiest SM: QK op 256 rows a head, PV 2 ops x 128 tokens a head (4 token streams each).
    publish MODEL 8 words/cycle: an op leaves 4 streams x 128 dims x 4 heads = 2048 words; merge MODEL as DS (SU, 512 lanes):
    256 nodes x (128 dims x 4 heads) per KV head; 'smerge' variant merges the 4 stream nodes inside the SM first (lever)."""
    validate_evidence(d, "qwen8192")
    qk = max(o["cycles"]["span"] for o in d["ops"] if o["kind"] == "qk")
    pv = max(o["cycles"]["span"] for o in d["ops"] if o["kind"] == "pv")
    res = dict(measured=dict(qk_op=qk, pv_op=pv))

    def merge(nodes, words):
        c, n = 0, nodes
        while n > 1:
            c += math.ceil((n // 2) * words / 512) + 16
            n = math.ceil(n / 2)
        return c
    for var, pub, nodes in (("streams_published", 2 * 2048 / 8, 256), ("smerge", 2 * 512 / 8, 64)):
        for pf in (False, True):
            fa = FA - (FIRST if pf else 0)
            layer = 2 * (fa + qk) + 2 * (fa + 2 * pv + pub + merge(nodes, 512))
            tok = Q_TOK + Q_L * (layer - Q_ATT_LAYER)
            res[f"{var}_{'prefetch' if pf else 'exposed'}"] = dict(layer=round(layer, 1), a_layer=Q_ATT_LAYER,
                tok_s=round(CLK / tok, 1), vs_A=round(Q_TOK / tok - 1, 4))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds640")
    ap.add_argument("ds128")
    ap.add_argument("--qwen", help="qwen8192 bench JSON (Qwen3-8B TP4 on HBM, pathfinding)")
    ap.add_argument("--out")
    a = ap.parse_args()
    d640, d128 = json.load(open(a.ds640)), json.load(open(a.ds128))
    validate_evidence(d640, "ds640")
    validate_evidence(d128, "ds128")

    def span(d, prefix):
        return max(o["cycles"]["span"] for o in d["ops"] if o["name"].startswith(prefix))

    def qk(d):          # one mixed-format QK op a SM (qk_sm*), or the older split qk8 + qk4 runs (serial)
        if any(o["name"].startswith("qk_sm") for o in d["ops"]):
            return span(d, "qk_sm")
        return sum(span(d, p) for p in ("qk8", "qk4") if any(o["name"].startswith(p) for o in d["ops"]))

    comp = {640: dict(qk=qk(d640), pv=span(d640, "pv")), 128: dict(qk=qk(d128), pv=span(d128, "pv"))}
    nodes = {640: sum(1 for o in d640["ops"] if o["kind"] == "pv"), 128: sum(1 for o in d128["ops"] if o["kind"] == "pv")}
    PUB = 64
    out = dict(scope="component spans measured; first access, dispatch, publish and cross-SM merge modeled",
               native_sm_integration_qualified=False, physical_closure_qualified=False, measured_comp=comp, pv_nodes=nodes, model_terms=dict(fa=FA, first_access=FIRST, publish=PUB,
               merge={T: merge_cycles(nodes[T]) for T in nodes}))
    out["throughput_qualified"] = False
    out["rate_scope"] = "conditional computation estimate at component8/11 line cadence; actual32SM PC service and KV4 byte expansion not priced"
    out["unpriced_kv4_layout"] = dict(canonical_row_bytes=288, implemented_row_bytes=544,
        extra_read_bytes_per_ds640_pass=512*(544-288), extra_read_bytes_per_ds640_qk_pv=2*512*(544-288),
        extra_read_bytes_per_token=38*2*512*(544-288),
        extra_replica_write_bytes_per_token_if_writer_uses544=3*40*(544-288),
        critical_path_cycles=None, actual_PC_cadence_qualified=False,
        reason="Current KV4 packs4x136B with all32scales repeated in everyline. Actual writer/home/cache/PC schedule must match this layout; no token-rate penalty inferred from byte ratio.")
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
    if a.qwen:
        out["qwen"] = qwen_model(json.load(open(a.qwen)))
    s = json.dumps(out, indent=1)
    print(s)
    if a.out:
        open(a.out, "w").write(s)


if __name__ == "__main__":
    main()
