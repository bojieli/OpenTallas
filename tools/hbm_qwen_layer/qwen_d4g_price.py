#!/usr/bin/env python3
"""TOKEN-PASS-HBMQ (10-18): price of record PER LAYER for Qwen3-8B on the d4g GEN2 die, and the compiler's fixed
static schedule of the layer programmes the RTL vehicle runs (the schedule-assertion table).

Two programmes, one schedule machinery (hgi_sim.timing.schedule S2 = the CP as specified):
  record  the price of record: the TP-4 r25 programme under ds_die_split._qwen_job's split transform (16 SM / TP-8:
          SM rows per SM unchanged, DMA stream x 2, collective delivery G 4 -> 8 on 4 lanes) + the relay knob
          (ds_relay_latency, v5 -> plan_b stages) + the d4g adders (d4g_quadrant_1017.d4g_added as patched by
          d4g_price5_1018; two rings; Qwen without QBG) = HBM-PRICE5 d4g_2ring_qbg (Qwen 946.2 tok/s, reproduced).
  d4g8    the programme that actually runs on d4g: hgi_sim.qwen_compiler Geometry(tp=8) (D4G8 mapping, bit-identical
          to the TP-4 golden; see tools/hbm_qwen_layer/qwen_d4g_proof.py), priced NATIVELY on the same model:
          SM.MATVEC  rows m on 16 SM at 99 B/cycle/SM == the 32-SM model at 2 m (same per-SM bytes / lines)
          ATT.*      one KV head a die at half the die bandwidth: stream part x 2
          DMA.LOAD   stream part x 2 (2 stacks), its own (TP-8) bytes
          COLL.*     in-package base as perf.coll_cycles (AR-like 1,350 / gather 586) + the delivery delta G 4 -> 8
                     (4 lanes) of ds_die_split._qwen_job; GROUP_REDUCE_MCAST priced as the all-reduce of its result
          + the same relay knob and d4g adders (the D4G8 ACT gather is a C1 record: on-die ring all-gather).
Variants of the stages: 'base' = plan_b (the price of record); 'landed' = plan_b shifted by the HBM-LANDING
half-cycle land plan (results/arch/hbm_die_d4g/landing/land_plan_d4g.json, lanes/HBM-LANDING.md; Qwen 945.5).

Per-layer cycles (token programme, position 8191): layer L = end of its last record - end of layer L-1's last record
(L0 includes the pre-loop records); head = token end - end of layer 35.  Stage programmes (what the vehicle runs):
L0 (one layer, parts=layers), chain (2-layer LOOP), head (parts=head): total cycles and the per-record
(dispatch, start, end, cost) table = the static schedule the RTL must reproduce (commit cycles as assertions).

    PYTHONPATH=tools python3 tools/hbm_qwen_layer/qwen_d4g_price.py --out-dir results/rtl/hbm_qwen_layer_tput_1018
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import d4g_price5_1018 as P5  # noqa: E402,F401  (patches d4g_quadrant_1017.d4g_added: PRICE5 base)
from hgi_sim import d4g_quadrant_1017 as Q  # noqa: E402
from hgi_sim import ds_die_split as S  # noqa: E402
from hgi_sim import ds_relay_latency as RL  # noqa: E402
from hgi_sim import plan_study_price_1017 as PS  # noqa: E402
from hgi_sim import qwen_compiler as QC  # noqa: E402
from hgi_sim import timing as T  # noqa: E402
from hgi_sim.records import encode_program  # noqa: E402

CLK = 1.2e9
CFG = ROOT / "compiler/models/qwen3-8b/config.json"
STAGES = ROOT / "results/arch/hbm_plan_study_1017/stages.json"
POS = 8191


def knobs(st):
    """(relay knob, d4g knob) of the price of record (PRICE5 d4g_2ring_qbg; Qwen: G1 8, lanes 4, no QBG / FP8)"""
    var = PS.VARIANTS["b"]
    kn_relay = RL._knob(st["v5"], st[var["stages"]])
    kq = dict(Q.knob(Q.ADDERS, st, ledger=Q.load_ledger()), rings=2)
    q = var["qwen"]
    kq.update(G1=q["G1"], lanes=q["lanes"])
    return var, kn_relay, kq


def cost_record(var, knr, kq):
    """ds_die_split._qwen_job's cost (split transform) with T.cost carrying the d4g adders, as d4g_quadrant_1017._qwen"""
    q = var["qwen"]
    fa = S.first_access()
    mf = T.MEAS.get("SM.overhead", {}).get("value", 0) + fa

    def cf(r, dyn, L):
        c, g, how = T.cost(r, dyn, L)
        c += Q.d4g_added(r, c, kq)
        c += RL.added(r, knr["delta"], False, None, knr["b"], knr["o"])
        if r.unit in ("SM", "ATT") and q["sm_s"] != 1 and c > mf:
            c = mf + q["sm_s"] * (c - mf)
        elif r.unit == "DMA" and r.op == "LOAD" and c > fa:
            c = fa + q["bw_s"] * (c - fa)
        elif r.unit == "COLL":
            n = r.desc["A"].n if "A" in r.desc else 1
            k = 2 if r.op == "ALL_REDUCE_SUM" else 1
            f0 = max(1, math.ceil(n * 2 / q["G0"] / 64))
            f1 = max(1, math.ceil(n * 2 / q["G1"] / 64))
            c += k * (S.deliver(f1, q["G1"], q["lanes"]) - S.deliver(f0, q["G0"], S.LANES0)) + k * q.get("xc", 0) * S.CROSS
        return c, g, how
    return cf


def base_native(r, dyn, L):
    """the unit cost of a D4G8 record on the 16-SM / 2-stack die (module doc)"""
    if r.unit == "SM":
        r2 = copy.copy(r)
        r2.desc = dict(r.desc)
        r2.desc["B"] = copy.copy(r.desc["B"])
        r2.desc["B"].m = 2 * (r.desc["B"].m or 1)
        return T.cost(r2, dyn, L)
    if r.unit == "COLL" and r.op in ("ALL_GATHER", "GROUP_REDUCE_MCAST"):
        base = T.cv("units", "COLL.ALL_REDUCE_SUM" if r.op == "GROUP_REDUCE_MCAST" else "COLL.ARGMAX_MERGE")
        return base, "measured_budget", f"in-package {r.op} (perf.coll_cycles base)"
    c, g, how = T.cost(r, dyn, L)
    if r.unit == "ATT":
        stream = c - T.first_access() - T.cv("units", "ATT.fixed")
        return c + stream, g, how + " (half the die bandwidth)"
    if r.unit == "DMA" and r.op == "LOAD":
        fa = T.first_access()
        return fa + 2 * (c - fa), g, how + " (2 stacks)"
    return c, g, how


def cost_native(var, knr, kq):
    q = var["qwen"]

    def cf(r, dyn, L):
        c, g, how = base_native(r, dyn, L)
        c += Q.d4g_added(r, c, kq)
        c += RL.added(r, knr["delta"], False, None, knr["b"], knr["o"])
        if r.unit == "COLL":
            n = r.desc["O"].n if r.op == "GROUP_REDUCE_MCAST" else (r.desc["A"].n if "A" in r.desc else 1)
            k = 2 if r.op in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1
            f0 = max(1, math.ceil(n * 2 / q["G0"] / 64))
            f1 = max(1, math.ceil(n * 2 / q["G1"] / 64))
            c += k * (S.deliver(f1, q["G1"], q["lanes"]) - S.deliver(f0, q["G0"], S.LANES0))
        return c, g, how
    return cf


def run(recs, cf):
    s = T.schedule(recs, POS, "S2", cost_fn=cf)
    rows = []
    for i, (k, L, *_) in enumerate(s["ex"]):
        r = recs[k]
        # keys as tools/hbm_layer_vehicle/priced_layers.py (TOKEN-PASS-HBMDS vehicle interface 1) + rec / L / wait / disp
        rows.append(dict(i=i, rec=k, L=L, unit=r.unit, op=r.op, orig_op=f"{r.unit}.{r.op}", tag=r.tag,
                         cls=Q.classify(r), wait=r.wait, disp=round(s["disp"][i], 1), start=round(s["start"][i], 1),
                         end=round(s["end"][i], 1), cost=round(s["costs"][i][0], 1),
                         base_cost=round(s["costs"][i][0], 1)))
    return s, rows


def per_layer(recs, rows, nl):
    lo = next(k for k, r in enumerate(recs) if r.unit == "CTL" and r.op == "LOOP")
    hi = next(k for k, r in enumerate(recs) if r.unit == "CTL" and r.op == "ENDLOOP")
    ends = [max(x["end"] for x in rows if lo < x["rec"] < hi and x["L"] == L) for L in range(nl)]
    pre = max([x["end"] for x in rows if x["rec"] < lo] + [0.0])
    tot = max(x["end"] for x in rows)
    lay = [round(ends[0], 1)] + [round(ends[L] - ends[L - 1], 1) for L in range(1, nl)]
    fam = {}
    for x in rows:
        if lo < x["rec"] < hi and x["L"] == 1:
            fam[x["tag"]] = x["cost"]
    return dict(preamble_end=round(pre, 1), layer_cycles=lay,
                segments=[dict(L=L, cycles=c) for L, c in enumerate(lay)] + [dict(L="head", cycles=round(tot - ends[-1], 1))], head_cycles=round(tot - ends[-1], 1),
                token_cycles=round(tot, 1), tok_s=round(CLK / tot, 1),
                chained_layer_mean=round(sum(lay[1:]) / (nl - 1), 1), L1_record_costs=fam)


def price_all(st, label):
    cfg = json.loads(CFG.read_text())
    md = QC.qwen_params(cfg)
    var, knr, kq = knobs(st)
    out = {}
    for prog, tp, cf in (("record", 4, cost_record(var, knr, kq)), ("d4g8", 8, cost_native(var, knr, kq))):
        g = QC.Geometry(cfg, 8192, tp=tp)
        tok = QC.program(g, md, cfg["num_hidden_layers"])
        s, rows = run(tok, cf)
        o = dict(token=per_layer(tok, rows, cfg["num_hidden_layers"]), races=len(s["races"]), stages={})
        for stage, n, parts in (("L0", 1, ("layers",)), ("chain", 2, ("layers",)), ("head", 0, ("head",))):
            recs = QC.program(g, md, n, parts=parts)
            ss, rr = run(recs, cf)
            img = encode_program(recs)
            ent = dict(cycles=round(ss["total_cycles"], 1), records=len(recs), executed=len(rr),
                       image_sha256=hashlib.sha256(img).hexdigest(), races=ss["races"][:5], schedule=rr)
            if stage == "chain":
                ent["per_layer"] = per_layer(recs, rr, 2)["layer_cycles"] + [None]
            out_stage = ent
            o["stages"][stage] = out_stage
        out[prog] = o
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=STAGES)
    ap.add_argument("--land-plan", type=Path, default=ROOT / "results/rtl/hbm_qwen_layer_tput_1018/inputs/land_plan_d4g.json")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    st0 = json.loads(a.stages.read_text())
    res = {"base": price_all(st0, "base")}
    if a.land_plan.exists():
        lp = json.loads(a.land_plan.read_text())
        st = copy.deepcopy(st0)
        for c, v in lp["per_class"].items():
            if c in st["plan_b"] and v.get("delta_half_bw"):
                st["plan_b"][c] = round(st["plan_b"][c] + v["delta_half_bw"], 3)
        res["landed"] = price_all(st, "landed")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    summ = {}
    for v, d in res.items():
        for prog, o in d.items():
            t = o["token"]
            summ[f"{v}.{prog}"] = dict(tok_s=t["tok_s"], token_cycles=t["token_cycles"], L0=t["layer_cycles"][0],
                                       chained_mean=t["chained_layer_mean"], head=t["head_cycles"],
                                       stage_L0=o["stages"]["L0"]["cycles"], stage_chain=o["stages"]["chain"]["cycles"],
                                       stage_head=o["stages"]["head"]["cycles"], races=o["races"])
    rec = dict(schema="opentallas.hbm_qwen_d4g_price.v1", lane="TOKEN-PASS-HBMQ",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, position=POS, summary=summ,
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/qwen_compiler.py", "hgi_sim/timing.py", "hgi_sim/d4g_quadrant_1017.py",
                   "hgi_sim/d4g_price5_1018.py", "hgi_sim/ds_die_split.py", "hbm_qwen_layer/qwen_d4g_price.py")})
    (a.out_dir / "price_per_layer.json").write_text(json.dumps(dict(rec, results={
        v: {p: dict(token=o["token"], races=o["races"],
                    stages={k: {kk: vv for kk, vv in e.items() if kk != "schedule"} for k, e in o["stages"].items()})
            for p, o in d.items()} for v, d in res.items()}), indent=1, default=str) + "\n")
    sched = {v: {p: {k: e["schedule"] for k, e in o["stages"].items()} for p, o in d.items()} for v, d in res.items()}
    (a.out_dir / "static_schedule.json").write_text(json.dumps(dict(
        schema="opentallas.hbm_qwen_d4g_static_schedule.v1", rule="per executed record of each stage programme: "
        "dispatch / start / end (cycles at 1.2 GHz from the doorbell) and cost, hgi_sim.timing.schedule S2; the RTL "
        "vehicle asserts each record's commit cycle against 'end' (fixed latency, no credits)", schedule=sched),
        indent=0, default=str) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
