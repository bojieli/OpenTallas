#!/usr/bin/env python3
"""Simulated cycles of one DFlash step (draft + verify + accept) for Qwen3-8B on the r25 die (TP4, 8K context) through
HGI-1, with the command processor modelled (timing.py schedule S2), and the per-user rate at a given tau.

Unit costs are timing.py's (calibration.json) with four extensions the multi-slot program needs:
  SM.MATVEC P slots   spec 6.7: one weight read serves P <= 8 slots.  'spec' mode: the line issue is unchanged (the
                      slots ride the SM's per-column x stores); 'reissue' mode (the r25 RTL as it stands: ports carry
                      op_xb only, no slot count) replays every staged line P times -> issue x P, HBM read once.
                      INT8 issue: two-beat (64 codes / cycle / SM, the adopted front) or one-beat (RQ-HF-7, NO_FIT);
                      the BF16 drafter weights (fmt 0) always issue at the BF16 rate.
  ATT                 rows = B's n + C's n, bytes by the row format (FP8 target KV, BF16 drafter KV).
  COLL                ALL_REDUCE_SUM / ALL_GATHER: the measured TP4 4,096-word cost + 256 cycles per further 4,096
                      words (estimate: 64 B / cycle endpoint serialisation).
  SU                  + one HBM first access when an operand is in HBM (row scales read in place).

    python3 -m hgi_sim.dflash_timing --out REC.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import dflash as D  # noqa: E402
from hgi_sim import qwen_compiler as QC  # noqa: E402
from hgi_sim import timing as T  # noqa: E402
from hgi_sim.records import encode_program  # noqa: E402

CFG = ROOT / "compiler/models/qwen3-8b/config.json"
DCFG = ROOT / "compiler/models/qwen3-8b-dflash-b16/config.json"
CLK = 1.2e9

TAU = {
    16: dict(published=(8.01, "DFlash (Chen, Liang, Liu), arXiv:2602.06036v2 Table 3: Qwen3-8B, B200, SGLang, "
                              "concurrency 1, MATH-500, tau 8.01 (block 16) -- the largest published Qwen3-8B tau "
                              "(results/external/registry.json new:dflash_table3_table4)"),
             measured=(3.656, "our 264-turn DFlash b16 run, cycle-weighted, 9 primary workloads "
                              "(results/speculative/dflash_block_acceptance.json blocks.16.pooled.primary; "
                              "equal-weighted 4.662)"),
             measured_eq=(4.662, "same, mean of workloads")),
    8: dict(published=(round(8.01 * 5.8265 / 8.3572, 3),
                       "no published block-8 tau: 8.01 x (our MATH-500 non-thinking tau_direct block 8 / block 16 = "
                       "5.8265 / 8.3572; our block-16 value 8.36 reproduces the paper's 8.01 setting)"),
            measured=(3.2956, "our 264-turn run AT block 8 (direct), cycle-weighted primary "
                              "(dflash_block_acceptance.json blocks.8.pooled.primary; equal-weighted 3.748)"),
            measured_eq=(3.7478, "same, mean of workloads")),
}


def make_cost(sm_mode="spec", one_beat=False):
    bw = T.cv("hbm", "bytes_per_cycle")
    fa_hbm = T.first_access()

    def cost(r, dyn, L, cfg=None):
        u, op = r.unit, r.op
        if u == "SM":
            b = r.desc["B"]
            _, n, m, _, _ = T.eff(b, dyn, L)
            fmt = r.param & 3
            P = ((r.param >> 2) & 7) + 1
            tr = (1.0 if one_beat else T.TRANSPORT) if fmt == 3 else 1.0
            rate = (0.5 if one_beat else 1.0) if fmt == 3 else 1.0
            nbytes = n * m * T.ESZ[b.fmt] * tr
            stream = nbytes / bw
            R = -(-m // 32)
            lines = math.ceil(T.MEAS["SM.bf16_lines_per_row_k"]["value"] * R * n * rate)
            if sm_mode == "reissue":
                lines *= P
            comp = lines + T.MEAS["SM.drain"]["value"]
            fa = T.MEAS["hbm.first_access"]["value"] + T.MEAS["SM.overhead"]["value"]
            return fa + max(comp, stream), "measured", f"SM {m}x{n} {b.fmt} P{P}"
        if u == "ATT":
            rows, nbytes = 0, 0
            for k in ("B", "C"):
                d = r.desc.get(k)
                if d is None:
                    continue
                _, n, _, _, _ = T.eff(d, dyn, L)
                rows += n
                nbytes += n * 128 * T.ESZ[d.fmt]
            return fa_hbm + nbytes / bw + T.cv("units", "ATT.fixed"), "estimate", f"ATT {rows} rows"
        if u == "COLL" and op in ("ALL_REDUCE_SUM", "ALL_GATHER"):
            n = r.desc["A"].n
            return (T.cv("units", "COLL.ALL_REDUCE_SUM") + max(0, n / 4096 - 1) * 256, "measured_budget+estimate",
                    f"{op} {n} words")
        if u == "SU":
            c, g_, how = T.cost(r, dyn, L)
            if any(d.space == "HBM" for d in r.desc.values()):
                c += fa_hbm
            return c, g_, how
        if u == "CTL" and op == "TOKX":
            return r.desc["A"].n, "estimate", "TOKX beats"
        return T.cost(r, dyn, L)
    return cost


def run(B, sm_mode, one_beat, cfg, dcfg, md):
    g = D.DGeom(cfg, dcfg, 8192, B)
    pos = 8192 - B
    recs = D.step_program(g, md, timing_pos=pos)
    s = T.schedule(recs, pos, "S2", cost_fn=make_cost(sm_mode, one_beat))
    fam = {}
    for k, v in s["family_unit_cycles"].items():
        top = k.split("_")[0]
        fam[top] = fam.get(top, 0) + v
    return dict(B=B, sm_mode=sm_mode, one_beat_int8=one_beat, position=pos, records_in_image=len(recs),
                image_bytes=len(encode_program(recs)), records_executed=s["records_executed"],
                step_cycles=round(s["total_cycles"], 1), step_us=round(s["total_cycles"] / CLK * 1e6, 2),
                n_races=len(s["races"]), races=s["races"][:5], per_unit=s["per_unit"],
                unit_busy_by_phase={k: round(v, 1) for k, v in fam.items()},
                family_unit_cycles=dict(list(s["family_unit_cycles"].items())[:30]))


def ar(cfg, md, one_beat):
    g = QC.Geometry(cfg, 8192)
    recs = QC.program(g, md, cfg["num_hidden_layers"])
    s = T.schedule(recs, 8191, "S2", cost_fn=make_cost("spec", one_beat))
    return round(s["total_cycles"], 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    cfg = json.loads(CFG.read_text())
    dcfg = json.loads(DCFG.read_text())
    md = QC.qwen_params(cfg)
    res = dict(schema="opentallas.hgi_sim.dflash_timing.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               grade="pathfinding: unit entries are calibration.json estimates/measurements; not a closed rate",
               drafter="z-lab/Qwen3-8B-DFlash-b16 (5 layers, BF16 weights unchanged, target layers [1,9,17,25,33])",
               tau=TAU, ar={}, steps=[], table=[])
    for ob in (False, True):
        c = ar(cfg, md, ob)
        res["ar"]["one_beat" if ob else "two_beat"] = dict(cycles=c, tok_s=round(CLK / c, 1))
        print("AR", ob, c, round(CLK / c, 1), flush=True)
    for B in (8, 16):
        for mode in ("spec", "reissue"):
            for ob in (False, True):
                r = run(B, mode, ob, cfg, dcfg, md)
                res["steps"].append(r)
                print(B, mode, ob, r["step_cycles"], "races", r["n_races"], r["unit_busy_by_phase"], flush=True)
                for tk in ("published", "measured", "measured_eq"):
                    tau = TAU[B][tk][0]
                    res["table"].append(dict(B=B, sm_mode=mode, one_beat_int8=ob, tau_kind=tk, tau=tau,
                                             step_cycles=r["step_cycles"],
                                             tok_s=round(CLK * tau / r["step_cycles"], 1),
                                             vs_ar=round(CLK * tau / r["step_cycles"] /
                                                         res["ar"]["one_beat" if ob else "two_beat"]["tok_s"], 3)))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1, default=float) + "\n")
    for row in res["table"]:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
