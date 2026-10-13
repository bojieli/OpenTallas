#!/usr/bin/env python3
"""HBM B2 slice-ring calendar sweep (Claude ring-station-1013, 2026-10-13).

Re-runs the EXISTING exposure model (tools/hgi_e2e/b2.py record_traffic / traffic, SPEC 5.0 arrival-after-need on the
vector's s2 schedule) on the B2 compiler vectors with PER-EDGE ring latencies taken from the native die_v12 corridor
study instead of the 12/11-cycle price, and converts exposed cycles to a first-order single-user tok/s change.

    python3 tools/hbm_ring_calendar_sweep.py VEC_ROOT --out results/arch/hbm_ring_transport_1013/calendar_sweep.json

Nothing is re-priced: budgets (Qwen 93 / DS 290 exposed cycles a layer) and the layer cycle counts are the SPEC's.
The vector directory is never written (b2.py writes VEC/b2.txt, so each vector is read through a symlink shadow).
First-order: a stall is charged where it occurs and does not shift later records; not an RTL measurement.
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "tools/hgi_e2e"))
import b2  # noqa: E402

FACE = 3            # SPEC 5: 2 face flops + 1 ring-stop arbitration per hop
SPEC_LAYER = dict(ds=dict(cycles_per_layer=14139, tok_s=2121.8, layers=40),
                  qwen=dict(cycles_per_layer=35253, tok_s=945.5, layers=36))
# die_v12 polyline segments at <= 500 um (results/arch/hbm_native_ring_cut_1013/STUDY.md): SID order SW0 SE1 NW2 NE3
SEG_SID = [41, 60, 42, 67]          # edges 0-1 (H), 1-2 (SE-NW diagonal), 2-3 (H), 3-0 (NE-SW diagonal)
# geometric order SW SE NE NW: both diagonals become vertical neighbours. ESTIMATE: 12.99 mm centre pitch x the
# horizontal detour ratio 20.03 / 16.49 = 15.8 mm -> 32 segments (no polyline study exists for this order)
SEG_GEO = [41, 32, 42, 32]
BC_SPEC = 12                        # b2_params: bcast_hops 1 x ring_hop_cycles 12
BC_PHYS = 33                        # ESTIMATE: hub at die centre to a slice, (16.49 + 12.99) / 2 mm -> 30 segments + 3


def scen():
    out = {}
    def add(name, edges, bc, note):
        out[name] = dict(edges=edges, bcast=bc, note=note)
    add("spec_price", [11, 12, 11, 12], BC_SPEC, "SPEC 5 price (H 11 / V 12), control row")
    add("elastic4_sid", [4 * s + 4 for s in SEG_SID], BC_SPEC, "measured D8 elastic station on every segment (4 edges)")
    add("pipe_sid", [s + FACE for s in SEG_SID], BC_SPEC, "plain registered stages, one edge a segment, end-to-end credit")
    add("pipe_geo", [s + FACE for s in SEG_GEO], BC_SPEC, "plain stages + geometric slice order (vertical edges estimated)")
    add("hybrid_k8_sid", [s + 4 * -(-s // 8) + FACE for s in SEG_SID], BC_SPEC, "one elastic station per 8 plain stages")
    add("pipe_sid_bcast_phys", [s + FACE for s in SEG_SID], BC_PHYS, "pipe_sid + the COLL star at its own wire length (estimate)")
    add("pipe_geo_bcast_phys", [s + FACE for s in SEG_GEO], BC_PHYS, "pipe_geo + the COLL star at its own wire length (estimate)")
    add("spec_ring_bcast_phys", [11, 12, 11, 12], BC_PHYS, "ring at price, star at wire length: isolates the star")
    return out


def run(vec: Path, edges, bc, lead_words=None):
    P = b2.params(None)
    P["ring_hop_cycles"] = 1
    P["bcast_hops"] = bc
    n = P["nclust"]
    def hops(a, b_, n_):
        a, b_ = sorted((int(a), int(b_)))
        cw = sum(edges[a:b_]); return min(cw, sum(edges) - cw)
    b2.hops = hops
    with tempfile.TemporaryDirectory() as td:
        sh = Path(td) / vec.name; sh.mkdir()
        for f in ("meta.json", "vmw.bin", "b2"):
            os.symlink(vec / f, sh / f)
        return b2.traffic(sh, P)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path); ap.add_argument("--vec", nargs="+", required=True); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    S = scen(); rows = []
    for v in a.vec:
        for name, s in S.items():
            o = run(a.root / v, s["edges"], s["bcast"])
            m = o["model"]; L = SPEC_LAYER[m]
            top = sorted(((k, p["exposed"]) for k, p in o["per_op"].items() if p["exposed"] > 0), key=lambda x: -x[1])[:4]
            rows.append(dict(vector=v, model=m, scenario=name, exposed=o["exposed_cycles"], budget=o["budget_cycles_per_layer"],
                             within_budget=o["within_budget"], remote_records=o["remote_records"], records=o["records"],
                             remote_words=o["remote_words"], bcast_words=o["bcast_words"],
                             layer_loss_pct=round(100 * o["exposed_cycles"] / (L["cycles_per_layer"] + o["exposed_cycles"]), 3), top_ops=top))
            print(v, name, o["exposed_cycles"], o["budget_cycles_per_layer"], top, flush=True)
    summ = {}
    for name in S:
        for m in ("ds", "qwen"):
            r = [x for x in rows if x["scenario"] == name and x["model"] == m]
            if not r:
                continue
            base = [x for x in rows if x["scenario"] == "spec_price" and x["model"] == m]
            L = SPEC_LAYER[m]
            e = sum(x["exposed"] for x in r) / len(r); e0 = sum(x["exposed"] for x in base) / len(base)
            summ.setdefault(name, {})[m] = dict(
                mean_exposed_per_layer=round(e, 1), worst_exposed_per_layer=max(x["exposed"] for x in r), budget=r[0]["budget"],
                within_budget_all=all(x["within_budget"] for x in r), vectors=len(r),
                tok_s_first_order=round(L["tok_s"] * L["cycles_per_layer"] / (L["cycles_per_layer"] + e), 1),
                loss_pct_vs_priced_tok_s=round(100 * e / (L["cycles_per_layer"] + e), 2),
                loss_pct_vs_same_vectors_at_spec_price=round(100 * (e - e0) / (L["cycles_per_layer"] + e), 2))
    a.out.write_text(json.dumps(dict(
        schema="opentallas.hbm.ring_calendar_sweep.v1", author="Claude:ring-station-1013", date="2026-10-13",
        status="first-order model run (tools/hgi_e2e/b2.py SPEC 5.0 exposure on compiler B2 vectors); NOT an RTL measurement, "
               "NOT a qualification, nothing re-priced",
        model="b2.traffic with per-edge path latency (min of the two ring directions); stalls are not propagated",
        face_cycles_per_hop=FACE, segments_sid=SEG_SID, segments_geo_estimate=SEG_GEO, bcast_cycles=dict(spec=BC_SPEC, physical_estimate=BC_PHYS),
        spec_layer=SPEC_LAYER, scenarios=S, summary=summ, rows=rows), indent=1) + "\n")


if __name__ == "__main__":
    main()
