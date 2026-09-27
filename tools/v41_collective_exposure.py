#!/usr/bin/env python3
"""Gate C7 / O2: feed the RTL stage bench's measured collective exposure back into the V4.1 decode model.

Inputs: results/rtl/v41_stage_collective_campaign.json (tools/rtl_v41_stage_collective_campaign.py) and the V4.1
DESIGN-POINT MODEL on this tree (tools/arch_lanes_v41.py design_point(): the adopted ladder rungs of
results/arch/v41_latency_ladder.json, the lane split of results/arch/v41_lanes.json, on the design-point base
tools/arch_budget_v41_dp.py).  The design point itself now prices the measured exposure (arch_lanes_v41.build ->
v41_lanes.json design_point is the exposure-corrected headline; design_point_overlap_assumed is the conditional
point); this tool writes the standalone C7 record with the derivation and the specification model's rows.

Steps:
  1. dump   the design point's on-path collectives and stage hops (bytes time, depth, producer window) at 1M;
  2. terms  per class, residual = measured tail - (max(0, bytes - window) + depth), the explicit exposed term
            (tools/collective_exposure.py: issue = max(0, bytes - window) + residual, from the producer's LAST output);
  3. price  tokens/s/user at 200K and 1M, batch 1, without and with MTP, overlap-assumed vs measured exposure, on
            the design point, and on the specification model (tools/arch_budget_v41.py price, exposure=terms).

    python3 tools/v41_collective_exposure.py [--out results/arch/v41_collective_exposure.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
CAMPAIGN = ROOT / "results/rtl/v41_stage_collective_campaign.json"
OUT = ROOT / "results/arch/v41_collective_exposure.json"
CONTEXTS = (200000, 1048576)
# class -> the bench patterns that measure it, and the node whose design-point pricing the residual is taken against
CLASSES = {
    "all_reduce": dict(patterns=("allreduce_wo_b", "allreduce_down"), nodes=("attn.out_allreduce",
                                                                           "ffn.combine_allreduce"),
                       window="producer"),
    "all_gather_small": dict(patterns=("gather_router",), nodes=("ffn.router_allgather",), window="producer"),
    "all_gather_select": dict(patterns=("gather_topk",), nodes=("attn.idx.topk_merge",), window="fixed"),
    "all_gather_rows": dict(patterns=("gather_rows",), nodes=("attn.rows_allgather",), window="fixed"),
    "hop": dict(patterns=("stage_hop",), nodes=("substage_hop0", "hop"), window="producer"),
}


def campaign_binding(camp=None, path=CAMPAIGN):
    """Whether the campaign record binds the RTL / bench / driver sources on disk (its source_sha256 map)."""
    camp = camp or json.loads(Path(path).read_text())
    pins = camp.get("source_sha256") or {}
    now = {k: (hashlib.sha256((ROOT / k).read_bytes()).hexdigest() if (ROOT / k).exists() else None) for k in pins}
    stale = sorted(k for k, v in pins.items() if now[k] != v)
    return dict(pinned=bool(pins), current=bool(pins) and not stale, stale=stale, source_sha256=pins)


def dump_on_path(U, A, sp, muts, hz, ctx=1048576):
    """The design point's on-path collectives / stage hops at ctx, batch 1 (muts: the design point's mutations
    including its lane pricing; hz: (Hz, params) as arch_latency_ladder_v41.rung_spec returns it)."""
    import arch_latency_ladder_v41 as LX
    hzv, prm = hz
    out = dict(clock_hz=hzv)
    with LX.clock(hzv), U.params(**prm):
        clk = A._env()["clock"]
        r = U.solve(sp, ctx, levers=U.CHAIN_L3, muts=list(muts))
        b = r["_built"]
        g = b.g
        nodes = {}
        for n in g.path(b.sink):
            nd = g.nodes[n]
            if nd["kind"] not in ("collective", "hop"):
                continue
            key = re.sub(r"^(L\d+|E\d+|head)\.", "", n)
            pf = max(g.fin[d] for d in nd["deps"]) if nd["deps"] else 0.0
            row = nodes.setdefault(key, dict(count=0, examples=[]))
            row["count"] += 1
            row["examples"].append(dict(node=n, issue_cyc=nd["issue"] * clk, depth_cyc=nd["depth"] * clk,
                                        producer_window_cyc=max(g.nodes[d]["issue"] for d in nd["deps"]) * clk,
                                        exposed_cyc=(g.fin[n] - pf) * clk, stream=nd["stream"]))
            row["examples"] = sorted(row["examples"], key=lambda e: (-e["depth_cyc"], -e["exposed_cyc"]))[:3]
        out["on_path"] = nodes
        out["T_us"] = r["T_s"] * 1e6
        out["breakdown_us"] = r["breakdown_us"]
    return out


def derive_terms(camp, dump):
    clock = dump["clock_hz"]
    pats = camp["summary"]["patterns"]
    sched = camp["schedules"]
    terms, rows = {}, {}
    for cls, c in CLASSES.items():
        best = None
        for i, pat in enumerate(c["patterns"]):
            if pat not in pats:
                continue
            node = c["nodes"][min(i, len(c["nodes"]) - 1)]
            ex = [e for k in c["nodes"] if k in dump["on_path"] for e in dump["on_path"][k]["examples"]]
            ex = [e for e in ex if node in e["node"]] or ex
            e = max(ex, key=lambda x: x["depth_cyc"])            # the full (board) instance, not a group-boundary one
            span = max(sched[pat]) - min(sched[pat]) + 1
            window = e["producer_window_cyc"] if c["window"] == "producer" else span
            formula = max(0.0, e["issue_cyc"] - window) + e["depth_cyc"]
            meas = pats[pat]["measured_exposed_tail_cycles"]
            resid = meas - formula
            rows[pat] = dict(class_=cls, design_point_node=e["node"], bytes_cycles=e["issue_cyc"],
                             depth_cycles=e["depth_cyc"], window_cycles=window,
                             model_exposed_cycles=e["exposed_cyc"], formula_cycles=formula,
                             measured_tail_cycles=meas, residual_cycles=resid,
                             min_rx_depth_words=pats[pat]["min_rx_depth_for_best_tail"],
                             min_tx_queue_words=pats[pat]["min_tx_queue_without_producer_stall"])
            if best is None or resid > best[0]:
                best = (resid, window, pat)
        if best:
            terms[cls] = dict(window=c["window"], window_s=best[1] / clock, residual_s=best[0] / clock,
                              residual_cycles=best[0], from_pattern=best[2])
    return terms, rows


def design_point_rates(dp, terms):
    """Batch-1 tokens/s per user at 200K and 1M, without and with MTP, overlap-assumed vs measured exposure."""
    import arch_latency_ladder_v41 as LX
    import collective_exposure as CX
    base = list(dp["muts"]) + [dp["ml"]]
    out = {}
    for ctx in CONTEXTS:
        e0 = LX.evaluate(dp["sp"], ctx, base, hz=dp["hz"])
        e1 = LX.evaluate(dp["sp"], ctx, base + [CX.mutation(terms)], hz=dp["hz"])
        out[str(ctx)] = {k: dict(ar=e["ar"], mtp=e["mtp"], T_us=e["T_us"], verify_us=e["verify_us"],
                                 breakdown_us=e["breakdown_us"])
                         for k, e in (("overlap_assumed", e0), ("measured_exposure", e1))}
    return out


def derive(camp):
    """(terms, per-pattern rows, dump, design point) on this tree's design-point model."""
    import arch_lanes_v41 as AL
    dp = AL.design_point()
    dump = dump_on_path(AL.U, AL.A, dp["sp"], list(dp["muts"]) + [dp["ml"]], dp["hz"])
    terms, rows = derive_terms(camp, dump)
    return terms, rows, dump, dp


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--campaign", type=Path, default=CAMPAIGN)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    camp = json.loads(a.campaign.read_text())
    bind = campaign_binding(camp)
    terms, rows, dump, dp = derive(camp)
    rates = design_point_rates(dp, terms)
    rec = dict(schema="v41_collective_exposure/2", tool="tools/v41_collective_exposure.py",
               gate="C7 / O2", campaign=str(a.campaign.relative_to(ROOT)) if a.campaign.is_relative_to(ROOT)
               else str(a.campaign),
               campaign_binding=bind,
               design_point_model=dict(tools=["tools/arch_budget_v41_dp.py", "tools/arch_utilization_v41.py",
                                              "tools/arch_latency_ladder_v41.py", "tools/arch_lanes_v41.py"],
                                       split=dp["split"]),
               terms=terms, per_pattern=rows, design_point_on_path=dump["on_path"],
               design_point_T_us=dump["T_us"], design_point_breakdown_us=dump["breakdown_us"],
               design_point_rates=rates,
               spec_model_rates=("results/arch/arch_budget_v41.json collective_exposure (tools/arch_budget_v41.py "
                                 "prices the specification model with these terms, exposure=True)"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(binding={k: bind[k] for k in ("pinned", "current", "stale")},
                          terms={k: round(v["residual_cycles"], 1) for k, v in terms.items()},
                          rates={c: {k: (round(v["ar"]), round(v["mtp"])) for k, v in r.items()}
                                 for c, r in rates.items()}), indent=1))


if __name__ == "__main__":
    main()
