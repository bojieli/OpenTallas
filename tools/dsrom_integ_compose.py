#!/usr/bin/env python3
"""DS-ROM integration checkpoint: recompose the 1M token (position 1,048,575) with every adopted lever ON TOGETHER,
from the combined measurements, and compare with the separate-lever composition (2,532.2 AR / 7,319.9 MTP).

Same graph, inputs and code path as tools/dsrom_1m_measure.py compose (imported, not modified): the S81 unified graph
with every context-dependent node replaced by its full-shape RTL measurement, variant candidate_gather, CKV HBM latency
259.  The integration replaces:
  * re-index layers L24 / L28 / L32 / L36: idx.score + idx.topk_local (separately: worst gather + settle + idx-array
    latency, THEN the select on the gather order, serial) by the CHAINED measurement of
    results/rtl/dsrom_integration_20261004/reindex_wf.json (gather -> scorer latency -> mask-drop -> select on one
    rank, worst of the four ranks, start to last selection beat; L32 / L36 take the worse of L24 / L28, as the
    separate composition does); idx.topk_final (the cross-die select) is unchanged;
  * the draft chain: + the S81 fused head's measured added latency (results/rtl/dsrom_integration_20261004/
    fused_head.json, 6 cycles at 1.2 GHz) on each of the 5 serial chain steps;
  * the wavefront hand-off: unchanged (the measured 0.408 % of the reduced stage; the integrated stage measured 1 cycle).

    python3 tools/dsrom_integ_compose.py --out results/rtl/dsrom_integration_20261004/composition.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_measure as M  # noqa: E402

MEAS = ROOT / "results/rtl/dsrom_1m_measured_20261004"
RI = ROOT / "results/rtl/dsrom_reindex_candidates_20261004"
INTEG = ROOT / "results/rtl/dsrom_integration_20261004"
VARIANT, LAT = "candidate_gather", 259
CHAIN_STEPS = 5


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def compose(integrated: bool):
    reader = json.loads((MEAS / "reader.json").read_text())
    sel = {}
    for f in (MEAS / "select.json", MEAS / "select_l24_full.json"):
        sel.update(json.loads(f.read_text())["layers"])
    rs = json.loads((RI / "select.json").read_text())
    for tag, r in rs["layers"].items():
        sel[f"{tag}_mdrop"] = dict(local=dict(runs=r["drop_dense"]["runs"]), final=r["final"])
        sel[f"{tag}_gather"] = dict(local=dict(runs=r["gather"]["runs"]), final=r["final"])
    gather = json.loads((RI / "gather.json").read_text())
    run = json.loads((MEAS / f"ckv_lat{LAT}.json").read_text())
    g0, T0, _ = M.s58_graph()
    assert abs(1 / T0 - 2535.5) < 0.1, T0
    model_l20_idx = sum(g0.nodes[n]["issue"] for n in g0.nodes if n.startswith("L20.attn.idx")) * 1e6
    ck = M._ckv_cycles(run)
    g = copy.deepcopy(g0)
    patches, modelled, _, _, _ = M._apply(g, reader, sel, ck, VARIANT, gather)
    draft_us = M.DRAFT["fused_us"]
    extra = {}
    if integrated:
        rw = json.loads((INTEG / "reindex_wf.json").read_text())
        fh = json.loads((INTEG / "fused_head.json").read_text())
        assert rw["all_pass"] and fh["pass_"] and fh["fh1_exact"]
        cw = rw["timing"]["chained_worst"]
        chained = {24: cw["L24"], 28: cw["L28"], 32: max(cw.values()), 36: max(cw.values())}
        for L, cyc in chained.items():
            for node, c, src in ((f"L{L}.attn.idx.score", cyc,
                                  f"CHAINED gather -> scorer latency -> mask-drop -> select, worst rank, "
                                  f"{'L24' if L == 24 else 'L28' if L == 28 else 'worse of L24/L28'} (reindex_wf.json)"),
                                 (f"L{L}.attn.idx.topk_local", 0, "inside the chained measurement")):
                nd = g.nodes[node]
                old = next(p for p in patches if p["node"] == node)
                nd.update(issue=c / M.CLK, depth=0.0, ctrl=0.0, stream=False)
                old.update(separate_us=old["measured_us"], measured_us=round(c / M.CLK * 1e6, 4),
                           measured_cycles=int(c), source=src)
        add = fh["added_latency_cycles"]["design"]
        draft_us += CHAIN_STEPS * add / M.CLK * 1e6
        extra = dict(reindex_chained_cycles=chained, fused_head_added_cycles_per_step=add)
    t, lt = M.layer_times(g)
    ar = t * 1e6 + M.S81_EXTRA_HOPS * M.HOP_US
    idx_us = lambda L: sum(p["measured_us"] for p in patches if p["node"].startswith(f"L{L}.attn.idx"))
    W = M.WAVEFRONT
    l20_occ = W["l20_occ_us"] - model_l20_idx + idx_us(20)
    re_occ = W["l20_occ_us"] - model_l20_idx + idx_us(24)
    occ = max(W["head_occ_us"], l20_occ, re_occ)
    ii = occ * (1 + W["overhead"]) + W["hop_us"]
    verify = ar + W["positions"] * ii
    mtp = M.DRAFT["tau"] * 1e6 / (verify + draft_us + M.DRAFT["seed_commit_us"])
    return dict(AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1), II_us=round(ii, 3), verify_us=round(verify, 3),
                stage_occupancy_us=dict(head=W["head_occ_us"], L20=round(l20_occ, 3), reindex=round(re_occ, 3)),
                draft_us=round(draft_us, 4), MTP_tok_s=round(mtp, 1),
                reindex_patches=[p for p in patches if any(p["node"].startswith(f"L{L}.attn.idx") for L in M.REINDEX)],
                still_modelled_context_terms=modelled, **extra)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=INTEG / "composition.json")
    a = ap.parse_args()
    sep, integ = compose(False), compose(True)
    assert abs(sep["AR_tok_s"] - 2532.2) < 0.05 and abs(sep["MTP_tok_s"] - 7319.9) < 0.05, sep
    rec = dict(schema="opentallas.dsrom-integration.composition.v1", context=M.CTX, position=M.POS,
               variant=f"{VARIANT}.lat{LAT}", separate=sep, integrated=integ,
               delta=dict(AR_pct=round(100 * (integ["AR_tok_s"] / sep["AR_tok_s"] - 1), 3),
                          MTP_pct=round(100 * (integ["MTP_tok_s"] / sep["MTP_tok_s"] - 1), 3)),
               still_modelled=["context-independent nodes of every layer from the S81 unified graph (as in the "
                               "separate composition)", "L20 candidate-block select (cand.*)",
                               "stage hop 0.482 us", "head 13.63 us in the AR path / 12.37 us wavefront head occupancy",
                               "index scorer arithmetic inside the chained re-index measurement (idx-array latency 48 "
                               "+ settle 24 measured separately, results/rtl/w11_idx_array.json)",
                               "draft chain base 105.55 us (reduced-vehicle fused ratio at full shape) + the measured "
                               "S81 fused-head latency", "wavefront II overhead from the reduced L20 stage (0.408 %)"],
               inputs={str(p.relative_to(ROOT)): sha(p) for p in
                       (MEAS / "reader.json", MEAS / "select.json", MEAS / "select_l24_full.json",
                        MEAS / f"ckv_lat{LAT}.json", RI / "gather.json", RI / "select.json",
                        INTEG / "reindex_wf.json", INTEG / "fused_head.json", ROOT / "tools/dsrom_1m_measure.py",
                        ROOT / "tools/dsrom_integ_compose.py")})
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("delta",)}),
          json.dumps({k: {x: v[x] for x in ("AR_tok_s", "MTP_tok_s", "II_us", "verify_us", "draft_us")}
                      for k, v in (("separate", sep), ("integrated", integ))}))


if __name__ == "__main__":
    main()
