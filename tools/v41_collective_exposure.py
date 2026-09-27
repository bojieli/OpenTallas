#!/usr/bin/env python3
"""Gate C7 / O2: feed the RTL stage bench's measured collective exposure back into the V4.1 decode model.

Inputs: results/rtl/v41_stage_collective_campaign.json (tools/rtl_v41_stage_collective_campaign.py) and the V4.1
design point's own DAG.  The design point (8,622 tok/s/user at 1M, docs/ARCH_V41_RACK.md Table R-1) is priced by the
v41-rack-gates model chain (arch_lanes_v41 -> arch_latency_ladder_v41 -> arch_utilization_v41 -> arch_budget_v41 ->
decode_critical_path), which is not on this line; --rack-tree points at a checkout of it and this tool drives it in
a subprocess, loading tools/collective_exposure.py from HERE by path.

Steps:
  1. dump   the design point's on-path collectives and stage hops (bytes time, depth, producer window) at 1M;
  2. terms  per class, residual = measured tail - (max(0, bytes - window) + depth), the explicit exposed term
            (tools/collective_exposure.py: issue = max(0, bytes - window) + residual, from the producer's LAST output);
  3. price  tokens/s/user at 200K and 1M, batch 1, without and with MTP, overlap-assumed vs measured exposure, on
            the design point, and on this line's spec model (tools/arch_budget_v41.py price, exposure=True).

    python3 tools/v41_collective_exposure.py --rack-tree <checkout of v41-rack-gates> [--out results/arch/v41_collective_exposure.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def _cx():
    spec = importlib.util.spec_from_file_location("collective_exposure_here", ROOT / "tools/collective_exposure.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# -- driver: runs with cwd = the rack tree ------------------------------------------------------------------------------
def driver(action, terms_path):
    import re
    tree = Path.cwd()
    sys.path.insert(0, str(tree / "tools"))
    import arch_lanes_v41 as AL  # noqa: E402
    LX, U, A = AL.LX, AL.U, AL.A
    CX = _cx()
    base = U.unified(U.req_spec())
    adopted = {r["key"] for r in json.loads((tree / "results/arch/v41_latency_ladder.json").read_text())["ladder"]
               if r["adopted"]}
    LX.LADDER[:] = [(k, lab, kind if k in adopted else "none", pay, f) for k, lab, kind, pay, f in LX.LADDER]
    sp, muts, hz = LX.rung_spec(base, len(LX.LADDER))
    best = json.loads((tree / "results/arch/v41_lanes.json").read_text())["best_split"]
    ml = AL.m_lanes(best["tp"], best["stage"], best["two_step"])
    hzv, prm = hz
    out = dict(tree_split=dict(tp=best["tp"], stage=best["stage"], two_step=best["two_step"]), clock_hz=hzv)
    terms = json.loads(Path(terms_path).read_text())["terms"] if terms_path else None
    extra = [CX.mutation(terms)] if terms else []
    with LX.clock(hzv), U.params(**prm):
        clk = A._env()["clock"]
        if action == "dump":
            r = U.solve(sp, 1048576, levers=U.CHAIN_L3, muts=list(muts) + [ml])
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
        else:
            rates = {}
            for ctx in CONTEXTS:
                e0 = LX.evaluate(sp, ctx, list(muts) + [ml], hz=hz)
                e1 = LX.evaluate(sp, ctx, list(muts) + [ml] + extra, hz=hz)
                rates[str(ctx)] = dict(overlap_assumed=dict(ar=e0["ar"], mtp=e0["mtp"], T_us=e0["T_us"],
                                                            verify_us=e0["verify_us"], breakdown_us=e0["breakdown_us"]),
                                       measured_exposure=dict(ar=e1["ar"], mtp=e1["mtp"], T_us=e1["T_us"],
                                                              verify_us=e1["verify_us"],
                                                              breakdown_us=e1["breakdown_us"]))
            out["rates"] = rates
    print("DRIVER_JSON " + json.dumps(out))


def run_driver(tree, action, terms_path=None):
    cmd = [sys.executable, str(Path(__file__).resolve()), "--driver", action]
    if terms_path:
        cmd += ["--terms", str(terms_path)]
    r = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("DRIVER_JSON ")]
    if r.returncode or not line:
        raise RuntimeError(f"driver {action} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return json.loads(line[-1][len("DRIVER_JSON "):])


def rev(tree):
    return subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


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


def spec_model_rates(terms):
    sys.path.insert(0, str(ROOT / "tools"))
    import arch_budget_v41 as A  # noqa: E402
    sp = A.Spec(**json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["required_spec"])
    out = {}
    for ctx in CONTEXTS:
        r0 = A.price(sp, ctx)
        r1 = A.price(sp, ctx, exposure=terms)
        out[str(ctx)] = dict(overlap_assumed=r0["tokens_s_per_user"], measured_exposure=r1["tokens_s_per_user"],
                             T_us=[r0["T_s"] * 1e6, r1["T_s"] * 1e6])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--driver", choices=("dump", "eval"))
    ap.add_argument("--terms")
    ap.add_argument("--rack-tree", type=Path)
    ap.add_argument("--campaign", type=Path, default=CAMPAIGN)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    if a.driver:
        driver(a.driver, a.terms)
        return
    camp = json.loads(a.campaign.read_text())
    tree = a.rack_tree.resolve()
    dump = run_driver(tree, "dump")
    terms, rows = derive_terms(camp, dump)
    rec = dict(schema="v41_collective_exposure/1", tool="tools/v41_collective_exposure.py",
               gate="C7 / O2", campaign=str(a.campaign.relative_to(ROOT)) if a.campaign.is_relative_to(ROOT)
               else str(a.campaign),
               design_point_tree=dict(branch="v41-rack-gates", commit=rev(tree)),
               terms=terms, per_pattern=rows, design_point_on_path=dump["on_path"],
               design_point_T_us=dump["T_us"], design_point_breakdown_us=dump["breakdown_us"])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")        # the terms file the driver reads
    ev = run_driver(tree, "eval", a.out)
    rec["design_point_rates"] = ev["rates"]
    rec["spec_model_rates_this_line"] = spec_model_rates(terms)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(terms={k: round(v["residual_cycles"], 1) for k, v in terms.items()},
                          rates={c: {k: (round(v["ar"]), round(v["mtp"])) for k, v in r.items()}
                                 for c, r in ev["rates"].items()},
                          spec=rec["spec_model_rates_this_line"]), indent=1))


if __name__ == "__main__":
    main()
