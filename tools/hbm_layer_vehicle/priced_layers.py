#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): the compiler's static schedule of the HBM d4g DeepSeek-V4.1 AR token, per layer segment.

Reproduces the d4g price of record (d4g_2ring_qbg = price5 base: AR 1,905.4 tok/s) and writes, for every layer segment,
the priced cycles and the S2 static schedule (per record: unit, op, tag, d4g placement class, issue/start/end cycle,
priced cost).  This file is the CONTRACT the layer vehicle checks the RTL against: the vehicle replays the records of a
representative layer on the quadrant RTL and asserts each record's commit cycle = the start + the priced cost (the
"schedule assertions"), and reports measured layer cycles against per_segment[layer].

    PYTHONPATH=tools python3 -m hbm_layer_vehicle.priced_layers --out results/rtl/hbm_ds_layer_tput_1018/priced_layers.json \
        [--layers 0,2,14,3,head]
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import timing as T


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=Q.ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layers", default="0,1,2,3,14,head")
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    led = Q.load_ledger()
    kn = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)        # = opt_2ring_qbg (price of record)
    Q._D4G.clear()
    Q._D4G.update(kn)
    S.set_variant(PS.VARIANTS["b"], st)
    prog = RL.compile_case("AR")
    tot = V.run(prog, None)
    want = set(a.layers.split(","))
    end = [r for r in prog if r.unit == "CTL" and r.op == "END"][:1]
    segs = {}
    T.footprint = V._footprint
    try:
        for key, seg in V.segments(prog):
            k = str(key)
            if k not in want:
                continue
            seg2 = V.rebuild(seg + end)
            s = T.schedule(seg2, V.DT.POS, "S2", cost_fn=V.cost_fn(None))
            rows = []
            for i, r in enumerate(seg2):
                rows.append(dict(i=i, unit=r.unit, op=r.op, orig_op=getattr(r, "orig_op", f"{r.unit}.{r.op}"),
                                 tag=r.tag or "", cls=Q.classify(r),
                                 start=round(s["start"][i], 2) if i < len(s["start"]) else None,
                                 end=round(s["end"][i], 2) if i < len(s["end"]) else None,
                                 base_cost=round(getattr(r, "base_cost", 0.0) or 0.0, 2)))
            segs[k] = dict(cycles=round(s["total_cycles"], 1), records=rows,
                           per_unit={u: round(v["busy"], 1) for u, v in s["per_unit"].items()})
    finally:
        T.footprint = V._FP
    out = dict(schema="opentallas.hbm_ds_priced_layers.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               variant="d4g_2ring_qbg (price5 base; results/arch/hbm_d4g_price_1017/price5/summary.json)",
               ar_cycles=tot["cycles"], ar_tok_s=round(Q.CLK / tot["cycles"], 1), per_segment=tot["per_segment"],
               knob={k: (sorted(v) if isinstance(v, set) else v) for k, v in kn.items()}, segments=segs)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(dict(ar_cycles=out["ar_cycles"], ar_tok_s=out["ar_tok_s"],
                          layers={k: v["cycles"] for k, v in segs.items()}), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
