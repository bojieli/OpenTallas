#!/usr/bin/env python3
"""Runtime composition of the V4.1 HBM comparator's TP-96 decode token from measured elements (W19 B6/B7).

    python3 tools/w19_hbm_token_compose.py --program PROG.json --sm results/rtl/w19_sm_real_ops.json \
        [--fetch results/rtl/w19_expert_fetch.json] [--coll W15_RECORD.json] [--record results/uarch/w19_hbm_token.json]

WHAT IS COMPOSED.  The values of the token come from tools/w19_hbm_tp96_isa.py: the 96-rank executor of the TP-96 op
program, bit-exact per layer against the golden (and at the head against the 1M reference token 21946).  This tool
walks the SAME program (its JSON, op by op, in program order: every op of a layer depends on its predecessor except
where noted) and prices each op from a measured element:

  mv           the SM element (W13's ot_gpu_sm_v) run on the op's real operands by tools/w19_sm_real_ops.py: the
               die's busiest SM (32 SMs a die, rows split evenly) takes `lines` issue cycles plus the measured
               drain (last weight line -> last result).  Weights stream ahead through the bulk copy (the model's
               prefetching supply), so the first-line latency is not on the chain except where the weights are
               data-dependent (routed experts: the fetch below).  Consecutive independent matvecs (the 7 expert
               slots' w1/w3, their w2) issue back to back on the SMs: their lines add, one drain.  An op shape not in
               the SM record is priced by the SM record's per-format line rate and drain (flagged).
  local        the dedicated units at TP-96 widths (W11's elements, results/uarch/v41_dedicated_units.json rates):
               per-die index scoring at NK = 4 keys a cycle over the die's own keys, one head of attention a die,
               top-k at one comparator rank a key; the stream-unit steps (norms, hyper-connection mixes, Sinkhorn,
               RoPE, quantisers, SwiGLU, routing) at their W11 chain depths; the serial-chain units in the 0.9 GHz
               domain (AGENTS.md clock domains).
  collectives  the W15 switch: latency = fixed + per-byte slope at the op's bytes a die, from the W15 record when given,
               else the audit's scratch NVLS figures (labelled PENDING).
  expert_fetch the routed-expert fetch path (B2 record): the exposed first-access latency after the router, when given,
               else the audit's central 0.5 us (PENDING).
  boundaries   one hardware barrier (78 cycles, measured tb_gpu_barrier) per dependent SM-op boundary.

This is a composition of element measurements along the executed program, not a whole-die cycle-accurate simulation;
the record says which terms are measured, scaled or pending.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F_FAST = 1.2e9            # streaming domain: SMs, links, HBM service, index scan, attention tiles
F_SERIAL = 0.9e9          # serial-chain domain: SU, SFU, softplus, Sinkhorn, reducers, select
BARRIER_CYC = 78          # measured boundary (62 barrier + 16), results/rtl/gpu_supply_barrier.json
N_SM = 32
TP = 96


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class SMTable:
    """Measured SM cycles on real operands, keyed by (fn, fmt, K, rows on the busiest SM, cols)."""

    def __init__(self, recs: list, label: str):
        self.rows = {}
        for c in [c for rec in recs for c in rec["cases"].get(label, [])]:
            key = (c["fmt"], c["K"], c["sm_rows"][1] - c["sm_rows"][0])
            r = c["rtl"]
            self.rows[key] = dict(lines=r["lines"], drain=r["drain_last_line_to_last_result"],
                                  start_to_done=r["cycles_start_to_done"], exact=c["exact"])
        # per-format line rate (lines per row per K) and median drain, for unmeasured shapes
        self.rate, self.drain = {}, {}
        for (fmt, K, R), v in self.rows.items():
            self.rate.setdefault(fmt, []).append(v["lines"] / (R * K))
            self.drain.setdefault(fmt, []).append(v["drain"])

    def op(self, fmt, K, R):
        fmt = {"fp8": "v41_fp8", "fp4": "v41_fp4", "bf16": "v41_bf16"}.get(fmt, fmt)
        if (fmt, K, R) in self.rows:
            v = self.rows[(fmt, K, R)]
            return v["lines"], v["drain"], "measured"
        rs = sorted(self.rate[fmt])
        ds = sorted(self.drain[fmt])
        return math.ceil(max(rs) * R * K), ds[len(ds) // 2], "scaled"


def coll_us(nbytes_die: float, coll: dict) -> float:
    return coll["fixed_us"] + nbytes_die * coll["us_per_byte"]


# dedicated-unit / stream-unit step costs (ns at 1.2 GHz), from the uarch model's own arch-DAG node prices on the
# 1M critical path (tools/uarch_model.arch_graph; W11 unit widths), mapped onto the program's local steps.  The index
# scan and local top-k are re-scaled from the ROM die's keys (262,144) to the TP-96 die's (1/96 of the keys), plus the
# unit's pipeline latency; serial-chain steps run in the 0.9 GHz domain (x 4/3).
NODE_NS = {
    "hc_pre_norm": (42.6 + 74.5 + 104.5 + 44.5, "serial"),       # hc_pre, norm sumsq, rsqrt, scale
    "q_norm_kv_row": (74.5 + 104.5 + 41.6 + 40.6, "serial"),     # q_norm sumsq, rsqrt, scale, q quant
    "q_rope": (37.7, "serial"),
    "attend": (159.6 + 74.0 + 124.2 + 176.0 + 105.4, "fast"),    # scores, max, exp, pv, normalize (16-head price)
    "hc_post": (73.5, "serial"),
    "router_act": (278.6, "serial"),                              # softplus_sqrt
    "route": (32.9 + 31.9 + 25.1 + 43.5, "serial"),               # bias, top6, order, route weights
    "swiglu": (129.6, "serial"),
    "moe_sum": (40.6, "serial"),                                  # quant2 / sum
    "index_q": (45.5, "serial"),
    "engram_mix": (288.2 + 74.5 + 59.0, "serial"),
    "engram_fetch": (254.8, "fast"),
    "cand_mask": (0.0, "fast"),
    "final_norm": (42.6 + 74.5 + 104.5 + 44.5, "serial"),
    "argmax_local": (1415.3 * 1346 / 262144 + 139.3, "serial"),
}
OFF_PATH = {"hc_mixes", "compressor", "cand_apply"}
OFF_PATH_COLL = ("engram.", "candidate merge")             # Engram rows/kv (hash ids known at token start); L20 cands   # overlap the attention chain (inputs ready, outputs used later)
IDX_SCORE_NS, IDX_TOPK_NS, ROM_KEYS = 1686.7, 1415.3, 262144
UNIT_LAT_CYC = 48


def local_cycles(op: dict, m: dict) -> tuple[float, str]:
    """(ns at the unit's domain clock, note) of one local step on the chain; 0 for off-path steps."""
    fn = op["fn"]
    if fn in OFF_PATH:
        return 0.0, "off-path"
    if fn == "index_scores":
        keys = math.ceil(op["n"] / TP)
        return IDX_SCORE_NS * keys / ROM_KEYS + UNIT_LAT_CYC / F_FAST * 1e9, "fast"
    if fn in ("topk_local", "cand_local"):
        keys = math.ceil(m["n_keys"] / TP)
        return (IDX_TOPK_NS * keys / ROM_KEYS + UNIT_LAT_CYC / F_FAST * 1e9) * F_FAST / F_SERIAL, "serial"
    ns, dom = NODE_NS[fn]
    return ns * (F_FAST / F_SERIAL if dom == "serial" else 1.0), dom


def compose(prog: dict, sm: SMTable, coll: dict, fetch_us: float, m: dict) -> dict:
    per_layer, flags = [], set()
    tot = dict(sm=0.0, barrier=0.0, collective=0.0, local=0.0, fetch=0.0)
    for lay in prog["layers"]:
        t = dict(sm=0.0, barrier=0.0, collective=0.0, local=0.0, fetch=0.0)
        pend = None                                    # a run of independent matvecs issued back to back
        ncoll = 0
        swi = False

        def flush():
            nonlocal pend
            if pend:
                t["sm"] += (pend["lines"] + pend["drain"]) / F_FAST * 1e6
                t["barrier"] += BARRIER_CYC / F_FAST * 1e6
            pend = None
        for op in lay["ops"]:
            k = op["kind"]
            if k == "mv":
                rows_die = max(r1 - r0 for r0, r1 in op["rows"])
                R = math.ceil(rows_die / N_SM)
                lines, drain, how = sm.op(op["fmt"], op["k"], R)
                if how != "measured":
                    flags.add(f"SM shape {op['fmt']} K={op['k']} R={R} priced by line rate (not measured)")
                batchable = op["tag"].startswith("expert slot")
                if pend and batchable and pend["batch"]:
                    pend["lines"] += lines
                    pend["drain"] = max(pend["drain"], drain)
                else:
                    flush()
                    pend = dict(lines=lines, drain=drain, batch=batchable)
                continue
            if k == "local" and op["fn"] == "swiglu":     # the SMs' SIMT lanes, on the rows each SM produced:
                if not swi:                               # charged once a layer (the slots' rows run together)
                    t["local"] += local_cycles(op, m)[0] / 1e3
                    swi = True
                continue
            flush()
            if k in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                if op["tag"].startswith(OFF_PATH_COLL):       # ready at token start / only masks later layers
                    t["off_path_collectives"] = t.get("off_path_collectives", 0) + 1
                    continue
                t["collective"] += coll_us(op["bytes"] / TP, coll)
                ncoll += 1
            elif k == "expert_fetch":
                t["fetch"] += fetch_us
            elif k == "local":
                if op["fn"] == "index_scores":
                    m["n_keys"] = op["n"]
                ns, _ = local_cycles(op, m)
                t["local"] += ns / 1e3
        flush()
        offc = t.pop("off_path_collectives", 0)
        per_layer.append(dict(layer=lay["layer"], collectives=ncoll, off_path_collectives=offc,
                              us={k: round(v, 3) for k, v in t.items()}, total_us=round(sum(t.values()), 3)))
        for kk in tot:
            tot[kk] += t[kk]
    T = sum(tot.values())
    return dict(collectives_on_path=sum(l["collectives"] for l in per_layer), total_us=round(T, 2), tokens_s=round(1e6 / T, 1), parts_us={k: round(v, 2) for k, v in tot.items()},
                layers=per_layer, flags=sorted(flags))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", type=Path, required=True)
    ap.add_argument("--sm", type=Path, nargs="+", required=True)
    ap.add_argument("--fetch", type=Path)
    ap.add_argument("--coll", type=Path)
    ap.add_argument("--record", type=Path)
    a = ap.parse_args()
    prog = json.loads(a.program.read_text())
    sm = SMTable([json.loads(p.read_text()) for p in a.sm], "ar")
    if a.coll:
        c = json.loads(a.coll.read_text())
        coll = dict(fixed_us=c["fit"]["fixed_us"], us_per_byte=c["fit"]["us_per_byte"], source=str(a.coll))
    else:
        coll = dict(fixed_us=0.83, us_per_byte=1 / 0.9e12 * 1e6, source="PENDING: audit scratch W15 NVLS P=6 "
                    "(0.81-0.89 us), slope at the 0.9 TB/s package link")
    if a.fetch:
        fetch_us = json.loads(a.fetch.read_text())["exposed_fetch_us"]
        fsrc = str(a.fetch)
    else:
        fetch_us, fsrc = 0.5, "PENDING: audit central 0.5 us"
    m = dict(n_keys=0, node_ns=NODE_NS, off_path=sorted(OFF_PATH),
             source="uarch_model arch-DAG node prices on the 1M path (W11 widths), serial steps at 0.9 GHz")
    res = compose(prog, sm, coll, fetch_us, m)
    res.update(collective_model=coll, fetch_source=fsrc, dedicated=m)
    print(json.dumps({k: v for k, v in res.items() if k != "layers"}, indent=1))
    if a.record:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        rec = dict(schema="opentallas.uarch.w19_hbm_token.v1", source_commit=head,
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   inputs={str(p): sha(p) for p in (a.program, *a.sm, a.fetch, a.coll) if p},
                   source_sha256={"tools/w19_hbm_token_compose.py": sha(ROOT / "tools/w19_hbm_token_compose.py")},
                   result=res)
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
