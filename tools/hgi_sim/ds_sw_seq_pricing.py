#!/usr/bin/env python3
"""DS-V4.1 1M token: price the approved software sequences for the gathers (hgi-takeover pricing request 10-09
16:48, spec G20 / G21 on main e17bf2e57) on the bit-exact native program, against today's pricing.

  TOPK_MERGE (G20)  local IDX.TOPK (k = n) + 2 x COLL.ALL_GATHER (values, ids; G = 96) + IDX.MERGE key 0 (96 runs,
                    k) + SU ids -> -float(id) + IDX.TOPK over -id (k = n = k) + an indexed VM read for the
                    ascending table.  IDX.MERGE: 7,881 cycles MEASURED at 96 x 512 k 512; other k scaled
                    linearly in the outputs from that point (head load 1,500 + per output).
  ROW_GATHER (G21)  IDX.OWNED (K 512: 1,227 cycles MEASURED; K 2,048: 4,510) + per slot j < M: indexed DMA.LOAD of
                    one 2 KB row, one exact ALL_GATHER (32 flits a rank, 96 ranks: 3,072 flits at 4 lanes / cycle
                    = 768 cycles + the TU crossing / endpoint latency), and the head dies' DMA.STORE of the 96 rows;
                    COLL-serial: M gathers back to back, each paying delivery + latency; the "slots_pipelined" variant
                    lets the next slot's gather start while the previous delivers (M x 768 + the latency once).  M per layer is the
                    bit-exact run's own selection (row_gather stats); the request's 11-12 is reported alongside.
  ARGMAX_MERGE      an exact gather of 1 flit a rank + a 5-cycle fold.
Today's pricing: TOPK_MERGE / ARGMAX_MERGE = the composition's measured collective classes (walk), ROW_GATHER = the
bypass model of ds_native_timing.  Each priced program is scheduled (timing.py S2, CP modelled), so the token delta
includes the overlap the dependences allow.

    python3 -m hgi_sim.ds_sw_seq_pricing --program PROG.json --run RUN.json --out REC.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402
from hgi_sim import ds_native_timing as DT  # noqa: E402
from hgi_sim.perf import coll_cycles  # noqa: E402

CLK = 1.2e9
MERGE_MEAS = dict(base=594.0, per_output=1.37, points={512: 1297, 2048: 3407})   # IDX.MERGE measured (hgi-takeover)
HC_POST = 540.0                                                     # HC_MIX_POST measured (G22)
OWNED_MEAS = {512: 1227.0, 2048: 4510.0}                            # IDX.OWNED measured
TOPK = lambda n: 20 + n / 16                                         # noqa: E731  IDX.TOPK estimate (16 / cycle)
VM_IDX_READ = 2.0                                                    # indexed VM read: 4 outstanding, ~8 cycles


def merge_cycles(k):
    return MERGE_MEAS["points"].get(k) or MERGE_MEAS["base"] + MERGE_MEAS["per_output"] * k


def topk_merge_seq(k, n_local, G=96):
    parts = dict(local_topk=TOPK(n_local),
                 gathers=2 * coll_cycles("ALL_GATHER", G * n_local * 4, G)[0],
                 idx_merge=merge_cycles(k),
                 su_neg_id=60 + k / 64,
                 topk_neg_id=TOPK(k),
                 indexed_read=VM_IDX_READ * k)
    return sum(parts.values()), parts


def row_gather_seq(K, M, G=96, pipelined=False, c=1):
    bw = T.cv("hbm", "bytes_per_cycle")
    load = T.first_access() + 2048 / bw
    gat = 768 + coll_cycles("ALL_GATHER", G * 64, G)[0] - (108.6 + 23.75)   # the 3,072-flit delivery + latency
    store = T.cv("units", "DMA.store_latency") + G * 2048 / bw
    owned = OWNED_MEAS.get(K) or OWNED_MEAS[512] * K / 512
    lat = gat - 768
    rounds = math.ceil(M / c)                        # c slots per ALL_GATHER (the compiler's batching, c = 2: 393 KB VM)
    parts = dict(idx_owned=owned, first_load=load, gathers=(M * 768 + lat) if pipelined else rounds * (c * 768 + lat),
                 last_store=store)
    return sum(parts.values()), dict(parts, per_gather=round(c * 768 + lat, 1), M=M, slots_per_gather=c)


def argmax_merge_seq(G=96):
    return coll_cycles("ALL_GATHER", G * 64, G)[0] + 5


class SeqCost(DT.NativeCost):
    """NativeCost with the software sequences in place of TOPK_MERGE / ROW_GATHER / ARGMAX_MERGE."""

    def __init__(self, ops, recs, row_gather, M_override=None, pipelined=False, c=1, hc_g22=False, rtl=None):
        super().__init__(ops, recs, row_gather=row_gather)
        self.M_override, self.log, self.pipelined, self.c, self.hc_g22 = M_override, {}, pipelined, c, hc_g22
        self.rtl = rtl or {}                                 # unit.op -> measured RTL / simulator ratio

    def __call__(self, r, dyn, L):
        c, g, how = self.base(r, dyn, L)
        return c * self.rtl.get(f"{r.unit}.{r.op}", 1.0), g, how

    def base(self, r, dyn, L):
        if self.hc_g22 and r.unit == "HC" and r.op == "HC_MIX":
            full = super().__call__(r, dyn, L)[0]
            c = full / 24 + coll_cycles("ALL_GATHER", 24 * 4, 96)[0] + HC_POST     # G22: 1 row + gather + post
            self.log[(r.layer, r.tag)] = dict(op="HC_MIX (G22 rows + gather + post)", cycles=round(c, 1),
                                              was=round(full, 1))
            return c, "measured+model", "G22"
        if r.unit == "COLL" and r.op == "TOPK_MERGE":
            c, parts = topk_merge_seq(r.imm_a, r.desc["A"].n)
            self.log[(r.layer, r.tag)] = dict(op="TOPK_MERGE", k=r.imm_a, n_local=r.desc["A"].n,
                                              cycles=round(c, 1), parts={k: round(v, 1) for k, v in parts.items()})
            return c, "measured+model", "G20 sequence"
        if r.unit == "COLL" and r.op == "ROW_GATHER":
            s = self.rg[r.layer]
            M = self.M_override or s["max_owned"]
            c, parts = row_gather_seq(s["k"], M, pipelined=self.pipelined, c=self.c)
            self.log[(r.layer, r.tag)] = dict(op="ROW_GATHER", K=s["k"], cycles=round(c, 1),
                                              parts={k: round(v, 1) for k, v in parts.items()})
            return c, "measured+model", "G21 sequence"
        if r.unit == "COLL" and r.op == "ARGMAX_MERGE":
            c = argmax_merge_seq()
            self.log[(r.layer, r.tag)] = dict(op="ARGMAX_MERGE", cycles=round(c, 1))
            return c, "model", "exact gather + fold"
        return super().__call__(r, dyn, L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--rtl", type=Path, help="e2e_calibration output: apply its measured unit.op ratios (not DMA.*: "
                                             "priced at full bandwidth, the wide DMA -> VM port is being built)")
    a = ap.parse_args()
    rtl = {}
    if a.rtl:
        pu = json.loads(a.rtl.read_text())["result"]["per_unit"]
        rtl = {k: v["ds_L0"]["ratio"] for k, v in pu.items() if "ds_L0" in v and not k.startswith("DMA.")}
    d, recs = DT.load(a.program)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(a.run.read_text())["results"]:
        for s in x.get("row_gather") or []:
            rg[x["layer"]] = s
    base_cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    today = {}
    for r in recs:
        if r.unit == "COLL" and r.op in ("TOPK_MERGE", "ROW_GATHER", "ARGMAX_MERGE"):
            today[(r.layer, r.tag)] = round(base_cf(r, T.Dyn(DT.POS), 0)[0], 1)
    s_today = T.schedule(recs, DT.POS, "S2", cost_fn=base_cf)["total_cycles"]
    res = dict(today=dict(cycles=round(s_today, 1), tok_s=round(CLK / s_today, 1)))
    scen = [("software_sequences_M_measured_per_layer", dict()), ("software_sequences_M_12", dict(M_override=12)),
            ("software_sequences_slots_pipelined", dict(pipelined=True)),
            ("approved_path_c2_g22", dict(c=2, hc_g22=True))]
    if rtl:
        scen.append(("approved_path_c2_g22_current_rtl_ratios", dict(c=2, hc_g22=True, rtl=rtl)))
    res["rtl_ratios_applied"] = rtl
    for name, kw in scen:
        cf = SeqCost(d["ops"], recs, rg, **kw)
        s = T.schedule(recs, DT.POS, "S2", cost_fn=cf)
        ops = [dict(layer=k[0], tag=k[1], today_cycles=today.get(k, v.get("was")), **v) for k, v in cf.log.items()]
        res[name] = dict(cycles=round(s["total_cycles"], 1), tok_s=round(CLK / s["total_cycles"], 1),
                         delta_cycles=round(s["total_cycles"] - s_today, 1),
                         delta_pct=round(100 * (s["total_cycles"] / s_today - 1), 2), n_races=len(s["races"]),
                         ops=ops, op_sum_today=round(sum(o["today_cycles"] for o in ops), 1),
                         op_sum_sequences=round(sum(o["cycles"] for o in ops), 1))
        print(name, res[name]["cycles"], res[name]["tok_s"], res[name]["delta_pct"], flush=True)
    # the generic token-path charge (perf.py: one COLL.TOPK_MERGE of 2 x 512 words, the TU endpoint model)
    res["perf_generic_topk_merge_charge"] = round(coll_cycles("TOPK_MERGE", 2 * 512 * 2, 96)[0], 1)
    rec = dict(schema="opentallas.hgi_sim.ds_sw_seq_pricing.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               request="hgi-takeover 2026-10-09 16:48 PT + 10-10 inputs (IDX.MERGE 594 + 1.37 k, G22 HC rows, ROW_GATHER c = 2, DMA full bandwidth)",
               program=str(a.program.name), run=str(a.run.name), measured=dict(idx_merge=MERGE_MEAS,
                                                                               idx_owned=OWNED_MEAS),
               method=__doc__.split("\n\n")[1], result=res)
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
