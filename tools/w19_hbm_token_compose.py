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


def coll_us(nbytes_die: float, coll: dict, kind: str = "all_gather") -> float:
    c = coll.get(kind, coll.get("all_gather", coll))
    return c["fixed_us"] + nbytes_die * c["us_per_byte"]


def w15_prod(rec: dict, config: str) -> dict:
    """W15b's product-port pricing (results/rtl/w15_hbm_nvls.json reading_guide): a gather of B bytes a rank costs
    fixed + slope x ceil(B / slot_bytes) cycles (slot = 0.9 TB/s port x clock period); the all-reduce fit is per
    bench record and is applied per slot of the multicast output (W15b's extrapolation for the grouped reduce);
    the top-k merge adds the ot_coll_topk_merge select, 9 x (P x k / 64) cycles (W15b ESTIMATE, measurement queued)."""
    cfg = rec["configs"][config + "_prod"]
    ar = rec["configs"][config]["fit"]["all_reduce"]
    return dict(kind="w15_prod", hz=cfg["clock_hz"], slot=cfg["slot_bytes"], ag=cfg["fit"]["all_gather"], ar=ar,
                source=f"results/rtl/w15_hbm_nvls.json configs.{config}_prod (gathers) / {config} (all-reduce fit)")


def prod_us(op: dict, coll: dict, P: int) -> tuple[float, str]:
    hz, slot = coll["hz"], coll["slot"]
    k = op["kind"]
    if k == "all_reduce":
        n = math.ceil(P * op["bytes"] / slot)                         # the multicast output a die receives
        return (coll["ar"]["fixed_cycles"] + coll["ar"]["cycles_per_word"] * n) / hz * 1e6, "extrapolated"
    per_rank = P * op["bytes"] / TP
    cyc = coll["ag"]["fixed_cycles"] + coll["ag"]["cycles_per_word"] * math.ceil(per_rank / slot)
    how = "measured-fit"
    if k == "topk_merge" and op.get("what") in ("sel", "cand"):
        if coll.get("select_cycles") and op.get("what") == "sel":     # measured unit, blocking: P merges in series
            cyc += coll["select_cycles"] * P
            how = "fit + select MEASURED (series over positions)"
        else:
            cyc += 9 * (TP * op["k"] / 64) * P                        # select over the gathered candidates
            how = "fit + select ESTIMATE"
    return cyc / hz * 1e6, how


def w15_fit(rec: dict, config: str) -> dict:
    """W15's record layout: configs.<name>.fit.{all_gather,all_reduce}.{fixed_cycles, cycles_per_word} with 64-B
    words per rank and clock_hz."""
    cfg = rec["configs"][config]
    hz = cfg.get("clock_hz", rec.get("clock_hz"))
    out = {}
    for k, v in cfg["fit"].items():
        out[k] = dict(fixed_us=v["fixed_cycles"] / hz * 1e6, us_per_byte=v["cycles_per_word"] / 64 / hz * 1e6)
    return out


# dedicated-unit / stream-unit step costs (ns at 1.2 GHz), from the uarch model's own arch-DAG node prices on the
# 1M critical path (tools/uarch_model.arch_graph; W11 unit widths), mapped onto the program's local steps.  The index
# scan and local top-k are re-scaled from the ROM die's keys (262,144) to the TP-96 die's (1/96 of the keys), plus the
# unit's pipeline latency; serial-chain steps run in the 0.9 GHz domain (x 4/3).
# Each local step is the list of its arch-DAG nodes: (node, ns, class, ctrl_ns), at the arch clock (1.0339 GHz)
# from tools/uarch_model.arch_graph(1048576) contributions.  Classes (AGENTS.md operator fusion, 2026-10-01):
#   head      a chain's first op: its operand comes from the VM (a matvec, collective, scan or select wrote it)
#   chained   lane-local, consumes the previous op's lane register: under FUSION it pays its unit depth only
#             (the SU stream address-to-write SU_BASE = 29 cycles and its dispatch ctrl are removed)
#   reduce / rope / quant / select / scan   true cross-lane steps (reduction, pair rotation, segmented absmax
#             quantise, selection, KV scan): paid in full with or without fusion
# Unfused, every node pays its full price (the model's per-op VM round trip).
SU_BASE_NS = 29 / 1.0339e9 * 1e9            # tools/decode_critical_path.py SU_BASE at the arch clock
NORM = lambda q: [("norm.sumsq", 74.5, "reduce", 0.0), ("norm.rsqrt", 104.5, "chained", 6.8),  # noqa: E731
                  ("norm.scale", q, "chained", 6.8)]
NODE_PARTS = {
    "hc_pre_norm": ([("hc_pre", 42.6, "chained", 0.0)] + NORM(44.5) + [("quant", 40.6, "quant", 0.0)], "serial"),
    "q_norm_kv_row": (NORM(41.6) + [("q_quant", 40.6, "quant", 0.0)], "serial"),
    "q_rope": ([("q_rope", 37.7, "rope", 0.0)], "serial"),
    "attend": ([("scores", 159.6, "scan", 0.0), ("max", 74.0, "reduce", 0.0), ("exp", 124.2, "head", 0.0),
                ("pv", 176.0, "scan", 0.0), ("normalize+inv_rope", 105.4, "rope", 0.0)], "fast"),
    "hc_post": ([("hc_post", 73.5, "head", 6.8)], "serial"),
    "router_act": ([("softplus_sqrt", 278.6, "head", 0.0)], "serial"),
    "route": ([("bias", 32.9, "head", 0.0), ("top6", 31.9, "select", 6.8), ("top6_order", 25.1, "select", 6.8),
               ("route_w", 43.5, "chained", 6.8)], "serial"),
    "swiglu": ([("swiglu", 129.6, "head", 0.0)], "serial"),
    "moe_sum": ([("quant2", 40.6, "quant", 0.0)], "serial"),
    "index_q": ([("idx.q", 45.5, "rope", 0.0)], "serial"),
    "engram_mix": ([("eng.hh", 74.5, "reduce", 0.0), ("eng.gate", 288.2, "chained", 6.8),
                    ("eng.add", 59.0, "chained", 6.8)], "serial"),
    "engram_fetch": ([("eng.rows", 254.8, "head", 0.0)], "fast"),
    "cand_mask": ([], "fast"),
    "final_norm": ([("hc_pre", 42.6, "chained", 0.0)] + NORM(44.5), "serial"),
    "argmax_local": ([("argmax", 1415.3 * 1346 / 262144 + 139.3, "reduce", 0.0)], "serial"),
    "z_quant": ([("z_quant", 40.6, "quant", 0.0)], "serial"),     # charged at the wo_b matvec (its FP8 input)
}
FUSION = {"on": False}


def part_ns(fn):
    parts, dom = NODE_PARTS[fn]
    tot = 0.0
    for name, ns, cls, ctrl in parts:
        if FUSION["on"] and cls == "chained":
            ns = ns - SU_BASE_NS - ctrl
        tot += ns
    return tot, dom


def class_split(prog: dict) -> dict:
    """Unfused ns (at the domain clock) of the token's on-path local steps by op class, and the fused saving."""
    out = {}
    for lay in prog["layers"]:
        swi = False
        for op in lay["ops"]:
            fn = op.get("fn") if op["kind"] == "local" else ("z_quant" if op.get("tag") == "wo_b" else None)
            if fn not in NODE_PARTS:
                continue
            if fn == "swiglu":                       # charged once a layer (the slots' rows run together)
                if swi:
                    continue
                swi = True
            parts, dom = NODE_PARTS[fn]
            f = F_FAST / F_SERIAL if dom == "serial" else 1.0
            for name, ns, cls, ctrl in parts:
                c = out.setdefault(cls, dict(ops=0, ns=0.0, fused_saving_ns=0.0))
                c["ops"] += 1
                c["ns"] += ns * f
                if cls == "chained":
                    c["fused_saving_ns"] += (SU_BASE_NS + ctrl) * f
    return {k: dict(ops=v["ops"], us=round(v["ns"] / 1e3, 2), fused_saving_us=round(v["fused_saving_ns"] / 1e3, 2))
            for k, v in out.items()}
OFF_PATH = {"hc_mixes", "compressor", "cand_apply"}
# P verify positions on the dedicated / stream units: each extra position repeats the step's ISSUE, the pipeline
# depth is paid once.  The issue fraction of the chain's dedicated time is the model's own
# (v41_hbm_chain(positions=6): verify_extra_issue 95.955 us over dedicated_and_su 103.253 us for 5 extra positions).
ISSUE_FRAC = 95.955 / 103.253 / 5
LOCAL_REPEAT = lambda P: 1.0 + (P - 1) * ISSUE_FRAC  # noqa: E731
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
    ns, dom = part_ns(fn)
    return ns * (F_FAST / F_SERIAL if dom == "serial" else 1.0), dom


def compose(prog: dict, sm: SMTable, coll: dict, fetch_us: float, m: dict, mtp: dict | None = None) -> dict:
    """mtp: None (one position) or dict(P, union{layer: n}, stream_us_per_expert): the verify pass rides the SM
    columns (measured: 6-column cycles = 1-column), carries P positions' bytes in each collective, repeats the
    per-position dedicated/SU steps and the head's attention P times, and streams the union of routed experts
    (each expert's w1/w3/w2 lines once) with the fetch exposed as max(first access, union stream - SM work)."""
    per_layer, flags = [], set()
    P = mtp["P"] if mtp else 1
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
            if k == "mv" and op["tag"] == "wo_b":
                t["local"] += LOCAL_REPEAT(P) * local_cycles(dict(fn="z_quant"), m)[0] / 1e3
            if k == "mv":
                rows_die = max(r1 - r0 for r0, r1 in op["rows"])
                R = math.ceil(rows_die / N_SM)
                lines, drain, how = sm.op(op["fmt"], op["k"], R)
                if mtp and op["tag"].startswith("expert slot") and "slot 6" not in op["tag"]:
                    lines = lines * mtp["union"][lay["layer"]] / 6.0     # the union's weights pass once
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
                    t["local"] += LOCAL_REPEAT(P) * local_cycles(op, m)[0] / 1e3
                    swi = True
                continue
            flush()
            if k in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                if op["tag"].startswith(OFF_PATH_COLL):       # ready at token start / only masks later layers
                    t["off_path_collectives"] = t.get("off_path_collectives", 0) + 1
                    continue
                if coll.get("kind") == "w15_prod":
                    us, how = prod_us(op, coll, P)
                    if how != "measured-fit":
                        flags.add(f"collective {op['tag']}: {how}")
                    t["collective"] += us
                else:
                    t["collective"] += coll_us(P * op["bytes"] / TP, coll,
                                               "all_reduce" if k == "all_reduce" else "all_gather")
                ncoll += 1
            elif k == "expert_fetch":
                if mtp:
                    stream = mtp["stream_us_per_expert"] * mtp["union"][lay["layer"]]
                    t["fetch"] += max(fetch_us, stream - mtp["union"][lay["layer"]] / 6.0 * mtp["routed_sm_us"])
                else:
                    t["fetch"] += fetch_us
            elif k == "local":
                if op["fn"] == "index_scores":
                    m["n_keys"] = op["n"]
                ns, _ = local_cycles(op, m)
                t["local"] += LOCAL_REPEAT(P) * ns / 1e3
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
    ap.add_argument("--fetch-case", default="ar_L0_refresh_postponed")
    ap.add_argument("--mtp", type=Path, help="the 96-rank MTP record: compose the 6-position verify pass")
    ap.add_argument("--coll-config", default="hbm_p48_ss")
    ap.add_argument("--select", type=Path, help="W15b's measured 96-way select record (replaces the estimate)")
    ap.add_argument("--fusion", action="store_true", help="AGENTS.md operator fusion: chained lane-local SU ops "
                    "pay unit depth only")
    ap.add_argument("--record", type=Path)
    a = ap.parse_args()
    prog = json.loads(a.program.read_text())
    sm = SMTable([json.loads(p.read_text()) for p in a.sm], "ar")
    if a.coll:
        coll = w15_prod(json.loads(a.coll.read_text()), a.coll_config)
        if a.select:
            sr = json.loads(a.select.read_text())
            cs = sr["cases"] if isinstance(sr["cases"], list) else []
            coll["select_cycles"] = next(c["cycles"] for c in cs if c["case"] == "l20_index_topk" and c["exact"])
            coll["select_source"] = f"{a.select} l20_index_topk (P={sr['parameters']['P']})"
    else:
        coll = dict(fixed_us=0.83, us_per_byte=1 / 0.9e12 * 1e6, source="PENDING: audit scratch W15 NVLS P=6 "
                    "(0.81-0.89 us), slope at the 0.9 TB/s package link")
    if a.fetch:
        fetch_us = json.loads(a.fetch.read_text())["audit_comparison"]["exposed_ns"][a.fetch_case] / 1e3
        fsrc = f"{a.fetch} exposed_ns[{a.fetch_case}]"
    else:
        fetch_us, fsrc = 0.5, "PENDING: audit central 0.5 us"
    FUSION["on"] = a.fusion
    m = dict(n_keys=0, node_parts=NODE_PARTS, fusion=a.fusion, op_class_split_unfused=class_split(prog), off_path=sorted(OFF_PATH),
             source="uarch_model arch-DAG node prices on the 1M path (W11 widths), serial steps at 0.9 GHz")
    mtp = None
    if a.mtp:
        mr = next(iter(json.loads(a.mtp.read_text())["runs"].values()))["result"]
        fr = json.loads(a.fetch.read_text()) if a.fetch else None
        case = next((c for c in fr["cases"] if c["case"] == "mtp_union35_refresh_postponed"), None) if fr else None
        # one stack share: 35 experts streamed in (done - req) ns
        per = ((case["ns_from_first_router_value"]["done"] - case["ns_from_first_router_value"]["req"]) / 1e3 / 35
               if case else 3.6e12 ** -1 * 191e3 * 1e6 / 0.797)
        rsm = sm.op("fp4", 5120, 1)
        routed = 12 * (rsm[0]) / F_FAST * 1e6                  # 6 experts' w1/w3 lines on the SM (AR)
        mtp = dict(P=len(mr["positions"]), union={l["layer"]: l["n_union"] for l in mr["layers"]},
                   stream_us_per_expert=per, routed_sm_us=routed)
    res = compose(prog, sm, coll, fetch_us, m, mtp)
    if mtp:
        res["mtp_inputs"] = dict(P=mtp["P"], mean_union=sum(mtp["union"].values()) / len(mtp["union"]),
                                 stream_us_per_expert=round(mtp["stream_us_per_expert"], 4))
    res.update(collective_model=coll, fetch_source=fsrc, dedicated=m)
    print(json.dumps({k: v for k, v in res.items() if k != "layers"}, indent=1))
    if a.record:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        rec = dict(schema="opentallas.uarch.w19_hbm_token.v1", source_commit=head,
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   inputs={str(p): sha(p) for p in (a.program, *a.sm, a.fetch, a.coll, a.select) if p},
                   source_sha256={"tools/w19_hbm_token_compose.py": sha(ROOT / "tools/w19_hbm_token_compose.py")},
                   result=res)
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
