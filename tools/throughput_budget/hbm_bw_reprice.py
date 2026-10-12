#!/usr/bin/env python3
"""HBM-bandwidth re-price (owner 2026-10-12, option 1): the token's S2 schedule with every SM weight line priced at the
SM's physical HBM share (w19_hbm_token_compose.SM_HBM_BYTES_PER_CYCLE) instead of one 136-B line a cycle.

Rows (same records, same scheduler, only the per-SM bandwidth changes):
  before   unlimited per-SM bandwidth (the old price: 1 line = 1 cycle = 136 B/cycle/SM)
  after    4 HBM3E stacks x 1.0 TB/s x 0.95 sustained / 1.2 GHz / 32 SMs = 98.96 B/cycle/SM (the design)
  hbm4     PAPER SENSITIVITY ONLY (not a design change): ~5.2 TB/s peak a die x 0.95 / 1.2 GHz / 32 = 128.6 B/cycle/SM

    python3 -m throughput_budget.hbm_bw_reprice --out ../results/arch/hbm_bw_reprice_1012/reprice.json   (from tools/)
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import w19_hbm_token_compose as W  # noqa: E402
from hgi_sim import timing as T  # noqa: E402
from throughput_budget import build as B  # noqa: E402

HBM4_DIE_BYTES_PER_S = 5.2e12
ROWS = {
    "before": float("inf"),
    "after": W.SM_HBM_BYTES_PER_CYCLE,
    "hbm4_paper": HBM4_DIE_BYTES_PER_S * W.HBM_SUSTAINED / W.F_FAST / W.N_SM,
}


def ds_cycles(bpc):
    """DS-V4.1 1M AR token on the HBM die: G25 rank-0 native program, S2 (as throughput_budget.build.ds_budget)."""
    from hgi_sim import ds_native_timing as DT
    W.SM_HBM_BYTES_PER_CYCLE = bpc
    d, recs = DT.load(B.PROG)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(B.RUN.read_text())["results"]:
        for s_ in x.get("row_gather") or []:
            rg[x["layer"]] = s_
    DT.apply_dyn_counts(recs, rg)
    cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    cls = collections.defaultdict(lambda: [0, 0.0])
    sm = collections.defaultdict(lambda: [0, 0.0])

    def g(r, dyn, L):
        c = cf(r, dyn, L)
        k = f"{r.unit}.{r.op}"
        cls[k][0] += 1
        cls[k][1] += c[0]
        if r.unit == "SM":
            kind = "batched_expert" if getattr(r, "batched", False) else "other"
            sm[kind][0] += 1
            sm[kind][1] += c[0]
        return c
    tot = T.schedule(recs, DT.POS, "S2", cost_fn=g)["total_cycles"]
    return tot, {k: dict(records=v[0], price_cycles_per_token=round(v[1], 1)) for k, v in sorted(cls.items())}, \
        {k: dict(records=v[0], price_cycles_per_token=round(v[1], 1)) for k, v in sm.items()}


def qwen_cycles(bpc):
    """Qwen3-8B 8K AR token on the HBM die (qwen_compiler, S2).  The Qwen SM price is timing.cost: max(lane lines,
    the die stream, the busiest SM's rows at bw / 32)."""
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads((B.ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
    sm = [0, 0.0]

    def g(r, dyn, L):
        c = T.cost(r, dyn, L)
        if r.unit == "SM":
            sm[0] += 1
            sm[1] += c[0]
        return c
    tot = T.schedule(recs, 8191, "S2", cost_fn=g)["total_cycles"]
    return tot, dict(records=sm[0], price_cycles_per_token=round(sm[1], 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--qwen", action="store_true", help="also the Qwen 8K token (its SM price is timing.cost)")
    a = ap.parse_args()
    out = dict(schema="opentallas.hbm-bw-reprice.v1", generated_utc=datetime.datetime.utcnow().isoformat() + "Z",
               constants=dict(hbm_stacks=W.HBM_STACKS, stack_bytes_per_s=W.HBM_STACK_BYTES_PER_S,
                              sustained=W.HBM_SUSTAINED, clock_hz=W.F_FAST, n_sm=W.N_SM, sm_line_bytes=W.SM_LINE_BYTES,
                              sm_peak_bytes_per_cycle=round(W.SM_HBM_PEAK_BYTES_PER_CYCLE, 3),
                              sm_sustained_bytes_per_cycle=round(W.SM_HBM_BYTES_PER_CYCLE, 3),
                              line_price_factor=round(W.SM_LINE_BYTES / W.SM_HBM_BYTES_PER_CYCLE, 4)),
               ds={}, qwen={})
    for name, bpc in ROWS.items():
        tot, cls, sm = ds_cycles(bpc)
        out["ds"][name] = dict(sm_bytes_per_cycle=None if bpc == float("inf") else round(bpc, 3),
                               token_cycles=round(tot, 1), tok_s=round(W.F_FAST / tot, 1), sm=sm, classes=cls)
        print(f"DS {name}: {tot:,.0f} cycles, {W.F_FAST / tot:,.1f} tok/s", flush=True)
    if a.qwen:
        tot, sm = qwen_cycles(None)
        out["qwen"]["after"] = dict(token_cycles=round(tot, 1), tok_s=round(W.F_FAST / tot, 1), sm=sm)
        print(f"Qwen after: {tot:,.0f} cycles, {W.F_FAST / tot:,.1f} tok/s", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
