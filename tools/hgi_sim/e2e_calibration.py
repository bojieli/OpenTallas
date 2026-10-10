#!/usr/bin/env python3
"""hgi_sim cost tables vs the die-level RTL bench (hgi-e2e, results/rtl/hgi_e2e_*/runs/*/report.json).

For every bench run with REAL units, the per-unit RTL busy cycles against the simulator's price of the same records
(report.per_unit: rtl_busy / sim_cost), and -- as a SENSITIVITY, not a recalibration -- the DS-V4.1 1M and Qwen3-8B
P8191 tokens re-timed (timing.py S2) with each unit's cost scaled by that ratio.  The current RTL carries open
defects (hgi-e2e F3 gather sends whole rows / F4 PFMAX 64 / F5 one fetch sector in flight / F6 DMA mover boot-path
rate), so the published HBM rates keep the simulator's tables (the fixed RTL); re-run this tool as each fix lands
and move a unit's calibration entry to the measured value once its ratio is stable on the fixed RTL.

    python3 -m hgi_sim.e2e_calibration --out REC.json        (from tools/)
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402

OPEN_DEFECTS = {"COLL": "F3 whole-row gathers + F4 PFMAX 64 (die build faults; PFMAX 512 what-if measured)",
                "DMA": "F6 mover boot-path rate (one element / 4 edges + a kport round trip a sector miss)",
                "CP": "F5 one 32 B fetch sector in flight"}


def ratios(reports):
    """unit -> {vehicle -> rtl / sim} over the all-real runs (the run with the most real units per vehicle)."""
    best = {}
    for p in reports:
        d = json.loads(p.read_text())
        veh = p.parent.name.split("_L0")[0] + "_L0"
        nreal = sum(v.get("real", 0) for v in d["per_unit"].values())
        if d.get("pass_") and (veh not in best or nreal > best[veh][0]):
            best[veh] = (nreal, p, d)
    out = defaultdict(dict)
    runs = {}
    for veh, (nreal, p, d) in best.items():
        runs[veh] = dict(run=str(p.relative_to(ROOT)), cycles=d["summary"]["cycles"], real_records=nreal)
        for u, v in d["per_unit"].items():
            if v.get("real") and v.get("sim_cost"):
                out[u][veh] = dict(rtl_busy=v["rtl_busy"], sim_cost=v["sim_cost"],
                                   ratio=round(v["rtl_busy"] / v["sim_cost"], 3), real=v["real"], exact=v["exact"])
    return dict(out), runs


def scaled(base_cost, k):
    def cf(r, dyn, L):
        c, g, how = base_cost(r, dyn, L)
        return c * k.get(r.unit, 1.0), g, how
    return cf


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ds-program", type=Path, help="ds_native --program-out dump (rank 0) for the DS sensitivity")
    ap.add_argument("--ds-run", type=Path, help="the ds_native result of that program (ROW_GATHER stats)")
    a = ap.parse_args()
    reports = sorted(ROOT.glob("results/rtl/hgi_e2e_*/runs/*/report.json"))
    rt, runs = ratios(reports)
    res = dict(runs=runs, per_unit=rt, open_defects=OPEN_DEFECTS)
    # sensitivity: today's RTL ratios applied to the whole tokens
    sens = {}
    if a.ds_program:
        from hgi_sim import ds_native_timing as DT
        d, recs = DT.load(a.ds_program)
        recs = T.rebuild_waits(recs)
        rg = {}
        if a.ds_run:
            for x in json.loads(a.ds_run.read_text())["results"]:
                for s_ in x.get("row_gather") or []:
                    rg[x["layer"]] = s_
        cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
        k = {u: v["ds_L0"]["ratio"] for u, v in rt.items() if "ds_L0" in v}
        s0 = T.schedule(recs, DT.POS, "S2", cost_fn=cf)["total_cycles"]
        s1 = T.schedule(recs, DT.POS, "S2", cost_fn=scaled(cf, k))["total_cycles"]
        sens["ds_1M"] = dict(scale=k, fixed_rtl_cycles=round(s0, 1), fixed_rtl_tok_s=round(1.2e9 / s0, 1),
                             current_rtl_cycles=round(s1, 1), current_rtl_tok_s=round(1.2e9 / s1, 1))
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    qrecs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
    k = {u: v["qwen_L0"]["ratio"] for u, v in rt.items() if "qwen_L0" in v}
    s0 = T.schedule(qrecs, 8191, "S2")["total_cycles"]
    s1 = T.schedule(qrecs, 8191, "S2", cost_fn=scaled(T.cost, k))["total_cycles"]
    sens["qwen_P8191"] = dict(scale=k, fixed_rtl_cycles=round(s0, 1), fixed_rtl_tok_s=round(1.2e9 / s0, 1),
                              current_rtl_cycles=round(s1, 1), current_rtl_tok_s=round(1.2e9 / s1, 1))
    res["sensitivity"] = sens
    res["reading"] = ("ratios > 1 are the RTL's extra cycles over the simulator's price on the same records; the HBM "
                      "rates published by reprice assume the FIXED RTL (simulator tables); 'current_rtl' is what the "
                      "token would cost with today's RTL units (open defects listed)")
    rec = dict(schema="opentallas.hgi_sim.e2e_calibration.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               reports=[str(p.relative_to(ROOT)) for p in reports], result=res)
    print(json.dumps(res, indent=1)[:3000])
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
