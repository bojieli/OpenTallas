#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash 1M token re-timed on the NATIVE HGI-1 record stream: the exact per-die program that runs
bit-exact in the simulator (hgi_sim.ds_native --program-out, rank 0: a head die), scheduled with the command
processor modelled (hgi_sim.timing), instead of the one-record-per-w19-op stream of hgi_sim.ds_hgi.

Unit costs (1.2 GHz cycles), per record:
  SM.MATVEC, HC.HC_MIX, FUSED.HC_PRE_NORM / HC_POST, IDX.*, ARGMAX, COLL.*   the DS composition's walk price of the
        w19 op the record lowers (ds_hgi.WalkCost: measured adapters at the target clocks); an op lowered to several
        records of one unit (the per-buffer all-gathers) splits its price evenly over them
  ATT.QK / ATT.PV      the walk's attention-tile rows of the attend op, half each
  SU.VOP               the SU depth model per record (timing.su_cost; == the RTL emit -> write depth for every op
        class, hbm_su_c12): the native stream runs every SU template as its own record, where the walk prices a
        fused chain -- the difference is the native lowering's cost
  FUSED.QDQ_*          ceil(n / 32) + 8 (ot_hdc_fp4qdq / the DS quantiser: 32 elements a cycle, II 1, latency 8)
  DMA.* / CTL.*        timing.cost (first access measured, stores / fences estimates)
Wait masks are recomputed over the whole token (the per-layer programs' masks do not see the previous layer).

    python3 -m hgi_sim.ds_native_timing --program PROG.json --out REC.json        (from tools/; ~minutes)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402
from hgi_sim.ds_hgi import WalkCost  # noqa: E402
from hgi_sim.records import decode_one, encode_program  # noqa: E402

POS = 1048575


def load(path):
    d = json.loads(Path(path).read_text())
    recs = []
    for lay in d["layers"]:
        for x in lay["records"]:
            r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
            r.tag, r.family, r.reads, r.writes = x["tag"], x["family"], x["reads"], x["writes"]
            r.src_key = None if not x["src"] else f"{x['src'][0]}:{x['src'][1]}"
            r.src_extra = [f"{x['src'][0]}:{e}" for e in x["src"][2]] if x["src"] and len(x["src"]) > 2 else []
            r.layer = lay["layer"]
            recs.append(r)
    return d, recs


ROW_BYTES = 288          # a DS compressed KV row as shipped: 9 sectors of 32 B (spec 6.10)


class NativeCost:
    def __init__(self, ops, recs, row_gather=None):
        self.wc = WalkCost()
        self.ops = ops
        self.rg = row_gather or {}          # layer -> {max_owned, k, G}: the bypass ROW_GATHER pricing
        self.prepare(recs)

    def row_gather(self, r, dyn, L):
        """Bypass ROW_GATHER (hgi-die-gaps round 4): each owner reads its selected rows from its row store, padded to
        the group's maximum owned count M, then ONE exact gather pass (every rank contributes M rows), and the head
        dies write the k received rows to HBM.  M is the bit-exact run's selection (row_gather stats)."""
        from hgi_sim.perf import coll_cycles
        s = self.rg[r.layer]
        M_, G, k = s["max_owned"], s["G"], s["k"]
        bw = T.cv("hbm", "bytes_per_cycle")
        read = T.first_access() + M_ * ROW_BYTES / bw
        gat, g, _ = coll_cycles("ALL_GATHER", G * M_ * ROW_BYTES, G)
        write = k * ROW_BYTES / bw
        return read + gat + write, "measured_tu_budget", (f"bypass row gather: max owned {M_} of {k} rows over {G} "
                                                          f"(pad {M_ * G / k:.2f}x), read {read:.0f} + gather "
                                                          f"{gat:.0f} + write {write:.0f}")

    def prepare(self, recs):
        """Per-stream bookkeeping: records of one op on one unit share its price; consecutive expert-slot matvecs
        are one flush group (the walk's rule)."""
        self.share = Counter((r.src_key, r.unit) for r in recs if r.src_key)
        prev = None
        for r in recs:
            # the walk's flush group = consecutive expert-slot matvecs IN THE SM QUEUE (the SM runs its records in
            # order; another unit's record between two slots does not drain the SM)
            r.batched = False
            if r.unit == "SM":
                if r.tag.startswith("expert slot"):
                    r.batched = prev is not None
                    prev = r
                else:
                    prev = None

    def walk(self, r, part=None):
        key = r.src_key
        op = self.ops[key]
        L = int(key.split(":")[0])
        r.src = dict(layer=L if L < 40 else "head", op=op, batched=getattr(r, "batched", False), part=part)
        ex = getattr(r, "src_extra", None)
        if ex:                                   # G18 frame: the record also runs these w19 ops
            r.src["extra"] = [self.ops[k] for k in ex]
        return self.wc(r, None, 0)

    def __call__(self, r, dyn, L):
        u, op = r.unit, r.op
        if u == "CTL":
            return (0.0 if op == "NOP" else 1.0), "estimate", f"CTL.{op}"
        if u == "SU":
            c, how = T.su_cost(r, dyn, L)
            return c, "measured_depth_model", how
        if u == "FUSED" and op.startswith("QDQ"):
            n = r.desc["A"].n
            return math.ceil(n / 32) + 8, "rtl_spec", "DS quantiser: 32 / cycle, latency 8"
        if u in ("DMA",):
            return T.cost(r, dyn, L)
        if u == "COLL" and op == "ROW_GATHER" and getattr(r, "layer", None) in self.rg:
            return self.row_gather(r, dyn, L)
        if u == "ATT":
            c, g, how = self.walk(r, part="tile")
            return c / 2, g, how
        if r.src_key is None:
            return T.cost(r, dyn, L)
        c, g, how = self.walk(r)
        n = getattr(r, "share", None) or self.share[(r.src_key, u)]
        return c / n, g, how + (f" (/{n} records)" if n > 1 else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--run", type=Path, help="the ds_native result of the same program: ROW_GATHER bypass pricing")
    a = ap.parse_args()
    d, recs = load(a.program)
    recs = T.rebuild_waits(recs)           # (copies keep src_key / layer)
    rg = {}
    if a.run:
        for x in json.loads(a.run.read_text())["results"]:
            for s in x.get("row_gather") or []:
                rg[x["layer"]] = s
    cf = NativeCost(d["ops"], recs, row_gather=rg)
    image = encode_program(recs)
    walk_us, _ = cf.wc.DA.walk({"layers": []}, cf.wc.sm, cf.wc.su1, cf.wc.coll, cf.wc.local, cf.wc.hbm, use=cf.wc.use)
    res = dict(program=dict(rank=d["rank"], records=len(recs), image_bytes=len(image),
                            image_sha256=hashlib.sha256(image).hexdigest(),
                            unit_ops=dict(Counter(f"{r.unit}.{r.op}" for r in recs).most_common())))
    S = {}
    for mode in ("S0", "S1", "S2"):
        s = T.schedule(recs, POS, mode, cost_fn=cf)
        S[mode] = s
        res[mode] = dict(total_cycles=round(s["total_cycles"], 1), us=round(s["total_cycles"] / 1200, 3),
                         tok_s=round(1.2e9 / s["total_cycles"], 1), records_executed=s["records_executed"],
                         cp_busy_cycles=s["cp_busy"], n_races=len(s["races"]), races=s["races"][:5],
                         per_unit=s["per_unit"], family_unit_cycles=dict(list(s["family_unit_cycles"].items())[:30]))
        print(mode, res[mode]["total_cycles"], res[mode]["us"], "races", len(s["races"]), flush=True)
    v = {}
    v["S2_no_wires"] = T.schedule(recs, POS, "S2", wires=False, cost_fn=cf)["total_cycles"]
    ls = T.list_schedule(recs, POS, cost_fn=cf)
    sls = T.schedule(ls, POS, "S2", cost_fn=cf)
    v["S2_list_scheduled"] = sls["total_cycles"]
    v["S2_list_scheduled_races"] = len(sls["races"])
    v["S2_list_scheduled_no_wires"] = T.schedule(ls, POS, "S2", wires=False, cost_fn=cf)["total_cycles"]
    res["variants"] = {k: (round(x, 1) if isinstance(x, float) else x) for k, x in v.items()}
    su = sum(c[0] for r, c in zip(recs, (cf(r, T.Dyn(POS), 0) for r in recs)) if r.unit == "SU")
    res["su_record_cycles_sum"] = round(su, 1)
    res["compare"] = dict(
        published_walk_us=460.05, ds_hgi_walk_op_stream_S2_cycles=544648, ds_hgi_list_scheduled_cycles=461646,
        native_S2_vs_walk_op_S2_pct=round(100 * (S["S2"]["total_cycles"] / 544648 - 1), 2),
        native_list_vs_walk_op_list_pct=round(100 * (sls["total_cycles"] / 461646 - 1), 2))
    res["critical_path_S2_tail"] = T.critical_path(S["S2"], recs)[-30:]
    print(json.dumps(res["variants"]), json.dumps(res["compare"]), flush=True)
    rec = dict(schema="opentallas.hgi_sim.ds_native_timing.v1", position=POS,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               grade="pathfinding: walk-priced engine records (measured adapters), SU per record by the measured-depth "
                     "model, CP entries estimates (calibration.json)",
               program_source=str(a.program.name), program_sha256=hashlib.sha256(a.program.read_bytes()).hexdigest(),
               result=res, calibration_cp=T.CAL["cp"],
               run_source=str(a.run) if a.run else None,
               row_gather_bypass=dict(rule="owner read padded to the max owned count + one exact gather pass "
                                           "(perf.coll_cycles ALL_GATHER, measured TU endpoint model) + head HBM write",
                                      layers={str(k): v for k, v in rg.items()}) if rg else None)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
