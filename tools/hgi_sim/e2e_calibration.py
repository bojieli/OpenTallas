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


def service(records):
    """per real record: RTL service time = retire - max(dispatch, the same unit's previous retire) (the queueing behind
    an earlier record of the unit is not the unit's cost), against the simulator's cost of that record"""
    last = {}
    out = defaultdict(lambda: dict(rtl=0.0, sim=0.0, n=0))
    for r in sorted(records, key=lambda x: x["disp"]):
        if r["ret"] < 0 or r["disp"] < 0:
            continue
        st = max(r["disp"], last.get(r["unit"], -1))
        last[r["unit"]] = r["ret"]
        if r["real"]:
            o = out[(r["unit"], r["op"])]
            o["rtl"] += r["ret"] - st
            o["sim"] += r["cost"]
            o["n"] += 1
    return out


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
        runs[veh] = dict(run=str(p), cycles=d["summary"]["cycles"], real_records=nreal)
        import hbm_generic_iface as HGI
        sv = service(d["records"])
        for (u, op), v in sv.items():
            if v["sim"] > 0:
                name = f"{u}.{HGI.D_OPS[u][op]}" if u in HGI.D_OPS and op < len(HGI.D_OPS[u]) else f"{u}.{op}"
                out[name][veh] = dict(rtl_service=round(v["rtl"], 1), sim_cost=round(v["sim"], 1),
                                      ratio=round(v["rtl"] / v["sim"], 3), records=v["n"])
    return dict(out), runs


def scaled(base_cost, k):
    """scale each record's cost by the measured ratio of its unit.op (unmeasured ops keep the simulator's cost)"""
    def cf(r, dyn, L):
        c, g, how = base_cost(r, dyn, L)
        return c * k.get(f"{r.unit}.{r.op}", 1.0), g, how
    return cf


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ds-program", type=Path, help="ds_native --program-out dump (rank 0) for the DS sensitivity")
    ap.add_argument("--ds-run", type=Path, help="the ds_native result of that program (ROW_GATHER stats)")
    ap.add_argument("--dflash", action="store_true", help="also re-time the DFlash block-16 step")
    ap.add_argument("--reports", type=Path, nargs="*", help="hgi-e2e report.json files (default: results/rtl/hgi_e2e_*)")
    a = ap.parse_args()
    reports = sorted(a.reports) if a.reports else sorted(ROOT.glob("results/rtl/hgi_e2e_*/runs/*/report.json"))
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
    # variants with DMA at full bandwidth (hgi-takeover is building the wide bank-parallel DMA -> VM write port)
    for key, veh in (("ds_1M", "ds_L0"), ("qwen_P8191", "qwen_L0")):
        if key in sens:
            sens[key]["scale_dma_full_bw"] = {u: x for u, x in sens[key]["scale"].items() if not u.startswith("DMA.")}
    kq = sens["qwen_P8191"]["scale_dma_full_bw"]
    s2 = T.schedule(qrecs, 8191, "S2", cost_fn=scaled(T.cost, kq))["total_cycles"]
    sens["qwen_P8191"].update(current_rtl_dma_full_bw_cycles=round(s2, 1),
                              current_rtl_dma_full_bw_tok_s=round(1.2e9 / s2, 1))
    if "ds_1M" in sens:
        kd = sens["ds_1M"]["scale_dma_full_bw"]
        s2 = T.schedule(recs, DT.POS, "S2", cost_fn=scaled(cf, kd))["total_cycles"]
        sens["ds_1M"].update(current_rtl_dma_full_bw_cycles=round(s2, 1),
                             current_rtl_dma_full_bw_tok_s=round(1.2e9 / s2, 1))
    if a.dflash:
        from hgi_sim import dflash as DF
        from hgi_sim import dflash_timing as DFT
        dcfg = json.loads(DFT.DCFG.read_text())
        g = DF.DGeom(cfg, dcfg, 8192, 16)
        drecs = DF.step_program(g, QC.qwen_params(cfg), timing_pos=8192 - 16)
        base = DFT.make_cost("spec", False)
        out = {}
        for nm, kk in (("fixed_rtl", {}), ("current_rtl_dma_full_bw", kq),
                       ("current_rtl", sens["qwen_P8191"]["scale"])):
            st = T.schedule(drecs, 8192 - 16, "S2", cost_fn=scaled(base, kk))["total_cycles"]
            out[nm] = dict(step_cycles=round(st, 1), tok_s_tau_8_01=round(8.01 * 1.2e9 / st, 1))
        sens["dflash_b16"] = out
    res["sensitivity"] = sens
    res["reading"] = ("ratios > 1 are the RTL's extra cycles over the simulator's price on the same records; the HBM "
                      "rates published by reprice assume the FIXED RTL (simulator tables); 'current_rtl' is what the "
                      "token would cost with today's RTL units (open defects listed)")
    rec = dict(schema="opentallas.hgi_sim.e2e_calibration.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               reports=[str(p) for p in reports], result=res)
    print(json.dumps(res, indent=1)[:3000])
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
